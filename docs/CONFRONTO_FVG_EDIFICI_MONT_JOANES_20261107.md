# Confronto cartografico regionale — Via Mont Joanes, 7 novembre 2026

## Decisione operativa

**Nessuna modifica automatica alla strada, agli edifici o alle collisioni.** Sono stati reperiti e confrontati i livelli ufficiali degli edifici della Regione Autonoma Friuli Venezia Giulia con le sagome OSM, il vero asfalto triangolato della candidata Unreal `f4373a62b482` e la telemetria fisica Windows precedentemente registrata. Sono emerse **cinque impronte regionali** potenzialmente attraversate, contro le **tre impronte OSM** del precedente audit complessivo; il servizio regionale scaricato copre **soltanto 240 × 240 metri** intorno a Via Mont Joanes.

L'attuale progetto giocabile è ancora il pacchetto **`4a05593a4282`**. La candidata `f4373a62b482` è **separata e non attiva**, e un test sorgente/planimetrico non dimostra né prestazioni 4K né collisioni di pareti in Unreal.

## Fonti verificate

La Regione FVG documenta che il **DBTsped** è stato ricavato dalla digitalizzazione semiautomatica delle **Trueortofoto 2017–2020**. Il livello `DBS_EDIFICATO` nel WFS regionale riporta esplicitamente questa provenienza nel campo Abstract del GetCapabilities. Gli altri livelli sono due edizioni della **Carta Tecnica Regionale Numerica**: carte vettoriali storiche che possono essere state riutilizzate nelle stesse geometrie. Non sono tre rilievi di parete indipendenti.

- **Servizio ufficiale:** [FVG EDIFICI WFS, GetCapabilities](https://serviziogc.regione.fvg.it/geoserver/EDIFICI/ows?service=WFS&version=2.0.0&request=GetCapabilities)
- **Metodologia:** [Regione FVG — DBTfvg e DBTsped](https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA4/FOGLIA3/)
- **Basi disponibili e condizioni di riuso:** [Regione FVG — Basi cartografiche](https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA4/)
- **OSM:** © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright).
- **Quote:** [Catalogo regionale dei modelli altimetrici DTM, DSM, DBM 0,5 m](https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826).

I tre download sono avvenuti il **7 novembre 2026** via **WFS 1.0.0 GetFeature**, con `bbox` in coordinate regionali **EPSG:6708 (RDN2008/TM33)**. Non inviare il bbox in latitudine/longitudine senza reproiezione: con WFS nativo il risultato apparirebbe falsamente vuoto.

- Centro query: longitudine **13.360700**, latitudine **46.167350**;
- Coordinate regionali del centro: E **373449,112**, N **5113947,623** m;
- Raggio: 120 m, riquadro 240 × 240 m;
- `DBS_EDIFICATO`: **62 poligoni**, `EDIFICATO_CTRN_ED1_067`: **64**, `EDIFICATO_CTRN_ED2_067`: **76**;
- ogni file ha hash SHA-256, conteggio/CRS verificato, URL e data nel manifesto locale.

**Dati grezzi lasciati locali** in `results/fvg_official_buildings/mont_joanes_20261107_v1/` (manifesto più 3 GeoJSON). Il servizio regionale è ufficiale ma la precisione delle impronte e l'anno esatto di ogni fabbricato sono informazioni distinte dalla disponibilità del layer. Non attribuire una licenza generalizzata agli asset del gioco: i dati regionali sono regolati dalle loro condizioni di distribuzione, mentre OSM resta sotto ODbL. La repository pubblica contiene **solo strumenti, statistiche documentate e tavole derivate attribuite**, non l'estratto WFS completo.

## Verifica completa della telemetria disponibile, limitata al riquadro

Sono stati esaminati tutti i **105.214 intervalli** consecutivi delle **105.215 pose** del giro fisico Windows `f4373a62b482`, ciascuno per mezzo del precedente inviluppo planimetrico del telaio di 3,8 × 1,68 × 0,75 m. **Nessun salto** nella telemetria rispetto alle soglie previste. Il test considera **solo** le impronte edilizie delle tre sorgenti regionali recuperate nel riquadro Mont Joanes, quindi **non certifica il resto del circuito**.

| Fonte regionale | Intervalli con sovrapposizione planimetrica | Poligoni regionali interessati | Picco (m²) |
| --- | ---: | ---: | ---: |
| DBTsped `DBS_EDIFICATO` | **184** | **5** | **1,699** |
| CTRN 1a edizione | 50 | 2 | 0,214 |
| CTRN 2a edizione | 50 | 2 | 0,214 |

Le due CTRN coincidono negli esiti presso i due fabbricati iniziali e non valgono come due prove indipendenti. Le aree sono le **intersezioni 2D fra impronta mappata e proiezione del telaio interpolato**, non le aree di contatto tridimensionale col mondo reale. Il test non modella albero, coffa, tetto e differenze altimetriche.

### Casi DBTsped da approfondire, in ordine di picco

