extends RefCounted
## Parking readiness only. Occupants remain aboard; no fictitious visit completion.

var phase := "approach"
var stable_s := 0.0
var hold_s := 1.5
var reason := "Raggiungi la zona di sosta"


func update(sensors: Dictionary, delta: float) -> void:
	var eligible: bool = (
		sensors.inside
		and sensors.gates
		and sensors.speed < 0.1
		and sensors.angular_speed < 0.05
		and sensors.upright > 0.95
		and sensors.contacts == 4
		and sensors.brake >= 0.5
		and not sensors.incident
	)
	if not eligible:
		stable_s = 0
		if phase == "ready":
			phase = "approach"
		reason = "Ferma tutta l'auto nel riquadro, sulle quattro ruote, e tieni il freno"
	else:
		stable_s += delta
		if phase != "parked" and stable_s >= hold_s:
			phase = "ready"
		reason = "E: conferma la sosta" if phase == "ready" else "Attendi l'arresto stabile"


func enter() -> bool:
	if phase != "ready":
		return false
	phase = "parked"
	return true


func leave() -> bool:
	if phase != "parked":
		return false
	reset()
	return true


func reset() -> void:
	phase = "approach"
	stable_s = 0
	reason = "Raggiungi la zona di sosta"
