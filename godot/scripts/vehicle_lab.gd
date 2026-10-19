class_name LaboratoryVehicle
extends RigidBody3D
## Four single-ray contacts, rigid mast and locked passenger proxies.
## No final Yaris model, wheel angular dynamics, ESC or elastic mast.

const BERNIE_MODEL = preload("res://godot/assets/characters/bernie.glb")
const BIANCA_MODEL = preload("res://godot/assets/characters/bianca.glb")

var config: Dictionary
var properties: Dictionary
var throttle := 0.0
var braking := 0.0
var steering_target := 0.0
var steering := 0.0
var wheel_loads := PackedFloat32Array([0.0, 0.0, 0.0, 0.0])
var wheel_lengths := PackedFloat32Array([0.31, 0.31, 0.31, 0.31])
var wheel_anchors: Array[Vector3] = []
var wheels: Array[Node3D] = []
var diagnostic_contact_count := 0
var reset_requested := false
var invalidated := false
var telemetry: FileAccess
var elapsed := 0.0
var sample_clock := 0.0
var physics_frames := 0
var driver: PhysicsOccupant
var lookout: PhysicsOccupant
var steering_wheel: Node3D
var driver_grips: Array[Node3D] = []
var pedal_pivots: Array[Node3D] = []
var lookout_grips: Array[Node3D] = []
var driver_acceleration := Vector3.UP * 9.81
var lookout_acceleration := Vector3.UP * 9.81
var previous_linear := Vector3.ZERO
var previous_angular := Vector3.ZERO
var motion_initialized := false


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
	var stamp := str(int(Time.get_unix_time_from_system()))
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
		motion_initialized = false
		driver.reset_motion()
		lookout.reset_motion()
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
	_capture_support_motion(state, dt)
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


func _process(_delta: float) -> void:
	for i in range(wheels.size()):
		wheels[i].position = wheel_anchors[i] - Vector3.UP * wheel_lengths[i]
		wheels[i].rotation.y = -steering if i < 2 else 0.0


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
	_box(Vector3(1.745, 0.36, 3.94), Vector3(0, 0.55, 0), Color("bb333b"))
	# Open window envelope keeps the driver visible. Bodywork remains a proxy.
	_box(Vector3(1.45, 0.06, 1.9), Vector3(0, 1.5, 0.1), Color("bb333b"))
	for side in [-1.0, 1.0]:
		_box(Vector3(0.06, 0.5, 0.06), Vector3(side * 0.69, 1.25, -0.82), Color("bb333b"))
		_box(Vector3(0.06, 0.5, 0.06), Vector3(side * 0.69, 1.25, 1.02), Color("bb333b"))
	_box(Vector3(0.18, 5.3, 0.18), Vector3(0, 3.9, 0), Color("aa7e46"))
	_box(Vector3(1.2, 0.3, 1.2), Vector3(0, 5.6, 0), Color("c49c64"))
	# Occupant mass remains in the aggregate; deformation rigs add no rigid bodies.
	driver = PhysicsOccupant.new()
	driver.name = "BernieDriver"
	driver.role = "driver"
	driver.position = Vector3(-0.32, 0.63, -0.35)
	driver.add_child(BERNIE_MODEL.instantiate())
	add_child(driver)
	lookout = PhysicsOccupant.new()
	lookout.name = "BiancaLookout"
	lookout.position = Vector3(0.22, 5.756, -0.23)
	lookout.add_child(BIANCA_MODEL.instantiate())
	add_child(lookout)
	_build_contact_supports()
	for anchor in wheel_anchors:
		var wheel := Node3D.new()
		add_child(wheel)
		var mesh := MeshInstance3D.new()
		var cylinder := CylinderMesh.new()
		cylinder.top_radius = float(config.tire.radius_m)
		cylinder.bottom_radius = float(config.tire.radius_m)
		cylinder.height = 0.195
		mesh.mesh = cylinder
		mesh.rotation.z = PI * 0.5
		mesh.material_override = _material(Color("303c42"))
		wheel.add_child(mesh)
		wheel.position = anchor - Vector3.UP * 0.31
		wheels.append(wheel)


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


func _capture_support_motion(state: PhysicsDirectBodyState3D, dt: float) -> void:
	var acceleration := Vector3.ZERO
	var angular_acceleration := Vector3.ZERO
	if motion_initialized:
		acceleration = (state.linear_velocity - previous_linear) / dt
		angular_acceleration = (state.angular_velocity - previous_angular) / dt
	previous_linear = state.linear_velocity
	previous_angular = state.angular_velocity
	motion_initialized = true
	var basis := state.transform.basis.orthonormalized()
	var gravity := state.total_gravity
	var driver_offset: Vector3 = basis * (driver.position + Vector3(0, 0.35, 0) - properties.com)
	var lookout_offset: Vector3 = basis * (lookout.position + Vector3(0, 0.45, 0) - properties.com)
	driver_acceleration = point_specific_force(
		acceleration, angular_acceleration, state.angular_velocity, driver_offset, basis, gravity
	)
	lookout_acceleration = point_specific_force(
		acceleration, angular_acceleration, state.angular_velocity, lookout_offset, basis, gravity
	)


