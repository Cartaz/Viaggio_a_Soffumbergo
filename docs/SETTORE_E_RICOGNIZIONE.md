# Settore E — discesa Costalunga / Mont Joanes / Canal di Grivò

**Scheda tecnica provvisoria — 20 ottobre 2026. La mappatura visiva completa non è stata eseguita.**

Fonte vincolante: [CIRCUITO_SOPRALLUOGO.md](CIRCUITO_SOPRALLUOGO.md), ricognizione del 19/10/2026. Il settore E non passa da via Monte Piccat (settori V e D). L'ordine qui documentato deriva dal **link originale del percorso** fornito dall'utente e non dalle ipotesi precedenti.

## Percorso e confini

| Passaggio Maps | Tratto in direzione del gioco | Distanza indicata da Maps il 19/10 |
|---|---|---|
| 16 | Dalla strada per Valle, continua su **strada per Costalunga** | circa **4,2 km** |
| 17 | Continua su **via Mont Joanes** | circa **350 m** |
| 18 | Destra verso il segnaposto **Canal di Grivò** | circa **13 m** |

Valore ottenuto sommando gli arrotondamenti dell'app: **4.563 m**, non misura GIS certificata. Il ritorno dal segnaposto (passaggio 19) e la svolta successiva (passaggio 20) sono **settore F**. La deviazione di 13 m di Maps e la sua inversione non sono tornanti della collina.

La dicitura **via Juretigh** visibile nella mini-mappa del nodo 17 deve essere riconciliata con cartografia e segnaletica; non viene trattata automaticamente come un altro tratto o una diramazione.

## Evidenza osservata nella precedente ricognizione

I tre panorami del dossier sono **osservazioni del 19 ottobre**, non una nuova navigazione Street View eseguita in questa consegna. Coordinate WGS84 del punto di vista, non misure della strada. I link completi sono conservati nei singoli elementi di [sector_e_anchors.geojson](../data/geography/sector_e_anchors.geojson).

