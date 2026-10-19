extends SceneTree
## Fixed contact, constant limb lengths, damped response and garment collision checks.

var vehicle: LaboratoryVehicle
var worst_grip := 0.0
var worst_length := 0.0
var driver_grip := 0.0
var lookout_grip := 0.0
var least_cloth_clearance := 100.0
var failures: Array[String] = []


func _initialize() -> void:
	call_deferred("run_checks")


func run_checks() -> void:
	vehicle = LaboratoryVehicle.new()
	root.add_child(vehicle)
	vehicle.set_physics_process(false)
	var g := Vector3(0, -9.81, 0)
	var low := LaboratoryVehicle.point_specific_force(
		Vector3.ZERO, Vector3(0, 0, 1), Vector3.ZERO, Vector3(0, 1, 0), Basis.IDENTITY, g
	)
	var high := LaboratoryVehicle.point_specific_force(
		Vector3.ZERO, Vector3(0, 0, 1), Vector3.ZERO, Vector3(0, 6, 0), Basis.IDENTITY, g
	)
	check(absf(high.x / low.x - 6.0) < 0.00001, "Point acceleration must reflect attachment height")
	for steering in [-0.52, 0.0, 0.52]:
		vehicle.steering = steering
		for force in [Vector3(0, 9.81, 0), Vector3(8, 14, -8), Vector3(-8, 5, 8)]:
			vehicle.driver.reset_motion()
			vehicle.lookout.reset_motion()
			vehicle.driver_acceleration = force
			vehicle.lookout_acceleration = force * Vector3(1.2, 1, 1.2)
			for frame in range(60):
				vehicle._physics_process(1.0 / 120.0)
				inspect_contacts()
	check(worst_grip < 0.0001, "Hands lost contact: " + str(worst_grip))
	check(worst_length < 0.00001, "IK stretched a limb: " + str(worst_length))
	check(least_cloth_clearance >= -0.0001, "Cape/arm penetration: " + str(least_cloth_clearance))
	var pitch := vehicle.lookout.lean.x
	check(pitch < 0.0, "Braking must move the upper body toward the front")
	check(vehicle.lookout.heave > 0.003, "Reduced vertical support must unload the knees")
	vehicle.driver_acceleration = Vector3.UP * 9.81
	vehicle.lookout_acceleration = Vector3.UP * 9.81
	for frame in range(480):
		vehicle._physics_process(1.0 / 120.0)
	check(vehicle.lookout.lean.length() < 0.00001, "Reaction failed to settle at rest")
	check(absf(vehicle.lookout.heave) < 0.00001, "Vertical reaction failed to settle at rest")
	check(vehicle.lookout.cloth_swing.length() < 0.00001, "Cape failed to settle at rest")
	var values: Array[Vector3] = []
	for hz in [60, 120, 240]:
		vehicle.lookout.reset_motion()
		vehicle.lookout_acceleration = Vector3(4, 9.81, -3)
		for frame in range(hz):
			vehicle._physics_process(1.0 / float(hz))
		values.append(vehicle.lookout.lean)
	check(values[0].distance_to(values[2]) < 0.0001, "Reaction varies with physics step")
	var report := {
		"worst_grip_error_m": worst_grip,
		"worst_limb_length_error_m": worst_length,
		"minimum_cape_arm_clearance_m": least_cloth_clearance,
		"failures": failures,
		"driver_grip": driver_grip,
		"lookout_grip": lookout_grip,
		"samples": 540,
		"physics_steps_hz": [60, 120, 240]
	}
	DirAccess.make_dir_recursive_absolute("res://art/source/generated/characters")
	var file := FileAccess.open(
		"res://art/source/generated/characters/occupant_checks.json", FileAccess.WRITE
	)
	file.store_string(JSON.stringify(report, "  "))
	print(JSON.stringify(report))
	vehicle.free()
	quit(0 if failures.is_empty() else 1)


func inspect_contacts() -> void:
	driver_grip = maxf(driver_grip, vehicle.driver.grip_error)
	lookout_grip = maxf(lookout_grip, vehicle.lookout.grip_error)
	for actor in [vehicle.driver, vehicle.lookout]:
		worst_grip = maxf(worst_grip, actor.grip_error)
		worst_length = maxf(worst_length, actor.length_error)
		for i in range(actor.skeleton.get_bone_count()):
			var pose: Transform3D = actor.skeleton.get_bone_global_pose(i)
			check(pose.is_finite(), "Non-finite bone pose")
			check(absf(pose.basis.determinant() - 1.0) < 0.0001, "Bone scale changed")
	least_cloth_clearance = minf(least_cloth_clearance, vehicle.lookout.cape.minimum_clearance)


func check(condition: bool, message: String) -> void:
	if not condition and not failures.has(message):
		failures.append(message)
