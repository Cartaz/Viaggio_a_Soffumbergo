# Preparazione senza editor 3D

> Aggiornamento personaggi del 19/10/2026: l’utente ha autorizzato corporature adattate agli studi e locomozione bipede, con Bianca più affusolata e Bernie compatto. Questa scelta supera i precedenti riferimenti all’esclusività quadrupede e ai soli occhi deformati. Due modelli vestiti sono ora generati e renderizzati; rig, animazioni e fitting dei comandi restano da realizzare. Vedere [PERSONAGGI.md](PERSONAGGI.md).

La consegna contiene codice, dati e prove ripetibili. Godot e Blender non sono stati eseguiti. Non sono state create build, prodotti modelli finali o misurati FPS.

## Prove effettive

- **28 test Python**: inerzie analitiche, invarianza per traslazione, positività del tensore, mille richieste nel cerchio di aderenza, sospensione senza trazione, assestamento del banco numerico a 60/120/240 Hz, arti a lunghezza fissa, checkpoint e visita, venti cicli logici, salvataggi e geografia.
- GDScript analizzato con **gdtoolkit 4.5.0**: parsing, formattazione e lint. Non equivale alla verifica di tipi/API nel motore.
- Script Blender verificati come sintassi Python, senza eseguire `bpy`.
- Riferimenti `res://` verificati e report rigenerabili. Mappa SVG renderizzata e controllata visivamente.

Comando: `python tools/check_project.py`. I test numerici a diversi passi non dimostrano ancora la stabilità del veicolo Godot. Il workflow GitHub ripete i controlli dei sorgenti; non esporta il gioco.

## Laboratorio Godot

`project.godot` nella radice avvia `godot/scenes/lab.tscn`. La scena genera un piazzale sintetico, rettilineo, cerchio di riferimento di raggio 20 m, rampa, illuminazione, camera e HUD. Non è il tracciato reale.

Il veicolo applica forze su un `RigidBody3D`: quattro raggi ruota, molle/smorzatori, arresto di compressione, aderenza combinata, trazione anteriore limitata da forza e potenza, frenata regolarizzata, resistenza aerodinamica e al rotolamento. Lo sterzo ha velocità di azionamento limitata. Le collisioni includono telaio, albero e coffa. Nessuna soglia di velocità o rollio attiva il ribaltamento.

La telemetria è predisposta a circa 20 Hz: tempo, frequenza fisica, posizione, velocità, orientamento, carichi ruota e invalidazione dopo ripristino. I CSV saranno prodotti alla prima esecuzione in `user://telemetry`, con percorso assoluto stampato in console.

### Approssimazioni da collaudare e superare

1. Carico aggregato rigido: non ci sono ancora flessione dell’albero e reazioni indipendenti della passeggera.
2. Il calcolo conserva il tensore completo, ma il corpo Godot riceve **solo la diagonale** negli assi del telaio. Servono confronto con assi principali e verifica dinamica.
3. Un solo raggio per ruota: mancano contatto a volume finito, cinematica delle sospensioni, rotazione delle ruote, slittamento longitudinale e Ackermann.
4. Pneumatico laterale regolarizzato e saturazione nel cerchio di aderenza: manca calibrazione completa e dipendenza dal carico. Nessun ESC Toyota simulato.
5. Motore ibrido semplificato; nessuna riproduzione interna della trasmissione Toyota.
6. Grip unico nel laboratorio; differenza asfalto/prato da introdurre.
7. Superficie stradale generata solo provvisoria: larghezza, pendenza trasversale, normali grafiche, giunti e incroci richiedono lavoro dedicato.

## Masse, anatomia e asset

`vehicle_lab.json` è esplicitamente sperimentale. Produce 1.605 kg e baricentro a circa 1,482 m sul piano nominale, prima dell’assestamento nel motore. Conserva anche l’asimmetria laterale. Il report contiene il tensore completo e diagnostiche statiche; queste non sono un predittore dinamico di ribaltamento.

Le masse di 85 kg dei personaggi e le quote della vecchia ipotesi di laboratorio **non fissano la taglia finale**. Sagoma naturale, scala uniforme e pose decideranno nuovi valori. Baricentro e sommità visibile sono distinti.

`mouse_rig.json` vieta lo stretch IK. Il generatore Blender prepara sagome raccolte, zampe, muso, orecchie, coda sottile e occhi più grandi: anatomia ancora da confrontare con gli allegati. Le prolunghe dei pedali sono un ingombro meccanico, non un cinematismo già risolto. Volante adattato, portiera, vestito da picnic, rig e animazioni restano da costruire. `asset_register.json` elenca richieste, stato e lacune.

## Regole e visita

`tools/coffa/session.py` è una **specifica eseguibile Python, non il gestore attivo della scena Godot**. Rifiuta checkpoint errati o al contrario, discesa in movimento, visita saltata, rientro senza passeggera nella coffa e vittorie dopo recupero. Il completamento delle transizioni richiede appoggi/pose confermati, non un semplice timer.

Ogni personaggio ha una sola proprietà della massa: aggregato o corpo indipendente. Durante la scalata quest’ultimo deve continuare a caricare l’auto attraverso vincoli e contatti. Il registro delle regole non genera quelle forze: l’adattatore fisico con conservazione della quantità di moto va ancora realizzato. Non si sfuma la massa fra corpi scollegati e non si fa sparire il peso.

I controller Godot di locomozione e seguito non sono ancora istanziati nel laboratorio. Richiedono collisioni adattate al corpo a quattro zampe, rig, animazioni, navmesh e terreno. Il recupero da un blocco non teletrasporta la compagna.

## Geografia acquisita

La copia OSM contiene **127 elementi: 91 edifici, 35 tratti stradali/pedonali, un punto abitato**. È una base del borgo, non dell’intero anello. I 91 edifici non sono 91 facciate osservate né modelli già costruiti. Non è stata assunta alcuna quota come terreno verificato.

Overpass regionale non ha risposto utilmente: errori 502/406 sul servizio principale, 500 su un’alternativa pubblica. Una richiesta regionale all’API OSM ha restituito 400; l’estrazione piccola del borgo è riuscita. La copia utile è inclusa offline, con fonte, ambito, attribuzione e impronta del download.

`prepare_route.py` richiede una LineString con quote e datum dichiarati. Rifiuta un percorso senza altezze. La trasformazione WGS84/ECEF/ENU conserva tutti i vertici originari dei tornanti, senza smussamento automatico. Accetta quote ellissoidiche: un DTM ortometrico richiede prima la trasformazione geoidale corretta. La larghezza fornita dall’operatore resta provvisoria.

## Ricerca ancora aperta, indipendente dagli editor

- Polilinea completa Faedis–Campeglio–Valle e ritorno nordoccidentale, con quote e fonte riutilizzabile.
- Sopralluogo integrale dei tornanti e delle facciate; confronto delle date delle immagini.
- Collegamento pedonale continuo e conferma del prato preciso.
- Riferimenti metrici sufficienti per abitacolo, comandi e taglia definitiva.

Queste lacune non dipendono da Godot o Blender e non vengono dichiarate risolte. Il pacchetto permette intanto di avviare il laboratorio sul PC.
