class_name CapeMotion
extends RefCounted
## Persistent GPU-deformed cloth. CPU reference is used by headless contact tests.

const CLOTH_SHADER = preload("res://godot/shaders/cape_motion.gdshader")

var mesh_node: MeshInstance3D
var rest_arrays: Array
var bind_bones: PackedInt32Array
var bind_poses: Array[Transform3D] = []
var material: Material
var vertices := PackedVector3Array()
var minimum_clearance := 0.0
var corrections := 0
var shader_material: ShaderMaterial
var cpu_validation := DisplayServer.get_name() == "headless"


func setup(node: MeshInstance3D, skeleton: Skeleton3D) -> void:
	mesh_node = node
	rest_arrays = node.mesh.surface_get_arrays(0)
	material = node.mesh.surface_get_material(0)
	for i in range(node.skin.get_bind_count()):
		bind_bones.append(skeleton.find_bone(node.skin.get_bind_name(i)))
		bind_poses.append(node.skin.get_bind_pose(i))
	node.skin = null
	node.skeleton = NodePath()
	var arrays: Array = rest_arrays.duplicate()
	var joint_indices := PackedFloat32Array()
	for index in rest_arrays[Mesh.ARRAY_BONES]:
		joint_indices.append(float(index))
	arrays[Mesh.ARRAY_CUSTOM0] = joint_indices
	arrays[Mesh.ARRAY_CUSTOM1] = rest_arrays[Mesh.ARRAY_WEIGHTS]
	arrays[Mesh.ARRAY_BONES] = null
	arrays[Mesh.ARRAY_WEIGHTS] = null
	var flags := (
		(Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT)
		| (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT)
	)
	var persistent := ArrayMesh.new()
	persistent.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, flags)
	shader_material = ShaderMaterial.new()
	shader_material.shader = CLOTH_SHADER
	shader_material.set_shader_parameter(
		"cape_color", (material as StandardMaterial3D).albedo_color
	)
	persistent.surface_set_material(0, shader_material)
	node.mesh = persistent
	node.custom_aabb = AABB(Vector3(-0.4, 0.1, -0.35), Vector3(0.8, 0.65, 0.7))


func update(skeleton: Skeleton3D, capsules: Array, torso: Transform3D) -> void:
	if mesh_node == null:
		return
	var rest: PackedVector3Array = rest_arrays[Mesh.ARRAY_VERTEX]
	var bones: PackedInt32Array = rest_arrays[Mesh.ARRAY_BONES]
	var weights: PackedFloat32Array = rest_arrays[Mesh.ARRAY_WEIGHTS]
	var skin_matrices: Array[Transform3D] = []
	for i in range(bind_bones.size()):
		skin_matrices.append(skeleton.get_bone_global_pose(bind_bones[i]) * bind_poses[i])
	shader_material.set_shader_parameter("skin_matrices", skin_matrices)
	shader_material.set_shader_parameter("torso", torso)
	shader_material.set_shader_parameter("torso_inverse", torso.affine_inverse())
	var starts := PackedVector4Array()
	var ends := PackedVector4Array()
	for capsule in capsules:
		var a: Vector3 = capsule.a
		var b: Vector3 = capsule.b
		starts.append(Vector4(a.x, a.y, a.z, capsule.radius))
		ends.append(Vector4(b.x, b.y, b.z, 0))
	shader_material.set_shader_parameter("capsule_a", starts)
	shader_material.set_shader_parameter("capsule_b", ends)
	if not cpu_validation:
		return
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
		# Overlapping elbow/torso capsules can alternate projections. Escape their
		# union monotonically away from the torso rather than oscillating in it.
		var radial := torso_inverse * p - Vector3(0, 0.42, 0)
		radial.y = 0.0
		var escape := torso.basis * radial.normalized()
		for iteration in range(4):
			var escaped := false
			for capsule in capsules:
				var q := Geometry3D.get_closest_point_to_segment(p, capsule.a, capsule.b)
				if p.distance_squared_to(q) >= float(capsule.radius) * float(capsule.radius):
					continue
				var center: Vector3 = (capsule.a + capsule.b) * 0.5
				var radius: float = capsule.a.distance_to(capsule.b) * 0.5 + capsule.radius
				var offset := p - center
				var along := offset.dot(escape)
				var exit := (
					-along
					+ sqrt(maxf(0, along * along - offset.length_squared() + radius * radius))
				)
				p += escape * (exit + 0.001)
				escaped = true
			if not escaped:
				break
		vertices[i] = p
	minimum_clearance = 100.0
	for p in vertices:
		for capsule in capsules:
			var q := Geometry3D.get_closest_point_to_segment(p, capsule.a, capsule.b)
			minimum_clearance = minf(minimum_clearance, p.distance_to(q) - float(capsule.radius))
