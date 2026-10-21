extends RefCounted
## Shared tile-local visual/collider, with per-vertex area-weighted road normals.


static func make_material(color: Color, grain_scale := 70.0) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = preload("res://godot/shaders/circuit_surface.gdshader")
	mat.set_shader_parameter("surface_color", color)
	mat.set_shader_parameter("grain_scale", grain_scale)
	return mat


static func build(data: Dictionary, chunk: Node3D, layer: int, mat: Material) -> StaticBody3D:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	var vertices := PackedVector3Array()
	for point in data.vertices_m:
		vertices.append(
			Vector3(
				float(point[0]) - chunk.position.x,
				float(point[1]),
				float(point[2]) - chunk.position.z
			)
		)
	var indices := PackedInt32Array()
	var normals := PackedVector3Array()
	normals.resize(vertices.size())
	for triangle in data.triangles:
		var a := int(triangle[0])
		var b := int(triangle[1])
		var c := int(triangle[2])
		indices.append_array(PackedInt32Array([a, b, c]))
		var normal := (vertices[c] - vertices[a]).cross(vertices[b] - vertices[a])
		for index in [a, b, c]:
			normals[index] += normal
	for i in range(normals.size()):
		normals[i] = normals[i].normalized()
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_INDEX] = indices
	arrays[Mesh.ARRAY_NORMAL] = normals
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var visual := MeshInstance3D.new()
	visual.mesh = mesh
	visual.material_override = mat
	chunk.add_child(visual)
	var body := StaticBody3D.new()
	body.collision_layer = layer
	body.collision_mask = 0
	var shape := CollisionShape3D.new()
	shape.shape = mesh.create_trimesh_shape()
	body.add_child(shape)
	chunk.add_child(body)
	return body
