# Valle 3D 0.1 — prototipo geografico

20 ottobre 2026. Scena autonoma `godot/scenes/valle.tscn`, separata dal laboratorio
auto e dai lavori locali sui personaggi. È un ambiente di ispezione con camera
libera, non il viaggio giocabile o una ricostruzione artistica approvata.

## Dati e coordinate

Il generatore riusa `import_valle_lidar05.read_grids/mosaic`: verifica SHA256
dell'archivio originale, intestazioni, celle valide e sovrapposizioni identiche.
L'area di questo campione è **768 × 768 m**, centrata sull'origine proiettata
**E 375920, N 5112728, H 720 m**. Non coincide con l'intera copertura del mosaico
né con l'anello completo. Il file `data/config/valle_3d.json` contiene i parametri.

EPSG:6708, X est, Y alto, Z sud. Le quote sono quelle ellissoidiche dichiarate dai
nomi originali `Ell_DTM`; la verifica indipendente del metadato verticale rimane
aperta. Sottrarre 720 m trasla la scena: non converte il datum. OSM è proiettato
da WGS84 con PROJ/pyproj, asse longitudine/latitudine esplicito, rete disabilitata
e trasformazioni ballpark vietate. Il JSON conserva la descrizione dell'operazione.

Il campionamento usa i **centri delle celle** ASC, non gli angoli: primo centro
E 375240,25 / N 5113364,75. Anche l'esportatore GLB precedente è stato corretto
di mezzo pixel (0,25 m su ciascun asse). Gli originali restano invariati.

Fonti: [LiDAR FVG 2017–2020](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826),
[acquisizione e impronte](ACQUISIZIONE_LIDAR05_REALE_20261020.md),
`data/geography/provenance.json`. OSM © OpenStreetMap contributors,
[ODbL](https://www.openstreetmap.org/copyright). La data del nome ZIP non viene
usata come data del rilievo. Nessuna nuova fotografia è inclusa.

## Geometria e limiti

- 36 settori di 128 m, griglia fissa a 2 m, LOD visivi a 2/4/8 m con soglie
  orizzontali 180/360 m e isteresi. Una sola mesh visibile per settore; culling
  del motore e materiali condivisi. Collisioni statiche a 2 m, 294.912 triangoli,
  indipendenti dal LOD; nessuna parete artificiale delle giunzioni nella fisica.
- Normali calcolate sul raster globale; 60 bordi condividono quote e normali
  identiche. Le gonne verticali nascondono le giunzioni fra LOD; profondità
  misurata dal massimo errore locale + 1 m. Non entrano nelle collisioni.
- Rispetto alla griglia a 2 m, errore massimo dei LOD 4 m **3,90 m**, 8 m
  **4,992 m**. La decimazione non conserva muri, gradini o dettagli del rilievo
  a 0,5 m. I LOD lontani possono discostarsi dalle linee stradali drappeggiate;
  vanno rifiniti prima della guida. Non sono errori altimetrici del LiDAR originale.
- Tutte le 91 sagome OSM del file esistente, senza lacune o tagli nell'area;
  tetti piatti e muri con collisioni. Altezza **6 m sopra il campione più alto
  dell'impronta**, fondazione sotto il più basso: scelta di blockout, non misura.
  I tag OSM `height` non vengono promossi a misure verificate. Facciate, chiesa,
  campanile e dislivelli degli accessi richiedono ricostruzione documentata.
- 266 segmenti ritagliati dalle 35 linee OSM: strade ambra, sentieri/scale magenta.
  Larghezze grafiche 4 m / 1,2 m dichiarate provvisorie; nessuna nuova collisione
  stradale. Quote drappeggiate sul terreno fisico a 2 m, non asfalto verificato.
  Nessun accesso prato–borgo inventato. PV-01 resta un punto candidato senza
  confine del prato o autorizzazione di parcheggio.

La scena non istanzia veicolo, personaggi o regole della gita. Mantiene aperte
le prove P3/P4 su parcheggio, uscita, cammino, seguito e ritorno.

## Rigenerare e avviare

Python 3.12; ambiente dedicato, dipendenze offline in `requirements-terrain.txt`.
Godot non richiede Python per leggere il risultato. Conservare lo ZIP originale
solo in una cartella privata o `build/`. Raster, archivio e derivati geografici
restano esclusi da Git finché i termini di redistribuzione non sono verificati.
Il generatore accetta solo output sotto `build/` e vi crea `.gdignore`, evitando
che l'editor importi ambienti Python o il progetto Blender derivato.

```powershell
python -m pip install -r requirements-terrain.txt -r requirements-dev.txt
python tools/build_valle_3d.py --source "C:\dati-privati\download-20261027070111018.zip"
python tools/check_valle_3d.py build/valle/valle_scene.json
godot --path . res://godot/scenes/valle.tscn
```

Oppure aprire la scena e usare F6. F5 continua ad aprire il laboratorio auto.
Se i dati locali mancano compare un messaggio con il percorso del generatore.
`-- --valle-data=C:\percorso\valle_scene.json` permette un archivio esterno.
WASD muove la camera, Q/E la sollevano/abbassano, Maiusc accelera, tasto destro
controlla lo sguardo, R ripristina la vista, 1/2 alternano strade/edifici.
La camera è uno strumento libero e può attraversare il terreno.

## Collaudo riproducibile

```powershell
python tools/validate_valle.py --godot "C:\strumenti\godot_console.exe" --blender "C:\strumenti\blender.exe" --source "C:\dati-privati\download-20261027070111018.zip" --capture
```

Include test Python e regressione Yaris, parser/formattazione/lint GDScript,
rigenerazione identica byte per byte, controllo bordi e fonti, import Godot,
confronti numerici preesistenti, raggi Jolt sui 36 settori e sui 91 tetti,
commutazione LOD senza alterare le collisioni, caduta di un corpo e commutazione
dello strato stradale. La prova senza dati deve essere esplicitamente richiesta;
un dataset mancante durante il collaudo normale fallisce. Errori nel log fanno
fallire il runner anche quando l'editor termina con codice zero.

Con `--capture` il renderer reale salva due PNG. Blender crea
`build/valle_validation/valle.blend` e verifica mesh e normali del terreno.
Log, immagini e rapporti completi in `build/valle_validation/`; sintesi pubblicabile
in `reports/VALLE_3D_VERIFICA.json`. Queste prove non costituiscono un benchmark
FPS rappresentativo né un giro completo. Riferimenti API:
[ArrayMesh e fronte orario](https://docs.godotengine.org/en/4.5/classes/class_arraymesh.html).

## Copia Windows con lavori locali

`tools/sync_valle_local.py --target "C:\Giochi\Sviluppo\Viaggio a Soffumbergo" --godot "C:\strumenti\godot_console.exe"`
aggiunge soltanto i file elencati esplicitamente nello script e i derivati locali;
controlla che la base OSM sia identica e si ferma prima di sostituire un sorgente
diverso. Appende una nota a README/roadmap e aggiunge `Avvia Valle 3D.cmd`.
Non cambia branch, scena iniziale, auto o personaggi; rapporto in
`build/valle_validation/local_sync.json` nella copia di sviluppo.

**Aggiornamento DTM:** le 41 tessere dell'intero anello sono ora disponibili e
catalogate; [copertura, differenze nei bordi e procedura](DTM_CIRCUITO_COMPLETO.md).
Prossimo incremento: gestire le sovrapposizioni con provenienza esplicita,
estendere il corridoio, poi costruire superficie stradale e accessi dai riscontri.
