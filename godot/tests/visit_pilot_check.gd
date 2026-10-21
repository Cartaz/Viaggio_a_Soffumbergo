extends "res://godot/tests/parking_pilot_check.gd"

const VisitScene = preload("res://godot/scenes/visit_pilot.tscn")


func _initialize() -> void:
	if "--hz=60" in OS.get_cmdline_user_args():
		Engine.physics_ticks_per_second = 60
	super._initialize()
	scene_resource = VisitScene
	output_dir = "build/visit_validation"
	if "--hz=60" in OS.get_cmdline_user_args():
		output_dir = output_dir.path_join("60")


func _expected_visit_hint() -> String:
	return "F: scendi"


func _after_drive(scene: Node3D) -> void:
	await super._after_drive(scene)
	var car: LaboratoryVehicle = scene.vehicle
	var original_mass := car.mass
	var occupant_mass := 0.0
	for part in car.config.components:
		if part.id in ["driver", "passenger"]:
			occupant_mass += float(part.mass_kg)
	var original_children := car.get_child_count()
	car.braking = 0
	check(not scene.begin_dismount(), "Dismount requires the brake even at rest")
	car.braking = 1
	check(scene.begin_dismount(), "Stable confirmed stop permits dismount")
	check(
		scene.visitors.size() == 2 and absf(car.mass - original_mass + occupant_mass) < 0.001,
		"Each occupant becomes a separate mass exactly once"
	)
	check(scene.split_momentum_error < 0.001, "Splitting preserves linear momentum")
	check(not scene.toggle_stop(), "Cannot resume driving with occupants outside")
	check(not scene.begin_dismount(), "Duplicate dismount rejected")
	scene.guide_speed_m_s = 0
	await ticks(2)
	check(scene.visit_phase == "descending", "A blocked guide cannot finish by elapsed time")
	var supported_sum := 0.0
	for i in range(simulation_hz / 2):
		await physics_frame
		for force in car.wheel_loads:
			supported_sum += force
	var suspended_support := supported_sum / (simulation_hz / 2)
	check(
		absf(suspended_support / (original_mass * 9.81) - 1) < 0.03,
		"Wheel loads retain suspended occupants after ownership split"
	)
	scene.guide_speed_m_s = 0.4
	await wait_phase(scene, "walking", 75)
	check(
		scene.visit_phase == "walking", "Descent finishes from actual arrivals and ground contacts"
	)
	if scene.visit_phase != "walking":
		print(
			"VISIT DEBUG ",
			scene.visit_phase,
			" paths ",
			scene.path_indices,
			" positions ",
			scene.visitors[0].position,
			" ",
			scene.visitors[1].position,
			" message ",
			scene.trial.incident
		)
		return
	for actor in scene.visitors:
		check(actor.grounded(), "Visitor supported on the real collision surface")
	await ticks(2)
	await capture_phase(scene, "walking", 0)
	var unloaded_support := 0.0
	for force in car.wheel_loads:
		unloaded_support += force
	check(
		absf(unloaded_support / (car.mass * 9.81) - 1) < 0.03,
		"Wheel loads unload only after both bodies stand on the ground"
	)
	check(scene.maximum_mass_error < 0.001, "Total dynamic mass remains constant")
	check(scene.max_force_pair_error < 0.001, "Guide support reaction is applied to the vehicle")
	var start: Vector3 = scene.visitors[0].position
	var target: Vector3 = car.global_transform * Vector3(-2.5, 0, 2.5)
	for i in range(simulation_hz * 20):
		scene.walk_intent = (target - scene.visitors[0].position).slide(Vector3.UP).limit_length(
			0.8
		)
		await physics_frame
		if scene.visited_trial:
			break
	scene.walk_intent = Vector3.ZERO
	await ticks(2)
	check(
		scene.visitors[0].position.distance_to(start) > 1,
		"Leader walks by ground forces without teleportation"
	)
	check(scene.visited_trial, "Companion follows the recorded route to the local test marker")
	var max_limb_error := 0.0
	var max_hand_error := 0.0
	var rung_frames := 0
	for actor in scene.visitors:
		max_limb_error = maxf(max_limb_error, actor.max_limb_length_error_m)
		max_hand_error = maxf(max_hand_error, actor.max_rung_hand_error_m)
		rung_frames += actor.rung_pose_frames
	check(max_limb_error < 0.001, "Imported rigs keep fixed limb lengths")
	await capture_phase(scene, "companion", 1)
	check(scene.request_board(), "Both nearby visitors can request return")
	check(not scene.toggle_stop(), "Driving remains blocked while gathering and climbing")
	await wait_phase(scene, "aboard", 100)
	check(scene.visit_phase == "aboard", "Both reach their travel poses before drive unlock")
	if scene.visit_phase != "aboard":
		print(
			"VISIT DEBUG ",
			scene.visit_phase,
			" paths ",
			scene.path_indices,
			" positions ",
			scene.visitors[0].position,
			" ",
			scene.visitors[1].position,
			" message ",
			scene.trial.incident
		)
		return
	check(
		scene.visitors.is_empty() and absf(car.mass - original_mass) < 0.001,
		"Boarding restores aggregate once and removes independent masses"
	)
	await ticks(0.1)
	check(
		scene.find_children("*", "RigidBody3D", true, false).size() == 1,
		"Boarding leaves no hidden rigid occupant bodies"
	)
	check(car.get_child_count() == original_children, "Temporary guide geometry is released")
	check(scene.toggle_stop(), "Driving can resume only after both board")
	car.braking = 1
	await ticks(2)
	check(scene.toggle_stop(), "New stable stop permits another cycle")
	check(scene.begin_dismount(), "Second dismount supported")
	await ticks(2)
	await scene.reset_trial("Mid-transition recovery test")
	check(
		scene.visitors.is_empty() and absf(car.mass - original_mass) < 0.001,
		"Recovery during descent leaves exactly one mass owner"
	)
	check(not scene.trial.valid, "Emergency recovery invalidates attempt")
	print(
		"VISIT_METRICS ",
		JSON.stringify(
			{
				"split_momentum_error_ns": scene.split_momentum_error,
				"suspended_wheel_support_n": suspended_support,
				"grounded_wheel_support_n": unloaded_support,
				"max_imported_limb_length_error_m": max_limb_error,
				"max_rung_hand_error_m": max_hand_error,
				"rung_pose_samples": rung_frames,
				"max_mass_error_kg": scene.maximum_mass_error,
				"max_force_pair_error_n": scene.max_force_pair_error
			}
		)
	)


func wait_phase(scene: Node3D, wanted: String, seconds: int) -> void:
	var captured := false
	for i in range(simulation_hz * seconds):
		await physics_frame
		if (
			capture
			and not captured
			and scene.visit_phase == "descending"
			and i > simulation_hz * 10
		):
			await capture_phase(scene, "descent", 1)
			captured = true
		if scene.visit_phase == wanted or not scene.trial.incident.is_empty():
			return


func capture_phase(scene: Node3D, label: String, actor: int) -> void:
	if not capture:
		return
	DirAccess.make_dir_recursive_absolute(output_dir)
	scene.observed_actor = actor
	await ticks(0.5)
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(output_dir.path_join(label + ".png"))
