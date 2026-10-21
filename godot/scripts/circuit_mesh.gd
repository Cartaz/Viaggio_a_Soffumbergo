extends RefCounted
## Clockwise terrain fronts; unknown cells generate no faces and no collision.


static func build(data: Dictionary, stride: int, skirts: bool) -> ArrayMesh:
	var side := int(data.side)
	@warning_ignore("integer_division")
	var count := (side - 1) / stride + 1
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var valid: Array[bool] = []
	var indices := PackedInt32Array()
	for r in range(0, side, stride):
		for c in range(0, side, stride):
			var k := r * side + c
			var exists: bool = data.heights_m[k] != null
			valid.append(exists)
			# Internal unused vertices are never referenced by triangles.
			var height := float(data.heights_m[k]) if exists else 0.0
			vertices.append(Vector3(c * data.step_m, height, r * data.step_m))
			var n: Array = data.normals[k]
			normals.append(Vector3(n[0], n[1], n[2]))
	for r in range(count - 1):
		for c in range(count - 1):
			var k := r * count + c
			if valid[k] and valid[k + 1] and valid[k + count]:
				indices.append_array(PackedInt32Array([k, k + 1, k + count]))
			if valid[k + 1] and valid[k + count + 1] and valid[k + count]:
				indices.append_array(PackedInt32Array([k + 1, k + count + 1, k + count]))
	if skirts:
		var edges: Array[Array] = [[], [], [], []]
		for i in range(count):
			edges[0].append(i)
			edges[1].append(i * count + count - 1)
			edges[2].append(count * count - 1 - i)
			edges[3].append((count - 1 - i) * count)
		for edge in edges:
			for i in range(edge.size() - 1):
				var a: int = edge[i]
				var b: int = edge[i + 1]
				if not valid[a] or not valid[b]:
					continue
				var k := vertices.size()
				vertices.append(vertices[a] - Vector3.UP * data.skirt_depth_m)
				vertices.append(vertices[b] - Vector3.UP * data.skirt_depth_m)
				normals.append(normals[a])
				normals.append(normals[b])
				indices.append_array(PackedInt32Array([a, k, b, b, k, k + 1]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	if not indices.is_empty():
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
