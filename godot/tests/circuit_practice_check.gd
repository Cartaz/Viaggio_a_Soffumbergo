extends SceneTree
## Ordinary pedals/steering only during each measured drive; switches are separate.

const Scene = preload("res://godot/scenes/circuit_practice.tscn")
var checks := 0
var failures: Array[String] = []
var simulation_hz := 120
var tail := 0.0
var selected := 4
var all_sections := false
var capture := false
var physics_only := false
var spawn_only := false
var output := "build/practice_validation"
var reports: Array[Dictionary] = []


func _initialize() -> void:
	simulation_hz = Engine.physics_ticks_per_second
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--hz="):
			simulation_hz = int(arg.trim_prefix("--hz="))
		if arg.begins_with("--tail="):
			tail = float(arg.trim_prefix("--tail="))
		if arg.begins_with("--section="):
			selected = int(arg.trim_prefix("--section="))
		if arg.begins_with("--output="):
			output = arg.trim_prefix("--output=")
		all_sections = all_sections or arg == "--all-sections"
		capture = capture or arg == "--capture"
		physics_only = physics_only or arg == "--physics-only"
		spawn_only = spawn_only or arg == "--spawn-only"
	Engine.physics_ticks_per_second = simulation_hz * 8
	Engine.time_scale = 8
	Engine.max_physics_steps_per_frame = 32
	call_deferred("run")


