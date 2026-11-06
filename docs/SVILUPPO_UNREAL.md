# Sviluppo Unreal — 22 ottobre 2026

## Incremento eseguito

**Aggiornamento territorio esteso:** il successivo incremento importa tutti i 113 settori Landscape e verifica il caricamento nativo. Quattro ponti sono confermati in Street View. Stato corrente, numeri e limiti in [Territorio completo](TERRITORIO_COMPLETO.md); l'elenco seguente conserva le evidenze del primo ritaglio.

1. **Landscape verificato.** Importazione nativa del ritaglio 505×505 a 0,5 m. Rilettura integrale identica al file R16; 81/81 raggi sul terreno corretto, errore massimo 0,014213 cm nei campioni controllati. Errore massimo della conversione delle quote originali a R16: 0,0004215 m. Sono due verifiche distinte. Le altre tessere non sono ancora importate in questo livello.
2. **Maschere geografiche.** Riutilizzate le estrazioni OSM locali con hash e provenienza. Copertura forestale e prati sono trasformati in EPSG:6708 e allineati ai centri dei campioni LiDAR. Posizioni dei singoli alberi e specie non sono considerate osservate. Assenza di dati significa nessuna vegetazione. Esclusioni conservative di progetto: 5 m dagli edifici, 8 m dagli assi delle strade, 6 m dagli assi dei sentieri. Queste distanze includono margine per la chioma e non descrivono larghezze rilevate.
3. **Generazione nativa.** Tre varianti di albero, due arbusti e un ciuffo d'erba creati in Unreal dal generatore parametrico del progetto; ognuno ha tre LOD. Il grafo PCG campiona il Landscape, applica maschera e limiti di pendenza, varia scala/rotazione con seme esplicito e genera istanze con distanze di visibilità differenziate. Alberi e arbusti sono forme botaniche generiche da rifinire; non sono una ricostruzione delle specie del luogo. Collisione dei tronchi e vento restano aperti.
4. **Ripetibilità.** Quattro generazioni reali: prima disposizione, stesso seme, seme diverso, ripristino del seme. La prima, seconda e quarta hanno la stessa impronta delle trasformazioni; la terza cambia. Risultato finale: 132 alberi, 274 arbusti, 1.115 ciuffi d'erba. Zero violazioni della maschera nei punti generati controllati. Restano da validare distanze effettive fra chiome e passaggi di LOD in movimento.
5. **Prima guida sul rilievo.** Il livello usa il vero veicolo Chaos e non aggiunge il piazzale sintetico. Partenza vicina a un asse OSM, scelta per la lieve pendenza del DTM (circa 1,82°), non per una carreggiata già verificata. Tre prove a 120 Hz passano: fermo, breve avanzamento e breve retromarcia, con frenata e quattro contatti finali. La caduta iniziale del veicolo dalla posizione di spawn contribuisce al picco di velocità riportato; non è una misura di accelerazione del motore. All'utente sono disponibili guida, freno, tre viste, retromarcia, ripartenza ed uscita.
6. **Materiali e luce.** Materiali provvisori, foglie a due facce e variazione per istanza. Prima acquisizione 4K sovraesposta: non valida per una revisione artistica. Esposizione e compatibilità dei materiali con le istanze sono state corrette; conservare le acquisizioni successive e distinguerle dal primo tentativo. Nessuna qualità finale approvata.
7. **Eseguibile Windows.** Creato realmente il pacchetto Development e provato senza editor: fermo, avanzamento e retromarcia passano anche con rendering 3840×2160 e passo del gioco variabile. I CSV confermano quattro contatti finali e arresto. La creazione del pacchetto ha richiesto circa 125 secondi su questo PC. Il lanciatore usa il pacchetto locale.
8. **Inventario esteso.** Lette tutte le 41 tessere: 123.984.000 campioni sorgente validi, zero NoData nei file forniti. Mosaico a passo originale 0,5 m, 10.140×12.780 celle includendo le zone senza copertura. Controllati 24.324.800 confronti di sovrapposizione con la sorgente già selezionata: 33.195 differenze oltre 1 mm e massimo circa 0,63 m. Non si dichiara che tutte le giunzioni siano identiche. Nelle sovrapposizioni si conserva un valore originale della tessera il cui campione è più lontano dal bordo; nessuna media o lisciatura. La provenienza per cella è salvata e le giunzioni richiedono revisione prima dell'importazione estesa.
9. **Profilo territoriale candidato.** Ricavati 9.959 campioni di quota lungo il tracciato OSM candidato, senza campioni mancanti. Segnalati 63 tratti fra campioni con pendenza del suolo oltre il 20%: sono punti da rivedere per allineamento e profilo stradale, non rampe che il gioco deve copiare alla cieca. Non vengono identificati come ponti o errori del rilievo senza altri riscontri. Il mosaico esteso non è ancora il mondo importato in Unreal.

