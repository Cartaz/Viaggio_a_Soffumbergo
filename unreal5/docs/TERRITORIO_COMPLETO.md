# Territorio completo — stato verificato

Aggiornamento successivo: la carreggiata derivata è ora costruita e in collaudo. Consultare [Strada guidabile](STRADA_GUIDABILE.md), che distingue anche i tre ponti realmente attraversati dal quarto manufatto adiacente al bivio. Le prove descritte qui sotto riguardano il territorio originale.

Il mosaico delle 41 fonti DTM è ora importato in **113 Landscape nativi** da 504×504 m, ciascuno con 1009×1009 campioni al passo originale di 0,5 m. Il ritaglio iniziale e il suo eseguibile sono conservati. Il nuovo livello persistente è `/Game/Maps/CircuitoSoffumbergo`.

## Quote, confini e assenza di rilievo

Origine e assi sono gli stessi del prototipo: E/N/H = 375690,25 / 5112864,75 / 689,74 m; X est, Y sud, Z alto, in centimetri. EPSG:6708 e quote ellissoidiche sono conservati secondo la provenienza disponibile; gli ASC non contengono una certificazione autonoma del datum.

Una codifica R16 globale mantiene identici tutti i 202 bordi condivisi, comprese le maschere. Il suo passo verticale è 0,0121919585 m: errore di conversione massimo teorico circa 6,10 mm. Non è l'errore complessivo del rilievo. Nei punti senza copertura si importano veri fori di visibilità e collisione; nessun terreno viene estrapolato.

La rilettura dei livelli salvati verifica **115.043.153 altezze e altrettanti valori di maschera**, senza differenze. Passano 28.257 raggi su terreno valido e 4.400 raggi attraverso i fori. Errore massimo di collisione osservato: 1,0617 cm. Il motore comprime nuovamente ogni heightfield fisico: la tolleranza deriva da un ulteriore quanto R16 più 1 mm, non da una soglia scelta per occultare i risultati. Fonte locale del comportamento: `Chaos/HeightField.cpp`, `BuildData`.

Le divergenze delle fonti sovrapposte fino a 0,63 m non sono scomparse. Il mosaico seleziona il campione originale più interno alla rispettiva fonte e salva la provenienza. L'uguaglianza dei bordi esportati non dimostra che le fonti originarie fossero identiche.

## Caricamento dei settori

L'incremento usa **level streaming nativo Unreal** con livelli Landscape separati. World Partition era la direzione inizialmente ipotizzata; non viene dichiarato implementato. Questa scelta permette di conservare tutti i settori e di verificare esplicitamente caricamento, collisioni e scaricamento.

Parametri attuali di progetto: richiesta entro 850 m dai limiti del settore, scaricamento oltre 1150 m, verifica di disponibilità entro 120 m dall'auto. All'avvio la gravità e le velocità del veicolo restano sospese finché il sostegno è disponibile; la fisica non viene sostituita con una posa imposta. La telemetria conta questi intervalli: un giro completo dovrà dimostrare che non ricompaiono durante la guida normale.

La prima immagine dell'eseguibile mostrava sottili fessure geometriche lontane, causate dai Landscape indipendenti che sceglievano LOD separati. È stato applicato il gruppo nativo comune `LODGroupKey=20261022` a tutti i 113 livelli, senza cambiare quote o collisioni, nuovamente verificate. Questa funzione è prevista da `LandscapeProxy.h` per raccordare i bordi tra Landscape distinti e ricava la griglia comune dalle trasformazioni, senza imporre lo stesso LOD a tutto il territorio. Rapporto: `results/world_lod_stitching.json`. La conferma visiva riguarda le immagini effettivamente ispezionate, non ogni possibile visuale in movimento.

Una sonda diagnostica nel motore esamina **19.010 punti**, con 19.010 contatti corretti e nessun errore oltre tolleranza: 9.959 centri della griglia più vicini ai campioni del percorso candidato, poi 9.051 punti sui confini dei settori e ai loro lati. Errore massimo 0,861 cm. La prova carica e scarica realmente i livelli; massimo osservato 23 settori visibili. L'ordine delle sonde salta fra confini lontani: i circa 51 secondi di esecuzione e il numero di caricamenti non sono una misura della guida o delle prestazioni grafiche.

