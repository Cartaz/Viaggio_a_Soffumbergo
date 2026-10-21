extends SceneTree
## Real Jolt benchmark on an 40 km flat test pad, separate from finite interactive lab.

const Vehicle = preload("res://godot/scripts/vehicle_lab.gd")
const Powertrain = preload("res://godot/scripts/yaris_powertrain.gd")
var checks := 0
var failures: Array[String] = []
var folder := "build/yaris_performance/120"
var results: Dictionary = {}
var physics_only := false
var simulation_hz := 120
var fast := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg == "--physics-only":
			physics_only = true
		if arg == "--fast-physics":
			fast = true
		if arg.begins_with("--hz="):
			simulation_hz = int(arg.trim_prefix("--hz="))
		if arg.begins_with("--output="):
			folder = arg.trim_prefix("--output=")
	Engine.physics_ticks_per_second = simulation_hz * (8 if fast else 1)
	Engine.time_scale = 8 if fast else 1
	Engine.max_physics_steps_per_frame = 32
	call_deferred("run")


func run() -> void:
	var ground := StaticBody3D.new()
	var collision := CollisionShape3D.new()
	var pad := BoxShape3D.new()
	pad.size = Vector3(40000, 1, 40000)
	collision.shape = pad
	collision.position.y = -0.5
	ground.add_child(collision)
	root.add_child(ground)
	var model: Dictionary = (
		JSON
		. parse_string(FileAccess.get_file_as_string("res://data/config/yaris_performance.json"))
		. model
	)
	check(Powertrain.drive_force(500.0 / 3.6, 1, model) == 0, "No drive above forward envelope")
	check(Powertrain.drive_force(-100.0 / 3.6, -1, model) == 0, "Reverse has separate envelope")
	check(Powertrain.road_speed(Vector3(0, -140, 0), Vector3.UP, 0) == 0, "Fall is not road speed")
	check(
		Powertrain.drive_force(35, 1, model) < Powertrain.drive_force(5, 1, model),
		"Force falls with speed"
	)
	check(Powertrain.drive_force(35, 1, model) * 35 <= 85000, "Wheel power below system power")
	check(
		absf(4 * Powertrain.brake_force(0, 1.5, 1605, 1.0 / 120, 1, 16000) - 1605 * 1.5) < 0.01,
		"Static brake contact forces balance grade gravity"
	)
	check(
		Powertrain.brake_force(0, 1.5, 1605, 1.0 / 120, 0, 16000) == 0,
		"Released brake cannot hold a grade"
	)
	for stock in [true, false]:
		var car := Vehicle.new()
		if stock:
			var config: Dictionary = JSON.parse_string(
				FileAccess.get_file_as_string("res://data/config/vehicle_lab.json")
			)
			config.components = config.components.filter(
				func(c: Dictionary) -> bool: return c.id in ["car", "driver"]
			)
			config.components[1].mass_kg = 75
			car.configuration_override = config
		car.stock_reference = stock
		car.position = Vector3(0, 0.2, 0)
		root.add_child(car)
		if physics_only:
			# Node callbacks animate occupants/visual wheels; Jolt integration remains active.
			car.set_process(false)
			car.set_physics_process(false)
		car.braking = 1
		await ticks(2.0)
		car.braking = 0
		car.throttle = 1
		var start_clock := car.elapsed
		var times: Dictionary = {}
		var peak := 0.0
		var minimum_contacts := 4
		var previous_speed := 0.0
		for i in range(simulation_hz * 150):
			await physics_frame
			var speed := car.road_speed_m_s() * 3.6
			peak = maxf(peak, speed)
			minimum_contacts = mini(minimum_contacts, car.diagnostic_contact_count)
			for threshold in [80, 100, 120]:
				if not times.has(threshold) and speed >= threshold:
					var fraction := (float(threshold) - previous_speed) / (speed - previous_speed)
					times[threshold] = (i + fraction) / simulation_hz
			previous_speed = speed
		check(
			absf(car.elapsed - start_clock - 150) < 0.02,
			"Actual integrator clock matches benchmark time"
		)
		var measured := {
			"mass_kg": car.mass,
			"time_0_100_s": times.get(100, -1),
			"time_80_120_s": times.get(120, -1) - times.get(80, -1),
			"peak_kmh": peak,
			"terminal_kmh": car.road_speed_m_s() * 3.6,
			"min_wheel_contacts": minimum_contacts,
			"height_m": car.position.y
		}
		check(minimum_contacts == 4, "Ground contact throughout straight run")
		check(car.position.y > -0.2 and car.position.y < 0.5, "No fall outside benchmark plane")
		check(peak < 177 and peak > (150 if stock else 130), "Finite forward terminal speed")
		if stock:
			check(
				absf(float(times.get(100, -100)) - 9.7) < 1.0,
				"Stock 0-100 within declared tolerance"
			)
			check(
				absf(float(measured.time_80_120_s) - 8.1) < 0.6,
				"Stock 80-120 within declared tolerance"
			)
			check(absf(float(measured.terminal_kmh) - 175) < 2, "Stock maximum within 2 km/h")
		else:
			check(
				float(measured.time_0_100_s) > float(results.stock.time_0_100_s),
				"Load slows acceleration"
			)
			check(
				float(measured.terminal_kmh) < float(results.stock.terminal_kmh),
				"Rig increases drag"
			)
		car.throttle = 0
		var before_coast := car.road_speed_m_s()
		await ticks(3)
		check(car.road_speed_m_s() < before_coast, "Lift-off coasts down")
		car.braking = 1
		await ticks(12)
		check(car.road_speed_m_s() < 0.3, "Service brake stops the car")
		measured["upright_after_braking"] = car.global_basis.y.dot(Vector3.UP)
		car.reset_requested = true
		await ticks(2)
		car.braking = 0
		car.throttle = -1
		await ticks(20)
		measured["reverse_kmh"] = car.road_speed_m_s() * 3.6
		check(car.linear_velocity.dot(-car.global_basis.z) < -1, "Reverse moves backward")
		check(float(measured.reverse_kmh) < 23, "Reverse cannot accelerate indefinitely")
		results["stock" if stock else "rig"] = measured
		car.queue_free()
		await process_frame
	results["checks"] = checks
	results["failures"] = failures
	results["physics_hz"] = simulation_hz
	results["scheduler_hz"] = Engine.physics_ticks_per_second
	results["simulation_time_scale"] = Engine.time_scale
	results["visual_animation_disabled"] = physics_only
	results["engine"] = Engine.get_version_info().string
	results["scope"] = "Stock-target longitudinal calibration and estimated rig; not full validation"
	DirAccess.make_dir_recursive_absolute(folder)
	var file := FileAccess.open(folder.path_join("report.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(results, "  ") + "\n")
	file.close()
	print(JSON.stringify(results))
	ground.queue_free()
	await process_frame
	quit(0 if failures.is_empty() else 1)


func ticks(seconds: float) -> void:
	for i in range(roundi(seconds * simulation_hz)):
		await physics_frame


func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)
