extends SceneTree

const Grid = preload("res://godot/scripts/circuit_mesh.gd")


func _initialize() -> void:
	var data := {"side": 3, "step_m": 2, "skirt_depth_m": 2, "heights_m": [], "normals": []}
	for i in range(9):
		data.heights_m.append(2.0 if i != 4 else null)
		data.normals.append([0, 1, 0])
	var mesh := Grid.build(data, 1, false)
	var arrays := mesh.surface_get_arrays(0)
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var good := indices.size() == 6 and not indices.has(4)
	for index in indices:
		good = good and is_equal_approx(vertices[index].y, 2.0)
	data.heights_m.fill(null)
	good = good and Grid.build(data, 1, true).get_surface_count() == 0
	print("Circuit mesh unknown-cell regression: ", "passed" if good else "FAILED")
	quit(0 if good else 1)
