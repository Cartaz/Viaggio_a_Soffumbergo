# Accesso a Valle — prova di guida 0.1

20 ottobre 2026. Prima integrazione della Yaris con il corridoio DTM e il
caricamento dei settori. Scena `godot/scenes/drive_pilot.tscn`.

Il tratto usa gli ultimi **601,49 m** del settore C candidato OSM. Termina
vicino all'aggancio nord del borgo, non conferma prato PV-01 o itinerario
pedonale. Nessuna svolta reale è dichiarata verificata. È una prova di
ingegneria riproducibile, non la ricostruzione approvata della strada.

## Geometria dichiarata

- Asse orizzontale del candidato OSM già versionato, origine e datum del
  circuito conservati: EPSG:6708, X est/Y alto/Z sud.
- Larghezza **4,5 m scelta per il test**, pendenza trasversale zero. Non sono
  misure stradali. Due metri di piazzola tecnica complessiva alle estremità.
- Profilo di progetto: regressione lineare locale su finestra ±12 m delle
  quote DTM, più 15 cm. Ogni scostamento dal terreno è registrato; non si
  presenta il terreno nudo come quota dell'asfalto.
- Terreno modificato soltanto nel derivato della scena pilota, sotto strada
  e fasce laterali, per consentire collisioni coerenti. Il massimo scavo/riporto
  di prova è nel rapporto (circa 4 m): richiede verifica reale, non è un'opera
  osservata. Il corridoio di ispezione originale e tutti i raster sono invariati.
- Superficie marrone e bordi ambra: segnalazione persistente del carattere
  provvisorio. Collisioni della strada sul layer 4, terreno 1, edifici 2;
  ruote sul terreno/strada, telaio anche contro gli edifici. Nessun binario invisibile.

I 352 settori conservano il caricamento progressivo, ora centrato sul veicolo.
Soltanto sette settori richiedono il derivato di sistemazione del fondo. La
fisica non dipende dal LOD visivo. Non sono implementati giro completo,
checkpoint della gita, parcheggio definitivo, discesa o visita a piedi.

## Avvio e comandi

Nella copia Windows: `Avvia accesso a Valle.cmd`. W/S accelerano avanti/indietro,
A/D sterzano, Spazio frena, R riparte dalla posa iniziale, M mostra la mappa,
C ripristina la camera al seguito. Oltre l'area della prova viene dichiarato
un ripristino: non conta come tragitto completato. Arrivo richiede avvicinamento
all'estremità e arresto. La scena iniziale e le scene di ispezione sono conservate.

```powershell
python tools/build_drive_pilot.py
godot --path . res://godot/scenes/drive_pilot.tscn
godot --headless --fixed-fps 120 --path . --script godot/tests/drive_pilot_check.gd
godot --fixed-fps 120 --path . --script godot/tests/drive_pilot_check.gd -- --capture
godot --headless --fixed-fps 120 --path . --script godot/tests/yaris_performance_check.gd -- --hz=120
godot --headless --fixed-fps 60 --path . --script godot/tests/yaris_performance_check.gd -- --hz=60 --output=build/yaris_performance/60
```

Richiede i derivati locali di Circuito 3D 0.1. Il generatore verifica le impronte
dei chunk prima di usarli, salva una manifestazione separata e non modifica
`build/circuit/manifest.json`. Rigenerando due volte si ottengono gli stessi file.

Nella copia sorgente GitHub il gate completo è `python tools/validate_drive_pilot.py --godot PERCORSO_GODOT
--blender PERCORSO_BLENDER --capture` (su un'unica riga). Controlla anche
regressioni del laboratorio e di Valle, test Python, formattazione e lint.
La variante Windows conserva il proprio laboratorio: per le sue regressioni
usare anche `godot/tests/driving_bench.gd` e `godot/tests/lab_controls_bench.gd`.

La prova automatica guida applicando gli stessi comandi del giocatore,
misura deviazione, contatti, velocità, assetto e caricamento/scaricamento.
Controlla raggi sulla superficie e interferenze del terreno durante il percorso;
non teletrasporta l'auto per raggiungere l'arrivo. Salva log e telemetria locali
in `build/drive_validation`. Vedere [prestazioni Yaris](YARIS_PRESTAZIONI.md).

## Copia Windows e pubblicazione

`tools/sync_drive_local.py` applica soltanto gli aggiornamenti fisici/HUD della
variante locale nota, conserva modello Hybrid approvato, struttura pirata,
personaggi, esercizi, F11/Esc e `project.godot`. Verifica impronte prima di
scrivere; conserva copie precedenti in `build/drive_backups` e una ricevuta.
Una variante modificata dall'utente interrompe la sincronizzazione.

Il repository pubblico continua a usare i propri asset già versionati: i
modelli e i riferimenti privati della copia Windows non vengono pubblicati.
Raster, strada, terreno modificato, screenshot e telemetria restano sotto
`build/`, fuori Git. La fedeltà della strada richiede ancora rilievo di
larghezze, bivi, asfalto, muri, passaggi e altezza libera della struttura.
