# Rilievo LiDAR oltre i settori dettagliati

Aggiornamento 25 ottobre, ore 07:44: nuova revisione diagnostica e37/pcg_census_v1 esportata e censimento Windows di tutte le 593.327 piante passato. Scansione Windows aggiornata passata, giro completo in corso. [Metodo e stato](CENSIMENTO_PCG_RUNTIME.md). Precisazione: GetNumTriangles legge i conteggi delle sezioni LOD0, non i byte dei buffer; in Windows NullRHI tali conteggi non sono disponibili, mentre tutti i 113 asset dei fondali sono identificati correttamente. La precedente espressione «audit dei buffer» va limitata ai conteggi nativi e alla separata verifica Editor della MeshDescription, senza prova di residenza GPU. Correzione esplicita in results/vegetation_census/lod_readback_scope_review_20261025.json; rapporti originali conservati.

## Stato — 25 ottobre, ore 00:20

La candidata separata **e37b807b9236** supera ora i giri fisici completi sia Editor sia Windows: **18,86 km, 31 fasi, tre manovre, zero recuperi** e nessun intervallo registrato senza contatto o fuori superficie. Nell'eseguibile esportato sono verificati auto e carico completi da 1.605 kg, una sola attesa iniziale e RHI Null. Nessun rendering, nessuna certificazione GPU o 4K/60, nessuna promozione della candidata.

Pacchetto Windows in `build/RoadCandidateWindows/e37b807b9236/v2/Windows`, eseguibile `3b4ed2ff20b53b27ebddcd1a121b55edda5fb0745dd218ca62b6617d0ffdc4e4`. Esportazione di 227 livelli con compilazione offline dei materiali senza marcatori noti di errore o sostituzione col materiale predefinito. Il tentativo v1 falliva prima del motore per il limite di 8.191 caratteri del lanciatore batch; v2 avvia direttamente AutomationTool con il runtime .NET fornito dal motore, conservando i file precedenti in `packaging_history/v1`. Il report convenzionale è la copia dell'ultimo export accettato; i file della v2 rimangono separati.

La pipeline `candidate_verification_pipeline.json` termina in `native_headless_pipeline_finished`: soltanto scansione e giro senza rendering, nessun bootstrap grafico, galleria o giro 4K. La scansione Windows passa tutti i 110.414 controlli e i nove vuoti: 113 fondali caricati, 860 nascondimenti e 850 ricomparse, nessuna violazione finale di collisione, ombre o visibilità. Rapporto aggregato e firme in `results/road_drafts/e37b807b9236/distant_validation_20261025.json`; 441 file protetti risultano identici anche dopo export e prove Windows. Tutti i processi di questa sequenza sono terminati.

Resta da verificare separatamente il contenuto PCG nell'eseguibile: il giro su asfalto non è il censimento di tutte le istanze vegetali. È il prossimo controllo senza rendering, insieme alla presenza effettiva delle mesh dei fondali nel runtime. Restano inoltre materiali/aspetto, giunti con il LOD effettivo dei Landscape, camere, rientri e contesto antropico; le prove grafiche impegnative attendono le verifiche dell'alimentazione.

## Integrazione nativa — 24 ottobre, ore23:46

La nuova candidata completa separata **e37b807b9236**, parent535938d92746, importa realmente tutti113fondali e li collega allo streaming del percorso. Passano creazione nativa, salvataggio/ricarica,2.078.060vertici e3.741.068facce riletti,339sonde negative di collisione e441fileparent/datiattivi protetti identici. La successiva lettura indipendente dei bufferLOD0passa su113asset e conferma3.741.068triangoli effettivi, con asset intatti. Entrambe le prove terminano normalmente e sono senza rendering. L'errore massimo della sola memorizzazionefloat dei vertici è0,001951cm, distinto dall'errore di approssimazione del fondale e dalla precisione del rilievo.

Passa `results/road_draft_checks/distant_e37b807b9236_surface_editor_v1/report.json`:110.414controlli di superficie,9/9vuoti sotto impalcato e nessuna differenza dalla strada attesa. Sono realmente caricati113livelli di fondale, con790passaggi a nascosto e784a visibile,0incoerenze finali e0violazioni di collisione/ombre. Alla fine107fondali sono visibili e6nascosti perché è visibile il terreno dettagliato corrispondente. Picco22Landscapevicini residenti, distinto dai113fondali leggeri. Prova senza rendering,318,16secondi; nessuna certificazione grafica o prestazionale.

