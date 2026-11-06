# AGENTS.md — unico progetto Unreal

## Mandato
Lavorare esclusivamente sulla versione Unreal Engine 5.8 del gioco, nella radice di questa repository. L'installazione locale completa è in `C:\Giochi\Sviluppo\Viaggio a Soffumbergo Unreal`. Godot è stato ritirato dal ramo `main`; non reintrodurre `project.godot`, `godot/` né vecchi test Godot. Per consultare il vecchio lavoro esiste il ramo `archive/pre-unreal-cleanup-2026-11-06`.

Prima di modificare il progetto leggi `README.md`, `docs/SVILUPPO_UNREAL.md`, `docs/STRADA_GUIDABILE.md`, `docs/TERRENO_E_VEGETAZIONE.md`, `docs/STABILITA_GRAFICA.md` e le note pertinenti. In caso di conflitti fra documenti, i report localmente verificati più recenti prevalgono sui piani storici; non confondere i risultati `NullRHI` con il rendering grafico.

## Vincoli
- Esperienza: guida dalla partenza a Faedis verso Valle di Soffumbergo, sosta nel prato candidato, visita libera del borgo e ritorno lungo il circuito senza ribaltamenti. Tutto offline, singolo giocatore.
- Stile **realismo fiabesco**; topolini realistici con occhi solo più grandi, nessun allungamento arti, comandi adattati ai personaggi. Yaris Hybrid Trend rossa con coffa e albero maestro. La versione locale importa asset MAH storici come base tecnica, non come approvazione finale di carrozzeria e personaggi.
- Valle e opere antropiche conformi a riscontri Street View documentati; LiDAR solo per quote del suolo, non per dedurre forme degli edifici o larghezze stradali reali. Elementi vegetali PCG sono procedurali, non censimenti botanici.
- Target Windows 4K/60 FPS su RX 6800 **non certificato**. I risultati storici di giri `NullRHI`, cook e censimenti PCG non dimostrano qualità grafica, stabilità, collisioni continue o completamento del gioco.
- Il contenuto editor Unreal binario, le tessere LiDAR, le build, i report, i risultati privati e gli asset non redistribuibili non sono nella repo. Non pubblicarli senza verifica esplicita di provenienza e diritti. Nessuna nuova licenza o visibilità della repository senza istruzione.

## File e verifiche
- Codice motore `Unreal/Source/`, configurazione `Unreal/Config/`, progetto `Unreal/SoffumbergoLab.uproject`.
- Strumenti `tools/` (Python), parametri `parameters/`, fonti `data/geography/`, LiDAR grezzo solo locale `data/lidar/raw_20261020/`.
- Gli script non devono dipendere da vecchie cartelle Godot o worktree `Soffumbergo-Unreal-5-8`. Usare percorsi ricavati da `Path(__file__).resolve().parents[1]` quando necessario.
- `python -m compileall -q tools` per validazione sintattica; per modifiche C++ compilare con Unreal su Windows e verificare comportamento nel motore completo. Eseguire i collaudi pertinenti e distinguere chiaramente esiti effettivi, osservazioni e attività residue.
- Non cancellare né riscrivere file di progetto importati, sorgenti LiDAR e baseline locali per fare passare una verifica. Conservare provenienza, hash e rapporti. Non creare nuovi ambienti paralleli.
