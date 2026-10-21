extends RefCounted
## Rotation-only two-bone IK. Clamp unreachable targets; never translate/scale limbs.


static func reach(skeleton: Skeleton3D, names: Array, target: Vector3, pole: Vector3) -> float:
	var a := skeleton.find_bone(names[0])
	var b := skeleton.find_bone(names[1])
	var c := skeleton.find_bone(names[2])
	if mini(a, mini(b, c)) < 0:
		return 0
	var start := skeleton.get_bone_global_pose(a)
	var elbow := skeleton.get_bone_global_pose(b)
	var tip := skeleton.get_bone_global_pose(c)
	var first := start.origin.distance_to(elbow.origin)
	var second := elbow.origin.distance_to(tip.origin)
	var direction := target - start.origin
	var distance := clampf(
		direction.length(), absf(first - second) + 0.0001, first + second - 0.0001
	)
	direction = direction.normalized()
	var bend := pole - direction * pole.dot(direction)
	if bend.length_squared() < 0.0001:
		bend = direction.cross(Vector3.RIGHT)
	bend = bend.normalized()
	var along := (first * first - second * second + distance * distance) / (2 * distance)
	var wanted_elbow := (
		start.origin + direction * along + bend * sqrt(maxf(0, first * first - along * along))
	)
	var rotation := Basis(
		Quaternion(
			(elbow.origin - start.origin).normalized(), (wanted_elbow - start.origin).normalized()
		)
	)
	skeleton.set_bone_global_pose(a, Transform3D(rotation * start.basis, start.origin))
	elbow = skeleton.get_bone_global_pose(b)
	tip = skeleton.get_bone_global_pose(c)
	var wanted_tip := start.origin + direction * distance
	rotation = Basis(
		Quaternion(
			(tip.origin - elbow.origin).normalized(), (wanted_tip - elbow.origin).normalized()
		)
	)
	skeleton.set_bone_global_pose(b, Transform3D(rotation * elbow.basis, elbow.origin))
	return skeleton.get_bone_global_pose(c).origin.distance_to(target)
