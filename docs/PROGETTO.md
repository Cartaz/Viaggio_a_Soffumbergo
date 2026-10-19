# Coffa e tornanti

> Aggiornamento personaggi del 19/10/2026: l’utente ha autorizzato corporature adattate agli studi e locomozione bipede, con Bianca più affusolata e Bernie compatto. Questa scelta supera i precedenti riferimenti all’esclusività quadrupede e ai soli occhi deformati. Due modelli vestiti hanno ora rig, guida/tenuta animate e reazioni verificate nel laboratorio. Cammino, scalata e fitting finale restano aperti; vedere anche ANIMAZIONI.md. Vedere [PERSONAGGI.md](PERSONAGGI.md).

## Progetto di un’esperienza di guida ed esplorazione 3D fra Faedis e Soffumbergo

Versione 2.0 — 19 ottobre 2026. Documento di progettazione, non prototipo già implementato. Integra la Trend senza optional, anatomia naturale dei topolini con soli occhi ingranditi, prolunghe meccaniche, fedeltà concentrata su Valle, parcheggio nel prato ed esplorazione a piedi.

Un’auto piccola, due topolini grandi e un albero maestro decisamente fuori scala: una gita verso Soffumbergo diventa una prova di guida delicata, fra boschi, borghi e panorami friulani.

## 1. Decisioni concordate e obiettivo

| Aspetto | Specifica |
| --- | --- |
| Piattaforme | Gioco nativo per PC Linux e Windows, offline, giocatore singolo |
| Territorio | Circuito riconoscibile; Valle di Soffumbergo fedele nelle parti documentate, Faedis e le altre località più generiche |
| Grafica | 3D dettagliato e cartoonesco, forme morbide, materiali curati, atmosfera accogliente |
| Veicolo | Toyota Yaris Hybrid MY 2022 Trend per il mercato italiano, rossa, senza optional aggiuntivi, proporzioni fedeli |
| Modifica | Foro nel tetto, albero maestro e coffa occupata dalla passeggera |
| Personaggi | Proporzioni da topo naturale come IMG_8548.webp; unica deformazione anatomica: occhi grandi ed espressivi come IMG_8549.png; lui guida, lei è sulla coffa in tenuta da picnic |
| Movimento | Dinamica fisica coerente per veicolo, struttura e movimento corporeo dei personaggi |
| Meta della gita | Valle di Soffumbergo: parcheggio in una zona verde lungo la strada sotto il paese, discesa dall’auto e visita a piedi |
| Sfida completa | Raggiungere la meta, effettuare la sosta e tornare a Faedis completando l’anello senza ribaltarsi |
| Identità | Gita tenera e buffa, con tensione generata da curve, velocità e trasferimenti di carico |

Durante la guida il giocatore controlla l’auto e la topolina reagisce autonomamente; non esiste un secondo comando per spostarne il peso. Durante la visita il giocatore controlla il topolino e la compagna lo segue. La visita è libera, senza limite di tempo. La sosta a Valle e il completamento dell’anello sono due traguardi distinti: raggiungere il paese non elimina la parte di ritorno richiesta all’inizio.

**Criterio generale:** l’aspetto è da piccolo mondo illustrato; le conseguenze di sterzata, frenata, pendenza e massa devono essere comprensibili e coerenti. Non si promette una simulazione ingegneristica validata della Yaris modificata: mancano misure reali di quella configurazione immaginaria. Si realizza un modello fisico verificabile e dichiaratamente approssimato.

## 2. Perimetro della prima versione completa

La versione 1.0 del gioco comprende un circuito completo, un’auto, due personaggi, una condizione ambientale asciutta diurna, tutorial, pratica per settori, parcheggio sotto Valle, discesa e risalita dei protagonisti, esplorazione a piedi degli esterni accessibili del borgo, ritorno in auto, risultati, impostazioni e salvataggi locali.

Il circuito è una strada temporaneamente riservata alla gita. Non servono traffico dinamico o pedoni attraversanti: le prime difficoltà sono già la strada e la struttura sul tetto. Personaggi ambientali eventualmente presenti rimangono in aree protette, come cortili e terrazze.

Base territoriale: **l’anello di circa 20 km indicato nella schermata fornita dall’utente**, attraverso Faedis, Campeglio e Valle di Soffumbergo [S11]. La schermata riporta 39 minuti di itinerario automobilistico: è una stima dell’app, non il tempo di gioco previsto né una misura indipendente eseguita in questo progetto.

Si parte dalla ricostruzione dell’intero anello, preservando i tornanti di salita e discesa. La precedente ipotesi di un circuito ridotto a 5–7 km è superata dagli allegati e dalla richiesta di sopralluogo. Adattamenti artistici e piccole correzioni per la giocabilità restano ammessi; eventuali accorciamenti dei collegamenti si valutano soltanto dopo aver documentato il percorso completo. Nessun taglio automatico ai tornanti. Il tempo effettivo del giro viene misurato con la fisica funzionante; pratica a settori e ripartenze vicine permettono di imparare senza ripetere sempre tutto l’anello.

Non sono inclusi nella prima versione: mondo aperto esteso oltre circuito e borgo, interni delle abitazioni, multiplayer, altre automobili, tuning meccanico, meteo variabile, ciclo giorno/notte, distruzione strutturale completa e simulazione interna dettagliata della trasmissione ibrida. Gli esterni di Valle e la visita a piedi sono parte del perimetro principale.

## 3. Riferimenti verificati e limiti delle fonti

La cartina informativa del Comune di Faedis riporta Faedis, Campeglio, Colloredo di Soffumbergo, Valle di Soffumbergo e Canal di Grivò. La stessa carta dichiara un uso indicativo e decorativo: è adatta all’orientamento iniziale, non alla ricostruzione metrica delle curve [S1].

Il catalogo regionale FVG descrive modelli altimetrici a passo 0,50 m derivati dai rilievi LiDAR 2017–2020 [S2]. La copertura effettiva delle tessere utili, la modalità di download, il sistema di coordinate e le condizioni di riuso vanno verificati nella fase GIS. Questa ricerca non ha scaricato né validato quelle tessere.

Toyota documenta la quarta generazione europea della Yaris e il sistema ibrido da 116 CV [S3]. Una scheda ufficiale della Yaris GR SPORT dell’epoca riporta ingombri di 3.940 × 1.745 × 1.500 mm e passo di 2.560 mm [S4]. Questi sono riferimenti dimensionali della carrozzeria; la versione scelta dall’utente è la **Trend senza optional**, le cui dotazioni sono verificate nella scheda italiana MY22 [S13]. Non si trasferiscono alla Trend cerchi o dettagli specifici della GR SPORT.

La documentazione ufficiale Godot avverte che VehicleBody3D presenta problemi noti e non è progettato per una fisica automobilistica realistica [S5]. È una ragione concreta per prevedere un modello dedicato, invece di appoggiare tutta la meccanica centrale al componente standard.

Tutti i numeri di masse aggiunte, baricentro, aderenza, durata, budget grafici e carico di lavoro che seguono sono **ipotesi progettuali o obiettivi di collaudo**, salvo esplicita attribuzione a una fonte.

## 4. Ricostruzione geografica

### 4.1 Tracciato di lavoro

Gli allegati chiariscono il riferimento: **Faedis → Campeglio → Valle di Soffumbergo → ritorno a Faedis sul ramo nordoccidentale mostrato nella mappa**. È lo stesso anello che nella schermata dell’app parte da Valle, passa per Faedis e Campeglio e torna a Valle; spostare l’origine del giro a Faedis non cambia l’anello.

Il collegamento del ramo nordoccidentale con la zona di Canal di Grivò e i passaggi intermedi vanno verificati sui dati stradali. Colloredo non viene inserito automaticamente come checkpoint soltanto perché è una località vicina: devono decidere polilinea e sopralluogo. Il verso di lavoro proposto è partenza da Faedis, avvicinamento a Campeglio, salita a Valle e ritorno sul ramo verso via dei Castelli. Le posizioni esatte di partenza e arrivo rimangono una scelta di game design.

### 4.2 Procedura GIS

1. Ottenere una polilinea stradale chiusa da dati riutilizzabili, eventualmente OpenStreetMap; in alternativa far indicare i passaggi essenziali all’utente.
2. Conservare separati il tracciato sorgente e la versione adattata. Annotare origine, data, condizioni di utilizzo e trasformazioni.
3. Usare QGIS per riproiettare i dati in un sistema metrico adatto alla zona, verificando il sistema di riferimento del DTM. Evitare calcoli di distanze in gradi geografici. Il tracciato metrico deriva da fonti geografiche riutilizzabili, non dal ricalco delle immagini Google.
4. Importare terreno e tracciato in coordinate locali vicino all’origine del mondo, mantenendo una trasformazione documentata verso le coordinate geografiche.
5. Ricavare la quota iniziale della strada dal terreno e correggerla nei punti in cui ponti, rilevati, muri o tornanti rendono inadeguato il campionamento automatico.
6. Costruire la strada con una spline 3D, sezione trasversale, banchine, pendenza longitudinale e inclinazione trasversale esplicite.
7. Confrontare una vista dall’alto, il profilo altimetrico e immagini di riferimento. Non confondere un itinerario escursionistico con una strada carrabile.
8. Preparare una mappa con origine, salita, paese, discesa e ritorno; mostrare anche la versione di gioco per rendere trasparenti gli adattamenti.

OpenStreetMap richiede attribuzione e applica la ODbL: le modalità di distribuzione dei dati derivati vanno gestite secondo le indicazioni ufficiali [S10]. Non si incorporano automaticamente immagini, texture o modelli di servizi cartografici soltanto perché visibili online.

### 4.3 Come adattare senza perdere il luogo

Conservare la sequenza dei paesaggi, i rapporti fra collina e pianura, i cambi di pendenza, l’alternanza di abitato e bosco e alcuni riferimenti architettonici. Ridurre soprattutto trasferimenti ripetitivi e rettilinei poco significativi.

