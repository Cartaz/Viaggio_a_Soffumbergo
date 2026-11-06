# Canal di Grivò — revisione planimetrica Via Mont Joanes (6 novembre 2026)

## Decisione tecnica

**Non attivare modifiche automatiche** alla carreggiata, alla posizione degli edifici né alle collisioni fino a riconciliare i muri realmente visibili con il tracciato. L'analisi ha confermato che l'asfalto generato della **candidata** `f4373a62b482` interseca due impronte OpenStreetMap; tuttavia le impronte non sono geometrie catastali, le panoramiche non sono georeferenziate al centimetro e non è dimostrata una collisione tra veicolo e un muro reale.

Il pacchetto attivo `4a05593a4282` non è stato modificato o collaudato nuovamente. La candidata f437 non va confusa con la geometria attiva.

## Fonti archiviate e loro limiti

| Fonte | Risultato utilizzato | Limite |
| --- | --- | --- |
| `data/geography/world_cover_20261024_buildings_v4/` | Impronte OSM delle way 36158227 e 36158219, estratte 24 ottobre 2026 | Poligoni cartografici indicativi, non muri misurati |
| `terrain/drainage_surfaces/f4373a62b482/manifest.json` | Triangoli effettivi di **solo asfalto**, esclusa la banchina, caricati dai mesh della candidata | Geometria generata di progetto, non asfaltatura rilevata |
| `results/building_context/f437_swept_chassis_20261106_v1/report.json` | Intervalli della telemetria Windows fisica, su proiezione planimetrica del telaio | Non sono misure 3D continue di collisione |
| `results/territory/canal_mont_joanes_building_clearance_review_20261025.json` | Due posizioni Street View già esaminate (agosto 2024) in Via Mont Joanes 59–61 | Facciata di pietra e spigolo osservati, nessuna misura o attribuzione univoca delle impronte |

**Osservazioni dei sopralluoghi precedenti, non nuova ispezione visiva:** il muro in pietra è presente al livello della strada, con fascia pavimentata leggermente rialzata, serramenti e angolo sporgente; l'accesso con arco è arretrato. Elementi lignei e gronda appartengono ai volumi superiori. La sorgente registra anche incertezza dovuta al mosaico della panoramica sul punto di contatto più vicino.

I link alle singole viste **registrate e realmente osservate nel precedente sopralluogo** sono riportati nel file HTML locale e nel JSON sorgente. L'assenza di nuove osservazioni non giustifica correggere arbitrariamente il poligono per far sparire l'interferenza.

## Misure calcolate realmente sui file del PC

La versione `tools/review_mont_joanes_clearance.py` ricostruisce un quadrato di **64 × 64 m** centrato sulla posa di massima intersezione per ciascun caso. Proietta alla stessa origine UE i triangoli dell'asfalto, le impronte OSM, l'itinerario e le posizioni delle panoramiche. L'HTML offre due planimetrie SVG in scala indicativa locale con **nord in alto** e una barra da 10 m.

| Way | Asfalto generato che ricade nel poligono OSM, nel riquadro | Massima sovrapposizione planimetrica del telaio interpolato |
| --- | ---: | ---: |
| [36158227](https://www.openstreetmap.org/way/36158227) | **14,677 m²** | **0,432193 m²** |
| [36158219](https://www.openstreetmap.org/way/36158219) | **12,378 m²** | **0,060389 m²** |

Le aree di asfalto non sono aree di collisione: **un'area grande di intersezione fra asfalto generato e OSM può dipendere anche da una imprecisione della mappa, da un offset stradale o da volume di tetto riflesso nell'impronta**. La presenza documentata del muro a terra impedisce però di scartare il problema come pura gronda. Per `way/36158219` non esiste ancora una corrispondenza verificata tra facciata e poligono.

**Osservazione delle fonti:** il report `f437_route_corridor_20261025_v1` elenca `current_manifest_building_mesh_records: 0`. Il successo di un giro stradale senza edifici importati non dimostra alcuna distanza di sicurezza da edifici reali.

## Risultato locale disponibile

Cartella, esclusa dal controllo versione:

`results/mont_joanes/source_plan_20261106_v5/`

File:

- `review.html`: planimetrie vettoriali SVG originali, senza fotografie o asset protetti, con collegamenti diretti alle fonti;
- `review.json`: geometrie metriche calcolate, identità delle fonti protette con SHA-256, distanze e risultati;
- `plan_36158227.svg` e `plan_36158219.svg`: planimetrie vettoriali riproducibili, pubblicabili senza fotografie.

**Tavole disponibili anche su GitHub:** [mappa way/36158227](figure_mont_joanes/plan_36158227.svg) · [mappa way/36158219](figure_mont_joanes/plan_36158219.svg) · [confronto HTML](figure_mont_joanes/review.html). Queste copie sono artefatti sintetici generati dalla versione v5 e conservati per l'ispezione; i dati grezzi e la telemetria rimangono esclusivamente locali.

Comando per rigenerare in una nuova cartella:

```powershell
.\.venv\Scripts\python.exe tools\review_mont_joanes_clearance.py --output results\mont_joanes\source_plan_NUOVA_VERSIONE
```

Non sovrascrivere le prove: ogni output deve essere versionato, mentre le sorgenti rimangono immutate. La verifica del 6 novembre 2026 ha terminato con exit code **0** e `all_source_data_unchanged: true`. **Nove test Python** complessivi della pipeline audit/visualizzazione superati, senza compilare nuovamente Unreal.

## Criteri per la futura correzione

1. Identificare per ciascuna way il segmento che rappresenta effettivamente il **muro piano terra** (e non una sagoma di tetto/cortile) confrontando viste da entrambi i versi, eventuali misure in loco e geometria OSM. Non assegnare un'altezza ai poligoni sulla base dei soli tag OSM.
2. Ricostruire separatamente la fascia pavimentata rialzata, la linea del bordo della carreggiata e la facciata; indicare origine e incertezza di ogni misura. La larghezza e la posizione della strada oggi sono parametri di progetto.
3. Proporre in una **candidata separata** un allineamento o ingombro che conservi la fedeltà ai riscontri reali, senza modificare le quote LiDAR originarie; ripetere verifiche di asfalto, spigoli e carrozzeria (inclusi albero e coffa).
4. Dopo esito accettato, eseguire prove native Unreal con collisioni reali degli edifici, percorso completo e rendering Windows 4K. Non trasferire automaticamente l'esito di precedenti candidati.

Questa indagine **non è una correzione geometrica né un collaudo del gioco**. È una base riproducibile per non compromettere la fedeltà del tracciato. Dati OSM © OpenStreetMap contributors, ODbL 1.0; le fotografie Street View non sono state copiate.
