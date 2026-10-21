extends RigidBody3D
## Independent mass. An active guide applies equal/opposite forces to the vehicle.
## Upright collider and authored powered guide are explicit prototype approximations.

const LimbIK = preload("res://godot/scripts/visit_ik.gd")

var vehicle: RigidBody3D
var role := "driver"
var guide_enabled := false
var guide_target := Vector3.ZERO
var desired_velocity := Vector3.ZERO
var visual: Node3D
var skeleton: Skeleton3D
var initial_poses: Array[Quaternion] = []
var initial_positions: Array[Vector3] = []
var initial_scales: Array[Vector3] = []
var visual_start := Vector3.ZERO
var visual_clock := 0.0
var gait_distance := 0.0
var guide_force := Vector3.ZERO
var reaction_force := Vector3.ZERO
var max_guide_error := 0.0
var proxy_legs: Array[Node3D] = []
var max_limb_length_error_m := 0.0
var ladder_base := Vector3.ZERO
var max_rung_hand_error_m := 0.0
var rung_pose_frames := 0
var return_to_seat := false
var seat_blend := 0.0


func _ready() -> void:
	lock_rotation = true
	can_sleep = false
	linear_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	linear_damp = 0
	contact_monitor = true
	max_contacts_reported = 8
	collision_layer = 16
	collision_mask = 23
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.2
	capsule.height = 0.5
	shape.shape = capsule
	add_child(shape)
	var surface := PhysicsMaterial.new()
	surface.friction = 0
	surface.bounce = 0
	physics_material_override = surface
	# Match the original component's intrinsic box tensor, rather than an auto sphere.
	inertia = (
		Vector3(0.45 * 0.45 + 0.6 * 0.6, 0.32 * 0.32 + 0.6 * 0.6, 0.32 * 0.32 + 0.45 * 0.45)
		* mass
		/ 12
	)
	if visual == null:
		_build_proxy()
	else:
		add_child(visual)
		var rigs := visual.find_children("*", "Skeleton3D", true, false)
		if not rigs.is_empty():
			skeleton = rigs[0]
			for i in range(skeleton.get_bone_count()):
				initial_poses.append(skeleton.get_bone_pose_rotation(i))
				initial_positions.append(skeleton.get_bone_pose_position(i))
				initial_scales.append(skeleton.get_bone_pose_scale(i))