Evitare una compressione uniforme estrema: accorciare tutto aumenta le curvature e altera la fisica. L’impostazione di lavoro mantiene l’anello completo. Se, dopo il sopralluogo e la prova di guida, si propone di abbreviare un collegamento, si ricostruiscono raccordi geometrici regolari e si documenta il cambiamento. Ogni curva modificata si collauda con l’auto e il carico definitivo.

La fedeltà è distribuita secondo la priorità esplicita dell’utente:

| Zona | Fedeltà richiesta | Libertà di adattamento |
| --- | --- | --- |
| Valle e prato di sosta | Massima sulle parti documentate: esterni, viabilità, quote relative, chiesa, campanile, accessi e viste | Materiali e forme cartooneschi; non sostituire il paese con un borgo generico |
| Salita e discesa | Andamento riconoscibile, sequenza dei tornanti e alternanza bosco/aperture | Vegetazione e dettagli secondari semplificabili; correzioni stradali documentate |
| Faedis, Campeglio e collegamenti | Coerenza geografica generale e atmosfera friulana | Edifici e arredi più generici, costruiti con moduli coerenti |

Dentro Valle non si sposta un edificio caratteristico per semplificare l’inquadratura: si corregge prima la camera. Il confronto riguarda anche viste dal basso e prospettiva dal prato. Le parti ignote restano dichiaratamente approssimate. I materiali mantengono la stessa qualità e coerenza nelle zone meno fedeli.

### 4.4 Sopralluogo Google Street View, passo per passo

Richiesta esplicita dell’utente: osservare come si snodano i tornanti sia in salita sia in discesa. Questa diventa una fase necessaria prima di finalizzare la strada e produrre tutto l’ambiente.

Street View si consulta nel browser come riferimento visivo. La costruzione metrica di strada, terreno ed edifici usa basi geografiche e riferimenti con condizioni di riuso adeguate. Le fotografie Google non diventano texture o asset incorporati nel gioco. L’osservazione visiva non fornisce da sola pendenze o raggi esatti: prospettiva, grandangolo e inclinazione della camera possono ingannare.

Procedura operativa:

1. Preparare la polilinea chiusa indipendente e suddividerla in rami: Faedis–Campeglio, salita Campeglio–Valle, attraversamento/accesso di Valle, ramo di ritorno verso Faedis.
2. Individuare la copertura Street View di ciascun ramo. Distinguere panorami navigabili di Google, foto sferiche isolate e normali fotografie degli utenti: una galleria fotografica non prova la percorribilità virtuale della strada.
3. Iniziare al punto di partenza scelto e avanzare in modo continuo, senza saltare a una destinazione diversa con una nuova ricerca. A ogni bivio verificare il ramo sulla polilinea, evitando che il sopralluogo prenda involontariamente una scorciatoia.
4. Osservare ogni immagine nei tratti con curve strette, cambi di pendenza o ostacoli. Nei raccordi omogenei registrare inizio/fine e continuità della copertura, senza inventare dettagli non visti.
5. Per ogni tornante osservare ingresso, centro e uscita, ruotando la visuale quando necessario; controllare anche la vista all’indietro. Annotare se la curva successiva si vede prima di quella attuale e quando il bosco nasconde l’orizzonte.
6. Annotare qualitativamente carreggiata, segnaletica, banchine, muri, guardrail, aperture sul panorama, edifici e vegetazione. Separare ciò che è visibile da ciò che viene stimato o resta coperto.
7. Verificare gli ostacoli in quota rispetto alla futura coffa: rami, sottopassi, cavi e aggetti. Le immagini non consentono una misura certa dell’altezza libera; il gioco richiede un controllo geometrico del volume dell’intero veicolo.
8. Osservare il ramo di discesa nella direzione di gioco, perché leggibilità e occlusioni cambiano col senso di marcia. Non ricavare la discesa soltanto invertendo le annotazioni della salita.
9. Registrare la data delle immagini quando esposta e i punti dove cambia la campagna fotografica. Una pianta spoglia in una ripresa primaverile non significa che la scena estiva debba essere priva di fogliame.
10. Marcare esplicitamente interruzioni, panorami mancanti o rami non navigabili. Per quei tratti usare altri riferimenti consentiti o mantenere la ricostruzione dichiaratamente approssimata. Non estendere la descrizione del panorama precedente al tratto mancante.
11. Confrontare il circuito provvisorio in gioco con le osservazioni: prima ordine e andamento delle curve, poi terreno, ingombri e architettura, infine dettagli artistici.

Il lavoro produce un diario testuale di sopralluogo con copertura verificabile e riferimenti consultabili. Gli screenshot del browser rimangono materiale di ispezione interno, salvo richiesta dell’utente di riceverli come allegati.

### 4.5 Scheda di ricostruzione per curva o tratto

Ogni elemento del percorso riceve un identificatore progressivo soltanto quando viene effettivamente osservato. Non si assegna qui un numero totale di tornanti: non è stato ancora contato.

| Campo | Contenuto da compilare |
| --- | --- |
| Identificatore | Ramo e progressivo, per esempio SAL-001 o DIS-001; esempi di formato, non curve già censite |
| Posizione | Progressiva sulla polilinea indipendente e località/strada |
| Direzione | Senso di marcia e curva destra/sinistra |
| Forma | Tornante, curva ampia, esse, raccordo; raggio misurato sulla base geografica quando disponibile |
| Profilo | Quota e pendenza dai dati territoriali; impressione visiva tenuta distinta |
| Ingresso/uscita | Visibilità, chiusura/apertura della curva e collegamento alla successiva |
| Margini | Muro, prato, bosco, parapetto o scarpata, sui due lati |
| Elementi distintivi | Edificio, slargo, incrocio, panorama o vegetazione riconoscibile |
| Ingombro alto | Elementi da verificare con l’altezza e il volume della coffa |
| Evidenza | Fonte, data delle immagini e riferimento consultabile |
| Attendibilità | Osservato, stimato o non verificato |
| Adattamento nel gioco | Modifica proposta e sua motivazione, oppure nessuna modifica |
| Stato | Da osservare, osservato, modellato, collaudato |

La copertura si misura sulla lunghezza della polilinea con tratti osservati e tratti mancanti. Il numero di immagini aperte da solo non prova di aver coperto tutto il giro. Per finalizzare il percorso serve la continuità di entrambi i rami collinari, oppure un elenco esplicito delle lacune e delle fonti sostitutive.

### 4.6 Stato reale del sopralluogo al 19 ottobre 2026

- Allegati IMG_8546.png e IMG_8547.png: aperti e osservati. Documentano l’anello scelto e la stima di circa 20 km dell’app [S11].
- Google Maps: aperto su Faedis e poi Valle di Soffumbergo.
- Street View: accesso riuscito su **77 via Prestento**, immagini indicate come **marzo 2026**. Controllo ripreso lungo il margine occidentale: strada e prato sotto il paese, vista al campanile, prosecuzione verso il limite settentrionale. Riferimenti intorno a 46.15687 N, 13.39181 E per il prato e 46.15847 N, 13.39226 E per il tratto nord: posizioni del panorama, non rilievi topografici [S12, S15].
- Esaminati quattro scatti originali di autori identificati su Wikimedia Commons, due del 2020 e due del 2008. Documentano facciata, campanile e parti dello spazio circostante. Allestimenti delle feste e auto presenti nelle foto non diventano automaticamente elementi del gioco [S16–S19].
- Riuscito anche l’accesso Street View nel nucleo davanti alla chiesa, con immagini esposte come **maggio 2023**: osservati in più direzioni piazzetta, facciate adiacenti, terrazza con albero e gradini e imbocco della discesa. Il borgo centrale ha quindi riscontri diretti oltre alle fotografie, senza copertura completa di tutti i vicoli [S22].
- Non sono ancora censiti i tornanti dell’intera salita né dell’intera discesa. Il campione non permette di attestare larghezze esatte, pendenze, numero di curve o copertura continua dell’anello.
- La prima sessione browser si era interrotta; il controllo è stato ripreso il 19 ottobre. La copertura di tutti i vicoli, del collegamento pedonale prato–borgo e dell’intero anello non è ancora attestata. Il documento consegna progetto e riscontri parziali, non un rilievo completo.

### 4.7 Borgo e area verde di sosta

Identificatore di lavoro **PV-01**: prato osservato accanto a via Prestento, sul lato del borgo, con accesso chiaro/ghiaioso e vista al campanile più in alto. È un candidato coerente con la descrizione dell’utente, non una conferma dell’esatto prato desiderato. La presenza di un accesso non attesta che sia un parcheggio pubblico reale: nel gioco diventa una zona di sosta della gita.

Prima di fissarlo: verificare pendenza, spazio di manovra, terreno, ostacoli in quota e collegamento pedonale. Non inventare una scalinata diretta alla chiesa se non documentata. Se l’accesso reale passa da una strada più lunga, rappresentarlo o dichiararne l’adattamento.

Per ogni elemento caratteristico di Valle preparare una scheda con posizione, foto, data, prospetti visibili, proporzioni e parti ignote. Chiesa, campanile e spazi adiacenti precedono le case secondarie. Gli scatti del 2008 e 2020 sono confronti storici e non provano lo stato attuale di ogni facciata.

## 5. Struttura del circuito e progressione

Questi settori sono funzioni di gioco da collocare sul tracciato adattato, non descrizioni puntuali già verificate dei luoghi reali.

