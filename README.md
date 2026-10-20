# Viaggio a Soffumbergo

## Coffa e tornanti

**Valle 3D 0.1:** scena autonoma con terreno LiDAR georeferenziato, 36 settori,
LOD 2/4/8 m, collisioni a 2 m, 91 sagome OSM e strade provvisorie colorate.
Verificata in Godot 4.5.1 e Blender 4.5.3; camera libera di ispezione.
[Rigenerazione, avvio e limiti](docs/VALLE_3D.md) ·
[Evidenze dei test](reports/VALLE_3D_VERIFICA.json).
Raster originali e derivati geografici restano locali sotto `build/`, esclusi
dal repository. F5 mantiene il laboratorio; Valle si apre con F6 dalla scena
`godot/scenes/valle.tscn`. Il viaggio completo resta da integrare.

**DTM dell'intero circuito ricevuti:** catalogate 41 tessere a 0,5 m, nessun
NoData; tutti i 9.966 campioni dell'asse OSM candidato sono coperti. Registrate
le differenze nelle sovrapposizioni, senza mediarle o dichiarare pronta la strada.
[Rapporto e procedura](docs/DTM_CIRCUITO_COMPLETO.md).

Una gita 3D cartoonesca a Valle di Soffumbergo: una Toyota Yaris Hybrid Trend MY 2022 rossa, un albero maestro con coffa e due topolini con anatomia naturale e occhi grandi. La nuova direzione artistica si ispira a Bianca e Bernie Disney per colori, volti e accessori, senza antropomorfizzare la struttura corporea.

**Stato: Yaris 0.1 guidabile nel laboratorio Godot 4.5.1.** Il modello è stato generato e renderizzato in Blender 4.5.3 LTS. Passano 28 test preparatori, i controlli dell'asset e 28 controlli dell'integrazione nel laboratorio con rendering reale su Windows. La qualità artistica finale, la dinamica completa e il giro giocabile restano da verificare; il sopralluogo è parziale e non sono stati misurati FPS rappresentativi.

**Modello Yaris 0.1 — base da scolpire ancora molto.** Questa versione conserva l'idea e l'integrazione tecnica; carrozzeria e abitacolo richiedono una sostanziale lavorazione delle forme prima di avvicinarsi alla fedeltà realistica richiesta. La numerazione riguarda il modello auto, non una release giocabile del gioco.

Il modello ha esterni e abitacolo, quattro portiere e portellone apribili, ruote e volante separati, tre livelli di dettaglio e una variante con foro reale per l'albero. [File, ispezione e integrazione](docs/YARIS_MODELLO.md) · [Versione e contenuti](art/vehicles/yaris_2022/MODEL_VERSION.json) · [Riferimenti Toyota e stime](references/yaris_2022/README.md) · [Evidenze del collaudo](reports/yaris_2022/VERIFICA.md).

## Base tecnica disponibile

| Parte | Consegna | Limite della verifica |
| --- | --- | --- |
| Godot | Yaris guidabile, quattro sospensioni, pneumatici, trazione anteriore, carico alto, tre camere, HUD e CSV | Accelerazione, curva breve, frenata e comandi provati; accettazione dinamica completa ancora aperta |
| Calcoli | Masse, baricentro, tensore completo, aderenza combinata | Test Python, non ancora dinamica motore |
| Regole | Checkpoint ordinati, sosta, visita, ritorno e salvataggio atomico | Modello Python, da collegare alla scena 3D |
| Valle | 91 sagome OSM, inventario e mappa del sopralluogo | Dati mappati; quote, facciate e copertura da verificare |
| Blender | Sorgente Yaris, GLB e render; generatori delle guide del borgo | Yaris eseguita; revisione artistica finale e guide del borgo ancora aperte |
| Esplorazione | Controller di movimento e seguito della compagna | Richiedono rig, navmesh e integrazione nella scena |
| Percorso | Pipeline WGS84 → coordinate locali e superficie provvisoria | Il solo DTM 0,5 m di Valle è stato acquisito; asse stradale e terreno dell'intero anello ancora da verificare |

Il laboratorio è un piazzale sintetico con rampa e cerchio di riferimento: **non rappresenta Faedis o Valle**. La Yaris usa la ricostruzione da fotografie; albero, coffa e occupanti rimangono segnaposto. I render del modello e le prove del motore non approvano automaticamente la fedeltà artistica finale.

## Provare la Yaris nel laboratorio

Aprire `project.godot` con Godot 4.5.1, attendere l'importazione e premere **F5**. Frecce/WASD per guidare, **Spazio** per frenare, **R** per ripristinare la prova. **C** alterna vista esterna, vista dell'albero/coffa e abitacolo; **O** apre/chiude le quattro portiere, **H** il portellone. L'apertura è consentita sotto 0,2 m/s. [Immagini del gioco e verifica riproducibile](reports/yaris_2022/LABORATORIO.md).

## Verifiche senza editor

Con Python 3.12, senza dipendenze per calcoli e regole:

```bash
python tools/check_project.py
```

Per GDScript installare `requirements-dev.txt` e lanciare `gdparse`, `gdformat --check` e `gdlint` sui file in `godot/scripts` e `godot/tests`. Il workflow GitHub replica i controlli; non pubblica release.

