# Tracciato OSM — candidato planimetrico del 20 ottobre 2026

**Stato:** rete regionale OSM realmente acquisita e candidato 2D connesso in sette settori. Non è un rilievo certificato, non ha quote e non è una mesh guidabile.

## Provenienza verificata

- Fonte geometrica: © OpenStreetMap contributors, **ODbL 1.0**; servizio `https://overpass-api.de/api/interpreter`; query conservata in `tools/fetch_geography.py`.
- Acquisizione: [GitHub Actions #39337016363](https://github.com/Cartaz/Viaggio_a_Soffumbergo/actions/runs/39337016363); risposta delle ore 22:45 UTC del 19/10/2026, base OSM datata **2026-10-19T22:43:51Z**.
- SHA256 del payload originale: `95b742820c9ae5013d21ee032ee7796dfa7085f0782c1bc996a8b648dfdf81c3`.
- **1.149** ways OSM stradali estratti; **821** marcati solo come possibili candidati automobilistici.
- Rete: `data/geography/osm_regional_roads_20261020.geojson`; provenienza: `data/geography/osm_regional_roads_20261020_provenance.json`; tracciato chiuso candidato: `data/geography/circuito_osm_candidate_20261020.geojson`.
- Algoritmo riproducibile: `tools/reconstruct_loop_candidate.py` con test su dataset reale in `tests/test_reconstruct_loop_candidate.py`.

Le coordinate del tracciato sono derivate **solo da OSM**, non da pixel, screenshot o linework Google. L'itinerario Google originale resta un riferimento per i 24 passaggi, conservando le brevi deviazioni di Campeglio e Canal di Grivò.

## Lunghezze per settore

Le lunghezze OSM sono approssimazioni **orizzontali da coordinate 2D**. Quelle dell'app sono somme di istruzioni *arrotondate* e non vanno scambiate per un rilievo.

| Settore | OSM candidato | Istruzioni app | Differenza |
| --- | ---: | ---: | ---: |
| A | 4.152,3 m | 4.009 m | +143,3 m |
| B | 2.068,6 m | 2.020 m | +48,6 m |
| C | 4.396,7 m | 4.300 m | +96,7 m |
| V | 533,7 m | 530 m | +3,7 m |
| D | 1.321,8 m | 1.400 m | −78,2 m |
| E | 4.579,2 m | 4.563 m | +16,2 m |
| F | 1.815,3 m | 1.872 m | −56,7 m |
| **Totale** | **18.867,6 m** | **18.694 m** | **+173,6 m** |

Maps indicava 18,7 km per il percorso completo. La vicinanza delle lunghezze è un controllo di plausibilità, **non** conferma di identità della strada, di tornanti, sensi unici o percorribilità. Le distanze di aggancio ai panorami sono registrate come attributi GeoJSON.

## Risultati e limiti

- **Implementato e testato:** download di una rete OSM completa nell'area; grafo candidato dei settori A-B-C-V-D-E-F; ritorno a Faedis chiuso nel grafo; verifica di regressione contro il GeoJSON salvato.
- **Non verificato:** che le curve siano tutte quelle del percorso dell'utente; legalità di svolte e sensi unici; carreggiata e accessibilità con auto, albero e coffa; copertura continua di Street View.
- **Non acquisito:** DTM/DEM reale sul circuito, datum verticale, quote della superficie stradale, profilo, pendenze, raggi, larghezze, inclinazione trasversale e altezza libera di cavi/rami. Non convertire il candidato in mesh guidabile.

Da controllare in ordine: **A** uscita bar e tappa Campeglio; **B** tornanti Monte San Lorenzo–Colloredo; **C** curve via Prestento e prato PV-01; **V** piazza, inversione e accessi; **D** continuità dei 1,4 km senza saltare curve; **E** svolte Costalunga e denominazione via Juretigh; **F** Canal di Grivò, Borgo Scubla, via dei Castelli e rientro bar.

## Riproduzione

```bash
python tools/reconstruct_loop_candidate.py --input data/geography/osm_regional_roads_20261020.geojson --provenance data/geography/osm_regional_roads_20261020_provenance.json --output build/qgis/circuito_osm_candidate.geojson
python tools/check_project.py
```

Importare il GeoJSON risultante in QGIS (EPSG:4326, nessuna quota); per misure metriche locali utilizzare EPSG:7792 e una trasformazione esplicita, non cambiare a mano il datum. La fase successiva è acquisire DTM con datum verificato e confermare la geometria e la percorribilità tramite rilievo progressivo.

Altri dettagli: [Guida QGIS/LiDAR](QGIS_LIDAR_SOPRALLUOGO.md), [acquisizione delle fonti](ACQUISIZIONE_FONTI_GIS.md) e [sopralluogo originale](CIRCUITO_SOPRALLUOGO.md). **P0 resta aperta**.