static func point_specific_force(
	acceleration: Vector3,
	alpha: Vector3,
	omega: Vector3,
	offset: Vector3,
	basis: Basis,
	gravity: Vector3
) -> Vector3:
	return (
		basis.inverse()
		* (acceleration + alpha.cross(offset) + omega.cross(omega.cross(offset)) - gravity)
	)


func _physics_process(delta: float) -> void:
	if driver == null:
		return
	steering_wheel.rotation.y = -steering * 0.30
	driver.pedal_inputs = Vector2(absf(throttle), braking)
	pedal_pivots[0].rotation.x = -0.12 * braking
	pedal_pivots[1].rotation.x = -0.12 * absf(throttle)
	var axis := driver.skeleton.global_basis.inverse() * steering_wheel.global_basis.y
	var turn := Basis(axis.normalized(), -steering * 0.30)
	driver.animate_support(
		delta, driver_acceleration, _contact_frames(driver, driver_grips, turn), steering
	)
	lookout.animate_support(
		delta, lookout_acceleration, _contact_frames(lookout, lookout_grips, Basis.IDENTITY), 0.0
	)


func _contact_frames(
	actor: PhysicsOccupant, nodes: Array[Node3D], hand_basis: Basis
) -> Array[Transform3D]:
	var frames: Array[Transform3D] = []
	for node in nodes:
		var frame := actor.skeleton.global_transform.affine_inverse() * node.global_transform
		frame.origin += hand_basis * Vector3(0, 0.040, 0)
		frame.basis = hand_basis
		frames.append(frame)
	return frames


func _build_contact_supports() -> void:
	_box(Vector3(0.29, 0.04, 0.25), driver.position + Vector3(0, 0.135, 0.04), Color("303738"))
	_box(Vector3(0.29, 0.28, 0.04), driver.position + Vector3(0, 0.27, 0.13), Color("303738"))
	var mount := Node3D.new()
	mount.name = "SteeringMount"
	mount.position = driver.position + Vector3(0, 0.385, -0.13)
	mount.rotation.x = deg_to_rad(90)
	add_child(mount)
	steering_wheel = Node3D.new()
	steering_wheel.name = "SteeringWheel"
	mount.add_child(steering_wheel)
	var mesh := MeshInstance3D.new()
	var ring := TorusMesh.new()
	ring.inner_radius = 0.067
	ring.outer_radius = 0.083
	mesh.mesh = ring
	mesh.material_override = _material(Color("292c31"))
	steering_wheel.add_child(mesh)
	for spoke in range(3):
		var angle := float(spoke) * TAU / 3.0
		_rod(
			Vector3.ZERO, Vector3(cos(angle) * 0.067, 0, sin(angle) * 0.067), 0.004, steering_wheel
		)
	for side in [-1, 1]:
		var grip := Node3D.new()
		grip.position = Vector3(side * 0.075, 0, 0)
		steering_wheel.add_child(grip)
		driver_grips.append(grip)
		var pedal := Node3D.new()
		pedal.position = driver.position + Vector3(side * 0.082, 0.023, -0.15)
		add_child(pedal)
		pedal_pivots.append(pedal)
		var pad := MeshInstance3D.new()
		var pad_mesh := BoxMesh.new()
		pad_mesh.size = Vector3(0.065, 0.025, 0.10)
		pad.mesh = pad_mesh
		pad.material_override = _material(Color("53595c"))
		pad.position = Vector3(0, -0.0105, -0.05)
		pedal.add_child(pad)
		_rod(Vector3(side * 0.56, 5.75, -0.56), Vector3(side * 0.56, 6.21, -0.56), 0.018)
		var handhold := Node3D.new()
		handhold.position = lookout.position + Vector3(side * 0.11, 0.480, -0.14)
		add_child(handhold)
		lookout_grips.append(handhold)
		_rod(
			Vector3(lookout.position.x + side * 0.18, 6.21, -0.56),
			lookout.position + Vector3(side * 0.18, 0.480, -0.14),
			0.009
		)
	_rod(Vector3(-0.56, 6.21, -0.56), Vector3(0.56, 6.21, -0.56), 0.018)
	_rod(
		lookout.position + Vector3(-0.18, 0.480, -0.14),
		lookout.position + Vector3(0.18, 0.480, -0.14),
		0.009
	)


func _rod(a: Vector3, b: Vector3, radius: float, parent: Node3D = null) -> void:
	var mesh := MeshInstance3D.new()
	var cylinder := CylinderMesh.new()
	cylinder.top_radius = radius
	cylinder.bottom_radius = radius
	cylinder.height = a.distance_to(b)
	mesh.mesh = cylinder
	mesh.material_override = _material(Color("8d6c43") if parent == null else Color("292c31"))
	mesh.position = (a + b) * 0.5
	mesh.quaternion = Quaternion(Vector3.UP, (b - a).normalized())
	if parent == null:
		add_child(mesh)
	else:
		parent.add_child(mesh)
