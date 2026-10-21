extends SceneTree
## Private assembled snapshot for Blender verification; never a public asset.

const Scene = preload("res://godot/scenes/circuit_practice.tscn")


func _initialize() -> void:
	call_deferred("run")


func run() -> void:
	var scene := Scene.instantiate()
	scene.automated = true
	root.add_child(scene)
	for i in range(600):
		if not scene.switching:
			break
		await process_frame
	if not scene.ready_ok or scene.switching:
		push_error("Approved circuit scene not ready")
		quit(1)
		return
	for i in range(20):
		await physics_frame
	var result := preload("res://godot/tests/final_vehicle_guard.gd").inspect(scene.vehicle)
	if not bool(result.approved_assembly_loaded):
		push_error("Final Yaris, pirate rig and both mice required")
		quit(1)
		return
	var output := ProjectSettings.globalize_path("res://").path_join(
		"build/final_vehicle_validation"
	)
	DirAccess.make_dir_recursive_absolute(output)
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	var error := document.append_from_scene(scene.vehicle, state)
	if error == OK:
		error = document.write_to_filesystem(state, output.path_join("final_vehicle.glb"))
	result["export_error"] = error
	result["passed"] = error == OK
	var file := FileAccess.open(output.path_join("snapshot_report.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "\t") + "\n")
	print(JSON.stringify(result))
	scene.queue_free()
	await process_frame
	await physics_frame
	quit(0 if error == OK else 1)
