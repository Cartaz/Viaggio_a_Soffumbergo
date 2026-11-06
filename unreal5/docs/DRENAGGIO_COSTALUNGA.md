# Margine di scolo a Costalunga

**25 ottobre, ore 08:19:** importazione nativa senza rendering completata e passata sulla candidata f4373a62b482. Dopo salvataggio e ricarica restano identici 6.168 PCG locali, trasformazioni, mesh e collisioni; 1.018.081 quote e fori riletti senza differenze. I 667 file parent/attivi protetti rimangono invariati. Scansione completa aggiornata in corso, poi giro Editor e solo successivamente esportazione/prove Windows. Materiale e texture sono nativi, ma aspetto e prestazioni non sono ancora verificati. Le parti di preparazione sotto descrivono la fase precedente.

Il 25 ottobre sono riesaminate due panoramiche Google Street View di agosto 2024: [prima posa](https://www.google.com/maps/@?api=1&map_action=pano&pano=_MGYQoVLuzA0e1RgdV4QlA&heading=90&pitch=-18&fov=75), [posa vicina](https://www.google.com/maps/@?api=1&map_action=pano&pano=B7tuOv0jtcOfFiQszIxxUA&heading=90&pitch=-18&fov=75). Il basso cordolo muschioso, il margine stretto verso l'asfalto e la rete sulla scarpata sono elementi distinti. Foglie, vegetazione e deformazioni della panoramica impediscono di misurare una sezione della canaletta. Nessuna griglia o serie regolare di scarichi è confermata da queste due viste; non se ne deduce l'assenza altrove.

Le osservazioni sono in `results/territory/costalunga_drainage_review_20261025.json`. Nessuna fotografia entra negli asset del gioco. Restano vincolanti le istruzioni dell'utente sugli elementi antropici; le quote del terreno rimangono basate sul LiDAR e le dimensioni della geometria già progettata non diventano misure fotografiche.

## Spazio nella geometria attuale

`tools/audit_drainage_margin.py` controlla 260 sezioni dei 44 solidi del cordolo, con passo longitudinale non superiore a 0,1 m e dieci sonde attraverso ogni margine: 2.600 punti in tutto. Si usa il bordo esatto delle mesh dell'asfalto e si confrontano i triangoli R16 con le superfici stradali/banchine già esistenti.

Nel mondo e37 il margine calcolato misura circa **0,1697–0,1719 m**. Tutte le sonde ricadono anche sulla banchina; la superficie di supporto superiore è fra **0,9 mm e 119 mm sotto il bordo dell'asfalto**. Sono valori della geometria di progetto esistente, non dimensioni del luogo misurate nelle foto, e i campioni non costituiscono una dimostrazione di massimi continui. Non sono prove idrauliche o collisioni eseguite nel motore.

Rapporto e sezioni: `results/drainage_margin/e37_costalunga_20261025_v1/`. Input conservati, nessuna escavazione o modifica alla superficie. Il primo intervento può quindi essere una finitura dei triangoli già presenti; un eventuale nuovo scavo richiederebbe una variante separata e altre verifiche.

## Variante nativa in verifica

**f4373a62b482**, parent e37/pcg_census_v1. Dati in `terrain/drainage_surfaces/f4373a62b482/manifest.json`; candidata in `results/road_drafts/f4373a62b482`. Preparazione: `tools/prepare_drainage_surface.py`, parametri `parameters/costalunga_drainage_surface_v1.json`.

È pronta una maschera geometrica 1024×1024, passo 0,02 m, per la finitura procedurale di pietra/cemento e muschio sul solo margine della banchina. Il poligono di circa 3,576 m² è ritagliato contro le impronte esatte dell'asfalto e del cordolo. Risultano 5.765 texel non nulli, con margine matematico minimo di circa 1,76 mm per il supporto del filtro bilineare rispetto al poligono. Il limite vale per i valori originali, al mip base: **importare senza mipmap e senza compressione a blocchi**, con filtro bilineare, sRGB disattivato e bordi clamp. Il colore e gli scostamenti della maschera sono scelte artistiche dichiarate.

`drainage_mask_audit.json` passa; non dimostra ancora correttezza degli UV nativi, del materiale cotto o dei pixel. La variante ora ha materiale, texture e livello nativi salvati e ricaricati. Passa la nuova scansione Editor di 110.414 punti e nove vuoti; il giro completo è in corso. Windows, lettura del materiale da un processo fresco e immagini restano da verificare a questo aggiornamento. Non attribuirle automaticamente le prove della e37.

L'importazione duplica soltanto il livello T_04_01 e il materiale di banchina, assegnandolo come override al componente. Mesh, collisioni, materiale fisico, quote/fori, PCG, asfalto, cordolo e fondali sono conservati. La modifica prevista riguarda base color e l'unione della maschera di opacità nel solo margine; fuori dalla maschera deve restare il ramo originario. Nessuno spostamento dei vertici aggiunto. Il confronto numerico dopo salvataggio e ricarica passa per tutte le trasformazioni e le 6.168 istanze PCG locali; non usa rappresentazioni testuali con indirizzi di memoria.

Dopo l'importazione servono le verifiche native della nuova candidata; il rendering del materiale e i controlli visivi attendono la verifica dell'alimentazione. La distribuzione attiva e la e37 già collaudata restano conservate. Non è una canaletta definitiva approvata.

Importatore: `tools/import_drainage_surface.py`; worker: `tools/run_drainage_surface_import.py`. Journal `results/road_drafts/f4373a62b482/drainage_native_import.json`, sentinella all_imported=true, worker terminato con codice zero. La verifica del materiale da un nuovo processo è preparata in `audit_drainage_assets.py` / `run_drainage_asset_audit.py`, ancora da eseguire dopo il giro. La texture nativa usa TC_GRAYSCALE, sRGB false, nessun mip, filtro bilineare, clamp e sampler LinearGrayscale. Il controllo di queste impostazioni non equivale alla lettura dei byte del materiale/texture nel Windows cotto o a una prova grafica.
