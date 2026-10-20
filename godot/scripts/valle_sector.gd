extends Node3D
## One static collision surface, three visual LODs; skirts never enter physics.

var meshes: Array[ArrayMesh] = []
var visual := MeshInstance3D.new()
var current_lod := -1
var triangle_counts: Array[int] = []
var center := Vector3.ZERO


func build(data: Dictionary, config: Dictionary, material: Material) -> void:
	name = "Terrain_" + str(data.id)
	position = Vector3(data.offset_xz_m[0], 0, data.offset_xz_m[1])
	center = position + Vector3(64, 0, 64)
	var base: ArrayMesh
	for stride in config.lod_strides:
		var surface := make_grid(data, int(stride), float(config.terrain_step_m))
		if int(stride) == 1:
			base = surface
		var arrays := surface.surface_get_arrays(0)
		# Godot may synthesize tangents on upload; skirts change the vertex count.
		arrays[Mesh.ARRAY_TANGENT] = null
		add_skirts(arrays, int(data.side - 1) / int(stride) + 1, data.skirt_depth_m)
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		meshes.append(mesh)
		triangle_counts.append((arrays[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3)
	var body := StaticBody3D.new()
	body.collision_layer = 1
	body.collision_mask = 0
	var shape := CollisionShape3D.new()
	shape.shape = base.create_trimesh_shape()
	body.add_child(shape)
	add_child(body)
	visual.material_override = material
	add_child(visual)
	select_lod(2)


func update_lod(eye: Vector3, distances: Array) -> void:
	var distance := Vector2(eye.x - center.x, eye.z - center.z).length()
	# Hysteresis prevents repeated mesh switches on a threshold.
	var margin := 12.0
	if current_lod == 0 and distance < float(distances[0]) + margin:
		return
	if current_lod == 2 and distance > float(distances[1]) - margin:
		return
	var next := 0 if distance < float(distances[0]) else 1
	if distance >= float(distances[1]):
		next = 2
	select_lod(next)


func select_lod(level: int) -> void:
	if current_lod != level:
		current_lod = level
		visual.mesh = meshes[level]


static func make_grid(data: Dictionary, stride: int, step: float) -> ArrayMesh:
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var indices := PackedInt32Array()
	var side := int(data.side)
	@warning_ignore("integer_division")
	var count := (side - 1) / stride + 1
	for r in range(0, side, stride):
		for c in range(0, side, stride):
			var k := r * side + c
			vertices.append(Vector3(c * step, data.heights_m[k], r * step))
			var n: Array = data.normals[k]
			normals.append(Vector3(n[0], n[1], n[2]))
	for r in range(count - 1):
		for c in range(count - 1):
			var k := r * count + c
			indices.append_array(PackedInt32Array([k, k + 1, k + count]))
			indices.append_array(PackedInt32Array([k + 1, k + count + 1, k + count]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


static func add_skirts(arrays: Array, side: int, depth: float) -> void:
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var edges: Array[Array] = [[], [], [], []]
	for i in range(side):
		edges[0].append(i)
		edges[1].append(i * side + side - 1)
		edges[2].append(side * side - 1 - i)
		edges[3].append((side - 1 - i) * side)
	for edge in edges:
		for i in range(edge.size() - 1):
			var a: int = edge[i]
			var b: int = edge[i + 1]
			var k := vertices.size()
			vertices.append(vertices[a] - Vector3.UP * depth)
			vertices.append(vertices[b] - Vector3.UP * depth)
			normals.append(normals[a])
			normals.append(normals[b])
			indices.append_array(PackedInt32Array([a, k, b, b, k, k + 1]))
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = indices
