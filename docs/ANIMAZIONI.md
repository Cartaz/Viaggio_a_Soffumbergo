# Guida e tenuta della coffa — animazioni fisiche

Implementazione del **19 ottobre 2026**, sulla base dei personaggi approvati dall’utente.

Bernie ha una posa seduta, braccia con presa sul volante, dita raccolte e piedi sulle prolunghe dei pedali. Volante e pedali seguono i comandi; busto e testa reagiscono alle accelerazioni. Bianca mantiene mani e piedi sugli appigli e sulla pedana: busto, testa e ginocchia assorbono trasferimenti di carico e sobbalzi.

## Movimento e contatti

Il laboratorio misura accelerazione lineare del baricentro e accelerazione/velocità angolari del corpo Jolt. Per ogni personaggio calcola l’accelerazione del proprio punto di supporto:

`a_punto = a_baricentro + alpha × r + omega × (omega × r)`

La forza specifica locale è `R^-1 * (a_punto - gravità)`. La quota della coffa entra quindi realmente nel calcolo: non si copia la reazione dell’abitacolo. Una molla smorzata guida inclinazione e cedimento verticale, entro limiti articolari. Non sono usati cicli sinusoidali, velocità soglia per far cadere il veicolo o input fittizi per animare il busto.

Ogni modello ha 35 ossa con pesi di deformazione. IK analitica a due segmenti mantiene inalterate le lunghezze di braccia e gambe. Le mani seguono gli appoggi mentre il busto si muove. Seduta, piccolo volante e appigli interni della coffa sono adattati alla portata delle zampe; lo sterzo del laboratorio usa una corsa ridotta sul comando adattato. Il collider e la massa dei personaggi restano nell’aggregato del veicolo: nessun corpo dinamico o massa viene aggiunto dal rig.

Questa è una risposta visiva guidata dalla fisica del veicolo, non un ragdoll con redistribuzione continua delle masse. Il modello fisico conserva masse, baricentro e inerzie provvisori del laboratorio.

## Cappelli e mantellina

I cappelli sono ridotti di circa il 10% e rifiniti con tasche geometriche attorno al volume delle orecchie, lasciando un margine. Una verifica BVH in Blender rifiuta intersezioni cappello/orecchio. Cappelli e orecchie hanno lo stesso osso della testa, quindi il loro distacco relativo resta invariato durante le reazioni.

La mantellina ha una griglia più fitta, pesi su busto e braccia e pannelli con risposta secondaria smorzata. Dopo la deformazione, il motore proietta i vertici fuori da capsule conservative delle braccia e dal volume del busto; ricostruisce le normali. Questo evita che il tessuto attraversi maniche e braccia nell’intervallo di pose controllato. Non è una simulazione generale di stoffa, vento e autocollisione. La presa resta obbligatoria: pose fuori portata devono essere risolte spostando gli appoggi, mai stirando gli arti.

## Verifiche riproducibili

```bash
blender --background --factory-startup --python tools/blender/build_characters.py -- --overwrite
godot --headless --editor --path . --quit
godot --headless --path . --script res://godot/tests/occupant_checks.gd
godot --headless --path . --fixed-fps 120 --script res://godot/tests/record_occupant_motion.gd
blender --background --factory-startup --python tools/blender/preview_occupant_motion.py -- --render
godot --path . --script res://godot/tests/capture_occupants_in_game.gd
# Ripresa del laboratorio con le stesse animazioni dal vivo:
godot --path . --write-movie prova.avi --fixed-fps 30 --script res://godot/tests/capture_occupants_in_game.gd -- --movie
```

Il primo test verifica prese e lunghezze agli estremi di sterzata, reazioni in più direzioni, smorzamento a riposo e concordanza a 60/120/240 Hz. Il secondo esegue otto secondi reali nel motore con accelerazione, curve, carico laterale al carico alto, impulso verticale applicato come forza e frenata. Non è una ricostruzione del percorso reale o una prova completa di guida.

Esito misurato: 540 pose limite senza errori; massimo scarto delle prese 1,49e-8 m e delle lunghezze 2,98e-8 m. Nella registrazione Jolt, 106 campioni: prese senza scarto misurabile, mantellina fuori dalle capsule conservative, picco orizzontale della forza specifica 5,11 m/s² nell’abitacolo e 6,85 m/s² sulla coffa. Questi sono risultati del caso di prova, non garanzie per qualsiasi urto.

Sono stati ispezionati anche fotogrammi prodotti dal renderer Godot con auto, seduta, volante, coffa e mantellina dal vivo. Le immagini `art/previews/characters/ingame_*.jpg` documentano questa verifica. Nel laboratorio, **V** alterna la vista generale e le due inquadrature ravvicinate; la camera disattiva la propria interpolazione fisica per seguire correttamente i cambi di soggetto.

L’anteprima è renderizzata in Blender da una registrazione delle deformazioni effettive del rig e dei vertici della mantellina in Godot. Gli appoggi sono mostrati come studio separato per rendere leggibili i movimenti: non è una ripresa di una build finale del gioco. La scena modificabile con la presa animata è `art/source/occupant_animation.blend`; il file base con i rig è `art/source/characters.blend`. I GLB contengono rig e pesi; l’animazione reattiva dal vivo è nel controller Godot, non un ciclo già contenuto nei GLB.

## Limiti ancora aperti

Camminata, salita/discesa, ingresso/uscita dall’auto e rilascio delle prese non sono implementati da questa consegna. Restano il fitting sull’abitacolo finale, prestazioni su hardware dichiarato, casi di ribaltamento completo e un’eventuale simulazione elastica indipendente di albero/coffa. Nel laboratorio attuale la struttura è rigida: Bianca reagisce al movimento effettivo della sua posizione su quella struttura.

API usata: [Skeleton3D di Godot 4.5](https://docs.godotengine.org/en/4.5/classes/class_skeleton3d.html), con pose globali nello spazio dello scheletro. I dati anatomici e i sorgenti Blender rimangono modificabili.
