# Settore B — via Monte San Lorenzo → località Colloredo

**Ricognizione documentale del 20 ottobre 2026. Stato: cartografia sorgente e panorami intermedi non acquisiti; tre nodi osservati in precedenza. Non è una mappatura stradale completa.**

## Identificazione univoca

Il riferimento è l'[itinerario originale](CIRCUITO_SOPRALLUOGO.md): partenza da Faedis, via Campeglio, arrivo a Valle e ritorno via Canal di Grivò. Il settore B si colloca **dopo** il settore A (bivio della SR356) e **prima** del settore C (Valle Soffumbergo / via Prestento). Non confonderlo con Colloredo di Monte Albano, altra località dell'Udinese.

| Passaggio dell'app | Provenienza | Descrizione | Distanza arrotondata dall'app |
| --- | --- | --- | ---: |
| 7 | CIR-06 → CIR-07 | Sinistra in via Monte San Lorenzo | 1,8 km |
| 8 | CIR-07 → CIR-08 | Leggera destra verso località Colloredo | 220 m |
| **B totale** | | Dato indicativo, **non somma metrica certificata** | **circa 2,02 km** |

Le coordinate che seguono sono **posizioni approssimative dei panorami**, non punti geodetici di asse strada. Tutte sono in WGS84, ordine longitudine/latitudine nei dati GeoJSON; la data è quella **dell'immagine**, non dell'ispezione.

## Nodi effettivamente osservati nel sopralluogo precedente

