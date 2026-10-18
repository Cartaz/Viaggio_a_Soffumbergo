# Viaggio a Soffumbergo

## Coffa e tornanti

Una gita 3D cartoonesca a Valle di Soffumbergo: una Toyota Yaris Hybrid Trend MY 2022 rossa, un albero maestro con coffa e due topolini con anatomia naturale e occhi grandi.

**Stato: preparazione tecnica e sorgenti del laboratorio. Nessuna build giocabile o esecuzione in Godot/Blender ancora verificata.** Sono passati 28 test sui calcoli, sulle regole e sugli strumenti geografici; gli script GDScript superano parsing e lint. Il sopralluogo è parziale e non è stata misurata alcuna prestazione del gioco.

## Base tecnica disponibile

| Parte | Consegna | Limite della verifica |
| --- | --- | --- |
| Godot | Laboratorio con quattro sospensioni, pneumatici, trazione anteriore, carico alto, camera, HUD e CSV | Sorgenti controllati; esecuzione da collaudare |
| Calcoli | Masse, baricentro, tensore completo, aderenza combinata | Test Python, non ancora dinamica motore |
| Regole | Checkpoint ordinati, sosta, visita, ritorno e salvataggio atomico | Modello Python, da collegare alla scena 3D |
| Valle | 91 sagome OSM, inventario e mappa del sopralluogo | Dati mappati; quote, facciate e copertura da verificare |
| Blender | Generatori delle sagome di prova e delle guide del borgo | Sintassi Python; nessun modello finale già prodotto |
| Esplorazione | Controller di movimento e seguito della compagna | Richiedono rig, navmesh e integrazione nella scena |
| Percorso | Pipeline WGS84 → coordinate locali e superficie provvisoria | L’anello completo e il terreno non sono ancora acquisiti |

Il laboratorio è un piazzale sintetico con rampa e cerchio di riferimento: **non rappresenta Faedis o Valle**. I cubi sono segnaposto, non la Yaris fedele e i protagonisti definitivi.

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

## Stack proposto

Il progetto contiene ora `project.godot`, scene e sorgenti. Base API: **Godot 4.5.1 con Jolt integrato**, scelta riproducibile, non indicata come versione più recente né come compatibilità già provata. Generatori preparati per **Blender 4.5 LTS**. Prima verificheremo le versioni presenti sul PC. QGIS rimane utile per terreno e trasformazioni di datum.

## Primo risultato da costruire

Il prossimo passaggio è importare il laboratorio nel motore, collaudare equilibrio e guida e generare le sagome in Blender. Il primo campione artistico completo rimane l’arrivo a Valle con prato, parcheggio e passaggio all’esplorazione. Fonti e attribuzioni della cartografia sono in [NOTICE.md](NOTICE.md).

## Provenienza e distribuzione

Le fotografie esterne sono collegate nella documentazione, non incluse come texture o asset del gioco. Gli allegati dell’utente restano riferimenti esterni alla repository pubblica; nella documentazione sono descritti i vincoli che fissano. Non è stata scelta una licenza di pubblicazione per il progetto.

