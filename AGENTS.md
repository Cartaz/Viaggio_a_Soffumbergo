# AGENTS.md — Viaggio a Soffumbergo / Coffa e tornanti

## Mandato operativo
Sviluppa autonomamente il gioco 3D offline per Linux e Windows, senza attendere conferme per ogni attività ordinaria. Prima di intervenire leggi `README.md`, `docs/DECISIONI.md`, la fase pertinente di `docs/ROADMAP.md` e questo file; consulta `docs/PROGETTO.md` per le specifiche complete. Lavora per piccoli incrementi verificabili: ispeziona, implementa, prova, correggi, documenta e registra le modifiche. Non dichiarare completato ciò che è soltanto progettato.

## Vincoli inderogabili
- Esperienza: da Faedis verso Valle di Soffumbergo tramite l'anello indicato dall'utente (circa 20 km), sosta nel prato sotto il borgo, discesa dall'auto, visita libera a quattro zampe e ritorno completando l'anello senza ribaltarsi. La passeggera segue il giocatore nel borgo e deve tornare sulla coffa prima della ripartenza.
- Massima fedeltà documentata a **Valle di Soffumbergo** (chiesa, campanile, piazzetta, accessi, panorami); Faedis e località intermedie possono essere più generiche. Non inventare facciate, scorciatoie o quote presentandole come osservate. Il prato PV-01 è **solo candidato**.
- Veicolo: **Toyota Yaris Hybrid Trend italiana MY 2022 rossa, senza optional**, con foro nel tetto, albero maestro e coffa. Dinamica coerente con massa alta, sospensioni e carichi; nessun ribaltamento pilotato da soglie arbitrarie.
- Personaggi: lui guidatore, lei passeggera. Anatomia da topo naturale secondo `IMG_8548.webp`, **solo occhi più grandi** secondo `IMG_8549.png`. Bianca e Bernie sono riferimenti per palette, volti, carattere e accessori, non un invito a modificare l'anatomia in bipede. Non allungare ossa o arti: adattare seduta, volante, appoggi e prolunghe meccaniche. Riferimenti privati dell'utente non presenti nella repo pubblica.
- Non copiare nella repository immagini Disney, screenshot non autorizzati o asset di terzi senza diritti di riuso; non scegliere unilateralmente una licenza o pubblicare release.

## Mappa dei contenuti (percorsi verificati)

- **Pratica del circuito:** `docs/PRATICA_CIRCUITO.md`, scena
  `circuit_practice.tscn`, `tools/build_circuit_practice.py`,
  `godot/scripts/practice_route.gd`, `godot/tests/circuit_practice_check.gd`.
  Dieci tratti separati, cambi come riposizionamenti di allenamento, margini
  prima delle inversioni e raccordi ordinari allargati di progetto. Revisione
  documentale in `data/geography/circuit_maneuver_review.json`; nessuna manovra
  reale confermata. Gate `validate_circuit_construction.py --practice`.
  Non confondere le prove separate con il giro continuo o la visita integrata.

- **Terraforming / costruzione circuito:** `docs/COSTRUZIONE_CIRCUITO.md`,
  `tools/build_circuit_construction.py`, `tools/check_circuit_construction.py`,
  `tools/validate_circuit_construction.py`, scena `circuit_construction.tscn`.
  Superficie di progetto dell'intero candidato e terreno derivato separato,
  confronto T e punti critici F9. Quattro inversioni conservate e da rivedere;
  nessun giro fisico completo dichiarato. Configurazione in
  `data/config/circuit_construction.json`, evidenze in
  `reports/COSTRUZIONE_CIRCUITO_VERIFICA.json`. Raster e derivati fuori Git.

- **Discesa e passeggiata di prova:** `docs/VISITA_PILOTA.md`, scena
  `visit_pilot.tscn`, `tools/validate_visit_pilot.py`, test `visit_mass_check.gd`
  e `visit_pilot_check.gd`. Due corpi indipendenti, forze di sostegno con reazione
  all'auto, seguito e risalita; nessuna visita del borgo ancora certificata.
  Il pubblico usa proxy, Windows riusa i modelli locali senza pubblicarli.

- **Sosta tecnica:** `docs/SOSTA_PILOTA.md`, `parking_pilot.tscn`, generatore
  `tools/build_parking_pilot.py`, gate `tools/validate_parking_pilot.py`.
  Piazzola sintetica distinta da PV-01; E conferma solo dopo arresto stabile.
  Personaggi a bordo: discesa e visita non implementate da questa scena.

- **Guida pilota / Yaris:** `docs/GUIDA_PILOTA.md`, `docs/YARIS_PRESTAZIONI.md`,
  `godot/scenes/drive_pilot.tscn`, `tools/validate_drive_pilot.py`. 601 m del
  candidato C con sistemazione sintetica dichiarata, non asfalto verificato.
  Dati ufficiali separati dai parametri calibrati; nessun taglio di velocità.
  La variante Windows conserva i propri asset/rig/personaggi e comandi.
  Cinque checkpoint direzionali del tratto in `trial_progress.gd`: R recupera
  invalidando la prova, N ricomincia. Non sono i checkpoint dell'intera gita;
  `godot/tests/trial_progress_check.gd` funziona anche senza dati locali.

- **Circuito 3D 0.1:** `docs/CIRCUITO_3D.md`, `tools/build_circuit_3d.py`,
  `tools/validate_circuit.py`, scena `godot/scenes/circuit.tscn`. 352 settori;
  selezione di fonte per vertice esplicita, senza media, e protezione delle
  quote di Valle. Dettaglio/collisioni caricati vicino alla camera. Vedere
  `reports/CIRCUITO_3D_VERIFICA.json`. Non è la guida/visita integrata.

