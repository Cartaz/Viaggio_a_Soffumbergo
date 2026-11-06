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

## Consolidamento effettivamente completato sul PC
Le vecchie cartelle `Viaggio a Soffumbergo` (Godot), `Soffumbergo-Unreal-5-8` (worktree di sperimentazione) e `Backup Viaggio a Soffumbergo` sono state **spostate** dal percorso di lavoro a `C:\Giochi\Archivi\Viaggio_a_Soffumbergo_20261106\` (circa 8,6 GB di contenuti storici). **Non sono state cancellate definitivamente**, perché il worktree storico aveva modifiche non pubblicate e asset locali da preservare. In `C:\Giochi\Sviluppo\` rimane una sola cartella Soffumbergo attiva: `Viaggio a Soffumbergo Unreal`.

La cartella Unreal attiva è stata inizializzata come checkout Git locale del nuovo ramo `main` (269 file tracciati al commit `757b86e` prima di questo aggiornamento). I vecchi file di intestazione locali sono stati conservati nell'archivio prima di allineare `README.md`, `AGENTS.md`, `.gitignore` e `NOTICE.md` alla repository; i contenuti binari Unreal e i dati geospaziali non sono stati sovrascritti. Le vecchie cartelle non sono più necessarie come sorgenti di percorso per gli 11 script corretti.

**Verifica funzionale aggiuntiva:** `tools/inventory_lidar.py` eseguito nell'ambiente Python della cartella Unreal unificata, codice d'uscita **0**. Ha rilevato **41 tessere**, per **853.275.721 byte**, e tutte le impronte dei sette settori del percorso rientrano nelle impronte dei raster, salvo errori numerici trascurabili. Quest'ultimo risultato **non** certifica le celle LiDAR valide, la correttezza altimetrica della strada o le collisioni in Unreal.

Le fonti OSM intermedie e grandi, le risposte GIS e i risultati restano locali e sono esclusi da Git; le fonti/testi di provenienza già condivisibili rimangono tracciati. I file temporanei del consolidamento sono custoditi nell'archivio.
