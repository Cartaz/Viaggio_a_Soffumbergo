extends SceneTree
## Check every coded tile with the approved vehicle assembly active in practice.

const Scene = preload("res://godot/scenes/circuit_practice.tscn")
const Guard = preload("res://godot/tests/final_vehicle_guard.gd")
var failures: Array[String] = []
var checks := 0
var output := "build/environment_validation"
var capture := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			output = arg.trim_prefix("--output=")
		capture = capture or arg == "--capture"
	call_deferred("run")


func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error(message)


func run() -> void:
	var scene := Scene.instantiate()
	scene.automated = true
	root.add_child(scene)
	for i in range(600):
		if scene.ready_ok and is_instance_valid(scene.vehicle) and not scene.switching:
			break
		await process_frame
	check(scene.ready_ok and not scene.switching, "Practice initialized")
	if not failures.is_empty():
		quit(1)
		return
	var guard := Guard.inspect(scene.vehicle)
	check(bool(guard.approved_assembly_loaded), "Approved Yaris, pirate rig, Bernie and Bianca")
	check(bool(guard.visual_process_active), "Final vehicle visual processing active")
	check(bool(guard.visual_physics_process_active), "Final vehicle physics active")
	if not failures.is_empty():
		quit(1)
		return
	scene.vehicle.braking = 1
	var layer: Node3D = scene.environment_layer
	check(layer.enabled, "Catalog accepted for current construction")
	check(scene.data.buildings.is_empty(), "Legacy Valle boxes replaced without duplicates")
	if not failures.is_empty():
		quit(1)
		return
	var visited: Dictionary = {}
	var max_position_error := 0.0
	var total_primitives := 0
	var total_batches := 0
	for id: String in layer.catalog.tiles:
		var parent := Node3D.new()
		var entry: Dictionary = scene.entries[id]
		parent.position = Vector3(entry.offset_xz_m[0], 0, entry.offset_xz_m[1])
		scene.add_child(parent)
		layer.attach_tile(parent, id)
		var holder := parent.get_node("EnvironmentPlaceholders")
		check(
			holder.find_children("*", "CollisionObject3D", true, false).is_empty(),
			"No guessed collider " + id
		)
		var instance_count := 0
		for child in holder.get_children():
			if child is MultiMeshInstance3D:
				instance_count += child.multimesh.instance_count
				total_batches += 1
			else:
				var item: Dictionary = child.get_meta("placeholder")
				check(not visited.has(item.code), "Unique runtime identity " + str(item.code))
				visited[item.code] = true
				var point: Array = item.position_m
				var actual: Vector3 = child.global_position
				var error := Vector3(point[0], point[1], point[2]).distance_to(actual)
				max_position_error = maxf(max_position_error, error)
				check(error < 0.002, "Georeferenced placement " + str(item.code))
				check(not str(item.description).is_empty(), "Description " + str(item.code))
		var expected := 0
		for code in layer.catalog.tiles[id]:
			expected += layer.objects[code].primitives.size()
		check(instance_count == expected, "Complete primitive recipe " + id)
		total_primitives += expected
		parent.free()
		# Final characters keep their ordinary process/physics callbacks throughout.
		await process_frame
	var old_codes: Array[String] = layer.active_codes()
	check(old_codes.is_empty(), "Released temporary tile markers")
	# Rebuild resident markers after temporary duplicate inspection fixtures were freed.
	for id: String in scene.residents:
		var chunk: Node3D = scene.residents[id]
		var previous := chunk.get_node_or_null("EnvironmentPlaceholders")
		if previous != null:
			previous.free()
		layer.attach_tile(chunk, id)
	check(not layer.active_codes().is_empty(), "Resident environment visible")
	var ev := InputEventKey.new()
	ev.keycode = KEY_F10
	ev.pressed = true
	layer._unhandled_input(ev)
	check(layer.show_codes and layer.labels.visible, "F10 exposes codes and descriptions")
	var snapshots: Array[String] = []
	if capture:
		for index in [5, 0]:
			await scene.select_section(index, 185.0 if index == 5 else 0.0)
			scene.vehicle.braking = 1
			for i in range(24):
				await process_frame
			await RenderingServer.frame_post_draw
			var file := "valle.png" if index == 5 else "faedis.png"
			DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output))
			root.get_texture().get_image().save_png(output.path_join(file))
			snapshots.append(file)
	var final_guard := Guard.inspect(scene.vehicle)
	check(
		bool(final_guard.approved_assembly_loaded), "Approved assembly still visible after checks"
	)
	check(scene.stream_errors.is_empty(), "No stream errors")
	var report := {
		"status": "passed" if failures.is_empty() else "failed",
		"checks": checks,
		"failures": failures,
		"catalog_build_id": layer.catalog.build_id,
		"catalog_sha256": FileAccess.get_sha256("res://data/geography/circuit_placeholders.json"),
		"approved_vehicle": final_guard,
		"tiles_checked": layer.catalog.tiles.size(),
		"unique_objects_checked": visited.size(),
		"primitives_checked": total_primitives,
		"batches_checked": total_batches,
		"max_position_error_m": max_position_error,
		"snapshots": snapshots,
		"continuous_lap_tested": false,
		"terrain_or_vehicle_settings_changed": false
	}
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output))
	var file := FileAccess.open(output.path_join("report.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	print(JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)