Le tre manovre Chaos di 15 secondi passano anche nel nuovo livello: fermo, breve avanzamento e retromarcia con arresto; quattro contatti finali, massa 1605 kg, Yaris Hybrid MAH con coffa e due occupanti. Un solo intervallo iniziale di attesa del terreno, zero ripartenze richieste. **Non è ancora un giro dell'itinerario.**

Evidenze: `results/world_tiles_import.json`, `world_terrain_validation.json`, `streaming/circuit_terrain_survey.json`, `circuit_vehicle_checks.json`. Il pacchetto Windows esteso ha una cartella separata `build/CircuitWindows/Windows`. Dopo il gruppo LOD comune è stato ricreato ed eseguito: **19.010/19.010 sonde passano nell'eseguibile**, poi passano le tre manovre con rendering 3840×2160 nel profilo C. Confermati veicolo completo, massa dinamica 1605 kg, quattro contatti finali, arresto, zero recuperi e una sola attesa iniziale del terreno. Passa anche il vero bootstrap indicato dal nuovo lanciatore.

Rapporti correnti: `results/streaming_packaged/`, `circuit_vehicle_packaged_rendered_C_checks.json`, `circuit_bootstrap_check.json`, `circuit_stage_validation.json` e `circuit_build_manifest.json`. L'immagine effettivamente ispezionata è `private/screenshots/circuit_lidar_packaged_lod_group_4k.png`: le sottili fessure bianche osservate prima non sono visibili in questo fotogramma. Restano materiali provvisori, assenza di strada/borgo/vegetazione estesa e verifica delle visuali in movimento. **Le prove brevi non dimostrano un giro completo né 60 FPS sul gioco finito.**

## Vincoli per la strada

I 63 tratti ripidi sono raggruppati in 20 aree di revisione. Le osservazioni effettivamente aperte in Google Street View sono salvate con URL e data immagine in `results/territory/streetview_verified_20261022.json`; le immagini non sono asset del gioco.

Sono individuati quattro attraversamenti mappati sull'itinerario e confermati visivamente: ponte SR356 a Faedis, ponte SR356 presso Campeglio e due su Via Monte Joanes. Le dimensioni metriche e le quote degli impalcati restano da ricavare/progettare e verificare; la vista panoramica non le misura. Le loro superfici devono restare separate dal terreno sottostante, senza trasformare il canale in un rilevato pieno. Inventario in `results/territory/bridge_review.json`.

Le sezioni numeriche di ciascun ponte sono già campionate dal mosaico in `results/territory/bridge_cross_sections.json`: quote ogni metro in longitudine, con sette campioni trasversali da −8 a +8 m. Una retta diagnostica delle rampe esterne trova dislivelli verso il basso fino a circa 3,89 / 4,44 / 3,77 m in tre attraversamenti; presso il ponte più basso di Canal di Grivò il centro DTM resta invece quasi continuo. La retta non è una quota rilevata dell'impalcato. Nel quarto caso il DTM potrebbe includere o interpolare il ponte: non certifica il terreno sotto l'impalcato e non deve diventare automaticamente un volume pieno.

Restano necessari: profilo e carreggiata continua, raccordi alle intersezioni, manovre alle tappe di andata/ritorno, giri completi con sole forze e comandi, verifiche dell'eseguibile in movimento e misure 4K/60. La vegetazione PCG collaudata appartiene ancora al ritaglio iniziale: non è già estesa a questi 113 settori.

## Riproduzione

1. `build_unreal.ps1` compila il codice Editor.
2. `tools/export_world_tiles.py` prepara i raster dalle fonti; non è necessario ripeterlo senza modifiche alle fonti.
3. Eseguire `tools/import_world_tiles.py` con l'Editor Python; riprende il giornale e conserva mappe non riconosciute. Una prova limitata non chiude l'importazione.
4. `tools/prepare_circuit_world.py` pubblica il manifesto di soli livelli verificati.
5. `tools/run_circuit_survey.py` esegue la sonda; `--packaged` usa il pacchetto Windows.
6. `tools/run_lidar_checks.py --circuit` esegue le manovre; aggiungere `--packaged --render --preset C` per l'eseguibile a 4K.
7. `package_lidar.ps1 -Circuit` include esplicitamente tutti i livelli nella cottura: l'argomento UAT `-map` sostituisce la lista editor `MapsToCook`, quindi indicare il solo livello persistente non include i livelli caricati tramite stringhe JSON.
