extends "res://godot/scripts/circuit.gd"
## Isolated engineering trial. No assertion of surveyed road width, junctions or PV-01.

const Vehicle = preload("res://godot/scripts/vehicle_lab.gd")
var vehicle: LaboratoryVehicle
var road: Dictionary = {}
var points := PackedVector3Array()
var station := PackedFloat32Array()
var progress_m := 0.0
var lateral_error_m := 0.0
var trial_resets := 0
var arrived := false
var follow := true
var automated := false
var trial_message := ""
var spawn := Transform3D.IDENTITY


func _ready() -> void:
	data_path = "build/circuit/pilot_manifest.json"
	var path := "res://build/circuit/pilot_road.json"
	if not FileAccess.file_exists(path):
		_setup_view()
		hud.text = "Accesso a Valle | dati locali assenti: rigenerare con tools/build_drive_pilot.py"
		return
	road = JSON.parse_string(FileAccess.get_file_as_string(path))
	if road.get("status") != "engineering_trial_not_surveyed_road":
		push_error("Unsupported road trial")
		return
	for p in road.points_m:
		points.append(vector(p))
	station.append(0)
	for i in range(1, points.size()):
		station.append(station[-1] + points[i - 1].distance_to(points[i]))
	spawn = Transform3D(Basis.looking_at(points[3] - points[2]), points[2] + Vector3.UP * 0.2)
	super._ready()
	if not ready_ok:
		return
	camera.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	road_root.visible = false
	_build_trial_road()
	camera.position = spawn.origin
	refresh_stream()
	while not pending.is_empty():
		load_next()
	await get_tree().physics_frame
	vehicle = Vehicle.new()
	vehicle.wheel_collision_mask = 5
	vehicle.collision_mask = 7
	vehicle.transform = spawn
	vehicle.reset_transform = spawn
	add_child(vehicle)
	vehicle.braking = 1
	trial_message = "Strada di prova: larghezza e sistemazione del fondo da verificare"


func _build_trial_road() -> void:
	var faces := PackedVector3Array()
	for triangle in road.triangles:
		for index in triangle:
			faces.append(vector(road.vertices_m[index]))
	var mat := material(Color("8b7952"))
	var instance := Content.face_mesh(faces, mat)
	add_child(instance)
	instance.create_trimesh_collision()
	var body := instance.get_child(0) as StaticBody3D
	body.collision_layer = 4
	body.collision_mask = 0
	var mesh := ImmediateMesh.new()
	var edge := material(Color("ffbd38"))
	edge.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	for side in range(2):
		mesh.surface_begin(Mesh.PRIMITIVE_LINE_STRIP, edge)
		for i in range(points.size()):
			mesh.surface_add_vertex(vector(road.vertices_m[i * 2 + side]) + Vector3.UP * 0.03)
		mesh.surface_end()
	var borders := MeshInstance3D.new()
	borders.mesh = mesh
	add_child(borders)


func distance_to_entry(id: String) -> float:
	var p: Array = entries[id].offset_xz_m
	var origin := vehicle.position if is_instance_valid(vehicle) else spawn.origin
	return Vector2(origin.x - p[0] - 64, origin.z - p[1] - 64).length()


func _physics_process(_delta: float) -> void:
	if not is_instance_valid(vehicle):
		return
	_measure_progress()
	if not automated:
		vehicle.throttle = (
			float(Input.is_physical_key_pressed(KEY_W))
			- float(Input.is_physical_key_pressed(KEY_S))
		)
		vehicle.braking = float(Input.is_physical_key_pressed(KEY_SPACE))
		vehicle.steering_target = (
			float(Input.is_physical_key_pressed(KEY_D))
			- float(Input.is_physical_key_pressed(KEY_A))
		)
	if lateral_error_m > 18 or vehicle.position.y < -100:
		reset_trial("Fuori dall'area di prova: ripartenza")
	arrived = progress_m > station[-1] - 8 and vehicle.road_speed_m_s() < 0.05


func _measure_progress() -> void:
	var best := INF
	var q := Vector2(vehicle.position.x, vehicle.position.z)
	for i in range(points.size() - 1):
		var a := Vector2(points[i].x, points[i].z)
		var b := Vector2(points[i + 1].x, points[i + 1].z)
		var t := clampf((q - a).dot(b - a) / (b - a).length_squared(), 0, 1)
		var distance := q.distance_to(a.lerp(b, t))
		if distance < best:
			best = distance
			progress_m = lerpf(station[i], station[i + 1], t)
	lateral_error_m = best


func target_at(distance: float) -> Vector3:
	for i in range(1, station.size()):
		if station[i] >= distance:
			return points[i - 1].lerp(
				points[i], (distance - station[i - 1]) / (station[i] - station[i - 1])
			)
	return points[-1]


func _process(delta: float) -> void:
	if not is_instance_valid(vehicle):
		return
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
	if follow:
		var heading := -vehicle.global_basis.z
		heading.y = 0
		heading = heading.normalized()
		var desired := vehicle.position - heading * 10 + Vector3.UP * 5
		camera.position = camera.position.lerp(desired, 1.0 - exp(-5 * delta))
		camera.look_at(vehicle.position + Vector3.UP * 1.8)
	hud.text = (
		"ACCESSO A VALLE | prova su candidato OSM e terreno DTM\n"
		+ "W/S: avanti/retro | A/D: sterzo | Spazio: freno | R: riparti | M: mappa | C: insegui\n"
		+ (
			"%.1f km/h | %.0f / %.0f m | %s\n"
			% [
				vehicle.road_speed_m_s() * 3.6,
				progress_m,
				station[-1],
				"Arrivo raggiunto" if arrived else "Verso l'ingresso del borgo"
			]
		)
		+ trial_message
	)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_R:
			reset_trial("Prova ripristinata")
		elif event.keycode == KEY_M:
			follow = false
			show_overview()
		elif event.keycode == KEY_C:
			follow = true


func reset_trial(message: String) -> void:
	trial_resets += 1
	vehicle.reset_requested = true
	trial_message = message
	arrived = false
