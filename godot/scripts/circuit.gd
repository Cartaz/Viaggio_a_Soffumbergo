extends "res://godot/scripts/valle.gd"
## Streamed survey inspector: inherits the Valle camera and shared OSM layers.

const Grid = preload("res://godot/scripts/circuit_mesh.gd")
const FineSector = preload("res://godot/scripts/circuit_sector.gd")
const EnvironmentLayer = preload("res://godot/scripts/circuit_environment.gd")
var environment_layer: Node3D
var entries: Dictionary = {}
var overview: Dictionary = {}
var residents: Dictionary = {}
var pending: Array[String] = []
var stream_errors: Array[String] = []
var base_dir := ""
var ground: StandardMaterial3D
var stream_timer := 0.0
var max_residents := 0
var max_build_ms := 0
var chunks_loaded := 0
var chunks_unloaded := 0
var overview_triangles: Dictionary = {}
var show_diagnostics := false
var overview_bounds := AABB()
var data_path := "build/circuit/manifest.json"


func _ready() -> void:
	var started := Time.get_ticks_msec()
	_setup_view()
	camera.far = 20000
	var path := ProjectSettings.globalize_path("res://").path_join(data_path)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--circuit-data="):
			path = arg.trim_prefix("--circuit-data=")
	if not FileAccess.file_exists(path):
		hud.text = "Circuito 3D | DTM locale assente\nRigenerare: tools/build_circuit_3d.py"
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary or parsed.get("prototype") != "Circuito 3D 0.1":
		stream_error("Unsupported circuit manifest")
		return
	data = parsed
	if data.get("axes") != "+X east, +Y up, +Z south" or data.get("horizontal_crs") != "EPSG:6708":
		stream_error("Circuit coordinate frame mismatch")
		return
	base_dir = path.get_base_dir()
	ground = material(Color("758968"))
	ground.cull_mode = BaseMaterial3D.CULL_BACK
	_build_overview()
	data["buildings"] = data.valle_content.buildings
	environment_layer = EnvironmentLayer.new()
	add_child(environment_layer)
	if environment_layer.configure(path, camera):
		data["buildings"] = data.buildings.filter(
			func(item: Dictionary) -> bool:
				return not environment_layer.covered_osm.has(str(item.id))
		)
	data["roads"] = data.valle_content.roads
	_build_buildings()
	_build_roads()
	_build_candidate()
	ready_ok = true
	load_ms = Time.get_ticks_msec() - started
	refresh_stream()


