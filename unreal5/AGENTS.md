# AGENTS — Unreal 5.8 (snapshot sorgenti pubblico)

Lavoro attivo: `Unreal/SoffumbergoLab.uproject`, engine Unreal 5.8.4 come riscontrato localmente al 25/10/2026; obiettivo Windows 4K/60 FPS sulla RX 6800, non ancora certificato. Leggi `README.md`, `docs/SVILUPPO_UNREAL.md`, `docs/STRADA_GUIDABILE.md`, `docs/TERRENO_E_VEGETAZIONE.md` e le istruzioni principali `../AGENTS.md`.

Il snapshot GitHub include codice e automazioni ma **non** le mappe binarie Unreal, i pacchetti, gli asset importati, i 113 Landscape salvati o i grandi file LiDAR. Non dichiarare riproducibile il gioco dal solo repository. Per modifiche C++ è necessario compilare e testare nel motore sull'ambiente completo; per script Python controllare la sintassi e poi le prove funzionali con dati autentici. I report di test locali del 25 ottobre non sono test odierni.

Non promuovere una candidata stradale senza controlli di geometria, collisioni, provenienza e rientro. Conservare le baseline e distinguere i giri headless `NullRHI` dal rendering completo. Non stimare edifici o infrastrutture dal solo DTM; Street View e sopralluoghi sono vincolanti per gli elementi antropici osservati. Evitare pubblicazione di contenuti soggetti a diritti di terzi o privati. Non modificare i prototipi storici Godot.
