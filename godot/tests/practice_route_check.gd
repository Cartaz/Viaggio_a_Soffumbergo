extends SceneTree

const Route = preload("res://godot/scripts/practice_route.gd")
var checks := 0
var failures: Array[String] = []


func _initialize() -> void:
	var route := Route.new()
	route.configure([[0, 0, 0], [100, 10, 0], [100, 10, 2], [0, 0, 2]])
	check(route.at(-3) == Vector3.ZERO, "Negative station clamps")
	check(route.at(300) == Vector3(0, 0, 2), "End station clamps")
	check(route.at(50).distance_to(Vector3(50, 5, 0)) < 1e-5, "Binary interpolation")
	for i in range(90):
		route.sample(Vector3(i, i * 0.1, 1.5), 3)
		check(
			absf(route.progress - i) < 0.001,
			"Nearby returning branch cannot steal forward progress"
		)
	for i in range(90, 80, -1):
		route.sample(Vector3(i, i * 0.1, 0), 3)
		check(absf(route.progress - i) < 0.001, "Ordinary short reversing remains local")
	route.configure([[0, 0, 0], [100, 0, 0], [100, 0, 2], [0, 0, 2]])
	route.sample(Vector3(90, 0, 2), 3)
	check(route.progress < 13, "Discontinuity cannot acquire distant branch")
	print(JSON.stringify({"checks": checks, "failures": failures}))
	quit(0 if failures.is_empty() else 1)


func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)
