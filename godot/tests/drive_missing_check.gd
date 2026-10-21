extends SceneTree
## A clone without private generated data must show instructions, not fabricate a road.

const Pilot = preload("res://godot/scripts/drive_pilot.gd")


func _initialize() -> void:
	call_deferred("run")


func run() -> void:
	var scene := Pilot.new()
	scene.road_data_path = "build/nonexistent_drive_acceptance_input.json"
	root.add_child(scene)
	await physics_frame
	var ok := not scene.ready_ok and scene.vehicle == null and "assenti" in scene.hud.text
	print(JSON.stringify({"checks": 3, "passed": ok, "scope": "Missing local road data"}))
	if not ok:
		push_error("Missing-data road trial did not remain inactive with instructions")
	scene.queue_free()
	await process_frame
	await physics_frame
	quit(0 if ok else 1)
