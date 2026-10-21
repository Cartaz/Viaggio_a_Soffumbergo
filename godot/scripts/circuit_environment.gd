extends Node3D
## Coded visual blockouts. Recipes are data; unverified extents have no colliders.

var catalog: Dictionary = {}
var objects: Dictionary = {}
var covered_osm: Dictionary = {}
var markers: Dictionary = {}
var meshes: Dictionary = {}
var materials: Dictionary = {}
var labels := Node3D.new()
var caption := Label.new()
var show_codes := false
var elapsed := 0.0
var eye: Camera3D
var enabled := false


func configure(manifest_path: String, camera: Camera3D) -> bool:
	var path := "res://data/geography/circuit_placeholders.json"
	if not FileAccess.file_exists(path):
		return false
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:
		push_error("Invalid environment catalog")
		return false
	if parsed.get("construction_manifest_sha256") != FileAccess.get_sha256(manifest_path):
		# Original-terrain inspection retains its own historical Valle layer.
		return false
	if not _valid_frame(parsed):
		push_error("Environment frame or schema mismatch")
		return false
	for item: Dictionary in parsed.objects:
		var code := str(item.get("code", ""))
		if code.is_empty() or objects.has(code) or bool(item.get("collision_enabled", true)):
			objects.clear()
			push_error("Duplicate environment identity or unverified collision")
			return false
		objects[code] = item
	catalog = parsed
	for id in catalog.covered_legacy_osm_ids:
		covered_osm[str(id)] = true
	eye = camera
	name = "CodedEnvironment"
	add_child(labels)
	labels.visible = false
	var canvas := CanvasLayer.new()
	add_child(canvas)
	canvas.add_child(caption)
	caption.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	caption.offset_left = 18
	caption.offset_right = -18
	caption.offset_top = -82
	caption.offset_bottom = -12
	caption.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	caption.add_theme_color_override("font_shadow_color", Color.BLACK)
	caption.add_theme_constant_override("shadow_offset_x", 2)
	caption.add_theme_constant_override("shadow_offset_y", 2)
	caption.text = (
		"Segnaposto del paesaggio | F10: codici e descrizioni vicine\n"
		+ "Forme provvisorie, posizioni visive stimate | OSM © contributors"
	)
	enabled = true
	return true


func _valid_frame(parsed: Dictionary) -> bool:
	var origin: Array = parsed.get("origin_ENH_m", [])
	return (
		origin.size() == 3
		and parsed.get("schema_version") == 1
		and parsed.get("horizontal_crs") == "EPSG:6708"
		and float(origin[0]) == 375920.0
		and float(origin[1]) == 5112728.0
		and float(origin[2]) == 720.0
		and parsed.get("axes") == "+X east, +Y up, +Z south"
	)


func attach_tile(parent: Node3D, id: String) -> void:
	if not enabled or not catalog.tiles.has(id):
		return
	var holder := Node3D.new()
	holder.name = "EnvironmentPlaceholders"
	parent.add_child(holder)
	var batches: Dictionary = {}
	for code in catalog.tiles[id]:
		var item: Dictionary = objects[code]
		var marker := Node3D.new()
		marker.name = str(code)
		# Subtract integral tile origin in doubles before constructing float Vector3.
		marker.position = Vector3(
			float(item.position_m[0]) - float(parent.position.x),
			item.position_m[1],
			float(item.position_m[2]) - float(parent.position.z)
		)
		marker.rotation.y = deg_to_rad(float(item.yaw_deg))
		marker.set_meta("placeholder", item)
		holder.add_child(marker)
		markers[str(code)] = weakref(marker)
		for primitive: Dictionary in item.primitives:
			var key := "%s:%s:%s" % [item.category, primitive.kind, primitive.color]
			if not batches.has(key):
				batches[key] = {"primitive": primitive, "transforms": []}
			var size: Array = primitive.size_m
			var center: Array = primitive.center_m
			var local := Transform3D(
				Basis.IDENTITY.scaled(Vector3(size[0], size[1], size[2])),
				Vector3(center[0], center[1], center[2])
			)
			batches[key].transforms.append(marker.transform * local)
	for key in batches:
		var batch: Dictionary = batches[key]
		var primitive: Dictionary = batch.primitive
		var multi := MultiMesh.new()
		multi.transform_format = MultiMesh.TRANSFORM_3D
		multi.mesh = _mesh(str(primitive.kind))
		multi.instance_count = batch.transforms.size()
		for index in range(multi.instance_count):
			multi.set_instance_transform(index, batch.transforms[index])
		var instance := MultiMeshInstance3D.new()
		instance.name = str(key).replace(":", "_")
		instance.multimesh = multi
		instance.material_override = _material(str(primitive.color))
		instance.visibility_range_end = float(catalog.render_distance_m)
		holder.add_child(instance)


