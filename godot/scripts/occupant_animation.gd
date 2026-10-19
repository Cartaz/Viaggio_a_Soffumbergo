class_name PhysicsOccupant
extends Node3D
## Deformation rig driven by support-point acceleration, with fixed-length contact IK.

var role := "lookout"
var pedal_inputs := Vector2.ZERO
var skeleton: Skeleton3D
var rest: Dictionary = {}
var bones: Dictionary = {}
var lean := Vector3.ZERO
var lean_velocity := Vector3.ZERO
var heave := 0.0
var heave_velocity := 0.0
var cloth_swing := Vector3.ZERO
var cloth_velocity := Vector3.ZERO
var effective_acceleration := Vector3.UP * 9.81
var grip_error := 0.0
var length_error := 0.0
var cape: CapeMotion
var torso_deformation := Transform3D.IDENTITY
var capsules: Array = []
var pose_freedom := 1.0
var applied_lean := Vector3.ZERO


func _ready() -> void:
	skeleton = find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D
	for i in range(skeleton.get_bone_count()):
		var key := skeleton.get_bone_name(i)
		bones[key] = i
		rest[key] = skeleton.get_bone_global_rest(i)
	var capes := find_children("*purple_cape*", "MeshInstance3D", true, false)
	if not capes.is_empty():
		cape = CapeMotion.new()
		cape.setup(capes[0], skeleton)


func reset_motion() -> void:
	lean = Vector3.ZERO
	lean_velocity = Vector3.ZERO
	heave = 0.0
	heave_velocity = 0.0
	cloth_swing = Vector3.ZERO
	cloth_velocity = Vector3.ZERO


func animate_support(
	dt: float, acceleration: Vector3, grips: Array[Transform3D], steering: float
) -> void:
	effective_acceleration = acceleration
	var target := Vector3(-acceleration.z, 0, acceleration.x) * 0.040
	var limit := 0.18 if role == "driver" else 0.30
	var pitch_limit := 0.10 if role == "driver" else limit
	target.x = clampf(target.x, -pitch_limit, pitch_limit)
	target.z = clampf(target.z, -limit, limit)
	var steps := maxi(1, ceili(dt * 240.0))
	var step := dt / float(steps)
	for i in range(steps):
		lean_velocity += ((target - lean) * 81.0 - lean_velocity * 16.2) * step
		lean += lean_velocity * step
		var heave_target := clampf(-(acceleration.y - 9.81) * 0.003, -0.020, 0.016)
		heave_velocity += ((heave_target - heave) * 144.0 - heave_velocity * 21.6) * step
		heave += heave_velocity * step
		var cloth_target := Vector3(-acceleration.z, 0, acceleration.x) * 0.024
		cloth_target = cloth_target.limit_length(0.22)
		cloth_velocity += ((cloth_target - cloth_swing) * 100.0 - cloth_velocity * 14.0) * step
		cloth_swing += cloth_velocity * step
	_pose(grips, steering)


