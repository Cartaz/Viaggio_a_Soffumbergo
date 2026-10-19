# Settore D — Strada per Valle (discesa dopo il borgo)

**Aggiornamento 20 ottobre 2026.** Mappatura preparatoria **parziale e verificabile**. Questo documento si basa ora sul file `CIRCUITO_SOPRALLUOGO.md` allegato al progetto ChatGPT, sessione 19/10/2026. Corregge l'attribuzione precedente: il "Borgo alto", la chiesa, il campanile e Piazza Clemencig sono prioritariamente settore **V**, **non D**. Il dossier sbagliato è stato eliminato dal ramo di lavoro.

## 1. Identità esatta nel circuito originale

| Dato | Valore / fonte |
| --- | --- |
| Settore | **D — Bivio Monte Piccat → strada per Valle** |
| Senso di percorrenza | **Dal ritorno dalla piazza verso ovest, in direzione Costalunga** |
| Passaggio del link originale | **15: «Leggermente a sinistra in strada per Valle»** |
| Lunghezza riportata da Maps | **1,4 km**, cifra arrotondata dell'app, **non** rilievo metrico |
| Inizio | Bivio via Monte Piccat / Strada per Valle, vicino a `CIR-VAL-15` |
| Fine | Innesto Strada per Valle / Strada per Costalunga, vicino a `CIR-12` |
| Settore precedente | **V**: via Monte Piccat → piazza → ritorno al bivio (passaggi 11–14) |
| Settore seguente | **E**: continua su Strada per Costalunga, 4,2 km prima del successivo passaggio (n. 16) |
| Giro complessivo | Da/verso Bar Al Telefono, Faedis, attraverso Campeglio, Valle e Canal di Grivò; riferimento utente **18,7 km / 36 minuti / 24 passaggi** nella sessione Maps del 19/10/2026 |

**Nota di confine:** la posizione geografica dei panorami è un punto di osservazione *vicino* all'innesto, non il rilievo degli assi stradali. I 1,4 km non possono essere suddivisi in progressive affidabili senza polilinea verificata. Nessuna curva interna è già osservata nel file sorgente.

## 2. Panorami già registrati nel file originale

