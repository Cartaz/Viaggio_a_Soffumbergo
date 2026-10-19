extends SceneTree
## Render the real laboratory, including its car, supports, skins and live cloth.

var movie_lab: Node3D
var movie_frame := 0
var reaction_review := false


func _initialize() -> void:
	call_deferred("capture_run")


func capture_run() -> void:
	DisplayServer.window_set_position(Vector2i(-2500, 40))
	root.size = Vector2i(960, 640)
	root.content_scale_size = Vector2i(960, 640)
	var lab: Node3D = (load("res://godot/scenes/lab.tscn") as PackedScene).instantiate()
	root.add_child(lab)
	lab.set_process(false)
	lab.set_physics_process(false)
	lab.hud.visible = false
	if lab.get("exercise") != null:
		lab.exercise.set_physics_process(false)
	for node in lab.get_children():
		if node is CanvasLayer:
			node.visible = false
	var vehicle: LaboratoryVehicle = lab.vehicle
	var movie := "--movie" in OS.get_cmdline_user_args()
	reaction_review = "--reaction-review" in OS.get_cmdline_user_args()
	if movie:
		movie_lab = lab
		process_frame.connect(follow_movie)
	DirAccess.make_dir_recursive_absolute("res://art/source/generated/ingame")
	var end := 1921 if reaction_review else (961 if movie else 721)
	for frame in range(1, end):
		await physics_frame
		movie_frame = frame
		var t := float(frame) / 120.0
		vehicle.throttle = 0.45 if t > 1.0 and t < 4.6 else 0.0
		vehicle.braking = 0.4 if t >= 4.8 else 0.0
		vehicle.steering_target = 0.18 if t > 2.0 and t < 4.0 else -0.12
		if t > 2.7 and t < 3.3:
			if not reaction_review:
				vehicle.apply_force(vehicle.global_basis.x * 900.0, vehicle.global_basis.y * 5.7)
		if reaction_review:
			var cycle := fmod(t, 8.0)
			vehicle.throttle = 0.55 if cycle > 1.0 and cycle < 6.0 else 0.0
			vehicle.braking = 0.65 if cycle >= 6.0 else 0.0
			vehicle.steering_target = 0.35 if cycle > 2.0 and cycle < 4.0 else -0.35
			if cycle < 2.0 or cycle >= 6.0:
				vehicle.steering_target = 0.0
			if frame == 960:
				vehicle.reset_requested = true
		if movie:
			continue
		if frame == 240:
			await shot(lab, 1, "driver_acceleration")
		elif frame == 360:
			await shot(lab, 2, "lookout_cornering")
		elif frame == 600:
			await shot(lab, 1, "driver_braking")
		elif frame == 720:
			await shot(lab, 2, "lookout_braking")
			await shot(lab, 0, "vehicle_overview")
	print("IN_GAME_CAPTURES_DONE")
	quit()


func follow_movie() -> void:
	if reaction_review:
		frame_camera(movie_lab, 1 if movie_frame < 960 else 2)
		return
	var view := 0
	if movie_frame >= 150:
		view = 1
	if movie_frame >= 360:
		view = 2
	if movie_frame >= 720 and movie_frame < 840:
		view = 1
	frame_camera(movie_lab, view)


func shot(lab: Node3D, view: int, key: String) -> void:
	frame_camera(lab, view)
	await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	if image.is_empty():
		push_error("Renderer returned an empty in-game image")
		quit(1)
		return
	image.save_png("res://art/source/generated/ingame/" + key + ".png")
	print("CAPTURED ", key)


func frame_camera(lab: Node3D, view: int) -> void:
	var vehicle: LaboratoryVehicle = lab.vehicle
	var camera: Camera3D = lab.camera
	var focus := vehicle.global_position + Vector3(0, 2.8, 0)
	var offset := Vector3(8, 6, 12)
	camera.fov = 48
	if view == 1:
		focus = vehicle.driver.global_position + vehicle.global_basis * Vector3(0, 0.37, 0)
		offset = vehicle.global_basis * Vector3(-0.58, 0.20, -0.46)
	elif view == 2:
		focus = vehicle.lookout.global_position + vehicle.global_basis * Vector3(0, 0.42, 0)
		offset = vehicle.global_basis * Vector3(0.95, 0.30, -1.0)
	camera.global_position = focus + offset
	camera.look_at(focus, Vector3.UP)
	camera.reset_physics_interpolation()
