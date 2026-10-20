# Primo profilo altimetrico del circuito — dati reali FVG, 20 ottobre 2026

**Stato:** rilevamento preliminare del **terreno nudo** ricampionato a 10 m. **NON** è un profilo verificato della superficie asfaltata; la geometria della strada è ancora un candidato OSM e il riferimento verticale dei valori è da confermare. Non usare queste coordinate come input di `tools/prepare_route.py` o come mesh guidabile di Godot.

## Origine verificabile dei dati

- **Fonte:** Regione autonoma Friuli Venezia Giulia, DTM Protezione Civile; tavoletta **067-NO (Faedis)**, ricampionamento a 10 m del rilievo LiDAR 2006–2010. Formato ESRI ASCII.
- **URL originale verificato con il portale cartografico:** https://irdat.regione.fvg.it/cartogdownload/DTM_PCR/10M/6708/DTM10_PCR_067_NO_RDN2008_TM33.zip
- **Impronta SHA-256 dell'archivio:** `5e98b18802da5e49ed8fb05f0e114fdc29612907164f934238514b3f9c87d39b`. Variazioni richiedono un nuovo controllo documentato.
- **Contenuto del ZIP:** `DTM_067_NO_10m_PCR.asc`, 1.440 colonne × 1.251 righe, passo 10 m; angolo inferiore sinistro del grigliato (E, N) (370449.032, 5105582.115).
- **CRS orizzontale dichiarato:** RDN2008/TM33NE (EPSG:6708). Le coordinate **X/Y** del raster ASCII sono Easting/Northing; in trasformazione con pyproj utilizzare `always_xy=True` ed esaminare visivamente la corrispondenza con i punti noti. Il CRS verticale è ancora **ignoto** e non va desunto dai valori del raster.
- **Fonte itinerario 2D:** il candidato OSM versionato in `data/geography/circuito_osm_candidate_20261020.geojson` con condizioni ODbL.
- **Job con log dei download, impronta e campionamento:** https://github.com/Cartaz/Viaggio_a_Soffumbergo/actions/runs/39374632568.
- **Dati campionati persistenti:** `data/geography/circuito_dtm10_terrain_profile_20261020.json`; [grafico SVG](../reports/terrain_10m_profile.svg).
- **Script:** `tools/profile_dtm_route.py` e `tools/plot_dtm_profile.py`.

Il file ZIP originale non è aggiunto alla repository: rimane scaricabile dal portale FVG. La posizione dell'intero itinerario candidato è dentro la tavoletta, e tutti i campioni interpolati hanno ricevuto un valore dal raster; non è una verifica di copertura di altri prodotti, come il nuovo DTM LiDAR 2017–2020 a 0,5 m.

## Misure ottenute

La geometria OSM è stata trasformata dalla latitudine/longitudine in EPSG:6708 e densificata con distanza massima di 10 m **per segmento**; quindi si sono campionate le celle del DTM mediante interpolazione bilineare, senza riempire eventuali celle NoData.

| Settore | Punti raster validi | Intervallo di valori griglia DTM |
| --- | ---: | ---: |
| A | 466/466 | 129,383–169,904 |
| B | 255/255 | 130,128–266,819 |
| C | 548/548 | 266,176–682,590 |
| V | 71/71 | 678,417–685,484 |
| D | 198/198 | 581,082–682,590 |
| E | 644/644 | 208,586–581,082 |
| F | 212/212 | 169,904–211,606 |
| **Totale** | **2.394/2.394** | **129,383–685,484** |

Lunghezza calcolata sulla proiezione: **18.884,861 m**. Questo valore non sostituisce i **18.867,6 m** precedentemente calcolati con distanze planimetriche approssimative geografiche sul candidato OSM; la differenza dei metodi non equivale a una correzione del percorso reale.

**Interpretazione:** il DTM suggerisce una forte salita lungo B e C e la corrispondente discesa D-E. Tuttavia, **non** sono state misurate pendenze reali della carreggiata, quote altimetriche stradali, sopraelevazioni né franchi per l'albero e la coffa. I valori tabellati sono altezze memorizzate nel raster, **non altezze s.l.m. dichiarate** finché il datum verticale non sarà identificato.

## Riproduzione senza QGIS

Con Python 3.12 e il pacchetto `pyproj` per la sola riproiezione (installabile separatamente dall'ambiente di base):

```bash
python -m pip install "pyproj==3.7.2"
python tools/profile_dtm_route.py --ascii build/geodata/fvg/067_NO_DTM10_PCR.zip --source-url https://irdat.regione.fvg.it/cartogdownload/DTM_PCR/10M/6708/DTM10_PCR_067_NO_RDN2008_TM33.zip --horizontal-crs EPSG:6708 --spacing-m 10 --output build/geodata/fvg/profilo_10m.json
python tools/plot_dtm_profile.py --input build/geodata/fvg/profilo_10m.json --output build/terrain_10m_profile.svg
python tools/check_project.py
```

La ZIP da 5,7 MB va scaricata dall'URL ufficiale appena citato e **confrontata con il checksum** prima di essere usata. Nei formati ASCII il file `.asc` è contenuto nell'archivio e lo script lo legge senza installare GDAL. `build/` è escluso dal versionamento, così da non distribuire indiscriminatamente le tessere originali. Il comando non sostituisce la validazione in QGIS.

## Prossimi controlli

1. Controllare con la Regione il **datum verticale** del DTM PCR 067-NO, l'epoca e l'eventuale trasformazione geoidale. Il laboratorio di Godot richiede dati ellissoidici coerenti, oppure una trasformazione esplicita verificata.
2. Acquisire il nuovo **DTM LiDAR 2017–2020 a 0,5 m** da Eagle.fvg per i settori C/V/D e per il borgo, con tessere e licenze registrate.
3. Accertare le svolte di ogni settore e ogni tornante prima di assumere l'asse OSM come quello realmente percorso; misurare la superficie stradale e le differenze da quota terreno sui ponti, muri e terrapieni.
4. Progettare un terreno preliminare in Blender/Godot **come prototipo non collaudato**; solo dopo le verifiche realizzare la carreggiata con profilo e pendenze credibili.
5. Riesaminare il prato PV-01 e il collegamento alla chiesa senza inventare accessi.

**Provenienza e diritti:** dati territoriali © Regione Autonoma Friuli Venezia Giulia, cartografia ufficiale; attribuzione OSM © OpenStreetMap contributors, ODbL 1.0. La Regione segnala IODL 2.0 come licenza standard dei propri open data, ma verificare la licenza applicabile al singolo download prima di redistribuire i raster.
