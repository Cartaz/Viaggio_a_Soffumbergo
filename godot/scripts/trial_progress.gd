extends RefCounted
## Rules for the engineering trial only, not the full journey/visit state machine.

var gates: Array[Dictionary] = []
var next_gate := 0
var valid := true
var incident := ""
var previous := Vector3.ZERO
var elapsed_s := 0.0
var half_width_m := 2.25


func configure(definitions: Array[Dictionary], start: Vector3, half_width: float) -> void:
	gates = definitions
	half_width_m = half_width
	new_attempt(start)


func new_attempt(start: Vector3) -> void:
	next_gate = 0
	valid = true
	incident = ""
	elapsed_s = 0
	previous = start


func fail(reason: String) -> void:
	valid = false
	if incident.is_empty():
		incident = reason


func recover(start: Vector3) -> void:
	# A recovery never restores eligibility, elapsed time or skipped checkpoints.
	valid = false
	incident = ""
	previous = start


func sample(position: Vector3, delta: float, upright: bool) -> bool:
	if not position.is_finite() or not is_finite(delta) or delta <= 0:
		fail("Campione fisico non valido")
		return false
	elapsed_s += delta
	var movement := position - previous
	# Technical discontinuity guard (288 km/h plus 0.5 m tolerance), not a force.
	if movement.length() > 80 * delta + 0.5:
		fail("Spostamento discontinuo: ripristinare la prova")
	var crossed := false
	if incident.is_empty() and upright and next_gate < gates.size():
		var gate: Dictionary = gates[next_gate]
		var normal: Vector3 = gate.forward
		var origin: Vector3 = gate.origin
		var before := (previous - origin).dot(normal)
		var after := (position - origin).dot(normal)
		if before < 0 and after >= 0:
			var hit := previous.lerp(position, -before / (after - before))
			var right := normal.cross(Vector3.UP).normalized()
			var offset: Vector3 = hit - gate.origin
			if absf(offset.dot(right)) <= half_width_m and absf(offset.y) <= 2.0:
				next_gate += 1
				crossed = true
	previous = position
	return crossed


func can_arrive() -> bool:
	return incident.is_empty() and not gates.is_empty() and next_gate == gates.size()
