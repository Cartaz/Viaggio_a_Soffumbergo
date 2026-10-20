extends Node3D
## Fine geometry and fixed collision are created only while the chunk is resident.

const Grid = preload("res://godot/scripts/circuit_mesh.gd")
var visual := MeshInstance3D.new()
var meshes: Array[ArrayMesh] = []
var triangle_counts: Array[int] = []
var current_lod := -1
var center := Vector3.ZERO


func build(data: Dictionary, mat: Material) -> void:
	name = "Circuit_" + str(data.id)
	position = Vector3(data.offset_xz_m[0], 0, data.offset_xz_m[1])
	center = position + Vector3(64, 0, 64)
	for stride in [1, 2, 4]:
		var mesh := Grid.build(data, stride, true)
		meshes.append(mesh)
		var triangles := 0
		if mesh.get_surface_count() > 0:
			var arrays := mesh.surface_get_arrays(0)
			triangles = (arrays[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
		triangle_counts.append(triangles)
	var body := StaticBody3D.new()
	body.collision_layer = 1
	body.collision_mask = 0
	var shape := CollisionShape3D.new()
	var collision_mesh := Grid.build(data, 1, false)
	if collision_mesh.get_surface_count() > 0:
		shape.shape = collision_mesh.create_trimesh_shape()
		body.add_child(shape)
		add_child(body)
	else:
		shape.free()
		body.free()
	visual.material_override = mat
	add_child(visual)
	select_lod(2)


func update_lod(eye: Vector3, distances: Array) -> void:
	var distance := Vector2(eye.x - center.x, eye.z - center.z).length()
	if current_lod == 0 and distance < float(distances[0]) + 12:
		return
	if current_lod == 2 and distance > float(distances[1]) - 12:
		return
	select_lod(0 if distance < float(distances[0]) else 1 if distance < float(distances[1]) else 2)


func select_lod(level: int) -> void:
	if current_lod != level:
		current_lod = level
		visual.mesh = meshes[level]