| ID | Coordinate lat., lon. | Immagini | Evidenza attestata dal dossier | Che cosa non prova |
| --- | --- | --- | --- | --- |
| [CIR-06](https://www.google.com/maps/@?api=1&map_action=pano&pano=apdNekWQ0-mRaBBCzONB1A&viewpoint=46.1271692%2C13.3666683&heading=110.04&pitch=0) | 46.1271692, 13.3666683 | aprile 2026 | Innesto SR356/via Monte San Lorenzo, sinistra vicino a casa chiara con balcone; strada principale con mezzeria e marciapiedi | Geometria e visibilità dell'intera salita |
| [CIR-07](https://www.google.com/maps/@?api=1&map_action=pano&pano=N4dZ5v3ba82LlKJo6Fyiog&viewpoint=46.1331275%2C13.3820732&heading=36.16&pitch=0) | 46.1331275, 13.3820732 | marzo 2026 | Carreggiata senza mezzeria, muro di pietra a destra, pendio vegetato a sinistra, case e vigneto | Continuità di tali elementi fino agli altri punti; presenza di tornanti |
| [CIR-08](https://www.google.com/maps/@?api=1&map_action=pano&pano=sUkLbqb6kVahRI6qFIMwjA&viewpoint=46.1345686%2C13.3838913&heading=6.16&pitch=0) | 46.1345686, 13.3838913 | marzo 2026 | Bivio presso le case; muro, bacheca a sinistra e margini erbosi | Larghezza, raggio e quota del raccordo con il settore C |

L'indicazione **«leggera curva a destra»** al passaggio 8 deriva dalle istruzioni di navigazione. Non è un rilievo di apice, raggio o tornante. Il numero di tornanti del settore B è **sconosciuto**, non pari a zero.

## Inventario degli elementi e ricadute sul modello

| Elemento | Evidenza | Trattamento nel 3D | Attendibilità |
| --- | --- | --- | --- |
| Ingresso da strada più ampia e segnalata | CIR-06 | Passaggio visivo da SR356 alla strada locale; nessun cambio di sezione quotato | Osservato nel nodo |
| Edificio chiaro con balcone | CIR-06 | Landmark artistico **provvisorio**, da confrontare con prospettive aggiuntive | Osservato nel nodo |
| Muro in pietra sul margine destro | CIR-07 | Elemento di riferimento locale, lunghezza e altezza da acquisire | Osservato nel nodo |
| Vegetazione a monte, abitazioni e vigneto | CIR-07 | Moduli paesaggistici plausibili, senza attribuire un'estensione verificata | Osservato nel nodo |
| Muro, bacheca, case al bivio | CIR-08 | Segnalare l'arrivo a Colloredo e il passaggio al settore C | Osservato nel nodo |
| Curve, scarpate, barriere, cavi, rami e accessi intermedi | **Nessuna copertura continua** | Non posizionare come elementi reali prima del censimento; usare solo segnaposti dichiarati | Da verificare |
| Strada completa e altimetria | **Polilinea e DTM assenti** | Niente mesh carrabile, collisioni stradali definitive o calcolo di velocità consigliate | Non verificato |

**Gameplay proposto, non osservazione geografica:** il settore deve introdurre il rollio dovuto alla massa alta di coffa, albero e passeggera sulle curve relativamente ampie. Il trasferimento di carico dipende dalla fisica, non da trigger che ribaltano arbitrariamente l'auto. Non inventare curve o allargamenti apposta presentandoli come reali.

## Lacune ordinate e protocollo di chiusura

1. **B-07, CIR-06 → CIR-07 (app: 1,8 km).** Percorrere Street View passo-passo nel senso del circuito. Salvare per ogni vista almeno ID, data immagini, posizioni inizio/fine di copertura, margine destro e sinistro, segnaletica, accessi e ostacoli alti. In corrispondenza di ogni vera curva registrare ingresso, apice e uscita; i tornanti ricevono identificativi solo dopo controllo.
2. **B-08, CIR-07 → CIR-08 (app: 220 m).** Verificare la leggera destra, il posizionamento effettivo dell'incrocio e la connessione con il settore C. Non trasformare il bivio in un tornante.
3. Estrarre le **way stradali complete da OSM** per il settore, con data e licenza; verificarne continuità e direzione rispetto alle istruzioni originali. La sola distanza più breve della rete non identifica necessariamente il percorso dell'utente.
4. Acquisire terreno regionale FVG con sistema di riferimento e datum espliciti. Solo dopo: quote, profilo, raggi geometrici, banchine e limiti di visibilità; controllare separatamente l'altezza libera necessaria alla coffa.
5. Preparare versione `source` e versione `game` della spline, indicare ogni adattamento e ripetere collaudo in Godot sulla fisica della Yaris.

L'acquisizione non si dichiara completa sulla base di **18 panorami complessivi dell'intero anello**: solo tre appartengono ai nodi del settore B. La copertura continua su questo settore **non è misurabile** con i dati attuali.

## File verificabili

- [`data/geography/sector_b_observations.geojson`](../data/geography/sector_b_observations.geojson): soltanto 3 geometrie `Point`, **nessuna LineString inventata**.
- [`references/circuito/settore_b.json`](../references/circuito/settore_b.json): tratte B-07/B-08, rischi, valori mancanti espressi come `null` e stato della ricognizione.
- [`tools/extract_sector_b.py`](../tools/extract_sector_b.py): estrazione **opzionale** di una candidatura da una base OSM GeoJSON acquisita separatamente. Non scarica dati; non conferma il percorso. Esempio, **solo dopo** una estrazione OSM completa:

```bash
python tools/extract_sector_b.py --input data/geography/osm_survey.geojson --output reports/sector_b_osm_candidate.geojson
```

L'estrazione attuale presente in `data/geography/osm_survey.geojson` riguarda **solo Valle**, e quindi deve produrre un errore di mancanza dei nodi B; non falsificare coordinate o collegamenti per superare il controllo. Dopo l'acquisizione di un estratto sufficientemente ampio, confrontare manualmente la candidata col percorso della fonte primaria.

- [`tests/test_sector_b_survey.py`](../tests/test_sector_b_survey.py): prove sintetiche che rifiutano reti scollegate o incomplete e impediscono di classificare i panorami come asse stradale definitivo.

## Fonti e limiti d'uso

1. [`docs/CIRCUITO_SOPRALLUOGO.md`](CIRCUITO_SOPRALLUOGO.md), ricognizione virtuale del 19 ottobre 2026, URL Google Maps originale e campioni CIR-06/07/08.
2. [Cartina orientativa del Comune di Faedis](https://faedisnicefaedisgood.com/wp-content/uploads/2023/03/cartina_comune_faedis.pdf): orientamento generale, **non** misure di strada.
3. [OSM copyright e ODbL](https://www.openstreetmap.org/copyright): fonte della **futura** polilinea riutilizzabile; i 3 punti fotografici qui registrati non sono un'acquisizione OSM.
4. [Catalogo altimetrico FVG](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826): metadati disponibili, **nessun DTM del settore acquisito/validato**.

Nessuna immagine Google, screenshot, texture o geometria tracciata da Google viene incorporata nei dati o nella repository. Lo stato «mappatura completa» rimane **aperto** finché non siano verificati raccordi, curve, quote e copertura continua.

### Stato della consegna e controlli

Sessione 20 ottobre 2026: inventario delle osservazioni, dati macchina e estrattore di candidati OSM preparati. Sei test unitari isolati superati su dati sintetici; non è un test del gioco. Sono ancora da eseguire il controllo integrale `python tools/check_project.py` su una copia del repository e prove GIS/Street View/Godot. La cartella Windows locale non è accessibile da questa sessione, quindi la sincronizzazione con il PC non è confermata.