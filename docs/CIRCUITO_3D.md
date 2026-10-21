# Circuito 3D 0.1 — corridoio del terreno

20 ottobre 2026. Scena di ispezione dell'intero candidato OSM A/B/C/V/D/E/F,
nel medesimo frame di Valle 3D 0.1: X est, Y alto, Z sud, origine ENH
375920 / 5112728 / 720 m. Non è una strada asfaltata o un giro guidabile.

## Consegna

- **352 settori di 128 m**, selezionati attorno all'asse OSM con semilarghezza
  grafica 96 m, più il quadrato di Valle già collaudato. Il campionamento
  conservativo della selezione aggiunge 1 m e arrotonda a settori interi:
  non è una larghezza stradale rilevata o un corridoio uniforme di 192 m.
- Griglia fisica a **2 m** e LOD visivi a 2/4/8 m; veduta generale a 8 m.
  Nessun vertice senza copertura nel corridoio prodotto. I campioni mancanti
  in altri input restano `null`: il generatore di mesh omette quei triangoli.
- **562 giunzioni** con quote, normali e ID della fonte identici. Le gonne
  visive coprono il passaggio fra LOD; non generano muri nelle collisioni.
- Le quote dei **36 settori di Valle coincidono esattamente** con Valle 3D 0.1.
  Le 91 sagome OSM e le linee provvisorie usano lo stesso costruttore condiviso.
- Tutti i **9.966 punti** dell'asse candidato sono stati confrontati con Jolt
  mentre la camera attraversava l'anello, con collisioni caricate/scaricate.
  I rapporti riportano errore massimo, numero di controlli e residenza misurata.

## Politica esplicita delle sovrapposizioni

La scelta riguarda la rappresentazione del prototipo, non corregge i dati o
risolve quale quota sia scientificamente più accurata. A ogni coordinata:

1. Si considerano soltanto tessere valide sui centri delle celle; niente
   estrapolazione e nessun riempimento dei NoData.
2. Nel quadrato di Valle hanno priorità le quattro tessere originali verificate.
3. Fra le candidate rimaste si sceglie quella con **maggiore distanza dal
   bordo più vicino**. A parità prevale il nome file in ordine alfabetico.
4. Si interpola soltanto all'interno della tessera scelta, senza medie o
   fusione fra fonti. Ogni vertice conserva l'indice della tessera e il manifest
   la relativa impronta SHA256. Le differenze fra tutte le candidate sono registrate.

È una regola globale, indipendente dall'ordine di lettura e dal settore della
mesh: lo stesso punto riceve la stessa fonte su entrambi i lati di una giunzione.
Le quattro tessere primarie non vengono alterate. I 24 punti precedentemente
ambigui del candidato hanno ora una fonte scelta **esplicita**, conservando lo
scarto fra le fonti; la vecchia acquisizione rimane un rapporto storico corretto.

Gli originali sono verificati contro le 41 SHA256 del catalogo a ogni generazione.
Le quote sono ellissoidiche come dichiarato dalla raccolta `Ell_DTM`, senza
conversione verticale. La verifica indipendente dei metadati resta aperta.

## Caricamento a settori

Il manifest contiene la vista generale dell'anello. I file dei settori a 2 m
si caricano entro 384 m dalla camera, si scaricano oltre 512 m e hanno collisioni
fisse indipendenti dal LOD. La veduta generale non ha collisioni. L'isteresi evita
caricamenti ripetuti sullo stesso bordo; i file vengono controllati con SHA256
prima dell'uso. Una generazione completa viene pubblicata localmente con
sostituzione atomica del manifest; non si mescolano chunk di due generazioni.

Il budget di caricamento di 8 ms è un obiettivo fra due chunk: un singolo chunk
non è interrompibile e può superarlo. Le misure reali sono nel rapporto; non è
un benchmark FPS rappresentativo. Rispetto alla griglia a 2 m, errore massimo
dei LOD del corridoio: **9,06625 m a 4 m**, **13,7075 m a 8 m**, soprattutto su
rilievi ripidi. Il dettaglio lontano e le gonne sono approssimazioni visive;
la fisica vicina rimane sulla griglia a 2 m. Anche questa griglia decima il
raster originario a 0,5 m e non conserva ogni gradino, muro o dettaglio del suolo.

L'asse ambra è una sovrapposizione grafica sempre leggibile, non una superficie
fisica. Larghezze dell'asfalto, banchine, muri, pendenze trasversali e bivi reali
rimangono da verificare prima della guida. Edifici e accessi restano blockout.

## Rigenerazione e avvio

Dipendenze in `requirements-terrain.txt` e `requirements-dev.txt`. Occorre prima
il derivato locale `build/valle/valle_scene.json`; vedere [VALLE_3D.md](VALLE_3D.md).
Nella copia Windows lo ZIP sorgente di Valle è conservato privatamente sotto
`build/geodata/fvg/`. I 41 originali sono nella cartella `DTM Completi`.

```powershell
python tools/build_circuit_3d.py --input-dir "C:\Giochi\Sviluppo\Viaggio a Soffumbergo\DTM Completi"
python tools/check_circuit_3d.py build/circuit/manifest.json --input-dir "C:\Giochi\Sviluppo\Viaggio a Soffumbergo\DTM Completi"
godot --path . res://godot/scenes/circuit.tscn
```

Oppure usare F6 sulla scena o `Avvia circuito 3D.cmd` nella copia Windows.
WASD/Q/E muovono la camera, Maiusc accelera, tasto destro controlla lo sguardo.
R torna a Valle, M mostra l'anello, F1–F7 richiamano A/B/C/V/D/E/F; 1 e 2
alternano linee ed edifici, F8 mostra i dati di collaudo. F5 e il laboratorio
auto rimangono invariati. La camera è libera e può attraversare il terreno.

## Verifiche riproducibili

```powershell
python tools/validate_circuit.py --godot "C:\strumenti\godot_console.exe" --blender "C:\strumenti\blender.exe" --input-dir "C:\Giochi\Sviluppo\Viaggio a Soffumbergo\DTM Completi" --capture
```

Il runner esegue test Python, regressione Yaris, parser/formattazione/lint,
due generazioni identiche, confronti geometrici, 3.168 campioni scalari indipendenti
dai raster, import e prove Godot, regressione Valle, prova NoData, attraversamento
di tutti i punti del candidato, verifica della liberazione dei corpi fisici,
caduta reale e modalità senza dati. Gli errori nei log fanno fallire il gate.
Con `--capture` salva tre viste dal renderer reale. Blender valida le mesh e le
normali della veduta generale (8 m), le 91 sagome e salva il progetto nativo.

Output locali: `build/circuit/`, log e risultati in `build/circuit_validation/`.
Sintesi pubblica: [CIRCUITO_3D_VERIFICA.json](../reports/CIRCUITO_3D_VERIFICA.json).
Raster, chunk, profili, immagini e `.blend` restano fuori Git in attesa della
verifica dei termini di redistribuzione. OSM © OpenStreetMap contributors,
[ODbL](https://www.openstreetmap.org/copyright); fonte DTM e metadati in
[DTM_CIRCUITO_COMPLETO.md](DTM_CIRCUITO_COMPLETO.md).
