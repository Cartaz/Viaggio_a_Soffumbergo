# Viaggio a Soffumbergo — Unreal Engine 5.8

Gioco 3D in **realismo fiabesco**: una Toyota Yaris Hybrid rossa con albero maestro e coffa porta due topolini da Faedis a Valle di Soffumbergo. La gita prevede guida sull'anello, sosta nel prato sotto il borgo, visita a piedi e ritorno senza ribaltarsi. Valle richiede fedeltà ai riscontri reali; terreno LiDAR e osservazioni stradali hanno fonti e limiti separati.

## Aggiornamento verificato dell'11 novembre 2026

La versione Unreal dispone ora di un primo sistema **guida → discesa → esplorazione a piedi → rientro** con modello Bernie proporzionato uniformemente e controlli WASD/mouse/E. I test nativi in editor con fisica Chaos sono superati a **Valle, Campeglio e Canal di Grivò**; anche un primo inseguimento fisico di Bianca è verificato nelle tre fermate. Una prova breve D3D12 con viewport effettivo 1280×720 supera il ciclo senza crash e produce un'immagine QA, non approvata come resa finale. Si tratta di **sorgente compilato**, non di una build Windows distribuita né di un borgo finito. Vedi [Esplorazione a piedi](docs/ESPLORAZIONE_A_PIEDI_UNREAL_20261111.md) e [Revisione tecnica per priorità](docs/REVISIONE_TECNICA_UNREAL_20261111.md). In particolare i muri reali, la compagna Bianca e il target 4K/60 restano aperti.

## Un solo progetto attivo

