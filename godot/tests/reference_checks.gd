extends SceneTree
## Run on the connected PC after the first editor import. NOT run in preparation.

const MassScript = preload("res://godot/scripts/mass_properties.gd")
const ForceScript = preload("res://godot/scripts/wheel_forces.gd")
var failures := 0
var checks := 0


func _initialize() -> void:
	var config: Dictionary = JSON.parse_string(
		FileAccess.get_file_as_string("res://data/config/vehicle_lab.json")
	)
	var reference: Dictionary = JSON.parse_string(
		FileAccess.get_file_as_string("res://reports/design_diagnostics.json")
	)
	var calculated: Dictionary = MassScript.calculate(config.components)
	check(absf(float(calculated.mass) - float(reference.mass_kg)) < 0.000001, "mass reference")
	var com: Vector3 = calculated.com
	for i in range(3):
		check(absf(com[i] - float(reference.com_m[i])) < 0.00001, "COM component")
		for j in range(3):
			check(
				absf(calculated.tensor[i][j] - float(reference.inertia_kg_m2[i][j])) < 0.01,
				"tensor component"
			)
	var random := RandomNumberGenerator.new()
	random.seed = 734
	for i in range(1000):
		var load := random.randf_range(0, 6000)
		var mu := random.randf_range(0.1, 1.2)
		var force: Vector2 = ForceScript.combined(
			random.randf_range(-20000, 20000), random.randf_range(-20000, 20000), load, mu
		)
		check(force.length() <= mu * load + 0.01, "combined friction budget")
	check(ForceScript.spring(-0.1, -1.0, config.suspension) == 0.0, "no tensile contact")
	print("Godot reference checks: ", checks, "; failures: ", failures)
	quit(1 if failures else 0)


func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error(message)
