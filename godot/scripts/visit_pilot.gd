extends "res://godot/scripts/parking_pilot.gd"
## Local dismount/walk/remount trial. This does not certify a route to the village.

const Actor = preload("res://godot/scripts/visit_actor.gd")
const Transfer = preload("res://godot/scripts/visit_mass.gd")
var visit_phase := "aboard"
var visitors: Array = []
var paths: Array = []
var path_indices := [0, 0]
var seated_visuals: Array[Node3D] = []
var walk_intent := Vector3.ZERO
var breadcrumbs: Array[Vector3] = []
var visited_trial := false
var split_momentum_error := 0.0
var max_force_pair_error := 0.0
var maximum_mass_error := 0.0
var initial_mass := 0.0
var transition_clock := 0.0
var guide_speed_m_s := 0.4
var guide_meshes: Array[Node3D] = []
var observed_actor := 0


func _ready() -> void:
	await super._ready()
	if is_instance_valid(vehicle):
		initial_mass = vehicle.mass


func begin_dismount() -> bool:
	if (
		visit_phase != "aboard"
		or stop.phase != "parked"
		or not inside_stop()
		or not trial.incident.is_empty()
		or vehicle.linear_velocity.length() >= 0.1
		or vehicle.angular_velocity.length() >= 0.05
		or vehicle.diagnostic_contact_count != 4
		or vehicle.braking < 0.5
		or vehicle.global_basis.y.dot(Vector3.UP) <= 0.95
	):
		return false
	var before: Vector3 = vehicle.mass * vehicle.linear_velocity
	for part in vehicle.config.components:
		if part.id not in ["driver", "passenger"]:
			continue
		var actor := Actor.new()
		actor.vehicle = vehicle
		actor.role = part.id
		actor.mass = part.mass_kg
		actor.transform = Transform3D(
			vehicle.basis, vehicle.global_transform * vector(part.position_m)
		)
		actor.linear_velocity = (
			vehicle.linear_velocity
			+ vehicle.angular_velocity.cross(
				actor.position - vehicle.global_transform * vehicle.center_of_mass
			)
		)
		var original := (
			vehicle.find_child(
				"BernieDriver" if part.id == "driver" else "BiancaLookout", true, false
			)
			as Node3D
		)
		if original != null and original.get_child_count() > 0:
			actor.visual = original.get_child(0).duplicate() as Node3D
			actor.visual.position = Vector3(0, -0.25, 0)
			original.visible = false
			seated_visuals.append(original)
		else:
			for child in vehicle.get_children():
				if (
					child is MeshInstance3D
					and child.position.distance_to(vector(part.position_m)) < 0.1
				):
					child.visible = false
					seated_visuals.append(child)
		add_child(actor)
		if original != null and actor.visual != null:
			actor.visual.global_transform = original.get_child(0).global_transform
			actor.visual_start = actor.visual.position
		actor.add_collision_exception_with(vehicle)
		actor.guide_enabled = true
		actor.guide_target = vector(part.position_m)
		visitors.append(actor)
	Transfer.set_aggregate(vehicle, false)
	split_momentum_error = (Transfer.momentum(vehicle, visitors) - before).length()
	paths = [_descent_path(0), _descent_path(1)]
	path_indices = [0, 0]
	transition_clock = 0
	visit_phase = "descending"
	vehicle.yaris_visual.set_door_open("FL", 1)
	_build_guides()
	return true


func _descent_path(index: int) -> Array[Vector3]:
	var actor: RigidBody3D = visitors[index]
	var start: Vector3 = vehicle.to_local(actor.position)
	var side := -1.0 if index == 0 else 1.0
	var ground := _ground_target(Vector3(side * 1.55, 0, start.z))
	# The passenger exits above the parapet, then descends outside the bodywork.
	if index == 1:
		return [start + Vector3.UP * 0.45, Vector3(side * 1.55, start.y + 0.45, start.z), ground]
	return [Vector3(side * 1.55, start.y, start.z), ground]


