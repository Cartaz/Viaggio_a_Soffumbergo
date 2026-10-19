# Verifica effettivamente eseguita — 19 ottobre 2026

Ambiente: Windows x64, Blender **4.5.3 LTS** (`67807e1800cc`), Godot **4.5.1 stable** (`f62fdbde1`), renderer di progetto GL Compatibility, fisica Jolt. Le prove iniziali del motore sono headless. I cinque PNG originari sono render Cycles del modello; i quattro nuovi `lab_*.png` sono immagini del laboratorio acquisite dal viewport Godot su Radeon RX 6800, OpenGL 3.3, driver 26.8.1.260806. Queste prove non misurano FPS rappresentativi.

| Prova | Esito |
| --- | --- |
| Generazione sorgente Blender e GLB, tre dettagli | Eseguita, file prodotti e leggibili |
| Render frontale, posteriore, laterale, abitacolo e porte aperte | Prodotti e osservati; la revisione artistica finale resta aperta |
| Struttura GLB, texture autonome, UV/normali, indici finiti, articolazioni | Passata sui quattro GLB; dettagli in `export_checks.json` |
| Foro reale nel tetto e nel rivestimento | Passato: raggio verticale centrale libero, raggi adiacenti intercettano entrambe le superfici; `roof_passage_check.json` |
| `python tools/check_project.py` | 28 test passati, integrità e report deterministici passati |
| gdformat e gdlint | Passati su tutti gli script del progetto |
| Godot, importazione effettiva con editor headless | Passata |
| `godot/tests/yaris_import_check.gd` | Zero errori: assi/interasse, ruote, sterzo, sospensione, cerniere e assenza di corpi fisici duplicati |
| `godot/tests/reference_checks.gd` | 1.014 controlli, zero errori |
| Laboratorio con modello e albero | Avviato per 180 frame a passo fisso di rendering, nessun errore di script; non è una prova dinamica completa |
| Integrazione interattiva del laboratorio, renderer reale | 28 controlli, zero errori: input, tre camere, aperture, accelerazione, curva breve, frenata e ripristino; `lab_integration.json` e `LABORATORIO.md` |
| Scena autonoma `yaris_showroom.tscn` | Avviata nel motore per 10 frame, nessun errore di script |
| Banco statico 120 Hz | Passato, velocità finale circa 0,000117 m/s |
| Banco statico 240 Hz | Passato, velocità finale circa 0,000067 m/s |
| Banco statico 60 Hz | **Non passato**: velocità residua circa 0,06772 m/s, oltre il limite 0,02; sostegno medio corretto. La stabilità a questo passo rimane aperta |

I risultati numerici grezzi del motore sono in `engine_checks.json`. I banchi finali sono stati eseguiti in sequenza per mantenere separati i CSV di telemetria. La configurazione predefinita del progetto rimane a 120 Hz e non è stata ritarata per nascondere l'esito a 60 Hz.

Comandi riproducibili, dalla radice, con i percorsi degli eseguibili del proprio PC:

```text
python tools/check_project.py
python tools/check_yaris_asset.py
gdformat --check godot/scripts/*.gd godot/tests/*.gd
gdlint godot/scripts/*.gd godot/tests/*.gd
godot --headless --path . --editor --import --quit
godot --headless --path . --script godot/tests/yaris_import_check.gd
godot --headless --path . --script godot/tests/reference_checks.gd
godot --headless --path . --fixed-fps 60 --quit-after 180
godot --headless --path . godot/scenes/yaris_showroom.tscn --quit-after 10
godot --headless --path . --script godot/tests/static_bench.gd -- --hz=120
```

Nel contesto di esecuzione ristretto, i test Python sono stati lanciati con la directory temporanea limitata alla cartella di lavoro. Non sono stati cambiati i test o le loro soglie. Gli output del controllo preparatorio continuano correttamente a precisare che **quello specifico comando** non avvia Godot o Blender: le esecuzioni dei due programmi sono prove separate.

## Limiti residui

Non sono verificati: guida prolungata e dinamica completa in curva, stabilità a 60 Hz, rendering/prestazioni nel gioco completo, build Linux/Windows distribuite, ingombri dei protagonisti, meccanismi per le zampe e ancoraggio strutturale definitivo dell'albero. La prova breve documentata in `LABORATORIO.md` non chiude questi punti. La somiglianza della carrozzeria e dell'abitacolo è una revisione artistica; il superamento dei test di geometria e importazione non certifica una replica fotorealistica di qualità finale. Le quote secondarie e i materiali restano stime fotografiche documentate.