func _build_overview() -> void:
	for item in data.sectors:
		var id := str(item.id)
		entries[id] = item
		var instance := MeshInstance3D.new()
		var mesh := Grid.build(item.overview, 1, true)
		instance.mesh = mesh
		instance.material_override = ground
		instance.position = Vector3(item.offset_xz_m[0], 0, item.offset_xz_m[1])
		add_child(instance)
		overview[id] = instance
		var arrays := mesh.surface_get_arrays(0)
		overview_triangles[id] = (arrays[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3


func _build_candidate() -> void:
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color("ffb52e")
	# An inspection overlay, not a road surface or a road-width measurement.
	mat.no_depth_test = true
	var mesh := ImmediateMesh.new()
	for feature in data.route:
		mesh.surface_begin(Mesh.PRIMITIVE_LINE_STRIP, mat)
		for p in feature.points_m:
			mesh.surface_add_vertex(vector(p) + Vector3.UP * 0.4)
		mesh.surface_end()
		var label := Label3D.new()
		label.text = "Settore " + str(feature.sector) + " | candidato OSM"
		label.position = vector(feature.points_m[0]) + Vector3.UP * 15
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.font_size = 36
		label.pixel_size = 0.04
		road_root.add_child(label)
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	road_root.add_child(instance)


func _process(delta: float) -> void:
	if not ready_ok:
		return
	var movement := Vector3(
		float(Input.is_physical_key_pressed(KEY_D)) - float(Input.is_physical_key_pressed(KEY_A)),
		float(Input.is_physical_key_pressed(KEY_E)) - float(Input.is_physical_key_pressed(KEY_Q)),
		float(Input.is_physical_key_pressed(KEY_S)) - float(Input.is_physical_key_pressed(KEY_W))
	)
	var speed := 250.0 if Input.is_physical_key_pressed(KEY_SHIFT) else 45.0
	if movement.length_squared() > 0:
		camera.position += camera.basis * movement.normalized() * speed * delta
	stream_timer += delta
	if stream_timer > 0.15:
		refresh_stream()
		stream_timer = 0
	var start := Time.get_ticks_msec()
	while (
		not pending.is_empty() and Time.get_ticks_msec() - start < int(data.config.stream_budget_ms)
	):
		load_next()
	update_lods()
	hud.text = (
		"CIRCUITO 3D 0.1 | terreno reale, percorso ancora da verificare\n"
		+ "WASD + Q/E: camera | Maiusc: veloce | destro: guarda | R: Valle | M: anello\n"
		+ "F1…F7: settori A/B/C/V/D/E/F | 1: linee  2: sagome OSM\n"
		+ "Ambra: percorso provvisorio | Grigio: edifici segnaposto | F8: dati di collaudo"
	)
	if show_diagnostics:
		hud.text += (
			"\n%d settori | %d residenti | %d in coda | %d triangoli assegnati | %d ms avvio"
			% [entries.size(), residents.size(), pending.size(), visible_triangles(), load_ms]
		)


func refresh_stream() -> void:
	for id in residents.keys():
		if distance_to_entry(id) > float(data.config.unload_radius_m):
			(residents[id] as Node3D).queue_free()
			residents.erase(id)
			(overview[id] as MeshInstance3D).visible = true
			chunks_unloaded += 1
	pending.clear()
	for id in entries:
		if not residents.has(id) and distance_to_entry(id) <= float(data.config.load_radius_m):
			pending.append(id)
	pending.sort_custom(
		func(a: String, b: String) -> bool: return distance_to_entry(a) < distance_to_entry(b)
	)


func distance_to_entry(id: String) -> float:
	var p: Array = entries[id].offset_xz_m
	return Vector2(camera.position.x - p[0] - 64, camera.position.z - p[1] - 64).length()


func load_next() -> void:
	if pending.is_empty():
		return
	var id: String = pending.pop_front()
	var item: Dictionary = entries[id]
	var path := base_dir.path_join(str(item.path))
	if not str(item.path).begins_with("datasets/") or str(item.path).contains(".."):
		stream_error("Unsafe terrain chunk path")
		return
	if not FileAccess.file_exists(path) or FileAccess.get_sha256(path) != str(item.sha256):
		stream_error("Missing or changed terrain chunk " + id)
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary or parsed.get("id") != id or parsed.get("side") != 65:
		stream_error("Invalid terrain chunk " + id)
		return
	var start := Time.get_ticks_msec()
	var chunk := FineSector.new()
	add_child(chunk)
	chunk.build(parsed, ground)
	if is_instance_valid(environment_layer):
		environment_layer.attach_tile(chunk, id)
	residents[id] = chunk
	(overview[id] as MeshInstance3D).visible = false
	chunk.update_lod(camera.position, data.config.lod_distances_m)
	max_build_ms = maxi(max_build_ms, Time.get_ticks_msec() - start)
	max_residents = maxi(max_residents, residents.size())
	chunks_loaded += 1


func update_lods() -> void:
	for chunk: Node3D in residents.values():
		chunk.update_lod(camera.position, data.config.lod_distances_m)


func visible_triangles() -> int:
	var total := 0
	for id in entries:
		if residents.has(id):
			var chunk: Node3D = residents[id]
			total += int(chunk.triangle_counts[chunk.current_lod])
		else:
			total += int(overview_triangles[id])
	return total


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode >= KEY_F1 and event.keycode <= KEY_F7:
			focus_sector(event.keycode - KEY_F1)
			return
		if event.keycode == KEY_M:
			show_overview()
			return
		if event.keycode == KEY_F8:
			show_diagnostics = not show_diagnostics
			return
	super._unhandled_input(event)


func focus_sector(index: int) -> void:
	if not ready_ok or index >= data.route.size():
		return
	var points: Array = data.route[index].points_m
	var target := vector(points[points.size() / 2])
	camera.position = target + Vector3(140, 180, 200)
	camera.look_at(target)
	refresh_stream()


func show_overview() -> void:
	if not ready_ok:
		return
	var bounds := AABB()
	for item in entries.values():
		var heights: Array = item.overview.heights_m.filter(
			func(h: Variant) -> bool: return h != null
		)
		if heights.is_empty():
			continue
		var p: Array = item.offset_xz_m
		bounds = bounds.expand(Vector3(p[0], heights.min(), p[1]))
		bounds = bounds.expand(Vector3(p[0] + 128, heights.max(), p[1] + 128))
	overview_bounds = bounds
	var target := bounds.get_center()
	var extent := maxf(bounds.size.x, bounds.size.z)
	var offset := Vector3(0, extent * 0.6, extent * 0.6)
	for i in range(24):
		camera.position = target + offset
		camera.look_at(target)
		if overview_fits():
			break
		offset *= 1.1
	refresh_stream()


func overview_fits() -> bool:
	var size := get_viewport().get_visible_rect().size
	var frame := Rect2(Vector2(24, 136), Vector2(maxf(1, size.x - 48), maxf(1, size.y - 160)))
	for i in range(8):
		var point := overview_bounds.get_endpoint(i)
		if (
			camera.is_position_behind(point)
			or not frame.has_point(camera.unproject_position(point))
		):
			return false
	return true


func stream_error(message: String) -> void:
	stream_errors.append(message)
	push_error(message)