| Settore | Atmosfera | Cosa insegna o verifica | Accorgimenti |
| --- | --- | --- | --- |
| A. Partenza a Faedis | Piazza o slargo riconoscibile, case e verde | Partenza, frenata dolce, sterzata progressiva | Spazio per ripetere il tutorial; nessuna sorpresa |
| B. Avvicinamento alla collina | Campagna, filari dove documentati, case sparse | Il peso in alto si sente anche nelle curve ampie | Prima occasione sicura di alleggerire le ruote interne |
| C. Salita | Boschi, muri di sostegno, tornanti | Preparare la velocità prima della curva | Tornanti leggibili; banchine e parapetti con collisioni curate |
| D. Valle e visita | Prato, borgo fedele, campanile e panorama | Parcheggio, discesa ed esplorazione a piedi | La guida termina nel prato durante la sosta; niente auto forzata nei vicoli |
| E. Discesa | Curve concatenate e visuali variabili | Gestire velocità, frenata e inversione del rollio | Tratto più tecnico; pericoli segnalati dall’ambiente |
| F. Rientro | Apertura del paesaggio e ritorno al paese | Non perdere il controllo dopo la parte difficile | Finale riconoscibile e arrivo celebrato con sobrietà |

Prevedere almeno tre punti panoramici e alcune zone di sosta. Fermarsi a guardare deve essere possibile nella modalità gita e allenamento. La strada deve essere percorribile lentamente senza un fallimento imposto dal tempo.

## 6. Direzione artistica

### 6.1 Linguaggio visivo

Un piccolo mondo illustrato tridimensionale: volumi pieni, spigoli addolciti, vegetazione a masse leggibili, colori naturali semplificati e superfici con variazioni dipinte a mano. Animal Crossing è un riferimento per calore e leggibilità, non un insieme di asset o personaggi da copiare.

La qualità deve emergere da composizione, luce, animazione e coerenza dei materiali. Una mesh con pochi poligoni non è una scelta stilistica sufficiente. Evitare sia l’aspetto da prototipo con coni e cubi, sia il contrasto fra un’auto fotorealistica e un paesaggio da giocattolo.

Materiali: intonaco morbido, pietra leggibile senza rumore eccessivo, legno con venature larghe, stoffe opache, carrozzeria verniciata con riflessi controllati. La Yaris conserva le proporzioni; è il trattamento delle superfici a integrarla nel mondo.

### 6.2 Palette e luce

Proposta iniziale: pomeriggio di fine estate, cielo chiaro, sole caldo e ombre morbide. Verdi salvia e bosco, pietra calda, tetti terracotta, tocchi crema. Il rosso dell’auto è il punto focale. La tenuta da picnic usa colori che restano distinguibili sia dal rosso sia dalla vegetazione.

Preferire illuminazione statica precalcolata per gran parte dell’ambiente, con luce e ombre dinamiche per auto, struttura e personaggi. Foschia atmosferica leggera per profondità e leggibilità del panorama. L’illuminazione definitiva si valuta su immagini reali del gioco, non soltanto su un render esterno.

### 6.3 Tre distanze di dettaglio

| Fascia | Contenuto | Priorità |
| --- | --- | --- |
| Vicina alla strada | Muri, vegetazione, portoni, vasi, panchine, segnaletica, canali e giunti | Modellazione, materiali e collisioni accurati |
| Intermedia | Cortili, pendii, filari e case secondarie | Moduli e istanze con variazioni controllate |
| Panorama | Colli e pianura lontana | Silhouette, colore e profondità; geometria economica |

## 7. Yaris: riproduzione e modifica piratesca

### 7.1 Specifica del modello

Modellare in Blender a scala reale, un’unità uguale a un metro. Raccogliere riferimenti frontali, posteriori, laterali e a tre quarti della Yaris europea corretta. Il materiale Toyota serve a verificare l’identità, non giustifica l’uso indiscriminato delle immagini come texture.

**Configurazione confermata:** Hybrid Trend MY22 italiana, dotazione di serie, nessun pacchetto aggiuntivo. Il rosso richiesto viene mantenuto; Emotional Red 3U5 è il riferimento cromatico previsto nella scheda dell’epoca [S13]. La scelta cromatica non autorizza l’aggiunta di altri accessori.

| Dettaglio da riprodurre | Riferimento Trend MY22 [S13] |
| --- | --- |
| Ruote | Lega da 16 pollici, pneumatici 195/55 R16 |
| Illuminazione | Fari e fendinebbia LED, gruppi posteriori LED Light Guide |
| Carrozzeria | Maniglie e specchi in tinta; tetto monocolore; vetri posteriori non oscurati |
| Abitacolo | Tessuto nero, volante in pelle, climatizzatore automatico monozona |
| Strumenti e multimedia | Display da 4,2 pollici e tachimetro digitale; Toyota Touch 3, quattro altoparlanti |
| Avviamento | Configurazione senza Smart Entry/Push Start opzionale |
| Parcheggio | Retrocamera di serie |

Nessun Comfort Pack, navigatore opzionale o accessorio di altre versioni. Il foro, l’albero e la coffa costituiscono la modifica narrativa richiesta; il resto dell’auto segue questa configurazione.

Devono risultare riconoscibili: sagoma compatta a cinque porte, proporzioni della vetratura, disegno dei gruppi ottici dell’allestimento scelto, calandra, paraurti, passaruota, portellone, specchi e cerchi. Non mescolare Yaris, Yaris Cross, GR Yaris e dettagli di aggiornamenti successivi al MY richiesto.

Il modello comprende ruote separate, sospensioni visibili quanto basta, sterzo, fari, stop, retrovisori semplificati e un interno credibile nelle parti inquadrate. Il guidatore deve vedersi dai finestrini senza richiedere una simulazione ottica costosa dei vetri.

Per la verifica dimensionale: errore massimo dell’1% su ingombri principali e passo rispetto al riferimento selezionato. Il giudizio finale di somiglianza richiede confronti visivi, perché le sole dimensioni non garantiscono una carrozzeria fedele.

### 7.2 Albero e coffa

Foro del tetto realmente modellato, con bordo rifinito e collare visibile. L’albero attraversa l’abitacolo e trova un appoggio immaginario nella struttura inferiore: non appare incollato alla lamiera del tetto. Posizione iniziale proposta: zona centrale/posteriore dell’abitacolo, da controllare per spazio del guidatore e bilanciamento longitudinale.

La coffa ha pavimento, parapetto in legno, fissaggi, una bandierina e un piccolo cesto. Nessuna vela nella prima versione: introdurrebbe un’altra meccanica aerodinamica prima di aver stabilizzato quella centrale.

Quota iniziale di progetto del pavimento: circa 5,5 m dal suolo a vettura ferma. L’altezza complessiva si ricalcola con il topo ad anatomia naturale e la sua postura; la precedente ipotesi intorno a 7 m non è una dimensione da imporre. Sono valori da sperimentare. La coffa deve essere leggibile senza oscurare la strada e avere una via di discesa visibile.

Il carico non si stacca durante il normale gioco. La deformazione strutturale completa non è inclusa: elasticità limitata e ribaltamento sono sufficienti. Gli oggetti da picnic sono vincolati; un cappello può muoversi senza diventare causa casuale di fallimento.

## 8. Personaggi e animazione

### 8.1 Design

**Riferimento anatomico vincolante: IMG_8548.webp, osservato direttamente.** Corpo raccolto e arrotondato, muso da roditore, zampe corte, orecchie proporzionate, vibrisse e coda sottile. Non si costruisce un corpo umano con testa da topo. L’impressione cicciottina e goffa deriva dalla sagoma e dalle reazioni.

**Unica eccezione anatomica: occhi grandi ed espressivi**, secondo IMG_8549.png. Ingrandire gli occhi preservando il volume generale di cranio e muso; espressioni tramite sguardo, palpebre, inclinazione della testa e riflessi. Le mani disegnate e gli accessori del meme non sono riferimenti anatomici. Non ingrandire anche orecchie e zampe.

La taglia complessiva resta quella di personaggi grandi rispetto a topi reali, come concordato inizialmente; la scala precisa si fissa con una prova sul sedile e si applica uniformemente al corpo. Le proporzioni naturali prevalgono sulla vecchia ipotesi di postura umana. La taglia umana non impone gambe, busto o altezza eretta da persona. Masse e baricentri si ricalcolano dopo la scelta: gli 85 kg dell’esempio restano ipotesi, non vincoli artistici.

Il rig conserva lunghezze ossee fisse; IK con limiti articolari e senza stiramento. Per raggiungere un bersaglio si adattano meccanismo, seduta e posa entro i limiti. È vietato allungare una zampa per far funzionare la scena.

Gli abiti da picnic si adattano al corpo animale, lasciando liberi appoggi e movimento; non suggeriscono un’anatomia umana nascosta sotto una gonna. Il pelo si rende con materiali e dettagli coerenti, senza simulare ogni pelo.

### 8.1a Prolunghe meccaniche e seduta

Costruire un accessorio separato dalla vettura di serie: seduta sagomata e pedana che portano superfici di comando nella zona raggiungibile dalle zampe posteriori. Le prolunghe di acceleratore e freno hanno leve, rinvii ai pedali originali, fulcri, corsa limitata e ritorno meccanico visibile.

Freno e acceleratore hanno cinematismi distinti, senza compenetrazioni o azionamento incrociato. L’animazione segue la corsa effettiva dei comandi e dei pedali originali. Sono accessori narrativi del gioco, non istruzioni per modificare una vettura reale.

Posizionare seduta e appoggi affinché le zampe anteriori raggiungano il volante senza allungarsi. Se necessario, usare una presa o un rinvio accessorio compatto, dichiarandolo come modifica dedicata. Collaudare riposo, sterzata completa, frenata, cintura ed uscita dalla porta con lo stesso rig.

### 8.2 Guidatore

Animazioni base: respirazione, occhiate, accelerazione, frenata, sterzata, sobbalzo, apprensione e sollievo. Zampe anteriori sugli appoggi del volante e posteriori sui comandi prolungati, con IK senza stiramento; corpo sostenuto dalla seduta e cintura adattata alla sagoma. Testa e corpo reagiscono con ritardo smorzato alle accelerazioni.

Il volante segue l’effettivo angolo delle ruote, non il solo tasto premuto. Evitare che la testa attraversi il vetro o le orecchie escano dal tetto per un errore di rig.

