extends SceneTree
## Actual engine bench to execute on the connected PC, not yet run.
## godot --headless --path . --script res://godot/tests/static_bench.gd -- --hz=120

const VehicleScript = preload("res://godot/scripts/vehicle_lab.gd")


func _initialize() -> void:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--hz="):
			var hz := int(argument.trim_prefix("--hz="))
			if hz not in [60, 120, 240]:
				push_error("Supported bench rates: 60, 120, 240")
				quit(2)
				return
			Engine.physics_ticks_per_second = hz
	call_deferred("run_bench")


func run_bench() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var ground := StaticBody3D.new()
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(100, 0.4, 100)
	collision.shape = shape
	collision.position.y = -0.2
	ground.add_child(collision)
	world.add_child(ground)
	var vehicle = VehicleScript.new()
	vehicle.position.y = 0.2
	world.add_child(vehicle)
	await create_timer(8.0, true, true).timeout
	var load_total := 0.0
	var samples := Engine.physics_ticks_per_second * 2
	for i in range(samples):
		await physics_frame
		for load in vehicle.wheel_loads:
			load_total += load
	var average := load_total / samples
	var weight := float(vehicle.mass) * 9.81
	var error := absf(average - weight) / weight
	var up_dot: float = vehicle.global_basis.y.dot(Vector3.UP)
	var passed: bool = (
		error < 0.02
		and vehicle.linear_velocity.length() < 0.02
		and vehicle.angular_velocity.length() < 0.02
		and up_dot > 0.999
	)
	print(
		"STATIC ENGINE BENCH: ",
		JSON.stringify(
			{
				"hz": Engine.physics_ticks_per_second,
				"mean_support_N": average,
				"weight_N": weight,
				"relative_error": error,
				"velocity_m_s": vehicle.linear_velocity.length(),
				"up_dot": up_dot,
				"passed": passed
			}
		)
	)
	quit(0 if passed else 1)
