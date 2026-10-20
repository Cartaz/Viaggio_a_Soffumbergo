extends Node3D
## Georeferenced survey prototype. Free camera is an inspection tool, not a visitor.

const Sector = preload("res://godot/scripts/valle_sector.gd")
const DEFAULT_DATA := "build/valle/valle_scene.json"
var data: Dictionary = {}
var sectors: Array[Node3D] = []
var camera := Camera3D.new()
var hud := Label.new()
var road_root := Node3D.new()
var building_root := Node3D.new()
var ready_ok := false
var load_ms := 0
var lod_timer := 0.0


func _ready() -> void:
	var started := Time.get_ticks_msec()
	_setup_view()
	var path := ProjectSettings.globalize_path("res://").path_join(DEFAULT_DATA)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--valle-data="):
			path = arg.trim_prefix("--valle-data=")
	if not FileAccess.file_exists(path):
		hud.text = (
			"Valle 3D 0.1 | DTM locale assente\n"
			+ "Rigenerare con tools/build_valle_3d.py (vedere docs/VALLE_3D.md)"
		)
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary or parsed.get("prototype") != "Valle 3D 0.1":
		push_error("Valle: unsupported local data")
		return
	data = parsed
	if data.get("axes") != "+X east, +Y up, +Z south" or data.get("horizontal_crs") != "EPSG:6708":
		push_error("Valle: coordinate frame mismatch")
		return
	var ground := material(Color("758968"))
	ground.cull_mode = BaseMaterial3D.CULL_BACK
	for sector_data in data.sectors:
		var sector := Sector.new()
		add_child(sector)
		sector.build(sector_data, data.config, ground)
		sectors.append(sector)
	_build_buildings()
	_build_roads()
	for anchor in data.anchors:
		var label := Label3D.new()
		label.text = str(anchor.name) + "\n" + str(anchor.status)
		label.position = vector(anchor.position_m) + Vector3.UP * 12
		label.font_size = 32
		label.pixel_size = 0.04
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		add_child(label)
	ready_ok = true
	load_ms = Time.get_ticks_msec() - started
	update_lods()


func _setup_view() -> void:
	var environment := WorldEnvironment.new()
	var settings := Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color("b6cbd1")
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color("e5e4d9")
	settings.ambient_light_energy = 0.45
	environment.environment = settings
	add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-45, -35, 0)
	sun.light_energy = 0.65
	sun.shadow_enabled = true
	add_child(sun)
	add_child(camera)
	camera.position = Vector3(220, 220, 280)
	camera.look_at(Vector3(0, 0, 0))
	camera.far = 2400
	camera.current = true
	var canvas := CanvasLayer.new()
	add_child(canvas)
	hud.position = Vector2(18, 16)
	hud.add_theme_color_override("font_color", Color.WHITE)
	hud.add_theme_color_override("font_shadow_color", Color.BLACK)
	hud.add_theme_constant_override("shadow_offset_x", 2)
	hud.add_theme_constant_override("shadow_offset_y", 2)
	canvas.add_child(hud)
	add_child(building_root)
	add_child(road_root)


func _process(delta: float) -> void:
	if not ready_ok:
		return
	var movement := Vector3.ZERO
	movement.x = (
		float(Input.is_physical_key_pressed(KEY_D)) - float(Input.is_physical_key_pressed(KEY_A))
	)
	movement.z = (
		float(Input.is_physical_key_pressed(KEY_S)) - float(Input.is_physical_key_pressed(KEY_W))
	)
	movement.y = (
		float(Input.is_physical_key_pressed(KEY_E)) - float(Input.is_physical_key_pressed(KEY_Q))
	)
	var speed := 100.0 if Input.is_physical_key_pressed(KEY_SHIFT) else 30.0
	if movement.length_squared() > 0:
		camera.position += (camera.basis * movement.normalized()) * speed * delta
	lod_timer += delta
	if lod_timer > 0.15:
		update_lods()
		lod_timer = 0
	hud.text = (
		"VALLE 3D 0.1 | DTM FVG 0,5 m → terreno 2/4/8 m | OSM © contributors\n"
		+ "Grigio: sagome OSM, altezze segnaposto | Ambra: strade provvisorie | Magenta: sentieri\n"
		+ "WASD + Q/E: camera libera | Maiusc: veloce | tasto destro: guarda | R: vista iniziale\n"
		+ "1: strade  2: edifici | PV-01 candidato | Nessuna superficie asfaltata verificata\n"
		+ (
			"%d settori | %d triangoli terreno visibili | caricamento %d ms"
			% [sectors.size(), visible_triangles(), load_ms]
		)
	)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if event.pressed else Input.MOUSE_MODE_VISIBLE
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		camera.rotation.y -= event.relative.x * 0.003
		camera.rotation.x = clampf(camera.rotation.x - event.relative.y * 0.003, -1.5, 1.5)
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_R:
			camera.position = Vector3(220, 220, 280)
			camera.look_at(Vector3.ZERO)
		if event.keycode == KEY_1:
			road_root.visible = not road_root.visible
		if event.keycode == KEY_2:
			building_root.visible = not building_root.visible
		if event.keycode == KEY_ESCAPE:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func update_lods() -> void:
	for sector in sectors:
		sector.update_lod(camera.position, data.config.lod_distances_m)


