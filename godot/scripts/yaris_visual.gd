class_name YarisVisual
extends Node3D
## Render-only vehicle. The laboratory remains the sole owner of physical mass.

const WHEEL_IDS := ["FL", "FR", "RL", "RR"]
const STEERING_AXIS := Vector3(0.0, -0.327, -0.945)
var steer_nodes: Array[Node3D] = []
var spin_nodes: Array[Node3D] = []
var wheel_spin := 0.0
var steering_wheel: Node3D


func _ready() -> void:
	for wheel_id in WHEEL_IDS:
		steer_nodes.append(find_child("Steer_" + wheel_id, true, false) as Node3D)
		spin_nodes.append(find_child("Wheel_" + wheel_id, true, false) as Node3D)
	steering_wheel = find_child("SteeringWheel", true, false) as Node3D
	# Imported inspection clips must never start during driving.
	for child in find_children("*", "AnimationPlayer", true, false):
		(child as AnimationPlayer).stop()


func update_running_gear(
	anchors: Array[Vector3], lengths: PackedFloat32Array, steer: float, speed: float, delta: float
) -> void:
	wheel_spin = fmod(wheel_spin - speed * delta / 0.31045, TAU)
	for i in range(4):
		steer_nodes[i].position = anchors[i] - Vector3.UP * lengths[i]
		steer_nodes[i].rotation.y = -steer if i < 2 else 0.0
		spin_nodes[i].rotation.x = wheel_spin
	# Ratio is an animation estimate, not a calibrated Toyota steering mechanism.
	steering_wheel.basis = Basis(STEERING_AXIS.normalized(), -steer * 13.6)


func set_door_open(wheel_id: String, fraction: float) -> void:
	var door := find_child("Door_" + wheel_id, true, false) as Node3D
	if door:
		var sign_side := -1.0 if wheel_id.ends_with("L") else 1.0
		door.rotation.y = sign_side * clampf(fraction, 0.0, 1.0) * 1.05


func set_hatch_open(fraction: float) -> void:
	var hatch := find_child("Hatch", true, false) as Node3D
	if hatch:
		hatch.rotation.x = -clampf(fraction, 0.0, 1.0) * 1.05