func _pose(grips: Array[Transform3D], steering: float) -> void:
	skeleton.reset_bone_poses()
	# Seat and hand contacts constrain torso travel, never the lengths of limbs.
	pose_freedom = 1.0
	var body := _body_pose(pose_freedom)
	if not _contacts_reachable(body, grips):
		var low := 0.0
		var high := 1.0
		for iteration in range(9):
			var middle := (low + high) * 0.5
			if _contacts_reachable(_body_pose(middle), grips):
				low = middle
			else:
				high = middle
		pose_freedom = low
		body = _body_pose(pose_freedom)
	applied_lean = lean * pose_freedom
	var pelvis: Transform3D = body[0]
	torso_deformation = body[1]
	_set_global("pelvis", pelvis * rest.pelvis)
	_set_global("spine", torso_deformation * rest.spine)
	var head_rest: Transform3D = rest.head
	var head_pivot: Vector3 = torso_deformation * head_rest.origin
	var head_rotation := Basis.from_euler(-applied_lean * 0.35 + Vector3(0, steering * 0.10, 0))
	_set_global("head", _around(head_pivot, head_rotation) * torso_deformation * head_rest)
	_set_global(
		"tail",
		(
			pelvis
			* _around((rest.tail as Transform3D).origin, Basis.from_euler(-cloth_swing))
			* rest.tail
		)
	)
	grip_error = 0.0
	length_error = 0.0
	capsules = []
	for side in [-1, 1]:
		var suffix := str(side)
		var index := 0 if side == -1 else 1
		var shoulder: Vector3 = (
			torso_deformation * (rest["upper_arm_" + suffix] as Transform3D).origin
		)
		var chain := _solve_chain(
			"upper_arm_" + suffix,
			"forearm_" + suffix,
			"hand_" + suffix,
			shoulder,
			grips[index].origin,
			Vector3(side, -0.3, 0.2)
		)
		_set_global(
			"hand_" + suffix,
			Transform3D(
				grips[index].basis * (rest["hand_" + suffix] as Transform3D).basis, chain[2]
			)
		)
		grip_error = maxf(grip_error, chain[2].distance_to(grips[index].origin))
		capsules.append({"a": chain[0], "b": chain[1], "radius": 0.037})
		capsules.append({"a": chain[1], "b": chain[2], "radius": 0.027})
		var hip: Vector3 = pelvis * (rest["thigh_" + suffix] as Transform3D).origin
		var foot: Vector3 = (rest["foot_" + suffix] as Transform3D).origin
		if role == "driver":
			foot = Vector3(side * 0.082, 0.023, -0.15)
		_solve_chain(
			"thigh_" + suffix,
			"shin_" + suffix,
			"foot_" + suffix,
			hip,
			foot,
			Vector3(side * 0.15, 0.25, -1)
		)
		var foot_basis: Basis = (rest["foot_" + suffix] as Transform3D).basis
		if role == "driver":
			var press := pedal_inputs.y if side == -1 else pedal_inputs.x
			foot_basis = Basis(Vector3.RIGHT, -0.12 * press) * foot_basis
		_set_global("foot_" + suffix, Transform3D(foot_basis, foot))
		var cape_name := "cape_" + suffix
		_set_global(
			cape_name,
			(
				torso_deformation
				* _around((rest[cape_name] as Transform3D).origin, Basis.from_euler(cloth_swing))
				* rest[cape_name]
			)
		)
		for digit in range(4):
			var prefix := "finger_" + suffix + "_" + str(digit)
			skeleton.set_bone_pose_rotation(bones[prefix + "_a"], Quaternion(Vector3.RIGHT, 0.70))
			skeleton.set_bone_pose_rotation(bones[prefix + "_b"], Quaternion(Vector3.RIGHT, 0.85))
	_set_global(
		"cape_back",
		(
			torso_deformation
			* _around((rest.cape_back as Transform3D).origin, Basis.from_euler(cloth_swing))
			* rest.cape_back
		)
	)
	if cape != null:
		cape.update(skeleton, capsules, torso_deformation)


func _body_pose(amount: float) -> Array[Transform3D]:
	var pelvis := Transform3D.IDENTITY
	if role == "driver":
		pelvis.origin = Vector3(-lean.z * 0.10 * amount, -0.105, 0.015 + lean.x * 0.05 * amount)
	pelvis.origin.y += heave * amount * (0.5 if role == "driver" else 1.0)
	var pivot: Vector3 = pelvis * (rest.spine as Transform3D).origin
	return [pelvis, _around(pivot, Basis.from_euler(lean * amount)) * pelvis]


