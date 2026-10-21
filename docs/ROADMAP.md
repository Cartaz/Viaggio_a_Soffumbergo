# Roadmap verificabile

Stato attuale: preparazione tecnica, laboratorio avviato in Godot e prima ricostruzione Yaris eseguita in Blender. Una casella completata richiede una consegna o una prova ispezionabile. Il solo avvio headless non chiude le prove dinamiche o artistiche.

## Valle 3D 0.1 — 20 ottobre 2026

**Incremento guida pilota e prestazioni:** [prova di 601 m](GUIDA_PILOTA.md),
[fonti Toyota e modello longitudinale](YARIS_PRESTAZIONI.md).

- [x] Riprodurre l'uscita dal piazzale e distinguere velocità stradale/caduta.
- [x] Introdurre spinta alle ruote decrescente, resistenza e regolazione della
  spinta in prossimità della massima, con auto di serie e carico separati.
- [x] Collaudare 0–100, 80–120, terminale, rilascio/freno/retro a 60/120 Hz.
- [x] Collegare la Yaris a un accesso di prova del candidato C, mantenendo
  terreno originale e ricostruzione di prova distinti.
- [x] Percorrere il tratto applicando soltanto comandi fisici, con arrivo,
  arresto, controllo dei contatti e caricamento/scaricamento dei settori.
- [ ] Verificare larghezze, asfalto, bivi e sistemazione reale del fondo:
  il test non chiude la superficie stradale verificata o P2/P3.
- [ ] Modello completo dell'ibrido, ABS/ESC e taratura di sospensioni/pneumatici.

- [x] Riutilizzare le quattro tessere reali, centri delle celle e datum espliciti.
- [x] Generare 768 × 768 m in 36 settori con LOD 2/4/8 m, collisioni a 2 m
  indipendenti e 60 giunzioni numericamente identiche.
- [x] Collocare 91 sagome OSM con altezze dichiarate segnaposto.
- [x] Mostrare strade/accessi OSM provvisori e punto PV-01 candidato, senza
  dedurre larghezze reali, asfalto o continuità pedonale dalla cartografia.
- [x] Rigenerazione deterministica, test Python/GDScript, raggi/caduta in Jolt,
  due acquisizioni dal renderer e creazione/verifica del progetto Blender.
- [ ] Approvare facciate, chiesa, campanile, muri e quote dei passaggi reali.
- [ ] Costruire una superficie stradale verificata e collegare guida/visita.
- [x] Acquisire/catalogare le 41 tessere dell'anello: 123.984.000 celle senza
  NoData e asse OSM candidato coperto su 9.966 campioni a passo massimo 2 m.
- [x] Gestire le sovrapposizioni per il prototipo con selezione esplicita della
  fonte per vertice, senza media; incertezza originaria conservata nei metadati.
- [x] Estendere il terreno a un corridoio di 352 settori con vista generale,
  dettaglio/collisioni vicini alla camera e regressioni su tutti i 9.966 punti.
- [ ] Verificare la superficie stradale e i bivi prima di integrare la guida.

**Circuito 3D 0.1:** [politica, avvio, misure e limiti](CIRCUITO_3D.md),
risultati in `reports/CIRCUITO_3D_VERIFICA.json`. Le quote a 2 m di Valle
rimangono identiche; il corridoio è un ambiente di ispezione, non il giro guidabile.

[Procedura e limiti](VALLE_3D.md), [risultati](../reports/VALLE_3D_VERIFICA.json).
P0, P3 e P4 restano aperte: questa scena è un campione geografico, non una
prova del viaggio completo o un'approvazione artistica.

## Incremento veicolo — 19 ottobre 2026

- [x] Raccogliere fonti Toyota MY22 e distinguere le dotazioni italiane dai campioni fotografici di altri allestimenti.
- [x] Generare e consegnare geometria di esterni/abitacolo, sorgente Blender, GLB, varianti LOD e render.
- [x] Collegare sterzo, sospensioni e rotazione visiva delle ruote al laboratorio senza aggiungere massa.
- [x] Aprire porte/portellone e predisporre una scena autonoma per l'ispezione.
- [x] Creare il foro dell'albero nel tetto e nel rivestimento, con verifica geometrica dell'apertura.
- [x] Eseguire import, controlli dell'asset e avvio delle scene in Godot 4.5.1.
- [x] Rendere la Yaris 0.1 provabile nel laboratorio principale con tre camere e comandi per porte/portellone; verificare guida breve, sterzo, frenata e immagini dal renderer reale (28 controlli).
- [ ] Approvare la fedeltà artistica e rifinire superfici, ottiche, cerchi e plancia alla qualità finale.
- [ ] Collaudare prestazioni, personaggi e cinematismi nel campione P3.

Evidenze: `reports/yaris_2022/VERIFICA.md`. La casella complessiva P3 resta aperta.

## Consegna preparatoria senza Godot/Blender

- [x] Calcoli di massa, baricentro e tensore con test analitici.
- [x] Modello Python delle regole della gita, proprietà unica della massa e salvataggio atomico.
- [x] Ventotto test numerici/logici/geografici eseguiti.
- [x] Sorgenti del laboratorio Godot, telemetria e prove motore predisposte.
- [x] Sorgenti dei controller di movimento e seguito, da integrare.
- [x] Generatori Blender per ingombri e guide, controllati sintatticamente.
- [x] Copia OSM del borgo, inventario di 91 sagome e mappa planimetrica.
- [x] Pipeline di trasformazione e preparazione di una strada con quote verificate.
- [x] Parsing/lint GDScript e istruzioni di collaudo sul PC.

