# Decisioni e vincoli

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
| Anatomia | Aggiornamento utente 19/10/2026: corporatura dagli studi, Bianca più affusolata e Bernie compatto; bipedia autorizzata. Mai stirare gli arti per raggiungere i comandi |
| Identità visiva | Adattare i modelli ai disegni e studi di animazione di Bianca e Bernie (Disney, 1977), comprese silhouette, volti e abiti |
| Espressività | Occhi ridimensionati e meno sporgenti, con palpebre, sopracciglia e muso adattati agli studi; corporeità bipede autorizzata |
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

Due modelli di studio vestiti generati e renderizzati in Blender; nessuna build giocabile completa verificata, modello 3D definitivo animato, terreno importato, censimento completo del borgo, rilievo integrale del circuito o benchmark reale. Esistono ora sorgenti del laboratorio, generatori e 28 test indipendenti dagli editor. Le regole della visita sono un modello Python da collegare al 3D. Non confondere controlli statici e prove numeriche con un gioco collaudato.

