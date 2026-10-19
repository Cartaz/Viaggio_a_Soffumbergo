# Settore V — Valle di Soffumbergo: mappatura planimetrica e sopralluogo incompleto

Aggiornamento: 20 ottobre 2026. **È stata ricostruita integralmente la polilinea 2D del ramo di andata e ritorno presente nell'estratto OSM esistente, non l'intera copertura Street View, né un terreno 3D collaudato.**

## Riferimento non negoziabile

L'itinerario originale del file dell'utente `CIRCUITO_SOPRALLUOGO.md` attraversa Faedis, Campeglio e Valle, poi rientra via Canal di Grivò. Il settore V è solo la deviazione **via Monte Piccat → Piazza don Antonio Clemencig → ritorno al bivio** (passaggi 11–14). Il settore D comincia al passaggio 15. La località della tappa è indicata anche come “piazza A. Clementig” nell'app; la toponomastica OSM e [Pro Loco](https://www.consorzioprolocotorrenatisone.it/proloco/pro-loco-valle-di-soffumbergo/) riportano “Piazza don Antonio Clemencig”. Nessuna modifica all'itinerario scelto dall'utente.

La geometria proviene da `data/geography/osm_survey.geojson` (estrazione OSM del 18/10/2026), non da un ricalco di Google Maps. L'intersezione alla piazza usa quattro way consecutivi: `1041538032` → `136283440` → `136494659` → `1107817252`. Le loro estremità coincidono nelle coordinate OSM disponibili.

| Passo Maps | Istruzione originale | App, arrotondata | Asse 2D OSM, indicativo |
| --- | --- | ---: | ---: |
| 11 | Destra in via Monte Piccat | 230 m | 219.585 m |
| 12 | Leggermente a destra verso la tappa in piazza | 45 m | 47.245 m |
| 13 | Riparti dalla tappa verso via Monte Piccat | 45 m | 47.245 m |
| 14 | Leggermente a sinistra in via Monte Piccat | 210 m | 219.585 m |
| **Totale** | Andata e ritorno | **530 m** | **533.66 m** |

Le differenze sono attese: le svolte Google e il centro del segnaposto non coincidono necessariamente con le giunzioni OSM; i valori dell'app sono arrotondati. **La corrispondenza semantica dei passaggi ai way è un'interpretazione topologica, non una verifica metro per metro in Street View.** Il punto di piazza sull'asse OSM è 46.1569279 N, 13.3933009 E; il segnaposto Google è 46.1569587 N, 13.3933096 E.

## Inventario planimetrico disponibile

- `data/geography/sector_v_route.geojson`: due LineString con tutti i vertici OSM, in andata e ritorno, più punti di confine/svolta; nessuna quota o larghezza.
- `data/geography/sector_v_context.geojson`: **53 sagome OSM** con centroide planimetrico a non più di 60 m dall'asse stradale, **7 tratti pedonali/tracce candidati** e **5 tratti stradali adiacenti**, conservati separatamente da quelli previsti per la guida. Il raggio di 60 m è un filtro di lavoro, non una fascia di visibilità o un confine amministrativo.
- La chiesa dei **Santi Pietro e Lorenzo** è individuata con la sagoma OSM `way/36686356`, non con un modello di facciata. La Pro Loco è documentata in piazza Don A. Clemencig 10; non si trasferisce automaticamente tale informazione a una specifica sagoma senza verifica fotografica.
- Nel contesto sono presenti una `highway=steps` (`way/243981581`) e un `highway=path` con `tunnel=building_passage` (`way/604025801`). **Non sono elementi guidabili dalla Yaris** né confermano altezze libere e continuità del percorso a piedi.
- Il prato `PV-01` è un candidato documentato nel progetto a 46.1568696 N, 13.3918124 E, **esterno alla deviazione stradale principale**. L'accesso, i confini e il collegamento a piedi restano da verificare.

## Diario fotografico già acquisito (non nuova visita autonoma)

