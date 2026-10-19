# Specifica di modellazione — Bianca e Bernie

Revisione **19 ottobre 2026**, aggiornata alle indicazioni successive dell’utente.

## Direzione approvata dall’utente

Adattare anche corporature, volti e abiti ai disegni e studi di animazione catalogati nella repo. **Bianca più affusolata**, Bernie più compatto. Postura e locomozione **bipedi autorizzate**: questa decisione supera i precedenti vincoli di esclusività quadrupede e di ingrandimento dei soli occhi.

Su ulteriore richiesta dell’utente, gli occhi del prototipo sono ridotti di circa un terzo e integrati maggiormente nel volto, con palpebre, pupille e ciglia proporzionate.

Conservare il carattere da topo: zampe, orecchie, vibrisse e coda sottile. Gli arti mantengono le lunghezze definite in `data/config/mouse_rig.json`; seduta, prolunghe e comandi devono adattarsi ai personaggi. Le dimensioni sono scelte di lavoro, non misure ricavate dai disegni.

## Bernie — guidatore

Tronco raccolto e rotondo, guance continue senza lobi sporgenti, muso corto, sopracciglia con lieve apprensione. Pelo bruno caldo; coppola con visiera, maglione rosso con collo e orlo a coste. Palmi stretti, dita separate e unghiette discrete; piedi con tallone, collo e dita distinguibili.

## Bianca — vedetta

Busto più stretto e slanciato, testa meno larga, musetto corto e semplice senza guance a rilievo, nasino piccolo, palpebre e ciglia espressive. Pelo avorio, naso rosato; berretto viola inclinato, mantellina viola aperta sul davanti, fiocco/foulard e abito lilla da picnic. Zampe più sottili, con dita separate e piccole unghie.

## Fonti e uso

BB-01/02/03 guidano il confronto di costruzione e carattere; BB-06 contiene studi con varianti preliminari. Le tavole pubblicate da Andreas Deja (BB-21) sono state visualizzate direttamente: distinguere i concept di cappelli e costumi dalle forme di produzione. Non mescolare tutte le varianti come se fossero un unico model sheet ortografico.

Palette qualitativa di lavoro, senza pretendere valori cromatici esatti dai cel. Le mesh sono costruite nel progetto; nessuna immagine esterna è usata come texture o incorporata nei file.

## Consegna verificabile

Generatore: `tools/blender/build_characters.py`. Configurazione: `data/config/characters.json`. GLB: `godot/assets/characters/bernie.glb` e `bianca.glb`. Scena di confronto: `godot/scenes/characters.tscn`. Viste e istruzioni: [Personaggi](../../docs/PERSONAGGI.md).

I modelli hanno ora rig e animazioni reattive nel laboratorio: vedere [ANIMAZIONI.md](../../docs/ANIMAZIONI.md). Cappelli ridotti con controllo delle orecchie; mantellina deformata con braccia e correzione delle collisioni. Cammino, salita, ingresso/uscita e fitting finale restano aperti.