### 8.3 Passeggera

A bassa sollecitazione guarda il panorama e si gira. La postura prevalente è raccolta o sui quattro appoggi; può sollevarsi brevemente sulle zampe posteriori senza locomozione umana. Quando aumenta l’accelerazione laterale, abbassa il corpo, allarga gli appoggi e cerca il parapetto con le zampe anteriori. In frenata tende a spostarsi in avanti rispetto all’auto; nelle curve il movimento relativo iniziale tende all’esterno, seguito dalla correzione attiva.

Le zampe rimangono sulla piattaforma o sugli appoggi raggiungibili con IK senza stiramento; il corpo segue un equilibrio attivo con limiti anatomici e ritardi. Parapetto e impugnature si adattano alla sua portata. Vestito, orecchie, coda e cappello hanno movimento secondario smorzato, principalmente visivo.

È importante distinguere due livelli: le oscillazioni decorative non cambiano la massa; lo spostamento consistente del busto e del bacino viene rappresentato nel modello dinamico e produce una reazione sulla struttura. Non si sposta visivamente un personaggio pesante lasciando la sua massa fisica fissa altrove.

### 8.4 Rappresentazione fisica sostenibile

Per il prototipo: un unico corpo rigido equivalente per auto, albero, coffa e occupanti, con baricentro e inerzia calcolati. Serve a verificare la meccanica, ma **non soddisfa ancora completamente** la richiesta sui movimenti dei passeggeri.

Per la versione completa: telaio e parte fissa dell’albero come corpo principale; gruppo alto con massa di coffa e passeggera rappresentata da pochi corpi equivalenti e collegamenti elastici limitati; massa mobile del corpo della topolina vincolata alla piattaforma con controllo attivo e reazioni reciproche. Il rig grafico segue questi stati, senza simulare ogni dito o osso.

Il guidatore, vincolato al sedile, può essere incluso nella massa del telaio se i suoi spostamenti fisici restano piccoli; reazioni più ampie vanno modellate o limitate. Nessuna massa va contata due volte. I corpi dinamici rimangono indipendenti nella gerarchia fisica e collegati da vincoli, senza trasformazioni ereditate che li teletrasportino.

Questa soluzione è un’approssimazione a pochi gradi di libertà, da verificare per stabilità e credibilità. Un ragdoll integrale libero durante la guida sarebbe più difficile da controllare e non equivale automaticamente a un comportamento umano più realistico.

## 9. Modello fisico del veicolo

### 9.1 Regole fondamentali

Fisica in metri, chilogrammi e secondi, gravità iniziale 9,81 m/s². Aggiornamento a passo fisso, candidato iniziale 120 Hz con rendering interpolato; il valore finale dipende dai test di convergenza e dal costo CPU. Non basta aumentare la frequenza per correggere un modello errato.

L’auto è un corpo dinamico mosso da forze e coppie. Non viene riposizionata a ogni fotogramma sulla spline della strada. Non si blocca il rollio, non si introduce una rotazione arbitraria quando supera una velocità e non si applica una coppia invisibile per farla ribaltare.

RigidBody3D offre massa, baricentro personalizzato, inerzia, applicazione di forze e rilevamento continuo delle collisioni [S7]. Per una configurazione asimmetrica occorre gestire anche gli assi principali di inerzia, oppure ricorrere a un’approssimazione simmetrica dichiarata e verificata. Cambiare soltanto il baricentro lasciando l’inerzia di un’auto normale è insufficiente.

### 9.2 Sospensioni e contatto ruota

Quattro punti ruota con molla, smorzatore, fine corsa e antirollio fisicamente motivato. Si parte con sospensioni equivalenti tarate per la risposta richiesta; non si pretende di riprodurre ogni cinematismo della vettura reale.

Per il contatto stradale, confrontare shape cast a volume finito e raggi multipli con campioni rappresentativi di tornanti, banchine e giunti. Un solo raggio centrale è economico ma rischia di saltare cordoli e bordi. Il componente selezionato deve rilevare correttamente anche atterraggi e ruote quasi scariche.

Le forze si applicano in punti coerenti con la geometria della sospensione e del contatto. Ogni ruota conserva carico normale, compressione, velocità di rotazione e stato di aderenza. Una ruota senza contatto non deve continuare a generare forza laterale.

### 9.3 Pneumatici

Modello combinato longitudinale/laterale con saturazione progressiva in funzione di slittamento e angolo di deriva, dipendenza dal carico e cerchio o ellisse di aderenza. A bassissima velocità si usa un trattamento regolarizzato che eviti divisioni instabili e tremolii.

La taratura deve permettere sia scivolamento sia ribaltamento. Un’auto con poco grip può slittare prima di capovolgersi: aumentare indiscriminatamente l’aderenza per ottenere il ribaltamento produrrebbe un comportamento poco credibile. Con il carico alto scelto, la soglia di scarico delle ruote interne va confrontata con quella di perdita di aderenza.

Materiali iniziali: asfalto asciutto e banchina erbosa/ghiaiosa, con transizione controllata. Cordoli, terrapieni e muretti possono causare ribaltamenti da urto; non devono essere usati per mascherare una fisica in curva che non funziona.

### 9.4 Motore, freni e sterzo

Trazione anteriore e risposta di una piccola ibrida automatica. Erogazione semplificata ma continua, limite di potenza, resistenze al moto e prestazioni modificate dalla massa aggiunta. La potenza complessiva del sistema non si ottiene sommando automaticamente i picchi del termico e dell’elettrico.

La frenata combina un contributo rigenerativo approssimato e freni meccanici; si tiene conto del trasferimento di carico. ABS e controllo di trazione semplificati possono rendere la guida controllabile, ma non devono eliminare artificialmente la dinamica di ribaltamento.

La stabilizzazione elettronica di serie della Yaris non viene dichiarata riprodotta fedelmente: nella configurazione immaginaria non si dispone della sua calibrazione. Eventuali aiuti che influenzano il rollio sono una modalità assistita esplicita, separata dalla sfida standard.

Sterzo con geometria approssimata coerente, velocità di azionamento limitata e ritorno progressivo. La tastiera deve generare un comando analogico filtrato, non un salto istantaneo a fondo sterzo. Tutti i filtri dipendono dal tempo fisico e sono regolabili.

## 10. Baricentro: calcolo iniziale e calibrazione

La NHTSA definisce il fattore statico di stabilità come rapporto fra carreggiata e doppio dell’altezza del baricentro [S9]. Per un modello rigido semplificato su piano orizzontale:

\[
h_{CG}=\frac{\sum_i m_i h_i}{\sum_i m_i},\qquad SSF=\frac{t}{2h_{CG}},\qquad \frac{a_{y,lim}}{g}\approx SSF
\]

L’ultima relazione è una stima quasi statica di ordine di grandezza, non una previsione completa. Sospensioni, inclinazione della strada, elasticità, pneumatici e transitori cambiano il risultato. Il fattore non è una probabilità di ribaltamento.

### 10.1 Esempio numerico riproducibile

**Tutti i valori della tabella seguente sono ipotesi di sviluppo**, inclusi massa e baricentro della vettura base. Le altezze si riferiscono ai centri di massa, non alla sommità degli oggetti, a veicolo fermo e carico.

| Componente | Massa ipotizzata | Quota del suo baricentro |
| --- | ---: | ---: |
| Auto base, senza occupanti né struttura aggiunta | 1.150 kg | 0,55 m |
| Guidatore | 85 kg | 0,85 m |
| Albero e sostegni, distribuiti lungo la struttura | 180 kg | 3,00 m |
| Coffa | 90 kg | 5,60 m |
| Passeggera | 85 kg | 6,40 m |
| Accessori da picnic | 15 kg | 5,70 m |

Massa totale: **1.605 kg**. Altezza del baricentro equivalente: **circa 1,482 m**. Assumendo una carreggiata di lavoro arrotondata di 1,52 m, si ottiene **SSF ≈ 0,513**, corrispondente a circa **0,51 g** nel modello elementare. Su una curva piana ideale di raggio 20 m, la velocità associata sarebbe circa **36 km/h**, usando \(a_y=v^2/R\).

Questi numeri servono a stabilire se il concetto può funzionare. Non sono dati misurati della Yaris, velocità sicure su una strada reale, né valori finali da imporre al gioco. Masse e geometria della struttura devono anche risultare visivamente credibili: una coffa enorme non può pesare come un cestino e un’asta sottilissima non può giustificare da sola un carico elevato.

### 10.2 Ordine della calibrazione

1. Verificare la vettura base su piano, senza albero: equilibrio, frenata, cerchio a raggio costante e risposta allo sterzo.
2. Aggiungere la struttura rigida con masse e inerzia documentate; confrontare il carico statico sulle quattro ruote con le reazioni attese.
3. Eseguire una prova di inclinazione lenta e confrontarla con l’equilibrio geometrico semplificato.
4. Aumentare gradualmente la velocità su un cerchio costante e misurare scarico ruote, slittamento e rollio.
5. Introdurre struttura elastica e passeggera mobile; verificare dissipazione delle oscillazioni e reazioni reciproche.
6. Solo dopo modificare strada e difficoltà. Non cambiare contemporaneamente grip, massa, altezza, molle e geometria della curva.

## 11. Elasticità della struttura e risposta della passeggera

L’albero deve sembrare abbastanza rigido da sostenere la coffa, con flessione contenuta e ritardata. Una molla molto morbida lo farebbe sembrare gomma, cambiando completamente il tipo di gioco.

Il gruppo superiore può essere rappresentato con pochi gradi di libertà in rollio e beccheggio, limiti angolari e smorzamento. Per collegamenti non adeguatamente rappresentabili dai joint disponibili, implementare forze elastiche e coppie con reazioni opposte sui corpi collegati. La documentazione Jolt segnala differenze e proprietà dei vincoli non supportate: vanno verificate nella versione fissata [S6].