func visible_triangles() -> int:
	var total := 0
	for sector in sectors:
		total += int(sector.triangle_counts[sector.current_lod])
	return total


func _build_buildings() -> void:
	var gray := material(Color("c8c4b8"))
	for building in data.buildings:
		var ring := PackedVector2Array()
		for p in building.ring_xz_m:
			ring.append(Vector2(p[0], p[1]))
		var faces := PackedVector3Array()
		var roof := Geometry2D.triangulate_polygon(ring)
		for i in range(0, roof.size(), 3):
			var a := Vector3(ring[roof[i]].x, building.roof_y_m, ring[roof[i]].y)
			var b := Vector3(ring[roof[i + 1]].x, building.roof_y_m, ring[roof[i + 1]].y)
			var c := Vector3(ring[roof[i + 2]].x, building.roof_y_m, ring[roof[i + 2]].y)
			if (b - a).cross(c - a).y > 0:
				faces.append_array(PackedVector3Array([a, c, b]))
			else:
				faces.append_array(PackedVector3Array([a, b, c]))
		for i in range(ring.size()):
			var p := ring[i]
			var q := ring[(i + 1) % ring.size()]
			var a := Vector3(p.x, building.base_y_m, p.y)
			var b := Vector3(q.x, building.base_y_m, q.y)
			var c := Vector3(q.x, building.roof_y_m, q.y)
			var d := Vector3(p.x, building.roof_y_m, p.y)
			faces.append_array(PackedVector3Array([a, b, c, a, c, d]))
		var instance := face_mesh(faces, gray)
		instance.name = "OSM_" + str(building.id).replace("/", "_")
		instance.set_meta("source_url", building.source_url)
		instance.set_meta("height_status", building.height_status)
		building_root.add_child(instance)
		instance.create_trimesh_collision()
		var body := instance.get_child(0) as StaticBody3D
		body.collision_layer = 2
		body.collision_mask = 0
		var collision := body.get_child(0) as CollisionShape3D
		(collision.shape as ConcavePolygonShape3D).backface_collision = true


func _build_roads() -> void:
	var amber := material(Color("e8a43e"))
	var magenta := material(Color("cc64c6"))
	for road in data.roads:
		var faces := PackedVector3Array()
		var columns := int(road.columns)
		for i in range(columns, road.vertices_m.size()):
			if i % columns == columns - 1:
				continue
			var a := vector(road.vertices_m[i - columns])
			var b := vector(road.vertices_m[i - columns + 1])
			var c := vector(road.vertices_m[i])
			var d := vector(road.vertices_m[i + 1])
			faces.append_array(PackedVector3Array([a, c, b, b, c, d]))
		var instance := face_mesh(faces, magenta if road.pedestrian else amber)
		instance.set_meta("source_url", road.source_url)
		instance.set_meta("status", road.status)
		road_root.add_child(instance)


static func face_mesh(faces: PackedVector3Array, mat: Material) -> MeshInstance3D:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for p in faces:
		surface.add_vertex(p)
	surface.generate_normals()
	var instance := MeshInstance3D.new()
	instance.mesh = surface.commit()
	instance.material_override = mat
	return instance


static func material(color: Color) -> StandardMaterial3D:
	var result := StandardMaterial3D.new()
	result.albedo_color = color
	result.roughness = 0.92
	# OSM ring orientation is source-dependent; closed blockouts are two-sided.
	result.cull_mode = BaseMaterial3D.CULL_DISABLED
	return result


static func vector(p: Array) -> Vector3:
	return Vector3(p[0], p[1], p[2])
