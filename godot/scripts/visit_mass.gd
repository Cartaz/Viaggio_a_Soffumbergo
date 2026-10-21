extends RefCounted
## One owner per occupant. Transfers use physical COM velocities, not visual origins.

const Properties = preload("res://godot/scripts/mass_properties.gd")


static func parts(car: RigidBody3D, aboard: bool) -> Array:
	var result: Array = []
	for part in car.config.components:
		if aboard or part.id not in ["driver", "passenger"]:
			result.append(part)
	return result


static func set_aggregate(car: RigidBody3D, aboard: bool) -> void:
	var previous_com: Vector3 = car.center_of_mass
	var properties := Properties.calculate(parts(car, aboard))
	car.linear_velocity += car.angular_velocity.cross(
		car.global_basis * (properties.com - previous_com)
	)
	car.properties = properties
	car.mass = properties.mass
	car.center_of_mass = properties.com
	car.inertia = properties.diagonal


static func momentum(car: RigidBody3D, visitors: Array) -> Vector3:
	var value := car.mass * car.linear_velocity
	for visitor: RigidBody3D in visitors:
		value += visitor.mass * visitor.linear_velocity
	return value


static func merge(car: RigidBody3D, visitors: Array) -> void:
	var linear := momentum(car, visitors)
	var full := Properties.calculate(parts(car, true))
	var center: Vector3 = car.global_transform * full.com
	var angular := world_inertia(car) * car.angular_velocity
	angular += (car.global_transform * car.center_of_mass - center).cross(
		car.mass * car.linear_velocity
	)
	for visitor: RigidBody3D in visitors:
		angular += world_inertia(visitor) * visitor.angular_velocity
		angular += (visitor.global_position - center).cross(visitor.mass * visitor.linear_velocity)
	set_aggregate(car, true)
	car.linear_velocity = linear / car.mass
	car.angular_velocity = world_inertia(car).inverse() * angular
	for visitor: RigidBody3D in visitors:
		visitor.set_physics_process(false)
		visitor.collision_layer = 0
		visitor.collision_mask = 0
		visitor.freeze = true
		visitor.queue_free()


static func world_inertia(body: RigidBody3D) -> Basis:
	var diagonal := Basis.from_scale(body.inertia)
	return body.global_basis * diagonal * body.global_basis.transposed()
