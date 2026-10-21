extends "res://godot/scripts/drive_pilot.gd"
## Synthetic stop at the north approach. No dismount, mass transfer or PV-01 claim.

const StopState = preload("res://godot/scripts/parking_state.gd")
var stop := StopState.new()
var zone := Transform3D.IDENTITY
var zone_size := Vector2.ZERO
var zone_marker: MeshInstance3D


func _init() -> void:
	road_data_path = "build/circuit/parking_road.json"
	trial_manifest_path = "build/circuit/parking_manifest.json"


func _ready() -> void:
	await super._ready()
	if not is_instance_valid(vehicle):
		return
	var parking: Dictionary = road.parking
	zone = Transform3D(Basis.looking_at(vector(parking.forward)), vector(parking.center_m))
	zone_size = Vector2(parking.width_m, parking.length_m)
	stop.hold_s = parking.hold_s
	var vertices := PackedVector3Array()
	for p in [
		Vector3(-1, 0, -1),
		Vector3(1, 0, -1),
		Vector3(1, 0, 1),
		Vector3(-1, 0, 1),
		Vector3(-1, 0, -1)
	]:
		vertices.append(zone * Vector3(p.x * zone_size.x / 2, 0.1, p.z * zone_size.y / 2))
	var mesh := ImmediateMesh.new()
	mesh.surface_begin(Mesh.PRIMITIVE_LINE_STRIP)
	for p in vertices:
		mesh.surface_add_vertex(p)
	mesh.surface_end()
	zone_marker = MeshInstance3D.new()
	zone_marker.mesh = mesh
	zone_marker.material_override = material(Color("ffe19c"))
	add_child(zone_marker)
	var label := Label3D.new()
	label.text = "Sosta provvisoria"
	label.position = zone.origin + Vector3.UP * 3
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.font_size = 24
	label.pixel_size = 0.006
	add_child(label)


func inside_stop() -> bool:
	if zone_size == Vector2.ZERO:
		return false
	# Every body-footprint corner must fit, not only the vehicle origin.
	for x in [-0.5, 0.5]:
		for z in [-0.5, 0.5]:
			var local := (
				zone.affine_inverse()
				* (
					vehicle.global_transform
					* Vector3(
						x * float(vehicle.config.body.width_m),
						0,
						z * float(vehicle.config.body.length_m)
					)
				)
			)
			if (
				absf(local.x) > zone_size.x / 2
				or absf(local.z) > zone_size.y / 2
				or absf(local.y) > 1
			):
				return false
	return true


func _physics_process(delta: float) -> void:
	super._physics_process(delta)
	if not is_instance_valid(vehicle) or recovering or zone_size == Vector2.ZERO:
		return
	if stop.phase == "parked":
		vehicle.throttle = 0
		vehicle.braking = 1
		vehicle.steering_target = 0
		if not inside_stop():
			trial.fail("Auto fuori dalla sosta: recuperare con R")
	stop.update(
		{
			"inside": inside_stop(),
			"gates": trial.can_arrive(),
			"speed": vehicle.linear_velocity.length(),
			"angular_speed": vehicle.angular_velocity.length(),
			"upright": vehicle.global_basis.y.dot(Vector3.UP),
			"contacts": vehicle.diagnostic_contact_count,
			"brake": vehicle.braking,
			"incident": not trial.incident.is_empty()
		},
		delta
	)


func toggle_stop() -> bool:
	if recovering or not trial.incident.is_empty():
		return false
	if stop.phase == "parked":
		return stop.leave()
	return stop.enter()


func _process(delta: float) -> void:
	super._process(delta)
	if not is_instance_valid(vehicle):
		return
	hud.text += (
		"\nSOSTA TECNICA | %s\nPersonaggi a bordo: discesa e visita ancora da integrare"
		% ("Sosta attiva | E: torna alla guida" if stop.phase == "parked" else stop.reason)
	)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_E:
		toggle_stop()
	else:
		super._unhandled_input(event)


func reset_trial(message: String, fresh := false) -> void:
	stop.reset()
	await super.reset_trial(message, fresh)
