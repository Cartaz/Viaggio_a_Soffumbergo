class_name MouseLocomotion
extends CharacterBody3D
## Navigation/collision controller only. Biped rig and foot IK are still required.
## This never scales bones. Motion intent can come from player input or follower.

@export var speed_m_s := 1.8
@export var acceleration_m_s2 := 4.0
@export var turn_rate_rad_s := 4.0
@export var enabled := false
var desired_direction := Vector3.ZERO
var gravity_m_s2 := 9.81


func _ready() -> void:
	gravity_m_s2 = float(ProjectSettings.get_setting("physics/3d/default_gravity", 9.81))
	floor_snap_length = 0.20
	floor_max_angle = deg_to_rad(42)
	# Collision shape must be fitted to the approved mouse body envelope.
	# The biped design does not authorize resizing limbs to clear steps.


func _physics_process(delta: float) -> void:
	var direction := desired_direction if enabled else Vector3.ZERO
	direction.y = 0
	if direction.length_squared() > 1:
		direction = direction.normalized()
	var target := direction * speed_m_s
	velocity.x = move_toward(velocity.x, target.x, acceleration_m_s2 * delta)
	velocity.z = move_toward(velocity.z, target.z, acceleration_m_s2 * delta)
	if not is_on_floor():
		velocity.y -= gravity_m_s2 * delta
	elif velocity.y < 0:
		velocity.y = 0
	move_and_slide()
	if direction.length_squared() > 0.001:
		var desired_yaw := atan2(-direction.x, -direction.z)
		rotation.y = rotate_toward(rotation.y, desired_yaw, turn_rate_rad_s * delta)