| ID | Immagine | Nodo riscontrato nel dossier del 19/10 | Cosa resta da verificare |
| --- | --- | --- | --- |
| [CIR-11](https://www.google.com/maps/@?api=1&map_action=pano&pano=VG6N0zxqJ7PLJ6BbJX5OWA&viewpoint=46.1588292%2C13.3922833&heading=2.49&pitch=0) | Marzo 2026 | Bivio nord tra via Prestento e via Monte Piccat, segnaletica e parapetti | Continuità fino a CIR-VAL-12 |
| [CIR-VAL-12](https://www.google.com/maps/@?api=1&map_action=pano&pano=vpV1Mx9ExgiJUS-jD1uK2g&viewpoint=46.1574774%2C13.3932969&heading=133.71&pitch=0) | Maggio 2023 | Muri di terrazzamento, ringhiera e lampione | Curve intermedie e accesso effettivo alla tappa |
| [CIR-VAL-14](https://www.google.com/maps/@?api=1&map_action=pano&pano=vRTA51C8D5061qUOBsYf0A&viewpoint=46.1571511%2C13.3934294&heading=359.32&pitch=0) | Maggio 2023 | Strada senza mezzeria e STOP di ricongiungimento | Distanze, visuali e manovra di ritorno |
| [CIR-VAL-15](https://www.google.com/maps/@?api=1&map_action=pano&pano=KAzz8xQ3_0RkMdu4rPLCNA&viewpoint=46.1588137%2C13.3926044&heading=321.61&pitch=0) | Maggio 2023 | Connessione settentrionale con strada per Valle | Immissione e continuità verso D |
| SV-03 / SV-04 | Maggio 2023 | Chiesa, campanile, piazzetta, terrazza, gradini e ringhiere | Facciate nascoste e percorso continuo |

Fonti di riscontro addizionali: [fotografia della chiesa, YukioSanjo, 2020](https://commons.wikimedia.org/wiki/File:Faedis_-_Valle_-_Chiesa_1.jpg), [seconda fotografia del campanile](https://commons.wikimedia.org/wiki/File:Faedis_-_Valle_-_Chiesa_-_2.jpg). Sono riferimenti esterni, non asset incorporati nel repository. Arredi occasionali nelle fotografie non saranno modellati come permanenti senza prova.

## Lacune e criterio di chiusura del settore

1. Percorrere con immagini consecutive **ciascun intervallo** CIR-11 → CIR-VAL-12 → piazza → CIR-VAL-14 → CIR-VAL-15, annotando le interruzioni effettive. L'esistenza di waypoint isolati non equivale a copertura continua.
2. Registrare incroci, eventuali tornanti verificati (solo allora codici T-*), visibilità, ingresso/apice/uscita, margini, ringhiere, gradini, restringimenti, alberi e cavi in quota.
3. Confermare se la Yaris modificata possa raggiungere la piazza ed effettuare la manovra prevista dall'itinerario, senza supporre che il segnaposto sia un posto auto. In gioco, qualsiasi manovra adattata va dichiarata come adattamento.
4. Validare quote, datum verticale, pendenza, raggi, sezioni e altezza libera usando fonti territoriali idonee. Non usare 2D OSM come superficie stradale con quote inventate.
5. Completare il censimento **fotografico delle facciate**, campanile, piazzetta e gradini; verificare il cammino reale dal prato PV-01 prima di preparare navmesh per i topolini.
6. Importare la geometria 3D soltanto dopo l'acquisizione delle quote; provare davvero in Godot 4.5.1 e Blender e registrare screenshot/telemetrie. Nessuna prova nel motore è stata compiuta in questa ricognizione.

**Stato:** ricostruzione geografica 2D dell'andata/ritorno completata per i quattro way scelti, contesto OSM ritagliato, sopralluogo visuale e visita a piedi **ancora incompleti**.

## Provenienza, diritti e riproducibilità

Fonte: `data/geography/provenance.json`; OSM 18/10/2026, EPSG:4326 lon/lat, coordinate senza quote. © OpenStreetMap contributors, [ODbL 1.0](https://www.openstreetmap.org/copyright). Le osservazioni Street View sono riportate come testi e URL dall'allegato del 19 ottobre; nessuna immagine, screenshot o spline stradale è stata copiata da Google. Le sagome degli edifici sono cartografiche, non rilevamenti di facciate. I dati dei settori A, B, C, D, E, F non vengono modificati.


## Output ispezionabili della mappatura V

- [Pianta SVG del settore](../reports/sector_v_planimetry.svg): i tratti di andata e ritorno coincidono nella pianta, perché la tappa in piazza richiede di ripercorrere lo stesso asse.
- [Checklist degli edifici entro 60 m](../reports/sector_v_building_checklist.csv): 53 sagome con gli stessi `VAL-B...` dell'inventario generale; nessuna facciata è segnata come verificata.
- [Centrolinea GeoJSON](../data/geography/sector_v_route.geojson), [contesto con sagome e accessi](../data/geography/sector_v_context.geojson) e [registro JSON](../data/geography/sector_v_survey.json).
- [Test di integrità](../tests/test_sector_v.py): verificano l'esatta concatenazione delle way OSM, la geometria del ritorno, i quattro passaggi originali, la conservazione delle geometrie sorgenti e la distinzione tra osservato e ignoto.

La pianta SVG usa spessori grafici puramente simbolici per strada e sentieri: **non equivale a una rappresentazione in scala della larghezza della carreggiata**, che resta ignota. L'esistenza dei sentieri OSM non certifica libertà di accesso, gradini superabili o percorso a piedi continuo dal prato.