## Esperienza prevista

Partire da Faedis, salire verso Valle, parcheggiare in un prato lungo la strada sotto il paese, scendere e visitare il borgo a piedi; poi tornare all’auto e completare l’anello senza ribaltarsi. La passeggera deve risalire sulla coffa prima del ritorno.

Il territorio segue l’anello di circa 20 km mostrato dall’utente. Valle è la meta e riceve la maggiore fedeltà: disposizione degli esterni, chiesa, campanile, piazzetta, accessi e viste. Faedis e le località secondarie possono essere più generiche, con la stessa coerenza artistica.

## Vincoli confermati

- PC Linux e Windows, gioco nativo offline e singolo giocatore.
- Stile cartoonesco curato e fisica coerente per guida, carico alto e occupanti.
- Yaris Hybrid MY 2022 Trend italiana senza optional aggiuntivi; rosso mantenuto come richiesto.
- Topolini con proporzioni naturali della foto di riferimento: occhi grandi come unica deformazione anatomica.
- Mai allungare zampe o arti per raggiungere i comandi: seduta, appoggi e prolunghe meccaniche devono adattarsi ai personaggi.
- Locomozione a quattro zampe nella visita; la compagna segue il giocatore.
- Parcheggio candidato PV-01 osservato in via Prestento; punto esatto ancora da confermare.

## Documentazione

**LiDAR 0,5 m 2017–2020:** ricevute e verificate **tutte e quattro le tessere ellissoidiche** di Valle (`06701210`, `06701211`, `06701214`, `06701215`), 12.096.000 valori validi, nessuna lacuna, giunzioni identiche. Generati un mosaico GeoTIFF a 0,5 m e un GLB provvisorio a passo ~4 m; file consegnati nella conversazione e non pubblicati su GitHub. [Rapporto di acquisizione](docs/ACQUISIZIONE_LIDAR05_REALE_20261020.md) · [Tool di importazione](tools/import_valle_lidar05.py). La geometria stradale e il collaudo nel motore restano aperti.

**Sopralluogo cartografico (20/10/2026):** [pipeline QGIS + LiDAR FVG](docs/QGIS_LIDAR_SOPRALLUOGO.md), [acquisizione dei dati ufficiali](docs/ACQUISIZIONE_FONTI_GIS.md) e [rapporto sul circuito OSM candidato 2D](docs/TRACCIATO_OSM_CANDIDATO_20261020.md). Estratti 1.149 elementi stradali OSM, ricostruito un candidato planimetrico chiuso di **18.867,6 m** in sette settori, con dati e script versionati. **Non** sono ancora verificate le svolte reali, l'altimetria, la percorribilità o la mesh per il gioco.


| Documento | Contenuto |
| --- | --- |
| [Preparazione tecnica](docs/PREPARAZIONE_TECNICA.md) | Risultati verificati, approssimazioni e lacune |
| [Collaudo sul PC](docs/COLLAUDO_PC.md) | Primo import Godot, prove e generatori Blender |
| [Architettura](docs/ARCHITETTURA.md) | Responsabilità, coordinate e interfacce |
| [Mappa del sopralluogo](reports/valle_survey_map.svg) | Base OSM planimetrica, senza quote |
| [Progetto completo](docs/PROGETTO.md) | Direzione artistica, dinamica, animazioni, esplorazione, sviluppo e collaudi |
| [Roadmap](docs/ROADMAP.md) | Fasi, criteri di accettazione e attività ancora aperte |
| [Decisioni](docs/DECISIONI.md) | Richieste vincolanti e scelte progettuali da verificare |
| [Riferimenti e sopralluogo](docs/RIFERIMENTI_E_SOPRALLUOGO.md) | Riscontri del borgo, fonti, date e lacune |
| [Riferimenti dei topolini](references/README.md) | Anatomia e occhi, con provenienza dei due allegati |
| [Bianca e Bernie: catalogo](references/bianca_bernie/README.md) | 20 fonti originali/archivistiche e risorse secondarie, con link e priorità |
| [Specifica di modellazione](references/bianca_bernie/SPECIFICA_MODELLAZIONE.md) | Vincoli per Blender/Godot, rig, accessori e verifica del design |

## Stack proposto

Il progetto contiene `project.godot`, scene e sorgenti. Base verificata in questa consegna: **Godot 4.5.1 con Jolt integrato** e **Blender 4.5.3 LTS**. Non sono indicati come le versioni più recenti. QGIS rimane utile per terreno e trasformazioni di datum.

## Primo risultato da costruire

Il prossimo passaggio è collaudare equilibrio e guida, rifinire il modello auto confrontandolo con i riferimenti e integrare i protagonisti. Il primo campione artistico completo rimane l’arrivo a Valle con prato, parcheggio e passaggio all’esplorazione. Fonti e attribuzioni della cartografia sono in [NOTICE.md](NOTICE.md).

## Provenienza e distribuzione

Le fotografie esterne e i disegni Disney di Bianca e Bernie sono collegati nella documentazione, non inclusi come texture o asset del gioco. Gli allegati dell’utente restano riferimenti esterni alla repository pubblica; nella documentazione sono descritti i vincoli che fissano. Non è stata scelta una licenza di pubblicazione per il progetto.

