extends "res://godot/scripts/circuit_construction.gd"
## Yaris training on the construction surface; section switches are explicit relocations.

const Vehicle = preload("res://godot/scripts/vehicle_lab.gd")
const Route = preload("res://godot/scripts/practice_route.gd")
const Progress = preload("res://godot/scripts/trial_progress.gd")
var route := Route.new()
var trial := Progress.new()
var vehicle: LaboratoryVehicle
var practice: Dictionary = {}
var section_index := 4
var switching := true
var recovery_focus := Vector3.ZERO
var follow := true
var automated := false
var arrived := false
var resets := 0
var relocations := 0
var tipped_seconds := 0.0
var gate_distances: Array[float] = []
var markers: Array[MeshInstance3D] = []
var message := ""
var attempt_start := 0.0


func _ready() -> void:
	super._ready()
	if not ready_ok:
		return
	var path := base_dir.path_join("practice.json")
	if not FileAccess.file_exists(path):
		ready_ok = false
		hud.text = "PRATICA CIRCUITO | dati assenti: eseguire build_circuit_practice.py"
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary or parsed.get("status") != "training_sections_not_complete_journey":
		ready_ok = false
		stream_error("Invalid practice data")
		return
	practice = parsed
	if (
		FileAccess.get_sha256(base_dir.path_join("construction_manifest.json"))
		!= str(practice.construction_manifest_sha256)
	):
		ready_ok = false
		stream_error("Construction changed; regenerate practice data")
		return
	vehicle = Vehicle.new()
	vehicle.freeze = true
	vehicle.wheel_collision_mask = 5
	vehicle.collision_mask = 7
	vehicle.braking = 1
	add_child(vehicle)
	road_root.visible = false
	camera.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	await select_section(section_index)


func distance_to_entry(id: String) -> float:
	var p: Array = entries[id].offset_xz_m
	var origin := (
		recovery_focus
		if switching
		else vehicle.position if is_instance_valid(vehicle) else camera.position
	)
	return Vector2(origin.x - p[0] - 64, origin.z - p[1] - 64).length()


func select_section(index: int, start_distance := 0.0) -> void:
	if practice.is_empty() or not is_instance_valid(vehicle):
		return
	switching = true
	section_index = posmod(index, practice.sections.size())
	relocations += 1
	route.configure(practice.sections[section_index].points_m)
	start_distance = clampf(start_distance, 0, route.station[-1] - 25)
	attempt_start = start_distance
	route.progress = start_distance
	_setup_gates(start_distance)
	if not await _place_vehicle(start_distance + 2):
		message = "Dati della superficie mancanti: rigenerare"
		return
	trial.configure(
		_gate_definitions(), vehicle.position, float(construction.report.config.width_m) / 2
	)
	arrived = false
	tipped_seconds = 0
	message = "Allenamento separato: cambio tratto con riposizionamento dichiarato"
	switching = false
	follow = true


func _setup_gates(start: float) -> void:
	for marker in markers:
		marker.queue_free()
	markers.clear()
	gate_distances.clear()
	var last: float = route.station[-1] - 10
	gate_distances.append(minf(start + 15, last))
	var distance := start + 250
	while distance < last - 20:
		gate_distances.append(distance)
		distance += 250
	if last > gate_distances[-1] + 1:
		gate_distances.append(last)
	for definition in _gate_definitions():
		var marker := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(float(construction.report.config.width_m), 0.035, 0.3)
		marker.mesh = mesh
		marker.position = definition.origin + Vector3.UP * 0.04
		marker.basis = Basis.looking_at(definition.forward)
		marker.material_override = material(Color("ffbd38"))
		add_child(marker)
		markers.append(marker)


func _gate_definitions() -> Array[Dictionary]:
	var definitions: Array[Dictionary] = []
	for distance in gate_distances:
		var forward := route.at(distance + 1) - route.at(distance - 1)
		forward.y = 0
		definitions.append({"origin": route.at(distance), "forward": forward.normalized()})
	return definitions


func _place_vehicle(distance: float) -> bool:
	vehicle.freeze = true
	vehicle.throttle = 0
	vehicle.braking = 1
	vehicle.steering_target = 0
	recovery_focus = route.at(distance)
	refresh_stream()
	while not pending.is_empty():
		load_next()
	await get_tree().physics_frame
	await get_tree().physics_frame
	var query := PhysicsRayQueryParameters3D.create(
		recovery_focus + Vector3.UP * 5, recovery_focus - Vector3.UP * 5, 4
	)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty() or not stream_errors.is_empty():
		trial.fail("Superficie assente: rigenerare i dati")
		return false
	var heading := route.at(distance + 2) - route.at(distance)
	vehicle.reset_transform = Transform3D(
		Basis.looking_at(heading), hit.position + Vector3.UP * 0.2
	)
	vehicle.reset_requested = true
	vehicle.freeze = false
	vehicle.sleeping = false
	await get_tree().physics_frame
	await get_tree().physics_frame
	route.progress = distance
	route.sample(vehicle.position, 12)
	camera.position = vehicle.position + vehicle.basis.z * 8 + Vector3.UP * 5
	camera.look_at(vehicle.position + Vector3.UP * 1.8)
	return true


