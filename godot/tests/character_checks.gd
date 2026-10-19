extends SceneTree
## Real GLB import/instantiation checks; does not validate animation or contact fit.


func _initialize() -> void:
	call_deferred("_check_characters")


func _check_characters() -> void:
	var widths: Dictionary = {}
	for key in ["bernie", "bianca"]:
		var path: String = "res://godot/assets/characters/" + key + ".glb"
		var packed := load(path) as PackedScene
		if packed == null:
			_fail("Cannot load " + path)
			return
		var model := packed.instantiate() as Node3D
		root.add_child(model)
		var bodies := model.find_children("*_body", "MeshInstance3D", true, false)
		if bodies.size() != 1:
			_fail("Expected one body for " + key)
			return
		widths[key] = (bodies[0] as MeshInstance3D).mesh.get_aabb().size.x
		var toes := model.find_children("*toe_claw*", "MeshInstance3D", true, false)
		var fingers := model.find_children("*finger_claw*", "MeshInstance3D", true, false)
		if toes.size() != 10 or fingers.size() != 8:
			_fail("Expected ten toe claws and eight finger claws for " + key)
			return
		if not model.find_children("*", "CollisionObject3D", true, false).is_empty():
			_fail("Visual character adds an unexpected physics body: " + key)
			return
		model.free()
	if float(widths.bianca) >= float(widths.bernie):
		_fail("Bianca's torso must be narrower than Bernie's")
		return
	var review := load("res://godot/scenes/characters.tscn") as PackedScene
	if review == null:
		_fail("Cannot load character review scene")
		return
	var display := review.instantiate()
	root.add_child(display)
	display.free()
	print("Character checks passed: both GLBs, slender Bianca, articulated paws, review scene.")
	quit(0)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