La postura attiva della topolina usa obiettivi limitati, ritardi e capacità di correzione finita. Non deve anticipare una curva senza indizi né compensare perfettamente qualunque accelerazione. Il movimento deve aiutare il giocatore a leggere il pericolo, senza trasformarsi in un salvataggio automatico.

Il controllo attivo può compiere lavoro, come fanno i muscoli: non si impone quindi una conservazione dell’energia dell’intero sistema in ogni manovra. Si devono invece evitare aumenti inspiegabili di energia nei vincoli passivi e nello smorzamento. In assenza di nuovi input, oscillazioni passive devono attenuarsi.

## 12. Regole di gioco e fallimento

### 12.1 Modalità

| Modalità | Regola | Risultato |
| --- | --- | --- |
| Impara | Tutorial breve e settori ripetibili | Nessuna pressione, ripartenza vicina |
| Gita completa | Andata, parcheggio sotto Valle, visita libera e ritorno senza ribaltarsi | Traguardo della gita e completamento dell’anello distinti |
| Visita libera | Accesso al borgo da un salvataggio valido nel prato | Esplorazione senza dover ripetere la salita |
| Prova a tempo | Stessa fisica; tempi di guida per settori, separati dalla durata della visita | Record locale senza fretta durante la passeggiata |

Procedere pianissimo è una soluzione valida per la prima riuscita. La prova a tempo introduce in seguito il compromesso fra prudenza e velocità. Non si inventa un vento obbligatorio o un timer severo per rendere difficile l’obiettivo iniziale.

### 12.2 Stati della corsa

Stati della sessione: pronto, guida di andata, instabilità recuperabile, parcheggio, discesa, esplorazione, risalita, guida di ritorno, incidente e concluso. Due ruote sollevate non equivalgono a un fallimento immediato: il recupero è una parte importante della guida.

Ribaltamento confermato con combinazione di orientamento, appoggio persistente su fianco/tetto o struttura alta e perdita della normale possibilità di marcia. Le soglie angolari e temporali sono parametri da tarare; una soglia diagnostica candidata di circa 80° per un intervallo breve non deve sostituire la verifica dei contatti. Una breve escursione oltre la soglia con recupero resta recuperabile.

Un urto della coffa può generare fisicamente l’incidente; un contatto marginale decorativo non deve far perdere per una regola nascosta. Il gioco evita collisioni punitive con foglie e ramoscelli privi di leggibilità.

In caso di uscita dal mondo, incastro non recuperabile o caduta in una zona chiusa, si offre una ripartenza. In allenamento si torna all’ultimo punto sicuro; nel giro completo il reset rende il tentativo non valido e avvia una nuova corsa o propone l’allenamento del settore.

### 12.3 Validazione del giro

Linea di partenza/arrivo direzionale, checkpoint ordinati, tappa di sosta a Valle e continuità del percorso. Nessuna vittoria attraversando il traguardo in retromarcia, tagliando la collina o saltando settori. Le soglie di distanza devono tollerare soste e piccoli errori senza permettere scorciatoie. Entrambi i protagonisti devono tornare nelle posizioni di viaggio, compresa la passeggera sulla coffa, prima della partenza di ritorno; lasciarla a terra per abbassare il baricentro non è un giro valido.

Risultati: completamento valido, tempo, reset, settori, massimo rollio e momenti di ruote scariche. Le statistiche tecniche più dettagliate rimangono nel menu di analisi, senza invadere l’esperienza normale.

### 12.4 Parcheggio e visita di Valle

**Arrivo:** rallentare sull’asfalto, entrare nel prato di sosta senza sterzate brusche e fermarsi nella zona giocabile individuata. Il cambio asfalto–ghiaia–erba usa le superfici fisiche previste e raccordi reali della geometria. Nessun aggancio magnetico alla posizione corretta. Una guida visiva discreta può indicare lo spazio utilizzabile senza trasformarlo in un parcheggio a righe estraneo al luogo.

**Condizioni per scendere:** auto completamente ferma e sufficientemente assestata, posizione P e freno di stazionamento inseriti, spazio libero per la porta e per la discesa dalla coffa, pendenza compatibile con la sosta. Se una condizione manca, spiegare quale; non teletrasportare la vettura. Velocità e pendenza limite sono parametri di gioco da tarare, non deduzioni dalle fotografie.

**Uscita del guidatore:** apre la porta, libera la cintura, raggiunge la pedana e scende con appoggi alla portata delle zampe. La portiera e la pedana si modellano per questa transizione; il corpo non attraversa volante o vetri. Il giocatore prende il controllo a terra soltanto dopo che la posa è stabile.

**Discesa della passeggera:** predisporre una scaletta a pioli e piccole pedane lungo l’albero, con appigli adatti alla sua anatomia. La topolina scende con un’animazione continua supportata da IK e vincoli. Non salta da oltre cinque metri e non compare magicamente sul prato. La sequenza può essere abbreviata su richiesta, ma il cambiamento di posizione e carico deve rimanere coerente.

**Masse durante la sosta:** ogni personaggio ha un solo responsabile della propria massa. Passare dal corpo equivalente al corpo indipendente mantenendo posa e velocità e verificando la conservazione della quantità di moto; durante la transizione i vincoli e i contatti con auto, scaletta e pedane continuano a trasmettere il peso alla struttura. La quota del carico cambia progressivamente perché il corpo si sposta realmente. Non interpolare percentuali di massa fra due corpi scollegati e non cancellare istantaneamente il peso mentre il personaggio è ancora in alto. Il controller CharacterBody a terra richiede un adattatore di interazione, perché non sostituisce automaticamente il corpo dinamico usato nella scalata. Non consentire di guidare durante questi passaggi. L'adattatore fisico e le animazioni vanno ancora implementati e collaudati.

**Esplorazione:** controllare il topolino in terza persona lungo esterni, stradine, slarghi e percorsi effettivamente documentati di Valle. Camminata e piccolo trotto sui quattro appoggi, brevi posture sulle zampe posteriori per osservare, salita di gradini compatibili con anatomia e scala. Niente gambe allungabili o camminata umana standard. La camera si adatta alla sua altezza e permette di guardare edifici e panorama senza perdere il personaggio.

La compagna segue usando un percorso navigabile controllato, attende nei passaggi stretti e si avvicina ai punti di osservazione. Deve poter raggiungere tutti i punti richiesti senza attraversare muri o comparire continuamente accanto al giocatore. Se resta bloccata, prima ripianifica; un recupero eccezionale usa un punto sicuro fuori dall’inquadratura e non influisce sulla validità del giro. Non trasformare l’IA della compagna in una causa di fallimento della guida.

Per il movimento usare un controller con accelerazione e arresto progressivi, collisioni del corpo, gestione di pendii e gradini e appoggi del rig su superficie. CharacterBody3D è una base possibile: la documentazione lo definisce mosso da script, non un corpo fisico libero; la credibilità locomotoria va quindi costruita e verificata, non attribuita automaticamente al motore [S20]. NavigationAgent3D fornisce strumenti di percorso per la compagna; l’effettivo movimento rimane responsabilità del controller [S21].

Attività minime: raggiungere lo spazio della chiesa e un punto panoramico accessibile, osservare il paese, sedersi o predisporre una breve sosta da picnic. Sono interazioni ambientali leggere, senza missioni artificiali o collezionabili obbligatori. Nessun ingresso nelle case private nella prima versione; gli interni non documentati non si inventano come riproduzioni fedeli.

**Ritorno all’auto:** interagire con la vettura; la compagna torna alla scaletta e risale, il guidatore rientra con la sequenza inversa. Dopo verifica degli occupanti e assestamento si riabilita la guida. L’auto continua ad avere albero e coffa, e riprende il ramo di ritorno dell’anello.

**Salvataggi:** checkpoint persistente dopo una sosta valida e salvataggio dello stato di esplorazione. Registrare posizione dell’auto, freni, personaggi, progressione della gita e versione dei parametri. Al caricamento scegliere un punto sicuro a terra e uno stato completo, senza lasciare il personaggio a metà porta o scaletta. La ripresa conserva la validità precedente, mentre il riavvio dopo un incidente è marcato come nuovo tentativo.

### 12.5 Criteri di qualità della visita

- Si può camminare dal prato al borgo e tornare senza ricaricare una scena scollegata; se il mondo è suddiviso in settori, il passaggio rimane continuo per il giocatore.
- Chiesa, campanile, accessi e spazi circostanti conservano relazioni e forme documentate. La stilizzazione riguarda materiali e dettagli, senza sostituire la geografia con una scenografia generica.
- Zampe e portata degli arti restano identiche in guida, sulla scaletta e a terra; occhi grandi come sola modifica anatomica.
- Non si può partire senza la compagna sulla coffa, creare più copie degli occupanti, duplicare il loro peso o lasciare l’auto in moto durante la visita.
- Almeno venti cicli di parcheggio, uscita, visita, rientro e ripartenza senza blocchi, perdita di progressione o deriva della massa totale.
- Gradini, vicoli e porte delle transizioni si provano alla scala definitiva dei protagonisti; piedi/zampe non pattinano e la coda non si incastra sistematicamente.

## 13. Feedback, comandi e telecamera

### 13.1 Comandi

Tastiera: avanti/indietro, freno, sterzo, camera, pausa e riavvio con pressione prolungata. Gamepad: grilletti per acceleratore e freno, stick per sterzo, pulsanti per camera e menu. Mappatura completa, sensibilità, zona morta e curve analogiche configurabili. La retromarcia richiede auto quasi ferma e azione intenzionale.

Il gamepad è consigliato per modulare la guida; la tastiera deve comunque consentire un giro completo e il recupero dalle instabilità. Supporto volante e force feedback sono estensioni successive.

### 13.2 Camera

Camera principale posteriore a tre quarti, abbastanza lontana da mostrare auto, albero e passeggera e abbastanza bassa da rendere leggibile la strada. Usare FOV moderato, da valutare indicativamente fra 50° e 65°. In curva, inquadratura anticipata e correzione laterale evitano che il palo copra il punto di corda.

