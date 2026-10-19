extends SceneTree
## Exercise the main laboratory, its input route and the real physics/visual scene.

const LabScene = preload("res://godot/scenes/lab.tscn")
var failures := 0
var checks := 0
var captures: Array[String] = []
var capture_dir := ""


func _initialize() -> void:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--capture-dir="):
			capture_dir = argument.trim_prefix("--capture-dir=")
	call_deferred("run_check")


func run_check() -> void:
	var lab := LabScene.instantiate()
	root.add_child(lab)
	var vehicle: LaboratoryVehicle = lab.get("vehicle")
	var camera: Camera3D = lab.get("camera")
	var visual := vehicle.yaris_visual
	Input.action_press("brake")
	await ticks(300)
	check(vehicle.diagnostic_contact_count == 4, "Four ground contacts after settling")
	check(root.find_children("*", "RigidBody3D", true, false).size() == 1, "One mass owner")
	check(absf(vehicle.mass - 1605.0) < 0.001, "Visual does not add mass")
	check(visual.find_children("*", "MeshInstance3D", true, false).size() > 50, "Real Yaris meshes")
	await capture("lab_auto")
	await tap_key(KEY_C)
	check(int(lab.get("camera_mode")) == 1, "Full rig camera input")
	await capture("lab_albero_coffa")
	await tap_key(KEY_C)
	var eye := visual.find_child("DriverEye", true, false) as Node3D
	check(camera.global_position.distance_to(eye.global_position) < 0.001, "Cabin camera socket")
	await capture("lab_abitacolo")
	await tap_key(KEY_C)
	check(int(lab.get("camera_mode")) == 0, "Return to vehicle camera")
	await tap_key(KEY_O)
	await tap_key(KEY_H)
	var door := visual.find_child("Door_FL", true, false) as Node3D
	var hatch := visual.find_child("Hatch", true, false) as Node3D
	check(door.rotation.y < -0.5 and hatch.rotation.x < -0.5, "Panel controls while stopped")
	await capture("lab_portiere")
	await tap_key(KEY_O)
	await tap_key(KEY_H)
	check(absf(door.rotation.y) < 0.001 and absf(hatch.rotation.x) < 0.001, "Panels close")
	Input.action_release("brake")
	var start := vehicle.global_position
	Input.action_press("accelerate")
	await ticks(120)
	var forward_speed := vehicle.linear_velocity.dot(-vehicle.global_basis.z)
	var forward_distance := (vehicle.global_position - start).dot(Vector3.FORWARD)
	check(forward_speed > 1.0 and forward_distance > 0.2, "Throttle moves the loaded car forward")
	var spin_before := visual.spin_nodes[0].rotation.x
	await ticks(4)
	var spin_delta := wrapf(visual.spin_nodes[0].rotation.x - spin_before, -PI, PI)
	var bottom_tread_displacement := Vector3(spin_delta, 0, 0).cross(Vector3(0, -0.31045, 0))
	check(bottom_tread_displacement.z > 0.0001, "Bottom tread moves backward during forward travel")
	await tap_key(KEY_O)
	check(not bool(lab.get("doors_open")), "Door opening blocked while moving")
	Input.action_press("right")
	await ticks(48)
	check(vehicle.steering > 0.1, "Steering input reaches the vehicle")
	check(visual.steer_nodes[0].rotation.y < -0.1, "Front wheel follows steering")
	check(absf(visual.steer_nodes[2].rotation.y) < 0.001, "Rear wheel does not steer")
	var visual_center := visual.steer_nodes[0].position
	var physics_center := vehicle.wheel_anchors[0] - Vector3.UP * vehicle.wheel_lengths[0]
	check(visual_center.distance_to(physics_center) < 0.02, "Wheel follows suspension travel")
	var yaw_speed := vehicle.angular_velocity.y
	check(yaw_speed < -0.001, "Right steering produces a right turn through forces")
	Input.action_release("accelerate")
	Input.action_release("right")
	var speed_before_braking := vehicle.linear_velocity.length()
	Input.action_press("brake")
	await ticks(300)
	var speed_after_braking := vehicle.linear_velocity.length()
	check(speed_after_braking < 0.2, "Brake stops the vehicle")
	await tap_key(KEY_R)
	await ticks(90)
	check(vehicle.invalidated, "Reset invalidates the run")
	check(
		vehicle.global_position.distance_to(Vector3(0, 0, 8)) < 0.5, "Reset returns to test start"
	)
	Input.action_release("brake")
	var report := {
		"engine": Engine.get_version_info().string,
		"display_driver": DisplayServer.get_name(),
		"checks": checks,
		"failures": failures,
		"forward_speed_m_s": forward_speed,
		"forward_distance_m": forward_distance,
		"right_turn_yaw_rad_s": yaw_speed,
		"speed_before_braking_m_s": speed_before_braking,
		"speed_after_braking_m_s": speed_after_braking,
		"rolling_delta_rad": spin_delta,
		"captures": captures
	}
	if not capture_dir.is_empty():
		DirAccess.make_dir_recursive_absolute(capture_dir)
		var file := FileAccess.open(capture_dir.path_join("lab_integration.json"), FileAccess.WRITE)
		file.store_string(JSON.stringify(report, "  ") + "\n")
	print("LAB_YARIS_CHECK ", JSON.stringify(report))
	lab.queue_free()
	quit(0 if failures == 0 else 1)


func tap_key(code: Key) -> void:
	for pressed in [true, false]:
		var event := InputEventKey.new()
		event.keycode = code
		event.physical_keycode = code
		event.pressed = pressed
		Input.parse_input_event(event)
		await process_frame
		await process_frame


func ticks(count: int) -> void:
	for i in range(count):
		await physics_frame
	await process_frame


func capture(label: String) -> void:
	if capture_dir.is_empty() or DisplayServer.get_name() == "headless":
		return
	DirAccess.make_dir_recursive_absolute(capture_dir)
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	check(not image.is_empty(), "Rendered viewport " + label)
	var path := capture_dir.path_join(label + ".png")
	check(image.save_png(path) == OK, "Capture " + label)
	captures.append(label + ".png")


func check(condition: bool, label: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error(label)
