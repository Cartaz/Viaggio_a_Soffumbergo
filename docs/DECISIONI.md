# Decisioni e vincoli

Aggiornato il 21 ottobre 2026. Il progetto completo rimane il riferimento per i dettagli; questo elenco permette di controllare le richieste senza confonderle con ipotesi tecniche.

## Richieste confermate dall’utente

| Tema | Decisione |
| --- | --- |
| Distribuzione | Nativa per Linux e Windows |
| Direzione artistica | Realismo fiabesco, confermato dall'utente; supera il cartoonesco iniziale. Materiali PBR, ambienti dettagliati, luce cinematografica, pelo e tessuti credibili |
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

## Decisione artistica registrata il 21 ottobre 2026

Fonte: conferma «realismo fiabesco» nella conversazione [Confronto Godot Unreal](chatgpt-conversation://6ad8f352-df20-83eb-893d-832cede2b84d), ripresa nella richiesta corrente. L'immagine `Gemini_Generated_Image_2whrds2whrds2whr.jpg` è stata osservata: riferimento privato per atmosfera, luce, dettaglio e contrasto fra Yaris rossa, legno della coffa, pelo e abiti. Non viene aggiunta alla repository pubblica né usata come texture.

La decisione riguarda la resa dell'intera scena. Restano vincolanti Valle di Soffumbergo documentata (nessun Cervino o borgo alpino inventato), Yaris Hybrid Trend italiana MY 2022 rossa senza optional con foro, albero e coffa, topolini naturali quadrupedi con soli occhi ingranditi. L'auto illustrata non sostituisce i riferimenti Toyota; i personaggi bipedi dell'immagine non sostituiscono i riferimenti anatomici. Bianca e Bernie restano ispirazione estetica per design originali, senza riproduzioni non autorizzate.

La vertical slice P3 deve dimostrare questa resa insieme a guida e visita. Si prepara il confronto **Unreal Engine 5.8 vs Godot**, senza migrare ora e senza attribuire vantaggi o FPS non misurati. Godot 4.5.1/Jolt resta la base corrente; la build esatta del candidato Unreal va verificata prima del test, senza sostituzioni di versione implicite. Target comune: Ryzen 7 5700X3D, RX 6800, 32 GB RAM, 1080p/60 FPS. Criteri, protocollo ed esiti ancora aperti in [TEST_MOTORI.md](TEST_MOTORI.md).

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

