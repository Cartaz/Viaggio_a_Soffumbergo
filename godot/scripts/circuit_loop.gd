extends "res://godot/scripts/circuit_practice.gd"
## Construction lap: gear changes require a stable stop, never a relocated body.

var loop_data: Dictionary = {}
var maneuver_case := -1
var eligible := true
var completed := false
var stop_seconds := 0.0
var completed_gates := 0
var transitions: Array[Dictionary] = []
var initialized := false


func _ready() -> void:
	var path := ProjectSettings.globalize_path("res://").path_join("build/circuit/loop.json")
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:
		stream_error("Missing loop data: run build_circuit_loop.py")
		return
	loop_data = parsed
	if (
		loop_data.get("status") != "construction_loop_with_backing_out_not_surveyed_maneuvers"
		or (
			FileAccess.get_sha256(
				ProjectSettings.globalize_path("res://").path_join(
					"build/circuit/construction_manifest.json"
				)
			)
			!= str(loop_data.construction_manifest_sha256)
		)
	):
		stream_error("Construction changed; regenerate loop data")
		return
	section_index = 0
	await super._ready()


func select_section(_index: int, _distance := 0.0) -> void:
	if initialized:
		message = "Il giro prosegue senza cambio tratto: R recupera, N ricomincia"
		return
	practice.sections = (
		loop_data.maneuver_cases[maneuver_case].legs if maneuver_case >= 0 else loop_data.legs
	)
	await super.select_section(0)
	initialized = true
	message = "Fermarsi al riferimento: attendere il cambio avanti/retro sul display"


func gear() -> int:
	return int(practice.sections[section_index].gear)


func _setup_gates(start: float) -> void:
	if route.station[-1] >= 30:
		super._setup_gates(start)
		return
	for marker in markers:
		marker.queue_free()
	markers.clear()
	gate_distances.assign([route.station[-1] * 0.5])
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


func _place_vehicle(distance: float) -> bool:
	vehicle.visible = false
	hud.text = "Caricamento della strada e delle collisioni..."
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
	var hit := get_world_3d().direct_space_state.intersect_ray(
		PhysicsRayQueryParameters3D.create(
			recovery_focus + Vector3.UP * 5, recovery_focus - Vector3.UP * 5, 4
		)
	)
	if hit.is_empty() or not stream_errors.is_empty():
		trial.fail("Superficie assente: rigenerare i dati")
		return false
	var heading := (route.at(distance + 2) - route.at(distance)) * gear()
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
	vehicle.visible = true
	return true


func recover(fresh := false) -> void:
	if switching:
		return
	eligible = false
	completed = false
	stop_seconds = 0
	if fresh:
		initialized = false
		completed_gates = 0
		transitions.clear()
		await select_section(0)
		eligible = ready_ok and not switching
	else:
		await super.recover(false)
	message = "Nuovo giro" if fresh else "Recupero dichiarato: intero giro non valido"


func _advance() -> void:
	transitions.append(
		{
			"leg": section_index,
			"position": [vehicle.position.x, vehicle.position.y, vehicle.position.z],
			"speed_m_s": vehicle.road_speed_m_s(),
			"angular_speed_rad_s": vehicle.angular_velocity.length(),
			"up": vehicle.basis.y.dot(Vector3.UP),
			"contacts": vehicle.diagnostic_contact_count,
			"gates": trial.next_gate,
			"expected_gates": trial.gates.size(),
			"stable_stop_s": stop_seconds
		}
	)
	completed_gates += trial.next_gate
	if section_index == practice.sections.size() - 1:
		completed = eligible and trial.valid
		arrived = true
		return
	section_index += 1
	route.configure(practice.sections[section_index].points_m)
	route.sample(vehicle.position, 12)
	_setup_gates(0)
	trial.configure(
		_gate_definitions(), vehicle.position, float(construction.report.config.width_m) / 2
	)
	stop_seconds = 0
	message = "AVANTI" if gear() > 0 else "RETROMARCIA sul ramo appena percorso"


func _physics_process(delta: float) -> void:
	if not ready_ok or switching or not is_instance_valid(vehicle):
		return
	route.sample(vehicle.position, vehicle.linear_velocity.length() * delta * 2 + 2)
	var up := vehicle.basis.y.dot(Vector3.UP)
	tipped_seconds = tipped_seconds + delta if up < 0.2 else 0.0
	if route.lateral > 8 or vehicle.position.y < route.at(route.progress).y - 6:
		trial.fail("Fuori dal percorso: R per recuperare")
	elif tipped_seconds > 1:
		trial.fail("Veicolo coricato: R per recuperare")
	if trial.sample(vehicle.position, delta, up > 0.5):
		markers[trial.next_gate - 1].material_override = material(Color("7fc583"))
	eligible = eligible and trial.valid and trial.incident.is_empty()
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
	var cfg: Dictionary = loop_data.config
	var offset := vehicle.position - route.at(route.station[-1])
	offset.y = 0
	var stopped := (
		trial.can_arrive()
		and offset.length() < float(cfg.endpoint_radius_m)
		and vehicle.road_speed_m_s() < float(cfg.stop_speed_m_s)
		and vehicle.angular_velocity.length() < float(cfg.stop_angular_speed_rad_s)
		and up > float(cfg.stop_up_dot)
		and vehicle.diagnostic_contact_count == 4
		and vehicle.braking >= 0.5
	)
	stop_seconds = stop_seconds + delta if stopped else 0.0
	if not arrived and stop_seconds >= float(cfg.stable_stop_s):
		_advance()
	if not trial.incident.is_empty() or arrived:
		vehicle.throttle = 0
		vehicle.braking = 1


func _process(delta: float) -> void:
	super._process(delta)
	if not initialized or switching:
		return
	hud.text = (
		(
			"GIRO DI COSTRUZIONE | fase %d/%d | %s\n"
			% [
				section_index + 1,
				practice.sections.size(),
				"AVANTI" if gear() > 0 else "RETROMARCIA"
			]
		)
		+ "W/S: avanti/retro | A/D: sterzo | Spazio: freno | R: recupero | N: nuovo giro\n"
		+ (
			"%.1f km/h | %.0f / %.0f m | punti %d | %s\n"
			% [
				vehicle.road_speed_m_s() * 3.6,
				route.progress,
				route.station[-1],
				completed_gates + trial.next_gate,
				"valido" if eligible else "giro invalidato"
			]
		)
		+ ("Giro su superficie di progetto concluso" if completed else message)
		+ "\nManovre reali da verificare. Visita del borgo separata."
	)
