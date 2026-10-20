# Tracciato di Valle di Soffumbergo — QGIS e LiDAR

Avvio: **20 ottobre 2026**. Stato: **rete OSM candidata 2D completa topologicamente e primo DTM ufficiale PCR 10 m acquisito, con 2.394 campioni del terreno validi**. Restano da verificare **geometria della strada, quote della carreggiata e datum verticale**, e resta da acquisire il LiDAR 2017–2020 a 0,5 m. [Resoconto e grafico](PROFILO_ALTIMETRICO_DTM10_20261020.md). Il sopralluogo virtuale resta parziale; cfr. `docs/CIRCUITO_SOPRALLUOGO.md`.

## Fonte e ambito

Itinerario di riferimento: **Bar Al Telefono (Faedis) → Campeglio → Monte San Lorenzo/Colloredo → Valle → ramo piazza A. Clementig (andata/ritorno) → strada per Valle → Costalunga → Canal di Grivò → Borgo Scubla → Faedis**. Conservare il link originale e le deviazioni incluse; non sostituirlo con un percorso apparentemente più corto.

Fonti verificabili:

- [IRDAT FVG, dataset 11826 LiDAR 2017–2020](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826): DTM a maglia 0,5 m, **quote ellissoidiche oppure ortometriche**, scaricabile mediante Eagle.fvg, funzione *download basi cartografiche*. La disponibilità di singole tessere sul tracciato deve ancora essere controllata.
- [Regione FVG, servizio WMS ortofoto e hillshade](https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA5/): `https://irdat-ortofoto.regione.fvg.it/geoserver/ortofoto/ows?request=GetCapabilities&service=wms`.
- [Catalogo IRDATfvg](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/home?language=it); [download CTRN e DTM 1/10 m](https://irdat.regione.fvg.it/CTRN/ricerca-cartografia/).
- [QGIS: DEM nella vista 3D, esportazione OBJ](https://docs.qgis.org/3.44/en/docs/user_manual/map_views/3d_map_view.html).

**CRS e quote:** le sorgenti GeoJSON sono EPSG:4326 **[longitudine, latitudine]** senza Z. Per misure in metri usare in QGIS **EPSG:7792**, RDN2008/UTM 33N con assi Est-Nord; alcuni prodotti regionali usano **EPSG:6708**, assi Nord-Est. Non scambiare gli assi e non ridefinire il CRS senza trasformazione. Quote **ortometriche ≠ ellissoidiche**. Il programma `tools/prepare_route.py` richiede quote ellissoidiche WGS84 verificate: campionare semplicemente un DTM non rende la quota della *superficie stradale* certificata; annotare anche incertezze e trasformazione orizzontale.

**Risultato reale:** [rapporto sul circuito candidato di 18.867,6 m](TRACCIATO_OSM_CANDIDATO_20261020.md); `data/geography/circuito_osm_candidate_20261020.geojson` contiene tutte le sezioni A/B/C/V/D/E/F in EPSG:4326 senza altezze. Non è la mesh stradale definitiva.

**Aggiornamento:** la guida operativa per **registrare grigliati regionali originali** e **acquisire la rete OSM separatamente dal borgo** è in [ACQUISIZIONE_FONTI_GIS.md](ACQUISIZIONE_FONTI_GIS.md). Un workflow opzionale produce solo un artefatto temporaneo con la rete OSM regionale, senza trasformarla in tracciato certificato.

## Prima estrazione riproducibile (senza QGIS)

Dalla radice del repository:

```bash
python tools/build_qgis_survey.py
python tools/check_project.py
```

Il generatore, senza dipendenze esterne, crea sotto `build/qgis/`:

| File | Contenuto | Limite |
| --- | --- | --- |
| `observation_anchors.geojson` | Panorami e segnaposto già censiti; in D, due estremi di riferimento (origine OSM V e panorama CIR-12) | Non sono punti topografici |
| `road_centerlines_partial.geojson` | Sole polilinee OSM 2D già documentate nei settori C e V | Non è un anello percorribile |
| `valle_context_roads.geojson` | Tratti OSM del borgo | Non copre le strade di tutto il giro |
| `valle_footprints.geojson` | Sagome OSM degli edifici | Nessuna facciata o quota verificata |
| `manifest.json` | Sorgenti, conteggi e limiti | Nessuna pendenza, larghezza o raggio |

Ogni feature conserva `origin_file`, `ref_id`, `evidence_role` e `metric_status`. **Nel settore D non esiste ancora la geometria stradale:** il generatore produce solo il vertice iniziale OSM di V-OUTBOUND e il panorama CIR-12, senza inventare una linea fra loro.

## Operazioni in QGIS

1. Aprire un progetto con CRS **EPSG:7792**; trascinare i quattro GeoJSON generati. I file sorgente restano in EPSG:4326 e QGIS li riproietta al volo. Non collegare i punti Street View in linea retta.
2. Aprire *Layer → Gestore sorgenti dati → WMS/WMTS → Nuovo*, inserire il WMS FVG riportato sopra, connettersi e selezionare uno dei layer di ortofoto/hillshade realmente proposti. **WMS/hillshade non contengono un DEM di quote utilizzabile per campionamento.**
3. Salvare `build/qgis/soffumbergo_sopralluogo.qgz`. Da Eagle.fvg scaricare le tessere del **DTM**, inizialmente per **Valle e settori C/V/D**, poi per A/B/E/F, verificando la copertura reale; non confondere DTM con DSM.
4. Conservare i raster originali **fuori da GitHub** in `build/geodata/fvg/`. Per ogni tessera registrare ID, URL, data, condizioni di riuso, checksum, CRS, tipo di quota (ellissoidica/ortometrica), risoluzione, NoData e confini. Verificare metadati con QGIS o `gdalinfo`.
5. Ricostruire le linee continue del percorso su basi riutilizzabili, confrontando la topologia con l'itinerario originale. Verificare tratti mancanti e ogni tornante in entrata, apice e uscita. **Street View** serve solo per verifiche visive: non estrarre screenshot, tracciati o texture.
6. Solo con strada planimetrica connessa e DEM validato, controllare ponte/piazzola/muro, sezioni, quote, pendenze e franco di passaggio della **coffa**. Non assegnare `elevation_status=verified` al solo valore del DTM. La geometria deve infine essere provata in Godot.

## Stato dei settori

| Settore | Materiale 2D in ingresso | Altimetria |
| --- | --- | --- |
| A, B | Osservazioni isolate | assente |
| C | Asse OSM parziale | assente |
| V | Ramo di piazza andata/ritorno OSM | assente |
| D | Due estremi, nessuna polilinea | assente |
| E, F | Punti osservati | assente |

**Fine P0 solo dopo:** rete coerente e continua di tutti i settori; proprietà metrico-altimetriche e datum registrati; tornanti censiti in progressione, larghezze e ingombri controllati; verifica della guida nel motore. La preparazione di questi file **non chiude P0**.

## Diritti

Geometrie OSM: © OpenStreetMap contributors, ODbL 1.0, https://www.openstreetmap.org/copyright. Per i dati FVG verificare la licenza specifica di ogni file scaricato prima di distribuirlo. Google Maps/Street View rimangono collegamenti e osservazioni testuali, non sorgenti di immagini o geometrie redistribuite.
