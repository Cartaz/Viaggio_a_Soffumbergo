class_name WheelForces
extends RefCounted
## Passive force kernels. Reference numerical tests live in tools/coffa/physics.py.
## Matching mathematics is not an engine test.


static func combined(longitudinal: float, lateral: float, normal: float, mu: float) -> Vector2:
	var wanted := Vector2(longitudinal, lateral)
	var budget := maxf(0.0, normal * mu)
	if wanted.length() > budget:
		return wanted.normalized() * budget
	return wanted


static func spring(compression: float, speed: float, settings: Dictionary) -> float:
	var bump := maxf(
		0.0, compression - (float(settings.rest_length_m) - float(settings.bump_length_m))
	)
	return maxf(
		0.0,
		(
			float(settings.spring_n_m) * compression
			+ float(settings.damping_ns_m) * speed
			+ float(settings.bump_spring_n_m) * bump
		)
	)