func _mesh(kind: String) -> Mesh:
	if meshes.has(kind):
		return meshes[kind]
	var mesh: Mesh
	if kind == "box":
		mesh = BoxMesh.new()
	elif kind == "sphere":
		var sphere := SphereMesh.new()
		sphere.radius = 0.5
		sphere.height = 1
		sphere.radial_segments = 8
		sphere.rings = 4
		mesh = sphere
	else:
		var cylinder := CylinderMesh.new()
		cylinder.top_radius = 0 if kind == "cone" else 0.5
		cylinder.bottom_radius = 0.5
		cylinder.height = 1
		cylinder.radial_segments = 8
		cylinder.rings = 1
		mesh = cylinder
	meshes[kind] = mesh
	return mesh


func _material(color: String) -> Material:
	if not materials.has(color):
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(color)
		mat.roughness = 0.95
		materials[color] = mat
	return materials[color]


func active_codes() -> Array[String]:
	var codes: Array[String] = []
	for code: String in markers.keys():
		if markers[code].get_ref() == null:
			markers.erase(code)
		else:
			codes.append(code)
	return codes


func _process(delta: float) -> void:
	if not enabled:
		return
	elapsed += delta
	if elapsed < 0.4:
		return
	elapsed = 0
	var codes := active_codes()
	if not show_codes:
		return
	for label in labels.get_children():
		label.free()
	codes.sort_custom(func(a: String, b: String) -> bool: return _distance(a) < _distance(b))
	var frames: Array[Rect2] = []
	var screen := get_viewport().get_visible_rect().size
	var safe_frame := Rect2(Vector2(12, 140), screen - Vector2(24, 250))
	if not codes.is_empty():
		var nearest: Dictionary = objects[codes[0]]
		caption.text = (
			str(nearest.code)
			+ " | "
			+ str(nearest.description)
			+ "\nSegnaposto provvisorio | F10: nascondi schede | Catalogo completo nei rapporti"
		)
	for i in range(mini(40, codes.size())):
		var code := codes[i]
		if _distance(code) > 80:
			break
		var item: Dictionary = objects[code]
		var marker: Node3D = markers[code].get_ref()
		var top := 2.2
		for primitive: Dictionary in item.primitives:
			top = maxf(top, float(primitive.center_m[1]) + float(primitive.size_m[1]) / 2)
		var anchor := marker.global_position + Vector3.UP * (top + 0.8)
		if eye.is_position_behind(anchor):
			continue
		var projected := eye.unproject_position(anchor)
		var frame := Rect2(projected - Vector2(120, 22), Vector2(240, 44))
		if not safe_frame.encloses(frame):
			continue
		if frames.any(func(other: Rect2) -> bool: return other.intersects(frame)):
			continue
		frames.append(frame)
		var label := Label3D.new()
		label.text = code + "\n" + str(catalog.categories[item.category].label)
		label.position = anchor
		label.font_size = 26
		label.pixel_size = 0.0011
		label.fixed_size = true
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.modulate = Color("fff2c7")
		labels.add_child(label)
		if frames.size() >= 6:
			break


func _distance(code: String) -> float:
	var marker: Node3D = markers[code].get_ref()
	return (
		Vector2(
			marker.global_position.x - eye.position.x, marker.global_position.z - eye.position.z
		)
		. length()
	)


func _unhandled_input(event: InputEvent) -> void:
	if enabled and event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_F10:
			show_codes = not show_codes
			labels.visible = show_codes
			if not show_codes:
				caption.text = (
					"Segnaposto del paesaggio | F10: codici e descrizioni vicine\n"
					+ "Forme provvisorie e posizioni visive stimate | OSM © contributors"
				)
			get_viewport().set_input_as_handled()
