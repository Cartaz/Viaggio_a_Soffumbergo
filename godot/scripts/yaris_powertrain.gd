class_name YarisPowertrain
extends RefCounted
## Effective wheel-force envelope. Estimates and official targets are distinct in JSON.


static func drive_force(speed: float, pedal: float, model: Dictionary) -> float:
	var reverse := pedal < 0.0
	var direction := -1.0 if reverse else 1.0
	var along := maxf(0.0, speed * direction)
	var limit := float(model.reverse_force_n if reverse else model.launch_force_n)
	var power := float(model.reverse_power_w if reverse else model.wheel_power_w)
	var start := float(model.reverse_governor_start_kmh if reverse else model.governor_start_kmh)
	var cutoff := float(model.reverse_governor_cutoff_kmh if reverse else model.governor_cutoff_kmh)
	var fraction := clampf((along * 3.6 - start) / (cutoff - start), 0.0, 1.0)
	var governor := 1.0 - fraction * fraction * (3.0 - 2.0 * fraction)
	return (
		direction
		* clampf(absf(pedal), 0.0, 1.0)
		* minf(limit, power / maxf(along, float(model.regularization_m_s)))
		* governor
	)


static func road_speed(velocity: Vector3, normal: Vector3, contacts: int) -> float:
	# A fall must never appear as increasing road speed.
	if contacts == 0:
		return Vector2(velocity.x, velocity.z).length()
	return velocity.slide(normal.normalized()).length()


static func drag(velocity: Vector3, model: Dictionary, stock: bool) -> Vector3:
	var area := float(model.stock_drag_area_m2)
	if not stock:
		area += float(model.rig_extra_drag_area_m2)
	return -0.5 * float(model.air_density_kg_m3) * area * velocity.length() * velocity


static func brake_force(
	speed: float,
	gravity_along: float,
	mass_kg: float,
	dt: float,
	pedal: float,
	total_limit: float,
	drive: float = 0.0
) -> float:
	var limit := clampf(pedal, 0, 1) * total_limit * 0.25
	if absf(speed) >= 0.5:
		return limit * signf(speed)
	# Contact impulse plus grade/drive balance, capped by brake torque and later tyre grip.
	# Unlike viscous regularization this can hold a slope at zero speed without teleporting.
	# Underrelax the coupled four-contact stop; retain full static gravity balance.
	return clampf(mass_kg * 0.25 * (speed / (4 * dt) + gravity_along) + drive, -limit, limit)
