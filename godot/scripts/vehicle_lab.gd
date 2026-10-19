class_name LaboratoryVehicle
extends RigidBody3D
## Four single-ray contacts, rigid mast and locked passenger proxies.
## Photo-reconstructed Yaris visual; no calibrated wheel dynamics, ESC or character rig.

const YarisScene = preload("res://godot/scenes/yaris_game_visual.tscn")

var config: Dictionary
var properties: Dictionary
var throttle := 0.0
var braking := 0.0
var steering_target := 0.0
var steering := 0.0
var wheel_loads := PackedFloat32Array([0.0, 0.0, 0.0, 0.0])
var wheel_lengths := PackedFloat32Array([0.31, 0.31, 0.31, 0.31])
var wheel_anchors: Array[Vector3] = []
var yaris_visual: YarisVisual
var diagnostic_contact_count := 0
var reset_requested := false
var invalidated := false
var telemetry: FileAccess
var elapsed := 0.0
var sample_clock := 0.0
var physics_frames := 0


func _ready() -> void:
	config = JSON.parse_string(FileAccess.get_file_as_string("res://data/config/vehicle_lab.json"))
	properties = MassProperties.calculate(config.components)
	mass = properties.mass
	center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	center_of_mass = properties.com
	inertia = properties.diagonal
	linear_damp = 0.0
	angular_damp = 0.0
	continuous_cd = true
	contact_monitor = true
	max_contacts_reported = 16
	var half_track := float(config.body.track_m) * 0.5
	var half_base := float(config.body.wheelbase_m) * 0.5
	var hardpoint := float(config.suspension.hardpoint_y_m)
	wheel_anchors = [
		Vector3(-half_track, hardpoint, -half_base),
		Vector3(half_track, hardpoint, -half_base),
		Vector3(-half_track, hardpoint, half_base),
		Vector3(half_track, hardpoint, half_base)
	]
	_build_proxies()
	# Single aggregate: proxy meshes have no separate rigid bodies or added mass.
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(1.68, 0.75, 3.8)
	shape.shape = box
	shape.position.y = 0.70
	add_child(shape)
	var mast_collision := CollisionShape3D.new()
	var mast_shape := BoxShape3D.new()
	mast_shape.size = Vector3(0.18, 5.3, 0.18)
	mast_collision.shape = mast_shape
	mast_collision.position.y = 3.9
	add_child(mast_collision)
	var nest_collision := CollisionShape3D.new()
	var nest_shape := BoxShape3D.new()
	nest_shape.size = Vector3(1.2, 0.3, 1.2)
	nest_collision.shape = nest_shape
	nest_collision.position.y = 5.6
	add_child(nest_collision)
	if not DirAccess.dir_exists_absolute("user://telemetry"):
		DirAccess.make_dir_recursive_absolute("user://telemetry")
	var stamp := (
		"%d_%d_%d" % [int(Time.get_unix_time_from_system()), OS.get_process_id(), get_instance_id()]
	)
	telemetry = FileAccess.open("user://telemetry/lab_" + stamp + ".csv", FileAccess.WRITE)
	if telemetry:
		telemetry.store_csv_line(
			PackedStringArray(
				[
					"time_s",
					"hz",
					"x_m",
					"y_m",
					"z_m",
					"speed_m_s",
					"up_dot",
					"FL_N",
					"FR_N",
					"RL_N",
					"RR_N",
					"reset_invalidated"
				]
			)
		)
	print("LAB ONLY — mass/COM: ", mass, " kg / ", center_of_mass)
	print("Full design tensor: ", properties.tensor, "; Godot approximation: diagonal")
	print("Telemetry folder: ", ProjectSettings.globalize_path("user://telemetry"))


func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	if reset_requested:
		state.transform = Transform3D(Basis.IDENTITY, Vector3(0, 0.2, 8))
		state.linear_velocity = Vector3.ZERO
		state.angular_velocity = Vector3.ZERO
		reset_requested = false
		invalidated = true
		reset_physics_interpolation()
		return
	var dt := state.step
	elapsed += dt
	physics_frames += 1
	steering = move_toward(
		steering,
		steering_target * float(config.powertrain.steering_max_rad),
		float(config.powertrain.steering_rate_rad_s) * dt
	)
	var basis := state.transform.basis.orthonormalized()
	var up := basis.y
	var speed_forward := state.linear_velocity.dot(-basis.z)
	var drive_total := (
		minf(
			float(config.powertrain.drive_force_limit_n),
			(
				float(config.powertrain.power_limit_w)
				/ maxf(absf(speed_forward), float(config.powertrain.power_regularization_m_s))
			)
		)
		* throttle
	)
	diagnostic_contact_count = 0
	for i in range(4):
		_solve_wheel(state, i, drive_total, up, basis)
	var velocity := state.linear_velocity
	var aero: Dictionary = config.aero
	state.apply_central_force(
		(
			-0.5
			* float(aero.air_density_kg_m3)
			* float(aero.drag_coefficient_area_m2)
			* velocity.length()
			* velocity
		)
	)
	sample_clock += dt
	if sample_clock >= 0.05:
		sample_clock -= 0.05
		_sample(state)


