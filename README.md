# Viaggio a Soffumbergo

## Coffa e tornanti

Una gita 3D cartoonesca a Valle di Soffumbergo: una Toyota Yaris Hybrid Trend MY 2022 rossa, un albero maestro con coffa e due topolini ispirati a Bianca e Bernie Disney. La direzione aggiornata comprende corporatura, volti e costumi: Bernie compatto al volante, Bianca più affusolata come vedetta. La postura bipede è ora autorizzata dall’utente.

**Stato: laboratorio con personaggi riggati e reazioni animate al movimento fisico. Bernie guida e Bianca si tiene agli appigli della coffa; test delle prese, degli arti e della mantellina eseguiti in Godot 4.5.1. Nessuna build giocabile completa del viaggio.** Sono passati 28 test sui calcoli, sulle regole e sugli strumenti geografici; gli script GDScript superano parsing e lint. Il sopralluogo è parziale e non è stata misurata alcuna prestazione del gioco.

## Base tecnica disponibile

| Parte | Consegna | Limite della verifica |
| --- | --- | --- |
| Godot | Laboratorio con quattro sospensioni, pneumatici, trazione anteriore, carico alto, camera, HUD e CSV | Eseguito con Jolt e renderer per le animazioni; dinamica completa da collaudare |
| Calcoli | Masse, baricentro, tensore completo, aderenza combinata | Test Python, non ancora dinamica motore |
| Regole | Checkpoint ordinati, sosta, visita, ritorno e salvataggio atomico | Modello Python, da collegare alla scena 3D |
| Valle | 91 sagome OSM, inventario e mappa del sopralluogo | Dati mappati; quote, facciate e copertura da verificare |
| Blender | Due modelli vestiti, GLB e generatore riproducibile; guide del borgo | Rig con 35 ossa per personaggio e anteprima animata; cammino ed esplorazione ancora da realizzare |
| Esplorazione | Controller di movimento e seguito della compagna | Richiedono rig, navmesh e integrazione nella scena |
| Percorso | Pipeline WGS84 → coordinate locali e superficie provvisoria | L’anello completo e il terreno non sono ancora acquisiti |

Il laboratorio è un piazzale sintetico con rampa e cerchio di riferimento: **non rappresenta Faedis o Valle**. La vettura resta un segnaposto; i protagonisti hanno rig e animazioni di guida/tenuta, con fitting finale dell’abitacolo e locomozione ancora aperti.

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
- Topolini con corporature distinte dagli studi di animazione: Bianca affusolata e Bernie compatto; occhi espressivi, zampe e coda da topo.
- Mai allungare zampe o arti per raggiungere i comandi: seduta, appoggi e prolunghe meccaniche devono adattarsi ai personaggi.
- Locomozione bipede autorizzata; le animazioni di cammino restano da realizzare. La compagna segue il giocatore.
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
| [Bianca e Bernie: catalogo](references/bianca_bernie/README.md) | 20 fonti originali/archivistiche e risorse secondarie, con link e priorità |
| [Specifica di modellazione](references/bianca_bernie/SPECIFICA_MODELLAZIONE.md) | Vincoli per Blender/Godot, rig, accessori e verifica del design |

## Stack proposto

Il progetto contiene ora `project.godot`, scene e sorgenti. Base API: **Godot 4.5.1 con Jolt integrato**, scelta riproducibile, non indicata come versione più recente né come compatibilità già provata. Generatori preparati per **Blender 4.5 LTS**. Prima verificheremo le versioni presenti sul PC. QGIS rimane utile per terreno e trasformazioni di datum.

## Primo risultato da costruire

I modelli sono in `godot/assets/characters/`; viste e istruzioni sono in [Personaggi](docs/PERSONAGGI.md). Guida e tenuta della coffa sono animate; cammino, salita e fitting finale dell’abitacolo restano aperti; equilibrio e guida richiedono ancora il collaudo previsto. Il primo campione artistico completo rimane l’arrivo a Valle con prato, parcheggio e passaggio all’esplorazione. Fonti e attribuzioni della cartografia sono in [NOTICE.md](NOTICE.md).

## Provenienza e distribuzione

Le fotografie esterne e i disegni Disney di Bianca e Bernie sono collegati nella documentazione, non inclusi come texture o asset del gioco. Gli allegati dell’utente restano riferimenti esterni alla repository pubblica; nella documentazione sono descritti i vincoli che fissano. Non è stata scelta una licenza di pubblicazione per il progetto.


## Animazioni collegate alla fisica

Vedere [ANIMAZIONI.md](docs/ANIMAZIONI.md) per pose, supporti adattati, mantellina, test e riproduzione dell’anteprima. Le reazioni usano accelerazioni lineari e angolari reali, non oscillazioni periodiche.
