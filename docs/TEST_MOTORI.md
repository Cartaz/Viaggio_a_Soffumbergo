# Vertical slice e confronto Unreal 5.8 vs Godot

Specifica del 21 ottobre 2026. **Stato: criteri definiti, test comparativo e benchmark non eseguiti; nessuna migrazione avviata o decisa.** Decisione artistica in [DECISIONI.md](DECISIONI.md), specifiche in [PROGETTO.md](PROGETTO.md), attività aperte in [ROADMAP.md](ROADMAP.md).

## Obiettivo e vincoli comuni

Valutare quale workflow permetta il realismo fiabesco richiesto con qualità, guida e prestazioni sostenibili. Godot 4.5.1/Jolt è la base corrente; Unreal Engine 5.8 è il candidato richiesto, la cui disponibilità e build esatta devono essere verificate prima di cominciare. Se non disponibile, registrare il blocco senza sostituire silenziosamente la versione. Annotare anche versione Blender, esportatori e commit dei sorgenti. Non aggiornare il progetto Godot per il solo confronto.

Il futuro prototipo Unreal deve essere separato dal progetto corrente. Riutilizzare solo asset originali o con diritti documentati, conservando sorgenti Blender, coordinate, scale, attribuzioni e laboratorio Godot. Il presente incremento modifica soltanto documentazione.

Vincoli che devono superare la revisione in entrambi i motori:

- **Luogo:** Valle di Soffumbergo reale, con chiesa, campanile, piazzetta, accessi e panorami documentati. Nessun Cervino o borgo alpino inventato; parti ignote esplicite. Il prato PV-01 resta candidato e il collegamento al borgo da verificare.
- **Auto:** Toyota Yaris Hybrid Trend italiana MY 2022 rossa, senza optional, con foro nel tetto, albero e coffa; forme e dotazioni verificate sui riferimenti Toyota. Non replicare eventuali differenze dell'auto nell'immagine.
- **Topolini:** lui guida, lei sulla coffa; anatomia naturale quadrupede, soli occhi ingranditi, nessun allungamento degli arti. Adattare seduta, appoggi e prolunghe; visita a quattro zampe, compagna al seguito e ritorno sulla coffa prima della partenza.
- **Identità:** design originali ispirati a Bianca e Bernie per palette, volti, espressioni e accessori, senza riproduzioni non autorizzate o immagini Disney incorporate.
- **Dinamica:** massa alta, baricentro, inerzia, sospensioni e carichi coerenti; nessuna soglia di ribaltamento arbitraria, massa duplicata o teletrasporto per nascondere transizioni incomplete.

L'immagine privata `Gemini_Generated_Image_2whrds2whrds2whr.jpg`, osservata nella conversazione «Confronto Godot Unreal», è un riferimento di atmosfera e qualità delle superfici. Non va copiata nella repo pubblica; Cervino, borgo alpino e personaggi bipedi dell'immagine sono esclusi dal design.

## Criteri artistici della vertical slice P3

| Area | Evidenza richiesta in gioco | Criterio di revisione |
| --- | --- | --- |
| Materiali PBR | Yaris a tre quarti e dettaglio di carrozzeria, vetri, gomme, legno/coffa, pietra e asfalto | Scala coerente, rugosità e riflessi distinguibili; nessuna superficie provvisoria presentata come finale |
| Ambiente dettagliato | Vista dal prato al borgo, tratto stradale, accesso pedonale e vista verso il panorama | Rapporti reali riconoscibili, vegetazione e arredi coerenti; dettagli e lacune collegati alle fonti |
| Luce cinematografica | Stesse viste fisse e sequenza in movimento | Esposizione, sole/cielo, ombre, riflessi e foschia coerenti; strada, volti e riferimenti del borgo leggibili |
| Pelo e tessuti | Primo piano dei due topolini, seduta, discesa e locomozione quadrupede | Pelo con volume e risposta alla luce credibili; trama, cuciture e pieghe leggibili, senza compenetrazioni evidenti o deformazioni anatomiche |
| Coerenza e camera | Guida, parcheggio, discesa, breve visita con seguito, risalita e ripartenza | Auto, protagonisti e borgo appartengono allo stesso mondo; strada visibile, albero/coffa gestiti dalla camera, nessuna transizione nascosta |

La scelta fra geometria, schede di pelo o altre tecniche e fra abiti animati o simulati rimane da misurare. Prevedere livelli di dettaglio e costi ridotti a distanza; nessuna tecnica specifica è obbligatoria se un'alternativa mantiene la qualità verificata.

Prima della produzione estesa raccogliere una revisione dell'utente delle immagini in gioco. I render Blender aiutano il confronto, ma non approvano la qualità nel motore. Un campione incompleto può servire a diagnosticare costi: va etichettato e non chiude P3.

## Protocollo comparabile

