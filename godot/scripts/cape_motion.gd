class_name CapeMotion
extends RefCounted
## Weighted arm-following cloth with collision projection after deformation.

var mesh_node: MeshInstance3D
var rest_arrays: Array
var bind_bones: PackedInt32Array
var bind_poses: Array[Transform3D] = []
var material: Material
var vertices := PackedVector3Array()
var minimum_clearance := 0.0
var corrections := 0


func setup(node: MeshInstance3D, skeleton: Skeleton3D) -> void:
	mesh_node = node
	rest_arrays = node.mesh.surface_get_arrays(0)
	material = node.mesh.surface_get_material(0)
	for i in range(node.skin.get_bind_count()):
		bind_bones.append(skeleton.find_bone(node.skin.get_bind_name(i)))
		bind_poses.append(node.skin.get_bind_pose(i))
	node.skin = null
	node.skeleton = NodePath()


func update(skeleton: Skeleton3D, capsules: Array, torso: Transform3D) -> void:
	if mesh_node == null:
		return
	var rest: PackedVector3Array = rest_arrays[Mesh.ARRAY_VERTEX]
	var bones: PackedInt32Array = rest_arrays[Mesh.ARRAY_BONES]
	var weights: PackedFloat32Array = rest_arrays[Mesh.ARRAY_WEIGHTS]
	var indices: PackedInt32Array = rest_arrays[Mesh.ARRAY_INDEX]
	var skin_matrices: Array[Transform3D] = []
	for i in range(bind_bones.size()):
		skin_matrices.append(skeleton.get_bone_global_pose(bind_bones[i]) * bind_poses[i])
	vertices.resize(rest.size())
	corrections = 0
	var torso_inverse := torso.affine_inverse()
	for i in range(rest.size()):
		var p := Vector3.ZERO
		for j in range(4):
			var weight := weights[i * 4 + j]
			if weight > 0.0:
				p += (skin_matrices[bones[i * 4 + j]] * rest[i]) * weight
		# Iterate because resolving one sleeve can approach the torso surface.
		for iteration in range(6):
			var changed := false
			var local := torso_inverse * p - Vector3(0, 0.42, 0)
			var radii := Vector3(0.137, 0.17, 0.122)
			var unit := local / radii
			if unit.length_squared() < 1.0:
				p = torso * (Vector3(0, 0.42, 0) + unit.normalized() * radii)
				corrections += 1
				changed = true
			for capsule in capsules:
				var q := Geometry3D.get_closest_point_to_segment(p, capsule.a, capsule.b)
				var offset: Vector3 = p - q
				var radius: float = capsule.radius
				if offset.length_squared() < radius * radius:
					var direction := offset.normalized()
					if direction.length_squared() < 0.01:
						direction = Vector3.RIGHT if q.x > 0 else Vector3.LEFT
					p = q + direction * (radius + 0.001)
					corrections += 1
					changed = true
			if not changed:
				break
		vertices[i] = p
	minimum_clearance = 100.0
	for p in vertices:
		for capsule in capsules:
			var q := Geometry3D.get_closest_point_to_segment(p, capsule.a, capsule.b)
			minimum_clearance = minf(minimum_clearance, p.distance_to(q) - float(capsule.radius))
	var normals := PackedVector3Array()
	normals.resize(vertices.size())
	for i in range(0, indices.size(), 3):
		var a := indices[i]
		var b := indices[i + 1]
		var c := indices[i + 2]
		var normal := (vertices[b] - vertices[a]).cross(vertices[c] - vertices[a])
		normals[a] += normal
		normals[b] += normal
		normals[c] += normal
	for i in range(normals.size()):
		normals[i] = normals[i].normalized()
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = indices
	var dynamic := ArrayMesh.new()
	dynamic.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	dynamic.surface_set_material(0, material)
	mesh_node.mesh = dynamic
