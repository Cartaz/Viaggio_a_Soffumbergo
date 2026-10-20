# Valle di Soffumbergo — DTM LiDAR 0,5 m acquisito, 20 ottobre 2026

**Stato verificato: ricevute quattro griglie originali di terreno nudo, elaborate in un GeoTIFF e in un GLB di prova.** I raster originali e i derivati non sono stati pubblicati nel repository; sono disponibili nella conversazione con il caricamento dell'utente. Il **terreno** non equivale a strada, edificio o terreno già verificato nel motore.

## Provenienza delle tessere

Dataset ufficiale: [Modelli altimetrici LiDAR RAFVG 2017–2020, 0,5 m](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826), archivi scaricati dall'utente tramite Eagle.fvg. Il prefisso **Ell_DTM_** identifica la variante di quote **ellissoidiche**. Riferimento orizzontale **EPSG:6708** (RDN2008/TM33NE), coordinate raster numeriche Est/Nord. Non è stata operata alcuna conversione in quote ortometriche.

Archivio di origine: `download-20261027070111018.zip`, dimensione **26.297.175 byte**, SHA256:
`bd715cd7c9b3820646f93f9e918cab1159950f47c2df5fc39e0218fc564a6a14`.
Il nome dell'archivio è quello caricato dall'utente, non la data del sopralluogo.

| Tessera | File sorgente | SHA256 ASC |
| --- | --- | --- |
| 06701210 | `Ell_DTM_06701210.asc` | `087ac4f775ab56597b56afcbd714c2932f1cba3b22c4679adae6c398cbce5cce` |
| 06701211 | `Ell_DTM_06701211.asc` | `a0df530ca24eb8e30a8f6accbd5228a3196deacb5bb3864adea62eb81836c388` |
| 06701214 | `Ell_DTM_06701214.asc` | `b9479d08184f0e390bf4ba7bc2779086a45b17d96a8aa3e64b00d5598bbae2b1` |
| 06701215 | `Ell_DTM_06701215.asc` | `a907b2106d486eaad64dddc85dc3fa7e02d272ea2ca978743c4ec96d27c41991` |

Ogni griglia contiene **1.800 × 1.680** celle da **0,5 m** senza valori `NoData`. La sovrapposizione sui bordi misura **80 m**: il confronto cella per cella restituisce **differenza massima 0 m**. Il mosaico unito ha **3.440 × 3.200 = 11.008.000** celle, copre **1.720 × 1.600 m** ed ha estensione nativa Est **375240–376960**, Nord **5111765–5113365**. I quattro file sono integri, senza difetti CRC. Dati verificati anche nel manifest [`data/geography/lidar05_valle_tile_manifest_20261020.json`](../data/geography/lidar05_valle_tile_manifest_20261020.json).

## Punti campionati

Sono interpolazioni del **DTM ellissoidico del suolo**, non del manto stradale:

| Punto | Quota DTM ellissoidica |
| --- | ---: |
| Centro del borgo (13.3930177, 46.1568367) | 722,50 m |
| Piazza (13.3933009, 46.1569279) | 724,52 m |
| Ingresso del settore V (13.3924178, 46.1590017) | 728,78 m |

## File già prodotti e testati nel runtime della conversazione

- `Valle_Soffumbergo_DTM_LiDAR_05m_ellissoidico_EPSG6708.tif`: GeoTIFF lossless georeferenziato **0,5 m** e EPSG:6708, ~17,1 MB.
- `Valle_Soffumbergo_terreno_blocco_4m.glb`: terreno decimato a circa **4 m**, **172.831 vertici e 344.000 triangoli**, assi locali **+X Est, +Y alto, +Z Sud**, origine locale di visualizzazione **E 375920, N 5112728, quota ellissoidica 720 m**, ~6,2 MB.
- `Valle_LiDAR05_QC_report.json`: relazione di verifica con impronta, copertura e controlli.

Il GLB è un **blockout del solo suolo**, non una scena di guida finita; la sottrazione dei 720 m è solo una traslazione locale, **non** una trasformazione del datum verticale. Nessun asset di questa acquisizione è stato collaudato in Godot o Blender, ma il GLB è stato aperto con trimesh e ne sono state controllate topologia e normali (+Y).

## Riprodurre sul PC

Eseguire dalla radice del progetto, dopo sincronizzazione GitHub:

1. Copiare lo ZIP originale in `build/geodata/fvg/download-20261027070111018.zip` (directory esclusa da Git).
2. Installare in un ambiente dedicato `numpy`, `rasterio`, `trimesh`. Queste librerie sono necessarie alla **conversione offline**, non all'avvio del gioco.
3. Avviare:

```powershell
python tools/import_valle_lidar05.py --source "build/geodata/fvg/download-20261027070111018.zip" --output-dir "build/geodata/fvg/valle05"
```

Lo script verifica prima la SHA256 originale, poi risoluzione, estensione, numero di celle, nodata e concordanza delle fasce sovrapposte; esporta TIFF e GLB. I file originali restano fuori dal repository pubblico fino al controllo dei termini di redistribuzione del dataset e dei derivati.

## Attività ancora aperte

- Confrontare con DSM/DBM, foto e rilievo gli **edifici**, i vicoli e i muri: il DTM è un suolo nudo senza edificato né vegetazione.
- Approvare e misurare i **tornanti**, la superficie reale dell'asfalto, le larghezze stradali, i passaggi per albero e coffa e il prato PV-01.
- Per l'intero anello A/B/C/V/D/E/F servono altre tessere: questo mosaico riguarda **Valle e i suoi dintorni**, non tutto il circuito.
- Trasformare il blockout in scene Godot/Blender solo dopo verifiche di orientamento, collisioni, LOD e resa artistica; il file GLB non è ancora un ambiente di gioco pronto.