La camera filtra il movimento del telaio e conserva un riferimento all’orizzonte: non copia tutte le oscillazioni e non cancella visivamente il rollio. Collisione con ambiente, zoom limitato e comportamento specifico nei borghi. Una camera dalla coffa è una vista opzionale da panorama/allenamento; non è necessaria per vincere.

### 13.3 Segnali di instabilità

Prima il corpo dell’auto si inclina; poi la topolina cambia postura, il legno scricchiola e le gomme interne si alleggeriscono. Un indicatore discreto a forma di piccolo pendolo o sagoma dell’auto può rendere accessibile la lettura del rischio.

L’indicatore usa soprattutto carichi ruota sinistra/destra, velocità di rollio e movimento del gruppo alto, non soltanto l’angolo della carrozzeria. L’angolo da solo confonde pendenza stradale e rischio dinamico.

Vibrazione gamepad facoltativa, segnali visivi e sonori ridondanti, testi scalabili, opzioni per ridurre oscillazione della camera e motion blur. Il colore non è l’unico codice del pericolo.

## 14. Audio e atmosfera

Paesaggio sonoro con uccelli, foglie, ambiente di paese e suono del rotolamento. L’auto alterna contributi elettrici e termici in modo plausibile, con risposta continua al carico: evitare cambi marcia sonori da trasmissione manuale.

Il legno ha un suono elastico leggero; il cesto e i tessuti producono dettagli discreti. Il guidatore e la passeggera comunicano soprattutto con piccoli versi ed espressioni. Eventuali battute sono rare, contestuali e con intervallo minimo, così la quindicesima ripetizione non diventa la vera prova di resistenza.

Musica acustica leggera opzionale. Il mix lascia sempre udibili i segnali di aderenza e instabilità. Ogni registrazione o asset audio deve avere una provenienza e un permesso d’uso documentati.

## 15. Stack tecnico e architettura

### 15.1 Scelta proposta

**Godot 4, versione stabile fissata all’avvio dell’implementazione; Jolt per la fisica 3D; Blender per modelli e animazioni; QGIS per la base territoriale.** La versione esatta del motore e degli export template viene bloccata nel progetto, insieme alle istruzioni di compilazione/esportazione. Non si aggiorna durante una fase di calibrazione senza rieseguire i test principali.

Godot documenta l’integrazione di Jolt nel motore e le sue differenze rispetto al backend precedente [S6]. L’uso di Jolt non fornisce automaticamente il modello pneumatici o una Yaris pronta: quei comportamenti sono lavoro di progetto.

GDScript tipizzato per logica, UI, strumenti e prima implementazione fisica. Passare a codice nativo tramite GDExtension solo se il profiling dimostra un collo di bottiglia. Non introdurre un’estensione C++ preventivamente per quattro ruote e pochi corpi dinamici.

### 15.2 Componenti

| Componente | Responsabilità | Interfaccia principale |
| --- | --- | --- |
| Sessione | Stato del gioco, pausa, risultati e ripartenze | Eventi di inizio, incidente e arrivo |
| Input | Tastiera/gamepad, filtri e rimappatura | Comandi normalizzati e intenzioni del giocatore |
| Dinamica veicolo | Telaio, sospensioni, ruote, trazione e frenata | Stato fisico e telemetria per ruota |
| Struttura alta | Masse, flessione, coffa e vincoli | Stato relativo e reazioni sul telaio |
| Personaggi | Anatomia vincolata, postura, IK senza stiramento, sguardo e occhi espressivi | Accelerazioni fisiche e bersagli d’animazione |
| Esplorazione | Locomozione a quattro zampe, interazioni e compagna | Input a piedi, collisioni e percorso |
| Transizioni | Porte, pedane, scaletta, occupanti e trasferimento delle masse | Stati di sosta, discesa e risalita |
| Percorso | Geometria, materiali, checkpoint e settori | Progressione, contatto stradale e punti sicuri |
| Mondo | Terreno, edifici, vegetazione e caricamento settori | Visibilità e disponibilità delle collisioni |
| Camera | Inquadratura, ostacoli e comfort | Stato interpolato di veicolo e percorso |
| Audio/UI | Informazioni e feedback accessibile | Eventi della sessione e dati filtrati |
| Diagnostica | Registrazione, benchmark e riproduzione problemi | Input, stati fisici, versione e parametri |

La fisica produce i dati; animazioni e audio li consumano. UI e camera non alterano accidentalmente la simulazione. Proprietà di massa e aderenza si trovano in risorse versionate, non duplicate in vari script.

### 15.3 Organizzazione dei sorgenti

Cartelle previste: documentazione, sorgenti artistici, asset importati, scene del gioco, codice dei sistemi, dati di veicolo e percorso, strumenti, scenari di test, esportazioni e registri dei collaudi. I file Blender e i dati geografici trasformati rimangono disponibili; consegnare soltanto file importati renderebbe difficile correggere il gioco.

Per ogni asset: nome, autore/origine, licenza, scala, versione, numero di materiali, collisione e LOD. Per ogni modifica alla fisica: parametro precedente, nuovo valore e prova che ne motiva il cambiamento.

## 16. Prestazioni e caricamento

Obiettivo principale: 1080p a 60 fps sulla macchina di riferimento indicata nel contesto, Ryzen 7 5700X3D, RX 6800 e 32 GB RAM. È un target da misurare: non è una prestazione già ottenuta. Aggiungere preset ridotto e limitatore a 30/60/120 fps.

Budget iniziali indicativi: VRAM del gioco entro 6 GB e RAM entro 8 GB sul percorso completo; frame CPU e GPU con margine rispetto ai 16,7 ms di 60 fps. I budget si aggiornano dopo il primo settore rappresentativo, conservando i risultati misurati.

Usare istanze per vegetazione, LOD per auto e ambiente, texture condivise dove sensato, ombre selettive, occlusione e settori di mondo. Eseguire il profiling nel borgo, nei boschi e nelle viste lunghe: un solo test nel piazzale iniziale non è rappresentativo.

Il dettaglio visivo si può caricare per settori, mantenendo strada e collisioni utili sempre disponibili in anticipo. La distanza di precaricamento deriva da velocità massima e peggior tempo di caricamento misurato, con margine. Nessuna ruota deve incontrare una strada non ancora caricata; neppure la coffa deve urtare un edificio comparso all’ultimo istante.

Controllare giunti tra settori e transizioni LOD: il paesaggio può semplificarsi, la superficie fisica della strada non deve cambiare sotto le ruote.

## 17. Inventario artistico iniziale

Quantità indicative per stimare il lavoro; da rivedere dopo il settore campione.

| Famiglia | Contenuto proposto | Verifica |
| --- | --- | --- |
| Auto | Un modello esterno fedele, interno delle parti visibili, ruote e materiali | Confronti sui riferimenti MY 2022 |
| Struttura | Albero, collare, sostegni, coffa, bandiera e cesto | Silhouette, scala, movimento e collisioni |
| Protagonisti | Due modelli originali con rig, espressioni e abiti | Test di seduta, presa, equilibrio e ingombri |
| Edifici | Moduli generici per località secondarie; esterni specifici e documentati per Valle | A Valle prevalgono riscontri e rapporti reali, non un numero prefissato di case |
| Vegetazione | 5–7 famiglie fra alberi, arbusti ed erba con varianti | Profondità del bosco, leggibilità e costo |
| Strada | Profili, banchine, muri, parapetti e segnaletica | Percorribilità, raccordi e chiarezza |
| Dettagli | 20–35 oggetti riutilizzabili: vasi, panchine, cassette, cancelli e simili | Posizionamento intenzionale, senza rumore |
| Panorama | Terreno e masse distanti semplificate | Riconoscibilità della collina e della pianura |

Un edificio rappresentativo e un tratto di bosco devono raggiungere la qualità finale prima di produrre tutte le varianti. Lo stesso vale per la carrozzeria e il volto di un topolino.

## 18. Piano di sviluppo con condizioni di avanzamento

Non si passa a una fase costosa se la precedente non supera il suo controllo. Ogni fase deve produrre qualcosa di concreto e ispezionabile, preferibilmente una build eseguibile quando esiste già codice.

| Fase | Attività | Consegna | Condizione per avanzare |
| --- | --- | --- | --- |
| 0. Riferimenti e sopralluogo | Fissare la polilinea dell’anello degli allegati; osservare salita e discesa in Street View; raccogliere riferimenti visivi della Trend MY22 confermata | Mappa, diario dei tratti osservati e delle lacune, raccolta riferimenti e scheda decisioni | Sequenza dei tornanti verificata; nessuna lacuna nascosta; riferimenti sufficienti per strada e auto |
| 1. Laboratorio fisico | Piano, cerchio costante, rampa, dosso, frenata e masse alte primitive | Build con telemetria e parametri modificabili | Ribaltamento e recupero prodotti dalle forze, comportamento ripetibile entro tolleranze |
| 2. Anello provvisorio | Terreno semplice e circuito interamente percorribile | Giro completo, checkpoint, incidente e ripartenza | Partenza, giro e arrivo funzionano; nessun buco stradale |
| 3. Settore rappresentativo | Tratto di arrivo a Valle con curva, prato, accesso al borgo, Yaris, prolunghe e protagonisti | Campione con parcheggio e passaggio a piedi | Grafica, camera, anatomia, transizioni e guida convincenti insieme |
| 4. Borgo ed esplorazione | Ricostruire gli esterni documentati di Valle e collegarli al prato; locomozione, compagna, interazioni e salvataggi | Visita del paese completa | Andata/ritorno a piedi e rientro in auto senza blocchi; fedeltà verificata per elemento |
| 4b. Produzione circuito | Completare l’anello con priorità di dettaglio e fedeltà per zona | Circuito completo e coerente | Nessuna grande zona in stato di prototipo; Valle rimane il centro artistico |
| 5. Rifinitura | Audio, tutorial, UI, risultati, accessibilità e comfort | Versione candidata completa | Un nuovo giocatore capisce obiettivo e segnali; nessuna modifica urgente alla meccanica |
| 6. Collaudo e consegna | Test incrociati Linux/Windows, profiling, correzioni e packaging | Build finali, sorgenti e rapporto verifiche | Criteri della sezione 20 superati o limiti esplicitamente documentati |

