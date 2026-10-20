extends RefCounted
## Shared OSM blockouts and provisional line graphics, in the common Valle frame.


static func build_buildings(target: Node3D, buildings: Array) -> void:
	var gray := material(Color("c8c4b8"))
	for building in buildings:
		var ring := PackedVector2Array()
		for p in building.ring_xz_m:
			ring.append(Vector2(p[0], p[1]))
		var faces := PackedVector3Array()
		var roof := Geometry2D.triangulate_polygon(ring)
		for i in range(0, roof.size(), 3):
			var a := Vector3(ring[roof[i]].x, building.roof_y_m, ring[roof[i]].y)
			var b := Vector3(ring[roof[i + 1]].x, building.roof_y_m, ring[roof[i + 1]].y)
			var c := Vector3(ring[roof[i + 2]].x, building.roof_y_m, ring[roof[i + 2]].y)
			if (b - a).cross(c - a).y > 0:
				faces.append_array(PackedVector3Array([a, c, b]))
			else:
				faces.append_array(PackedVector3Array([a, b, c]))
		for i in range(ring.size()):
			var p := ring[i]
			var q := ring[(i + 1) % ring.size()]
			var a := Vector3(p.x, building.base_y_m, p.y)
			var b := Vector3(q.x, building.base_y_m, q.y)
			var c := Vector3(q.x, building.roof_y_m, q.y)
			var d := Vector3(p.x, building.roof_y_m, p.y)
			faces.append_array(PackedVector3Array([a, b, c, a, c, d]))
		var instance := face_mesh(faces, gray)
		instance.name = "OSM_" + str(building.id).replace("/", "_")
		instance.set_meta("source_url", building.source_url)
		instance.set_meta("height_status", building.height_status)
		target.add_child(instance)
		instance.create_trimesh_collision()
		var body := instance.get_child(0) as StaticBody3D
		body.collision_layer = 2
		body.collision_mask = 0
		var collision := body.get_child(0) as CollisionShape3D
		(collision.shape as ConcavePolygonShape3D).backface_collision = true


static func build_roads(target: Node3D, roads: Array) -> void:
	var amber := material(Color("e8a43e"))
	var magenta := material(Color("cc64c6"))
	for road in roads:
		var faces := PackedVector3Array()
		var columns := int(road.columns)
		for i in range(columns, road.vertices_m.size()):
			if i % columns == columns - 1:
				continue
			var a := vector(road.vertices_m[i - columns])
			var b := vector(road.vertices_m[i - columns + 1])
			var c := vector(road.vertices_m[i])
			var d := vector(road.vertices_m[i + 1])
			faces.append_array(PackedVector3Array([a, c, b, b, c, d]))
		var instance := face_mesh(faces, magenta if road.pedestrian else amber)
		instance.set_meta("source_url", road.source_url)
		instance.set_meta("status", road.status)
		target.add_child(instance)


static func face_mesh(faces: PackedVector3Array, mat: Material) -> MeshInstance3D:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for p in faces:
		surface.add_vertex(p)
	surface.generate_normals()
	var instance := MeshInstance3D.new()
	instance.mesh = surface.commit()
	instance.material_override = mat
	return instance


static func material(color: Color) -> StandardMaterial3D:
	var result := StandardMaterial3D.new()
	result.albedo_color = color
	result.roughness = 0.92
	# OSM ring orientation is source-dependent; closed blockouts are two-sided.
	result.cull_mode = BaseMaterial3D.CULL_DISABLED
	return result


static func vector(p: Array) -> Vector3:
	return Vector3(p[0], p[1], p[2])
