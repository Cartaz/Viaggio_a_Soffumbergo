# Modello Yaris Hybrid Trend MY22

**Versione del modello: 0.1.** L'utente riconosce l'idea del modello, ma richiede ancora molta scultura. Questa è una base tecnica e di proporzioni: la lavorazione di lamiere, volumi, raccordi e dettagli dell'abitacolo è ancora sostanziale, non una semplice lucidatura finale. Non è l'approvazione della fedeltà realistica. La versione riguarda l'asset auto, non l'intero gioco.

## Consegna

La repository contiene geometria effettiva di carrozzeria e abitacolo, un sorgente Blender modificabile, tre GLB a dettaglio decrescente, una variante per il passaggio dell'albero e un adattatore Godot. Non sono soltanto script non eseguiti o viste fotografiche applicate a un cubo.

| File | Uso |
| --- | --- |
| `art/source/yaris_2022/yaris_trend_2022.blend` | Sorgente con componenti separati e texture impacchettate; Blender 4.5.3 LTS |
| `art/vehicles/yaris_2022/yaris_trend_2022.glb` | Auto di serie, esterni e interni, materiali PBR, texture incluse |
| `yaris_trend_2022_lod1.glb`, `yaris_trend_2022_lod2.glb` nella stessa cartella | Varianti semplificate, con gli stessi pivot; non un benchmark di prestazioni |
| `yaris_trend_2022_game.glb` nella stessa cartella | Variante immaginaria: foro reale da 0,32 × 0,32 m nel tetto e nel rivestimento, collare; mantiene separato il riferimento di serie |
| `godot/scenes/yaris_visual.tscn` | Modello di serie con API visiva, senza massa o collisioni aggiunte |
| `godot/scenes/yaris_showroom.tscn` | Scena autonoma di ispezione |
| `reports/yaris_2022/` | Render, statistiche e risultati del collaudo |
| `references/yaris_2022/README.md` | Fonti ufficiali, configurazione e limiti della ricostruzione |

## Ispezionare il modello

Aprire `project.godot` in Godot 4.5.1, attendere l'importazione, aprire `godot/scenes/yaris_showroom.tscn` ed eseguire la scena corrente (F6). Tasti 1/2/3 per esterni, posteriore e abitacolo; trascinamento sinistro per ruotare; rotella per la distanza; O apre le quattro porte, H il portellone.

Il laboratorio principale istanzia lo stesso adattatore visivo e muove le ruote usando gli ancoraggi e le lunghezze delle sospensioni già esistenti. La rotazione visiva delle ruote segue la distanza percorsa; non introduce un modello di slittamento rotazionale o modifica la taratura dei pneumatici. Le masse e la collisione di laboratorio rimangono sperimentali.

La scena standard mantiene l'auto di serie. La scena `yaris_game_visual.tscn` usa il foro del tetto ed è quella collegata al laboratorio con albero. Le prolunghe per le zampe, gli ancoraggi strutturali definitivi e il passaggio degli occupanti restano da progettare insieme ai personaggi: questa consegna non li dichiara collaudati.

## Coordinate e nodi

Un'unità equivale a un metro. Blender: X destra, Y avanti, Z alto. glTF/Godot: X destra, Y alto, avanti −Z. Origine a terra, al centro fra gli assi; la carrozzeria ha sbalzi differenti davanti e dietro.

- `Steer_FL/FR/RL/RR`: centri delle ruote; Godot Y = 0,31045 m, Z = −/+1,28 m, X = −/+0,759 m davanti e −/+0,757 m dietro.
- `Wheel_*`: figli dei nodi di sterzo; rotazione locale X per il rotolamento.
- `Door_FL/FR/RL/RR`: pivot anteriori delle quattro portiere; apertura su Y in Godot.
- `Hatch`: portellone, rotazione X.
- `SteeringWheel`: volante, asse inclinato dichiarato nell'adattatore; rapporto visivo stimato.
- `Sockets`: sedute, occhi del guidatore, impugnature, pedali, uscita e centro tetto. Sono punti di lavoro stimati per l'animazione, non misure ergonomiche Toyota.

`YarisVisual.update_running_gear()` sincronizza sterzo, altezza e rotolamento. `set_door_open()` e `set_hatch_open()` accettano un fattore 0–1. I GLB includono anche cinque clip di ispezione; l'adattatore le ferma per evitare che si sovrappongano ai comandi del gioco. Non inserire un secondo `RigidBody3D` dentro il modello.

## Rigenerazione riproducibile

Per le texture originali serve Python con Pillow. Per la geometria serve Blender 4.5 LTS:

```text
python tools/build_yaris_textures.py
blender --background --factory-startup --python tools/blender/build_yaris.py -- --overwrite --render
blender --background --factory-startup --python tools/blender/build_yaris_game_variant.py
python tools/check_yaris_asset.py
```

Il primo generatore salva il sorgente prima di raggruppare i componenti per materiale. Il GLB non dipende da percorsi assoluti, collegamenti remoti o texture esterne. La cartella del sorgente ha `.gdignore`, così Godot importa il GLB senza avviare Blender. Nessun eseguibile Blender/Godot, cache di download o fotografia Toyota è necessario nella distribuzione del gioco.

## Verifiche e limiti

Le statistiche effettive sono in `reports/yaris_2022/export_checks.json`. LOD0 conserva i dettagli dell'abitacolo; LOD1/2 riducono i triangoli ma richiedono un giudizio visivo alla distanza di impiego. Non sono state misurate prestazioni su Linux né FPS rappresentativi del percorso completo.

Le prove strutturali controllano file autonomi, geometria finita, UV/normali, indici, gerarchia, animazioni, assi e interasse. `godot/tests/yaris_import_check.gd` esercita la scena realmente importata, il movimento delle ruote e le cerniere; non valuta la somiglianza con una fotografia. Il collaudo del motore e i render sono registrati separatamente in `reports/yaris_2022/VERIFICA.md`.

La ricostruzione mantiene la configurazione MY22 documentata, ma forma fine delle lamiere, giunzioni, plancia, sedili, ottiche, cerchi e materiali restano interpretazioni da foto. Non sono inclusi motore dettagliato, parti meccaniche sotto il cofano, vano batteria, sistemi elettronici funzionali o una simulazione dell'e-CVT. La fase P3 richiede ancora revisione artistica, personaggi, cinematismi e una prova rappresentativa in gioco.