func _solve_wheel(
	state: PhysicsDirectBodyState3D, index: int, drive: float, up: Vector3, basis: Basis
) -> void:
	var suspension: Dictionary = config.suspension
	var tire: Dictionary = config.tire
	var origin := state.transform * wheel_anchors[index]
	var ray_length := (
		float(suspension.rest_length_m) + float(suspension.droop_m) + float(tire.radius_m)
	)
	var query := PhysicsRayQueryParameters3D.create(origin, origin - up * ray_length)
	query.exclude = [get_rid()]
	query.collision_mask = 1
	var hit := state.get_space_state().intersect_ray(query)
	wheel_loads[index] = 0.0
	wheel_lengths[index] = float(suspension.rest_length_m) + float(suspension.droop_m)
	if hit.is_empty():
		return
	var normal: Vector3 = hit.normal
	if normal.dot(up) < 0.2:
		return  # Wall/overturned contact belongs to chassis collision solver.
	var point: Vector3 = hit.position
	var length := maxf(0.0, origin.distance_to(point) - float(tire.radius_m))
	wheel_lengths[index] = length
	var lever := point - state.transform.origin
	var point_velocity := (
		state.linear_velocity + state.angular_velocity.cross(lever - state.center_of_mass)
	)
	var compression := float(suspension.rest_length_m) - length
	var compression_speed := -point_velocity.dot(up)
	var load := WheelForces.spring(compression, compression_speed, suspension)
	if load <= 0.0:
		return
	wheel_loads[index] = load
	diagnostic_contact_count += 1
	state.apply_force(normal * load, lever)
	var forward := -basis.z
	if index < 2:
		forward = forward.rotated(up, -steering)
	forward = (forward - normal * forward.dot(normal)).normalized()
	var lateral := forward.cross(normal).normalized()
	var vx := point_velocity.dot(forward)
	var vy := point_velocity.dot(lateral)
	var regularization := float(tire.low_speed_regularization_m_s)
	var slip := atan2(vy, maxf(absf(vx), regularization))
	var lateral_force := -float(tire.corner_stiffness_n_rad) * slip
	# Smooth regularization through zero; brake/rolling force oppose contact velocity.
	var longitudinal_force := drive * 0.5 if index < 2 else 0.0
	longitudinal_force -= (
		braking * float(config.powertrain.brake_force_total_n) * 0.25 * clampf(vx / 0.5, -1.0, 1.0)
	)
	longitudinal_force -= (
		float(config.aero.rolling_coefficient) * load * clampf(vx / 0.5, -1.0, 1.0)
	)
	var forces := WheelForces.combined(longitudinal_force, lateral_force, load, float(tire.mu))
	state.apply_force(forward * forces.x + lateral * forces.y, lever)


func _process(delta: float) -> void:
	if is_instance_valid(yaris_visual):
		yaris_visual.update_running_gear(
			wheel_anchors, wheel_lengths, steering, linear_velocity.dot(-global_basis.z), delta
		)


func _sample(state: PhysicsDirectBodyState3D) -> void:
	if not telemetry:
		return
	var p := state.transform.origin
	telemetry.store_csv_line(
		PackedStringArray(
			[
				str(elapsed),
				str(1.0 / state.step),
				str(p.x),
				str(p.y),
				str(p.z),
				str(state.linear_velocity.length()),
				str(state.transform.basis.y.dot(Vector3.UP)),
				str(wheel_loads[0]),
				str(wheel_loads[1]),
				str(wheel_loads[2]),
				str(wheel_loads[3]),
				str(invalidated)
			]
		)
	)
	if physics_frames % 120 == 0:
		telemetry.flush()


func _build_proxies() -> void:
	yaris_visual = YarisScene.instantiate() as YarisVisual
	add_child(yaris_visual)
	_box(Vector3(0.18, 5.3, 0.18), Vector3(0, 3.9, 0), Color("aa7e46"))
	_box(Vector3(1.2, 0.3, 1.2), Vector3(0, 5.6, 0), Color("c49c64"))
	_box(Vector3(0.32, 0.45, 0.6), Vector3(0.1, 6.4, 0), Color("cda5a0"))


func _box(size: Vector3, at: Vector3, color: Color) -> void:
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	mesh.mesh = box
	mesh.position = at
	mesh.material_override = _material(color)
	add_child(mesh)


func _material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.85
	return material
