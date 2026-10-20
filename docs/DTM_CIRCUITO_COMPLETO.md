# DTM dell'intero circuito — acquisizione del 20 ottobre 2026

Ricevute dall'utente **41 griglie `Ell_DTM_*.asc`** nella cartella locale
`C:\Giochi\Sviluppo\Viaggio a Soffumbergo\DTM Completi`.
Letti e verificati **853.275.721 byte**, **123.984.000 celle** a 0,5 m:
41 raster da 1.800 × 1.680 celle, nessun valore non finito e **nessun NoData**.
Le quattro tessere di Valle coincidono byte per byte con gli ASC già verificati
nell'archivio originario. Nessun originale è stato modificato o pubblicato.

Catalogo di impronte, estensioni e controlli:
[`data/geography/circuit_dtm_catalog_20261020.json`](../data/geography/circuit_dtm_catalog_20261020.json).
Fonte dichiarata: [LiDAR FVG 2017–2020](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826).
EPSG:6708 è assunto coerentemente con la raccolta e con le quattro tessere già
verificate; i singoli ASC non incorporano un CRS. Quote ellissoidiche secondo
il prefisso `Ell_DTM`, senza trasformazione verticale; metadati indipendenti
del datum da confermare prima della superficie stradale definitiva.

## Copertura verificata

Il candidato OSM A/B/C/V/D/E/F (18.867,6 m planimetrici, ancora da verificare
ai bivi) è stato proiettato e densificato conservando ogni vertice, con passo
massimo **2 m**. Tutti i **9.966 campioni** ricadono su dati validi.
La verifica riguarda l'asse candidato, non l'intera larghezza stradale o un
corridoio di terreno garantito; non attesta che le svolte siano quelle desiderate.

| Settore | Campioni | Senza copertura | Quote diverse fra tessere |
| --- | ---: | ---: | ---: |
| A | 2.127 | 0 | 0 |
| B | 1.089 | 0 | 0 |
| C | 2.306 | 0 | 0 |
| V | 285 | 0 | 0 |
| D | 734 | 0 | 0 |
| E | 2.489 | 0 | 17 |
| F | 936 | 0 | 7 |

## Sovrapposizioni da gestire

Confrontate cella per cella **123 coppie di sovrapposizioni**. **9 coppie**
contengono differenze; massimo globale **0,630005 m**. Questo massimo è un
confronto fra raster nelle fasce condivise, non l'errore altimetrico dell'intero
dataset. Sul candidato stradale le 24 posizioni con quote diverse hanno scarto
massimo **0,008039 m** (circa 8 mm). Le quattro tessere originarie di Valle
restano coerenti, come verificato per Valle 3D 0.1.

Il catalogatore non media le quote e non privilegia implicitamente la prima
tessera: i 24 campioni ambigui rimangono `null` nel profilo locale. Una differenza
di arrotondamento inferiore a 0,000001 m è ignorata solo per il calcolo numerico,
non come tolleranza di accettazione del terreno. **Non è stato creato un mosaico
integrale** con queste sovrapposizioni e non è stata dichiarata pronta la strada.
Il prossimo passaggio GIS deve scegliere e documentare una politica di mosaico
con provenienza per cella e verifica dei bordi del corridoio.

## Riprodurre

Con le dipendenze in `requirements-terrain.txt`:

```powershell
python tools/catalog_circuit_dtm.py --input-dir "C:\Giochi\Sviluppo\Viaggio a Soffumbergo\DTM Completi" --horizontal-crs EPSG:6708 --vertical-datum ellipsoidal
python tools/check_project.py
```

`build/circuit_dtm/dtm_catalog.json` contiene il catalogo completo;
`build/circuit_dtm/route_ground_candidate.json` il profilo del solo terreno,
nel frame locale di Valle (X est, Y alto, Z sud; ENH 375920/5112728/720).
Gli originali sono soltanto letti. Il profilo rimane locale sotto `build/`;
su GitHub vengono pubblicati soltanto script, test, metadati e statistiche.

Valle 3D 0.1 resta il campione di 768 × 768 m già collaudato. Questa acquisizione
fornisce il terreno necessario per proseguire sull'anello; non estende ancora
la scena a tutto il circuito e non trasforma il DTM in asfalto percorribile.