La prima decisione importante dopo il laboratorio fisico è se la guida è divertente anche con una scatola al posto dell’auto. Il settore rappresentativo verifica poi se quella guida regge con camera, personaggi e ambiente definitivi.

## 19. Stima del lavoro e rischi di produzione

Stima orientativa, non preventivo o promessa. Presuppone una persona già competente in programmazione 3D e accesso a competenze artistiche adeguate; asset quasi tutti personalizzati.

| Blocco | Giornate/persona indicative |
| --- | ---: |
| Riferimenti, sopralluogo e specifiche del borgo | 10–20 |
| Laboratorio e dinamica principale | 10–20 |
| Anello provvisorio e regole complete | 10–15 |
| Settore rappresentativo, auto e protagonisti | 25–45 |
| Produzione del mondo con priorità su Valle | 25–45 |
| Esplorazione, transizioni e compagna | 20–35 |
| Rifinitura audio, UI, animazione e accessibilità | 10–20 |
| Collaudo, ottimizzazione e confezionamento | 15–25 |
| Totale iniziale | 125–225 |

Circa 25–45 settimane/persona a cinque giornate; con margine di rischio del 25–35%, ordine di grandezza **8–15 mesi a tempo pieno per una persona**, da ricalcolare dopo il settore campione. La visita a piedi aggiunge controller, animazioni, transizioni e verifiche. Le località più generiche riducono la produzione specifica lontano da Valle, ma non annullano quel lavoro aggiuntivo. È una stima di progetto, non un preventivo o una promessa. Competenze da acquisire e qualità artistica possono allungarla; strumenti IA non sostituiscono i collaudi.

Le voci più incerte sono qualità dei protagonisti, somiglianza dell’auto e stabilità del modello a masse mobili. Una bella schermata si può ottenere prima; non dimostra che un intero circuito sia finito o che la fisica funzioni.

## 20. Piano di verifica e criteri di accettazione

### 20.1 Prove fisiche

| Prova | Procedura | Criterio iniziale |
| --- | --- | --- |
| Equilibrio statico | Auto carica ferma su piano per 60 secondi | Nessuna deriva progressiva o vibrazione visibile; somma dei carichi vicina al peso entro il 2% |
| Ripartizione masse | Confrontare carichi ruota attesi e misurati | Scarti entro il 5% per il modello rigido iniziale; spiegare gli scarti successivi |
| Inclinazione lenta | Ruotare lentamente un piano con insieme inizialmente rigido | Soglia di scarico coerente con calcolo geometrico, tolleranza iniziale 10% |
| Curva costante | Aumentare velocità a piccoli passi su raggio noto | Crescita continua del carico esterno; nessun ribaltamento comandato da script |
| Slittamento | Ripetere con coefficienti di attrito differenti | La perdita di aderenza segue la taratura e non viene soppressa per far capovolgere l’auto |
| Confronto carico | Prova identica con e senza struttura | Differenze di stabilità e risposta chiaramente misurabili |
| Frenata e salita | Accelerare, frenare e fermarsi su diverse pendenze | Trasferimento longitudinale coerente; nessuna trazione da ruote sospese |
| Cambio di direzione | Manovra destra-sinistra progressiva | Inerzia e oscillazione visibili senza crescita numerica incontrollata |
| Smorzamento | Perturbare la struttura e rilasciare | Oscillazioni passive in attenuazione, nessuna autoeccitazione |
| Urti e caduta | Bordo, parapetto, fianco, tetto e coffa | Contatti leggibili, nessun attraversamento sistematico delle superfici |
| Passo fisico | Confrontare 60, 120 e 240 Hz su scenari campione | Convergenza; fra 120 e 240 Hz differenza della velocità di primo sollevamento indicativamente entro il 5% |
| Frame rate | Stesso scenario a 30, 60 e 144 fps di rendering | Nessuna variazione significativa attribuibile al rendering |

Le tolleranze sono soglie di sviluppo da affinare. Un fallimento del confronto fra passi fisici si risolve prima di finalizzare la difficoltà, non scegliendo la frequenza che produce la scena più spettacolare.

### 20.2 Personaggi e camera

Verificare fermo, accelerazione, frenata, curve a destra/sinistra, inversioni e incidente. Mani e piedi devono restare sugli appoggi previsti; il corpo non attraversa abitacolo o parapetto; lo sguardo non scatta; abiti e code non esplodono numericamente. Gli spostamenti corporei fisicamente importanti devono corrispondere alle masse simulate.

Controllare visibilità della strada con tutti gli angoli di sterzo e rollio ordinari, passaggi fra case e tratti boscosi. Il palo non deve occupare a lungo la direzione di marcia. Ridurre le oscillazioni della camera deve modificare il comfort, non la fisica del veicolo.

### 20.3 Percorso e regole

Percorrere ogni segmento in entrambi i sensi per individuare bordi, giunti e collisioni; il giro ufficiale resta nella direzione prescelta. Verificare ogni banchina, punto sicuro, checkpoint e collegamento fra settori. Confrontare il percorso con il diario di sopralluogo: tutti i tornanti censiti devono essere presenti nell’ordine corretto, e ogni variazione deve essere documentata. Una lacuna Street View non diventa automaticamente una curva inventata e presentata come reale.

Provare: traguardo anticipato, passaggio inverso, salto di checkpoint, scorciatoia, ritorno su un settore, reset vicino all’arrivo, pausa durante incidente e completamento mentre si stanno ancora elaborando i contatti. Il risultato deve essere assegnato una sola volta e soltanto a un giro valido.

### 20.4 Prestazioni e piattaforme

Misurare nella build esportata, dopo riscaldamento, su un giro intero e su scene peggiori ripetute. Registrare hardware, OS, driver, risoluzione, preset, versione motore e parametri fisici. Obiettivo iniziale sulla macchina di riferimento: frame time al 95° percentile entro 20 ms, al 99° entro 33,3 ms e media almeno 60 fps a 1080p nel preset concordato; documentare stalli isolati e caricamenti.

Eseguire almeno tre giri consecutivi senza crescita anomala della memoria. Verificare avvio a rete disconnessa, assenza di dipendenze di sviluppo sul PC destinatario, input, audio, cambio risoluzione e salvataggio impostazioni. I test Linux e Windows devono avvenire su sistemi reali o ambienti effettivamente capaci di eseguire e visualizzare la build: esportare un file non equivale a collaudarlo.

### 20.5 Verifica del piacere di gioco

Almeno cinque prove con persone che non conoscano i dettagli della fisica, se disponibili. Raccogliere dove perdono il controllo e come interpretano i segnali, senza guidarli verbalmente in ogni curva. Target iniziale da valutare: capire causa del primo incidente, migliorare nei tentativi successivi e poter completare un settore grazie a frenate e sterzate migliori.

Una difficoltà che provoca incidenti incomprensibili si corregge anche se il simulatore è numericamente stabile. Una guida troppo facile a passo d’uomo non è un bug: la modalità a tempo serve a introdurre il rischio volontario.

## 21. Strumenti per diagnosi e manutenzione

Pannello sviluppatore disattivato nell’esperienza normale: baricentro, assi di inerzia, carichi e forze ruota, compressioni, contatti, rollio, posizione del gruppo alto e costo dei sistemi. Un comando permette di ripetere la stessa prova di laboratorio senza attraversare ogni volta il circuito.

Registrare input con timestamp e campioni dello stato fisico per riprodurre i problemi. Non presumere determinismo perfetto fra OS, hardware o versioni del motore. Per rivedere esattamente un incidente, usare stati registrati/interpolati; un semplice replay degli input può divergere e va usato con tolleranze diagnostiche.

Gli scenari fisici, i checkpoint e il reset meritano test automatici perché una regressione comprometterebbe il gioco. La somiglianza della Yaris, il comfort della camera e l’espressività richiedono invece immagini, video e prove umane; un test che controlla soltanto la presenza dei nodi non verifica la qualità.

## 22. Rischi e risposte previste

| Rischio | Conseguenza | Risposta |
| --- | --- | --- |
| Struttura alta bella ma quasi priva di massa | Auto troppo stabile, obiettivo senza senso | Calcolare massa e inerzia prima di rifinire gli asset |
| Carico troppo estremo | Si ribalta anche guidando con prudenza | Variare masse/quote documentate e geometria delle curve; verificare percorribilità |
| Slitta sempre prima di inclinarsi | Non emerge la meccanica richiesta | Confrontare grip e soglia di ribaltamento; correggere configurazione fisica senza trucchi |
| Vincoli rigidi o mass ratio problematici | Vibrazioni e instabilità numerica | Ridurre gradi di libertà, verificare timestep, masse e smorzamento |
| Topolina animata ma fisicamente irrilevante | Movimento e dinamica si contraddicono | Collegare gli spostamenti importanti al modello dinamico |
| Modello auto generico | Perdita del requisito di fedeltà | Confronti sistematici con la Yaris e l’allestimento corretto |
| Circuito compresso male | Curve innaturali, velocità poco plausibili | Compressione selettiva, ricostruzione dei raccordi e prove con auto definitiva |
| Troppo dettaglio uniforme | Costi e prestazioni fuori controllo | Priorità alle zone vicine e ai punti panoramici |
| Camera sempre altissima | Auto piccola e strada poco leggibile | Composizione a tre quarti e studio dell’ingombro verticale |
| Fallimento per ostacoli invisibili in alto | Frustrazione e perdita di fiducia | Verificare il volume percorso da coffa e topolina; rimuovere collisioni decorative |

## 23. Consegna finale prevista

