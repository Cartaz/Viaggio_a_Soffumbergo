extends SceneTree
## Real shoulder contacts plus an ordinary-control exit/re-entry on both sides.

const Scene = preload("res://godot/scenes/circuit_practice.tscn")
var failures: Array[String] = []
var checks := 0
var capture := false
var output := "build/shoulder_validation"
var hz := 120
var startup_msec := 0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		capture = capture or arg == "--capture"
		if arg.begins_with("--hz="):
			hz = int(arg.trim_prefix("--hz="))
		if arg.begins_with("--output="):
			output = arg.trim_prefix("--output=")
	Engine.physics_ticks_per_second = hz * 8
	Engine.time_scale = 8
	Engine.max_physics_steps_per_frame = 32
	call_deferred("run")


func run() -> void:
	var started := Time.get_ticks_msec()
	var scene := Scene.instantiate()
	scene.automated = true
	root.add_child(scene)
	for i in range(600):
		if not scene.switching:
			break
		await process_frame
	check(scene.ready_ok and not scene.switching, "Construction with shoulders ready")
	if not failures.is_empty():
		quit(1)
		return
	var final_vehicle := preload("res://godot/tests/final_vehicle_guard.gd").inspect(scene.vehicle)
	check(
		bool(final_vehicle.approved_assembly_loaded),
		"Approved Yaris, pirate rig, Bernie and Bianca required"
	)
	if not failures.is_empty():
		quit(1)
		return
	var groups: Array = JSON.parse_string(
		FileAccess.get_file_as_string(
			ProjectSettings.globalize_path("res://").path_join(
				"build/shoulder_validation/probes.json"
			)
		)
	)
	for group in groups:
		group["layer"] = 8
	var road_groups: Array = JSON.parse_string(
		FileAccess.get_file_as_string(
			ProjectSettings.globalize_path("res://").path_join(
				"build/construction_validation/probes.json"
			)
		)
	)
	for group in road_groups:
		group["layer"] = 4
	groups.append_array(road_groups)
	# The exhaustive scan belongs to headless acceptance, not the visible drive.
	if capture:
		groups = []
	var rays := 0
	var road_rays := 0
	var shoulder_rays := 0
	var max_error := 0.0
	for group in groups:
		# A frozen car is outside the measured driving interval during the geometry scan.
		scene.vehicle.freeze = true
		scene.switching = true
		var p: Vector3 = scene.vector(group.points_m[0])
		scene.recovery_focus = p
		scene.refresh_stream()
		while not scene.pending.is_empty():
			scene.load_next()
		await physics_frame
		await physics_frame
		for point in group.points_m:
			p = scene.vector(point)
			var hit: Dictionary = scene.get_world_3d().direct_space_state.intersect_ray(
				PhysicsRayQueryParameters3D.create(
					p + Vector3.UP * 3, p - Vector3.UP * 3, int(group.layer)
				)
			)
			check(not hit.is_empty(), "Actual shoulder collider ray")
			if not hit.is_empty():
				max_error = maxf(max_error, absf(hit.position.y - p.y))
				check(hit.normal.y > 0, "Shoulder front faces upwards")
			rays += 1
			road_rays += int(group.layer == 4)
			shoulder_rays += int(group.layer == 8)
	if rays > 0:
		check(max_error < .003, "Shoulder Jolt height matches independent interpolation")
	var fixture: Dictionary = JSON.parse_string(
		FileAccess.get_file_as_string(
			ProjectSettings.globalize_path("res://").path_join(
				"build/shoulder_validation/recovery_route.json"
			)
		)
	)
	scene.practice.sections = [fixture]
	scene.switching = false
	await scene.select_section(0)
	var car: LaboratoryVehicle = scene.vehicle
	startup_msec = Time.get_ticks_msec() - started
	for i in range(hz):
		await physics_frame
	var before_relocations: int = scene.relocations
	var before_resets: int = scene.resets
	var start_time := car.elapsed
	var minimum_up := 1.0
	var unsupported := 0
	var frozen := 0
	var right_exit := false
	var left_exit := false
	var shoulder_wheel_hits := 0
	var max_signed := 0.0
	var min_signed := 0.0
	var captures: Array[String] = []
	for frame in range(hz * 220):
		var progress: float = scene.route.progress
		var distance: float = minf(progress + 4, scene.route.station[-1])
		var target: Vector3 = scene.route.at(distance)
		var tangent: Vector3 = (
			(scene.route.at(distance + 1) - scene.route.at(distance - 1)).normalized()
		)
		var normal := Vector3(-tangent.z, 0, tangent.x).normalized()
		var offset := 4.2 * pow(sin(TAU * distance / 200), 3)
		target += normal * offset
		var relative := car.basis.inverse() * (target - car.position)
		var angle := atan2(relative.x, -relative.z)
		car.steering_target = clampf(atan(2 * 2.56 * sin(angle) / 4) / .52, -1, 1)
		var wanted := 2.0 if progress < 188 else 0.8 if progress < 194 else 0.0
		var speed := car.road_speed_m_s()
		car.throttle = clampf((wanted - speed) * .4 + .12, 0, .75) if wanted > 0 else 0.0
		car.braking = clampf((speed - wanted) * .4, 0, .6) if wanted > 0 else .6
		await physics_frame
		minimum_up = minf(minimum_up, car.basis.y.dot(Vector3.UP))
		unsupported += int(car.diagnostic_contact_count == 0)
		frozen += int(car.freeze or car.reset_requested)
		var signed_offset: float = (car.position - scene.route.at(scene.route.progress)).dot(normal)
		max_signed = maxf(max_signed, signed_offset)
		min_signed = minf(min_signed, signed_offset)
		right_exit = right_exit or signed_offset > 3.5
		left_exit = left_exit or signed_offset < -3.5
		if frame % maxi(1, hz / 10) == 0:
			for anchor: Vector3 in car.wheel_anchors:
				var q := car.global_transform * anchor
				var hit := car.get_world_3d().direct_space_state.intersect_ray(
					PhysicsRayQueryParameters3D.create(q + Vector3.UP * 2, q - Vector3.UP * 4, 8)
				)
				shoulder_wheel_hits += int(not hit.is_empty())
		if capture:
			var label := (
				"right_exit"
				if progress > 45 and progress < 55
				else "left_exit" if progress > 145 and progress < 155 else ""
			)
			if not label.is_empty() and not captures.has(label):
				captures.append(label)
				await save_capture(label)
		if scene.arrived or not scene.trial.incident.is_empty():
			break
	check(right_exit and left_exit, "Car actually leaves asphalt on both sides")
	check(shoulder_wheel_hits > 20, "Wheels physically supported by shoulder mesh")
	check(
		scene.arrived and scene.trial.valid,
		"Returns to asphalt and stops through ordinary controls"
	)
	check(minimum_up > .85 and unsupported == 0, "No fall or overturn during both recoveries")
	check(
		frozen == 0 and before_relocations == scene.relocations and before_resets == scene.resets,
		"No relocation, freeze or reset during driving"
	)
	check(scene.stream_errors.is_empty(), "All streamed surface files verified")
	var drive_elapsed := car.elapsed - start_time
	car.freeze = true
	scene.toggle_original()
	scene.refresh_stream()
	while not scene.pending.is_empty():
		scene.load_next()
	await physics_frame
	await physics_frame
	check(
		scene.shoulder_residents.is_empty() and scene.road_residents.is_empty(),
		"Comparison removes all derived road/shoulder colliders"
	)
	scene.toggle_original()
	scene.refresh_stream()
	while not scene.pending.is_empty():
		scene.load_next()
	await physics_frame
	await physics_frame
	check(not scene.shoulder_residents.is_empty(), "Comparison restores shoulder colliders")
	var report := {
		"drive_start_wall_msec": startup_msec,
		"final_vehicle": final_vehicle,
		"passed": failures.is_empty(),
		"checks": checks,
		"failures": failures,
		"engine": Engine.get_version_info().string,
		"renderer": RenderingServer.get_video_adapter_name(),
		"physics_hz": hz,
		"shoulder_rays": shoulder_rays,
		"road_rays": road_rays,
		"geometry_scan_skipped_for_visible_drive": capture,
		"max_ray_error_m": max_error,
		"elapsed_drive_s": drive_elapsed,
		"min_up": minimum_up,
		"unsupported_frames": unsupported,
		"min_signed_offset_m": min_signed,
		"max_signed_offset_m": max_signed,
		"shoulder_wheel_hits": shoulder_wheel_hits,
		"returned_and_stopped": scene.arrived,
		"resets_during_drive": scene.resets - before_resets,
		"relocations_during_drive": scene.relocations - before_relocations,
		"frozen_or_reset_frames": frozen,
		"max_residents": scene.max_residents,
		"full_lap_driven": false,
		"real_roadside_verified": false,
		"fixture": fixture.source_station_range_m
	}
	DirAccess.make_dir_recursive_absolute(output)
	var file := FileAccess.open(output.path_join("report.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	print(JSON.stringify(report))
	if capture:
		await save_capture("returned")
	scene.queue_free()
	await process_frame
	await physics_frame
	quit(0 if failures.is_empty() else 1)


func save_capture(label: String) -> void:
	DirAccess.make_dir_recursive_absolute(output)
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(output.path_join(label + ".png"))


func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)
