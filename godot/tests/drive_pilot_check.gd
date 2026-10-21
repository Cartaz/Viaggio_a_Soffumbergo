extends SceneTree
## Automatic driver applies ordinary throttle/brake/steering, without moving the body.

const Scene = preload("res://godot/scenes/drive_pilot.tscn")
var failures: Array[String] = []
var checks := 0
var capture := false
var simulation_hz := 120
var physics_only := false


func _initialize() -> void:
	simulation_hz = Engine.physics_ticks_per_second
	capture = "--capture" in OS.get_cmdline_user_args()
	physics_only = "--physics-only" in OS.get_cmdline_user_args()
	if capture or "--fast-physics" in OS.get_cmdline_user_args():
		Engine.physics_ticks_per_second = simulation_hz * 8
		Engine.time_scale = 8
		Engine.max_physics_steps_per_frame = 32
	call_deferred("run")


func run() -> void:
	var scene := Scene.instantiate()
	scene.automated = true
	root.add_child(scene)
	await physics_frame
	await physics_frame
	var car: LaboratoryVehicle = scene.vehicle
	check(is_instance_valid(car), "Car instantiated with trial road")
	if not is_instance_valid(car):
		quit(1)
		return
	car.braking = 1
	if physics_only:
		car.set_process(false)
		car.set_physics_process(false)
	await ticks(2)
	var max_ray_error := 0.0
	for p: Vector3 in scene.points:
		var query := PhysicsRayQueryParameters3D.create(p + Vector3.UP * 4, p - Vector3.UP * 6, 4)
		query.exclude = [car.get_rid()]
		var hit: Dictionary = scene.get_world_3d().direct_space_state.intersect_ray(query)
		check(not hit.is_empty(), "Continuous surface at every trial station")
		if not hit.is_empty():
			max_ray_error = maxf(max_ray_error, absf(hit.position.y - p.y))
		query.collision_mask = 1
		var terrain_hit: Dictionary = scene.get_world_3d().direct_space_state.intersect_ray(query)
		if not terrain_hit.is_empty():
			check(terrain_hit.position.y < p.y - 0.02, "Resident trial grading clears road surface")
	check(max_ray_error < 0.02, "Road collision height matches engineering mesh")
	var max_lateral := 0.0
	var max_speed := 0.0
	var min_up := 1.0
	var unsupported_frames := 0
	var telemetry: Array = []
	var start_clock := car.elapsed
	var elapsed := 0.0
	for i in range(simulation_hz * 260):
		var target: Vector3 = scene.target_at(scene.progress_m + 5)
		var relative: Vector3 = car.global_basis.inverse() * (target - car.position)
		var angle := atan2(relative.x, -relative.z)
		car.steering_target = clampf(atan(2 * 2.56 * sin(angle) / 5.0) / 0.52, -1, 1)
		var remaining: float = scene.station[-1] - scene.progress_m
		var wanted := 4.0 if remaining > 15 else 1.8 if remaining > 5 else 0.0
		var speed := car.road_speed_m_s()
		car.throttle = clampf((wanted - speed) * 0.4 + 0.12, 0, 0.6) if wanted > 0 else 0
		car.braking = clampf((speed - wanted) * 0.4, 0, 0.5) if wanted > 0 else 0.6
		await physics_frame
		elapsed += 1.0 / simulation_hz
		max_lateral = maxf(max_lateral, scene.lateral_error_m)
		max_speed = maxf(max_speed, speed * 3.6)
		min_up = minf(min_up, car.global_basis.y.dot(Vector3.UP))
		if car.diagnostic_contact_count == 0:
			unsupported_frames += 1
		if i % 120 == 0:
			var point: Vector3 = scene.target_at(scene.progress_m)
			var query := PhysicsRayQueryParameters3D.create(
				point + Vector3.UP * 4, point - Vector3.UP * 6, 1
			)
			query.exclude = [car.get_rid()]
			var hit: Dictionary = scene.get_world_3d().direct_space_state.intersect_ray(query)
			check(
				not hit.is_empty() and hit.position.y < point.y - 0.02,
				"Streamed terrain clears driven surface"
			)
			telemetry.append(
				[
					elapsed,
					scene.progress_m,
					speed * 3.6,
					scene.lateral_error_m,
					car.diagnostic_contact_count
				]
			)
		if scene.arrived or scene.trial_resets > 0:
			break
	check(
		absf(car.elapsed - start_clock - elapsed) < 0.03,
		"Actual integrator clock matches drive time"
	)
	check(scene.arrived, "Reached arrival and stopped through ordinary controls")
	check(scene.trial.valid, "Continuous physical drive remains eligible")
	check(scene.trial.next_gate == 5, "All five directional gates crossed in order")
	car.throttle = 0
	car.braking = 0.6
	await ticks(2)
	check(car.road_speed_m_s() < 0.05, "Brake holds the loaded car stopped on the trial grade")
	check(scene.trial_resets == 0, "No recovery or teleport during driven trial")
	check(max_lateral < 1.3, "Car remains within provisional surface")
	check(min_up > 0.85, "Loaded car remains upright on this slow route")
	check(unsupported_frames == 0, "At least one wheel supported throughout drive")
	check(scene.chunks_loaded > scene.residents.size(), "Terrain loaded while driving")
	check(scene.chunks_unloaded > 0, "Distant terrain released while driving")
	check(scene.stream_errors.is_empty(), "No missing or changed terrain chunks")
	DirAccess.make_dir_recursive_absolute("build/drive_validation")
	if capture:
		if physics_only:
			car.set_process(true)
			car.set_physics_process(true)
			await ticks(1)
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("build/drive_validation/arrival.png")
	var report := {
		"checks": checks,
		"failures": failures,
		"engine": Engine.get_version_info().string,
		"progress_m": scene.progress_m,
		"trial_length_m": scene.station[-1],
		"elapsed_s": elapsed,
		"max_lateral_error_m": max_lateral,
		"max_speed_kmh": max_speed,
		"min_up_dot": min_up,
		"unsupported_frames": unsupported_frames,
		"trial_resets": scene.trial_resets,
		"directional_checkpoints": scene.trial.next_gate,
		"valid_arrival": scene.trial.valid and scene.arrived,
		"surface_ray_max_error_m": max_ray_error,
		"chunks_loaded": scene.chunks_loaded,
		"chunks_unloaded": scene.chunks_unloaded,
		"max_residents": scene.max_residents,
		"capture": capture,
		"visual_animation_disabled_during_drive": physics_only,
		"scope": "Declared 601m engineering trial; no verified real road or full journey"
	}
	await scene.reset_trial("Recovery acceptance test")
	check(not scene.trial.valid, "Explicit recovery invalidates attempt")
	check(scene.trial.next_gate == 5, "Recovery retains accepted checkpoints")
	check(absf(scene.progress_m - 593) < 1, "Recovery uses last accepted checkpoint")
	check(not car.freeze and not scene.recovering, "Recovery releases car after streaming")
	await ticks(1)
	check(car.diagnostic_contact_count > 0, "Recovered car supported by resident collision")
	await scene.reset_trial("New attempt acceptance test", true)
	check(scene.trial.valid and scene.trial.next_gate == 0, "New attempt clears old gates")
	check(not scene.arrived and scene.progress_m < 6, "New attempt returns to initial pose")
	await ticks(1)
	check(car.diagnostic_contact_count > 0, "New start supported by resident collision")
	# Exercise observed incident handling; this intentional discontinuity is not a drive.
	car.reset_transform = Transform3D(car.basis, car.position + Vector3(30, 0, 0))
	car.reset_requested = true
	await ticks(0.2)
	check(
		not scene.trial.valid and not scene.trial.incident.is_empty(), "Off-road incident latched"
	)
	check(not scene.arrived and car.throttle == 0, "Incident blocks arrival and engine input")
	await scene.reset_trial("Incident recovery acceptance test")
	check(
		not scene.trial.valid and scene.trial.incident.is_empty(),
		"Incident recovery stays practice"
	)
	report["checks"] = checks
	report["recovery_and_incident_checks"] = 11
	var file := FileAccess.open("build/drive_validation/report.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "  ") + "\n")
	file.close()
	file = FileAccess.open("build/drive_validation/telemetry.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(telemetry) + "\n")
	file.close()
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