C++Editor compilato in `results/distant_terrain_editor_build_v2.log` e realmente eseguito: importatore binario dedicato senza creazione di collisioni, verifica dei dati nativi e gestione dei fondali ai cambi di visibilità effettivi dei livelli dettagliati. DLLguida91ef243b61fced6728a859fb5d74993cf48f8ec112c5bc53ce3cc6051e6edee3;TerrainEditor7f9bc9e64b913a29b0eb401f83e127523b5611ecfdc4119690f991bad328fa65. I giri precedenti614fnon sono prove di questaDLL. Il giro `distant_e37b807b9236_full_editor_v1` è poi terminato e passato, come quello Windows descritto sopra. Nessun nuovo rendering dopo il power-off e distribuzione4aconservata.

Preparazione/staging `tools/prepare_distant_world.py`, importazione `tools/import_distant_world.py`, worker `tools/run_distant_world_import.py`; audit buffer `tools/audit_distant_native_buffers.py`. Dati binariSFD1verificati contro le geometrie accettate156d5c3b983b; nuovi asset/livelli in `/Game/World/Distant/R_e37b807b9236`. Nessuna riscrittura dei vecchi manifesti o dei livelli vicini. Primo tentativo da9093cce172 respinto per metodoPythonActor non esposto (`is_hidden`); ora lettura della proprietàriflessa `hidden`, precedente output preservato. Il primo buildC++v1falliva l'iterazione diTObjectPtr; v2corretto e riuscito.

`CircuitTerrainWorld` legge i campi opzionali `distant_map`, assenti nei vecchi mondi, e tiene disponibili i livelli visivi separati. Gli attori diventano nascosti quando il Landscape corrispondente è realmente visibile, con aggiornamento alle notifiche native di comparsa/scomparsa. Nessuna collisione o ombra proiettata, nessuna modifica alla fisica del veicolo. La procedura di esportazione include esplicitamente i113livelli aggiuntivi soltanto dopo una scansione nativa valida. Il verificatore attende il processo reale anche se scade l'intervallo di osservazione, senza interromperlo o riavviarlo.

Restano da verificare nel rendering aspetto, materiali, bordi in rapporto alLOD effettivo dei Landscape, passaggi di visibilità e prestazioni. I bordi coincidenti con tutti i campioni sorgente non certificano da soli l'assenza di fessure contro un Landscape visualizzato aLODpiù grossolana. Nessuna di queste proveCPU dimostra stabilitàGPU o risolve l'ipotesi sull'alimentazione.

## Preparazione geometrica — 24 ottobre, ore23:27

Preparazione geometrica e audit indipendente completati per tutti113settori. Variante dati **156d5c3b983b**, derivata dal mondo9811cad1439f; la successiva integrazione nativa e37è documentata sopra. Nessun rendering eseguito dopo lo spegnimento dell'intero PC. Distribuzione, Landscape dettagliati, strada, PCG e collisioni esistenti conservati.

Manifesto `terrain/distant_terrain/156d5c3b983b/manifest.json`; audit `geometry_audit_all_tiles_v1.json`. 2.078.060vertici circa e **3.741.068triangoli**, contro199.271.044triangoli dei quadrilateri nativi validi secondo la stessa regola dei quattro vertici: **98,12%inmeno**. Il conteggio è geometrico; non è una misura di memoria del motore o prestazioniGPU.

## Problema rilevato

Le immagini native della galleria9811mostrano vaste aree blu lontane in alcune viste. Il codice `CircuitTerrainWorld.h/.cpp` carica Landscape entro850m dal punto più vicino del settore e li conserva fino1150m. Non contiene una rappresentazione del rilievo oltre i livelli dettagliati residenti.

`results/distant_terrain_audit_9811cad1439f_v1/report.json` confronta le sette posizioni esterne effettivamente registrate con tutto il DTM disponibile. A Prestento il campionamento radiale trova terreno oltre l'inviluppo di isteresi in307direzioni su360;145direzioni hanno profili più alti di almeno0,2gradi rispetto al terreno vicino, con guadagno massimo8,065gradi. A Valle il guadagno massimo è7,836gradi. Questo dimostra che parte del rilievo noto è esclusa dal dettaglio caricato, non spiega da solo ogni pixel blu: il modello ignora vegetazione, edifici, proiezione della camera e atmosfera e campiona ogni10m. La posizione iniziale dell'auto e quella finale della camera possono differire per le brevi manovre.