func grounded() -> bool:
	if get_contact_count() == 0:
		return false
	var query := PhysicsRayQueryParameters3D.create(position, position - Vector3.UP * 0.32, 5)
	query.exclude = [get_rid(), vehicle.get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	return not hit.is_empty() and hit.normal.dot(Vector3.UP) > 0.7


func _physics_process(delta: float) -> void:
	guide_force = Vector3.ZERO
	reaction_force = Vector3.ZERO
	if guide_enabled:
		var point: Vector3 = vehicle.global_transform * guide_target
		var lever: Vector3 = position - vehicle.global_transform * vehicle.center_of_mass
		var relative_velocity := (
			linear_velocity - vehicle.linear_velocity - vehicle.angular_velocity.cross(lever)
		)
		var error := point - position
		max_guide_error = maxf(max_guide_error, error.length())
		guide_force = (error * 100 - relative_velocity * 20 + Vector3.UP * 9.81) * mass
		guide_force = guide_force.limit_length(mass * 9.81 * 3)
		reaction_force = -guide_force
		apply_central_force(guide_force)
		# The actuator attaches at the actor COM: this force pair has zero net wrench.
		vehicle.apply_force(reaction_force, position - vehicle.global_position)
	elif grounded():
		var horizontal := Vector3(linear_velocity.x, 0, linear_velocity.z)
		var force := ((desired_velocity - horizontal) * mass * 8).limit_length(mass * 9.81 * 0.9)
		apply_central_force(force)
	_animate(delta)


func _animate(delta: float) -> void:
	visual_clock += delta
	gait_distance += (
		(
			linear_velocity.length()
			if guide_enabled
			else Vector2(linear_velocity.x, linear_velocity.z).length()
		)
		* delta
	)
	if skeleton != null:
		# Local rotations only: no rest edits, bone scale, IK stretching or copied private code.
		var blend := clampf(visual_clock / 2, 0, 1)
		if return_to_seat:
			seat_blend = minf(1, seat_blend + delta / 2)
			blend = 1 - seat_blend
		visual.position = visual_start.lerp(Vector3(0, -0.25, 0), blend)
		for i in range(skeleton.get_bone_count()):
			# Reset solver roundoff; translations and scale never accumulate between frames.
			skeleton.set_bone_pose_position(i, initial_positions[i])
			skeleton.set_bone_pose_scale(i, initial_scales[i])
			skeleton.set_bone_pose_rotation(i, initial_poses[i].slerp(Quaternion.IDENTITY, blend))
		for side in [-1, 1]:
			var stride := sin(gait_distance * 12 + (PI if side == -1 else 0)) * 0.28
			for bone in ["thigh_", "upper_arm_"]:
				var index := skeleton.find_bone(bone + str(side))
				if index >= 0:
					skeleton.set_bone_pose_rotation(
						index, initial_poses[index].slerp(Quaternion(Vector3.RIGHT, stride), blend)
					)
			if (
				guide_enabled
				and not return_to_seat
				and absf(vehicle.to_local(position).x - ladder_base.x) < 0.13
			):
				_pose_rung(side)
			for pair in [
				["upper_arm_", "forearm_"],
				["forearm_", "hand_"],
				["thigh_", "shin_"],
				["shin_", "foot_"]
			]:
				var a := skeleton.find_bone(pair[0] + str(side))
				var b := skeleton.find_bone(pair[1] + str(side))
				if a >= 0 and b >= 0:
					var rest_length := skeleton.get_bone_global_rest(a).origin.distance_to(
						skeleton.get_bone_global_rest(b).origin
					)
					var actual := skeleton.get_bone_global_pose(a).origin.distance_to(
						skeleton.get_bone_global_pose(b).origin
					)
					max_limb_length_error_m = maxf(
						max_limb_length_error_m, absf(actual - rest_length)
					)
	else:
		for i in range(proxy_legs.size()):
			proxy_legs[i].rotation.x = sin(gait_distance * 12 + (PI if i % 2 else 0)) * 0.25
	if not guide_enabled and desired_velocity.length_squared() > 0.01:
		visual.rotation.y = lerp_angle(
			visual.rotation.y,
			atan2(-desired_velocity.x, -desired_velocity.z) - rotation.y,
			1 - exp(-6 * delta)
		)


func _pose_rung(side: int) -> void:
	var hand := skeleton.find_bone("upper_arm_" + str(side))
	var foot := skeleton.find_bone("foot_" + str(side))
	if hand < 0 or foot < 0:
		return
	var shoulder_world := skeleton.global_transform * skeleton.get_bone_global_pose(hand).origin
	var foot_world := skeleton.global_transform * skeleton.get_bone_global_pose(foot).origin
	var height := vehicle.to_local(shoulder_world).y
	var foot_height := vehicle.to_local(foot_world).y
	var hand_rung := roundf((height - ladder_base.y - 0.05) / 0.2) * 0.2 + ladder_base.y
	var foot_rung := ceilf((foot_height - ladder_base.y) / 0.2) * 0.2 + ladder_base.y
	var hand_target := (
		vehicle.global_transform
		* Vector3(ladder_base.x + side * 0.1, hand_rung, ladder_base.z - 0.12)
	)
	var foot_target := (
		vehicle.global_transform
		* Vector3(ladder_base.x + side * 0.08, foot_rung, ladder_base.z - 0.12)
	)
	var error := LimbIK.reach(
		skeleton,
		["upper_arm_" + str(side), "forearm_" + str(side), "hand_" + str(side)],
		skeleton.to_local(hand_target),
		Vector3(side, -0.3, 0.2)
	)
	max_rung_hand_error_m = maxf(max_rung_hand_error_m, error)
	rung_pose_frames += 1
	LimbIK.reach(
		skeleton,
		["thigh_" + str(side), "shin_" + str(side), "foot_" + str(side)],
		skeleton.to_local(foot_target),
		Vector3(side * 0.2, 0, -1)
	)


func _build_proxy() -> void:
	visual = Node3D.new()
	add_child(visual)
	var color := Color("ad8263") if role == "driver" else Color("a7a9b8")
	_sphere(Vector3(0.18, 0.15, 0.28), Vector3.ZERO, color)
	_sphere(Vector3(0.13, 0.12, 0.15), Vector3(0, 0.08, -0.25), color)
	for side in [-1, 1]:
		_sphere(Vector3(0.065, 0.075, 0.025), Vector3(side * 0.1, 0.18, -0.2), color)
		for front in [-1, 1]:
			var leg := _sphere(
				Vector3(0.045, 0.095, 0.045), Vector3(side * 0.13, -0.13, front * 0.18), color
			)
			proxy_legs.append(leg)
	_sphere(Vector3(0.018, 0.018, 0.22), Vector3(0, -0.05, 0.39), Color("cba6a0"))


func _sphere(size: Vector3, at: Vector3, color: Color) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 1
	sphere.height = 2
	mesh.mesh = sphere
	mesh.scale = size
	mesh.position = at
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mesh.material_override = mat
	visual.add_child(mesh)
	return mesh
