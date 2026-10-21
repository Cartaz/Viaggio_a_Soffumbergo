# Terraforming e costruzione del circuito — 21 ottobre 2026

Prima base di costruzione dell'intero candidato A/B/C/V/D/E/F: una superficie
continua di progetto e un terreno sistemato separato dal DTM originale. La scena
è un banco di ispezione con collisioni, non una certificazione del percorso o un
giro già percorso con la Yaris. Le scene precedenti di guida, sosta e visita
rimangono disponibili.

## Aprire e confrontare

Nella copia Windows usare **Avvia costruzione circuito.cmd**. Nella copia sorgente
aprire `godot/scenes/circuit_construction.tscn` e premere F6 dopo la generazione.
F5 conserva il laboratorio e le impostazioni locali.

| Comando | Effetto |
| --- | --- |
| T | Alterna DTM originale e terreno di progetto; rimuove/ripristina anche la collisione stradale |
| F1…F7 | Richiama A/B/C/V/D/E/F; F4 porta a Valle |
| F9 | Passa alla successiva curva, inversione o sistemazione del terreno da rivedere |
| M | Inquadra tutto l'anello |
| WASD, Q/E, Maiusc, mouse destro | Muove, alza/abbassa, accelera e orienta la camera |
| 1, 2, F8 | Asse candidato, sagome OSM, dati del caricamento |

Ambra = superficie progettata provvisoria. Rosso = punto da verificare. Le sagome
OSM sono segnaposto. Nessuna modifica ai rig, ai modelli approvati o agli otto
esercizi della copia Windows. Questa scena non contiene l'auto: prima della guida
dell'anello servono la revisione delle inversioni e dei raccordi ai bivi.

## Parametri e rigenerazione

Modificare `data/config/circuit_construction.json`, poi eseguire dalla radice:

```powershell
python -m pip install -r requirements-dev.txt
python tools/build_circuit_construction.py
python tools/check_circuit_construction.py
```

Richiede il corridoio già generato in `build/circuit/manifest.json`; la relativa
procedura è in [CIRCUITO_3D.md](CIRCUITO_3D.md). Per il collaudo completo:

```powershell
python tools/validate_circuit_construction.py --godot <Godot.exe> --blender <Blender.exe> --input-dir "C:\Giochi\Sviluppo\Viaggio a Soffumbergo\DTM Completi" --capture
python tools/sync_circuit_construction_local.py --target "C:\Giochi\Sviluppo\Viaggio a Soffumbergo" --godot <Godot.exe>
```

Il sincronizzatore controlla tutte le destinazioni prima di scrivere, preserva
modifiche sconosciute, conserva backup degli aggiornamenti di propria competenza
e registra una ricevuta. Non sostituisce `project.godot`, modelli, personaggi,
README o roadmap privati. Per rigenerare nella copia Windows installare anche
Shapely 2.1.2 nell'interprete Python usato: il visualizzatore Godot non lo richiede.

Parametri iniziali **non misurati sul posto**: larghezza 4,5 m, pendenza trasversale
nulla, adattamento verticale con regressione locale su 12 m e rialzo 0,15 m,
terreno 0,5 m sotto la quota di progetto, banchina 1 m e raccordo al DTM su 8 m.
La sezione attuale non comprende una banchina stradale con collisione separata,
drenaggi, barriere, muri di sostegno o bilanciamento reale dei materiali.

Il profilo usa la distanza lungo l'asse chiuso, conserva tutte le X/Z e unifica
le quote progettate dei nodi ripercorsi. Il DTM rimane immutato. La ricerca dei
segmenti usa un indice spaziale e non media tra rami vicini di un tornante.
L'unione planimetrica della fascia evita superfici duplicate sui tratti ripercorsi;
la triangolazione vincolata conserva i vuoti interni. Suddivisioni conformi e
confini identici evitano tagli automatici e fessure fra settori stradali.
L'unione ai bivi è un'ipotesi geometrica, non il rilievo dell'incrocio.

## Risultato e limiti

L'asse proiettato EPSG:6708 misura **18.884,86 m orizzontali**; il profilo di
progetto misura 18.938,56 m in 3D. Il dato storico 18.867,6 m nel GeoJSON è una
stima planimetrica precedente: qui si riporta la misura della geometria metrica
effettivamente usata, senza cambiare il candidato. Restano 9.959 stazioni distinte
in sequenza, più il punto di chiusura; 225 posizioni vengono ripercorse.

Il terreno completo conserva 352 settori con LOD 2/4/8 m e collisioni a 2 m.
La variante modifica 188 settori, comprese le normali prossime ai raccordi;
la strada ha 167 settori e 208.994 triangoli. Le sue collisioni sul layer 4
nascono e vengono eliminate insieme al terreno residente. Il confronto T
ricostruisce anche la vista generale: non è una semplice variazione di colore.

Il profilo arriva a una pendenza progettata del 19,93%, con scarto massimo
di 2,61 m dall'asse DTM. Scavo/riporto massimo sul terreno **8,74 m**: da rivedere
prima di rifinire scarpate e muri. Le stime di volume su celle da 2 m sono circa
162.277 m³ di scavo e 60.870 m³ di riporto; non sono un computo lavori né un
bilancio geotecnico. F9 segnala anche i settori con modifiche oltre 6 m.

Sono conservate **quattro inversioni esatte**, due in A, una in V e una al
passaggio E/F. La superficie arrotonda solo la fascia di larghezza ipotetica;
non inventa piazzali sufficienti alla manovra della Yaris. Prima di dichiarare
guidabile l'intero anello bisogna verificare questi punti, i bivi, la sezione
reale, i dislivelli, i muri e il raccordo al prato. PV-01 resta candidato.

## Prove e file locali

Il gate verifica 100 test Python, tutti i GDScript, due generazioni identiche,
impronte dei 41 ASC prima/dopo e invariabilità dei manifest originali/pilota/sosta.
Controlla 562 giunzioni del terreno, quote e normali, e 191 della strada;
controlla area, fronti, lunghezza dei lati e copertura dell'asse e delle due
sezioni laterali su 29.877 punti. Godot/Jolt confronta le collisioni con una
interpolazione indipendente dei triangoli; prova inoltre caricamento/scaricamento,
confronto T, caduta di un corpo e inquadratura dell'anello. Non è un test di giro
completo o un benchmark FPS. Blender salva e verifica tutte le superfici stradali
e la vista generale del terreno. [Evidenze](../reports/COSTRUZIONE_CIRCUITO_VERIFICA.json).

- `build/circuit/construction_manifest.json`: terreno variante, superficie e punti critici.
- `build/circuit/construction_report.json`: parametri, quantità indicative e provenienza.
- `build/construction_validation/`: log, riferimenti, immagini e risultati dei collaudi.
- `build/construction_validation/circuit_construction.blend`: progetto Blender locale.

Originali e derivati geografici restano esclusi da Git. Non si risolve il datum
verticale o il diritto di redistribuzione tramite una lavorazione del terreno.
Nessuna nuova licenza o release. Le API di unione e triangolazione usate sono
documentate da [Shapely](https://shapely.readthedocs.io/en/2.1.2/reference/shapely.constrained_delaunay_triangles.html).

Prossima lavorazione: risolvere le quattro inversioni mantenendo l'itinerario
documentato, quindi rifinire sezioni, tornanti e opere del fondo prima del
collaudo della Yaris per settori. Restano separati parcheggio e accesso pedonale.