## Evidenze

- `results/landscape_collision.json`: dato importato e collisioni.
- `terrain/valle_first/vegetation_mask.json`: fonti, trasformazione, margini e copertura.
- `results/vegetation_generation.json`: quattro generazioni, impronte e conteggi.
- `results/lidar_vehicle_checks.json` e `results/lidar_vehicle/`: tre prove nel motore, CSV e metadati.
- `parameters/terrain_spawn.json`: punto, orientamento e limiti della partenza diagnostica.
- `results/lidar_windows_packaging.json`, quando presente: esito della creazione del pacchetto, distinto dalla sua esecuzione.
- `results/lidar_vehicle_packaged_rendered_checks.json`: tre prove reali dell'eseguibile esportato a 4K.
- `results/lidar_vehicle_packaged_rendered_C_checks.json`: ripetizione riuscita delle tre manovre nel pacchetto aggiornato con profilo C.
- `results/package_default_boot.json`: avvio riuscito dal vero eseguibile di lancio, senza argomento della mappa; asset completi e massa dinamica 1.605 kg verificati.
- `results/lidar_mosaic_validation.json`: celle valide, fonti e divergenze delle sovrapposizioni.
- `results/territory/coverage_route.png`, `route_terrain_anomalies.csv` e `results/territory_review.json`: copertura e punti da rivedere sul tracciato candidato.
- `results/current_build_manifest.json`: impronte di sorgenti, asset e binario locale.

## Diagnostica del renderer a 4K

Misure sull'eseguibile Windows con camera fissa e veicolo congelato, scena di soli 252×252 m. Ogni profilo ha un passaggio di 60 secondi dopo 30 secondi di riscaldamento; non sono tre ripetizioni e non è una sequenza rappresentativa P3. Risoluzione effettiva 3840×2160, scala scena 100%, risoluzione dinamica disattivata. La fisica congelata non produce misure valide di massa dinamica: il rapporto lo segnala; le prove di guida sono separate.

| Profilo | FPS medi | Frame time p95 | Frame time p99 |
| --- | ---: | ---: | ---: |
| A, raster leggero | 61,32 | 16,62 ms | 16,77 ms |
| B, qualità alta e Lumen | 57,47 | 17,69 ms | 17,87 ms |
| C, bilanciato e Lumen | 69,21 | 14,76 ms | 14,84 ms |

Il profilo C conserva Lumen e il rendering nativo 4K, usa qualità intermedia di distanza/ombre/postprocess e riduce al 100% il sovracampionamento della storia TSR, prima al 200%. Questo parametro riguarda la storia temporale, non abbassa la risoluzione della scena. Le immagini statiche sono state ispezionate; stabilità dei dettagli in movimento e qualità finale restano da verificare. Il lanciatore sceglie C e il gioco manuale limita il ritmo a 60 FPS. Il risultato parziale non certifica il target dell'intero gioco.

CSV grezzi, impostazioni, tempi e limiti in `results/lidar_render_diagnostic/` e `results/lidar_render_diagnostic.json`. Le allocazioni delle texture riportate dal motore non sono la misura dell'intera VRAM residente.

## Prossime attività

- Rifinire la resa e completare la verifica visiva con camera in movimento; pacchetto Windows e tre prove esportate di base già eseguiti.
- Completare la prova Windows del territorio esteso e poi attraversare i confini con l'auto: importazione completa e sonda del caricamento nel motore sono già riuscite.
- Ricostruire la carreggiata con un profilo e larghezze documentati; distinguere ponti, muri e superficie stradale dal terreno nudo.
- Aggiungere il borgo soltanto dai riscontri disponibili; mantenere le lacune esplicite.
- Rifinire vegetazione, materiali, vento, collisioni e livelli di dettaglio; validare pelo, tessuti e personaggi nel realismo fiabesco richiesto.
- Migrare animazioni, sosta, discesa, visita con compagna al seguito e ritorno; conservare masse e lunghezze degli arti.
- Misurare una scena rappresentativa e poi il gioco completo sul target Windows 4K/60. Le prove brevi o un'immagine 4K non certificano questo obiettivo.
