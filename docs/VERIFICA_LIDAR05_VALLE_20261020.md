# LiDAR RAFVG 2017–2020 a 0,5 m — tentativo di download a Valle

**Esito storico della ricerca automatica precedente: non era stato possibile scaricare il DTM senza completare la verifica email di Eagle.fvg. Successivamente, il 20 ottobre 2026, l'utente ha caricato uno ZIP originale con tutte e quattro le tessere a 0,5 m, analizzate e validate. [Rapporto di acquisizione effettiva](ACQUISIZIONE_LIDAR05_REALE_20261020.md).** Non sostituire il precedente DTM a 10 m con questi metadati. Non registrare quote o pendenze stradali sulla base del solo quadro d'unione.

## Quattro tessere individuate sul borgo

Ho interrogato il **servizio ufficiale WFS** relativo al quadro d'unione DTM LiDAR 2017–2020, chiedendo le tessere incidenti con il rettangolo **lon 13,390–13,395°, lat 46,155–46,159°**.

| Codice DTM | Identificativo WFS | Date rilievo | Rettangolo nativo (Est minimo, Nord minimo, Est massimo, Nord massimo) |
| --- | --- | --- | --- |
| 06701210 | QU_DTM_LIDAR_FVG.7910 | 2020-06-23 | 375240, 5112525, 376140, 5113365 |
| 06701211 | QU_DTM_LIDAR_FVG.9822 | 2019-02-14 / 2020-06-23 | 376060, 5112525, 376960, 5113365 |
| 06701214 | QU_DTM_LIDAR_FVG.11600 | 2020-06-23 | 375240, 5111765, 376140, 5112605 |
| 06701215 | QU_DTM_LIDAR_FVG.13645 | 2020-06-23 | 376060, 5111765, 376960, 5112605 |

**Riferimento numerico del reticolo:** RDN2008/TM33NE, EPSG:6708, coordinate raster qui riportate come Est/Nord. Le tessere si sovrappongono lungo i bordi; i rettangoli non descrivono esattamente dove siano disponibili valori validi per ciascuna cella.

**Manifest completo dei quattro record:** [`data/geography/lidar05_valle_tile_manifest_20261020.json`](../data/geography/lidar05_valle_tile_manifest_20261020.json).

## Fonti ufficiali

- [Catalogo dataset 11826 — Modelli altimetrici LIDAR RAFVG 2017–2020](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826): DTM, DSM e DBM a passo 0,5 m, file con quote ellissoidiche oppure ortometriche.
- [Quadro d'unione, dataset 11769](https://geodati.gov.it/geoportale/visualizzazione-metadati/scheda-metadati?metadataid=r_friuve%3Am10905-cc-i11769).
- [Richiesta WFS originale che ha restituito i quattro record](https://serviziogc.regione.fvg.it/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=GRIGLIEGEO%3AQU_DTM_LIDAR_FVG&bbox=13.39%2C46.155%2C13.395%2C46.159%2CEPSG%3A4326&outputFormat=application%2Fjson&maxFeatures=10).
- [Eagle.fvg per il download delle basi cartografiche](https://eaglefvg.regione.fvg.it/eagle/main.aspx?configuration=guest).

## Tentativi effettivi

1. **Portale Eagle.fvg raggiungibile** e codice pubblico del frontend consultato (20/10/2026). L'interfaccia del carrello permette il download a utente autenticato; per utente *guest* passa dalle chiamate `emailcheck`, `emailcheckVerify` e `downloadGuest` e richiede codice di verifica inviato via email. Non è stato usato alcun indirizzo email o codice dell'utente e non è stata effettuata una richiesta di download autorizzata.
2. **WFS regionale funzionante**: scaricati i metadati dei quattro poligoni, non il raster numerico.
3. **WCS regionali pubblici verificati**: `irdat-ortofoto.regione.fvg.it/geoserver/ortofoto/ows`, `serviziogc.regione.fvg.it/geoserver/ows`, `irdat.regione.fvg.it/geoserver/ows`. I cataloghi GetCapabilities non elencano il DTM 2017–2020 a 0,5 m come coverage scaricabile. L'hillshade è un'immagine e non contiene le quote utilizzabili come DTM originale.
4. Nessun URL diretto delle tessere originali è stato verificato. **Stato a quel punto: 0/4. Stato successivo: 4/4 acquisiti via ZIP dell'utente.**

## Passaggio necessario per ottenere i dati reali

Aprire Eagle.fvg e utilizzare «Download basi cartografiche», individuare Valle di Soffumbergo (46,157° N, 13,393° E), selezionare **DTM 0,5 m, LiDAR RAFVG 2017–2020**, controllare i quattro codici sopra e il tipo di quote (preferibilmente ellissoidiche con metadati espliciti). Aggiungere le tessere al carrello, accedere oppure confermare un proprio indirizzo email tramite il codice del portale, quindi scaricare e decomprimere gli archivi.

Conservare **fuori dal repository** i file originali in `build/geodata/fvg/`, registrando nome, checksum SHA-256, quota ellissoidica/ortometrica, EPSG, NoData, passo reale e condizioni di utilizzo. Confrontare i quattro tagli con il DTM a 10 m e solo allora preparare le quote del terreno per la scena di Valle. Il settore V e il borgo non rappresentano l'intero circuito; anche i settori C/D/E necessiteranno di ulteriori tessere.

**Vincolo di accuratezza:** neppure un DTM a 0,5 m fornisce automaticamente le quote esatte dell'asfalto sopra ponti, tombotti o altre opere, né l'altezza libera della coffa. Tali elementi richiedono rilievi ulteriori.
