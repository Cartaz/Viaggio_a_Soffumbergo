# AGENTS.md — unico progetto Unreal

## Mandato
Lavorare esclusivamente sulla versione Unreal Engine 5.8 del gioco, nella radice di questa repository. L'installazione locale completa è in `C:\Giochi\Sviluppo\Viaggio a Soffumbergo Unreal`. Godot è stato ritirato dal ramo `main`; non reintrodurre `project.godot`, `godot/` né vecchi test Godot. Per consultare il vecchio lavoro esiste il ramo `archive/pre-unreal-cleanup-2026-11-06`.

Prima di modificare il progetto leggi `README.md`, `docs/SVILUPPO_UNREAL.md`, `docs/STRADA_GUIDABILE.md`, `docs/TERRENO_E_VEGETAZIONE.md`, `docs/STABILITA_GRAFICA.md` e le note pertinenti. In caso di conflitti fra documenti, i report localmente verificati più recenti prevalgono sui piani storici; non confondere i risultati `NullRHI` con il rendering grafico.

## Vincoli
- Esperienza: guida dalla partenza a Faedis verso Valle di Soffumbergo, sosta nel prato candidato, visita libera del borgo e ritorno lungo il circuito senza ribaltamenti. Tutto offline, singolo giocatore.
- Stile **realismo fiabesco**; topolini realistici con occhi solo più grandi, nessun allungamento arti, comandi adattati ai personaggi. Yaris Hybrid Trend rossa con coffa e albero maestro. La versione locale importa asset MAH storici come base tecnica, non come approvazione finale di carrozzeria e personaggi.
- Valle e opere antropiche conformi a riscontri Street View documentati; LiDAR solo per quote del suolo, non per dedurre forme degli edifici o larghezze stradali reali. Elementi vegetali PCG sono procedurali, non censimenti botanici.
- Target Windows 4K/60 FPS su RX 6800 **non certificato**. I risultati storici di giri `NullRHI`, cook e censimenti PCG non dimostrano qualità grafica, stabilità, collisioni continue o completamento del gioco.
- Il contenuto editor Unreal binario, le tessere LiDAR, le build, i report, i risultati privati e gli asset non redistribuibili non sono nella repo. Non pubblicarli senza verifica esplicita di provenienza e diritti. Nessuna nuova licenza o visibilità della repository senza istruzione.

## File e verifiche
- Codice motore `Unreal/Source/`, configurazione `Unreal/Config/`, progetto `Unreal/SoffumbergoLab.uproject`.
- Strumenti `tools/` (Python), parametri `parameters/`, fonti `data/geography/`, LiDAR grezzo solo locale `data/lidar/raw_20261020/`.
- Gli script non devono dipendere da vecchie cartelle Godot o worktree `Soffumbergo-Unreal-5-8`. Usare percorsi ricavati da `Path(__file__).resolve().parents[1]` quando necessario.
- `python -m compileall -q tools` per validazione sintattica; per modifiche C++ compilare con Unreal su Windows e verificare comportamento nel motore completo. Eseguire i collaudi pertinenti e distinguere chiaramente esiti effettivi, osservazioni e attività residue.
- Non cancellare né riscrivere file di progetto importati, sorgenti LiDAR e baseline locali per fare passare una verifica. Conservare provenienza, hash e rapporti. Non creare nuovi ambienti paralleli.

## Conflitti fra strada e edifici di Via Mont Joanes

Prima di intervenire su sede stradale, muri o volumi in Canal di Grivò, leggi `docs/REVISIONE_CANAL_MONT_JOANES_20261106.md`. L'audit CPU `tools/review_mont_joanes_clearance.py` genera tavole SVG/HTML usando triangoli asfaltati della candidata `f4373a62b482`, telemetria e poligoni OSM verificati per hash. Le due impronte `way/36158227` e `way/36158219` si sovrappongono all'asfalto generato ma **non** sono muri reali misurati. La revisione visiva del 25/10 conferma murature al piano terra nel contesto di 36158227, senza equivalenza metrica tra facciata e poligono. Fino a un rilievo coerente non rimuovere edifici, non spostare automaticamente la strada e non attivare collisioni uniformi sulle sagome OSM. Il pacchetto attivo `4a05593a4282` e la candidata `f4373a62b482` sono diversi; non confonderne i collaudi.

## Fonti indipendenti per il corridoio Mont Joanes (7 novembre 2026)

Leggere `docs/CONFRONTO_FVG_EDIFICI_MONT_JOANES_20261107.md` prima di generare geometrie edilizie o correggere il tracciato in Canal di Grivò. Il servizio ufficiale FVG `EDIFICI` offre il `DBS_EDIFICATO` derivato da Trueortofoto 2017–2020 e due edizioni CTRN, in coordinate EPSG:6708. Le istanze WFS si acquisiscono soltanto in `results/` con tracciamento SHA e CRS controllato (`tools/fetch_fvg_building_footprints.py`). Confronto locale: `tools/compare_fvg_building_footprints.py`; audit sull'intera telemetria: `tools/audit_fvg_full_lap_clearance.py`; tavole QA: `tools/render_fvg_hotspot_overview.py`. Il dataset copre solo 240 × 240 m attorno a Mont Joanes. I 5 casi DBTsped non provano contatti reali e le edizioni CTRN possono condividere le stesse impronte. Non applicare automaticamente le sagome come collisioni in gioco. Una correzione richiede riscontri dei muri al suolo e, se reperibili, DSM/DBM regionali coerenti con il dato LiDAR e le quote del motore. Tutti i test correnti devono passare senza download di dati regionali in CI.

## Altimetria e verifiche del corridoio Canal di Grivò (7 novembre 2026)

Prima di modificare muri, tetti o superficie stradale, leggere docs/AUDIT_ALTIMETRICO_CANAL_MONT_JOANES_20261107.md. Gli hotspot del candidato f4373a62b482 hanno **solo DTM LiDAR ellissoidico validato** su Ell_DTM_06701307.asc, non DSM o DBM. Il file tools/audit_mont_joanes_height_sources.py campiona DTM 0,5 m e rifiuta input DSM/DBM aggiuntivi privi di manifesto SHA-256, EPSG:6708 e datum ellissoidico. Non trattare il DTM come superficie dei tetti, non fabbricare DSM/DBM, non sottrarre quote ortometriche da quote ellissoidiche e non interpretare l'interpolazione su un centro di traiettoria come quota certificata dell'asfalto. Nessuna correzione alla strada o alle collisioni finché i muri reali e la loro posizione non sono confermati.

## Archivio regionale Eagle.fvg in download
Prima di operare sul pacchetto ZIP della richiesta del 7 novembre 2026, consultare docs/PREPARAZIONE_ARCHIVIO_EAGLE_20261107.md. Non aprire il file Firefox .zip.part e non iniziare estrazioni su archivi incompleti. Usare tools/inspect_eagle_bundle.py per l'inventario senza estrazione completa; poi selezionare l'eventuale raster ufficiale DSM/DBM coerente con la tessera DTM 06701307. Non dedurre quote o collisioni dai nomi file e non pubblicare su GitHub dati grezzi non verificati. Non cancellare né modificare l'archivio ZIP originale.
