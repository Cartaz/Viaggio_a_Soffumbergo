extends SceneTree
## Ordinary controls only; separate maneuver fixtures or one uninterrupted lap.

const Scene = preload("res://godot/scenes/circuit_loop.tscn")
var simulation_hz := 120
var selected := 0
var full := false
var output := "build/loop_validation"
var failures: Array[String] = []
var checks := 0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--hz="):
			simulation_hz = int(arg.trim_prefix("--hz="))
		if arg.begins_with("--case="):
			selected = int(arg.trim_prefix("--case="))
		if arg.begins_with("--output="):
			output = arg.trim_prefix("--output=")
		full = full or arg == "--full"
	Engine.physics_ticks_per_second = simulation_hz * 8
	Engine.time_scale = 8
	Engine.max_physics_steps_per_frame = 32
	call_deferred("run")


func run() -> void:
	var scene := Scene.instantiate()
	scene.automated = true
	scene.maneuver_case = -1 if full else selected
	root.add_child(scene)
	for i in range(600):
		if scene.initialized and not scene.switching:
			break
		await process_frame
	check(scene.ready_ok and scene.initialized and not scene.switching, "Scene ready")
	if not failures.is_empty():
		quit(1)
		return
	var car: LaboratoryVehicle = scene.vehicle
	var final_vehicle := preload("res://godot/tests/final_vehicle_guard.gd").inspect(car)
	check(
		bool(final_vehicle.approved_assembly_loaded),
		"Approved Yaris, pirate rig, Bernie and Bianca required"
	)
	if not failures.is_empty():
		quit(1)
		return
	car.braking = 1
	for i in range(simulation_hz):
		await physics_frame
	var resets: int = scene.resets
	var relocations: int = scene.relocations
	var start_clock := car.elapsed
	var min_up := 1.0
	var max_lateral := 0.0
	var unsupported := 0
	var road_samples := 0
	var center_misses := 0
	var wheel_misses := 0
	var frozen := 0
	var requested_reset := 0
	var stalled := 0.0
	var crawl_clock := 0.0
	var crawl_start := 0.0
	var previous_progress: float = scene.route.progress
	var previous_phase: int = scene.section_index
	var telemetry: Array = []
	var misses_by_phase: Dictionary = {}
	var history: Array[Vector3] = []
	var reverse_index := 0
	var last_gear := 1
	var pedal_integral := 0.0
	var planned_route := preload("res://godot/scripts/practice_route.gd").new()
	var planned_phase := -1
	var length := 0.0
	for leg in scene.practice.sections:
		length += float(leg.length_horizontal_m)
	for frame in range(ceili(length / 0.6 + 240) * simulation_hz):
		var gear: int = scene.gear()
		if gear != last_gear:
			pedal_integral = 0
		var rear_axle := car.global_transform * Vector3(0, 0, 1.28)
		if gear > 0:
			if last_gear < 0:
				history.clear()
			if history.is_empty() or history[-1].distance_to(rear_axle) > 0.1:
				history.append(rear_axle)
		elif last_gear > 0:
			reverse_index = history.size() - 1
		last_gear = gear
		var speed := car.road_speed_m_s()
		var leg: Dictionary = scene.practice.sections[scene.section_index]
		var planned: bool = (
			leg.has("rear_points_m")
			and scene.route.progress < float(leg.planned_local_length_m) + 3
		)
		if planned and planned_phase != scene.section_index:
			planned_route.configure(scene.practice.sections[scene.section_index].rear_points_m)
			planned_phase = scene.section_index
		var lookahead := clampf(3 + speed * 0.35, 3, 5)
		# Bicycle geometry is referenced to the non-steered rear axle in both gears.
		var rear := car.global_transform * Vector3(0, 0, 1.28) if gear < 0 else car.position
		var target: Vector3 = scene.route.at(
			scene.route.progress + lookahead + (1.28 if gear < 0 else 0.0)
		)
		if gear < 0 and not history.is_empty():
			var nearest := INF
			for i in range(maxi(0, reverse_index - 50), mini(history.size(), reverse_index + 3)):
				var distance := rear_axle.distance_squared_to(history[i])
				if distance < nearest:
					nearest = distance
					reverse_index = i
			var index := reverse_index
			var distance := 0.0
			while index > 0 and distance < lookahead:
				distance += history[index].distance_to(history[index - 1])
				index -= 1
			target = history[index]
		var relative := car.basis.inverse() * (target - rear)
		if planned:
			lookahead = 1.5
			planned_route.sample(rear_axle, 3)
			target = planned_route.at(planned_route.progress + lookahead)
			relative = car.basis.inverse() * (target - rear_axle)
		var angle := atan2(relative.x * gear, -relative.z * gear)
		car.steering_target = clampf(gear * atan(2 * 2.56 * sin(angle) / lookahead) / 0.52, -1, 1)
		var remaining: float = scene.route.station[-1] - scene.route.progress
		var wanted := 4.0 if absf(angle) < 0.3 else 2.0 if absf(angle) < 0.6 else 1.0
		if gear < 0:
			var canal := selected == 3 if not full else str(leg.id) == "Retro 4"
			wanted = minf(wanted, 2.0 if canal else 1.0)
		if planned:
			wanted = minf(wanted, 0.8)
		if remaining < 8:
			wanted = minf(wanted, 0.8)
		if remaining < 2:
			wanted = minf(wanted, 0.3)
			if not planned:
				car.steering_target = 0
		if remaining < 0.4:
			wanted = 0
		car.throttle = gear * clampf((wanted - speed) * 0.4 + 0.12, 0, 0.75) if wanted > 0 else 0.0
		if wanted > 0 and (wanted <= 1 or gear < 0):
			pedal_integral = clampf(
				pedal_integral + (wanted - speed) * 0.15 / simulation_hz, 0, 0.85
			)
			car.throttle = gear * clampf((wanted - speed) * 0.4 + 0.12 + pedal_integral, 0, 1)
		elif wanted == 0:
			pedal_integral = 0
		car.braking = clampf((speed - wanted) * 0.4, 0, 0.6) if wanted > 0 else 0.6
		await physics_frame
		if absf(car.throttle) > 0.95 and speed < 0.1:
			if crawl_clock == 0:
				crawl_start = scene.route.progress
			crawl_clock += 1.0 / simulation_hz
		else:
			crawl_clock = 0
		min_up = minf(min_up, car.basis.y.dot(Vector3.UP))
		max_lateral = maxf(max_lateral, scene.route.lateral)
		unsupported += int(car.diagnostic_contact_count == 0)
		frozen += int(car.freeze)
		requested_reset += int(car.reset_requested)
		if frame % maxi(1, roundi(float(simulation_hz) / 10)) == 0:
			var points: Array[Vector3] = [car.position]
			for anchor: Vector3 in car.wheel_anchors:
				points.append(car.global_transform * anchor)
			for j in range(points.size()):
				var q := points[j]
				var hit := car.get_world_3d().direct_space_state.intersect_ray(
					PhysicsRayQueryParameters3D.create(q + Vector3.UP * 2, q - Vector3.UP * 4, 4)
				)
				road_samples += 1
				if hit.is_empty():
					var phase := str(scene.section_index)
					misses_by_phase[phase] = int(misses_by_phase.get(phase, 0)) + 1
					center_misses += int(j == 0)
					wheel_misses += int(j > 0)
		stalled = (
			stalled + 1.0 / simulation_hz
			if (
				scene.section_index == previous_phase
				and absf(scene.route.progress - previous_progress) < 0.0001
			)
			else 0.0
		)
		previous_progress = scene.route.progress
		previous_phase = scene.section_index
		if frame % (simulation_hz * 5) == 0:
			var sample := [
				car.elapsed - start_clock,
				scene.section_index,
				scene.route.progress,
				speed,
				scene.route.lateral,
				angle,
				car.diagnostic_contact_count
			]
			telemetry.append(sample)
			if frame % (simulation_hz * 30) == 0:
				print(JSON.stringify(sample))
		if (
			scene.arrived
			or not scene.trial.incident.is_empty()
			or stalled > 20
			or (crawl_clock > 15 and scene.route.progress - crawl_start < 0.5)
		):
			break
	check(scene.completed and scene.eligible, "All phases completed through ordinary controls")
	check(
		scene.transitions.size() == scene.practice.sections.size(),
		"Every phase ends at stable stop"
	)
	check(
		center_misses == 0 and wheel_misses == 0, "All center/wheel rays stay on constructed road"
	)
	check(min_up > 0.8 and unsupported == 0, "Supported upright throughout")
	check(
		(
			scene.resets == resets
			and scene.relocations == relocations
			and frozen == 0
			and requested_reset == 0
		),
		"No reset, relocation or freeze during measured interval"
	)
	check(scene.stream_errors.is_empty(), "No streaming errors")
	var report := {
		"final_vehicle": final_vehicle,
		"passed": failures.is_empty(),
		"checks": checks,
		"failures": failures,
		"full_lap_driven": full and scene.completed and failures.is_empty(),
		"journey_including_visit_complete": false,
		"real_maneuvers_verified": false,
		"case": -1 if full else selected,
		"reference_length_m": length,
		"phase": scene.section_index,
		"progress_m": scene.route.progress,
		"incident": scene.trial.incident,
		"elapsed_s": car.elapsed - start_clock,
		"physics_hz": simulation_hz,
		"engine": Engine.get_version_info().string,
		"renderer": RenderingServer.get_video_adapter_name(),
		"min_up": min_up,
		"max_lateral_m": max_lateral,
		"unsupported_frames": unsupported,
		"road_support_samples": road_samples,
		"center_off_road_samples": center_misses,
		"wheel_off_road_samples": wheel_misses,
		"resets_during_drive": scene.resets - resets,
		"relocations_during_drive": scene.relocations - relocations,
		"frozen_frames": frozen,
		"reset_requested_frames": requested_reset,
		"max_residents": scene.max_residents,
		"misses_by_phase": misses_by_phase,
		"transitions": scene.transitions.duplicate(true)
	}
	# These declared relocations occur only after the measured drive has ended.
	await scene.recover()
	check(
		not scene.eligible and not scene.completed and not car.freeze,
		"Recovery invalidates the whole lap and releases body"
	)
	await scene.recover(true)
	check(
		(
			scene.eligible
			and not scene.completed
			and scene.section_index == 0
			and scene.trial.next_gate == 0
		),
		"New attempt clears the whole lap and returns to its start"
	)
	var initial_relocations: int = scene.relocations
	await scene.select_section(1)
	check(
		scene.section_index == 0 and scene.relocations == initial_relocations,
		"Section keys cannot relocate during a lap"
	)
	report.passed = failures.is_empty()
	report.checks = checks
	DirAccess.make_dir_recursive_absolute(output)
	var file := FileAccess.open(output.path_join("report.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	file = FileAccess.open(output.path_join("telemetry.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(telemetry) + "\n")
	print(JSON.stringify(report))
	scene.queue_free()
	await process_frame
	await physics_frame
	quit(0 if failures.is_empty() else 1)


func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)