Il motore scelto il **22 ottobre 2026** è **Unreal Engine 5.8** (installazione locale rilevata: 5.8.4). Il vecchio laboratorio Godot non fa più parte del ramo `main`; una copia integrale dello stato precedente alla pulizia è recuperabile dal ramo [archive/pre-unreal-cleanup-2026-11-06](https://github.com/Cartaz/Viaggio_a_Soffumbergo/tree/archive/pre-unreal-cleanup-2026-11-06).

**Cartella di sviluppo Windows:** `C:\Giochi\Sviluppo\Viaggio a Soffumbergo Unreal`. Il progetto Unreal si apre da `Unreal/SoffumbergoLab.uproject` oppure con `Apri Unreal.cmd`, nell'installazione locale completa. I launcher per strada, territorio LiDAR e laboratorio richiedono asset e pacchetti locali.

## Stato registrato

I report locali aggiornati al 25 ottobre 2026 riportano 113 settori di terreno LiDAR, 593.327 istanze di vegetazione PCG, una Yaris con fisica Chaos, prove di percorso di circa **18,86 km**, tre manovre e vari controlli Editor/Windows `NullRHI`. **Sono collaudi circoscritti**, non un gioco già finito. La percorrenza renderizzata completa e i **60 FPS stabili a 3840×2160 sulla RX 6800** sono ancora da confermare; i riscontri Street View, le facciate, gli ingombri degli edifici e la qualità artistica restano aperti.

Il 6 novembre 2026 sono stati verificati sul computer la presenza del progetto, dei dati e dei tool, aggiornati i riferimenti dei tool a un'unica cartella e superata la compilazione sintattica degli script Python. **Non è stato eseguito un nuovo collaudo grafico o fisico in Unreal.**

## Cartelle

- `Unreal/` — codice C++ `SoffumbergoLab`, editor, configurazioni e definizione `.uproject`.
- `tools/` — generatori, verificatori, importatori, audit e pipeline Windows.
- `parameters/` — parametri versionati dei candidati per strada, territorio e vegetazione.
- `data/geography/` — geodati e metadati condivisibili, rilievi OSM/Street View e provenienza. Le copie complete dei dati sono sul PC.
- `docs/` — documentazione Unreal attiva e dossier geografici ancora utili.
- `references/`, `reports/` — indici di sopralluogo e tavole di riferimento. Non includono le vecchie prove del motore Godot.

## Contenuti locali esclusi da GitHub

La cartella `Unreal/Content/` locale occupa circa **6,1 GB** e include mappe, asset Unreal e contenuto importato; restano locali anche `terrain/`, le tessere LiDAR a 0,5 m (`data/lidar/raw_20261020/`), `build/`, `results/`, `private/` e i pacchetti Windows. Non sono caricati automaticamente per ragioni di dimensione, provenienza e diritti. **Il solo checkout GitHub non è sufficiente ad avviare il gioco.** Evitare di ricostruire asset mancanti con finzioni non documentate.

## Documentazione corrente

[Stato dello sviluppo Unreal](docs/SVILUPPO_UNREAL.md) · [Strada guidabile](docs/STRADA_GUIDABILE.md) · [Territorio e vegetazione](docs/TERRENO_E_VEGETAZIONE.md) · [Stabilità grafica](docs/STABILITA_GRAFICA.md) · [Sopralluogo circuito](docs/CIRCUITO_SOPRALLUOGO.md) · [Istruzioni per gli agenti](AGENTS.md).

Per recuperare lo stato Godot antecedente senza reintrodurlo nel progetto attivo, usare la cronologia Git o il ramo di archivio. I dati geografici originati nello sviluppo precedente sono stati **conservati**, perché ancora necessari ad alcuni strumenti Unreal.

**Licenze:** nessuna licenza generale del gioco è stata ancora scelta. Vedere [NOTICE.md](NOTICE.md).


## Audit CPU del percorso — 6 novembre 2026

È disponibile un nuovo [controllo delle sovrapposizioni tra telaio della Yaris ed edifici mappati](docs/AUDIT_INGOMBRI_EDIFICI_20261106.md). Analizza anche gli intervalli fra due pose fisiche registrate dalla candidata Unreal `f4373a62b482`, con un inviluppo planimetrico prudente. Sono stati controllati **105.214 intervalli**, nessuno escluso; rimangono **tre impronte OSM da confrontare con le fonti**, senza nuovi edifici segnalati. I cinque test sintetici Python sono superati. Non è una verifica 3D di collisione né un collaudo grafico; la geometria del circuito e il pacchetto attivo sono rimasti invariati.

## Via Mont Joanes — tavole di revisione (6 novembre 2026)

È disponibile la [revisione planimetrica dei due edifici critici](docs/REVISIONE_CANAL_MONT_JOANES_20261106.md), con [tavola 36158227](docs/figure_mont_joanes/plan_36158227.svg), [tavola 36158219](docs/figure_mont_joanes/plan_36158219.svg) e confronto HTML. Usando le mesh asfaltate della candidata f437 e le impronte OSM archiviate, l'audit trova rispettivamente **14,677 m²** e **12,378 m²** di intersezione *sulla mappa* entro 64×64 m. L'identità delle facciate rispetto ai poligoni e la loro posizione reale restano da verificare: non sono state applicate correzioni arbitrarie o collisioni edilizie. Il tool riproducibile è `tools/review_mont_joanes_clearance.py`, con quattro nuovi test sintetici.

## Confronto FVG: edifici regionali e circuito (7 novembre 2026)

L'audit [DBTsped/CTRN/OSM sulla candidata f437](docs/CONFRONTO_FVG_EDIFICI_MONT_JOANES_20261107.md) ha acquisito tre livelli WFS regionali nel riquadro di 240 × 240 m attorno a Via Mont Joanes (62, 64 e 76 poligoni), mantenendo in locale i GeoJSON e la provenienza SHA-256. Sono stati confrontati **105.214 intervalli** della telemetria fisica: il DBTsped segnala **5 impronte e 184 intervalli** potenzialmente sovrapposti al telaio 2D, la CTRN **2 impronte e 50 intervalli** in ciascuna edizione.

[Mappa SVG con i cinque punti](docs/figure_fvg_mont_joanes/overview.svg) · [Confronto HTML consultabile](docs/figure_fvg_mont_joanes/overview.html). Non sono collisioni reali dimostrate, né un sopralluogo di tutte le case del circuito; le carte sono di epoche differenti e non equivalgono a un rilievo dei muri al piano strada. Nessuna modifica agli asset o al pacchetto attivo è stata effettuata.

## Archivio storico: prima verifica solo DTM (7 novembre 2026; superata dall'acquisizione dell'11 novembre)

Verificato il [DTM ellissoidico originale a 0,5 m dei sette hotspot](docs/AUDIT_ALTIMETRICO_CANAL_MONT_JOANES_20261107.md) con lo strumento riproducibile tools/audit_mont_joanes_height_sources.py: tutti i punti sono coperti dalla tessera Ell_DTM_06701307.asc, con quote del suolo nudo comprese fra **261,894 m e 265,249 m**. Il rapporto SHA-256 rimane soltanto in locale. I **DSM e DBM ufficiali** sono documentati dalla Regione e acquistabili/scaricabili via Eagle.fvg, ma non sono ancora stati acquisiti qui; lo strumento accetta soltanto originali con provenienza, datum ellissoidico, griglia 0,5 m e hash dichiarati. Nessuna altezza di muro o collisione è stata dedotta dal solo DTM.

## Archivio storico: preparazione download Eagle.fvg (ora completato)
Il nuovo tools/inspect_eagle_bundle.py consente di inventariare in sicurezza l'archivio ZIP Eagle.fvg quando il download è concluso: cataloga i file e identifica candidati DTM/DSM/DBM/LiDAR e può estrarre la tessera 06701307 con controllo CRC e SHA-256 dei file estratti. Rifiuta file .zip.part temporanei e non modifica la geometria Unreal. Vedi docs/PREPARAZIONE_ARCHIVIO_EAGLE_20261107.md per comandi e limiti. Il carrello richiesto conteneva 1.034 risorse; la presenza di DSM/DBM nello ZIP rimane da verificare.

## Nuove superfici LiDAR ufficiali (11 novembre 2026)
Il [rapporto sull'acquisizione Eagle.fvg](docs/EAGLE_LIDAR_VERIFICATO_20261111.md) documenta il completamento dei dati altimetrici ellissoidici: **41 DTM originali verificati contro lo ZIP, 123 nuovi raster DBM/DSM primo/ultimo ritorno**, tutti con risoluzione 0,5 m e SHA-256/CRC verificati. Il giro fisico nativo f437 (105.215 pose) è coperto al 100% da celle valide di tutti e quattro i prodotti. La [nuova analisi altimetrica delle interferenze](tools/audit_eagle_surface_clearance.py) pesa le celle LiDAR nelle vere intersezioni 2D telaio/edifici, senza scambiare tetti e muri. Il programma di [estrazione verificata](tools/extract_eagle_route_surfaces.py) e il [controllo di copertura](tools/audit_eagle_route_coverage.py) sono riproducibili. Dati regionali originali e risultati completi restano esclusivamente locali; non sono state modificate mesh o collisioni Unreal.

## Bianca e Bernie a piedi — collaudi nativi completati

[Rapporto dell'esplorazione in coppia](docs/BIANCA_ACCOMPAGNATRICE_UNREAL_20261111.md): due personaggi scheletrici realmente renderizzati e appoggiati al suolo, con uscita dalla Yaris, inseguimento fisico locale senza teletrasporto e rientro di entrambi. Collaudi `NullRHI` superati a Valle, Campeglio e Canal; seconda prova D3D12 1280×720 con entrambi i modelli visibili. Restano asset artistici/animazioni, navigazione tra vicoli, edifici fedeli e benchmark 4K/60; pacchetto stabile Windows non sostituito.
