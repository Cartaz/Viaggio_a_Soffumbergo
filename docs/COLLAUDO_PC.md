# Primo collegamento al PC

**Valle 3D 0.1 (20/10/2026):** aggiunti ed eseguiti i collaudi della scena
geografica separata. Comando completo, prove, coordinate e limiti in
[VALLE_3D.md](VALLE_3D.md); risultati in `reports/VALLE_3D_VERIFICA.json`.
I collaudi Valle non chiudono le prove dinamiche del veicolo descritte sotto.

Obiettivo: rendere il laboratorio realmente verificato. Importazione, confronto numerico, avvio delle scene, banco statico a 120/240 Hz e una prova breve della Yaris guidabile con rendering reale sono eseguiti; il banco a 60 Hz non passa la soglia di velocità residua. Evidenze e limiti in `reports/yaris_2022/VERIFICA.md` e `LABORATORIO.md` nella stessa cartella. Le prove dinamiche complete sotto elencate restano da completare.

## Importazione

Registrare sistema operativo, GPU/driver e versioni installate. Base API: Godot 4.5.1/Jolt integrato; generatori preparati per Blender 4.5 LTS. Se sul PC sono presenti versioni successive, controllare la compatibilità prima di cambiare installazione o sorgenti.

Aprire `project.godot` nella radice, attendere il primo import e controllare gli errori. Verificare classi globali, motore Jolt e 120 tick fisici. Il parser esterno non intercetta tutti gli errori di tipo/API.

## Prove motore predisposte

Usare il percorso reale dell’eseguibile; su Windows preferire l’eseguibile con console. Dalla repository:

```bash
godot --headless --editor --path . --quit
godot --headless --path . --script res://godot/tests/reference_checks.gd
godot --headless --path . --script res://godot/tests/static_bench.gd -- --hz=60
godot --headless --path . --script res://godot/tests/static_bench.gd -- --hz=120
godot --headless --path . --script res://godot/tests/static_bench.gd -- --hz=240
```

Il primo runner confronta calcoli Godot/report Python e budget di aderenza. Il secondo lascia assestare il corpo otto secondi e campiona due secondi: richiede sostegno medio entro il 2% del peso, velocità inferiore a 0,02 m/s, velocità angolare inferiore a 0,02 rad/s e orientamento quasi verticale. Sono criteri proposti, non risultati ottenuti.

Conservare output, commit, impostazioni e CSV. Una prova statica non convalida la dinamica in curva.

## Prova visiva

Avviare il progetto con F5. Frecce/WASD per guida, spazio per freno, R per ripristino con invalidazione. C alterna auto, albero/coffa e abitacolo; O e H comandano porte e portellone (apertura sotto 0,2 m/s). I CSV vengono scritti in `user://telemetry`, con identificatori distinti per processo e veicolo per evitare sovrascritture fra test simultanei.

`godot/tests/lab_yaris_check.gd` esercita la scena principale tramite gli input reali, con accelerazione, breve curva a destra, frenata, ripristino, camere e aperture. Aggiungendo `--capture-dir=...` senza `--headless` registra quattro immagini del viewport e il rapporto JSON. Eseguito su Windows/Radeon RX 6800: 28 controlli, zero errori. Il render è una prova d'integrazione; non misura FPS rappresentativi né certifica l'intero banco dinamico.

| Prova | Controllo |
| --- | --- |
| Fermo per 60 s | Niente deriva/vibrazione, carichi e assestamento ragionevoli |
| Accelerazione e frenata | Niente spinte laterali spurie o inversione da fermo |
| Cerchio a velocità crescente | Evoluzione continua di carichi, deriva e alleggerimento ruote |
| Destra–sinistra | Oscillazione smorzata senza crescita numerica |
| Rampa e urti | Collisioni di telaio, albero e coffa |
| Due ruote | Possibile recupero generato dalle forze, nessun trigger |
| 30/60/144 FPS, 60/120/240 tick | Confronto controllato delle stesse prove |

Non confrontare prove con input diversi come replay equivalenti. Replay degli input e confronto dinamico automatizzato sono ancora da aggiungere.

## Blender

Questi comandi usano un nuovo processo con scena iniziale e creano raccolte dedicate. Gli output esistenti richiedono `--overwrite` esplicito.

```bash
blender --background --factory-startup --python tools/blender/build_blockout.py -- --output art/source/generated
blender --background --factory-startup --python tools/blender/build_site_guides.py -- --output art/source/generated/valle_guides.blend
```

Aprire i risultati: verificare scala, foro reale nel tetto, sagoma naturale e meccanismi. Il GLB è una prova d’ingombri, non un asset finale. Le guide di Valle sono piatte e non devono essere trattate come terreno.

Confrontare i topolini con gli allegati originali. Correggere l’anatomia e scegliere una scala uniforme; adattare seduta, volante e prolunghe. Provare sterzo, corsa pedali, portiera, appoggi e scaletta prima di approvare il rig. Mai allungare un osso per risolvere una distanza.

## Collegamento della visita

Portare le regole Python nel gestore Godot con test equivalenti. Collegare checkpoint misurati, zona di parcheggio, freno di stazionamento e presenza degli occupanti. Il freno del laboratorio è solo frenata, non l’intero interblocco della sosta.

Implementare portiera/pedana e scaletta con animazioni e conferme di contatto. La proprietà della massa deve corrispondere ai corpi fisici: mantenere posa e quantità di moto al cambio di rappresentazione e continuare a trasmettere le reazioni all’auto. Attivare poi locomozione, seguito e rientro.

Ripetere venti cicli **nella scena reale**: quelli Python verificano solo le regole. Esportare Linux e Windows e misurare FPS dopo un campione grafico rappresentativo. Il target 1080p/60 FPS rimane non misurato.
