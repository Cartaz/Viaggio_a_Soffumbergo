extends SceneTree
## Real streamed Jolt road rays, comparison mode, body release and rendering.

const Scene = preload("res://godot/scenes/circuit_construction.tscn")
var checks := 0
var failures: Array[String] = []
var output := "build/construction_validation"
var capture := false
var ray_count := 0
var max_ray_error := 0.0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		capture = capture or arg == "--capture"
	call_deferred("run_check")


func run_check() -> void:
	var scene := Scene.instantiate()
	root.add_child(scene)
	check(scene.ready_ok, "Construction scene loads")
	if not scene.ready_ok:
		quit(1)
		return
	var path := ProjectSettings.globalize_path("res://").path_join(output + "/probes.json")
	var groups: Array = JSON.parse_string(FileAccess.get_file_as_string(path))
	for group in groups:
		var entry: Dictionary = scene.entries[group.id]
		scene.camera.position = Vector3(entry.offset_xz_m[0] + 64, 60, entry.offset_xz_m[1] + 64)
		await settle(scene)
		check(scene.road_residents.has(group.id), "Road collider resident " + str(group.id))
		var world: PhysicsDirectSpaceState3D = scene.get_world_3d().direct_space_state
		for point in group.points_m:
			var p := Vector3(point[0], point[1], point[2])
			var hit := world.intersect_ray(
				PhysicsRayQueryParameters3D.create(p + Vector3.UP * 5, p - Vector3.UP * 5, 4)
			)
			check(
				not hit.is_empty(),
				"Road reference ray " + str(p) if hit.is_empty() else "Road reference ray"
			)
			if not hit.is_empty():
				max_ray_error = maxf(max_ray_error, absf(hit.position.y - p.y))
				check(hit.normal.y > 0, "Upward road contact")
			ray_count += 1
	check(ray_count == 29877, "All axis and both cross-section references probed")
	check(max_ray_error < 0.003, "Jolt matches independent triangle interpolation")
	check(scene.max_residents < 80, "Bounded streamed terrain/road residency")
	check(scene.chunks_unloaded > 0, "Road trip releases distant chunks")
	check(scene.stream_errors.is_empty(), "No hash or load errors")
	scene.focus_issue()
	await settle(scene)
	if capture:
		await save_capture("construction_project")
	var target: Vector3 = scene.vector(scene.construction.report.issues[0].point_m)
	var world: PhysicsDirectSpaceState3D = scene.get_world_3d().direct_space_state
	check(
		not (
			world
			. intersect_ray(
				PhysicsRayQueryParameters3D.create(
					target + Vector3.UP * 10, target - Vector3.UP * 10, 4
				)
			)
			. is_empty()
		),
		"Design road before comparison"
	)
	scene.toggle_original()
	await settle(scene)
	check(
		scene.original_mode and scene.road_residents.is_empty(), "Original comparison removes road"
	)
	check(
		(
			world
			. intersect_ray(
				PhysicsRayQueryParameters3D.create(
					target + Vector3.UP * 10, target - Vector3.UP * 10, 4
				)
			)
			. is_empty()
		),
		"No stale road physics in original mode"
	)
	if capture:
		await save_capture("construction_original")
	scene.toggle_original()
	await settle(scene)
	check(not scene.road_residents.is_empty(), "Design restored after comparison")
	await check_drop(scene, target)
	scene.show_overview()
	await settle(scene)
	check(
		scene.residents.is_empty() and scene.road_residents.is_empty(),
		"Map releases fine terrain and road"
	)
	check(scene.overview_fits(), "Whole candidate fits the map")
	if capture:
		await save_capture("construction_overview")
	var result := {
		"passed": failures.is_empty(),
		"checks": checks,
		"failures": failures,
		"engine": Engine.get_version_info().string,
		"renderer": RenderingServer.get_video_adapter_name(),
		"road_rays": ray_count,
		"max_ray_error_m": max_ray_error,
		"max_residents": scene.max_residents,
		"chunks_loaded": scene.chunks_loaded,
		"chunks_unloaded": scene.chunks_unloaded,
		"capture": capture,
		"full_lap_driven": false,
		"scope": "construction geometry and contacts; not a vehicle lap"
	}
	DirAccess.make_dir_recursive_absolute(output)
	var file := FileAccess.open(output.path_join("godot_report.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "\t") + "\n")
	print(JSON.stringify(result))
	scene.queue_free()
	await process_frame
	quit(0 if failures.is_empty() else 1)


func settle(scene: Node3D) -> void:
	scene.refresh_stream()
	while not scene.pending.is_empty():
		scene.load_next()
	await process_frame
	await physics_frame
	await physics_frame
	check(scene.pending.is_empty(), "Streaming complete")


func check_drop(scene: Node3D, target: Vector3) -> void:
	var ball := RigidBody3D.new()
	ball.collision_mask = 4
	var shape := CollisionShape3D.new()
	shape.shape = SphereShape3D.new()
	ball.add_child(shape)
	ball.position = target + Vector3.UP * 2
	scene.add_child(ball)
	for i in range(180):
		await physics_frame
	check(ball.position.y > target.y - 1, "Dynamic body supported by constructed road")
	ball.queue_free()
	await physics_frame


func save_capture(name: String) -> void:
	DirAccess.make_dir_recursive_absolute(output)
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(output.path_join(name + ".png"))


func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error(message)
