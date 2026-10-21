extends RefCounted
## Local arc window prevents a close hairpin/retraced branch from stealing progress.

var points := PackedVector3Array()
var station := PackedFloat64Array()
var progress := 0.0
var lateral := 0.0
var segment := 0


func configure(values: Array) -> void:
	points.clear()
	station.clear()
	station.append(0)
	for value in values:
		points.append(Vector3(value[0], value[1], value[2]))
	for i in range(1, points.size()):
		var d := Vector2(points[i].x - points[i - 1].x, points[i].z - points[i - 1].z)
		station.append(station[-1] + d.length())
	progress = 0
	lateral = 0
	segment = 0


func at(distance: float) -> Vector3:
	distance = clampf(distance, 0, station[-1])
	var i := clampi(station.bsearch(distance), 1, station.size() - 1)
	return points[i - 1].lerp(
		points[i], (distance - station[i - 1]) / (station[i] - station[i - 1])
	)


func sample(position: Vector3, travel_budget: float) -> void:
	var low := maxf(0, progress - 12)
	var high := minf(station[-1], progress + maxf(12, travel_budget))
	var first := maxi(0, station.bsearch(low) - 1)
	var last := mini(points.size() - 2, station.bsearch(high))
	var best := INF
	var q := Vector2(position.x, position.z)
	for i in range(first, last + 1):
		var a := Vector2(points[i].x, points[i].z)
		var d := Vector2(points[i + 1].x, points[i + 1].z) - a
		var t := clampf((q - a).dot(d) / d.length_squared(), 0, 1)
		var s := lerpf(station[i], station[i + 1], t)
		if s < low or s > high:
			continue
		var error := q.distance_to(a + d * t)
		if error < best:
			best = error
			segment = i
			progress = s
	lateral = best
