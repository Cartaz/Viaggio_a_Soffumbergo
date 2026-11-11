# Eagle.fvg — sorgenti LiDAR acquisite e verificate (11 novembre 2026)

## Esito operativo

**L'acquisizione delle superfici ellissoidiche necessarie al circuito è completata.** Il ZIP originale di Eagle.fvg è stato inventariato senza modificarlo. Le griglie originali DTM sono rimaste intatte, e il loro contenuto è stato confrontato tramite SHA-256 con le copie nell'archivio. Sono stati importati separatamente DBM, DSM primo ritorno e DSM ultimo ritorno.

**La build attiva Unreal e la fisica della Yaris non sono state modificate.** Tutti i controlli qui riportati usano la telemetria nativa della candidata separata f4373a62b482, non il rendering Windows 4K/60 FPS né collisioni tridimensionali complete.

## Archivio originale

| Grandezza | Verificata |
| --- | ---: |
| Dimensione ZIP su disco | 38.809.351.916 byte |
| File elencati nell'indice ZIP | 992 |
| Dimensione decompressione dichiarata | 47.465.513.500 byte |
| DTM classificati per nome | 160 |
| DBM classificati per nome | 132 |
| DSM classificati per nome | 264 |
| Nuvole LiDAR classificate per nome | 280 |
| Altri file | 156 |
| Risorse selezionate nel carrello Eagle.fvg | 1.034 |

Le **992 voci ZIP** non vanno equiparate alle 1.034 risorse del carrello; non è dimostrato alcun download mancante. L'indice ZIP è stato verificato, ma **non tutti i 992 membri sono stati sottoposti a controllo CRC integrale**. I raster selezionati per il gioco sono stati invece letti completamente, verificando CRC e SHA-256.

## Superfici altimetriche del circuito

Il nuovo strumento [extract_eagle_route_surfaces.py](../tools/extract_eagle_route_surfaces.py) ha verificato:

- **41 tessere DTM originali**, tutte identiche per SHA-256 alle copie nello ZIP.
- **123 nuovi raster ellissoidici**: per ciascuna delle 41 tessere, un DBM, un DSM primo ritorno e un DSM ultimo ritorno.
- Tutti gli originali selezionati hanno passo di **0,50 m**, stessa origine, stessa geometria raster e quote ellissoidiche riferite orizzontalmente a **EPSG:6708**. Le varianti ortometriche sono rimaste separate.

I file e i manifesti SHA-256 sono custoditi solo sul PC nella cartella ignorata da Git:
results/eagle_bundle/ellipsoid_route_20261111_v1/

## Copertura dell'intera telemetria nativa

Il nuovo [audit_eagle_route_coverage.py](../tools/audit_eagle_route_coverage.py) ha confrontato tutte le **105.215 posizioni** del giro fisico candidato f4373a62b482 con le quattro superfici. Ha esaminato l'effettiva cella raster più vicina, verificandone i valori NoData.

| Controllo | Risultato |
| --- | ---: |
| Pose fisiche registrate | 105.215 |
| Pose all'interno delle tessere | **105.215** |
| Pose con DTM valido | **105.215** |
| Pose con DBM valido | **105.215** |
| Pose con DSM primo ritorno valido | **105.215** |
| Pose con DSM ultimo ritorno valido | **105.215** |
| Pose con dati mancanti | **0** |

La copertura del **centro del veicolo** non certifica tetti, bordi stradali, collisioni o perfetta conformità al territorio attuale. Rapporto completo locale: results/eagle_bundle/route_surface_coverage_20261111_v1/report.json.

## Confronto sulle vere zone planimetriche di sovrapposizione

Il precedente confronto delle quote in corrispondenza del **centro** della Yaris non bastava: il corpo del veicolo può sovrapporsi a un'impronta edilizia soltanto su uno spigolo. Il nuovo [audit_eagle_surface_clearance.py](../tools/audit_eagle_surface_clearance.py) ricostruisce i poligoni di intersezione fra l'inviluppo della Yaris e gli edifici OSM/DBTsped. Analizza le celle LiDAR a passo 0,5 m che intersecano effettivamente il poligono, **pesando ciascuna cella per la superficie interessata**. Unisce le zone ripetute nel giro per non contare più volte la stessa area.

### Al picco di intersezione

