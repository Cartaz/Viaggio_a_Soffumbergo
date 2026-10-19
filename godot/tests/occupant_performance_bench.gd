extends SceneTree
## Wall-clock frame measurements in the real driving scene; no fixed-fps simulation.

var lab: Node3D
var samples: Array[float] = []
var results: Array = []
var phase := 0
var started := 0
var last := 0
var peak_driver_lean := 0.0
var peak_lookout_lean := 0.0
var head_min := Vector3(INF, INF, INF)
var head_max := Vector3(-INF, -INF, -INF)
var sway_min := INF
var sway_max := -INF


func _initialize() -> void:
	call_deferred("run_bench")


func run_bench() -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.size = Vector2i(3840, 2160)
	lab = (load("res://godot/scenes/lab.tscn") as PackedScene).instantiate()
	root.add_child(lab)
	current_scene = lab
	lab.set_physics_process(false)
	var exercise: Node = lab.get("exercise")
	if exercise != null:
		exercise.set_physics_process(false)
	lab.camera_view = 2
	Engine.max_fps = 60
	await create_timer(2.0).timeout
	started = Time.get_ticks_usec()
	last = started
	process_frame.connect(measure)
	physics_frame.connect(drive)


func drive() -> void:
	var t: float = lab.vehicle.elapsed
	lab.vehicle.throttle = 0.8 if fmod(t, 8.0) < 5.0 else 0.0
	lab.vehicle.braking = 0.8 if fmod(t, 8.0) >= 5.0 else 0.0
	lab.vehicle.steering_target = 0.35 if fmod(t, 8.0) < 4.0 else -0.35
	peak_driver_lean = maxf(peak_driver_lean, lab.vehicle.driver.applied_lean.length())
	peak_lookout_lean = maxf(peak_lookout_lean, lab.vehicle.lookout.applied_lean.length())
	var actor: PhysicsOccupant = lab.vehicle.driver
	var head: Vector3 = actor.skeleton.get_bone_global_pose(actor.bones.head).origin
	head_min = head_min.min(head)
	head_max = head_max.max(head)
	var seat: float = actor.skeleton.get_bone_global_pose(actor.bones.pelvis).origin.x
	sway_min = minf(sway_min, seat)
	sway_max = maxf(sway_max, seat)


func measure() -> void:
	var now := Time.get_ticks_usec()
	samples.append(float(now - last) / 1000.0)
	last = now
	if now - started < 8000000:
		return
	samples.sort()
	var total := 0.0
	for ms in samples:
		total += ms
	var result := {
		"phase": phase,
		"frames": samples.size(),
		"mean_fps": samples.size() * 1000.0 / total,
		"p95_ms": samples[int(samples.size() * 0.95)],
		"p99_ms": samples[int(samples.size() * 0.99)],
		"physics_ms": Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
		"draw_calls": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		"triangles": Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
		"driver_lean_deg": rad_to_deg(peak_driver_lean),
		"lookout_lean_deg": rad_to_deg(peak_lookout_lean),
		"resolution": str(root.size),
		"driver_head_range_m": head_max.distance_to(head_min),
		"driver_seat_sway_range_m": sway_max - sway_min,
		"fps_cap": Engine.max_fps,
		"view": lab.camera_view
	}
	results.append(result)
	print("OCCUPANT_PERFORMANCE ", JSON.stringify(result))
	phase += 1
	if phase == 1:
		lab.camera_view = 1
	elif phase == 2:
		lab.camera_view = 0
	elif phase == 3:
		lab.camera_view = 2
		Engine.max_fps = 0
	else:
		var capture := root.get_texture().get_image()
		DirAccess.make_dir_recursive_absolute("res://captures/occupant_60fps")
		capture.save_png("res://captures/occupant_60fps/4k_render.png")
		var passed := capture.get_size() == Vector2i(3840, 2160)
		for row in results:
			passed = passed and row.mean_fps >= 59.0 and row.p95_ms < 18.0
		passed = passed and head_max.distance_to(head_min) > 0.03 and sway_max - sway_min > 0.01
		var file := FileAccess.open(
			"res://reports/occupant_performance_validation.json", FileAccess.WRITE
		)
		file.store_string(
			JSON.stringify(
				{
					"passed": passed,
					"gpu": RenderingServer.get_video_adapter_name(),
					"results": results
				},
				"  "
			)
		)
		print("OCCUPANT_PERFORMANCE_PASSED ", passed)
		quit(0 if passed else 1)
	samples.clear()
	started = now
