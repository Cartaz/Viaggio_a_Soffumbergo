# Viaggio a Soffumbergo

## Coffa e tornanti

Una gita 3D cartoonesca a Valle di Soffumbergo: una Toyota Yaris Hybrid Trend MY 2022 rossa, un albero maestro con coffa e due topolini con anatomia naturale e occhi grandi.

**Stato: progettazione. Non esiste ancora una build giocabile.** Il sopralluogo è parziale e non è stata misurata alcuna prestazione del gioco.

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
| [Progetto completo](docs/PROGETTO.md) | Direzione artistica, dinamica, animazioni, esplorazione, sviluppo e collaudi |
| [Roadmap](docs/ROADMAP.md) | Fasi, criteri di accettazione e attività ancora aperte |
| [Decisioni](docs/DECISIONI.md) | Richieste vincolanti e scelte progettuali da verificare |
| [Riferimenti e sopralluogo](docs/RIFERIMENTI_E_SOPRALLUOGO.md) | Riscontri del borgo, fonti, date e lacune |
| [Riferimenti dei topolini](references/README.md) | Anatomia e occhi, con provenienza dei due allegati |

## Stack proposto

Godot 4 con versione stabile da fissare all’avvio dello sviluppo, Jolt, Blender e QGIS. La dinamica automobilistica sarà dedicata: non è già implementata. Il progetto non contiene ancora project.godot, scene o script eseguibili.

## Primo risultato da costruire

Laboratorio fisico con telaio, quattro ruote e carico alto; in parallelo logico, prova di sagoma dei topolini sul sedile senza stiramento degli arti. Nessuna necessità di assegnare il lavoro a più agenti. Il primo campione artistico completo sarà l’arrivo a Valle con prato, parcheggio e passaggio all’esplorazione.

## Provenienza e distribuzione

Le fotografie esterne sono collegate nella documentazione, non incluse come texture o asset del gioco. Gli allegati dell’utente restano riferimenti esterni alla repository pubblica; nella documentazione sono descritti i vincoli che fissano. Non è stata scelta una licenza di pubblicazione per il progetto.

