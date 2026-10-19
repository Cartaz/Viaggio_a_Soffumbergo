# Settore C — Colloredo / Valle Soffumbergo / via Prestento

**Stato (20 ottobre 2026): mappatura parziale.** Fonte vincolante: file `CIRCUITO_SOPRALLUOGO.md` del progetto ChatGPT (19 ottobre 2026). Non dichiarare un rilievo completo: il dossier contava soltanto i campioni CIR-08, CIR-09 e CIR-11. Non è stato effettuato un nuovo attraversamento continuativo di Street View, né un test del percorso in Godot.

## Confini esatti del settore

Il settore C parte dopo B presso Colloredo (passaggio 9 del percorso originale). Si percorre **Valle Soffumbergo per 1,0 km**, quindi **via Prestento per 3,3 km** (passaggio 10). La lunghezza **4,3 km** è somma di distanze arrotondate di Google Maps, non una misura del nostro rilievo. Il tratto termina al bivio superiore per via Monte Piccat, prima della svolta a destra del passaggio 11, che appartiene al **settore V**. Non confondere i rami V, D ed E con la salita C.

## Riferimenti osservati nel dossier

| ID | Punto WGS84 (lat; lon) | Immagini | Riscontro |
| --- | --- | --- | --- |
| [CIR-08](https://www.google.com/maps/@?api=1&map_action=pano&pano=sUkLbqb6kVahRI6qFIMwjA&viewpoint=46.1345686%2C13.3838913&heading=6.16&pitch=0) | 46.1345686; 13.3838913 | marzo 2026 | Bivio presso case, muro, bacheca, margini erbosi, senza mezzeria |
| [CIR-09](https://www.google.com/maps/@?api=1&map_action=pano&pano=4JvmsXRN5WUW20jnlf6hnA&viewpoint=46.1369502%2C13.3913328&heading=25.73&pitch=0) | 46.1369502; 13.3913328 | marzo 2026 | Asfalto senza mezzeria, bosco, margine sterrato a destra |
| [CIR-11](https://www.google.com/maps/@?api=1&map_action=pano&pano=VG6N0zxqJ7PLJ6BbJX5OWA&viewpoint=46.1588292%2C13.3922833&heading=2.49&pitch=0) | 46.1588292; 13.3922833 | marzo 2026 | Bivio con ringhiera su pilastrini, muretto e cartelli |

Coordinate dei panorami = riferimenti di osservazione, non rilievo dei margini stradali; le immagini sono linkate, non copiate.

## Dati cartografici implementati

- `data/geography/sector_c_partial.geojson`: **97 vertici originali** della way OSM [547054266](https://www.openstreetmap.org/way/547054266), già memorizzata in `data/geography/osm_survey.geojson`, `highway=unclassified`.
- Asse continuo disponibile: da **46.1463267 N / 13.3889350 E** a **46.1590017 N / 13.3924178 E**, somma geodetica dei segmenti **1736.7 m**. È solo parte della salita: non inferire che la differenza con 4,3 km sia la lunghezza esatta mancante.
- **Discontinuità 1:** CIR-08 → CIR-09 (circa 632 m in linea d'aria).
- **Discontinuità 2:** CIR-09 → primo vertice OSM (circa 1059 m in linea d'aria).
- **Discontinuità 3:** ultimo vertice OSM → CIR-11 (circa 22 m in linea d'aria).
- Le linee tratteggiate in `reports/sector_c_survey.svg` mostrano **solo separazioni dirette fra riferimenti, non una strada ricostruita o guidabile**.
- Nessuna quota, pendenza, sezione trasversale, raggio o altezza libera misurata. Non creare una strada 3D realistica a partire da questi soli dati.

## Due candidati a curva stretta (non confermati visivamente)

| ID | Progressiva dalla prima coordinata OSM | Punto WGS84 (lat; lon) | Stato |
| --- | ---: | --- | --- |
| C-MAP-01 | 172 m | 46.1476889; 13.3895224 | Potenziale tornante dalla geometria; verificare ingresso, apice, uscita e senso di percorrenza |
| C-MAP-02 | 261 m | 46.1469646; 13.3894332 | Potenziale tornante dalla geometria; verificare ingresso, apice, uscita e senso di percorrenza |

Questi cambi di direzione sono **priorità di sopralluogo**, non tornanti classificati/contati, e la loro progressiva NON parte da Colloredo. Solo una verifica visiva lungo l'intera strada consente di assegnare i codici T-xxx e associare parapetti, muri, vegetazione, segnaletica o affacci.

## Lavoro rimanente per una mappatura completa

- [x] Confini, passaggi, panorami e date del dossier riconciliati.
- [x] Copiati senza alterazioni i 97 vertici OSM con provenienza.
- [x] Esportati i tre riferimenti e i due candidati geometrici, con incertezze esplicite.
- [ ] Recuperare dal dataset stradale riutilizzabile l'intera polilinea tra confine B e confine V, verificando tutti gli innesti.
- [ ] Percorrere **continuamente** Street View nella direzione di gioco, con diario progressivo e segnalazione dei salti di copertura.
- [ ] Censire curve e tornanti verificando ingresso/apice/uscita, entrambi i margini e visuale retrospettiva.
- [ ] Censire parapetti, muri, slarghi, ponti, accessi, ramaglie/cavi in quota e ostacoli alla coffa, distinguendo osservazione e misura.
- [ ] Integrare il DTM con datum e licenza dichiarati; ricavare larghezze, raggi, pendenze e quote senza utilizzare geometria ricalcata da Google.
- [ ] Costruire la spline 3D, i bordi, la collisione e provare la Yaris caricata in Godot.

## Fonti, test e limiti

Fonte geometrica: [OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright), copia repo `data/geography/osm_survey.geojson`, provenance `data/geography/provenance.json`; fonte fotografica: collegamenti sopra e dossier utente. Per futuro DTM: [Regione FVG, CTRN](https://irdat.regione.fvg.it/CTRN/ricerca-cartografia/) (fonte individuata, **non ancora scaricata**). `tests/test_sector_c_survey.py` controlla corrispondenza esatta dei vertici, lunghezza, assenza di quote e status dei candidati. **Test statici ≠ sopralluogo completo o collaudo in Godot.** La cartella Windows locale non è accessibile a questa sessione.
