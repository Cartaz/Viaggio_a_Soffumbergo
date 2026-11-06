# Pulizia Unreal-only e consolidamento del PC — 6 novembre 2026

**Decisione:** Unreal Engine 5.8 è l'unico progetto attivo. Il ramo `main` non contiene Godot, `project.godot`, vecchi laboratori Blender né workflow del motore precedente. Gli stati originali si recuperano dal ramo Git `archive/pre-unreal-cleanup-2026-11-06` (commit di partenza `bfbb9b292a0c965242b698282985dc8a5ec61df1`).

## Cartella Windows principale
`C:\Giochi\Sviluppo\Viaggio a Soffumbergo Unreal`

Sono stati trasferiti nella cartella `data/geography/` i file geografici mancanti delle due copie precedenti; **29 file sorgente verificati, 12 copiati, nessun conflitto**. Sono state trasferite le 41 tessere LiDAR grezze in `data/lidar/raw_20261020/`. Undici strumenti Python sono stati modificati per usare percorsi relativi alla radice Unreal, senza dipendere dalle vecchie cartelle. Il test `python -m compileall -q tools` è riuscito (0). Nessuna nuova verifica di guida, collisioni C++, package o prestazioni grafiche.

La repository pubblica mantiene il sorgente Unreal e la documentazione, non i **6,1 GB** di `Unreal/Content/`, i pacchetti Windows o i LiDAR grezzi. Una installazione solo da GitHub non è il gioco completo.

## Cosa resta del precedente lavoro
Conservati: dossier del circuito, geometrie OSM candidati, manifesti e osservazioni per Soffumbergo, riferimenti di modellazione non protetti. Eliminati da `main`: Godot, test Godot, asset e rapporti vecchi non necessari, configurazioni superate e workflow collegati. Tutte le informazioni rimosse restano recuperabili nell'archivio Git.

## Attività ancora aperte
La copia Unreal contiene asset binari non distribuibili; il progetto non ha ancora una procedura pubblica per riacquisirli e non ha superato un collaudo rappresentativo 4K/60 FPS dell'intero giro. Eventuali ulteriori rimozioni locali devono avvenire dopo verifica di riferimenti e dati necessari.
