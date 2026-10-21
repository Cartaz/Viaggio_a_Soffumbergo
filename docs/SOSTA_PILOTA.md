# Sosta tecnica a Valle — prototipo 0.1

21 ottobre 2026. Scena separata `godot/scenes/parking_pilot.tscn`, raggiungibile
guidando l'approccio di prova. È una piazzola sintetica presso l'arrivo nord,
**non il prato PV-01**, una sua ricostruzione o un collegamento pedonale verificato.
Il punto panoramico candidato PV-01 dista circa 242 m in pianta dall'estremità
del tratto; non sono stati inventati un raccordo o un permesso di parcheggio.

## Prova giocabile

Nella copia Windows aprire **Avvia sosta a Valle.cmd**. W/S avanti/retro,
A/D sterzo, Spazio freno; R recupera invalidando il tentativo, N ricomincia,
M mostra la mappa, C torna alla camera al seguito. Attraversare i cinque
checkpoint nel verso corretto e fermare tutta l'auto entro il riquadro finale.

Con quattro ruote appoggiate, velocità totale sotto 0,1 m/s, velocità angolare
sotto 0,05 rad/s, asse verticale oltre 0,95 e freno almeno a metà per 1,5 s,
**E conferma la sosta**. I quattro angoli dell'ingombro dell'auto devono stare
nel riquadro, entro 1 m dalla quota progettata: non basta avvicinare l'origine.
Un incidente o un checkpoint mancante impediscono la conferma.

Durante la sosta acceleratore e sterzo sono disabilitati, il freno resta
applicato e l'auto continua a usare la fisica delle sospensioni/pneumatici.
Non viene congelata. **E torna alla guida**; prima di riconfermare serve un
nuovo arresto stabile. R/N annullano lo stato di sosta prima del recupero.
Una deriva fuori dal riquadro diventa un incidente, con recupero esplicito.

I personaggi rimangono a bordo: masse e baricentro non cambiano e non si
creano copie a terra. La modalità di sosta prepara l'interfaccia per la futura
discesa, ma **non implementa ancora discesa, visita o risalita**. L'HUD lo dichiara.
Il completamento della visita e quello dell'anello restano distinti dalla sosta.

La nuova variante separata [Visita pilota](VISITA_PILOTA.md) aggiunge il ciclo
di discesa, camminata nella piazzola e risalita. Questa scena di sola sosta
mantiene il comportamento precedente.

## Geometria e provenienza

`tools/build_parking_pilot.py` legge i derivati della prova precedente. Conserva
l'asse orizzontale; dagli ultimi circa 51 m raccorda il profilo fino a una
superficie piana negli ultimi 19 m. La larghezza passa da 4,5 a 8 m e il riquadro
misura 4,5 × 8 m: **tutti parametri di progetto**, senza misure stradali nuove.
L'altezza di progetto è circa 7,062 m rispetto all'origine locale del circuito,
con lo stesso datum; non è una quota di asfalto osservata.

La piazzola richiede circa 1,96 m di ulteriore scavo/riporto nel terreno di
prova e circa 1,88 m di variazione massima del profilo. Sono differenze rispetto
al precedente derivato sintetico, non rispetto a un rilievo stradale. Due chunk
hanno un'ulteriore sistemazione, salvata in un insieme separato. Raster originali,
corridoio di ispezione e approccio precedente rimangono invariati. I metadati
e le impronte degli ingressi sono in `build/circuit/parking_generation_report.json`.

## Rigenerazione e verifiche

```powershell
python tools/build_parking_pilot.py
godot --path . res://godot/scenes/parking_pilot.tscn
godot --headless --path . --script godot/tests/parking_state_check.gd
godot --headless --fixed-fps 120 --path . --script godot/tests/parking_pilot_check.gd -- --fast-physics
python tools/validate_parking_pilot.py --godot PERCORSO_GODOT --blender PERCORSO_BLENDER --capture
```

Il gate completo ripete le regressioni di guida/Yaris/Valle e verifica due
generazioni identiche senza alterare gli ingressi. Il conducente automatico
usa pedali e sterzo ordinari; soltanto dopo l'arrivo esegue i recuperi intenzionali.
I controlli di sosta verificano ingombro, arresto continuo, interblocco, mantenimento
fisico del freno, quattro appoggi e massa invariata. Una griglia di 153 raggi
controlla copertura e planarità dell'intero riquadro. Blender verifica fronti e
mesh dei sette chunk complessivamente modificati. Non è un benchmark FPS.
Il gate completo si esegue nella copia sorgente del repository. Nella variante
Windows usare i test Godot della sosta e i banchi del suo laboratorio: il
validatore completo dipende anche dagli asset e dai test della copia pubblica.

Report versionato: `reports/SOSTA_PILOTA_VERIFICA.json`. Derivati, screenshot,
telemetrie e progetto Blender rimangono locali sotto `build/`. La sincronizzazione
Windows usa le ricevute/backup esistenti e preserva Hybrid, rig, personaggi,
esercizi e scena iniziale. Non pubblica gli asset privati.

La prossima dipendenza è la discesa con appoggi e trasferimento del peso
verificabili, quindi locomozione/seguito e ritorno alla coffa. I controller
preparatori e le regole Python non equivalgono ancora a quel collaudo nel motore.