| ID e passaggio | Panorama e data immagine | Osservato nel dossier | Limite |
|---|---|---|---|
| [CIR-12](https://www.google.com/maps/@?api=1&map_action=pano&pano=PxnOlMmQDxYQPw0_-VBuEg&viewpoint=46.1580732%2C13.379205&heading=295.07&pitch=0), 16 | 46.1580732 N, 13.3792050 E; **maggio 2023** | Bivio nel bosco, parete/muro in pietra, margini erbosi, asfalto senza mezzeria, piccolo contenitore presso il bivio | L'oggetto mobile non è un elemento architettonico permanente; 4,2 km interni non visitati |
| [CIR-13](https://www.google.com/maps/@?api=1&map_action=pano&pano=nKp_t4HfrINTwSQXEBpzvQ&viewpoint=46.1676159%2C13.3623302&heading=287.48&pitch=0), 17 | 46.1676159 N, 13.3623302 E; **agosto 2024** | Avvicinamento a STOP, guardrail a destra, pendio vegetato a sinistra, edifici e protezioni di pietra | Denominazione Juretigh da accertare; mancano dimensioni |
| [CIR-14](https://www.google.com/maps/@?api=1&map_action=pano&pano=zSGMyb-MOznlSdQY-vlV_g&viewpoint=46.1659437%2C13.3596292&heading=225.6&pitch=0), 18 | 46.1659437 N, 13.3596292 E; **agosto 2024** | Attraversamento con parapetti metallici su pilastrini, edificio in pietra a sinistra, cavi aerei | Va controllato l'ingombro per l'albero e la coffa, senza stimare altezze dall'immagine |

## Segmenti di lavoro e lacune esplicite

| Tratto | Evidenza oggi disponibile | Intervallo ancora da rilevare |
|---|---|---|
| E16, Costalunga | Nodo iniziale CIR-12 e nodo finale CIR-13, istruzione Google Maps | **Circa 4,2 km**: sequenza reale di curve, tornanti, raccordi, accessi, larghezze, visibilità, scarpate, eventuali parapetti |
| E17, Mont Joanes | Nodo CIR-13 e nodo CIR-14, svolta Maps | **Circa 350 m**: verificare tutti i panorami intermedi, continuità e nome Juretigh |
| E18, Canal | Nodo CIR-14 e segnaposto di destinazione nel link originale | **Circa 13 m**: forma effettiva dell'innesto e ritorno verso F |
| Confine D/E | Nodo CIR-12 | Congiunzione geometrica e ricognizione continua del ramo D |
| Confine E/F | Nodo CIR-14 | Manovra del segnaposto e distinzione fra passaggi 18 e 19 |

**Nessuna curva T-### è stata numerata.** La ricognizione dei nodi non consente un elenco attendibile di tornanti; nessuna progressiva geometrica, quota, larghezza, pendenza, raggio o sopraelevazione può essere dedotta dai 3 punti isolati. Non è corretto misurare copertura in chilometri o dichiarare chiuso il settore.

### Protocollo di completamento

1. Percorrere in Street View, in direzione effettiva **CIR-12 → CIR-13 → CIR-14**, l'intero settore, registrando ogni panorama e le interruzioni. Attenzione a diramazioni, STOP, accessi e cambi di anno delle riprese.
2. Per ogni tornante realmente verificato registrare ingresso, apice, uscita, direzione, orientamenti e punti di occlusione; solo dopo assegnare un ID T-### stabile. Documentare barriere, fossi, vegetazione, guardrail, muri e spazi di manovra.
3. Verificare con attenzione cavi e rami in quota, guardrail, eventuali ponti e restringimenti per l'insieme **Yaris + albero maestro + coffa**; l'altezza libera va misurata con altra fonte o in situ.
4. Acquisire una **polilinea stradale indipendente**, per esempio OSM/CTRN, e confrontarla col percorso scelto senza ricopiarla dai pixel Google; conservare la provenienza e la licenza ODbL.
5. Acquisire tessere di terreno del [DTM regionale LiDAR 2017–2020](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826), verificando tessera, datum verticale, copertura e corretto allineamento con la strada. Non confondere quote ortometriche con WGS84 ellissoidale.
6. Solo a questo punto preparare una superficie provvisoria in Godot, verificare collisioni e percorribilità, quindi confrontare il comportamento fisico con le pendenze reali.

## Giocabilità — proposte, non dati osservati

La sezione E deve esercitare frenata prima della curva, trasferimento di carico longitudinale, inversione del rollio nelle curve concatenate e percezione del peso della passeggera in coffa. Non introdurre limiti di velocità, raggi di curva o ribaltamenti pilotati non dedotti dal contesto verificato. Confrontare l'ordine dei tornanti nella futura scena con la ricognizione, lasciando Faedis e i raccordi secondari stilizzabili e riservando la massima fedeltà a Valle.

## Provenienza e stato

- **Documento di partenza:** CIRCUITO_SOPRALLUOGO.md, sessione 19/10/2026; tre panorami E e 24 istruzioni originali.
- **Geometria qui prodotta:** soltanto 3 coordinate di viewpoint, nel GeoJSON di punti; nessuna LineString stradale.
- **OSM:** [© OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright); l'estratto preesistente nella repository è circoscritto al borgo, non copre in modo verificato E.
- **Fonte altimetrica futura:** [Regione FVG, basi cartografiche e DTM](https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA4/), catalogo controllato; **nessuna tessera scaricata** in questa lavorazione.
- **Verifiche di codice:** generatore tools/build_sector_e.py, test tests/test_sector_e.py e controllo di coerenza con il Markdown.
- **Stato effettivo:** ancore ed elenco lacune documentati; **rilievo continuo NON completato**, terreno e pista NON modellati, nessun collaudo Godot/Blender e nessuna sincronizzazione verificata con il PC Windows.

Eseguire: python tools/build_sector_e.py --check e python tools/check_project.py. I test statici non certificano sopralluogo né fisica in Godot.
