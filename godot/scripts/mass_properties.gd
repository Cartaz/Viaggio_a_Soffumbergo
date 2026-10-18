class_name MassProperties
extends RefCounted
## SI units. Full design tensor retained; initial Godot body uses its diagonal.


static func calculate(parts: Array) -> Dictionary:
	var total := 0.0
	var com := Vector3.ZERO
	for item in parts:
		var m := float(item.mass_kg)
		var p := vector(item.position_m)
		assert(m > 0.0)
		total += m
		com += m * p
	assert(total > 0.0)
	com /= total
	var tensor := Basis(Vector3.ZERO, Vector3.ZERO, Vector3.ZERO)
	for item in parts:
		var m := float(item.mass_kg)
		var r := vector(item.position_m) - com
		var s := vector(item.box_m)
		var diagonal := (
			Vector3(s.y * s.y + s.z * s.z, s.x * s.x + s.z * s.z, s.x * s.x + s.y * s.y) * m / 12.0
		)
		for i in range(3):
			for j in range(3):
				var value := -m * r[i] * r[j]
				if i == j:
					value += m * r.length_squared() + diagonal[i]
				tensor[i][j] += value
	return {
		"mass": total,
		"com": com,
		"tensor": tensor,
		"diagonal": Vector3(tensor.x.x, tensor.y.y, tensor.z.z)
	}


static func vector(values: Array) -> Vector3:
	return Vector3(float(values[0]), float(values[1]), float(values[2]))
