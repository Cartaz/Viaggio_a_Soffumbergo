# Architettura della preparazione

| Percorso | Responsabilità |
| --- | --- |
| `data/config` | Parametri SI, provvisorietà, rig e coda degli asset |
| `tools/coffa/physics.py` | Calcoli e kernels numerici indipendenti |
| `tools/coffa/session.py` | Regole e registro logico della massa; nessuna forza o animazione |
| `tools/coffa/geography.py` | WGS84 e geometria di preparazione |
| `godot/scripts/vehicle_lab.gd` | Forze del primo aggregato rigido e telemetria |
| `mass_properties.gd`, `wheel_forces.gd` | Calcoli nel motore, confronto predisposto con Python |
| `mouse_locomotion.gd`, `companion_follower.gd` | Movimento da istanziare con asset e navmesh |
| `route_preview.gd` | Superficie provvisoria da dati con quote |
| `tools/blender` | Generazione di ingombri e guide, non ancora eseguita |
| `reports` | Risultati derivati e inventario, non misure del gioco |

Il progetto Godot è nella radice e legge direttamente `res://data/config`. Il gioco finale è offline; i download geografici sono strumenti di preparazione con opzione esplicita `--download`.

## Coordinate

- Veicolo Godot: X destra, Y alto, Z indietro; avanti −Z. Origine sul piano sotto il telaio a carico nominale.
- GeoJSON: WGS84, longitudine/latitudine; quote utilizzabili solo con datum dichiarato.
- Mondo locale: ECEF → ENU → Godot, X est, Y alto, Z sud. L’output conserva l’origine geografica.
- Blender: X destra/est, Y avanti/nord, Z alto. Da Godot: `(x, -z, y)`; glTF converte l’asse verticale.
- SVG e guide OSM: zero altimetrico solo grafico, mai un terreno verificato.

I triangoli della superficie seguono il fronte orario Godot, controllato da test. Questo non sostituisce l’importazione e la prova delle collisioni.

## Interfacce ancora da collegare

Il gestore della gita riceverà eventi da checkpoint direzionali, parcheggio, animazioni con appoggi confermati e ingresso nel borgo. UI e camera non cambiano direttamente massa o progressione.

Durante la guida iniziale c’è un corpo equivalente. Durante la scalata i protagonisti diventano corpi indipendenti nella stessa posa e velocità, con reazioni tramite contatti/vincoli. Nessuna duplicazione o interpolazione di massa fra corpi scollegati. L’adattatore fisico non è ancora implementato.

Stati di riferimento: `outbound`, `dismounting`, `exploring`, `mounting`, `returning`, `incident`, `complete`. Gli ingressi sulle pose e sugli appoggi devono derivare dalla scena, non essere sempre veri. Nessun salvataggio a metà transizione; scrittura temporanea e sostituzione atomica nella stessa cartella.

Il futuro porting GDScript deve conservare i casi di test Python. Fino ad allora le regole restano una specifica eseguibile esterna al laboratorio.
