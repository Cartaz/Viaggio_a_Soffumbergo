# Architettura della preparazione

## Costruzione del circuito

`build_circuit_shoulders.py` aggiunge una fascia separata e rigenerabile dal
bordo 3D delle mesh al terreno derivato. La triangolazione segue ogni faccia
del terreno per evitare compenetrazioni; gli originali restano intatti.
`construction_surface.gd` costruisce normali, materiale e collisioni locali:
asfalto sul layer 4, raccordi sul layer 8. La Yaris della pratica e del giro usa
la maschera ruote 13; confronto e scaricamento eliminano entrambi i derivati.
`validate_circuit_shoulders.py` verifica geometria, recupero fisico, renderer e
Blender. [Procedura](RACCORDI_E_ASFALTO.md).

`build_circuit_loop.py`, `loop_route.py` e `maneuver_search.py` costruiscono un
riferimento con cambi di verso sulle superfici esistenti. `circuit_loop.gd`
avanza soltanto dopo arresti stabili e conserva l'invalidazione dell'intero
tentativo. Il cambio fase non scrive posa, velocità o freeze. Recupero e nuovo
tentativo sono riposizionamenti dichiarati; la visita non è conteggiata.
[Ambito](GIRO_COSTRUZIONE.md).

`coffa/road_construction.py` indicizza i segmenti, prepara il profilo ciclico e
costruisce l'unione della fascia provvisoria con triangolazione vincolata Shapely.
`build_circuit_construction.py` scrive una variante locale con scavi/riporti,
normali globali, LOD ricalcolati e settori stradali separati. Non modifica DTM,
manifest originale o prove precedenti. `check_circuit_construction.py` verifica
area, fronti, copertura e giunzioni e prepara i riferimenti indipendenti per Jolt.

`circuit_construction.gd` estende l'ispettore; la strada sul layer 4 condivide la
residenza del terreno sul layer 1. T elimina i corpi residenti e ricostruisce
terreno/viste generali dalla variante originale o di progetto. F9 richiama i punti
critici, senza correggerli automaticamente. Il gate Python/Godot/Blender è
`validate_circuit_construction.py`; il sincronizzatore separato protegge i file
privati tramite preflight, backup e ricevuta. [Procedura](COSTRUZIONE_CIRCUITO.md).

`build_circuit_practice.py` separa il profilo invariato ai confini geografici e
alle inversioni, con margini di arresto espliciti e impronta del manifest.
`circuit_practice.gd` riusa terreno/strada a caricamento progressivo, centrati
sul veicolo. `practice_route.gd` limita la ricerca a una finestra di progressiva
per non agganciare un ramo vicino; `trial_progress.gd` conserva l'ordine e il
verso dei checkpoint. Ogni cambio tratto è un riposizionamento separato.
Le prove misurano i comandi fisici e le proiezioni delle quattro ruote sul
pavimento effettivo. `validate_circuit_construction.py --practice` aggiunge
prove di avanzamento, partenze e guida dei singoli tratti. [Ambito](PRATICA_CIRCUITO.md).

## Guida pilota e prestazioni Yaris

`yaris_powertrain.gd` separa dati Toyota e parametri effettivi alle ruote in
`yaris_performance.json`. `vehicle_lab.gd` applica le forze tramite i contatti;
la velocità non viene troncata. Il tachimetro esclude la caduta verticale e il
laboratorio dichiara il ripristino oltre i propri confini. La variante Windows
conserva modelli, personaggi ed esercizi propri tramite aggiornamento mirato.

`build_drive_pilot.py` genera un manifest separato e sette chunk modificati
per una superficie progettata di prova. `drive_pilot.gd` riusa lo streaming
del circuito, centrato sul veicolo; layer 1 terreno, 2 edifici, 4 superficie.
`drive_pilot_check.gd` percorre il tratto usando pedali/sterzo, senza guidare
il corpo tramite trasformazioni. `validate_drive_pilot.py` e il generatore
Blender raccolgono prove. La modifica del terreno è dichiaratamente sintetica,
non un nuovo rilievo o una correzione dei raster. Vedere [limiti](GUIDA_PILOTA.md).

`trial_progress.gd` gestisce soltanto i checkpoint della prova: intersezione
direzionale fra campioni fisici e piano del prossimo punto, sagoma/altezza,
continuità, idoneità del tentativo e tempo. `drive_pilot.gd` osserva incidenti,
mostra le strisce e prepara il terreno prima del recupero esplicito. La ripresa
mantiene il progresso ma invalida il tentativo; soltanto una nuova prova azzera
tutto. Non scrive salvataggi e non dichiara completata la gita. Le regole di
discesa/visita/risalita in `coffa/session.py` restano da integrare nel motore.

