# Esplorazione a piedi — Unreal 5.8 (11 novembre 2026)

## Funzionalità realmente implementata

È stato aggiunto un primo passaggio dalla guida della Yaris Chaos a un personaggio-topolino controllabile a piedi e ritorno nello stesso veicolo fisico. È una modifica al **sorgente Unreal**, non all'eseguibile Windows attualmente distribuito. Nessuna modifica a LiDAR, strada, collisioni dei fabbricati, massa o fisica dell'auto.

**Comandi in CircuitoGuidabile:** E scende quando l'auto è ferma e il terreno accanto è libero; WASD e frecce muovono il topo, mouse controlla la camera; E vicino alla Yaris (entro 3 m) fa risalire; Escape chiude. Camera C, ripartenza R, freno e sterzo rimangono attivi durante la guida.

### Implementazione

- Nuova classe C++ **ASoffumbergoFootMouse**, in Unreal/Source/SoffumbergoLab/SoffumbergoFootMouse.h e .cpp.
- Integrazione con **ALabVehicle** (LabVehicle.h e LabVehicle.cpp) e relative mappature di input in Unreal/Config/DefaultInput.ini.
- Modello scheletrico Bernie già importato nel progetto, ridimensionato **uniformemente** senza alterarne gli arti. Capsula di collisione raggio **5 cm**, semialtezza **11 cm**. Velocità massima di camminata progettuale **85 cm/s**. La scala è un prototipo, non una misurazione anatomica del personaggio finito.
- Uscita solo se velocità lineare auto inferiore a 25 cm/s e velocità angolare inferiore a 0,25 rad/s; il motore controlla entrambi i lati del veicolo, normale del terreno, dislivello verticale e spazio libero per la capsula. Se non trova un punto valido, **non consente la discesa**.
- Mentre il mouse cammina, la Yaris rimane un oggetto fisico Chaos con freni applicati e trazione azzerata; non viene congelata o teletrasportata. Il conducente all'interno viene temporaneamente nascosto e riappare al rientro.
- Il rientro richiede distanza entro 300 cm e auto praticamente ferma. L'associazione corretta è memorizzata in un riferimento **ParkedVehicle**, non nel campo Actor.Owner, che Unreal può modificare quando il controller possiede il mouse.
- La funzione è esclusa durante test con input programmato, autopilota, benchmark e verifiche comandi. Lo streaming dei settori segue il Pawn controllato.

## Risultati nativi

### Compilazione
Compilazione e linking Unreal Engine **5.8.4 Win64 Development** realmente superati sul PC con UnrealBuildTool e MSVC, inclusa la nuova classe e i file generati da UHT. Non è stata ricostruita la build Windows distribuita.

### Giri di prova senza rendering
Tre prove native automatiche usano la vera mappa CircuitoGuidabile, fisica Chaos, terreno e comando diagnostico **-LabOnFootSmokeTest**. La prima versione ha scoperto un bug del rientro: il Pawn sostituiva l'Actor.Owner dopo la possessione. Dopo aver corretto il collegamento esplicito ParkedVehicle, tutti i test sono passati.

| Posizione di test | Uscita | Distanza camminata | Rientro | Suolo | Movimento Yaris |
| --- | --- | ---: | --- | --- | ---: |
| Valle | OK | 113,262 cm | OK | confermato | 0,0625 cm |
| Campeglio | OK | 113,266 cm | OK | confermato | 0,0730 cm |
| Canal di Grivò | OK | 113,260 cm | OK | confermato | 0,0767 cm |

Rapporti locali in results/on_foot_native_stop_1_20261111_v1/, stop_0_20261111_v1/, stop_2_20261111_v1/, con aggregato results/on_foot_native_3stops_20261111_summary.json. Primo test fallito e revisione superata conservati rispettivamente in results/on_foot_native_20261111_v1/ e v2/.

### Prima prova breve con rendering
Una prova **D3D12** con richiesta **1280×720** e preset grafico C a Valle termina senza crash, con uscita, movimento di 112,955 cm, appoggio a terra e rientro. L'auto si è spostata di 0,430 cm. Log e risultato in results/on_foot_rendered_valle_20261111_v1/. Il report iniziale riportava ancora una descrizione fissa NullRHI anche in modalità renderizzata: la diagnostica viene aggiornata per memorizzare RHI e viewport effettivi prima di considerare la verifica grafica definitiva.

**Questi test non certificano il gioco finito, la fedeltà grafica o la stabilità 4K/60.**

## Mancanze reali

- Il topo è controllabile ma manca una locomozione scheletrica animata e una revisione estetica completa.
- Un prototipo di Bianca a piedi segue Bernie usando il movimento con collisione, senza teletrasporto: ha superato prove native a Valle, Campeglio e Canal, ma non possiede ancora pathfinding, animazioni definitive o approvazione visiva.
- Il borgo non è ricostruito integralmente, e gli ingombri delle facciate non sono stati validati in 3D. Le superfici DBM indicano coperture elevate, non la posizione dei muri al suolo.
- Mancano verifica visuale della camera e dei materiali in un'esplorazione prolungata, pacchetto Windows candidato aggiornato e test completo a 4K/60 FPS.

## Riproducibilità

Compilare con UnrealBuildTool della installazione locale UE_5.8, progetto Unreal/SoffumbergoLab.uproject, target SoffumbergoLabEditor Win64 Development.

Esempio prova headless: lanciare UnrealEditor-Cmd.exe con progetto, mappa /Game/Maps/CircuitoGuidabile e gli argomenti -game -unattended -nosound -nullrhi -UseFixedTimeStep -FPS=120 -LabOnFootSmokeTest -CircuitTestStop=1 -LabOutput=NUOVA_CARTELLA. Il report on_foot_smoke.json contiene risultato, distanza percorsa, appoggio, spostamento auto e identificazione del tipo di rendering. Non avviare più renderer contemporanei.

I controlli sorgente offline sono in tests/test_on_foot_unreal_contract.py. Questi test non sostituiscono la compilazione C++ o un test in Unreal.

## Fonti
Sorgenti C++ e configurazioni del progetto; log del compilatore UBT locale, replay nativi di Unreal, report JSON e file immutati. Il codice di gioco rimane nella repository; binari, asset e output di collaudo restano locali.

## Ulteriore prova con Bianca (aggiornamento nella stessa giornata)
La modalità è stata estesa con `ASoffumbergoCompanionMouse`; sono state superate tre ulteriori prove native nel motore con movimento e rientro **di entrambi** i personaggi, più una prova D3D12 1280×720 e acquisizione visiva da due angoli. Le mesh e le capsule vengono allineate usando i rispettivi limiti geometrici originali senza deformazioni anatomiche. Dettagli e limiti: [Bianca accompagnatrice](BIANCA_ACCOMPAGNATRICE_UNREAL_20261111.md).
