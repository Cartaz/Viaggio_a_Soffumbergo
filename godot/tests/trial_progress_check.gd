extends SceneTree
## Directional crossing regressions, independent of private DTM or vehicle assets.

const Progress = preload("res://godot/scripts/trial_progress.gd")
var checks := 0
var failures: Array[String] = []


func _initialize() -> void:
	var trial := Progress.new()
	var gates: Array[Dictionary] = [
		{"origin": Vector3(10, 0, 0), "forward": Vector3.RIGHT},
		{"origin": Vector3(20, 0, 0), "forward": Vector3.RIGHT}
	]
	trial.configure(gates, Vector3.ZERO, 2.25)
	check(trial.valid and trial.next_gate == 0, "New attempt is eligible")
	check(not trial.can_arrive(), "No arrival without checkpoints")
	check(not trial.sample(Vector3(9, 0, 0), 1, true), "Proximity is not crossing")
	check(trial.sample(Vector3(11, 0, 0), 1, true), "Forward swept crossing accepted")
	check(trial.next_gate == 1, "Exactly one gate advanced")
	check(not trial.sample(Vector3(9, 0, 0), 1, true), "Reverse crossing rejected")
	check(not trial.sample(Vector3(11, 0, 0), 1, true), "Repeated gate cannot score twice")
	trial.sample(Vector3(19, 0, 3), 1, true)
	check(not trial.sample(Vector3(21, 0, 3), 1, true), "Crossing outside gate width rejected")
	trial.sample(Vector3(19, 3, 0), 1, true)
	check(not trial.sample(Vector3(21, 3, 0), 1, true), "Passing above surface rejected")
	trial.sample(Vector3(19, 0, 0), 1, true)
	check(not trial.sample(Vector3(21, 0, 0), 1, false), "Overturned crossing rejected")
	trial.sample(Vector3(19, 0, 0), 1, true)
	check(trial.sample(Vector3(21, 0, 0), 1, true), "Recrossing next gate accepted")
	check(trial.can_arrive() and trial.valid, "Ordered gates permit valid arrival")
	trial.fail("Test incident")
	trial.fail("Second incident")
	check(trial.incident == "Test incident", "First incident retained")
	check(not trial.can_arrive() and not trial.valid, "Incident blocks arrival")
	var clock := trial.elapsed_s
	trial.recover(Vector3(22, 0, 0))
	check(trial.next_gate == 2 and not trial.valid, "Recovery retains gates and invalidity")
	check(trial.elapsed_s == clock, "Recovery retains elapsed time")
	check(trial.can_arrive(), "Recovered run may finish as practice")
	trial.new_attempt(Vector3.ZERO)
	check(trial.valid and trial.next_gate == 0 and trial.elapsed_s == 0, "New run clears progress")
	trial.sample(Vector3(19, 0, 0), 1, true)
	# The swept segment legitimately crossed gate 1; test wrong order with rebase.
	trial.new_attempt(Vector3(19, 0, 0))
	check(not trial.sample(Vector3(21, 0, 0), 1, true), "Later gate cannot replace first gate")
	check(not trial.can_arrive(), "Missing first gate blocks arrival")
	trial.new_attempt(Vector3.ZERO)
	check(not trial.sample(Vector3(11, 0, 0), 0.01, true), "Teleport cannot cross gate")
	check(not trial.valid and not trial.incident.is_empty(), "Teleport invalidates attempt")
	trial.new_attempt(Vector3(9, 0, 0))
	check(trial.sample(Vector3(11, 0, 0), 0.05, true), "Fast physical crossing does not tunnel")
	trial.new_attempt(Vector3.ZERO)
	check(not trial.sample(Vector3(NAN, 0, 0), 1, true), "Nonfinite position rejected")
	check(not trial.valid, "Invalid samples invalidate run")
	trial.new_attempt(Vector3.ZERO)
	check(not trial.sample(Vector3.ZERO, 0, true), "Zero timestep rejected")
	print(JSON.stringify({"checks": checks, "failures": failures}))
	quit(0 if failures.is_empty() else 1)


func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)
