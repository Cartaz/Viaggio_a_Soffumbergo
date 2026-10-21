extends RefCounted
## User mandate: runtime acceptance requires the approved car, rig and both mice.


static func inspect(vehicle: Node) -> Dictionary:
	var expected := [
		"yaris_hybrid_red_game.glb", "pirate_mast_coffa.glb", "bernie.glb", "bianca.glb"
	]
	var found: Dictionary = {}
	var nodes: Array[Node] = [vehicle]
	nodes.append_array(vehicle.find_children("*", "Node", true, false))
	for node in nodes:
		var filename := node.scene_file_path.get_file()
		if expected.has(filename):
			found[filename] = {
				"sha256": FileAccess.get_sha256(node.scene_file_path),
				"visible": node is Node3D and node.is_visible_in_tree()
			}
	var valid := true
	for filename in expected:
		valid = (
			valid and found.has(filename) and bool(found.get(filename, {}).get("visible", false))
		)
	valid = valid and vehicle.find_child("BernieDriver", true, false) != null
	valid = valid and vehicle.find_child("BiancaLookout", true, false) != null
	valid = valid and vehicle.find_child("PirateRig", true, false) != null
	return {
		"approved_assembly_loaded": valid,
		"assets": found,
		"visual_process_active": vehicle.is_processing(),
		"visual_physics_process_active": vehicle.is_physics_processing()
	}
