extends "res://godot/scripts/circuit.gd"
## Engineering inspection scene. T compares immutable DTM with the graded variant.

const Surface = preload("res://godot/scripts/construction_surface.gd")
var shoulder_entries: Dictionary = {}
var shoulder_residents: Dictionary = {}
var asphalt := Surface.make_material(Color("303236"))
var verge := Surface.make_material(Color("758968"), 20.0)
var original_entries: Dictionary = {}
var construction_entries: Dictionary = {}
var construction: Dictionary = {}
var road_entries: Dictionary = {}
var road_residents: Dictionary = {}
var original_mode := false
var issue_index := -1
var issue_root := Node3D.new()


func _ready() -> void:
	data_path = "build/circuit/construction_manifest.json"
	super._ready()
	if not ready_ok:
		hud.text = "COSTRUZIONE CIRCUITO | dati locali assenti\nRigenerare: build_circuit_construction.py"
		return
	if not data.has("engineering_construction"):
		ready_ok = false
		stream_error("Construction manifest required")
		return
	construction = data.engineering_construction
	construction_entries = entries.duplicate(true)
	var path := base_dir.path_join("manifest.json")
	if FileAccess.get_sha256(path) != str(construction.report.source_manifest_sha256):
		ready_ok = false
		stream_error("Original terrain changed; regenerate construction")
		return
	var original: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
	for item in original.sectors:
		original_entries[str(item.id)] = item
	for item in construction.road_sectors:
		road_entries[str(item.id)] = item
	var shoulder_path := base_dir.path_join("shoulders.json")
	if FileAccess.file_exists(shoulder_path):
		var shoulders: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(shoulder_path))
		if (
			shoulders.get("construction_manifest_sha256")
			!= FileAccess.get_sha256(base_dir.path_join("construction_manifest.json"))
		):
			ready_ok = false
			stream_error("Construction changed: regenerate shoulders")
			return
		for item in shoulders.sectors:
			shoulder_entries[str(item.id)] = item
	add_child(issue_root)
	for issue in construction.report.issues:
		var label := Label3D.new()
		label.text = (
			"INVERSIONE DA VERIFICARE" if issue.kind == "exact_reversal" else "CURVA DA VERIFICARE"
		)
		if issue.kind == "large_earthworks_delta":
			label.text = "SCAVO / RIPORTO DA RIVEDERE"
		elif issue.kind == "steep_design_grade":
			label.text = "PENDENZA DA RIVEDERE"
		label.position = vector(issue.point_m) + Vector3.UP * 5
		label.modulate = Color("ff7468")
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.font_size = 32
		label.pixel_size = 0.025
		issue_root.add_child(label)
	# super._ready can queue terrain before road metadata is available.
	refresh_stream()
	while not pending.is_empty():
		load_next()
	focus_sector(2)


func load_next() -> void:
	var id := "" if pending.is_empty() else pending[0]
	super.load_next()
	if original_mode or id.is_empty() or not residents.has(id):
		return
	var chunk: Node3D = residents[id]
	if shoulder_entries.has(id):
		var body := _load_surface(shoulder_entries[id], chunk, 8, verge)
		if is_instance_valid(body):
			shoulder_residents[id] = body
	if road_entries.has(id):
		var body := _load_surface(road_entries[id], chunk, 4, asphalt)
		if is_instance_valid(body):
			road_residents[id] = body


func _load_surface(item: Dictionary, chunk: Node3D, layer: int, mat: Material) -> StaticBody3D:
	var relative := str(item.path)
	if not relative.begins_with("datasets/") or relative.contains(".."):
		stream_error("Unsafe surface path")
		return null
	var path := base_dir.path_join(relative)
	if not FileAccess.file_exists(path) or FileAccess.get_sha256(path) != str(item.sha256):
		stream_error("Missing or changed surface chunk " + str(item.id))
		return null
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary or parsed.get("id") != item.id:
		stream_error("Invalid construction surface chunk " + str(item.id))
		return null
	return Surface.build(parsed, chunk, layer, mat)


func refresh_stream() -> void:
	super.refresh_stream()
	for id in shoulder_residents.keys():
		if not residents.has(id):
			shoulder_residents.erase(id)
	for id in road_residents.keys():
		if not residents.has(id):
			road_residents.erase(id)


func toggle_original() -> void:
	if not ready_ok:
		return
	original_mode = not original_mode
	for chunk: Node3D in residents.values():
		chunk.queue_free()
	residents.clear()
	road_residents.clear()
	shoulder_residents.clear()
	pending.clear()
	entries = (
		original_entries.duplicate(true) if original_mode else construction_entries.duplicate(true)
	)
	for id in overview:
		var visual: MeshInstance3D = overview[id]
		visual.mesh = Grid.build(entries[id].overview, 1, true)
		visual.visible = true
	refresh_stream()


func focus_issue() -> void:
	if not ready_ok or construction.report.issues.is_empty():
		return
	issue_index = (issue_index + 1) % construction.report.issues.size()
	var target := vector(construction.report.issues[issue_index].point_m)
	camera.position = target + Vector3(24, 30, 30)
	camera.look_at(target)
	refresh_stream()


func _process(delta: float) -> void:
	if not ready_ok:
		return
	super._process(delta)
	var state := "DTM ORIGINALE" if original_mode else "PROGETTO PROVVISORIO"
	hud.text = (
		(
			"COSTRUZIONE CIRCUITO | %s | %.1f km candidati\n"
			% [state, float(construction.report.route_length_horizontal_m) / 1000]
		)
		+ "T: confronto terreno | F9: punto critico successivo | F1â€¦F7: settori | M: anello\n"
		+ "WASD + Q/E: camera | Maiusc: veloce | destro: guarda | 1: asse  2: edifici\n"
		+ (
			"Asfalto di progetto %.1f m + raccordi al terreno | Rosso: verifiche aperte"
			% float(construction.report.config.width_m)
		)
	)
	if show_diagnostics:
		hud.text += (
			"\n%d terreno / %d strada residenti | %d inversioni conservate"
			% [residents.size(), road_residents.size(), int(construction.report.exact_reversals)]
		)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_T:
			toggle_original()
			return
		if event.keycode == KEY_F9:
			focus_issue()
			return
	super._unhandled_input(event)