Due build giocabili, Linux e Windows, con comandi e istruzioni di avvio; progetto Godot completo; sorgenti artistici originali; risorse e script per rigenerare strada e terreno; registro di provenienza dei dati e delle licenze; documentazione breve per modificare masse, percorso e difficoltà; rapporto dei test con prestazioni misurate e limiti residui.

Prima di definire una build “completa”, devono esserci almeno un giro valido dimostrato, un ribaltamento fisicamente generato, un recupero da instabilità, entrambe le piattaforme collaudate e immagini/video che documentino qualità di auto, personaggi e ambiente. Nessun segnaposto importante deve essere presentato come asset finale.

Il primo prodotto intermedio da costruire è il laboratorio fisico. La prima verifica artistica è un’immagine in gioco della Yaris con i due topolini e la coffa; la prima verifica complessiva è il settore rappresentativo. Sono tre prove diverse e tutte necessarie.

## 24. Informazioni ancora utili

1. Punto preciso del prato: PV-01 è un candidato osservato, da confermare rispetto alla zona intesa dall’utente. Si può proseguire con un’area provvisoria senza dichiararla definitiva.
2. Colori del pelo, abiti e nomi restano personalizzabili; anatomia naturale e occhi grandi sono già vincolanti.
3. Il verso di lavoro proposto è Faedis → Campeglio → Valle → ritorno a Faedis. La preferenza opposta cambierebbe camera e tutorial, senza richiedere un nuovo anello.

Località, anello, Trend senza optional, anatomia, occhi grandi, priorità di fedeltà ed esplorazione sono già chiariti. Le scelte aperte non impediscono laboratorio fisico e strumenti. La visita a Valle è una tappa della gita; il ritorno preserva l’obiettivo originario del giro completo.

## 25. Fonti consultate

Ricerche effettuate il 18 ottobre 2026. Le fonti fondano i riferimenti geografici e tecnici; non costituiscono un’approvazione delle scelte creative o dei valori ipotizzati nel progetto.

Aggiornamento del 19 ottobre 2026: osservati i nuovi allegati, ripreso Street View, consultate fotografie originali e documentazione dei controller a piedi. I riscontri del borgo sono ancora parziali.

- **[S1] Comune di Faedis — cartina informativa, distribuita sul portale turistico locale.** Località e disposizione territoriale; avvertenza di uso indicativo. [PDF](https://faedisnicefaedisgood.com/wp-content/uploads/2023/03/cartina_comune_faedis.pdf).
- **[S2] Regione Autonoma FVG — catalogo IRDAT, dataset 11826.** Metadati dei modelli altimetrici a passo 0,50 m da rilievi LiDAR 2017–2020. Metadati reperiti nella ricerca; apertura diretta del catalogo non riuscita durante questa sessione. Download e copertura ancora da verificare. [Catalogo](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826). [Informazioni regionali sui formati](https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA4/FOGLIA5/).
- **[S3] Toyota Europe — The all-new Toyota Yaris, 27 luglio 2020.** Identità della quarta generazione europea e sistema ibrido da 116 CV. [Comunicazione ufficiale](https://newsroom.toyota.eu/the-all-new-toyota-yaris/).
- **[S4] Toyota Europe — Yaris GR SPORT specifications.** Riferimento ufficiale per ingombri e passo della carrozzeria; non determina l’allestimento richiesto. [Scheda PDF](https://newsroom.toyota.eu/download/1112913/2021202-spec-sheet-yaris-gr-sport-v3-final.pdf).
- **[S5] Godot — VehicleBody3D.** Limiti dichiarati del componente automobilistico standard. [Documentazione](https://docs.godotengine.org/en/stable/classes/class_vehiclebody3d.html).
- **[S6] Godot — Using Jolt Physics.** Integrazione, configurazione e differenze dei vincoli. [Documentazione](https://docs.godotengine.org/en/stable/tutorials/physics/using_jolt_physics.html).
- **[S7] Godot — RigidBody3D.** Corpo dinamico, forze, massa, baricentro, inerzia e collisioni. [Documentazione](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html).
- **[S8] Godot — Physics interpolation introduction.** Distinzione fra aggiornamento fisico e visualizzazione interpolata. Il valore proposto di 120 Hz è una scelta da collaudare. [Documentazione](https://docs.godotengine.org/en/stable/tutorials/physics/interpolation/physics_interpolation_introduction.html).
- **[S9] NHTSA — Crash Prevention Effectiveness of Light-Vehicle Electronic Stability Control, DOT HS 811 486, giugno 2011, appendice.** Definizione del fattore statico di stabilità. [Rapporto ufficiale PDF](https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/811486).
- **[S10] OpenStreetMap Foundation — Copyright and License.** Attribuzione e condizioni dei dati OSM. [Indicazioni ufficiali](https://www.openstreetmap.org/copyright).
- **[S14] Allegati dell’utente IMG_8548.webp e IMG_8549.png.** Primo riferimento per anatomia, secondo per occhi ingranditi; entrambi aperti e osservati. Nessuna identificazione di specie zoologica dedotta dalla sola foto.
- **[S15] Google Street View, via Prestento, sessione del 19 ottobre 2026.** Osservazione diretta di prato e strada sul lato occidentale di Valle. Il prato PV-01 è un candidato di progetto; data delle immagini esposta marzo 2026. Non attestati confini catastali, misure o uso pubblico del terreno.
- **[S16] YukioSanjo, Faedis – Valle – Chiesa 1, 7 ottobre 2020, CC BY-SA 4.0.** Foto originale osservata; facciata e rapporto con l’edificio adiacente. [Pagina del file](https://commons.wikimedia.org/wiki/File:Faedis_-_Valle_-_Chiesa_1.jpg).
- **[S17] YukioSanjo, Faedis – Valle – Chiesa – 2, 7 ottobre 2020, CC BY-SA 4.0.** Foto originale osservata; campanile, orologio e rapporto con la chiesa. [Pagina del file](https://commons.wikimedia.org/wiki/File:Faedis_-_Valle_-_Chiesa_-_2.jpg).
- **[S18] iw3rua, PANORAMA DI VALLE (2), 29 agosto 2008, CC BY-SA 3.0.** Foto originale osservata; facciata, spazio pavimentato e passaggio laterale in salita. [Pagina del file](https://commons.wikimedia.org/wiki/File:PANORAMA_DI_VALLE_-_panoramio_-_iw3rua_(2).jpg).
- **[S19] iw3rua, PANORAMA DI VALLE, 29 agosto 2008, CC BY-SA 3.0.** Foto originale osservata; campanile e copertura. [Pagina del file](https://commons.wikimedia.org/wiki/File:PANORAMA_DI_VALLE_-_panoramio_-_iw3rua.jpg).
- **[S20] Godot, CharacterBody3D.** Controller mosso da script e strumenti di collisione con pavimenti e pareti. [Documentazione](https://docs.godotengine.org/en/stable/classes/class_characterbody3d.html).
- **[S21] Godot, NavigationAgent3D.** Strumenti di navigazione per la compagna, da integrare con il controller di movimento. [Documentazione](https://docs.godotengine.org/en/stable/classes/class_navigationagent3d.html).
- **[S22] Google Street View, nucleo di Valle davanti alla chiesa, maggio 2023.** Panorami osservati intorno a 46.15684 N, 13.39302 E e 46.15690 N, 13.39311 E; piazzetta, facciate e terrazza. [Panorama verificato](https://www.google.com/maps/@46.1568367,13.3930177,679a,90y,90t/data=!3m7!1e1!3m5!1sn8n8zO3EQEP5lL15-mlSgg!2e0!6shttps:%2F%2Fstreetviewpixels-pa.clients6.google.com%2Fv1%2Fthumbnail%3Fcb_client%3Dmaps_sv.tactile%26w%3D900%26h%3D600%26pitch%3D0%26panoid%3Dn8n8zO3EQEP5lL15-mlSgg%26yaw%3D0!7i16384!8i8192?entry=ttu&g_ep=EgoyMDI2MTAxNC4wIKXMDSoASAFQAw%3D%3D).
- **[S13] Toyota Italia — Nuova Yaris MY22, Scheda Equipaggiamento, due pagine.** Dotazioni e colore della Hybrid Trend, verificati nella colonna corretta. [Scheda ufficiale PDF](https://www.toyota.it/content/dam/toyota/nmsc/italy/gamma/pdf/scheda-equipaggiamenti/YARIS_Scheda_equipaggiamento.pdf).
- **[S11] Allegati dell’utente IMG_8546.png e IMG_8547.png.** Osservazione diretta delle schermate: anello Valle di Soffumbergo–Faedis–Campeglio–Valle di Soffumbergo, circa 20 km e 39 minuti indicati dall’app. Valori della schermata, non misure indipendenti.
- **[S12] Google Maps / Google Street View — 77 via Prestento, Valle di Soffumbergo.** Osservazione diretta nel browser, immagini indicate come marzo 2026, limitata a pochi panorami ravvicinati. Non costituisce sopralluogo completo. [Panorama osservato](https://www.google.com/maps/place/Valle+di+Soffumbergo/@46.1565263,13.3918772,662a,75y,318.54h,90t/data=!3m7!1e1!3m5!1sNdSAY6ayhYwdMSruFTvA0Q!2e0!6shttps:%2F%2Fstreetviewpixels-pa.clients6.google.com%2Fv1%2Fthumbnail%3Fcb_client%3Dmaps_sv.tactile%26w%3D900%26h%3D600%26pitch%3D0%26panoid%3DNdSAY6ayhYwdMSruFTvA0Q%26yaw%3D318.53864278132727!7i16384!8i8192!4m6!3m5!1s0x477a4f2898865b99:0x2a4a5f41079f4b68!8m2!3d46.1569175!4d13.3928985!16s%2Fg%2F11c1x1yk_q?entry=ttu&g_ep=EgoyMDI2MTAxNC4wIKXMDSoASAFQAw%3D%3D).

