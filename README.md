# Viaggio a Soffumbergo — Coffa e tornanti

> **Stato verificato il 6 novembre 2026.** Il progetto di sviluppo **attivo sul computer è passato a Unreal Engine 5.8** per decisione registrata il 22 ottobre 2026. Questa repository conserva anche il precedente prototipo Godot come riferimento storico; i documenti Godot antecedenti alla migrazione non descrivono più lo stack attivo.

## Obiettivo del gioco

Gita 3D offline da Faedis a Valle di Soffumbergo e ritorno lungo il circuito, con una Yaris Hybrid rossa, albero maestro e coffa, due topolini dalle proporzioni naturali e occhi più grandi. Occorre guidare senza ribaltarsi, parcheggiare sotto il paese, scendere e visitare a piedi il borgo. Direzione artistica: **realismo fiabesco**. Luoghi e opere antropiche devono rispettare i riferimenti effettivamente osservati; il terreno deriva da LiDAR, senza presentare come misure gli elementi procedurali.

## Motore e stato di avanzamento

Il progetto Unreal locale dichiara **Unreal Engine 5.8.4** e fisica Chaos; punta a **Windows 4K/60 FPS su RX 6800**, risultato **non ancora convalidato** in un giro completo renderizzato. I registri locali aggiornati al 25 ottobre documentano 113 settori LiDAR, 593.327 istanze PCG censite, prove del percorso di circa 18,86 km con tre manovre e controlli di importazione, superficie e pacchetti Windows. **Sono risultati storici di test locali, non prove appena rieseguite da GitHub**. Restano aperti aspetti artistici, verifiche antropiche, il giro 4K completo, le prestazioni e la stabilità grafica.

**[Apri lo snapshot dei sorgenti Unreal](unreal5/README.md)** · [Rapporto di sincronizzazione e limitazioni](docs/SINCRONIZZAZIONE_LOCALE_20261106.md) · [Istruzioni per gli agenti](AGENTS.md).

### Cosa contiene la repository

- **`unreal5/`**: progetto `SoffumbergoLab.uproject`, C++, configurazioni, 125 file di strumenti/automazione, parametri, documentazione, lanciatori e una selezione di metadati geografici pubblicabili. Il progetto Unreal completo **non è ricostruibile da questi soli file**.
- **`project.godot`, `godot/`, `tools/`, `art/`**: precedente laboratorio Godot/Blender, **conservato e non cancellato**. Il testo introduttivo precedente è in [Archivio README Godot](docs/GODOT_README_STORICO_20261021.md).
- **`docs/` e `references/`**: rilievi e dossier del lavoro storico, con prove e limiti documentati.

### Dati ed asset non distribuiti

La copia Unreal sul computer contiene oltre **6 GB in `Unreal/Content`**, oltre a rilievi LiDAR, cache, risultati, pacchetti Windows, asset di terzi e materiale privato. Questa sincronizzazione **non** include `.uasset`, `.umap`, eseguibili, modelli importati, texture, grandi dati geografici o screenshot privati. I sorgenti qui pubblicati richiedono il contenuto originale conservato in locale per eseguire il gioco. **Nessun download da GitHub da solo produce una build giocabile.**

Non è stata scelta una licenza di riutilizzo del gioco. Le fonti pubbliche e le attribuzioni esistenti sono documentate in [NOTICE.md](NOTICE.md) e [unreal5/NOTICE.md](unreal5/NOTICE.md). Non pubblicare asset di terzi senza diritti adeguati.

## Prossime attività

Rendere riproducibile l'inventario delle dipendenze non distribuibili, mantenere tracciata la corrispondenza delle geometrie LiDAR e delle osservazioni Street View, risolvere le verifiche sugli ingombri degli edifici nel corridoio stradale e completare un collaudo rappresentativo dell'intero giro. **Non confondere prove `NullRHI` con rendering e prestazioni 4K.**

Per i dettagli operativi correnti: [sviluppo Unreal](unreal5/docs/SVILUPPO_UNREAL.md), [strada guidabile](unreal5/docs/STRADA_GUIDABILE.md), [vegetazione](unreal5/docs/VEGETAZIONE_TERRITORIO.md) e [stabilità grafica](unreal5/docs/STABILITA_GRAFICA.md).
