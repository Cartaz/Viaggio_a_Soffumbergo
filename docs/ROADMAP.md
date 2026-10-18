# Roadmap verificabile

Stato attuale: preparazione tecnica e sorgenti del laboratorio, non ancora eseguiti negli editor. Una casella completata richiede una consegna o una prova ispezionabile.

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

