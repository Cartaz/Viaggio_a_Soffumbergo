extends SceneTree

const StopState = preload("res://godot/scripts/parking_state.gd")
var checks := 0
var failures: Array[String] = []


func _initialize() -> void:
	var good := {
		"inside": true,
		"gates": true,
		"speed": 0.0,
		"angular_speed": 0.0,
		"upright": 1.0,
		"contacts": 4,
		"brake": 1.0,
		"incident": false
	}
	var bad := {
		"inside": false,
		"gates": false,
		"speed": 0.1,
		"angular_speed": 0.05,
		"upright": 0.95,
		"contacts": 3,
		"brake": 0.49,
		"incident": true
	}
	for key in bad:
		var stop := StopState.new()
		var sensors := good.duplicate()
		sensors[key] = bad[key]
		stop.update(sensors, 2)
		check(not stop.enter(), "Reject unsafe parking condition: " + key)
	var stop := StopState.new()
	check(not stop.enter() and not stop.leave(), "Cannot enter or leave before readiness")
	stop.update(good, 1)
	check(not stop.enter(), "Requires continuous stable hold")
	var moving := good.duplicate()
	moving.speed = 2
	stop.update(moving, 0.1)
	stop.update(good, 0.6)
	check(not stop.enter(), "Movement restarts hold clock")
	stop.update(good, 1)
	check(stop.enter(), "Sufficient continuous hold enables stop")
	check(stop.leave(), "Explicit return to driving supported")
	check(stop.phase == "approach" and stop.stable_s == 0, "Leaving clears readiness")
	print(JSON.stringify({"checks": checks, "failures": failures}))
	quit(0 if failures.is_empty() else 1)


func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)
