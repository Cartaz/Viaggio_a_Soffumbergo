# Allineamento con lo sviluppo sul computer — 6 novembre 2026

## Fonti direttamente controllate
- Repository GitHub `Cartaz/Viaggio_a_Soffumbergo`, ramo `main` al commit `004b23744472476f935f63b3a4338c01dd0d1d38` (21/10/2026).
- Copia Godot locale `C:\\Giochi\\Sviluppo\\Viaggio a Soffumbergo`: ramo `main` a `0f87a46` (19/10/2026), **37 commit indietro** rispetto al remote tracking; molte modifiche tracciate e non tracciate. Non resettata né sovrascritta.
- Worktree `Soffumbergo-Unreal-5-8`: checkout `experiment/unreal-5-8`, commit `004b237`, modifiche e file non tracciati conservati.
- Copia di sviluppo attiva `Viaggio a Soffumbergo Unreal`: autonoma, **non** inizializzata come repository Git; `README.md`, `AGENTS.md`, `docs/`, `Unreal/Source`, `Unreal/Config`, `parameters/`, `tools/`, `results/current_validation_summary.json` e inventario degli asset letti localmente.

## Materiale trasferito
- `unreal5/`: **206 file di sorgenti, configurazioni, strumenti e documentazione**, più **10 file selezionati di catalogo e provenienza geografica**. Il set include 125 file sotto `tools/`. L'AGENTS locale di circa 62 KB è volutamente sostituito da una sintesi pubblica verificabile: contiene una lunga cronologia operativa non ripulita. I file locali originali sono rimasti invariati.
- `README.md` e `AGENTS.md` della radice aggiornati per esplicitare la migrazione Unreal. Le precedenti versioni Godot sono conservate come documenti storici in `docs/`.
- Il vecchio progetto Godot non viene modificato o cancellato dal commit di sincronizzazione.

## Avanzamento tecnico documentato, non ricollaudato oggi
La documentazione Unreal registra la decisione del 22/10/2026 di passare a UE 5.8, installazione 5.8.4 (build 58902052), terreno LiDAR in 113 settori, censimento PCG di 593.327 piante, strada sperimentale percorsa in prove fisiche `NullRHI` per circa 18,86 km e tre manovre. Il rapporto `results/current_validation_summary.json` locale dichiara superati i controlli del primo prototipo Windows LiDAR/PCG. Documenti e rapporti più dettagliati, in gran parte datati 25/10/2026, segnalano esperimenti di terreno, vegetazione, drenaggio, scarpate e strutture stradali.

Questi sono **esiti riportati in file locali**. In questa sincronizzazione non sono stati ricompilati C++ Unreal, rieseguiti i giri, verificati rendering/4K/60 FPS o riprodotti i rapporti: la sola verifica automatica eseguita sulla copia locale è `python -m compileall -q tools`, con esito **0**.

## Esclusioni intenzionali
- `Unreal/Content/` locale circa **6.128 MB**, con `.uasset`, `.umap`, 113 settori di mondo e materiali: non pubblicata, in parte composta da contenuti di origine diversa. Il progetto in GitHub **non è autonomamente eseguibile**.
- `Unreal/Binaries/`, `Intermediate/`, `Saved/`, `DerivedDataCache/`, `build/`, `terrain/`, `private/`, `results/`, screenshot, eseguibili, cache, ambienti Python e LiDAR grezzo: mantenuti locali.
- Dei dati geografici si versionano solo piccoli file di catalogo/provenienza; risposte GIS massive e campioni 0,5 m rimangono in locale, in attesa di una strategia di distribuzione lecita e riproducibile.

## Questioni aperte
1. Preparare un inventario di dipendenze binarie con provenienza, licenza, SHA-256, dimensione e istruzioni di acquisizione, senza caricare opere di terzi.
2. Risolvere i conflitti potenziali tra corridoio stradale e impronte OSM degli edifici, senza assumere che una proiezione 2D sia un urto 3D.
3. Verificare l'aspetto visivo, il borgo, i materiali, la Yaris e gli occupanti nel motore completo.
4. Eseguire il giro completo con rendering rappresentativo e misurare realmente 4K/60 FPS, rispettando i precedenti problemi di spegnimento del PC.

**Regola:** non usare un semplice `git pull` nella vecchia copia Godot con modifiche locali; effettuare una integrazione separata e conservativa se necessario.
