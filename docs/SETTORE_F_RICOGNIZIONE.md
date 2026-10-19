# Settore F — Canal di Grivò → Borgo Scubla → Faedis

**Ricognizione strutturata: 20 ottobre 2026. Copertura *non continua*; mappatura integrale ancora aperta.**

## Riferimento vincolante

Il tracciato segue il file del progetto ChatGPT `CIRCUITO_SOPRALLUOGO.md` (ricognizione del 19 ottobre 2026, sequenza originale 19–24), non un nuovo itinerario ottimizzato. [Apri il circuito originale in Google Maps](https://www.google.com/maps/dir/Bar+Al+Telefono,+Piazza+I+Maggio,+23,+33040+Faedis+UD/Campeglio,+33040+UD/Festa+delle+Castagne+e+del+Miele+di+Castagno,+Piazza+A.Clementig,+1,+33040+Valle+UD/Canal+di+Griv%C3%B2,+33040+UD/Bar+Al+Telefono,+Piazza+I+Maggio,+23,+33040+Faedis+UD/). L'andata/ritorno di **13 m** al segnaposto Canal di Grivò resta incluso; non viene trasformato in un tornante. La destinazione finale è **Bar Al Telefono, Piazza I Maggio 23, Faedis**.

| Passaggio | Direzione come da Maps | Distanza indicata |
| --- | --- | ---: |
| 19 | Riparti dal segnaposto Canal di Grivò verso via Mont Joanes | 13 m |
| 20 | Tutto a destra su via Mont Joanes | 350 m |
| 21 | Leggermente a sinistra in Borgo Scubla | 650 m |
| 22 | Continua su via dei Castelli | 850 m |
| 23 | Sinistra, ingresso Bar Al Telefono | 9 m |
| 24 | Arrivo Bar Al Telefono | — |

**Totale delle distanze arrotondate delle istruzioni: 1.872 m.** È una somma di valori presentati dall'app, *non* una misura metrica certificata del segmento. Non usare tale somma per forzare la lunghezza della spline. La tappa originale di Canal di Grivò è un segnaposto, non una posizione di rilievo dell'asse stradale.

## Punti cartografici con provenienza

La raccolta GeoJSON è `data/geography/settore_f_ancore.geojson`. Le coordinate sono **lon, lat WGS84 senza quota**. Tre punti provengono da panorami descritti il 19 ottobre, due sono segnaposto Google Maps: non sono nuovi sopralluoghi visivi né punti metricamente rilevati.

| ID | Latitudine N | Longitudine E | Riscontro documentato e limiti |
| --- | ---: | ---: | --- |
| F-00 | 46.1657647 | 13.3592542 | Segnaposto Canal di Grivò, proveniente dal link dell'utente; imbocco carrabile non accertato. |
| CIR-17 | 46.1632064 | 13.3578603 | [Panorama 2024-08](https://www.google.com/maps/@?api=1&map_action=pano&pano=LSR3L4NSfxs4O_60YjAl0w&viewpoint=46.1632064%2C13.3578603&heading=233.93&pitch=0): via Mont Joanes / Borgo Scubla, STOP, riga d'arresto, muri, giardini e case; larghezze non note. |
| CIR-18 | 46.1588268 | 13.3528119 | [Panorama 2024-08](https://www.google.com/maps/@?api=1&map_action=pano&pano=13wcbhtdW3YwbDG8paz2fg&viewpoint=46.1588268%2C13.3528119&heading=225.99&pitch=0): Borgo Scubla verso via dei Castelli, asfalto senza mezzeria, recinzione e muro a destra, accesso secondario a sinistra. |
| CIR-19 | 46.1527672 | 13.3461990 | [Panorama 2022-07](https://www.google.com/maps/@?api=1&map_action=pano&pano=A7-gKW2wYZwHHMCg9VZUfg&viewpoint=46.1527672%2C13.346199&heading=223.84&pitch=0): rientro a Faedis, ambiente urbano, marciapiedi e chiesa visibile nell'orientamento osservato; SR356/SP15 da risolvere. |
| F-ARRIVO | 46.1527301 | 13.3465502 | Segnaposto Bar Al Telefono, non attestazione del punto fisico di ingresso carrabile. |

Il [panorama CIR-14](https://www.google.com/maps/@?api=1&map_action=pano&pano=zSGMyb-MOznlSdQY-vlV_g&viewpoint=46.1659437%2C13.3596292&heading=225.6&pitch=0) (passaggio 18, **settore E**, agosto 2024) offre contesto al confine: attraversamento con parapetti metallici su pilastrini, edificio in pietra e cavi aerei. Non è contato come nuova osservazione del settore F.

**Controllo di coerenza all'arrivo:** la distanza geodetica diretta fra CIR-19 e il segnaposto del bar è dell'ordine di **27 m**, mentre l'ultima manovra visualizzata dall'app è **9 m**. Non è una contraddizione risolta: il panorama è un riferimento urbano e può non coincidere con il punto esatto d'inizio dell'ingresso. Non posizionare la curva d'accesso basandosi su CIR-19.

## Fonti indipendenti e denominazioni

- [Comune di Faedis, stradario comunale](https://faedisnicefaedisgood.com/wp-content/uploads/2023/03/stradario_comune_faedis.pdf): elenca Borgo Scubla e via dei Castelli a Faedis; usa **via Mont Joannes** per Canal di Grivò, mentre Maps nel dossier scrive **via Mont Joanes**. Mantenere il nome originale del percorso come etichetta di navigazione e registrare la variante toponomastica, senza fingere risoluzione catastale.
- [Openalfa, Borgo Scubla](https://italy-streets.openalfa.com/streets/borgo-scubla-borgo-canal-del-ferro-faedis): restituisce tag OSM `tertiary`, `lanes=2`, `surface=asphalt` per l'entità catalogata; **non** usarli per dedurre una mezzeria o una larghezza uniforme: CIR-18 documenta visivamente l'assenza di mezzeria in un punto.
- [Openalfa, via dei Castelli](https://vie.openalfa.it/vie/via-dei-castelli-borgo-san-pietro-faedis): attribuisce alla via la categoria OSM residenziale; è un indizio di classificazione, non un collaudo di percorribilità.
- [Regione FVG, catalogo geografico IRDAT](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/home?language=it): offre dataset e servizi geografici da verificare e scaricare per ricostruire l'asse. La presenza del catalogo **non** significa che il grafo stradale sia già stato acquisito.
- [Attribuzione e termini OpenStreetMap](https://www.openstreetmap.org/copyright). Nessuna geometria OSM del settore F è stata importata in questa consegna; i soli riferimenti Street View sono link e note, non immagini o geometrie derivate.

## Ricostruzione artistica subordinata alle verifiche

1. **F0 — rientro dal segnaposto Canal di Grivò.** Riprodurre il breve raccordo soltanto dopo aver individuato la carreggiata e la posizione reale di manovra. Cavi aerei e parapetti di CIR-14 sono indizi al confine col settore E, non ingombri misurati.
2. **F1 — via Mont Joanes / Borgo Scubla.** Al punto CIR-17 usare come riferimento visivo STOP, muretti, giardini, case. Controllare ogni intersezione e la direzione del giro, specialmente il ritorno verso Faedis.
3. **F2 — Borgo Scubla.** In CIR-18 contesto con case, muro e recinzione, carreggiata priva di mezzeria. Le sezioni intermedie fra CIR-17 e CIR-18 non sono state osservate continuamente.
4. **F3 — via dei Castelli / Faedis.** Collegamento dall'ultimo nodo di Borgo Scubla al panorama CIR-19 ancora da ricostruire. Segnaletica, margini e allineamento urbano da riconciliare con cartografia riutilizzabile.
5. **F4 — ingresso al bar.** Ingresso di 9 m da Maps non ubicato con certezza al panorama; verificare accesso, attraversamenti, spazio per Yaris e coffa, parcheggio e linea del checkpoint finale.

## Requisiti prima di dire «settore F completo»

- [x] Sequenza originale 19–24 conservata senza tagliare i 13 m di segnaposto.
- [x] Tre panorami precedentemente descritti collegati con date, coordinate e limiti.
- [x] Segnaposti iniziale/finale registrati senza spacciarli per centri della strada.
- [x] Scheda dei nomi alternativi e provenienza delle fonti.
- [ ] Seguimento Street View *continuo* per ogni intervallo e registrazione dei vuoti.
- [ ] Inventario di **ogni curva** con ingresso/apice/uscita; nessun ID T-### o numero di tornanti inventato.
- [ ] Grafo stradale o asse vettoriale lecitamente riutilizzabile, con identità dei way/edge e confronto di topologia con Google Maps.
- [ ] Quote, datum verticale, pendenze, raggi e larghezze basati su dati appropriati.
- [ ] Rilievo di ponti, bordi e **altezza libera per albero/coffa**.
- [ ] Risoluzione dell'ingresso finale e prova di percorrenza in Godot.

**Divieto tecnico:** questi cinque punti sono un indice di ancore; non unire con segmenti rettilinei per creare una strada percorribile e non passarli a `tools/prepare_route.py`, che richiede una LineString quotata e verificata. Le coordinate Google dei panorami servono a ritrovare osservazioni, non sono una sorgente cartografica da ricalcare.

## Consegnato / non consegnato

Dati in `data/geography/settore_f_passaggi.json` e `data/geography/settore_f_ancore.geojson`, controlli di integrità in `tests/test_circuito_f.py`. **Non** sono state eseguite nuove osservazioni in Street View, non è stato ottenuto un grafo metrico, non è stata generata una mesh e non è stato effettuato un collaudo Godot/Blender del settore F. Il file originale `CIRCUITO_SOPRALLUOGO.md` è nei file del progetto ChatGPT e va mantenuto accessibile alle sessioni successive. Il repository locale Windows deve recepire i commit prima di essere dichiarato sincronizzato.
