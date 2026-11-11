# Candidata Windows on-foot — 11 novembre 2026

## Risultati effettivamente verificati

La modalita a piedi per Bernie e Bianca e stata sviluppata in Unreal Engine 5.8.4, compilata e testata sul computer Windows, mantenendo intatta la build stabile della Yaris. La prima prova di regressione della guida con il nuovo modulo C++ ha completato **18.857,9915 m**, 31/31 fasi, 3 manovre, zero ripristini, zero intervalli senza contatto e zero uscite dalla superficie stradale. La prova riguarda la fisica Chaos con **NullRHI**, non il rendering 4K.

La copia candidata onfoot_20261111_v1 e stata compilata dal sorgente e archiviata in build/OnFootCandidateWindows/onfoot_20261111_v1/Windows. Unreal AutomationTool BuildCookRun ha compilato il gioco, cucinato **789/789 pacchetti** e completato lo staging con ExitCode 0. I **114 livelli** richiesti sono la mappa CircuitoGuidabile piu 113 tile del terreno. La copia QA si trova in build/Qonfoot_20261111_v1; ha un GameDefaultMap specifico soltanto nella propria Config, senza alterare il progetto originale.

Il rapporto di esportazione build/Qonfoot_20261111_v1/on_foot_packaging_report.json riporta packaged=true, i controlli di identita delle sorgenti, il SHA-256 del gioco e original_baselines_unchanged=true. Il pacchetto attivo build/DrivingWindows/Windows/ non e stato sostituito.

## Test reali della nuova candidata Windows

Il nuovo eseguibile e stato avviato direttamente nel mondo Unreal in quattro prove:

| Fermata | Modalita | Uscita, movimento di entrambi, rientro |
| --- | --- | --- |
| Valle di Soffumbergo | NullRHI, fisica Chaos | **Superato** |
| Campeglio | NullRHI, fisica Chaos | **Superato** |
| Canal di Grivo | NullRHI, fisica Chaos | **Superato** |
| Valle di Soffumbergo | D3D12, viewport effettivo 1280x720 | **Superato** |

Il rapporto results/on_foot_packaged_20261111_v1/report.json contiene per ciascun caso le verifiche su entrambi i personaggi, le quote di movimento, il contatto col terreno e il rientro nella stessa Yaris parcheggiata. La prova D3D12 include due screenshot originali, custoditi localmente. La chiave protected_active_pak_unchanged e true. Nessun crash nelle brevi prove eseguite.

**Questi test non dimostrano ancora gameplay completo a piedi, animazioni corrette, pathfinding fra vicoli, fedelta del borgo ne 4K/60 FPS.**

### Regressione di guida nel pacchetto

La stessa coppia di dati stradali e gia stata verificata con giro completo nativo in Editor. Per la nuova candidata Windows va accettato soltanto un report originale, per lo stesso eseguibile e gli stessi dati, sotto results/driving_laps/onfoot_companion_20261111_full_packaged_v1/report.json con full_lap_passed=true. Non trasferire automaticamente il successo del giro Editor al pacchetto.

## Procedure riproducibili

Gli strumenti sono:

- tools/package_on_foot_candidate.py — rifiuta un giro fisico non completo o dati mutati, verifica 113 tile, preserva l'originale e usa un tag di candidato nuovo.
- tools/verify_on_foot_candidate.py — testa il vero eseguibile nei tre punti, con una prova D3D12 opzionale e controllo SHA-256 del pak stabile.
- tests/test_package_on_foot_candidate.py e tests/test_verify_on_foot_candidate.py — test sintetici che non sostituiscono Unreal.

Da PowerShell nella root del progetto:

    .\.venv\Scripts\python.exe tools\package_on_foot_candidate.py --lap-report results\driving_laps\onfoot_companion_20261111_full_editor_v1\report.json --tag onfoot_TAG_UNICO

    .\.venv\Scripts\python.exe tools\verify_on_foot_candidate.py --package-report build\Qonfoot_20261111_v1\on_foot_packaging_report.json --output results\on_foot_nuova_verifica --render-720p

Entrambi gli strumenti rifiutano la sovrascrittura degli output esistenti. I file binari Unreal, modelli, screenshot, report privati, ZIP Eagle.fvg, DTM e DSM/DBM rimangono locali. La nuova candidata non e stata automaticamente promossa al pacchetto stabile.

## Lavoro residuo

