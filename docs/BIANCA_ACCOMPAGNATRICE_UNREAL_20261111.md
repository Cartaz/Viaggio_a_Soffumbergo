# Bianca e Bernie esplorano insieme — verifica UE 5.8, 11 novembre 2026

## Funzionalità realizzata
La modalità prototipo di esplorazione **guida → discesa → cammino → rientro** ora coinvolge entrambi i topolini. La Yaris resta un corpo fisico Chaos, senza teleport o freeze del veicolo. Il personaggio controllato è Bernie; Bianca è una seconda **ACharacter** che segue Bernie usando **CharacterMovement**, collisioni del mondo, gravità e superfici realmente camminabili. Non c'è una NavigationMesh già validata per il borgo: se il percorso è ostruito, Bianca può fermarsi; il suo movimento non passa attraverso gli ostacoli per aggirare il problema.

### Come funziona
- Al comando **E**, quando la Yaris è quasi ferma, viene cercato terreno libero per Bernie e **anche per Bianca**. Si controllano raycast del terreno, pendenza, dislivello e ingombro di entrambe le capsule: se non ci sono due posizioni valide, **la discesa viene annullata**, senza lasciare un personaggio isolato.
- Bernie mantiene il modello scheletrico importato `/Game/Imported/bernie`; Bianca utilizza `/Game/Imported/bianca`. Scale uniformi di prova, capsule raggio 5 cm e semialtezza 11 cm: **nessun allungamento degli arti**.
- Bianca segue una direzione verso Bernie, lasciando una distanza minima di 65 cm. La velocità massima di prova è 95 cm/s; la sua modalità `bRunPhysicsWithNoController` permette di usare CharacterMovement senza controller AI. Anche oltre 5 m Bianca **continua a camminare**, invece di congelarsi; viene emesso soltanto un avviso diagnostico sulla navigazione ancora incompleta.
- Quando il giocatore si avvicina al veicolo e preme **E**, il rientro richiede che *entrambi* siano vicini alla Yaris (Bernie ≤ 300 cm, Bianca ≤ 320 cm), che Bianca sia sul terreno e la Yaris ferma. Solo allora i due attori a piedi vengono eliminati e tornano visibili i due passeggeri nell'auto.
- Tutte le operazioni sono disabilitate durante autopilota, benchmark nativi e controlli di input automatizzati. Il pacchetto stabile `4a05593a4282` non viene sostituito.

## Compilazione, test e prove reali
Il modulo C++ **SoffumbergoLabEditor** è compilato con UBT, MSVC e Unreal Engine 5.8.4. La prima compilazione della modalità Bianca ha segnalato un errore di tipo `TObjectPtr<USkeletalMeshComponent>` nella gestione dei passeggeri; è stato corretto usando un riferimento `const auto&` nel ciclo. La compilazione successiva è riuscita.

L'output nativo `on_foot_smoke.json` verifica esplicitamente: creazione Bianca con riferimento alla leader, spostamento di entrambe superiore a 10 cm, contatto con il terreno per entrambe, prossimità alla vettura, rientro e spostamento massimo di 50 cm della Yaris.

| Prova fisica nativa `NullRHI` | Bernie | Bianca | Rientro di entrambi | Spostamento vettura |
|---|---:|---:|---|---:|
| Valle di Soffumbergo | 113,262 cm | 127,855 cm | passato | 0,058 cm |
| Campeglio | 113,266 cm | 127,854 cm | passato | 0,066 cm |
| Canal di Grivò | 113,260 cm | 127,856 cm | passato | 0,070 cm |

Prove conservate sotto `results/on_foot_native_companion_stop_0_20261111_v1/`, `stop_1`, `stop_2` e aggregato `results/on_foot_native_companion_20261111_summary.json`. Non si tratta di un giro completo né di gameplay manuale del borgo.

**Prova renderizzata:** `UnrealEditor-Cmd.exe`, **D3D12, viewport effettiva 1280×720**, preset bilanciato, livello `CircuitoGuidabile` con test stop Valle; superati discesa, movimento di entrambi, suolo e rientro, senza crash. Telemetria `results/on_foot_rendered_companion_review_20261111_v2/on_foot_smoke.json` e log D3D12 corrispondenti. Sono state acquisite **due immagini reali**: `on_foot_midwalk.png` (da dietro Bernie, Bianca fuori inquadratura) e `on_foot_companion_review.png` (in particolare mostrano Bernie in rosso e Bianca in abito rosa accanto alla Yaris). Le immagini restano solo locali insieme agli asset binari.

## Osservazioni della revisione visiva
Il fermo immagine di confronto mostra realmente i due personaggi, la Yaris rossa e l'area stradale di Valle. **I modelli sono stati caricati e non mancano dal mondo renderizzato**. Il paesaggio e la linea dell'orizzonte risultano ancora semplici/provvisori; l'inquadratura è pensata per il collaudo, non rappresenta una scena artistica finale. Non si afferma che le figure abbiano un'animazione corretta: nella versione attuale il modello può **scivolare sul terreno senza una vera animazione di passi**.

## Fonti del metodo e limiti
La documentazione ufficiale [Epic Games, Unreal Engine 5.8 — UCharacterMovementComponent](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/UCharacterMovementComponent) conferma che `bRunPhysicsWithNoController` permette al CharacterMovement di avanzare anche senza `Controller`. Vedi anche [Epic — Movement Components](https://dev.epicgames.com/documentation/en-us/unreal-engine/movement-components-in-unreal-engine).

**Ancora aperto:** animazioni corporee reali e rifinitura di Bernie/Bianca, cambi di quota e gradini, vera navigazione attorno agli edifici, osservazioni delle facciate di Soffumbergo, valutazione di mezzi/ingombri/tetti del centro storico e benchmark grafico lungo a 3840×2160/60 FPS. Non è stato aggiunto alcun edificio inventato dai soli DSM/DBM LiDAR né modificata la geometria verificata della strada.

## File sorgente
- `Unreal/Source/SoffumbergoLab/SoffumbergoCompanionMouse.h` e `.cpp`: secondo personaggio.
- `Unreal/Source/SoffumbergoLab/SoffumbergoFootMouse.h` e `.cpp`: protagonista.
- `Unreal/Source/SoffumbergoLab/LabVehicle.h` e `.cpp`: discesa con controlli su entrambi, freni, ricongiungimento e diagnostica.
- `Unreal/Config/DefaultInput.ini`: comandi.
- `tests/test_on_foot_unreal_contract.py`: controlli sintetici del contratto; non sostituiscono il motore.

Non distribuire i modelli binari, i raster, gli screenshot o l'archivio regionale tramite la repository pubblica senza verifica dei diritti. La documentazione pubblica contiene soltanto parametri e risultati dei test.