func run() -> void:
	var scene := Scene.instantiate()
	scene.automated = true
	root.add_child(scene)
	for i in range(600):
		if not scene.switching:
			break
		await process_frame
	check(scene.ready_ok and not scene.switching, "Practice scene ready")
	if not scene.ready_ok or scene.switching:
		quit(1)
		return
	var car: LaboratoryVehicle = scene.vehicle
	var final_vehicle := preload("res://godot/tests/final_vehicle_guard.gd").inspect(car)
	check(
		bool(final_vehicle.approved_assembly_loaded),
		"Final Yaris, pirate rig, Bernie and Bianca required"
	)
	if not failures.is_empty() or physics_only:
		push_error("Run in the approved local project with all animation callbacks active")
		quit(1)
		return
	if physics_only:
		car.set_process(false)
		car.set_physics_process(false)
	check(
		scene.practice.sections.size() == 10,
		"Ten practice sections retain all four maneuver boundaries"
	)
	for index in range(scene.practice.sections.size()):
		if not all_sections and index != selected:
			continue
		var data: Dictionary = scene.practice.sections[index]
		var start := maxf(0, float(data.length_horizontal_m) - tail) if tail > 0 else 0.0
		await scene.select_section(index, start)
		car.throttle = 0
		car.braking = 1
		await ticks(0.7)
		check(car.diagnostic_contact_count > 0, "Resident road supports spawn " + str(data.id))
		check(not car.freeze and not scene.switching, "Spawn releases freeze " + str(data.id))
		if spawn_only:
			reports.append(
				{"section": data.id, "spawn_supported": car.diagnostic_contact_count > 0}
			)
			continue
		var max_lateral := 0.0
		var min_up := 1.0
		var max_speed := 0.0
		var unsupported := 0
		var road_samples := 0
		var center_off_road := 0
		var wheels_off_road := 0
		var start_clock := car.elapsed
		var before_resets: int = scene.resets
		var before_relocations: int = scene.relocations
		var stalled := 0.0
		var previous_progress: float = scene.route.progress
		var telemetry: Array = []
		var limit := ceili((float(data.length_horizontal_m) - start) / 0.8 + 120)
		for frame in range(limit * simulation_hz):
			var speed := car.road_speed_m_s()
			var lookahead := clampf(3 + speed * 0.35, 3, 5)
			var target: Vector3 = scene.route.at(scene.route.progress + lookahead)
			var relative := car.basis.inverse() * (target - car.position)
			var angle := atan2(relative.x, -relative.z)
			car.steering_target = clampf(atan(2 * 2.56 * sin(angle) / lookahead) / 0.52, -1, 1)
			var remaining: float = scene.route.station[-1] - scene.route.progress
			var wanted := 4.0 if absf(angle) < 0.3 else 2.0 if absf(angle) < 0.6 else 1.4
			if remaining < 14:
				wanted = minf(wanted, 1.5) if remaining > 5 else 0.0
			car.throttle = clampf((wanted - speed) * 0.4 + 0.12, 0, 0.75) if wanted > 0 else 0.0
			car.braking = clampf((speed - wanted) * 0.4, 0, 0.6) if wanted > 0 else 0.6
			await physics_frame
			max_lateral = maxf(max_lateral, scene.route.lateral)
			min_up = minf(min_up, car.basis.y.dot(Vector3.UP))
			max_speed = maxf(max_speed, speed * 3.6)
			if car.diagnostic_contact_count == 0:
				unsupported += 1
			if frame % maxi(1, roundi(float(simulation_hz) / 10)) == 0:
				var support_points: Array[Vector3] = [car.position]
				for anchor: Vector3 in car.wheel_anchors:
					support_points.append(car.global_transform * anchor)
				for j in range(support_points.size()):
					var q: Vector3 = support_points[j]
					var hit := car.get_world_3d().direct_space_state.intersect_ray(
						PhysicsRayQueryParameters3D.create(
							q + Vector3.UP * 2, q - Vector3.UP * 4, 4
						)
					)
					road_samples += 1
					if hit.is_empty():
						if j == 0:
							center_off_road += 1
						else:
							wheels_off_road += 1
			stalled = (
				stalled + 1.0 / simulation_hz
				if absf(scene.route.progress - previous_progress) < 0.0001
				else 0.0
			)
			previous_progress = scene.route.progress
			if frame % (simulation_hz * 5) == 0:
				telemetry.append(
					[
						car.elapsed - start_clock,
						scene.route.progress,
						speed * 3.6,
						scene.route.lateral,
						car.diagnostic_contact_count
					]
				)
			if scene.arrived or not scene.trial.incident.is_empty() or stalled > 20:
				break
		var result := {
			"section": data.id,
			"start_distance_m": start,
			"section_length_m": data.length_horizontal_m,
			"progress_m": scene.route.progress,
			"arrived": scene.arrived,
			"valid": scene.trial.valid,
			"incident": scene.trial.incident,
			"elapsed_s": car.elapsed - start_clock,
			"physics_hz": simulation_hz,
			"max_lateral_m": max_lateral,
			"min_up": min_up,
			"max_speed_kmh": max_speed,
			"unsupported_frames": unsupported,
			"road_support_samples": road_samples,
			"center_off_road_samples": center_off_road,
			"wheel_off_road_samples": wheels_off_road,
			"resets_during_drive": scene.resets - before_resets,
			"relocations_during_drive": scene.relocations - before_relocations,
			"gates": scene.trial.next_gate,
			"expected_gates": scene.trial.gates.size()
		}
		reports.append(result)
		print(JSON.stringify(result))
		check(
			scene.arrived and scene.trial.valid,
			"Reached section end through normal controls " + str(data.id)
		)
		check(
			scene.trial.next_gate == scene.trial.gates.size(),
			"Directional gates ordered " + str(data.id)
		)
		check(
			center_off_road == 0 and wheels_off_road == 0,
			"Center and four wheel projections remain over actual surface " + str(data.id)
		)
		check(
			min_up > 0.8 and unsupported == 0,
			"Loaded car stays upright and supported " + str(data.id)
		)
		check(
			scene.resets == before_resets and scene.relocations == before_relocations,
			"No reset or relocation during measured drive"
		)
		DirAccess.make_dir_recursive_absolute(output)
		var log_file := FileAccess.open(
			output.path_join("telemetry_" + str(data.id) + ".json"), FileAccess.WRITE
		)
		log_file.store_string(JSON.stringify(telemetry) + "\n")
		if capture:
			await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(
				output.path_join("arrival_" + str(data.id) + ".png")
			)
		if not failures.is_empty():
			break
	# Explicitly test reset ownership and eligibility after the drive metrics.
	if not spawn_only:
		await scene.recover()
		check(
			not scene.trial.valid and not car.freeze,
			"Recovery remains ineligible and releases body"
		)
		await ticks(0.5)
		check(car.diagnostic_contact_count > 0, "Recovery road preloaded before release")
		await scene.recover(true)
		check(
			scene.trial.valid and scene.trial.next_gate == 0,
			"New attempt clears checkpoint eligibility"
		)
		check(
			absf(scene.route.progress - (scene.attempt_start + 2)) < 1,
			"New attempt returns to this practice start"
		)
	check(scene.stream_errors.is_empty(), "No missing/changed terrain or road files")
	var report := {
		"final_vehicle": final_vehicle,
		"passed": failures.is_empty(),
		"checks": checks,
		"failures": failures,
		"sections": reports,
		"engine": Engine.get_version_info().string,
		"renderer": RenderingServer.get_video_adapter_name(),
		"physics_hz": simulation_hz,
		"visual_animation_disabled": physics_only,
		"max_residents": scene.max_residents,
		"chunks_loaded": scene.chunks_loaded,
		"chunks_unloaded": scene.chunks_unloaded,
		"full_lap_driven": false,
		"scope":
		"Separate practice drives; switching sections is an explicit relocation, not a continuous lap"
	}
	DirAccess.make_dir_recursive_absolute(output)
	var file := FileAccess.open(output.path_join("report.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	print(JSON.stringify(report))
	scene.queue_free()
	await process_frame
	await physics_frame
	quit(0 if failures.is_empty() else 1)


func ticks(seconds: float) -> void:
	for i in range(roundi(seconds * simulation_hz)):
		await physics_frame


func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)