Animazioni scheletriche realistiche e validazione estetica dei due topolini, navigazione di Bianca attorno agli ostacoli, esplorazione estesa del borgo, geometria fedele di facciate e muri osservati, benchmark grafico del giro completo 4K/60 su RX 6800. I raster DSM/DBM attestano superfici elevate, non la posizione delle pareti alla quota strada: non generare collisioni arbitrarie dagli edifici OSM/DBTsped.

Riferimenti: docs/BIANCA_ACCOMPAGNATRICE_UNREAL_20261111.md e docs/EAGLE_LIDAR_VERIFICATO_20261111.md.

## Qualifica funzionale finale — candidata Windows, 11 novembre 2026

Dopo la compilazione e i quattro test brevi, è stata completata **anche la prova fisica dell'intero circuito con l'eseguibile Windows candidato** `onfoot_20261111_v1`, senza usare il motore Editor come scorciatoia. Il report nativo, separato da quello Editor, è `results/driving_laps/onfoot_companion_20261111_full_packaged_v1/report.json` e certifica nell'ambito della guida headless:

| Misura dell'eseguibile candidato | Valore registrato |
| --- | ---: |
| `full_lap_passed` | **true** |
| Distanza percorsa | **18.857,9911 m** |
| Fasi | **31/31** |
| Manovre | **3** |
| Ripristini della Yaris | **0** |
| Intervalli senza contatto ruote | **0 s** |
| Intervalli fuori dalla superficie guidabile | **0 s** |
| Massimo scostamento laterale | **2,389 m** |
| Eseguibile sottoposto al test | **SHA-256 `98bf3bc7c5567871fc63091b10d02df8801c564bb792144a503b0cb284dfe633`** |
| `rendering` | **false** — giro completo NullRHI, NON grafico 4K |

È stata quindi ripetuta la batteria sul pacchetto **in una nuova cartella**, `results/on_foot_packaged_20261111_v2_integrity/`, usando la versione aggiornata di `tools/verify_on_foot_candidate.py`: tre test fisici con input automatico in Valle, Campeglio, Canal e uno D3D12 a **1280×720 reali** in Valle. **Quattro su quattro superati**, verificando discesa di Bernie e Bianca su suolo libero, movimento di entrambi, prossimità al rientro, assenza di teletrasporti della Yaris, identificazione dell'API grafica e presenza effettiva dei due screenshot di prova. Restano locali.

Il nuovo [gate finale di qualificazione](../tools/attest_on_foot_candidate.py) incrocia **tre fonti indipendenti**: manifesto e SHA-256 dell'esportazione, prove native del vero gioco pacchettizzato e giro completo fisico del medesimo eseguibile. Non eredita il successo del giro Editor e rifiuta versioni di build, hash o mappe incoerenti. Rilegge gli hash attuali del `.exe`, del `.pak` candidato, del `.pak` stabile e dei dati sorgente originali. Rapporto locale: `results/on_foot_packaged_20261111_v2_integrity/final_attestation.json`.

**Esito osservato: 19 verifiche su 19 positive**, `functional_native_qa_passed=true` e `release_promotion_authorized=false`. Il codice impone che l'eventuale promozione richieda ancora un altro processo separato: **non viene sostituita la distribuzione stabile**.

Per riprodurre il gate senza rilanciare Unreal:

    .\.venv\Scripts\python.exe tools\attest_on_foot_candidate.py --package-report build\Qonfoot_20261111_v1\on_foot_packaging_report.json --smoke-report results\on_foot_packaged_20261111_v2_integrity\report.json --full-lap-report results\driving_laps\onfoot_companion_20261111_full_packaged_v1\report.json --output results\NUOVA_QUALIFICA_ONFOOT.json

**Limiti non rimossi:** non è stato eseguito il giro renderizzato a 3840×2160/60 FPS; i topolini ancora non hanno locomozione scheletrica animata né navigazione complessa fra edifici; la ricostruzione fotografica e le collisioni tridimensionali reali di Soffumbergo richiedono ulteriori verifiche. L'archivio LiDAR Eagle.fvg, i dati derivati e gli asset originali non vengono pubblicati su GitHub.

Il metodo di confezionamento eseguito è coerente con la documentazione ufficiale [Epic Games, Unreal Engine 5.8 — Packaging Your Project](https://dev.epicgames.com/documentation/en-us/unreal-engine/packaging-your-project): fasi Build → Cook → Stage → Package, tramite `AutomationTool BuildCookRun`. Il successo del packaging, da solo, non dimostra il successo del gameplay: per questo la prova del vero eseguibile è una fonte distinta.
