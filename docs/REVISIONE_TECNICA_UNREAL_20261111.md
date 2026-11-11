# Revisione tecnico-funzionale del progetto Unreal — 11 novembre 2026

## Ambito e metodo

Sono stati ispezionati il progetto Unreal 5.8 presente su Windows, le istruzioni e i rapporti conservati, il codice di guida e streaming, l'inventario dei tool, le configurazioni input e le sorgenti LiDAR Eagle.fvg acquisite il giorno 11 novembre. L'audit separa fatti **verificati nella sessione**, prove storiche presenti nei report e attività **ancora aperte**. Non dichiara ispezionate visivamente tutte le mappe, le texture o i modelli binari: la repository GitHub contiene principalmente sorgenti, mentre i contenuti UE e i rapporti completi rimangono locali.

| Area | Esito | Evidenza e limite |
| --- | --- | --- |
| **Integrità dei dati LiDAR** | Verificata per il circuito campionato | 41 DTM originali identici allo ZIP RAFVG; 123 nuovi DBM/DSM ellissoidici con CRC/SHA-256; stessa origine e risoluzione 0,5 m |
| **Copertura del percorso fisico registrato** | Verificata | 105.215 posizioni native f437 con DTM, DBM e due DSM validi; non conferma tutte le aree sotto gli ingombri né tutti gli edifici |
| **Geometria degli edifici di Via Mont Joanes** | **Criticità aperta** | Audit dei cinque edifici DBTsped più sospetti e confronto LiDAR; superfici superiori elevate in zone della traiettoria, ma posizione di muri a piano strada non accertata |
| **Strada e guida** | Baseline conservata; collaudi storici circoscritti | Pacchetto attivo 4a05593a4282, candidata fisica f4373a62b482 separata. Nulla in questo audit autorizza promozione automatica |
| **Esplorazione a piedi** | **Implementata e verificata in Editor** | Nuova classe SoffumbergoFootMouse e integrazione Yaris; discesa, 1,13 m di camminata con appoggio, rientro superati a Valle, Campeglio e Canal |
| **Compagna Bianca** | Prima versione sperimentale in prova | Nuova classe SoffumbergoCompanionMouse con inseguimento fisico e collisione; controlli nativi superati nelle tre fermate, ma senza navigazione avanzata, animazioni o approvazione visiva |
| **Realismo della Yaris e topolini** | Non approvato esteticamente | La fisica e l'asset Yaris sono baselines tecniche, il nuovo topo conserva scala uniforme ma non è un asset finale |
| **Edifici e luoghi di Soffumbergo** | Incompleti | Non è stato aggiunto alcun volume di facciata/collisione desunto automaticamente dal DSM; servono sopralluoghi e revisione Street View |
| **Territorio, fondali e PCG** | Storicamente testati, non ricollaudati ora | Documentati 113 settori e 593.327 istanze, ma questa sessione non ha rifatto giri grafici completi né nuove catture approvate |
| **Rendering nativo** | Prova corta superata, **4K/60 aperto** | Una prova D3D12 breve a 1280×720 sulla scena Valle e con il topolino termina senza crash. Non misura FPS nel giro completo e non prova assenza futura di DXGI_ERROR_DEVICE_HUNG |
| **Pacchetto Windows giocabile** | **Non aggiornato** | Incremento on-foot compilato come DLL editor e provato realmente in Unreal, ma non inserito nell'eseguibile 4a distribuito. È necessario un packaging distinto e una validazione di regressione. |
| **GitHub vs asset locali** | Separazione preservata | Sorgenti e test pubblicabili senza LiDAR grezzo, ZIP, mesh UE, screenshot proprietari o dati privati |

## Correzione funzionale effettivamente sviluppata

Per la prima volta nella versione Unreal del progetto il giocatore può scendere dalla Yaris e muovere un topo sul terreno con collisione, quindi rientrare nella **stessa** auto fisica. Il vecchio codice si limitava a guidare e cambiare telecamera: non esisteva un Pawn per camminare. In questa sessione è stata creata e compilata una classe ACharacter e sono stati aggiunti i nuovi comandi.

Il primo test nativo ha **fallito il rientro** perché il controllo usava Actor.Owner, sovrascritto durante il passaggio di possessione a un controller. La correzione usa il riferimento persistente ParkedVehicle. Dopo la correzione la suite di prova supera tutti e tre i luoghi, più una sessione D3D12 a bassa risoluzione.

Dettagli, log esistenti e vincoli in [ESPLORAZIONE_A_PIEDI_UNREAL_20261111.md](ESPLORAZIONE_A_PIEDI_UNREAL_20261111.md).

## Problemi che non si possono dichiarare risolti

1. **Ricostruzione antropica completa**: le sagome OSM/DBTsped e il DBM non definiscono automaticamente lo spessore e la posizione delle pareti, aperture e porticati. Non generare collisioni edilizie indiscriminate che bloccherebbero la Yaris.
2. **Animazioni e compagna**: Bernie e Bianca sono ora soggetti fisici controllato/seguace in modalità prototipo, ma non dispongono ancora di locomozione animata definitiva, pathfinding attorno agli ostacoli e validazione visiva.
3. **Collaudo grafico completo**: verificare il 4K/60 sul giro realmente renderizzato, controllando la RX 6800 e il rischio di timeout grafici già documentati. La prova corta a 720p non sostituisce quella lunga.
4. **Pacchetto Windows**: l'eseguibile distribuito non include automaticamente modifiche al sorgente C++; produrre una candidata separata senza sovrascrivere il pacchetto 4a e controllare menu, input, discesa, rientro, caricamento e comportamento delle ruote.
5. **Fedeltà fotografica del borgo**: mancano rifiniture architettoniche con dati osservati, vegetazione e asset specifici della località.

## Sequenza successiva proposta, senza sostituire il lavoro verificato

- Usare [EAGLE_LIDAR_VERIFICATO_20261111.md](EAGLE_LIDAR_VERIFICATO_20261111.md) per la base DTM/DSM/DBM verificata, e la revisione Mont Joanes per il confine tra carreggiata e facciate.
- Creare **soltanto in una variante separata** una visualizzazione delle facciate probabili basata su contorni mappati e dati LiDAR, senza collisioni definitive; rivederla contro Street View osservato e quote di sopralluogo.
- Integrare e testare animazioni dei due topolini e una compagna che segua il mouse senza attraversare muri o immettersi su strada senza controllo.
- Compilare, esportare e collaudare una build Windows candidata con telemetria fisica e verifiche a piedi, senza sostituire la release corrente finché non completa i test.
- Validare materiali, framerate in movimento e gioco completo a 3840×2160, senza trarre conclusioni da NullRHI o una prova 720p.

Questa è una revisione trasparente di ciò che si è potuto verificare ed eseguire, **non una dichiarazione di completamento dell'intero gioco**. Conservare tanto le prove riuscite quanto i fallimenti e la loro causa.