- **DTM intero anello:** 41 ASC originali locali in
  `C:\Giochi\Sviluppo\Viaggio a Soffumbergo\DTM Completi`, fuori Git.
  Catalogo `data/geography/circuit_dtm_catalog_20261020.json`, procedura
  `tools/catalog_circuit_dtm.py`, limiti in `docs/DTM_CIRCUITO_COMPLETO.md`.
  Asse OSM candidato coperto a passo massimo 2 m; 9 coppie di sovrapposizioni
  non identiche, 24 quote ambigue sull'asse. Nessuna media o mosaico implicito.

- **Valle 3D 0.1 (20/10/2026):** `docs/VALLE_3D.md`, scena
  `godot/scenes/valle.tscn`, generatore `tools/build_valle_3d.py`, collaudo
  `tools/validate_valle.py`, evidenze `reports/VALLE_3D_VERIFICA.json`.
  Campione 768 × 768 m, 36 settori/LOD, collisioni, 91 sagome OSM e strade
  provvisorie. Derivati locali sotto `build/`, nessun raster originale pubblico.
  Non è l'intero anello o la visita integrata. Le note storiche “nessuna prova
  Godot/Blender” non si applicano ai collaudi documentati di questa scena.
- **Vincoli e piano:** `docs/DECISIONI.md`, `docs/PROGETTO.md`, `docs/ROADMAP.md`; architettura e coordinate in `docs/ARCHITETTURA.md`.
- **Personaggi:** `references/README.md`; catalogo di 20 fonti in `references/bianca_bernie/sources.json`, guida in `references/bianca_bernie/README.md` e `SPECIFICA_MODELLAZIONE.md` nella stessa cartella.
- **Sopralluogo e territorio:** `docs/RIFERIMENTI_E_SOPRALLUOGO.md`; OSM in `data/geography/osm_survey.geojson`, provenienza in `data/geography/provenance.json`; mappa e inventario in `reports/valle_survey_map.svg` e `reports/valle_building_inventory.csv`. Sono dati planimetrici del borgo, non terreno quotato. Dal 20/10/2026 sono presenti anche `data/geography/osm_regional_roads_20261020.geojson` e `data/geography/circuito_osm_candidate_20261020.geojson`: rete e percorso topologicamente collegato **solo come ipotesi OSM 2D**, senza verifica delle svolte né terreno. Vedere `docs/TRACCIATO_OSM_CANDIDATO_20261020.md`. **Aggiornamento LiDAR 20/10/2026:** 4 raster DTM ellissoidici a 0,5 m di Valle ricevuti dall'utente, verificati (12.096.000 celle totali e giunzioni identiche), composizione TIFF e blockout GLB preparati, ma **non inseriti nella repo**; strumenti in `tools/import_valle_lidar05.py`, fonti e limiti in `docs/ACQUISIZIONE_LIDAR05_REALE_20261020.md`. I campioni sono terreno nudo; non convertire automaticamente in superficie stradale pronta.
- **Parametri:** `data/config/vehicle_lab.json`, `mouse_rig.json`, `asset_register.json` (nella stessa cartella); valori sperimentali, non dimensioni definitive.
- **Logica testabile senza editor:** `tools/coffa/physics.py`, `session.py`, `geography.py` e `tests/`. Il modello di visita Python non è ancora collegato a Godot.
- **Godot:** `project.godot` nella radice; scena iniziale `godot/scenes/lab.tscn`; logica in `godot/scripts/` (in particolare `vehicle_lab.gd`, `mouse_locomotion.gd`, `companion_follower.gd`); test preparati in `godot/tests/`.
- **Blender:** generatori `tools/blender/build_blockout.py` e `build_site_guides.py`; gli output generati sono esclusi dal versionamento.
- **Collaudi:** `docs/PREPARAZIONE_TECNICA.md` per evidenze/limiti reali, `docs/COLLAUDO_PC.md` per comandi Godot/Blender e criteri di accettazione; diritti e attribuzioni in `NOTICE.md`.

## Procedura di sviluppo autonomo
1. Scegli la prima attività non completata della fase attiva in `docs/ROADMAP.md`, rispettando le dipendenze. Se manca una decisione non bloccante, usa un segnaposto dichiarato e continua su un sottocompito verificabile. Chiedi all'utente solo per decisioni irreversibili, scelte estetiche finali, prato preciso, diritti o modifiche sostanziali al perimetro.
2. Prima di aggiungere file o dipendenze, cerca quanto esiste; conserva interfacce, coordinate e attribuzioni. Per dati geografici registra fonte, data, datum e limiti; distingui osservazione, stima e invenzione artistica.
3. Dopo ogni modifica al codice esegui `python tools/check_project.py` (test Python, integrità e report). Per GDScript usa anche `requirements-dev.txt` / gdtoolkit. Quando sono disponibili Godot/Blender, **esegui davvero** le prove indicate in `docs/COLLAUDO_PC.md`; conserva log, telemetrie e risultati.
4. Aggiorna checklist e documentazione con **prove verificabili**. Riporta nei resoconti: file toccati, comandi eseguiti, esiti, limiti, prossima azione. Esegui commit piccoli e descrittivi, senza alterare la visibilità della repository.
5. Non confondere i 28 test preparatori con test del motore. **Stato al 19/10/2026: nessuna build giocabile né prova reale in Godot/Blender verificata.** Il laboratorio è sintetico; i modelli 3D finali, l'intero circuito e la ricostruzione completa di Valle restano da realizzare.