Queste consegne non chiudono automaticamente le prove P1–P4. Venti cicli logici Python non equivalgono a venti cicli animati in gioco.

## P0 — Fondamenti e riferimenti

- [x] Scrivere progetto e criteri di collaudo.
- [x] Fissare Yaris Trend MY22 senza optional tramite richiesta dell’utente e scheda Toyota.
- [x] Osservare i riferimenti anatomici e degli occhi.
- [x] Esaminare campioni Street View di via Prestento e del nucleo davanti alla chiesa.
- [x] Confrontare quattro fotografie originali con autore e data.
- [ ] Confermare il prato preciso con l’utente.
- [ ] Verificare il collegamento pedonale continuo prato–borgo.
- [ ] Censire gli esterni caratteristici di Valle e indicare le lacune.
- [ ] Ricavare una polilinea stradale riutilizzabile e verificare quota e sistema di riferimento del terreno.
- [ ] Completare il censimento dei tornanti di salita e discesa.

**Incremento GIS del 20/10/2026:** pipeline QGIS e catalogatore DTM; **acquisizione reale di 1.149 ways OSM e realizzazione di un candidato planimetrico chiuso A/B/C/V/D/E/F di 18.867,6 m**, derivato con grafo e test di regressione contro i dati versionati. **Ancora aperti**: conferma della geometria scelta ai bivi, censimento dei tornanti e rilievo continuo, quote e DTM, larghezze e verifica guidabilità. [Rapporto con prove e limiti](TRACCIATO_OSM_CANDIDATO_20261020.md).

**Incremento LiDAR 0,5 m del 20/10/2026:** le 4 tessere del borgo `06701210/11/14/15` sono state realmente fornite dall'utente, analizzate e controllate su **12.096.000 celle**, nessun NoData, overlap 80 m senza differenze. Mosaico GeoTIFF 0,5 m e prototipo terreno GLB ~4 m generati, **non collaudati in Godot/Blender né caricati come asset sul GitHub pubblico**. Procedura locale riproducibile in `tools/import_valle_lidar05.py`; [documentazione](ACQUISIZIONE_LIDAR05_REALE_20261020.md). **P0 rimane aperta** per conferma strade, pendenze dell'asfalto, rilievo del borgo e resto del circuito.

Uscita: dossier del percorso e del borgo con copertura esplicita, riferimenti del veicolo e prova di scala dei protagonisti.

## P1 — Anatomia, abitacolo e laboratorio fisico

- [ ] Bloccare silhouette naturale e dimensioni con scala uniforme.
- [ ] Progettare seduta e prolunghe dei pedali con arti a lunghezza fissa.
- [ ] Provare sterzata, frenata ed uscita dalla porta sullo stesso rig.
- [ ] Implementare telaio, sospensioni, pneumatici e trazione anteriore.
- [ ] Calcolare masse, baricentro e inerzia dell’insieme.
- [ ] Verificare equilibrio, rampa, cerchio costante, perdita di aderenza e primo sollevamento ruote.
- [ ] Ottenere ribaltamento e recupero tramite forze, senza eventi arbitrari.
- [ ] Confrontare i risultati a diversi passi fisici e frame rate.

Uscita: build di laboratorio con telemetria e scenari ripetibili.

## P2 — Percorso e regole provvisorie

- [ ] Rendere l’anello completamente percorribile con geometria semplice.
- [ ] Implementare checkpoint direzionali, incidenti e ripartenze.
- [ ] Gestire la tappa di sosta e distinguere arrivo a Valle da conclusione del giro.
- [ ] Bloccare la partenza di ritorno senza entrambi gli occupanti nelle posizioni previste.

Uscita: giro valido e incidente dimostrati sulla geometria provvisoria.

## P3 — Arrivo a Valle come campione completo

- [ ] Modellare Yaris e protagonisti vicini alla qualità finale.
- [ ] Realizzare albero, coffa, accessi e cinematismi.
- [ ] Costruire prato, tratto stradale e collegamento al borgo.
- [ ] Mostrare parcheggio, portiera, pedana, discesa e risalita dalla coffa.
- [ ] Verificare camera e prestazioni con il carico e i materiali rappresentativi.

Uscita: campione giocabile che dimostri insieme stile, guida e passaggio a piedi.

## P4 — Valle esplorabile

- [ ] Ricostruire chiesa, campanile, piazzetta e facciate adiacenti documentate.
- [ ] Costruire i vicoli e percorsi esterni effettivamente verificati.
- [ ] Implementare camminata/trotto a quattro zampe, pendenze e gradini.
- [ ] Implementare seguito della compagna e recupero dai blocchi.
- [ ] Collegare punti panoramici e sosta da picnic.
- [ ] Gestire salvataggi di visita e ritorno alla guida.
- [ ] Superare venti cicli completi di parcheggio, uscita, visita, rientro e ripartenza.

Uscita: visita continua senza blocchi e senza duplicazioni di personaggi o masse.

## P5 — Completamento e consegna

- [ ] Completare l’ambiente del circuito, con località secondarie più generiche.
- [ ] Rifinire audio, UI, tutorial, accessibilità e input.
- [ ] Verificare un giro completo con sosta e ritorno.
- [ ] Collaudare build esportate su Linux e Windows.
- [ ] Misurare prestazioni sull’hardware dichiarato e registrare limiti residui.
- [ ] Confezionare build, sorgenti artistici e documentazione.

Le stime di lavoro sono nel progetto completo e vanno ricalcolate dopo P3. Non assegnare una percentuale di completamento sulla sola quantità di documentazione.

