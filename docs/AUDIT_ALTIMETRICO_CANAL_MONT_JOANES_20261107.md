# Canal di Grivò — audit DTM altimetrico e stato DSM/DBM (7 novembre 2026)

## Risultato realmente eseguito

È stato sviluppato e lanciato **tools/audit_mont_joanes_height_sources.py**, campionando i sette punti critici di Via Mont Joanes sulle **griglie originali ESRI ASCII DTM a 0,50 m** già presenti sul PC. Il riferimento orizzontale è RDN2008/TM33NE (EPSG:6708); le quote del file originale sono **ellissoidiche**, NON ortometriche.

**Stato verificato: dtm_ground_only_dsm_dbm_missing.** Il software non calcola né inventa altezze di muri, tetti, cordoli o del manto stradale. Le quote DTM sono del **suolo nudo**.

| Origine del punto | Identificativo | Quota DTM del terreno, ellissoidica (m) |
| --- | --- | ---: |
| DBTsped FVG | DBS_EDIFICATO.569250 | 261,894 |
| DBTsped FVG | DBS_EDIFICATO.569249 | 262,100 |
| DBTsped FVG | DBS_EDIFICATO.569284 | 265,231 |
| DBTsped FVG | DBS_EDIFICATO.569283 | 264,672 |
| DBTsped FVG | DBS_EDIFICATO.569248 | 262,393 |
| OSM | way/36158227 | 264,263 |
| OSM | way/36158219 | 265,249 |

**Copertura:** tutti e sette i punti ricadono nella tessera originale **Ell_DTM_06701307.asc**, nella cartella locale data/lidar/raw_20261020. Il rapporto include coordinate EPSG:6708, nomi di griglia, SHA-256 degli input e quote interpolata sui centri cella. Gli audit originari vengono identificati con SHA-256; non vengono sovrascritti.

**Esecuzione:** nella cartella di progetto, con l'ambiente Python locale:

    .\.venv\Scripts\python.exe tools\audit_mont_joanes_height_sources.py --output results\fvg_official_buildings\height_ground_20261107_v1

File prodotto e conservato solo sul PC:
results/fvg_official_buildings/height_ground_20261107_v1/report.json

## Origine ufficiale e distinzione fra prodotti

Catalogo IRDAT FVG — **Modelli altimetrici rilievo LiDAR RAFVG 2017–2020**, passo di 0,5 m:
https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826

La Regione distingue:
- **DTM**: griglia del terreno senza edificato né vegetazione.
- **DBM**: terreno ed edificato, filtrando la vegetazione; derivato dal DSM ultimo ritorno.
- **DSM primo ritorno**: superfici superiori, manufatti ed edifici con vegetazione.
- **DSM ultimo ritorno**: superfici dagli echi finali, con edificato e vegetazione in determinate condizioni.

La Regione dichiara disponibili **quote ellissoidiche e quote ortometriche**. Il DTM già in progetto ha nome con prefisso Ell_ e quote ellissoidiche. Per confrontare un DBM o DSM è indispensabile ottenerne la stessa variante verticale: non si possono sottrarre quote di datum diversi senza una trasformazione verticale valida e documentata.

Consegna ufficiale dichiarata nel catalogo: **Eagle.fvg > download basi cartografiche**:
https://eaglefvg.regione.fvg.it/eagle/main.aspx?configuration=guest

Conferma regionale di disponibilità DTM/DSM/DBM 0,5 m e condizioni di riutilizzo:
https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA4/

## Stato acquisizione DSM e DBM

**Non risultano scaricati né importati DSM o DBM ufficiali nel corso di questa fase.**

Controlli eseguiti:
1. Verificati gli originali DTM locali (41 griglie Ell_DTM) ed individuata la tessera del corridoio.
2. Sondati i GetCapabilities WCS pubblici del GeoServer FVG e del GeoServer ortofoto: il servizio risponde ma non espone coperture chiamate DSM/DBM del dataset richiesto.
3. Raggiunto con HTTP 200 il portale Eagle.fvg. Non è stato identificato un endpoint diretto verificabile per scaricare le griglie DSM/DBM necessarie; il fatto che il catalogo documenti un dataset non equivale a possederne i raster.
4. Non è stata fabbricata alcuna copia di DTM con nome DSM/DBM e non sono stati inseriti dati fittizi nel progetto.

Per l'area Mont Joanes, il centro di richiesta è circa **E=373449,112 m, N=5113947,623 m** in EPSG:6708. Il download dovrà coprire l'insieme dei punti critici, compresi quelli più a sud.

## Interfaccia per raster successivi

Lo script accetta l'argomento opzionale **--optional-surfaces-manifest**. Il manifesto deve essere in JSON locale e dichiarare:

- horizontal_crs: "EPSG:6708"
- vertical_datum: "ellipsoidal"
- source_catalog_url: il link ufficiale IRDAT sopra riportato
- products: voci **DBM**, **DSM_FIRST**, **DSM_LAST**, ciascuna con product, path (percorso locale reale), original_basename (nome originale), source_download_url (pagina o file ufficiale di provenienza), sha256 (digest reale).

I nomi raster ammessi devono iniziare con Ell_ e contenere DBM oppure DSM in modo coerente con il ruolo. Non occorre che tutti i ruoli siano presenti, ma un file non può essere sostituito con un altro prodotto.

Il programma verifica per ogni fonte aggiuntiva:
- SHA-256 del file e informazioni di provenienza dichiarate;
- EPSG:6708, datum ellissoidico, estensione coerente, griglia ESRI ASCII 0,50 m, celle NoData;
- interpolazione bilineare solo dentro l'effettiva estensione del file;
- differenze fra superficie e DTM solo dove entrambe hanno valori validi, senza chiamarle automaticamente "altezza del muro".

Per ripetere con file aggiuntivi realmente verificati usare **una nuova cartella di output**:

    .\.venv\Scripts\python.exe tools\audit_mont_joanes_height_sources.py --optional-surfaces-manifest results\fvg_official_buildings\sorgenti_altimetriche.json --output results\fvg_official_buildings\height_with_surfaces_NUOVA_VERSIONE

Il programma rifiuta la sovrascrittura dei rapporti preesistenti.

## Decisione per la ricostruzione Unreal

**Nessuna modifica ai file originali LiDAR, alla superficie asfaltata, alle mesh di edifici, alle collisioni, alla fisica della Yaris né al pacchetto attivo.**

I risultati precedenti sul giro fisico candidato f4373a62b482 indicavano intersezioni 2D con impronte OSM e FVG nel corridoio di Via Mont Joanes. Questo nuovo rapporto fornisce la **quota del suolo**, non prova contatti 3D. Un DBM non costituisce da solo un rilievo degli spigoli del muro al piano terra, né verifica ingombri dell'albero e della coffa. Solo dopo ulteriori riscontri visivi e metrici, e l'acquisizione di superfici ufficiali aggiuntive, sarà giustificato progettare una candidata corretta e collaudarla in Unreal.

Dati e documentazione © Regione Autonoma Friuli Venezia Giulia; geometrie vettoriali OSM © OpenStreetMap contributors (ODbL).
