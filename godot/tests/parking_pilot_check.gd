extends "res://godot/tests/drive_pilot_check.gd"
## Reuses the ordinary physical driver, then checks the real stop interlocks.

const ParkingScene = preload("res://godot/scenes/parking_pilot.tscn")


func _initialize() -> void:
	scene_resource = ParkingScene
	output_dir = "build/parking_validation"
	super._initialize()


func _after_drive(scene: Node3D) -> void:
	var car: LaboratoryVehicle = scene.vehicle
	car.throttle = 0
	car.braking = 1
	await ticks(2)
	check(scene.inside_stop(), "Whole vehicle footprint fits technical stop")
	check(scene.stop.phase == "ready", "Stable physical arrival enables confirmation")
	var max_zone_error := 0.0
	for x in range(9):
		for z in range(17):
			var p: Vector3 = (
				scene.zone
				* Vector3(
					(x / 8.0 - 0.5) * scene.zone_size.x, 0, (z / 16.0 - 0.5) * scene.zone_size.y
				)
			)
			var query := PhysicsRayQueryParameters3D.create(
				p + Vector3.UP * 3, p - Vector3.UP * 4, 4
			)
			query.exclude = [car.get_rid()]
			var hit: Dictionary = scene.get_world_3d().direct_space_state.intersect_ray(query)
			check(not hit.is_empty(), "Continuous collision across entire marked stop")
			if not hit.is_empty():
				max_zone_error = maxf(max_zone_error, absf(hit.position.y - p.y))
	check(max_zone_error < 0.002, "Technical stop collision is level")
	var original_size: Vector2 = scene.zone_size
	scene.zone_size.x = 0.5
	check(not scene.inside_stop(), "Origin proximity cannot replace whole body footprint")
	scene.zone_size = original_size
	var press := InputEventKey.new()
	press.keycode = KEY_E
	press.pressed = true
	scene._unhandled_input(press)
	check(scene.stop.phase == "parked", "E confirms the ready stop")
	var start: Vector3 = car.position
	var mass_before: float = car.mass
	var com_before: Vector3 = car.center_of_mass
	car.throttle = 1
	car.braking = 0
	await ticks(3)
	check(car.throttle == 0 and car.braking == 1, "Parked controls prevent engine drive")
	check(not car.freeze, "Stop uses tyre brakes, not a frozen vehicle")
	check(car.position.distance_to(start) < 0.05, "Physical brakes hold within five centimetres")
	check(car.diagnostic_contact_count == 4, "Four wheel supports retained at rest")
	check(
		car.mass == mass_before and car.center_of_mass == com_before,
		"Occupants stay aboard without mass transfer"
	)
	check(not scene.trial.incident, "No false incident while parked")
	scene._unhandled_input(press)
	check(scene.stop.phase == "approach", "E returns to driving mode")
	check(not scene.toggle_stop(), "Immediate reconfirmation requires a fresh stable hold")
	car.braking = 1
	await ticks(2)
	check(scene.toggle_stop(), "Stable stop can be confirmed again")
	check("visita ancora da integrare" in scene.hud.text, "HUD does not claim a completed visit")