`parking_pilot.gd` estende la guida con un manifest separato, piazzola e sensori
dell'intero ingombro. `parking_state.gd` richiede un arresto continuo prima della
conferma; durante la sosta blocca la spinta attraverso i comandi e mantiene il
freno fisico. Nessun congelamento, duplicazione o trasferimento della massa:
gli occupanti rimangono sul veicolo. `build_parking_pilot.py` raccorda soltanto
il derivato tecnico finale; `validate_parking_pilot.py` verifica rigenerazione,
regressioni precedenti, arresto e copertura della piazzola. Vedere [limiti](SOSTA_PILOTA.md).

## Discesa e passeggiata di prova

La variante `visit_pilot.gd` estende la sosta, senza sostituirla: stati locali
`aboard`, `descending`, `walking`, `gathering`, `ascending`. `visit_mass.gd`
separa/riunisce la proprietà della massa e conserva la quantità di moto al
reinserimento. `visit_actor.gd` usa corpi dinamici, guide a forze uguali/opposte
e movimento sul terreno; `visit_ik.gd` applica rotazioni degli arti senza
stiramento. La raccolta avviene in sequenza per evitare conflitti nel passaggio
posteriore. Sosta e guida rimangono fisiche, senza congelare l'auto.

È il primo adattatore della visita nella scena tecnica: non porta ancora tutti
i checkpoint, il salvataggio o la visita obbligatoria di `coffa/session.py` nel
motore. Il solo indicatore `visited_trial` riguarda una passeggiata locale.
`validate_visit_pilot.py` aggiunge prove dei trasferimenti e del ciclo a 60/120 Hz.
Vedere [limiti e variante Windows](VISITA_PILOTA.md).

## Corridoio Circuito 3D 0.1

`coffa/dtm_mosaic.py` applica la scelta globale della fonte senza fusione di
quote. `build_circuit_3d.py` verifica i 41 originali, seleziona i settori e scrive
una generazione locale completa con impronte e ID di provenienza per vertice.
`check_circuit_3d.py` confronta bordi, profilo e campioni scalari indipendenti.

`circuit.gd` estende la camera di ispezione di Valle, mostra la veduta generale
e gestisce la residenza dei chunk. `circuit_sector.gd` mantiene fisica fissa a
2 m e tre mesh visive; `circuit_mesh.gd` omette i triangoli senza dati. Il modulo
`valle_content.gd` costruisce gli stessi edifici/linee OSM nelle due scene.
Le collisioni del terreno vengono eliminate con i chunk lontani; gli edifici
di Valle restano statici e le linee non hanno massa o superficie stradale.
Prove e limiti in [CIRCUITO_3D.md](CIRCUITO_3D.md).

## Incremento Valle 3D 0.1

`tools/build_valle_3d.py` riusa il lettore/mosaico LiDAR esistente;
`tools/coffa/terrain.py` verifica campionamento, ritaglio e errore LOD. PROJ
allinea OSM al sistema nativo EPSG:6708. Frame: X est, Y alto, Z sud,
origine ENH [375920, 5112728, 720]; nessuna conversione verticale.

`build/valle/valle_scene.json` è un derivato locale fuori Git con settori,
normali globali, provenienza e segnaposto espliciti. `valle_sector.gd` mantiene
una mesh visiva attiva per settore con tre LOD e una collisione fissa; le gonne
non hanno collisioni. `valle.gd` costruisce edifici/linee OSM e la camera libera,
senza dipendenze sul veicolo o sui personaggi. Terreno sul layer fisico 1,
edifici sul 2, strade senza corpi.

`tools/validate_valle.py` fallisce anche sugli errori del motore con uscita zero.
`tools/blender/build_valle.py` converte gli assi con (x, -z, y) e inverte i fronti
da Godot orari a Blender antiorari. Dettagli e limiti in [VALLE_3D.md](VALLE_3D.md).

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
| `tools/blender/build_yaris*.py` | Generatori eseguiti di auto di serie e variante con foro dell'albero |
| `art/vehicles/yaris_2022`, `art/source/yaris_2022` | GLB autonomi e sorgente artistico, separato dall'import automatico Godot |
| `godot/scripts/yaris_visual.gd` | Articolazioni visive, senza massa/collisioni proprie |
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

Durante la guida iniziale c’è un corpo equivalente. Nella visita pilota i protagonisti diventano corpi indipendenti nella stessa posizione e velocità del baricentro, sostenuti da guide a forze con reazione sul veicolo e poi da contatti col terreno. Nessuna duplicazione o interpolazione di massa fra corpi scollegati. Restano da finalizzare equilibrio anatomico e contatti dettagliati con abitacolo e scalette.

Stati di riferimento: `outbound`, `dismounting`, `exploring`, `mounting`, `returning`, `incident`, `complete`. Gli ingressi sulle pose e sugli appoggi devono derivare dalla scena, non essere sempre veri. Nessun salvataggio a metà transizione; scrittura temporanea e sostituzione atomica nella stessa cartella.

Il futuro porting dell'intera gita deve conservare i casi di test Python. La visita locale del prototipo non sostituisce quella specifica, né certifica già il ritorno dell'anello.
