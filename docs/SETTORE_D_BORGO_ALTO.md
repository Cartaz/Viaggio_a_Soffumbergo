# Settore D — Borgo alto di Valle di Soffumbergo

**Stato: inventario planimetrico preparatorio, NON sopralluogo completo.** Redatto il 20 ottobre 2026. Ambito: strada nel nucleo alto, incroci, piazzetta, chiesa/campanile, sagome degli edifici e connessioni pedonali da verificare. Non sostituisce il settore **V** dedicato alla visita/esplorazione, né le ricognizioni degli altri settori.

> **Vincolo documentale aperto.** Il file `CIRCUITO_SOPRALLUOGO.md`, indicato dall'utente nei *file di progetto di ChatGPT*, non è risultato consultabile tramite le sorgenti documentali disponibili in questa sessione e non è nel ramo `main` di GitHub. Prima di dichiarare *completo* il settore, allineare confini, formato e criteri di accettazione a tale documento. Si applica intanto il metodo in `docs/PROGETTO.md` §4 e `docs/RIFERIMENTI_E_SOPRALLUOGO.md`; non si indovinano confini o progressive mancanti.

## 1. Fonti, livelli di attendibilità e base metrica

| Codice | Fonte | Riscontro / limite |
| --- | --- | --- |
| D-S01 | `data/geography/osm_survey.geojson`, `data/geography/provenance.json` | Estratto OSM circoscritto al borgo, acquisito 18/10/2026; reticolo stradale e sagome, senza quote affidabili o garanzia di completezza. Dati © OpenStreetMap contributors, ODbL. |
| D-S02 | `docs/RIFERIMENTI_E_SOPRALLUOGO.md`, SV-01–SV-04 | Campioni Street View marzo 2026 (via Prestento) e maggio 2023 (piazzetta); non è un attraversamento continuo documentato. |
| D-S03 | [Wikimedia Commons: Valle di Soffumbergo](https://commons.wikimedia.org/wiki/Category:Valle_di_Soffumbergo), F-01–F-04 nel dossier | Fotografie originali 2008 e 2020, con licenze sulle rispettive pagine. Utili per facciata, campanile e scorci, ma non per dimensioni esatte o arredi attuali. |
| D-S04 | [Comune di Faedis — Piano comunale di emergenza, beni culturali](https://www.comune.faedis.ud.it/media/files/030036/attachment/piano_comunale_di_protezione_civile_G7z3fVl.pdf) | Distingue chiesa e campanile dei Santi Pietro e Lorenzo **a Valle** dalla diversa chiesa di San Giovanni e Paolo **a Colloredo**. |
| D-S05 | [Pro Loco Valle, programma 2025](https://www.prolocovalledisoffumbergo.it/wp-content/uploads/2025/09/CastagneMiele_lib_0925-web.pdf) | Indica Piazza Clemencig davanti alla chiesa come punto di ritrovo per l'evento; l'allestimento temporaneo non è arredo permanente. |
| D-S06 | [Veduta aerea della festa del 2022](https://www.nordest24.it/festa-delle-castagne-e-del-miele-di-castagno-a-valle-di-soffumbergo/) | Contesto visivo di coperture, chiesa, campanile e spazio della piazza; tavoli, tende, persone e veicoli non sono strutture permanenti. |

**Riferimento geografico:** WGS84/EPSG:4326, coppie `[longitudine, latitudine]`. Metodologia locale 3D in `docs/ARCHITETTURA.md`: ECEF → ENU → Godot con X est, Y alto, Z sud. L'estratto OSM non contiene un DTM validato: tag altimetrici eventualmente presenti **non sono una quota stradale certificata**. Il conteggio degli edifici non certifica numero reale di fabbricati.

## 2. Inventario riproducibile

Dalla base esistente si ricavano **91 sagome di edifici, 35 linee stradali/pedonali e un nodo di località** nell'area di estrazione, che si estende anche oltre il nucleo D. Di 91 edifici, **86** possiedono un tag `height` OSM: è metadata grezzo, **non** misura ricontrollata; non usarlo per generare mesh definitive. L'inventario completo, con ID OSM, bbox WGS84 e stati di verifica, è in [`data/geography/sector_d_survey.json`](../data/geography/sector_d_survey.json); la geometria completa resta nell'estratto originale per non duplicare e alterare le coordinate. Non è corretto dire che tutti e 91 gli edifici appartengano certamente al settore D: i confini esatti non sono ancora verificati.

| ID di lavoro | Elemento | Evidenza geografica | Verifica visiva / priorità |
| --- | --- | --- | --- |
| D-POI-01 | **Chiesa dei Santi Pietro e Lorenzo** | [OSM way 36686356](https://www.openstreetmap.org/way/36686356); geometria nell'estratto | Sagoma mappata; facciata e vicinanze confrontate con Street View SV-03/04 e foto Commons F-01/F-03. Priorità massima per modellazione delle superfici osservate. |
| D-POI-02 | **Campanile** | [OSM way 36427963](https://www.openstreetmap.org/way/36427963), tag `man_made=tower`, `tower:type=bell`; `height=17 m` **non verificato** | Foto F-02/F-04 e SV-03/04. Separare geometria verificabile della copertura dall'altezza OSM provvisoria. |
| D-POI-03 | **Piazza don Antonio Clemencig** | OSM ways 358101684, 1107817252, 1108507498 (strada); ramo 1107817255 marcato `track` | Riscontri fotografici e SV-04, pavimentazione e fronti da descrivere per singola vista. La larghezza non è misurata. |
| D-POI-04 | **Soggiorno Don Bosco** | [OSM way 36158063](https://www.openstreetmap.org/way/36158063) | Nome geografico mappato, non foto di facciata identificata: nessun dettaglio architettonico dichiarato osservato. |
| D-POI-05 | **Ingresso al nucleo da via Prestento** | OSM ways 358101686 (`track`) e 136494656 (`residential`) | Riscontri SV-01/02 riferiti a via Prestento ma **non** copertura continua del collegamento. |
| D-POI-06 | **Zona candidata PV-01 sotto Valle** | Punto d'osservazione circa [13.39181, 46.15687] nel dossier | Non è un poligono di parcheggio, né proprietà o accessibilità pubblica verificate. Il collegamento pedonale fino alla piazza non è ancora provato. |

I numeri OSM individuano *oggetti del dataset*: il nome, l'uso attuale di un edificio, l'altezza, le aperture e l'orientamento delle facciate devono ancora essere verificati uno per uno. Il dato `ele=678` del nodo dell'abitato è un tag grezzo con datum non verificato: non interpolare con esso una strada o i gradini.

## 3. Reticolo carrabile: ordine delle connessioni **OSM**, non percorso stradale approvato

L'analisi degli estremi delle polilinee mostra una catena topologicamente connessa da via Prestento alla piazza per **otto segmenti mappati**:

| Sequenza | Strada | OSM way | Lunghezza planimetrica indicativa |
| --- | --- | --- | ---: |
| D-R01 | Via Prestento | 136494656 | 30 m |
| D-R02 | Via Monte Piccat | 1107817257 | 4 m |
| D-R03 | Via Monte Piccat | 1107817254 | 25 m |
| D-R04 | Via Monte Piccat | 547054233 | 43 m |
| D-R05 | Via Monte Piccat | 1107817253 | 40 m |
| D-R06 | Via Monte Piccat | 136494659 | 38 m |
| D-R07 | Piazza don Antonio Clemencig | 1107817252 | 9 m |
| D-R08 | Piazza don Antonio Clemencig | 358101684 | 50 m |

**Somma indicativa ~238 m** sul reticolo di centrolinee originali, da approssimazione planimetrica locale con arrotondamento per segmento. Non è una progressiva dell'anello dell'utente e non include via Prestento esterna né eventuali corsie di manovra. Gli estremi degli otto segmenti coincidono nei dati; **non** prova che la Yaris con coffa possa percorrerli o che costituiscano il ramo del circuito indicato dall'utente.

**Altri oggetti da esaminare prima di convalidare percorsi:**
- Via Monte Piccat superiore: ways 136283440 e 1041538032; da verificare continuità con il settore di arrivo/uscita.
- Via Pocivalla: ways 358101685, 894320135 e 136283449 (quest'ultimo classificato `track`, non assumere strada asfaltata carrabile).
- Borgo di Sopra: way 358101687; collegamento effettivo da controllare.
- Collegamenti pedonali: way 136494655 (`footway`), 547054252 (`path`), 604025792 (`path`), 1096222972/73 (`path`), 243981581 (`steps`), 604025801 (`tunnel=building_passage`).
- **Accesso privato:** way 243981582 ha `access=private`. Non trasformarlo in itinerario pubblico o attraversabile senza fonte/permesso.
- I tratti extraurbani lunghi nell'estratto (es. 547054266) **non** vanno assegnati per intero al settore D solo perché intersecano il riquadro di acquisizione.

## 4. Schede d'osservazione necessarie per completare davvero il settore

| ID | Vista o passaggio | Riscontri disponibili | Cosa manca prima di modellare/collaudare |
| --- | --- | --- | --- |
| D-OBS-01 | Ingresso lato Prestento → primi edifici | SV-01/02, OSM | Percorso consecutivo in direzione di gioco; bordi, pendenze, muretti, curve, possibilità di incrocio e inizio preciso del settore. |
| D-OBS-02 | Via Monte Piccat, ramo basso | Reticolo OSM | Foto in avanti/indietro su ogni svolta, soglie, sbalzi, larghezze libere e rami/cavi alla quota della coffa. |
| D-OBS-03 | Bivio della piazza e ramo superiore | Reticolo OSM e SV-03/04 parziali | Sensi di marcia reali, geometria d'intersezione, accessibilità veicolare e ingombri laterali. |
| D-OBS-04 | Piazza Clemencig | SV-03/04, F-01–F-04, veduta aerea del 2022 | Rilievo pavimentazioni, dislivelli, parapetti, manufatti permanenti; distinguere elementi evento temporaneo. |
| D-OBS-05 | Chiesa/campanile | Sagome OSM, fotografie 2008–2020, Street View 2023 | Distanze e altezze confrontate con geometria verificata; materiale e colore per facciate non visibili; eliminare dettagli congetturali. |
| D-OBS-06 | Vie secondarie e passaggi a piedi | 35 linee in dataset, classi OSM | Percorribilità e vincoli d'accesso, scale, rampe, copertura fotografica e limiti di navmesh; nessuna scorciatoia inventata. |
| D-OBS-07 | Percorso PV-01 → nucleo | Punto candidato e reticolo separati | Prova del collegamento continuo percorribile dai topolini; confini del prato e decisione definitiva dell'utente. |
| D-OBS-08 | Uscita del settore D | Way 136283440 e rete circostante | Definizione reale del confine col settore successivo e verso del giro su `CIRCUITO_SOPRALLUOGO.md`. |

**Per ogni tratto:** ingresso/centro/uscita, vista all'indietro, curva sx/dx, margine dx/sx, banchina, guardrail/muro, ostacoli alti, quota e pendenza **solo da DTM validato**, data immagine, URL, livello `osservato/stimato/non verificato` e stato `da osservare/osservato/modellato/collaudato`. Il passaggio fra panorami deve risultare consecutivo: una foto sferica isolata non certifica copertura stradale.

## 5. Istruzioni per la ricostruzione 3D

1. **Bloccare l'allineamento** del tracciato con le coordinate OSM e le convenzioni di `docs/ARCHITETTURA.md`. Nessuna quotatura da screenshot o tag isolato, né radii inventati presentati come misurati.
2. **Prototipare con volumi** le sagome esistenti: chiesa, campanile, fronte piazza e accessi riconoscibili. Mantenere gli edifici senza facciata verificata come masse neutre; niente copie foto/texture protette.
3. **Separare percorsi**: volume di transito della Yaris (inclusi albero, coffa, passeggera, movimento di rollio) da navmesh dei topolini e passaggi privati o incerti.
4. **Testare la giocabilità** soltanto dopo geometria stradale continua, pendenze e collisioni realmente disponibili in Godot. Il corridoio può essere deliberatamente stretto, ma deve essere guidabile con prudenza senza collisioni invisibili o dimensioni falsificate.
5. **Rendere Valle riconoscibile**: silhouette, posizione relativa di chiesa, campanile, spazio della piazza, tetti e scorci, conservando lo stile cartoonesco. Addobbi festivi nelle foto non entrano nella scena diurna ordinaria senza decisione artistica esplicita.

## 6. Controlli effettuati e limiti

- **Eseguito:** lettura della base OSM già nel repository; conteggi delle 91 sagome, 35 linee, 1 nodo; registrazione delle 86 altezze *taggate*; verifica di ID univoci e sequenza con estremi in comune degli otto segmenti D-R01…D-R08. I dati sono conservati in JSON con riferimenti agli oggetti sorgente.
- **Non eseguito:** `python tools/check_project.py` sull'albero di lavoro, sopralluogo continuo con browser Street View, verifica DTM, prova di Blender/Godot, confronto di prospettive in-engine, collaudo della Yaris e della coffa nel settore D. Non attribuire copertura 100% o stato «completo».
- **Da verificare prima del merge come rilievo definitivo:** disponibilità e contenuto del `CIRCUITO_SOPRALLUOGO.md` del progetto ChatGPT, confini effettivi del settore, perimetro del prato, permessi d'accesso e quote. **Non è stato possibile aggiornare o verificare la sincronizzazione della cartella locale Windows** `C:\\Giochi\\Sviluppo\\Viaggio a Soffumbergo`.

## 7. Prossimo passo misurabile

1. Leggere `CIRCUITO_SOPRALLUOGO.md` originale e fissare limiti/verso D, evitando sovrapposizioni con i settori C, E e V.
2. Coprire **in modo continuo** le otto connessioni stradali candidate, verificando l'ordine di gioco; censire ogni svolta come D-OBS con panorama e data.
3. Associare le 91 sagome a viste esterne e annotare progressivamente `facade_status`; se una sagoma ricade fuori D dopo aver fissato i confini, riclassificarla senza cancellare la fonte.
4. Scaricare e controllare l'altimetria regionale, trasformare ENU, costruire la strada, eseguire test di collisioni e progressione Godot, e soltanto allora chiudere la mappatura.

**Fonti permanenti:** `docs/PROGETTO.md`, `docs/DECISIONI.md`, `docs/ARCHITETTURA.md`, `docs/RIFERIMENTI_E_SOPRALLUOGO.md`, `data/geography/provenance.json`, `NOTICE.md`.
