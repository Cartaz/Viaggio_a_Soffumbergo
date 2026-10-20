extends SceneTree
## Visit every OSM sector in real Jolt, verify residency, rays, unloads and stable LOD collision.

const Circuit = preload("res://godot/scenes/circuit.tscn")
var checks := 0
var failures: Array[String] = []
var output := "build/circuit_validation"
var capture := false
var expect_missing := false
var max_ray_error := 0.0
var visits: Array[Dictionary] = []
var ground_rays := 0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			output = arg.trim_prefix("--output=")
		capture = capture or arg == "--capture"
		expect_missing = expect_missing or arg == "--expect-missing"
	call_deferred("run_check")


func run_check() -> void:
	var scene := Circuit.instantiate()
	root.add_child(scene)
	if not scene.ready_ok:
		check(
			expect_missing and scene.hud.text.contains("DTM locale assente"),
			"Actionable missing-data mode"
		)
		write_report({"missing_data_mode": true})
		scene.queue_free()
		await process_frame
		quit(0 if failures.is_empty() else 1)
		return
	check(not expect_missing, "Circuit actually loaded")
	check(scene.entries.size() == 352, "352 corridor sectors")
	check(scene.building_root.get_child_count() == 91, "Valle OSM content shares the frame")
	await settle(scene)
	check(scene.residents.size() > 0 and scene.residents.size() < 80, "Detail residency is bounded")
	var first: String = scene.residents.keys()[0]
	await check_collision(scene, first)
	for index in range(7):
		var route: Dictionary = scene.data.route[index]
		var points: Array = route.points_m
		for start in range(0, points.size(), 96):
			var group := points.slice(start, mini(start + 96, points.size()))
			var target := Vector3(group[0][0], group[0][1], group[0][2])
			scene.camera.position = target + Vector3(0, 80, 0)
			scene.camera.look_at(target, Vector3.FORWARD)
			await settle(scene)
			await check_route_rays(scene, group)
		check(scene.residents.size() <= 80, "Bounded residents " + str(route.sector))
		check(
			(
				scene.find_children("*", "StaticBody3D", true, false).size()
				== scene.residents.size() + 91
			),
			"Unloaded physics bodies actually freed"
		)
		visits.append({"sector": route.sector, "residents": scene.residents.size()})
	check(scene.chunks_unloaded > 0, "Moving through the loop actually unloads collision chunks")
	check(scene.stream_errors.is_empty(), "No chunk hash/load errors")
	check(max_ray_error < 0.003, "Route references agree with Jolt ground")
	check(ground_rays == 9966, "Every densified candidate point probed in Jolt")
	await check_drop(scene)
	# A map view removes near collision but keeps the coarse full corridor.
	scene.show_overview()
	await settle(scene)
	check(scene.overview_fits(), "Map view frames the entire terrain below its controls")
	check(scene.residents.is_empty(), "Far map view unloads detailed collisions")
	check(scene.overview.size() == 352, "Overview retains the entire corridor")
	check(
		scene.find_children("*", "StaticBody3D", true, false).size() == 91,
		"Overview has no terrain collision bodies"
	)
	if capture:
		await save_capture("circuit_overview")
		scene.camera.position = Vector3(220, 220, 280)
		scene.camera.look_at(Vector3.ZERO)
		await settle(scene)
		await save_capture("circuit_valle")
		var key := InputEventKey.new()
		key.keycode = KEY_F1
		key.pressed = true
		scene._unhandled_input(key)
		await settle(scene)
		await save_capture("circuit_faedis")
	write_report(
		{
			"missing_data_mode": false,
			"engine": Engine.get_version_info().string,
			"renderer": RenderingServer.get_video_adapter_name(),
			"route_ray_max_error_m": max_ray_error,
			"ground_ray_count": ground_rays,
			"initial_load_ms": scene.load_ms,
			"max_single_chunk_build_ms": scene.max_build_ms,
			"max_residents": scene.max_residents,
			"chunks_loaded": scene.chunks_loaded,
			"chunks_unloaded": scene.chunks_unloaded,
			"visits": visits,
			"captures": capture
		}
	)
	scene.queue_free()
	await process_frame
	quit(0 if failures.is_empty() else 1)


func settle(scene: Node3D) -> void:
	scene.refresh_stream()
	var frames := 0
	while not scene.pending.is_empty() and frames < 240:
		await process_frame
		frames += 1
	check(scene.pending.is_empty(), "Streaming queue drains within 240 frames")
	await physics_frame
	await physics_frame


func check_collision(scene: Node3D, id: String) -> void:
	var chunk: Node3D = scene.residents[id]
	var body := chunk.get_child(0) as StaticBody3D
	var shape := (body.get_child(0) as CollisionShape3D).shape
	chunk.select_lod(0)
	var detailed: Mesh = chunk.visual.mesh
	chunk.select_lod(2)
	check(chunk.visual.mesh != detailed, "Visual LOD switches meshes")
	check(
		(body.get_child(0) as CollisionShape3D).shape == shape,
		"LOD retains the exact collision shape"
	)
	check(chunk.triangle_counts[0] > chunk.triangle_counts[2] * 8, "LOD triangle reduction")
	await physics_frame


func check_route_rays(scene: Node3D, points: Array) -> void:
	var center: Vector3 = scene.camera.position
	var world: PhysicsDirectSpaceState3D = scene.get_world_3d().direct_space_state
	var count := 0
	for p in points:
		var point := Vector3(p[0], p[1], p[2])
		if Vector2(point.x - center.x, point.z - center.z).length() > 220:
			continue
		var query := PhysicsRayQueryParameters3D.create(
			point + Vector3.UP * 100, point - Vector3.UP * 100, 1
		)
		var hit := world.intersect_ray(query)
		check(not hit.is_empty(), "Candidate ground ray")
		if not hit.is_empty():
			max_ray_error = maxf(max_ray_error, absf(hit.position.y - point.y))
			check(hit.normal.y > 0, "Ground normals face up")
		count += 1
		ground_rays += 1
	check(count == points.size(), "All grouped points lie inside streamed collision area")


func check_drop(scene: Node3D) -> void:
	var point: Vector3 = scene.camera.position
	var world: PhysicsDirectSpaceState3D = scene.get_world_3d().direct_space_state
	var hit := world.intersect_ray(
		PhysicsRayQueryParameters3D.create(point + Vector3.UP * 100, point - Vector3.UP * 200, 1)
	)
	check(not hit.is_empty(), "Falling-body test has ground")
	if hit.is_empty():
		return
	var ball := RigidBody3D.new()
	ball.collision_mask = 1
	var shape := CollisionShape3D.new()
	shape.shape = SphereShape3D.new()
	ball.add_child(shape)
	ball.position = hit.position + Vector3.UP * 4
	scene.add_child(ball)
	for i in range(360):
		await physics_frame
	check(ball.position.y > hit.position.y - 3, "Jolt body does not fall through ground")
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


func write_report(result: Dictionary) -> void:
	result["checks"] = checks
	result["failures"] = failures
	result["scope"] = "Streamed DTM inspection corridor; not a driven journey or representative FPS"
	DirAccess.make_dir_recursive_absolute(output)
	var file := FileAccess.open(output.path_join("godot_report.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "\t") + "\n")
	print(JSON.stringify(result))