1. Fissare un manifesto comune: commit e versioni degli asset, inventario di scena, metri/assi/origine, densità di vegetazione, LOD, texture, camere con posizione e campo visivo, ora/sole, esposizione e percorso della camera. Registrare scostamenti e conversioni per ciascun motore. Usare gli stessi dati geografici verificati e dichiarare ogni area provvisoria.
2. Preparare una sequenza ripetibile con curva e arrivo, parcheggio, portiera/pedana/scaletta, discesa, breve visita quadrupede con seguito e rientro in coffa. Conservare identiche durata e soste di osservazione. Separare la sequenza visiva comune dalle prove di fisica: un replay camera non convalida dinamica o gameplay.
3. Confrontare prima le stesse viste a qualità visiva concordata, poi il miglior compromesso di ciascun motore entro il target. Nomi dei preset o tecniche di illuminazione diverse non provano equivalenza. Registrare ciò che è stato ridotto per raggiungere le prestazioni.
4. Ripetere laboratorio statico, frenata/curva, carico alto, perdita di aderenza, sollevamento ruote, recupero/ribaltamento e transizioni di massa con scenari e parametri comuni. Riportare tolleranze e differenze dei solver senza presumere determinismo tra motori. Criteri numerici in PROGETTO.md §20.1.
5. Valutare anche importazione di mesh/rig/animazioni, materiali e coordinate, modifica di un asset e reimportazione, iterazione su luce/pelo/tessuti, esportazione offline Linux/Windows e quantità di codice da riscrivere. Annotare tempi osservati, errori e limiti; un eseguibile esportato non equivale a una prova sulla piattaforma destinataria.

## Benchmark RX 6800

**Target, non risultato:** 1920×1080 a 60 FPS su Ryzen 7 5700X3D, Radeon RX 6800 e 32 GB RAM. Budget indicativi esistenti: VRAM del gioco entro 6 GB, RAM entro 8 GB; da rivalutare su dati misurati. Non trasferire questi obiettivi a un PC diverso senza dichiararlo.

- Usare build esportate confrontabili sullo stesso OS e hardware, fuori dall'editor. Registrare versione/build del motore, modalità di build, commit, OS, driver GPU, backend grafico, preset, passo fisico e stato delle cache. Verificare Linux e Windows separatamente quando effettivamente disponibili.
- Misura primaria a 1080p nativo, scala interna 100%, risoluzione dinamica e generazione di fotogrammi disattivate. Registrare VSync e limitatore; per misurare il margine disattivarli, poi verificare il comportamento con limite a 60. Eventuali prove con upscaling vanno riportate separatamente con tecnica, fattore e risoluzione interna.
- Eseguire almeno 60 secondi di riscaldamento e tre passaggi della stessa sequenza di almeno 120 secondi, includendo bosco, vista lunga dal prato, borgo e primi piani con pelo/tessuti. Se il campione non comprende uno scenario, annotare la lacuna. Ripetere lo stesso percorso e archiviare separatamente i tempi di caricamento/primo avvio.
- Conservare campioni grezzi dei tempi per fotogramma e rapporto per scenario e passaggio: FPS medi, frame time p95/p99, tempi CPU/GPU, picchi VRAM/RAM, stalli e caricamenti. Non eliminare gli stalli dal rapporto; dichiarare strumenti e limiti di misura, senza inventare contatori non disponibili.
- Applicare le soglie iniziali del progetto: media almeno 60 FPS, p95 entro 20 ms, p99 entro 33,3 ms; budget nominale di 16,7 ms per fotogramma. Queste soglie ammettono cali: descriverli e non chiamare il risultato “60 FPS stabili” sulla sola media. Controllare crescita di memoria nei tre passaggi e difetti temporali di ombre, pelo, trasparenze e LOD.

Il collaudo dell'intero anello e i tre giri previsti da PROGETTO.md §20.4 rimangono necessari: una sequenza P3 non li sostituisce. Finché non esistono build, log e misure sulla macchina dichiarata, l'esito resta **non misurato**.

## Esito e decisione successiva

Conservare manifesto, impostazioni, log, dati grezzi, immagini alle stesse inquadrature, video e un riepilogo di conformità per motore. Pubblicare soltanto materiale con diritti verificati; i riferimenti privati restano esterni.

Il rapporto dovrà distinguere: qualità artistica approvata/da correggere, fedeltà e anatomia conformi/non conformi, gameplay provato/non provato, prestazioni misurate/non misurate, prove di piattaforma e costi di conversione osservati. Motivare differenze e lacune, senza assegnare un vincitore sulla reputazione del motore o su una singola immagine.

Un eventuale cambio di motore richiede una nuova decisione documentata, con costi, rischi e piano di conservazione del lavoro esistente. Non è autorizzato automaticamente dal test. **Al 21/10/2026: nessuna misura comparativa, nessun vincitore dichiarato, P3 ancora aperta.**

## Verifica dell'incremento documentale — 21 ottobre 2026

Modificati `AGENTS.md`, `README.md`, `docs/DECISIONI.md`, `docs/PROGETTO.md`, `docs/ROADMAP.md` e aggiunto questo protocollo. Eseguiti `python tools/check_project.py` (66 test superati, integrità e report coerenti), `git diff --check` e verifica UTF-8/35 collegamenti locali nei sei documenti. Questi controlli non eseguono Godot o Blender e non misurano qualità visiva o FPS.

Base GitHub verificata: `main` a `24c316daaae48758aa8dc2772ad5a8516fcbce4f`. La copia locale preesistente conteneva modifiche e risultava arretrata: preservata, senza reset o sovrascritture. Intervento preparato nella copia di lavoro separata `work/realismo-fiabesco`, aggiornata dalla base remota. Nessun file sincronizzato in `sources/` toccato. Prossima attività del confronto: verificare versioni disponibili e preparare il manifesto comune; le prove artistiche e il benchmark restano aperti.
