# Ingestione delle fonti geografiche — 20 ottobre 2026

**Stato verificabile:** **nessun DTM regionale acquisito**. La rete OSM regionale è stata **scaricata realmente tramite GitHub Actions**; il candidato chiuso 2D per tutti i sette settori è stato salvato e testato. I dati persistenti sono in `data/geography/osm_regional_roads_20261020.geojson` e `data/geography/circuito_osm_candidate_20261020.geojson`. Vedere [rapporto con metriche e limiti](TRACCIATO_OSM_CANDIDATO_20261020.md). Il runtime locale continua a non avere connettività GIS diretta, ma il job GitHub sì. I test comprendono fixture sintetiche **e riproduzione del dataset reale**.

Il tracciato dell'utente rimane quello fissato in `docs/CIRCUITO_SOPRALLUOGO.md`; nessuna scorciatoia o percorso turistico alternativo lo sostituisce.

## Risultato OSM già disponibile

Il job [GitHub Actions](https://github.com/Cartaz/Viaggio_a_Soffumbergo/actions/runs/39337016363) ha acquisito 1.149 ways stradali (821 candidati automobilistici preliminari). Un secondo job ha salvato la rete e la polilinea candidata OSM (18.867,6 m) nella repository; non serve riscaricare l'estratto per aprirla in QGIS. I comandi di download descritti più sotto restano disponibili per futuri aggiornamenti, mantenendo sempre i vecchi dati e la provenienza. **Nessuna quota disponibile.**

## Dati ufficiali FVG

1. [Catalogo LiDAR 2017–2020 — ID 11826](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826). Specifica un **DTM a maglia 0,50 m**, distribuito in grigliati ASCII con quote **ellissoidiche o ortometriche**. Aprire [Eagle.fvg](https://eaglefvg.regione.fvg.it/eagle/main.aspx?configuration=guest), voce «download basi cartografiche», e scegliere le tessere effettivamente comprese nel percorso. Disponibilità delle singole tessere e licenza del download da verificare.
2. Alternativa ufficiale: [ricerca cartografia regionale](https://irdat.regione.fvg.it/CTRN/ricerca-cartografia/), che presenta DTM Protezione Civile **a 1 m** e DTM a 10 m. Non scambiare il LiDAR più vecchio con quello 2017–2020: annotare fonte e periodo.
3. Dato regionale: sistema **RDN2008/TM33NE**. L'asse N-E in **EPSG:6708** differisce dall'ordine assi Est-Nord in **EPSG:7792**. Controllare le coordinate **effettive del raster**: in formati GIS alcuni programmi applicano l'ordine coordinate operativo indipendentemente dall'ordine formale dell'EPSG. Non scambiare gli assi perché le coordinate a numeri molto grandi sembrano plausibili.
4. Per l'altitudine finale del gioco servono trasformazione verticale (geoidale quando necessaria) e verifica della superficie stradale, non soltanto la quota del terreno nudo.

### Registrazione DTM dopo il download

Decomprimere i grigliati ASCII **fuori dal repository**, preferibilmente in `build/geodata/fvg/`, e dalla radice del progetto eseguire:

```powershell
python tools/register_dtm.py --input "build/geodata/fvg/TEssERA.asc" --tile-id "TESSERA" --source-url "https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826" --horizontal-crs EPSG:7792 --vertical-datum unknown
```

Sostituire nome e `--horizontal-crs` con i valori realmente riportati nella documentazione della tessera; **non usare l'EPSG dell'esempio in automatico**. Specificare `--vertical-datum orthometric` o `ellipsoidal` **solo dopo** averne letto i metadati originali.

Lo script scrive `build/geodata/fvg/dtm_catalog.json` con hash SHA256, confini numerici nel sistema del file, passo di griglia, nodata, min/max e numero celle valide. Rifiuta dati troncati, coordinate di griglia malformate o una tessera che cambia senza aggiornamento esplicito. Il datum indicato dall'operatore resta segnato come **non verificato in modo indipendente**; il file non certifica quote stradali.

Il programma attuale supporta **ESRI ASCII Grid**. File GeoTIFF o LAZ richiedono import e verifiche GIS specifiche (GDAL/QGIS), non vanno rinominati `.asc`.

## Estrazione rete stradale regionale da OpenStreetMap

Il precedente `tools/fetch_geography.py` ha due scopi storicamente sovrapposti: raccogliere rete stradale regionale e sagome locali. **Non usare il suo `--download` per questo passaggio**, perché sovrascriverebbe la base OSM documentata di Valle.

Il nuovo comando, dalla radice del progetto, separa i dati:

```powershell
python tools/fetch_regional_roads.py --download
```

Scarica un estratto Overpass limitato all'area del progetto mediante la query già registrata in `tools/fetch_geography.py`. Scrive solo in `build/geodata/osm/`:

- `regional_roads.geojson`: **rete stradale OSM 2D**, incluse possibili strade non transitabili;
- `regional_roads_provenance.json`: endpoint, query, hash, data e marcatura di ogni limite.

Se la rete esterna non è disponibile, **non produce falsi dati**. Per elaborare offline una risposta Overpass JSON già scaricata:

```powershell
python tools/fetch_regional_roads.py --input "percorso/estratto_overpass.json"
```

Per un candidato geometrico del settore B (non autorizza né garantisce l'effettiva strada usata dall'utente):

```powershell
python tools/extract_sector_b.py --input build/geodata/osm/regional_roads.geojson --output build/qgis/sector_b_candidate.geojson
```

Il grafo considera le strade OSM, ma una polilinea connessa non certifica accessibilità, direzione, pedaggi, curve, muri, raggi, pendenza o corrispondenza completa con il percorso originale. La successiva conferma va fatta settore per settore.

## Importazione in QGIS

- Preparare i vecchi livelli con `python tools/build_qgis_survey.py`.
- In QGIS aprire i GeoJSON della directory `build/qgis/` e, dopo l'acquisizione, `build/geodata/osm/regional_roads.geojson`; CRS di progetto EPSG:7792.
- Per il DTM aprire come layer raster l'ASCII Grid originale verificandone l'estensione sul borgo. Confrontare ortofoto ufficiali; usare Street View solo come osservazione visiva, senza ricalcarne pixel o distribuirne screenshot.
- Usare profili altimetrici in un secondo passaggio, dopo controllo del datum e dopo la verifica di un asse stradale continuo.
- Conservare tessere originali in `build/` (esclusa da Git); registrare specifici diritti di riuso quando noti.

## Verifiche e passaggio successivo

```powershell
python tools/check_project.py
```

I controlli automatici verificano solo la pipeline e le fixture. Mancano ancora: **download reale delle tessere**, idoneità e copertura della geometria OSM, riconciliazione del ramo di piazza e delle svolte, censimento completo dei tornanti, quote della carreggiata, collocazione del prato PV-01 e prove in QGIS/Godot.

Fonti: © OpenStreetMap contributors, ODbL 1.0; Regione FVG per i DEM (licenza puntuale da verificare). La repository non include immagini Google, screenshot, DTM regionali o una presunta strada quotata.
