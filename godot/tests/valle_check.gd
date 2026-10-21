extends SceneTree
## Real Jolt rays and falling-body test, LOD independence, GPU capture when requested.

const Valle = preload("res://godot/scenes/valle.tscn")
var failures: Array[String] = []
var checks := 0
var output := "build/valle_validation"
var capture := false
var expect_missing := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			output = arg.trim_prefix("--output=")
		if arg == "--capture":
			capture = true
		if arg == "--expect-missing":
			expect_missing = true
	call_deferred("run_check")


func run_check() -> void:
	var scene := Valle.instantiate()
	root.add_child(scene)
	if not scene.ready_ok:
		check(expect_missing, "Real terrain loaded unless explicitly testing missing data")
		check(
			scene.hud.text.contains("DTM locale assente"), "Missing DTM has an actionable message"
		)
		write_report({"missing_data_mode": true})
		quit(1 if failures.size() else 0)
		return
	check(not expect_missing, "Missing-data fixture is actually missing")
	await physics_frame
	await physics_frame
	check(scene.sectors.size() == 36, "36 terrain sectors")
	check(scene.building_root.get_child_count() == 91, "91 OSM blockouts")
	check(scene.road_root.get_child_count() == 266, "266 clipped OSM segments")
	var max_ray_error := 0.0
	var world: PhysicsDirectSpaceState3D = scene.get_world_3d().direct_space_state
	check_buildings(scene, world)
	for sector in scene.sectors:
		for mesh in sector.meshes:
			check(mesh.get_surface_count() == 1, "LOD mesh uploaded with valid arrays")
		var samples: Dictionary = scene.data.sectors[scene.sectors.find(sector)]
		var point: Vector3 = sector.position + Vector3(32, samples.heights_m[16 * 65 + 16], 32)
		var hit := cast(world, point, 1)
		check(not hit.is_empty(), "Terrain ray " + sector.name)
		if not hit.is_empty():
			max_ray_error = maxf(max_ray_error, absf(hit.position.y - point.y))
			check(hit.normal.y > 0, "Ground normal up " + sector.name)
		check(sector.triangle_counts[0] > sector.triangle_counts[2] * 8, "LOD reduces triangles")
		var near: Vector3 = sector.center
		sector.update_lod(near, scene.data.config.lod_distances_m)
		check(sector.current_lod == 0, "Near LOD selected")
		sector.update_lod(near + Vector3(1000, 0, 0), scene.data.config.lod_distances_m)
		check(sector.current_lod == 2, "Far LOD selected")
		var far_hit := cast(world, point, 1)
		check(not far_hit.is_empty(), "Far LOD keeps collision")
		if not hit.is_empty() and not far_hit.is_empty():
			check(
				hit.position.distance_to(far_hit.position) < 0.0001, "Collision independent of LOD"
			)
	check(max_ray_error < 0.002, "Projected coordinates and ray heights agree")
	# A real dynamic body must settle on the concave terrain, not fall through a backface.
	var ground_point := Vector3(-160, 0, 160)
	var ground := cast(world, ground_point, 1)
	var ball := RigidBody3D.new()
	ball.collision_mask = 1
	var shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.5
	shape.shape = sphere
	ball.add_child(shape)
	check(not ground.is_empty(), "Drop test has ground")
	if not ground.is_empty():
		ball.position = ground.position + Vector3.UP * 4
		scene.add_child(ball)
		for i in range(360):
			await physics_frame
		check(ball.position.y > ground.position.y - 2, "Jolt falling body supported")
	ball.queue_free()
	await physics_frame
	scene.update_lods()
	var triangles: int = scene.visible_triangles()
	if capture:
		DirAccess.make_dir_recursive_absolute(output)
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output.path_join("valle_overview.png"))
		scene.camera.position = Vector3(75, 80, 105)
		scene.camera.look_at(Vector3.ZERO)
		scene.update_lods()
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output.path_join("valle_borgo.png"))
	write_report(
		{
			"missing_data_mode": false,
			"terrain_ray_max_error_m": max_ray_error,
			"terrain_triangles_overview": triangles,
			"load_ms": scene.load_ms,
			"render_capture": capture,
			"engine": Engine.get_version_info().string,
			"renderer": RenderingServer.get_video_adapter_name()
		}
	)
	scene.queue_free()
	await process_frame
	quit(1 if failures.size() else 0)


func check_buildings(scene: Node3D, world: PhysicsDirectSpaceState3D) -> void:
	for building in scene.data.buildings:
		var ring := PackedVector2Array()
		for p in building.ring_xz_m:
			ring.append(Vector2(p[0], p[1]))
		var indices := Geometry2D.triangulate_polygon(ring)
		check(indices.size() >= 3, "OSM polygon triangulates " + building.id)
		if indices.size() < 3:
			continue
		var center := (ring[indices[0]] + ring[indices[1]] + ring[indices[2]]) / 3
		var point := Vector3(center.x, building.roof_y_m, center.y)
		# OSM has overlapping footprints: isolate the intended blockout for this test.
		var exclude: Array[RID] = []
		for instance in scene.building_root.get_children():
			if instance.get_meta("source_url") != building.source_url:
				exclude.append((instance.get_child(0) as StaticBody3D).get_rid())
		var query := PhysicsRayQueryParameters3D.create(
			point + Vector3.UP * 600, point - Vector3.UP * 600, 2, exclude
		)
		var hit := world.intersect_ray(query)
		check(not hit.is_empty(), "OSM roof collision " + building.id)
		if not hit.is_empty():
			check(absf(hit.position.y - point.y) < 0.002, "OSM roof height " + building.id)
	var previous: bool = scene.road_root.visible
	var key := InputEventKey.new()
	key.keycode = KEY_1
	key.pressed = true
	scene._unhandled_input(key)
	check(scene.road_root.visible != previous, "Road layer toggle input")
	scene._unhandled_input(key)
	check(scene.road_root.visible == previous, "Road layer toggle restores")


func cast(world: PhysicsDirectSpaceState3D, point: Vector3, mask: int) -> Dictionary:
	var query := PhysicsRayQueryParameters3D.create(
		point + Vector3.UP * 600, point - Vector3.UP * 600, mask
	)
	return world.intersect_ray(query)


func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error(message)


func write_report(result: Dictionary) -> void:
	result["checks"] = checks
	result["failures"] = failures
	result["scope"] = "Valle survey prototype, not full journey acceptance or representative FPS"
	DirAccess.make_dir_recursive_absolute(output)
	var file := FileAccess.open(output.path_join("godot_report.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "\t") + "\n")
	print(JSON.stringify(result))
