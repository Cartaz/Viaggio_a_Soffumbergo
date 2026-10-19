extends Node3D
## Offline inspection scene, intentionally independent from the physics laboratory.

var camera: Camera3D
var visual: YarisVisual
var azimuth := -0.64
var elevation := 0.27
var distance := 6.6
var interior := false
var doors_open := false
var hatch_open := false


func _ready() -> void:
	var model := load("res://godot/scenes/yaris_visual.tscn") as PackedScene
	visual = model.instantiate() as YarisVisual
	add_child(visual)
	var world := WorldEnvironment.new()
	var settings := Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color("22282e")
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color("dce3ed")
	settings.ambient_light_energy = 0.65
	world.environment = settings
	add_child(world)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-48, -25, 0)
	light.light_energy = 1.4
	light.shadow_enabled = true
	add_child(light)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, 145, 0)
	fill.light_energy = 0.65
	add_child(fill)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(200, 200)
	ground.mesh = plane
	ground.position.y = -0.002
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("41484f")
	material.roughness = 0.75
	ground.material_override = material
	add_child(ground)
	camera = Camera3D.new()
	camera.near = 0.015
	camera.current = true
	add_child(camera)
	var canvas := CanvasLayer.new()
	add_child(canvas)
	var label := Label.new()
	label.position = Vector2(20, 18)
	label.text = (
		"YARIS HYBRID TREND · MY22 · STUDIO DEL MODELLO\n"
		+ "1 Esterni · 2 Posteriore · 3 Abitacolo · O Portiere · H Portellone\n"
		+ "Trascina: ruota · Rotella: distanza · Ricostruzione da fotografie"
	)
	label.add_theme_color_override("font_color", Color("f1f2f4"))
	canvas.add_child(label)
	_update_camera()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		interior = false
		azimuth -= event.relative.x * 0.007
		elevation = clampf(elevation + event.relative.y * 0.005, 0.04, 1.25)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = maxf(2.2, distance - 0.35)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = minf(12.0, distance + 0.35)
	elif event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_1:
				interior = false
				azimuth = -0.64
			KEY_2:
				interior = false
				azimuth = 2.5
			KEY_3:
				interior = true
			KEY_O:
				doors_open = not doors_open
				for wheel_id in YarisVisual.WHEEL_IDS:
					visual.set_door_open(wheel_id, 1.0 if doors_open else 0.0)
			KEY_H:
				hatch_open = not hatch_open
				visual.set_hatch_open(1.0 if hatch_open else 0.0)
	_update_camera()


func _update_camera() -> void:
	if interior:
		camera.position = Vector3(-0.12, 1.19, 0.55)
		camera.fov = 88
		camera.look_at(Vector3(0, 0.85, -0.65))
	else:
		camera.fov = 43
		camera.position = (
			(
				Vector3(
					sin(azimuth) * cos(elevation), sin(elevation), -cos(azimuth) * cos(elevation)
				)
				* distance
			)
			+ Vector3(0, 0.75, 0)
		)
		camera.look_at(Vector3(0, 0.75, -0.1))
