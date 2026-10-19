extends SceneTree
## Real Jolt run: acceleration, turns, lateral load at the mast, then braking.

var vehicle: LaboratoryVehicle
var frame := 0
var samples: Array = []
var peak_grip := 0.0
var peak_length := 0.0
var cape_clearance := 100.0
var peak_driver_force := 0.0
var peak_lookout_force := 0.0


func _initialize() -> void:
	call_deferred("setup")


func setup() -> void:
	Engine.physics_ticks_per_second = 120
	var ground := StaticBody3D.new()
	var collision := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(200, 0.4, 200)
	collision.shape = box
	ground.add_child(collision)
	ground.position.y = -0.2
	root.add_child(ground)
	vehicle = LaboratoryVehicle.new()
	vehicle.position.y = 0.2
	root.add_child(vehicle)
	physics_frame.connect(tick)


func tick() -> void:
	frame += 1
	var t := float(frame) / 120.0
	vehicle.throttle = 0.45 if t > 1.0 and t < 5.5 else 0.0
	vehicle.braking = 0.4 if t >= 6.0 else 0.0
	vehicle.steering_target = 0.0
	if t > 2.5 and t < 4.0:
		vehicle.steering_target = 0.18
	elif t >= 4.0 and t < 5.5:
		vehicle.steering_target = -0.18
	if t > 3.2 and t < 3.8:
		vehicle.apply_force(vehicle.global_basis.x * 900.0, vehicle.global_basis.y * 5.7)
	elif t >= 3.8 and t < 4.4:
		vehicle.apply_force(-vehicle.global_basis.x * 900.0, vehicle.global_basis.y * 5.7)
	if t > 4.9 and t < 5.1:
		vehicle.apply_force(
			vehicle.global_basis.y * 2400.0, vehicle.global_basis * Vector3(0.76, 0, -1.28)
		)
	if frame % 8 == 0 and t >= 1.0:
		var phase := "Accelerazione"
		if t > 2.5:
			phase = "Curva e carico laterale"
		if t > 6.0:
			phase = "Frenata e assestamento"
		var driver := vehicle.driver.snapshot()
		var lookout := vehicle.lookout.snapshot()
		samples.append(
			{
				"time": t,
				"driver": driver,
				"lookout": lookout,
				"steering": vehicle.steering,
				"phase": phase,
				"pedals": [absf(vehicle.throttle), vehicle.braking],
				"vehicle_transform": PhysicsOccupant._matrix_array(vehicle.global_transform),
				"driver_force": vector(vehicle.driver_acceleration),
				"lookout_force": vector(vehicle.lookout_acceleration)
			}
		)
		peak_grip = maxf(peak_grip, maxf(driver.grip_error, lookout.grip_error))
		peak_length = maxf(peak_length, maxf(driver.length_error, lookout.length_error))
		cape_clearance = minf(cape_clearance, lookout.cape_clearance)
		peak_driver_force = maxf(
			peak_driver_force,
			Vector2(vehicle.driver_acceleration.x, vehicle.driver_acceleration.z).length()
		)
		peak_lookout_force = maxf(
			peak_lookout_force,
			Vector2(vehicle.lookout_acceleration.x, vehicle.lookout_acceleration.z).length()
		)
	if frame >= 960:
		physics_frame.disconnect(tick)
		var indices: PackedInt32Array = vehicle.lookout.cape.rest_arrays[Mesh.ARRAY_INDEX]
		var indices_json: Array = []
		for index in indices:
			indices_json.append(index)
		var report := {
			"source": "Godot 4.5.1 Jolt, actual vehicle simulation",
			"fps": 15,
			"samples": samples,
			"cape_indices": indices_json,
			"peak_grip_error_m": peak_grip,
			"peak_limb_error_m": peak_length,
			"minimum_cape_clearance_m": cape_clearance,
			"peak_driver_horizontal_specific_force": peak_driver_force,
			"peak_lookout_horizontal_specific_force": peak_lookout_force
		}
		var path := "res://art/source/generated/characters/physics_trace.json"
		DirAccess.make_dir_recursive_absolute("res://art/source/generated/characters")
		var file := FileAccess.open(path, FileAccess.WRITE)
		file.store_string(JSON.stringify(report))
		print(
			"PHYSICS_TRACE ",
			samples.size(),
			" samples; grip error ",
			peak_grip,
			"; limb error ",
			peak_length,
			"; cape clearance ",
			cape_clearance,
			"; forces ",
			peak_driver_force,
			" / ",
			peak_lookout_force
		)
		quit(0 if peak_grip < 0.0001 and cape_clearance >= -0.0001 else 1)


func vector(v: Vector3) -> Array:
	return [v.x, v.y, v.z]