| Fonte edilizia | Sovrapposizione planimetrica | Frazione dell'area su DBM elevato più di 0,5 m dal DTM | Media ponderata DBM−DTM | Massimo DBM−DTM |
| --- | ---: | ---: | ---: | ---: |
| DBTsped **569250** | 1,699 m² | **87,3%** | +5,38 m | +8,40 m |
| DBTsped **569249** | 1,210 m² | **96,4%** | +5,87 m | +9,04 m |
| DBTsped **569284** | 0,562 m² | 100% | +4,68 m | +7,45 m |
| DBTsped **569283** | 0,168 m² | 62,4% | +3,09 m | +5,96 m |
| DBTsped **569248** | 0,076 m² | 0% | 0,00 m | 0,00 m |
| OSM **36158227** | 0,432 m² | 23,8% | +1,22 m | +5,13 m |
| OSM **36158219** | 0,060 m² | 100% | +3,95 m | +5,82 m |

Le percentuali si riferiscono **all'area di sovrapposizione al picco**, non all'intero edificio. I target OSM e DBTsped potrebbero descrivere le stesse strutture: non sommare indiscriminatamente le rispettive superfici.

**Conclusione fondata:** le griglie DBM indicano superfici costruite elevate in molte zone di sovrapposizione fra telaio e sagome edilizie. **Non dimostrano un urto del telaio contro il muro reale**: i raster rappresentano superfici superiori e non permettono da soli di distinguere esattamente un tetto, un portico, una sporgenza, un muro di base o un errore di allineamento della cartografia. I due punti meridionali 569250 e 569249 sono prioritari.

Rapporto sorgente completo locale, con impronte SHA-256 e statistiche d'area:
results/fvg_official_buildings/vertical_contact_20261111_v1/report.json.

## Riproducibilità sul PC

Dalla cartella Unreal, con l'ambiente Python locale, usare per ogni esecuzione **nuovi nomi di output**, senza sovrascrivere i precedenti:

    .\.venv\Scripts\python.exe tools\inspect_eagle_bundle.py --archive "C:\Users\Casa\Downloads\download-20261114083722230.zip" --output results\eagle_bundle\NUOVO_INVENTARIO

    .\.venv\Scripts\python.exe tools\extract_eagle_route_surfaces.py --output results\eagle_bundle\NUOVA_ESTRAZIONE

    .\.venv\Scripts\python.exe tools\audit_eagle_route_coverage.py --tile-manifest results\eagle_bundle\ellipsoid_route_20261111_v1\manifest.json --output results\eagle_bundle\NUOVA_COPERTURA

    .\.venv\Scripts\python.exe tools\audit_eagle_surface_clearance.py --height-manifest results\eagle_bundle\official_surfaces_06701307_20261111_v1.json --output results\fvg_official_buildings\NUOVO_CONTROLLO_VERTICALI

I dati grezzi, i rapporti completi e il ZIP non vengono pubblicati su GitHub. La fonte ufficiale [Regione FVG: modelli altimetrici LiDAR RAFVG 2017–2020](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826) distingue esplicitamente DTM, DBM e DSM primo/ultimo ritorno, oltre a quote ellissoidiche e ortometriche.

## Passaggio successivo in Unreal

1. Preparare in una **candidata separata** le geometrie edilizie basate sul DBM valido nelle 41 tessere, verificando facciate, coperture, porticati e strada mediante ortofoto/panoramiche e sopralluogo.
2. Risolvere le ambiguità di posizione del muro a Via Mont Joanes prima di aggiungere collisioni alle impronte OSM/DBTsped.
3. Collaudare fisicamente in Unreal la Yaris completa di albero e coffa lungo tutto il circuito; poi verificare rendering, FPS e stabilità Windows.

Il nuovo pacchetto LiDAR completa **l'acquisizione dei dati altimetrici**, non la ricostruzione degli edifici né il gioco completo. Non sono stati modificati pacchetti Windows, asset Unreal, strada, veicolo, fisica o file DTM precedenti.

Attribuzioni: © Regione Autonoma Friuli Venezia Giulia, LiDAR RAFVG 2017–2020; © OpenStreetMap contributors, ODbL. La redistribuzione dei file originali o di mesh derivate deve rispettare le condizioni di licenza dei dati sorgente.