func _ground_target(local: Vector3) -> Vector3:
	var world := vehicle.global_transform * local
	var query := PhysicsRayQueryParameters3D.create(
		world + Vector3.UP * 10, world - Vector3.UP * 10, 5
	)
	query.exclude = [vehicle.get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		trial.fail("Appoggio a terra assente: recuperare con R")
		return local
	return vehicle.to_local(hit.position + Vector3.UP * 0.25)


func request_board() -> bool:
	if (
		visit_phase != "walking"
		or vehicle.linear_velocity.length() >= 0.1
		or not trial.incident.is_empty()
		or vehicle.braking < 0.5
	):
		return false
	for actor: RigidBody3D in visitors:
		if actor.position.distance_to(vehicle.position) > 4:
			return false
	# The companion goes around the rear, never across the vehicle collider.
	paths = []
	for i in range(2):
		var side := -1.0 if i == 0 else 1.0
		var from_side := -1.0 if vehicle.to_local(visitors[i].position).x < 0 else 1.0
		paths.append(
			[
				_ground_target(Vector3(from_side * 1.6, 0, 2.7)),
				_ground_target(Vector3(side * 1.6, 0, 2.7)),
				_ground_target(Vector3(side * 1.55, 0, -0.35 if i == 0 else 0))
			]
		)
	path_indices = [0, 0]
	visit_phase = "gathering"
	transition_clock = 0
	return true


func _physics_process(delta: float) -> void:
	super._physics_process(delta)
	if not is_instance_valid(vehicle) or recovering or visit_phase == "aboard":
		return
	vehicle.throttle = 0
	vehicle.braking = 1
	vehicle.steering_target = 0
	transition_clock += delta
	var total: float = vehicle.mass
	for actor in visitors:
		total += actor.mass
		max_force_pair_error = maxf(
			max_force_pair_error, (actor.guide_force + actor.reaction_force).length()
		)
	maximum_mass_error = maxf(maximum_mass_error, absf(total - initial_mass))
	if vehicle.global_basis.y.dot(Vector3.UP) < 0.9 or not inside_stop():
		trial.fail("Sosta instabile durante la visita: recuperare con R")
	if not trial.incident.is_empty():
		for actor in visitors:
			actor.desired_velocity = Vector3.ZERO
		return
	if visit_phase in ["descending", "ascending"]:
		_update_guides(delta)
	elif visit_phase == "gathering":
		_update_gathering()
	elif visit_phase == "walking":
		_update_walking()


func _update_guides(delta: float) -> void:
	var complete := true
	for i in range(2):
		var actor = visitors[i]
		if visit_phase == "ascending" and path_indices[i] >= 1:
			actor.return_to_seat = true
		if path_indices[i] < paths[i].size():
			complete = false
			var destination: Vector3 = paths[i][path_indices[i]]
			if actor.position.distance_to(vehicle.global_transform * actor.guide_target) < 0.13:
				actor.guide_target = actor.guide_target.move_toward(
					destination, guide_speed_m_s * delta
				)
			if (
				actor.position.distance_to(vehicle.global_transform * destination) < 0.04
				and actor.linear_velocity.length() < 0.08
			):
				path_indices[i] += 1
		if path_indices[i] == paths[i].size() and visit_phase == "descending":
			actor.guide_enabled = false
			actor.remove_collision_exception_with(vehicle)
			complete = complete and actor.grounded()
		if visit_phase == "ascending" and actor.skeleton != null and actor.seat_blend < 1:
			complete = false
	if complete:
		if visit_phase == "descending":
			visit_phase = "walking"
			breadcrumbs = [
				vehicle.global_transform * _ground_target(Vector3(1.6, 0, 2.7)),
				vehicle.global_transform * _ground_target(Vector3(-1.6, 0, 2.7)),
				visitors[0].position
			]
		else:
			_finish_boarding()


func _update_gathering() -> void:
	var complete := true
	for i in range(2):
		var actor = visitors[i]
		actor.desired_velocity = Vector3.ZERO
		# One visitor clears the shared rear passage before the other enters it.
		if i == 1 and path_indices[0] < paths[0].size():
			complete = false
			continue
		if path_indices[i] < paths[i].size():
			complete = false
			var target: Vector3 = vehicle.global_transform * paths[i][path_indices[i]]
			var distance: Vector3 = (target - actor.position).slide(Vector3.UP)
			actor.desired_velocity = distance.limit_length(0.8)
			if distance.length() < 0.15 and actor.grounded():
				path_indices[i] += 1
	if complete:
		paths = [_boarding_path(0), _boarding_path(1)]
		path_indices = [0, 0]
		for actor in visitors:
			actor.add_collision_exception_with(vehicle)
			actor.guide_target = vehicle.to_local(actor.position)
			actor.guide_enabled = true
		visit_phase = "ascending"


func _boarding_path(index: int) -> Array[Vector3]:
	var id := "driver" if index == 0 else "passenger"
	var seat := Vector3.ZERO
	for part in vehicle.config.components:
		if part.id == id:
			seat = vector(part.position_m)
	var side := -1.0 if index == 0 else 1.0
	var height: float = seat.y + (0.45 if index == 1 else 0.0)
	return [Vector3(side * 1.55, height, seat.z), seat + Vector3.UP * (height - seat.y), seat]


func _update_walking() -> void:
	var leader = visitors[0]
	var companion = visitors[1]
	if not automated:
		walk_intent = (
			vehicle.global_basis
			* Vector3(
				(
					float(Input.is_physical_key_pressed(KEY_D))
					- float(Input.is_physical_key_pressed(KEY_A))
				),
				0,
				(
					float(Input.is_physical_key_pressed(KEY_S))
					- float(Input.is_physical_key_pressed(KEY_W))
				)
			)
		)
	var wanted := walk_intent.slide(Vector3.UP).limit_length(1.0)
	if (
		leader.position.distance_to(vehicle.position) > 12
		and wanted.dot(leader.position - vehicle.position) > 0
	):
		wanted = Vector3.ZERO
	leader.desired_velocity = wanted
	if breadcrumbs.is_empty() or leader.position.distance_to(breadcrumbs[-1]) > 0.4:
		breadcrumbs.append(leader.position)
	companion.desired_velocity = Vector3.ZERO
	if companion.position.distance_to(leader.position) > 1.1 and not breadcrumbs.is_empty():
		if companion.position.distance_to(breadcrumbs[0]) < 0.5 and breadcrumbs.size() > 1:
			breadcrumbs.pop_front()
		companion.desired_velocity = (
			(breadcrumbs[0] - companion.position).slide(Vector3.UP).limit_length(1.0)
		)
	var marker: Vector3 = vehicle.global_transform * Vector3(-2.5, 0, 2.5)
	if (
		leader.position.distance_to(marker) < 0.9
		and companion.position.distance_to(leader.position) < 2.5
	):
		visited_trial = leader.grounded() and companion.grounded()
	for actor in visitors:
		if actor.position.y < zone.origin.y - 3:
			trial.fail("Caduta durante la prova a piedi: recuperare con R")


func _finish_boarding() -> void:
	Transfer.merge(vehicle, visitors)
	visitors.clear()
	_restore_visuals()
	visit_phase = "aboard"
	vehicle.yaris_visual.set_door_open("FL", 0)
	_clear_guides()


func _restore_visuals() -> void:
	for visual_node in seated_visuals:
		visual_node.visible = true
	seated_visuals.clear()
	if is_instance_valid(vehicle):
		vehicle.yaris_visual.set_door_open("FL", 0)


func _build_guides() -> void:
	for i in range(2):
		var local: Vector3 = paths[i][-1]
		visitors[i].ladder_base = local
		var height: float = visitors[i].guide_target.y + (0.8 if i == 1 else 0.35)
		for side in [-1, 1]:
			var pole := MeshInstance3D.new()
			var mesh := CylinderMesh.new()
			mesh.top_radius = 0.025
			mesh.bottom_radius = 0.025
			mesh.height = height - local.y
			pole.mesh = mesh
			pole.position = Vector3(local.x + side * 0.2, (height + local.y) / 2, local.z - 0.12)
			pole.material_override = material(Color("d6aa62"))
			vehicle.add_child(pole)
			guide_meshes.append(pole)
		for j in range(ceili((height - local.y) / 0.2)):
			var rung := MeshInstance3D.new()
			var mesh := BoxMesh.new()
			mesh.size = Vector3(0.45, 0.04, 0.05)
			rung.mesh = mesh
			rung.position = Vector3(local.x, local.y + j * 0.2, local.z - 0.12)
			rung.material_override = material(Color("d6aa62"))
			vehicle.add_child(rung)
			guide_meshes.append(rung)


func _clear_guides() -> void:
	for mesh_node in guide_meshes:
		mesh_node.queue_free()
	guide_meshes.clear()


func toggle_stop() -> bool:
	if visit_phase != "aboard":
		return false
	return super.toggle_stop()


func _process(delta: float) -> void:
	super._process(delta)
	if not is_instance_valid(vehicle):
		return
	var hint := "F: scendi per la prova a piedi"
	if visit_phase == "walking":
		hint = "WASD: cammina | F vicino all'auto: risali | percorso pedonale reale da verificare"
	elif visit_phase != "aboard":
		hint = "Discesa/risalita assistita in corso | guida bloccata | R: recupera"
	if visit_phase != "aboard":
		hint += " | Tab: cambia vista"
	hud.text = hud.text.replace("Personaggi a bordo: discesa e visita ancora da integrare", hint)
	if visit_phase != "aboard":
		hud.text = hud.text.replace("E: torna alla guida", "attendi il ritorno di entrambi")
		var target: Vector3 = visitors[observed_actor].position
		camera.position = camera.position.lerp(
			target + vehicle.global_basis.z * 4 + Vector3.UP * 2, 1 - exp(-5 * delta)
		)
		camera.look_at(target)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_TAB:
		observed_actor = 1 - observed_actor
		return
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F:
		if visit_phase == "aboard":
			begin_dismount()
		elif visit_phase == "walking":
			request_board()
	else:
		super._unhandled_input(event)


func reset_trial(message: String, fresh := false) -> void:
	if not visitors.is_empty():
		Transfer.merge(vehicle, visitors)
		visitors.clear()
	_restore_visuals()
	_clear_guides()
	visit_phase = "aboard"
	visited_trial = false
	observed_actor = 0
	await super.reset_trial(message, fresh)
