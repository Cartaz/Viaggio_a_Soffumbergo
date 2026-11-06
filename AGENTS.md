# Istruzioni operative — Viaggio a Soffumbergo

## Stato attivo (6 novembre 2026)
Il motore di sviluppo attivo è **Unreal Engine 5.8**: decisione registrata nella copia locale il **22 ottobre 2026**. Leggi prima `README.md`, `docs/SINCRONIZZAZIONE_LOCALE_20261106.md`, `unreal5/README.md`, `unreal5/AGENTS.md` e la documentazione Unreal pertinente. Il vecchio Godot e i documenti del confronto pre-migrazione sono **storici**, non autorità per ripristinare Godot. L'AGENTS storico è conservato in `docs/GODOT_AGENTS_STORICO_20261021.md`.

## Vincoli confermati
- Gioco 3D offline; itinerario Faedis → Valle di Soffumbergo → Faedis, sosta sotto il paese, visita a piedi e ritorno; realismo fiabesco.
- Fedeltà geografica prioritaria per Valle, non inventare strutture rilevate. Il LiDAR guida **quote del suolo**; non prova larghezze, carreggiate, edifici o specie vegetali. I riscontri Street View documentati guidano gli elementi antropici, distinguendo visibile, stima e da verificare.
- Yaris Hybrid MY 2022 rossa con albero/coffa e due topolini dalle proporzioni naturali, solo occhi maggiorati. Non allungare arti per raggiungere comandi; adottare prolunghe e supporti. Non presentare gli asset storici come approvati artisticamente.
- Target PC Windows 3840×2160/60 FPS sulla RX 6800: **obiettivo, non risultato certificato**. Distinguere con rigore test statici, `NullRHI`, corse fisiche, rendering, pacchetti e collaudo manuale.
- Conservare la sperimentazione Godot e i worktree locali. Non sovrascrivere modifiche locali, non fare `reset --hard` o `git pull` su un albero sporco.
- La repository è pubblica: non caricare LiDAR grezzo, dati privati, `.uasset` importati, screenshot non autorizzati, asset Disney/Toyota/MAH senza autorizzazione, build/caches/log pesanti, credenziali e dettagli privati. Non scegliere una licenza o cambiare visibilità.

## Lavoro verificabile
Procedi in piccoli incrementi: verifica versione delle fonti, registra i file, riproduci le prove appropriate, segnala i limiti. La cartella `unreal5/` è **snapshot dei sorgenti**: per eseguire Unreal sono necessari contenuti e dati locali non pubblicati. I rapporti citati in documentazione descrivono prove locali storiche e non sono sostituibili con supposizioni.
