# Raccordo della scarpata di Costalunga

Aggiornamento 25 ottobre: sulla base e37 già verificata senza rendering è preparata una finitura locale del margine di scolo, ancora da importare e verificare nel motore. Quote e collisioni conservate. Stato e riscontri in [Drenaggio a Costalunga](DRENAGGIO_COSTALUNGA.md). Le prove fisiche della e37 non si trasferiscono automaticamente alla nuova candidata.

Variante separata `fd61ea1aa8c4`, derivata dalla `6108bf03a38a`. Non è esportata né attivata nella distribuzione Windows.

## Difetto e intervento

Il confronto delle medesime 207 sezioni stradali con il DTM originale mostra che il precedente raccordo accentua la corrugazione della scarpata. A un metro dal bordo, la differenza seconda longitudinale ha RMS 0,90881 m nel derivato contro 0,25401 m nella sorgente. Non è corretto attribuire tutte le pieghe al rilievo originale.

La nuova variante sostituisce localmente la larghezza del raccordo dipendente dal dislivello con una sezione progettuale continua, dal piede stradale al terreno esistente. L'intervento riguarda soltanto il lato a monte del corridoio già documentato della rete, lungo circa 102,86 m. Le foto già consultate restano in `results/territory/costalunga_rockfall_extent_review_20261024.json`; nessuna nuova posa è consultata in questo incremento.

I parametri sono scelte di progetto, **non misure ricavate dalle fotografie**: piede 0,85 m, limite dei vertici modificabili 3 m dall'asfalto, raccordo esterno 0,5 m, sfumatura longitudinale 5 m e sottofondo almeno 0,08 m sotto il manto. L'interpolazione delle celle native può propagare l'effetto oltre i vertici modificati fino alla diagonale della cella da 0,5 m, circa altri 0,71 m. Non si dichiara quindi il terreno esattamente invariato a ogni punto oltre 3 m.

Sono modificati 1.032 campioni del solo settore T_04_01. Taglio massimo rispetto alla sorgente 4,316 m, ancora progettuale e da valutare nel contesto del luogo. Il DTM originale, tutti i fori e i bordi condivisi dei settori restano identici. Asfalto, cordolo, guardrail e itinerario sono conservati. Banchina e rete mantengono l'impronta precedente e seguono i nuovi triangoli nativi; la rete conserva il materiale, il distacco di 6 cm e l'assenza di collisione.

## Verifiche eseguite

- Audit indipendente dei dati salvati: `results/road_drafts/fd61ea1aa8c4/structure_geometry_audit.json`. Tutti i controlli passano. Testati 1.258 estremi delle intersezioni fra asfalto e triangoli nativi interessati dalla modifica: distacco minimo 0,10045 m. Impronta della banchina identica, rete conforme anche negli interni delle facce e fondazione del cordolo ancora interrata.
- Importazione nativa: `bank_native_import_v1.json` nella stessa cartella. Rilettura di 1.018.081 campioni e della visibilità senza differenze; 101 sonde positive sulla banchina e 102 di assenza di collisione sulla rete. Asset e mappe parent, dati attivi e materiali conservati. Nessuna modifica C++.
- Galleria `results/structure_gallery/fd61ea1aa8c4/bank_transition_editor_v1/report.json`: due direzioni, 32 eventi per prova, F11, auto completa, 4K reale e cap60. Cattura continua del cielo disattivata all'avvio, nessun GPUhang. Tutte sei le immagini native effettivamente viste; valutazione separata in `visual_review.json`.
- Scansione dell'intero percorso: `results/road_draft_checks/bank_fd61ea1aa8c4_surface_editor_v1/report.json`, passati 110.414 controlli, compresi i nove vuoti sotto gli impalcati. È una scansione, non un giro guidato.
- Giro fisico completo Editor corrente: `results/road_draft_checks/bank_fd61ea1aa8c4_full_editor_v1/report.json`, passato. Percorsi 18.859,1977 m in 5.260,7753 secondi simulati, tutte 31 le fasi e tre manovre, zero recuperi e nessun intervallo senza contatto o fuori dalla superficie di guida. DLL b2 invariata, sole forze, sterzo e freni. Prova senza rendering, non un test GPU o della futura esportazione Windows.

Tra 0,5 e 2 m dal bordo l'indice di corrugazione si riduce di oltre il 50%; a 1 m passa da 0,90881 a 0,12150 m. A 3 m aumenta invece da 0,13055 a 0,17892 m per l'interpolazione al margine dell'intervento: questo raccordo resta da rivedere. La sezione a 5 m conserva esattamente il dato sorgente.

## Limiti ancora aperti

È accettato il miglioramento locale del piede stradale, non la fedeltà visiva dell'intera scarpata. La parte alta resta uniforme e irregolare, il bordo della rete è frastagliato; roccia, muschio, vegetazione, scolo e fissaggi osservati richiedono ulteriori interventi. Restano i difetti storici di superfici nell'abitacolo e delle camere della coffa/esterna ravvicinata. Queste prove brevi non certificano la stabilità GPU dell'intero itinerario o 60 FPS stabili in movimento.

Preparazione riproducibile: `tools/prepare_bank_transition.py` con `parameters/costalunga_bank_transition_v1.json`; audit `tools/audit_bank_transition.py`; importatore isolato `tools/import_bank_transition.py`. Manifesto e firme di tutti gli input in `terrain/bank_transitions/fd61ea1aa8c4/manifest.json`. La distribuzione 4a resta attiva con cap60 e mitigazione del cielo.