func _contacts_reachable(body: Array[Transform3D], grips: Array[Transform3D]) -> bool:
	for side in [-1, 1]:
		var suffix := str(side)
		var index := 0 if side == -1 else 1
		var shoulder: Vector3 = body[1] * (rest["upper_arm_" + suffix] as Transform3D).origin
		var elbow: Vector3 = (rest["forearm_" + suffix] as Transform3D).origin
		var hand: Vector3 = (rest["hand_" + suffix] as Transform3D).origin
		var arm: float = (rest["upper_arm_" + suffix] as Transform3D).origin.distance_to(elbow)
		arm += elbow.distance_to(hand)
		if shoulder.distance_to(grips[index].origin) > arm - 0.001:
			return false
		var hip: Vector3 = (rest["thigh_" + suffix] as Transform3D).origin
		var knee: Vector3 = (rest["shin_" + suffix] as Transform3D).origin
		var foot: Vector3 = (rest["foot_" + suffix] as Transform3D).origin
		var leg := hip.distance_to(knee) + knee.distance_to(foot)
		var target := Vector3(side * 0.082, 0.023, -0.15) if role == "driver" else foot
		if (body[0] * hip).distance_to(target) > leg - 0.001:
			return false
	return true


func _solve_chain(
	upper: String, lower: String, end: String, a: Vector3, target: Vector3, pole: Vector3
) -> Array[Vector3]:
	var ra: Transform3D = rest[upper]
	var rb: Transform3D = rest[lower]
	var rc: Transform3D = rest[end]
	var first := ra.origin.distance_to(rb.origin)
	var second := rb.origin.distance_to(rc.origin)
	var vector := target - a
	var distance := clampf(
		vector.length(), absf(first - second) + 0.00001, first + second - 0.00001
	)
	var direction := vector.normalized()
	var along := (distance * distance + first * first - second * second) / (2.0 * distance)
	var height := sqrt(maxf(0.0, first * first - along * along))
	var bend := (pole - direction * pole.dot(direction)).normalized()
	var b := a + direction * along + bend * height
	var c := a + direction * distance
	_set_global(
		upper,
		Transform3D(
			(
				Basis(Quaternion((rb.origin - ra.origin).normalized(), (b - a).normalized()))
				* ra.basis
			),
			a
		)
	)
	_set_global(
		lower,
		Transform3D(
			(
				Basis(Quaternion((rc.origin - rb.origin).normalized(), (c - b).normalized()))
				* rb.basis
			),
			b
		)
	)
	_set_global(end, Transform3D(rc.basis, c))
	length_error = maxf(length_error, absf(a.distance_to(b) - first))
	length_error = maxf(length_error, absf(b.distance_to(c) - second))
	return [a, b, c]


func _set_global(key: String, pose: Transform3D) -> void:
	skeleton.set_bone_global_pose(bones[key], pose)


static func _around(pivot: Vector3, rotation: Basis) -> Transform3D:
	return Transform3D(rotation, pivot - rotation * pivot)


func snapshot() -> Dictionary:
	var poses: Dictionary = {}
	for key in bones:
		var deformation: Transform3D = (
			skeleton.get_bone_global_pose(bones[key]) * (rest[key] as Transform3D).affine_inverse()
		)
		poses[key] = _matrix_array(deformation)
	var cape_vertices: Array = []
	if cape != null:
		for vertex in cape.vertices:
			cape_vertices.append([vertex.x, vertex.y, vertex.z])
	return {
		"bones": poses,
		"cape_vertices": cape_vertices,
		"lean": [lean.x, lean.y, lean.z],
		"heave": heave,
		"pose_freedom": pose_freedom,
		"applied_lean": [applied_lean.x, applied_lean.y, applied_lean.z],
		"grip_error": grip_error,
		"length_error": length_error,
		"cape_clearance": cape.minimum_clearance if cape != null else 0.0
	}


static func _matrix_array(t: Transform3D) -> Array:
	return [
		[t.basis.x.x, t.basis.y.x, t.basis.z.x, t.origin.x],
		[t.basis.x.y, t.basis.y.y, t.basis.z.y, t.origin.y],
		[t.basis.x.z, t.basis.y.z, t.basis.z.z, t.origin.z],
		[0, 0, 0, 1]
	]
