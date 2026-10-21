extends SceneTree
## A clone without private generated data must show instructions, not fabricate a road.

const Pilot = preload("res://godot/scripts/drive_pilot.gd")
const Parking = preload("res://godot/scripts/parking_pilot.gd")


func _initialize() -> void:
	call_deferred("run")


func run() -> void:
	var all_ok := true
	for scene: Node3D in [Pilot.new(), Parking.new()]:
		scene.road_data_path = "build/nonexistent_drive_acceptance_input.json"
		root.add_child(scene)
		await physics_frame
		var ok: bool = not scene.ready_ok and scene.vehicle == null and "assenti" in scene.hud.text
		all_ok = all_ok and ok
		if not ok:
			push_error("Missing-data scene did not remain inactive with instructions")
		scene.queue_free()
		await process_frame
		await physics_frame
	print(
		JSON.stringify(
			{"checks": 6, "passed": all_ok, "scope": "Missing local drive and parking data"}
		)
	)
	quit(0 if all_ok else 1)
