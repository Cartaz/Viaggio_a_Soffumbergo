# Decisioni e vincoli

**Direzione esplicita del 21 ottobre 2026:** tutte le prove 3D devono usare la Yaris finale approvata, il pennone/coffa e i due topolini ispirati a Bianca e Bernie. Il proxy pubblico resta storico. Asfalto ribassato e raccordatura larga al massimo metà veicolo: scelta 0,85 m per lato. I controlli geometrici completi sono separati dalla prova visibile per evitare attese poco chiare.


**Richiesta del 21 ottobre 2026:** passare al terraforming e alla costruzione
del circuito. Realizzata una variante di progetto dell'intero asse candidato,
con parametri espliciti e confronto col DTM originale. Nessuna scorciatoia o
correzione implicita delle quattro inversioni; misure del luogo e guidabilità
rimangono da verificare. [Perimetro](COSTRUZIONE_CIRCUITO.md).

**Continuazione autorizzata:** pratica della Yaris su dieci tratti separati,
con riposizionamenti espliciti e raccordi allargati di progetto. Le inversioni
sono classificate dal dossier, senza confermarne lo spazio reale o cancellare
tappe. [Ambito e limiti](PRATICA_CIRCUITO.md).

**Incremento del 20 ottobre 2026:** prototipo richiesto “Valle 3D 0.1”, realizzato
come scena separata con terreno georeferenziato a settori/LOD, collisioni,
edifici OSM come blockout e accessi provvisori riconoscibili. [Limiti](VALLE_3D.md).
Raster originali e derivati rimangono locali in attesa della verifica dei termini
di redistribuzione. Altezze degli edifici e larghezze delle linee sono parametri
grafici, non misure del luogo. Questo incremento non cambia le scelte locali su
auto/personaggi e non conferma PV-01. Supera le vecchie note “terreno non importato”
limitatamente al campione geografico di Valle, non all'anello completo.

Aggiornato il 19 ottobre 2026. Il progetto completo rimane il riferimento per i dettagli; questo elenco permette di controllare le richieste senza confonderle con ipotesi tecniche.

## Richieste confermate dall’utente

| Tema | Decisione |
| --- | --- |
| Distribuzione | Nativa per Linux e Windows |
| Percorso | Anello degli allegati, riconoscibile e adattabile |
| Meta | Valle di Soffumbergo |
| Fedeltà | Massima nel borgo; località secondarie più generiche |
| Sosta | Una zona verde sulla strada subito sotto il paese |
| Esplorazione | Scendere dall’auto e visitare il borgo |
| Auto | Yaris Hybrid MY 2022 Trend italiana, rossa, senza optional aggiuntivi |
| Modifica | Foro nel tetto, albero maestro e coffa |
| Protagonisti | Lui guida; lei viaggia sulla coffa in abiti da picnic |
| Anatomia | Corpo e arti come il topo fotografato; mai adattare le lunghezze per raggiungere pedali o volante |
| Identità visiva | I due protagonisti devono ricordare Bianca e Bernie (Disney, 1977), soprattutto per colori del pelo, espressioni e accessori; base corporea da topo reale, non bipede Disney |
| Espressività | Occhi ingranditi come sola deformazione anatomica |
| Comandi | Prolunghe meccaniche e appoggi adatti alle zampe |
| Obiettivo originario | Completare l’anello senza ribaltarsi |
| Repository | Repository creata dall’utente: Cartaz/Viaggio_a_Soffumbergo, pubblica; nessuna modifica alla visibilità |

## Scelte progettuali proposte

- La visita è una tappa obbligatoria della gita completa; il ritorno conserva l’obiettivo iniziale.
- Il giocatore controlla il guidatore a piedi e la compagna lo segue.
- La passeggera scende e risale con una scaletta e appoggi compatibili con l’anatomia; non viene teletrasportata.
- Visita senza limite di tempo, con salvataggio alla sosta; i record riguardano i settori di guida.
- I due personaggi mantengono una scala complessiva grande rispetto a topi reali; dimensioni metriche definitive da provare sul sedile con scala uniforme.
- PV-01 è il prato candidato osservato lungo via Prestento, non il punto già confermato dall’utente.
- Sorgenti preparati sulla base API Godot 4.5.1/Jolt integrato e Blender 4.5 LTS; controllare le versioni installate e la compatibilità al primo collegamento. QGIS resta utile per dati geografici e datum.

## Questioni aperte che non bloccano il laboratorio

- Punto preciso e confini della zona verde scelta.
- Collegamento continuo e documentato fra prato e borgo.
- Scala metrica, massa e baricentro definitivi dei topolini.
- Palette esatta e disegno finale degli abiti da picnic/guida rispetto alle fonti Disney, da approvare nei render e con verifica dei diritti. La direzione cromatica e di personalità è documentata in `references/bianca_bernie/`.
- Portata dei vincoli elastici della struttura e parametri di aderenza.

## Cose che non risultano completate

Il modello auto corrente è denominato **0.1**, su richiesta dell'utente. Il riscontro conferma che l'idea è leggibile ma richiede ancora molta scultura: la versione è una base di lavoro, non un modello realistico definitivo. L'utente ha autorizzato il caricamento di modello, sorgenti, riferimenti collegati e prove su GitHub come questa versione.

Nessun giro giocabile verificato, modello 3D approvato come definitivo, terreno importato, censimento completo del borgo, rilievo integrale del circuito o benchmark reale. La Yaris dispone ora di una ricostruzione di esterni e abitacolo, generata/renderizzata in Blender e importata in Godot, con prove delle articolazioni e avvio del laboratorio. Fonti, stime e limiti sono in `docs/YARIS_MODELLO.md`. La richiesta corrente privilegia una riproduzione realistica dell'auto; il modello da foto resta da rifinire artisticamente. Le regole della visita sono ancora un modello Python da collegare al 3D.

