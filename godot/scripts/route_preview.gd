class_name SurveyRoutePreview
extends Node3D
## Attach to a separate scene after preparing verified-height route JSON.
## No route is silently fabricated when data is missing.

@export_file("*.json") var route_data_path := ""


func _ready() -> void:
	if route_data_path.is_empty():
		push_warning("Route preview: supply height-resolved data from tools/prepare_route.py")
		return
	var route: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(route_data_path))
	if route.get("schema_version") != 1 or route.get("axes") != "+X east, +Y up, +Z south":
		push_error("Unsupported route format")
		return
	var vertices := PackedVector3Array()
	for p in route.vertices_m:
		vertices.append(MassProperties.vector(p))
	var indices := PackedInt32Array()
	for face in route.triangles:
		for index in face:
			indices.append(int(index))
	var normals := PackedVector3Array()
	normals.resize(vertices.size())
	normals.fill(Vector3.UP)
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("616d69")
	material.roughness = 0.95
	instance.material_override = material
	add_child(instance)
	instance.create_trimesh_collision()
	print("Route preview: ", route.length_m, " m; width and crossfall remain provisional")
