class_name CompanionFollower
extends MouseLocomotion
## Attach to a fitted mouse CharacterBody with NavigationAgent3D child.
## Does not teleport when blocked; emits a diagnostic for authored recovery.

signal blocked(position: Vector3)

@export var leader: Node3D
@export var follow_distance_m := 1.2
@export var repath_interval_s := 0.4
var repath_clock := 0.0
var stationary_clock := 0.0
var previous_position := Vector3.ZERO
var navigation_ready := false
@onready var agent: NavigationAgent3D = $NavigationAgent3D


func _ready() -> void:
	super._ready()
	previous_position = global_position
	agent.path_desired_distance = 0.2
	agent.target_desired_distance = follow_distance_m
	# Nav map is synchronized after a physics frame, never query it in _ready.
	await get_tree().physics_frame
	navigation_ready = true


func _physics_process(delta: float) -> void:
	desired_direction = Vector3.ZERO
	if enabled and is_instance_valid(leader) and navigation_ready:
		repath_clock -= delta
		if repath_clock <= 0:
			agent.target_position = leader.global_position
			repath_clock = repath_interval_s
		if global_position.distance_to(leader.global_position) > follow_distance_m:
			if not agent.is_navigation_finished():
				desired_direction = (agent.get_next_path_position() - global_position).normalized()
		if (
			global_position.distance_to(leader.global_position) > follow_distance_m + 0.1
			and global_position.distance_to(previous_position) < 0.005
		):
			stationary_clock += delta
		else:
			stationary_clock = 0
		if stationary_clock > 3:
			blocked.emit(global_position)
			stationary_clock = 0
	previous_position = global_position
	super._physics_process(delta)