| ID | Funzione per D | Data immagini | Vista e informazioni effettivamente annotate |
| --- | --- | --- | --- |
| [CIR-11](https://www.google.com/maps/@?api=1&map_action=pano&pano=VG6N0zxqJ7PLJ6BbJX5OWA&viewpoint=46.1588292%2C13.3922833&heading=2.49&pitch=0) | Contesto al bivio, **prima** del passaggio per V | marzo 2026 | Bivio, ringhiera su pilastrini di cemento a sinistra, muretto a destra, segnali direzionali. Nel giro originale si va prima in V. |
| [CIR-VAL-15](https://www.google.com/maps/@?api=1&map_action=pano&pano=KAzz8xQ3_0RkMdu4rPLCNA&viewpoint=46.1588137%2C13.3926044&heading=321.61&pitch=0) | **Inizio D** (passaggio 15) | maggio 2023 | Incrocio asfaltato ai margini del bosco, banchine erbose, segnale blu e apertura sulla Strada per Valle. |
| [CIR-12](https://www.google.com/maps/@?api=1&map_action=pano&pano=PxnOlMmQDxYQPw0_-VBuEg&viewpoint=46.1580732%2C13.379205&heading=295.07&pitch=0) | **Fine D / inizio E** (passaggio 16) | maggio 2023 | Bivio nel bosco, parete/muro in pietra presso la diramazione, margini erbosi, asfalto senza mezzeria; piccolo contenitore di permanenza incerta. |

Dati WGS84 dei riferimenti `[lon, lat]`:
- `CIR-11` = `[13.3922833, 46.1588292]`, direzione panorama 2,49°;
- `CIR-VAL-15` = `[13.3926044, 46.1588137]`, direzione panorama 321,61°;
- `CIR-12` = `[13.379205, 46.1580732]`, direzione panorama 295,07°.

Le date sono quelle delle **riprese Street View** nel documento del 19/10/2026, non date del rilievo attuale. Un'anteprima fotografica non autorizza a estrapolare dettagli lungo gli intervalli non visti. Le due estremità **non** dimostrano copertura continua e non permettono di contare i tornanti o misurare la geometria.

## 3. Suddivisione operativa D-00…D-03 (non tratti geografici già misurati)

| Unità di lavoro | Riferimento | Obiettivo reale | Stato |
| --- | --- | --- | --- |
| D-00 — Raccordo di ingresso | `CIR-VAL-15` | Confrontare i due rami del bivio; senso verso Strada per Valle; protezioni laterali e vincoli di ingombro della coffa | **Nodo già documentato**, geometria e larghezza non verificate |
| D-01 — Tratto interno, prima parte | A ovest dell'innesto, prima delle curve da censire | Avanzare senza salti nei panorami Google, registrare ogni svolta, luce/vegetazione, muri, curve e ostacoli in quota | **Non osservato sistematicamente**, nessuna curva inventariata |
| D-02 — Tratto interno, seconda parte | Prima dell'innesto con Strada per Costalunga | Come D-01, anche visuali all'indietro e eventuali interruzioni Street View | **Non osservato sistematicamente**, separazione puramente organizzativa |
| D-03 — Raccordo di uscita | `CIR-12` | Collegamento D→E; continuità geometrica e segnaletica, raggio, corsie e margini | **Nodo già documentato**, geometria non verificata |

**D-01 e D-02 non hanno confine metrico definito.** La suddivisione serve alla squadra di rilevamento; non rappresenta chilometri, curve, tornanti o punti GPS osservati. Si assegnano i codici definitivi `T-001` e seguenti ai tornanti **solo dopo** il sopralluogo progressivo.

## 4. Scheda dati da raccogliere su ogni curva

Applicare la metodologia originale senza modificare l'itinerario: percorrere la discesa **nel senso di guida**, panorama dopo panorama, conservando URL, ID e data dell'immagine.

| Campo | Metodo e criterio |
| --- | --- |
| ID | `D-T001`, `D-T002` … soltanto per elementi realmente osservati, nell'ordine corretto |
| Posizione e progressiva | Waypoint su polilinea OSM verificata, metri lungo la centerline; sconosciuti finché la centerline manca |
| Geometria | Curva a destra/sinistra/tornante/esse, ingresso-apice-uscita; raggio solo se ricavato da geometria con datum/provenienza |
| Margini | Dx e sx nella **direzione di guida**: muro, guardrail, ciglio, prato, pendio, ostacoli visibili |
| Prospettiva | Avanti e retro; visuale verso la curva seguente; occlusioni di bosco/muro |
| Ingombro alto | Cavi, rami, aggetti, ponte/sottopasso; annotare visibilità ma **non** attribuire altezze libere da foto |
| Profilo | Quote e pendenze con DTM dichiarato e controllato, mai da angoli del panorama |
| Fonte | Pano ID, URL, mese/anno immagine, coordinate pano, fonte OSM/DTM distinta |
| Qualità della prova | `osservato`, `stimato`, `non verificato`; `osservato` vale solo per ciò che è effettivamente visibile |
| Integrazione gioco | Modello, collisioni, volume Yaris/coffa e test in Godot; tenuti distinti dai risultati statici |

### Registro delle lacune, senza false attestazioni

- **Copertura intermedia:** da `CIR-VAL-15` a `CIR-12` non risultano nel documento panorami intermedi; non è possibile garantire né negare che Street View copra l'intero collegamento.
- **Tornanti:** totale, ordine, lato della curva e raggi **ignoti**. Gli angoli della camera o una svolta dell'itinerario Maps non danno un conteggio.
- **Tracciato metrico:** non esiste ancora la polilinea verificata di D né un DTM regionale validato con sistema di riferimento/datum. La base `data/geography/osm_survey.geojson` contiene il **borgo** e non copre l'intero ramo stradale verso 13.379205 E; non usarla come prova del settore D.
- **Fisica:** altezza libera per coffa/albero, larghezza stradale, collisioni di guardrail/muro, pendenze, superficie reale e sicurezza del percorso non misurate né testate nel motore.
- **Servizi di terzi:** le immagini Google si collegano per ispezione, non si copiano come texture o materiali del gioco; usare fonti geometriche con diritti documentati.

## 5. Specifica di integrazione in Godot e Blender, ancora non implementata

1. Acquisire gli **OSM way effettivi per D**, mantenendo gli ID, i nodi sorgente, data e ODbL. Censire raccordi di inizio/fine e garantire concatenazione degli estremi in direzione V→D→E. Rifiutare salti fra linee o segmenti invertiti.
2. Campionare un **DTM regionale con datum verticale identificato** e trasformare EPSG:4326 → ENU → Godot (X est, Y alto, Z sud). In Blender: X est, Y nord, Z alto. I waypoint panoramici non sono punti della centerline.
3. Creare spline stradale, sezione/collisioni provvisorie, banchine e muri solo per parti osservate. La geometria per parti ignote può essere **artisticamente provvisoria**, chiaramente etichettata, ma non dichiarata replica del reale.
4. Prima di fissare gli ostacoli scenografici, testare l'inviluppo volumetrico della **Toyota Yaris con albero, coffa e passeggera**, incluse escursioni di rollio e sospensione; evitare collisioni invisibili.
5. Eseguire `python tools/check_project.py` e i collaudi prescritti in `docs/COLLAUDO_PC.md` quando codice/scena disponibili. Archiviare FPS, telemetria e difetti; la correttezza di un JSON non equivale a prova in-engine.

## 6. Controlli e decisione di rilascio

**Eseguito:** lettura del `CIRCUITO_SOPRALLUOGO.md` fornito, confronto con `AGENTS.md`, `README.md` e documenti progettuali del repository; trascrizione dei **passaggi 15–16** e dei tre riferimenti panoramici; sostituzione dell'inventario errato "Borgo alto"; predisposizione dati strutturati in `data/geography/sector_d_survey.json`.

**Non eseguito:** rilievo continuo dei 1,4 km in Street View; conteggio delle curve; download della polilinea D e del DTM; import Blender/Godot; test fisici di marcia D; sincronizzazione della copia Windows `C:\Giochi\Sviluppo\Viaggio a Soffumbergo`. Non è dimostrabile la "mappatura completa" richiesta.

**Criterio di completamento D:** segmento stradale continuo verificato dall'uscita V all'ingresso E, elenco dei panorami coprenti e delle lacune, tutte le curve/attraversamenti documentati nel senso di marcia, polilinea riutilizzabile con quote/datum validati, collisioni e ingombri controllati, test Godot superati con evidenze. **Finché non ci sono queste prove, il settore è solo «preparato», non «completo».**

## 7. Fonti

- **Fonte primaria dell'ambito e delle osservazioni:** `CIRCUITO_SOPRALLUOGO.md` allegato nel progetto ChatGPT, sessione 19/10/2026, righe 21–31, 46–51, 74–79 e 93–112.
- **Repository:** `AGENTS.md`, `docs/PROGETTO.md`, `docs/DECISIONI.md`, `docs/ARCHITETTURA.md`, `docs/RIFERIMENTI_E_SOPRALLUOGO.md`, `data/geography/provenance.json`.
- [Comune / itinerari territoriali di Faedis](https://www.faedisnicefaedisgood.com/sentieri-e-itinerari/): contesto generale fra Valle e Costalunga, **non** misura della strada D.
- [OpenStreetMap — licenza e attribuzioni](https://www.openstreetmap.org/copyright): riferimento per futura acquisizione dei dati stradali; **nessuna nuova estrazione completa D effettuata in questa modifica**.
