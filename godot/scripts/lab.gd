extends Node3D
## Synthetic test ground, explicitly unrelated to the real Faedis–Valle road.

enum CameraMode { VEHICLE, FULL_RIG, CABIN }

const CAMERA_LABELS := ["Auto", "Albero e coffa", "Abitacolo"]

var vehicle: LaboratoryVehicle
var camera: Camera3D
var hud: Label
var camera_mode := CameraMode.VEHICLE
var camera_snap := true
var doors_open := false
var hatch_open := false


func _ready() -> void:
	_setup_inputs()
	var environment := WorldEnvironment.new()
	var settings := Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color("a6d0dd")
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color("fff0d3")
	settings.ambient_light_energy = 0.6
	environment.environment = settings
	add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -25, 0)
	sun.light_color = Color("fff0d0")
	sun.light_energy = 1.2
	sun.shadow_enabled = true
	add_child(sun)
	_ground(Vector3(180, 0.4, 180), Vector3(0, -0.2, 0), Color("8dae76"))
	_ground(Vector3(12, 0.04, 140), Vector3(0, 0.01, 0), Color("606b6a"))
	# Constant-radius visual reference: no artificial cornering or invisible rails.
	for i in range(64):
		var angle := TAU * float(i) / 64.0
		var marker := MeshInstance3D.new()
		var box := BoxMesh.new()
		box.size = Vector3(0.16, 0.015, 0.65)
		marker.mesh = box
		marker.position = Vector3(32 + 20 * cos(angle), 0.025, 20 * sin(angle))
		marker.rotation.y = -angle
		add_child(marker)
	var ramp := _ground(Vector3(6, 0.3, 12), Vector3(-15, 1.0, -18), Color("bfab7c"))
	ramp.rotation.x = deg_to_rad(-8.0)
	vehicle = LaboratoryVehicle.new()
	vehicle.position = Vector3(0, 0.2, 8)
	add_child(vehicle)
	camera = Camera3D.new()
	camera.fov = 62
	camera.position = Vector3(10, 8, 21)
	add_child(camera)
	camera.current = true
	var canvas := CanvasLayer.new()
	add_child(canvas)
	hud = Label.new()
	hud.position = Vector2(20, 16)
	hud.add_theme_color_override("font_color", Color("ffffff"))
	hud.add_theme_color_override("font_shadow_color", Color("243b3f"))
	hud.add_theme_constant_override("shadow_offset_x", 2)
	hud.add_theme_constant_override("shadow_offset_y", 2)
	canvas.add_child(hud)


func _physics_process(_delta: float) -> void:
	vehicle.throttle = (
		Input.get_action_strength("accelerate") - Input.get_action_strength("reverse")
	)
	vehicle.braking = Input.get_action_strength("brake")
	vehicle.steering_target = Input.get_axis("left", "right")
	if Input.is_action_just_pressed("reset_lab"):
		vehicle.reset_requested = true


func _process(delta: float) -> void:
	if not is_instance_valid(vehicle):
		return
	_update_camera(delta)
	var loads := vehicle.wheel_loads
	hud.text = (
		(
			"VIAGGIO A SOFFUMBERGO — LABORATORIO · YARIS 0.1\n"
			+ "Frecce/WASD: guida · Spazio: freno · R: ripristino\n"
			+ "C: camera · O: portiere · H: portellone (apertura da fermo)\n"
			+ "Camera: %s · Velocità %.1f km/h · Contatti %d/4 · Passo %d Hz\n"
			+ "Carichi FL/FR/RL/RR: %.0f / %.0f / %.0f / %.0f N\n"
			+ "Modello da scolpire; albero, occupanti e masse provvisori.\n"
			+ "CSV: user://telemetry · Prova invalidata: %s"
		)
		% [
			CAMERA_LABELS[camera_mode],
			vehicle.linear_velocity.length() * 3.6,
			vehicle.diagnostic_contact_count,
			Engine.physics_ticks_per_second,
			loads[0],
			loads[1],
			loads[2],
			loads[3],
			str(vehicle.invalidated)
		]
	)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("cycle_camera"):
		camera_mode = (camera_mode + 1) % CameraMode.size()
		camera_snap = true
	elif event.is_action_pressed("toggle_lab_doors"):
		if doors_open or vehicle.linear_velocity.length() < 0.2:
			doors_open = not doors_open
			for wheel_id in YarisVisual.WHEEL_IDS:
				vehicle.yaris_visual.set_door_open(wheel_id, 1.0 if doors_open else 0.0)
	elif event.is_action_pressed("toggle_lab_hatch"):
		if hatch_open or vehicle.linear_velocity.length() < 0.2:
			hatch_open = not hatch_open
			vehicle.yaris_visual.set_hatch_open(1.0 if hatch_open else 0.0)


func _update_camera(delta: float) -> void:
	if camera_mode == CameraMode.CABIN:
		var eye := vehicle.yaris_visual.find_child("DriverEye", true, false) as Node3D
		camera.global_position = eye.global_position
		camera.fov = 80
		camera.look_at(
			eye.global_position - vehicle.global_basis.z * 2.0 - vehicle.global_basis.y * 0.17,
			vehicle.global_basis.y
		)
		camera_snap = false
		return
	var heading := -vehicle.global_basis.z
	heading.y = 0
	if heading.length_squared() < 0.01:
		heading = Vector3.FORWARD
	heading = heading.normalized()
	var right := heading.cross(Vector3.UP)
	var wide := camera_mode == CameraMode.FULL_RIG
	var desired := (
		vehicle.global_position
		- heading * (12.0 if wide else 6.5)
		+ right * (5.0 if wide else 3.0)
		+ Vector3.UP * (7.0 if wide else 2.7)
	)
	camera.fov = 62 if wide else 52
	if camera_snap:
		camera.global_position = desired
	else:
		camera.global_position = camera.global_position.lerp(desired, 1.0 - exp(-3.0 * delta))
	camera.look_at(vehicle.global_position + Vector3.UP * (2.8 if wide else 0.8), Vector3.UP)
	camera_snap = false


func _ground(size: Vector3, at: Vector3, color: Color) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = at
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collision.shape = shape
	body.add_child(collision)
	var visual := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	visual.mesh = box
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 1
	visual.material_override = material
	body.add_child(visual)
	add_child(body)
	return body


func _setup_inputs() -> void:
	var bindings := {
		"accelerate": [KEY_W, KEY_UP],
		"reverse": [KEY_S, KEY_DOWN],
		"left": [KEY_A, KEY_LEFT],
		"right": [KEY_D, KEY_RIGHT],
		"brake": [KEY_SPACE],
		"reset_lab": [KEY_R],
		"cycle_camera": [KEY_C],
		"toggle_lab_doors": [KEY_O],
		"toggle_lab_hatch": [KEY_H]
	}
	for action in bindings:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in bindings[action]:
			var event := InputEventKey.new()
			event.physical_keycode = key
			InputMap.action_add_event(action, event)