L'aggiunta proposta restituisce quel rilievo usando soltanto quote già disponibili. Non costruisce montagne fuori dall'estensione delle fonti. Eventuale contesto ancora più lontano richiede altri dati verificati e un datum verticale coerente; nessunDEMesterno è stato scaricato o allineato.

## Costruzione e conservazione

`tools/distant_terrain_mesh.py` suddivide localmente i settori: celle larghe nelle zone semplici, dettaglio maggiore dove lo richiedono forma e quote. Tutti i vertici generati coincidono con campioniR16esistenti, senza rumore o displacement. I bordi esterni mantengono il passo originale0,5m dove la superficie esiste. I vertici condivisi fra celle con dettaglio diverso sono inseriti su entrambi i lati. Ogni cella con dati mancanti viene raffinata fino alla risoluzione nativa o esclusa; il dominio finale coincide esattamente con i quadrilateri aventi tutti quattro i campioni validi.

Il limite progettuale per questa rappresentazione lontana è2m nei controlli dichiarati, distinto dall'accuratezza del rilievo. Nei vertici nativi controllati lo scostamento massimo è1,4814m; nelle sonde indipendenti interne e sui lati è1,96291m. **Sono verifiche finite, non un limite continuo dimostrato su tutte le intersezioni fra triangoli.** Il terreno vicino non viene sostituito da queste mesh e conserva tutti i suoi campioni/collisioni. I dati preparati dichiarano assenza di collisione e ombre per le future componenti, ancora da verificare nel motore.

## Verifica indipendente e tentativi respinti

`tools/audit_distant_terrain_mesh.py` rilegge i fileNPZsalvati, senza usare il costruttore: controlla corrispondenza di ogni vertice al campioneR16, indice e orientamento delle facce, area e dominio delle celle, assenza di sovrapposizioni, spigoli interni aperti e giunti non conformi, tutti i campioni sui bordi e190.030vertici comuni fra settori. Passano **14.964.272sonde** nei baricentri e nei tre punti medi di ogni triangolo contro le diagonali native del terreno.

La prima preparazione uniforme7a2d1192e6a6è fermata deliberatamente dopo17settori:24.759.302triangoli, troppo pesante come fondale. Tutti gli output parziali e la motivazione sono conservati; non è un altro arresto anomalo.

La successiva ba2f2fdcefb6termina113settori ma è respinta dal controllo interno delle facce: quattro settori superano2m, massimo6,523m pur rispettando il controllo sui soli vertici raster. `tools/refine_distant_terrain.py` conserva i byte dei109settori già validi e raffina le sole celle problematiche inT_02_03,T_03_07,T_06_04,T_09_05. La nuova156d5c3b983bpassa di nuovo l'intero audit, con soglia immutata. Nessun tentativo respinto viene attivato.

## Piano iniziale d'integrazione — seguito dalle prove native sopra

Creare asset e livelli dedicati senza collisione o ombre; mostrarli quando il corrispondente Landscape dettagliato non è visibile e nasconderli soltanto dopo che il livello vicino è pronto. Verificare caricamento e assenza di collisioni nel motore senza rendering, poi il passaggio fra dettaglio e fondale, materiali, prospettive e prestazioni nella futura sessione grafica. Non caricare tutti i Landscape completi per risolvere la distanza.

Il vecchio importatore `CreateCircuitMesh` accetta solo `/Game/World/Driving/` e costruisce anche collisioni complesse: per questo l'integrazione e37usa il nuovo percorso dedicato `CreateDistantTerrainMesh`/`VerifyDistantTerrainMesh`, senza collisioni, in `/Game/World/Distant/`. I manifesti preparati sono conservati e lo staging nativo è versionato separatamente.

Le prove grafiche impegnative restano da riprendere dopo le verifiche dell'alimentazione descritte in [Stabilità grafica](STABILITA_GRAFICA.md). L'obiettivo completo resta aperto.
