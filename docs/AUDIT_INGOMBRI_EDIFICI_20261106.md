# Audit degli ingombri Yaris-edifici — 6 novembre 2026

## Scopo e fonte della prova

Verificare su CPU anche il **tratto compreso tra due pose fisiche registrate**, non solo l'istante del campione, senza modificare terreno, strada, asset, fisica o build Unreal. Il rapporto originale è:

`results/building_context/f437_actual_chassis_clearance_20261025_v1/report.json`

L'input è la telemetria autentica del giro Windows **headless NullRHI** della candidata `f4373a62b482`, non il pacchetto attivo `4a05593a4282`. L'eseguibile Windows è identificato dal SHA-256:

`9f8eab7584d77fcf13907a5b00938ceb934d282ee96fef7e60c8d5fdf05ee2b2`

La geometria del telaio, 3,80 × 1,68 × 0,75 m, proviene dall'implementazione C++ già registrata dall'audit precedente. Sono utilizzate le impronte di **2.865 edifici** ricavate da dati OpenStreetMap, mantenendo la deduplicazione delle relazioni OSM. Non vengono assunte come misure catastali o come sagome 3D effettive.

## Implementazione

`tools/audit_swept_building_clearance.py` confronta il volume del telaio *proiettato sul piano* agli estremi di ciascun intervallo e costruisce l'inviluppo convesso della traslazione, maggiorato di un margine per la rotazione interpolata. Il margine geometrico è:

\[
\Delta = r \left(1-\cos(\theta/2)\right)
\]

dove `r` è la distanza massima di un vertice del telaio dal riferimento e `θ` è l'angolo relativo delle orientazioni registrate. L'inviluppo così costruito è prudente **soltanto rispetto all'interpolazione lineare del centro e alla rotazione sull'arco minimo**; non delimita tutti i movimenti non campionati possibili.

I controlli di discontinuità saltano esplicitamente intervalli con durata oltre 0,2 s, spostamento oltre 2 m o variazione angolare oltre 25°. Si usa un indice spaziale STRtree per il confronto con le impronte mappate. La procedura controlla le impronte SHA-256 degli input del precedente audit e rifiuta di sovrascrivere un rapporto già presente.

## Esecuzione realmente completata

Comando locale, nella cartella unificata `C:\Giochi\Sviluppo\Viaggio a Soffumbergo Unreal`:

```powershell
.\.venv\Scripts\python.exe tools\audit_swept_building_clearance.py --prior-report results\building_context\f437_actual_chassis_clearance_20261025_v1\report.json --output results\building_context\f437_swept_chassis_20261106_v1
```

**Esito 6 novembre 2026 — codice di uscita 0:**

| Controllo | Risultato |
| --- | ---: |
| Pose sorgente | 105.215 |
| Intervalli consecutivi | 105.214 |
| Intervalli verificati con le soglie definite | 105.214 |
| Intervalli esclusi | 0 |
| Intervalli con area positiva di sovrapposizione | 57 |
| Edifici OSM interessati | 3 |
| Nuovi edifici rispetto all'audit per pose | 0 |

| Impronta OSM | Intervalli interessati | Massimo sovrapposto sul piano |
| --- | ---: | ---: |
| [way/36158227](https://www.openstreetmap.org/way/36158227) | 23 | 0,432193 m² |
| [way/36158219](https://www.openstreetmap.org/way/36158219) | 31 | 0,060389 m² |
| [way/36162093](https://www.openstreetmap.org/way/36162093) | 3 | 0,000317 m² |

L'audit precedente, basato sulle singole pose, riportava rispettivamente 0,425229, 0,057854 e 0,000225 m² e un totale di 54 pose interessate. **Le 57 unità del nuovo rapporto sono intervalli**, non pose; i due conteggi non vanno confrontati come se avessero la stessa unità.

I file di risultato sono conservati **solo in locale**:
- `results/building_context/f437_swept_chassis_20261106_v1/report.json`
- `results/building_context/f437_swept_chassis_20261106_v1/swept_plan_overlaps.csv`

Sono stati eseguiti cinque test sintetici in `tests/test_audit_swept_building_clearance.py`, tutti superati, su passaggio tra due campioni, assenza di contatti lontani, gestione dei salti, rotazione e invarianti della telemetria. Passa `python -m compileall -q tools tests`.

## Priorità operative e limiti

1. **Via Mont Joanes, OSM 36158227:** verifica geometrica e riscontri visivi su bordo strada, spigolo dell'edificio, muri, eventuali sottopassi, roof overhang e corrispondenza fra OSM e terreno. È il conflitto quantitativamente maggiore. Non spostare l'edificio o la strada senza osservazioni adeguate.
2. **Via Mont Joanes, OSM 36158219:** secondo caso nello stesso corridoio, più piccolo ma non nullo; verificare unitamente al precedente.
3. **OSM 36162093:** sovrapposizione di circa 3,17 cm², prossima a una situazione di contatto limite; il dato non prova un ostacolo reale e richiede solo una verifica mirata.

Un'area 2D positiva **non dimostra una collisione reale**: le altezze e i portici, la pendenza, la vegetazione, le recinzioni, i tetti, l'incertezza dei poligoni OSM e le vere collisioni dei mesh Unreal non sono verificate qui. Il tool non aggiunge asset né modifica la fisica della Yaris o la mappa. Il loop Windows con rendering 4K/60 FPS completo resta non collaudato; evitare di dedurre prestazioni da questi risultati.

### Riproducibilità

Per eseguire nuovamente, scegliere **una nuova cartella di output**, conservare invariati gli input originali e usare l'ambiente Python locale con NumPy, Shapely e pyproj. Il solo checkout pubblico GitHub non contiene la telemetria, i dati di edifici completi e il pacchetto Unreal necessari a replicare il report reale. I test sintetici, invece, sono eseguibili con `python -m unittest discover -s tests -v` dopo aver installato `requirements-tools.txt`.

**Attribuzione cartografica:** © OpenStreetMap contributors, ODbL 1.0. Nessuna fotografia Street View o texture di terzi è stata copiata.