func recover(fresh := false) -> void:
	if switching or not is_instance_valid(vehicle):
		return
	switching = true
	resets += 1
	var distance: float = gate_distances[trial.next_gate - 1] + 3 if trial.next_gate > 0 else 2.0
	if fresh:
		distance = attempt_start + 2
	if not await _place_vehicle(distance):
		return
	if fresh:
		trial.new_attempt(vehicle.position)
		for marker in markers:
			marker.material_override = material(Color("ffbd38"))
	else:
		trial.recover(vehicle.position)
	arrived = false
	tipped_seconds = 0
	switching = false
	message = "Nuovo tentativo del tratto" if fresh else "Recupero: tentativo non valido"


func _physics_process(delta: float) -> void:
	if not ready_ok or switching or not is_instance_valid(vehicle):
		return
	route.sample(vehicle.position, vehicle.linear_velocity.length() * delta * 2 + 2)
	var up := vehicle.basis.y.dot(Vector3.UP)
	tipped_seconds = tipped_seconds + delta if up < 0.2 else 0.0
	if route.lateral > 8 or vehicle.position.y < route.at(route.progress).y - 6:
		trial.fail("Fuori dal tratto: R per recuperare")
	elif tipped_seconds > 1:
		trial.fail("Veicolo coricato: R per recuperare")
	if trial.sample(vehicle.position, delta, up > 0.5):
		markers[trial.next_gate - 1].material_override = material(Color("7fc583"))
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
		if not follow:
			vehicle.throttle = 0
			vehicle.braking = 1
	arrived = (
		trial.can_arrive()
		and route.progress > route.station[-1] - 8
		and vehicle.road_speed_m_s() < 0.05
		and up > 0.85
		and vehicle.diagnostic_contact_count > 0
	)
	if not trial.incident.is_empty() or arrived:
		vehicle.throttle = 0
		vehicle.braking = 1


func _process(delta: float) -> void:
	if not ready_ok or switching or not is_instance_valid(vehicle):
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
		var forward := -vehicle.basis.z
		forward.y = 0
		var desired := vehicle.position - forward.normalized() * 10 + Vector3.UP * 5
		camera.position = camera.position.lerp(desired, 1 - exp(-5 * delta))
		camera.look_at(vehicle.position + Vector3.UP * 1.8)
	var section: Dictionary = practice.sections[section_index]
	var status := (
		"Tratto concluso: arresto prima del raccordo"
		if arrived
		else "Allenamento su superficie provvisoria"
	)
	if not trial.incident.is_empty():
		status = trial.incident
	hud.text = (
		(
			"PRATICA CIRCUITO | tratto %s (%d/%d) | %s\n"
			% [section.id, section_index + 1, practice.sections.size(), status]
		)
		+ "W/S: avanti/retro | A/D: sterzo | Spazio: freno | R: recupero | N: nuovo tentativo\n"
		+ "PagSu/PagGiu: cambia tratto con riposizionamento | C: insegui | M: mappa\n"
		+ (
			"%.1f km/h | %.0f / %.0f m | punti %d/%d | %s\n"
			% [
				vehicle.road_speed_m_s() * 3.6,
				route.progress,
				route.station[-1],
				trial.next_gate,
				trial.gates.size(),
				"valido" if trial.valid else "recuperato"
			]
		)
		+ message
		+ " | Nessun giro completo certificato"
	)


func _unhandled_input(event: InputEvent) -> void:
	if switching or not event is InputEventKey or not event.pressed or event.echo:
		return
	match event.keycode:
		KEY_F11:
			var fullscreen := (
				DisplayServer.window_get_mode()
				in [
					DisplayServer.WINDOW_MODE_FULLSCREEN,
					DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN
				]
			)
			DisplayServer.window_set_mode(
				(
					DisplayServer.WINDOW_MODE_WINDOWED
					if fullscreen
					else DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN
				)
			)
		KEY_ESCAPE:
			get_tree().quit()
		KEY_PAGEUP:
			select_section(section_index - 1)
		KEY_PAGEDOWN:
			select_section(section_index + 1)
		KEY_R:
			recover()
		KEY_N:
			recover(true)
		KEY_C:
			follow = true
		KEY_M:
			follow = false
			show_overview()