| Priorità | Identificativo DBTsped | Intervalli positivi | Picco 2D (m²) | Coordinate WGS84 del picco (N, E) |
| --- | --- | ---: | ---: | --- |
| 1 | `DBS_EDIFICATO.569250` | 44 | **1,699** | 46.166557, 13.360320 |
| 2 | `DBS_EDIFICATO.569249` | 57 | **1,210** | 46.166628, 13.360422 |
| 3 | `DBS_EDIFICATO.569284` | 41 | 0,562 | 46.167519, 13.360770 |
| 4 | `DBS_EDIFICATO.569283` | 25 | 0,168 | 46.167401, 13.360705 |
| 5 | `DBS_EDIFICATO.569248` | 29 | 0,076 | 46.166728, 13.360541 |

I due maggiori conflitti sono **più a sud** rispetto ai due target OSM della prima analisi; **non** hanno ancora una corrispondenza verificata con una facciata osservata. Non si devono applicare collisioni arbitrariamente su queste sagome. Un edificio che compare in DBTsped ma non nella CTRN può derivare da differenze temporali, di restituzione o di sagoma, non necessariamente da errore del percorso.

### Confronto mirato sulle due way OSM originali

| Way OSM | Sovrapposizione OSM/telaio (m²) | IoU fra sagoma OSM e unione delle sagome DBTsped adiacenti | IoU con CTRN 1a ed. |
| --- | ---: | ---: | ---: |
| `36158227` | 0,432 | 0,880 | 0,957 |
| `36158219` | 0,060 | 0,918 | 0,954 |

L'IoU è un indice planimetrico di somiglianza (1 = coincidenza perfetta); **non misura l'errore del muro vero**. Sia nelle geometrie OSM sia in quelle regionali le superfici possono includere volumi, corpi di fabbrica o proiezioni non identificati come muratura a terra. Nel solo istante OSM più critico di `36158227` la DBTsped non presenta sovrapposizione col telaio, mentre la CTRN è prossima al contatto; sul tratto complessivo DBTsped esistono altri conflitti. Non trasformare queste differenze in una traslazione automatica della strada.

La revisione visiva locale del 25 ottobre 2026 in Via Mont Joanes 59–61 osservava **muri in pietra al piano strada**, fascia pavimentata rialzata, un angolo sporgente e gronde distinte. È una fonte **di contesto**, non una misura, e non documenta direttamente i nuovi punti più a sud.

## Output e strumenti

- [**Mappa panoramica dei cinque punti**](figure_fvg_mont_joanes/overview.svg), SVG originale con fonti attribuite, nord e scala 20 m.
- [**Confronto HTML**](figure_fvg_mont_joanes/overview.html), versione consultabile in browser senza alcuna dipendenza esterna.
- Risultati completi **solo sul PC**: `results/fvg_official_buildings/comparison_20261107_v1/`, `full_lap_20261107_v1/`, `overview_20261107_v1/`. I rapporti non sovrascrivono i test antecedenti.

Procedura locale, nella cartella di lavoro Unreal:

```powershell
.\.venv\Scripts\python.exe tools\fetch_fvg_building_footprints.py --output results\fvg_official_buildings\NUOVO_SNAPSHOT
.\.venv\Scripts\python.exe tools\compare_fvg_building_footprints.py --snapshot results\fvg_official_buildings\NUOVO_SNAPSHOT --prior-plan results\mont_joanes\source_plan_20261106_v5\review.json --output results\fvg_official_buildings\NUOVO_CONFRONTO
.\.venv\Scripts\python.exe tools\audit_fvg_full_lap_clearance.py --snapshot results\fvg_official_buildings\NUOVO_SNAPSHOT --swept-report results\building_context\f437_swept_chassis_20261106_v1\report.json --output results\fvg_official_buildings\NUOVO_GIRO
.\.venv\Scripts\python.exe tools\render_fvg_hotspot_overview.py --snapshot results\fvg_official_buildings\NUOVO_SNAPSHOT --full-lap results\fvg_official_buildings\NUOVO_GIRO\report.json --output results\fvg_official_buildings\NUOVA_MAPPA
```

Usare nomi di output nuovi e mantenere gli input immutati. Ogni output contiene o verifica le impronte SHA-256 dei file effettivi. Gli script non cambiano package, mesh, terreno, dati LiDAR originali né la fisica. `python -m unittest discover -s tests -v` esegue i test unitari sintetici disponibili.

## Sviluppo successivo

1. **Revisione visuale del tratto sud** attorno a 46.166557 N, 13.360320 E e 46.166628 N, 13.360422 E, da entrambi i versi. Confrontare i livelli di facciata, portici, coperture e confine asfalto/marciapiede; non confondere panoramiche vicine con quelle esattamente osservate.
2. Acquisire, se effettivamente accessibili, i **DSM e DBM regionali a 0,5 m** delle tessere corrispondenti, separati dal DTM già presente. Verificare quota verticale e sistema ellissoidico/ortometrico prima di confrontarli con Unreal. Un DSM di tetto non sostituisce il rilievo dei muri a terra.
3. Soltanto dopo riscontri concordanti proporre una **candidata stradale/edilizia separata**, quantificando le modifiche e verificando collisioni complete della Yaris più albero e coffa nel motore nativo. Il target 4K/60 FPS è ancora da collaudare.

**Limite principale:** questi dati ufficiali provengono da fotointerpretazione e da cartografia di epoche diverse; da soli non permettono di individuare al centimetro una parete realmente esistente. Il rapporto non autorizza un'importazione edilizia automatica nel gioco.
