# Terreno LiDAR e vegetazione procedurale

## Decisione attiva — 22 ottobre 2026

Unreal Engine 5.8 è il motore scelto, con installazione 5.8.4 verificata. L'utente richiede strumenti procedurali Unreal per terreno e vegetazione, sempre vincolati ai rilievi LiDAR. Questa richiesta supera il precedente stato di solo confronto con Godot.

## Terreno

Decisione del 23 ottobre: **Street View fa fede al 100% per gli elementi antropici, anche con immagini di età diverse**. Strade, muri, guardrail, ponti, edifici e accessi visibili costituiscono il riferimento da ricostruire. La sola data della fotografia non invalida l'elemento; quando più viste mostrano un cambiamento effettivo, si usa lo stato più recente visibile. Il terreno DTM non deve cancellare, sostituire con terra o contraddire una struttura osservata. Le quote del suolo restano basate sul LiDAR e le dimensioni costruttive non misurate sono dichiarate di progetto.

Il primo incremento usa Landscape, che espone la superficie al sistema PCG e mantiene la scala metrica. Non si inventa la forma della valle con rumore procedurale. La costruzione è automatizzata dal raster reale, con conversione delle quote e suddivisione compatibile con Landscape.

Sorgente iniziale: `C:\Giochi\Sviluppo\Viaggio a Soffumbergo\DTM Completi\Ell_DTM_06701210.asc`. Nella cartella delle fonti sono disponibili ulteriori tessere; questo incremento non afferma di averle validate o importate tutte. Il primo ritaglio usa righe 1000–1504 e colonne 900–1404, con indici da zero. 8×8 componenti da 63 quadrilateri, una sezione per componente, passo originale 0,5 m. Nessun ricampionamento per adattare le dimensioni.

Coordinate planimetriche conservate secondo la provenienza EPSG:6708; quote ellissoidiche conservate. Assi Unreal: X est, Y sud, Z alto; centimetri. La prima cella è un centro di campione, non il bordo della tessera. Il manifesto mantiene l'origine E/N/H e la formula di ricostruzione. La conversione al formato R16 introduce soltanto la quantizzazione misurata, senza lisciare il rilievo.

La zona estesa è ora importata in 113 livelli Landscape con level streaming nativo; la precedente ipotesi World Partition non è l'implementazione attuale. Rilettura completa, maschere NoData, collisioni e caricamento diagnostico sono verificati: [Territorio completo](TERRITORIO_COMPLETO.md). Strade e sentieri useranno vincoli documentati; eventuali correzioni del terreno vanno su livelli separati e motivate. I punti ignoti non diventano falsi dati rilevati.

**Paesaggio lontano,24ottobresera:** individuato rilievo LiDAR noto oltre l'inviluppo dei livelli dettagliati. Preparata una rappresentazione adattiva di tutti113settori,156d5c3b983b:3.741.068triangoli, circa98,12%inmeno dei quadrilateri nativi validi. Passano audit indipendente di dominio/bordi e14.964.272sonde interne. Nessuna extrapolazione di quote; Landscape vicini e fisica conservati. Aggiornamento 25 ottobre: ora integrati nella candidata e37 e verificati senza rendering in Editor e Windows, con giri completi. La resa grafica resta da approvare. Metodo, tentativi respinti e limiti in [Paesaggio lontano](PAESAGGIO_LONTANO.md).

## Vegetazione

**24 ottobre, sera:** maschere dell'intero territorio (113 settori) e PCG nativo completati sulla candidata separata **9811cad1439f**: 593.327 piante salvate e ricaricate in 110 settori, tre intenzionalmente vuoti. Audit indipendente di tutte le istanze passato, con copertura OSM, NoData ed esclusioni comprensive delle chiome. Passano scansione completa, giro fisico Editor corrente di 18,86 km senza recuperi e sette prove locali 4K/60. Tutte 21 le immagini sono viste; aspetto definitivo del terreno/vegetazione, contesto lontano e camere restano da rifinire. Stato e limiti in [Vegetazione del territorio](VEGETAZIONE_TERRITORIO.md). Il trattamento locale roccia/muschio di Costalunga è in una variante separata. La prima prova252m sotto resta storica; il gioco Windows attivo non è ancora aggiornato con questo PCG esteso.

PCG campiona il terreno LiDAR e userà pendenza, quota e maschere di copertura/esclusione. Il seed è esplicito e salvato. Si distinguono copertura forestale osservata, posizione degli alberi effettivamente misurata e distribuzione plausibile generata.

Il DTM è terreno nudo. Se verranno reperiti DSM/nuvole LAS-LAZ con ritorni vegetazione e metadati coerenti, si potranno ricavare altezze e copertura della chioma dal confronto con il DTM. Le specie non si desumono automaticamente dal solo rilievo altimetrico. Senza questi dati aggiuntivi, le maschere dipenderanno da ortofoto/copertura del suolo o sopralluoghi verificati.

Esclusioni previste: carreggiate con banchine documentate, impronte del borgo, ingressi e percorsi pedonali, prato candidato e corridoi di gameplay. Le distanze di rispetto sono parametri di progetto da verificare, non misure inventate del luogo.

Il grafo iniziale di campionamento è conservato. L'incremento successivo ha aggiunto `/Game/Procedural/PCG_ValleVegetazione`: tre rami di campionamento, filtro nativo della maschera e della pendenza, variazione deterministica e spawner delle mesh originali generate dentro Unreal. Generazione e limiti effettivamente verificati sono in [Sviluppo Unreal](SVILUPPO_UNREAL.md). Il Procedural Vegetation Editor rimane un'alternativa per l'authoring botanico; nella documentazione Epic 5.8 è sperimentale e non è una dipendenza necessaria per questa distribuzione con PCG.

## Verifiche aperte

- Controllare quote e collisioni del nuovo Landscape con campioni geografici e raggi nel motore; il vecchio import OBJ non aveva superato il controllo delle collisioni.
- Verificare bordi del mosaico, copertura completa e tracciato stradale distinto dal suolo LiDAR.
- Collegare dati di copertura ed esclusioni al grafo PCG, senza vegetazione su strada o accessi.
- Verificare rigenerazione identica a parità di seed, versioni dei dati e impostazioni.
- Confermare stile di realismo fiabesco e riconoscibilità del borgo con una scena rappresentativa.
- Misurare 4K/60 sulla RX 6800 in build Windows, includendo bosco, vista lunga e borgo. Nessun risultato del banco sintetico chiude questo punto.

## Fonti tecniche

- [Importazione heightmap Landscape, Epic](https://dev.epicgames.com/documentation/unreal-engine/importing-and-exporting-landscape-heightmaps-in-unreal-engine).
- [PCG Framework, Epic](https://dev.epicgames.com/documentation/unreal-engine/procedural-content-generation-overview?lang=en-US).
- [Procedural Vegetation Editor 5.8, Epic](https://dev.epicgames.com/documentation/unreal-engine/procedural-vegetation-editor-pve-in-unreal-engine).
