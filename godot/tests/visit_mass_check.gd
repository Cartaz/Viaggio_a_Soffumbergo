extends SceneTree
## Transfer invariants over twenty round trips, including nonzero COM velocities.

const Vehicle = preload("res://godot/scripts/vehicle_lab.gd")
const Actor = preload("res://godot/scripts/visit_actor.gd")
const Transfer = preload("res://godot/scripts/visit_mass.gd")
var checks := 0
var failures: Array[String] = []


func _initialize() -> void:
	call_deferred("run")


func run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var car := Vehicle.new()
	car.freeze = true
	world.add_child(car)
	var original_mass := car.mass
	var original_com := car.center_of_mass
	for cycle in range(20):
		car.linear_velocity = Vector3(0.04, 0.03, -0.02)
		car.angular_velocity = Vector3(0.01, -0.01, 0.02)
		var before := car.mass * car.linear_velocity
		var actors: Array = []
		for part in car.config.components:
			if part.id not in ["driver", "passenger"]:
				continue
			var actor := Actor.new()
			actor.vehicle = car
			actor.mass = part.mass_kg
			actor.position = (
				car.global_transform
				* Vector3(part.position_m[0], part.position_m[1], part.position_m[2])
			)
			actor.linear_velocity = (
				car.linear_velocity
				+ car.angular_velocity.cross(
					actor.position - car.global_transform * car.center_of_mass
				)
			)
			world.add_child(actor)
			actors.append(actor)
		Transfer.set_aggregate(car, false)
		check(
			(Transfer.momentum(car, actors) - before).length() < 0.001, "Split preserves momentum"
		)
		check(
			absf(car.mass + actors[0].mass + actors[1].mass - original_mass) < 0.001,
			"Unique mass owner after split"
		)
		actors[0].linear_velocity += Vector3(0.01, 0.02, 0.03)
		var combined := Transfer.momentum(car, actors)
		Transfer.merge(car, actors)
		check(
			(car.mass * car.linear_velocity - combined).length() < 0.001,
			"Merge preserves actual combined momentum"
		)
		check(
			car.mass == original_mass and car.center_of_mass == original_com,
			"Original aggregate restored exactly"
		)
		check(
			actors[0].freeze and not actors[0].is_physics_processing(),
			"Inactive bodies cannot double apply support after merge"
		)
	print(JSON.stringify({"checks": checks, "failures": failures, "cycles": 20}))
	world.queue_free()
	await process_frame
	await physics_frame
	quit(0 if failures.is_empty() else 1)


func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)
