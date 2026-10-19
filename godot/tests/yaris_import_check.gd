extends SceneTree
## Actual imported scene/transform checks, not an artistic similarity score.

var failures := 0


func _initialize() -> void:
	call_deferred("run_checks")


func run_checks() -> void:
	var scene := load("res://godot/scenes/yaris_visual.tscn") as PackedScene
	var visual := scene.instantiate() as YarisVisual
	root.add_child(visual)
	for wheel_id in YarisVisual.WHEEL_IDS:
		check(visual.find_child("Door_" + wheel_id, true, false) != null, "Door " + wheel_id)
		check(visual.find_child("Wheel_" + wheel_id, true, false) != null, "Wheel " + wheel_id)
	var fl := visual.find_child("Steer_FL", true, false) as Node3D
	var rl := visual.find_child("Steer_RL", true, false) as Node3D
	check(absf(fl.position.y - 0.31045) < 0.00001, "Wheel radius/ground height")
	check(absf(fl.position.distance_to(rl.position) - 2.56) < 0.0001, "Axle spacing")
	var initial := fl.transform
	var anchors: Array[Vector3] = [
		Vector3(-0.759, 0.62, -1.28),
		Vector3(0.759, 0.62, -1.28),
		Vector3(-0.757, 0.62, 1.28),
		Vector3(0.757, 0.62, 1.28)
	]
	visual.update_running_gear(anchors, PackedFloat32Array([0.3, 0.3, 0.3, 0.3]), 0.2, 3, 0.1)
	check(not fl.transform.is_equal_approx(initial), "Suspension and steering update")
	var spin := visual.find_child("Wheel_FL", true, false) as Node3D
	check(absf(spin.rotation.x) > 0.1, "Wheel rolls")
	visual.set_door_open("FL", 1.0)
	var door := visual.find_child("Door_FL", true, false) as Node3D
	check(absf(door.rotation.y + 1.05) < 0.0001, "Driver hinge")
	visual.set_hatch_open(1.0)
	var hatch := visual.find_child("Hatch", true, false) as Node3D
	check(absf(hatch.rotation.x + 1.05) < 0.0001, "Hatch hinge")
	check(
		visual.find_children("*", "CollisionObject3D", true, false).is_empty(),
		"Visual adds no physical bodies"
	)
	print("YARIS_IMPORT_CHECK failures=", failures)
	visual.queue_free()
	quit(1 if failures else 0)


func check(condition: bool, label: String) -> void:
	if not condition:
		failures += 1
		push_error(label)
