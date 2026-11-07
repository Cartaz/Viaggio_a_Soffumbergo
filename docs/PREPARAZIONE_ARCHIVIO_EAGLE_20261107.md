# Eagle.fvg — preparazione verifica ZIP (7 novembre 2026)

## Stato reale
Sono state selezionate 1.034 risorse nel carrello Eagle.fvg, con somma nominale di 44.602,40 MB. Firefox mostra un download ZIP di circa 36,1 GB. La differenza potrebbe derivare dalla compressione, ma non è ancora verificata. La richiesta di download è già stata effettuata dall'utente. Durante il controllo Windows, il file ZIP completo era ancora vuoto e il contenuto veniva scritto nel temporaneo .zip.part. Il download non è terminato; non elaborare file temporanei.

## Nuovo script
tools/inspect_eagle_bundle.py esamina soltanto archivi ZIP completi, senza estrarre tutti i dati. Genera un inventario JSON dei membri, con dimensioni compresse/decompresse, percorsi e CRC dichiarati nell'archivio. Classifica come candidati DTM, DSM, DBM, LAS e LAZ in base ai nomi, senza presumere che la classificazione sia affidabile finché non sono verificati i metadati.

L'opzione --extract-targets estrae esclusivamente i raster candidati per la tessera LiDAR 06701307 e calcola SHA-256 di ciascun file; la lettura verifica anche il CRC del membro ZIP. La scansione iniziale NON calcola SHA-256 dell'archivio da 36,1 GB né verifica tutti i dati compressi: il manifesto lo dichiara esplicitamente. Vengono respinti percorsi pericolosi, ZIP incompleti, duplicati, cifratura, link simbolici e rapporti di compressione anomali.

## Dopo il completamento di Firefox
Nella directory Unreal, usare questi comandi PowerShell sostituendo il nome ZIP qualora Firefox lo cambi.

Inventario:
    .\.venv\Scripts\python.exe tools\inspect_eagle_bundle.py --archive "C:\Users\Casa\Downloads\download-20261114083722230.zip" --output results\eagle_bundle\inventory_v1

Estrazione selettiva della tessera originale:
    .\.venv\Scripts\python.exe tools\inspect_eagle_bundle.py --archive "C:\Users\Casa\Downloads\download-20261114083722230.zip" --output results\eagle_bundle\target_v1 --target-tile 06701307 --extract-targets

Creare sempre una cartella output nuova. Non rimuovere il file ZIP originale. I rapporti ed estratti rimangono sotto results/, esclusa da GitHub.

## Decisioni e limiti
La precedente lista del carrello mostrava CRN, CTR, CTRN, DBTsped, DTM, HILLSHADE, LIDAR e ortofoto. Non sono stati verificati DSM o DBM tra le risorse scaricate. La Regione documenta i modelli DSM/DBM a 0,5 m ma questo non dimostra che siano in questo archivio. I nomi file da soli non verificano il sistema di coordinate e il datum; i grigliati in quota ortometrica non possono essere sottratti direttamente al DTM ellissoidico locale.

Catalogo ufficiale: https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826
Basi cartografiche ufficiali: https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA4/

Nessuna modifica a Unreal Engine, veicolo, strada, collisioni o dati LiDAR originali. Le licenze dei file regionali e la ridistribuzione devono essere verificate prima di caricare materiali derivati pubblicamente.
