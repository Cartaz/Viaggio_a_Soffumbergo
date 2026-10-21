# Giro sperimentale sulla costruzione

**Stato dopo il ribassamento della strada:** riferimenti rigenerati; collaudo
completo con il modello finale ancora aperto. Le precedenti prove sul proxy
pubblico e sulla superficie rialzata non costituiscono accettazione della
versione corrente. Tutte le nuove prove richiedono Yaris finale, pennone/coffa
e Bianca/Bernie; il controllo degli asset interrompe la prova se mancano.
La manovra M1 è stata verificata sulla nuova superficie con l'assemblaggio
finale: cinque fasi, arresti stabili, nessuna ruota fuori dall'asfalto,
recupero invalidante e nuovo tentativo. M2, M3, M4 e giro continuo restano aperti.

La scena `godot/scenes/circuit_loop.tscn` collega le tappe del candidato senza
riposizionare l'auto tra le fasi. Le quattro inversioni rimangono nel percorso:
si raggiunge il riferimento, si arresta l'auto e si torna indietro sul ramo
appena percorso. Ai raccordi M1 e M3 sono previste ulteriori correzioni
avanti/retro, trovate all'interno della superficie già costruita. Nessun
piazzale aggiunto, nessun ramo o tornante eliminato.

È un itinerario di progetto, non la conferma di poter eseguire le manovre sulle
strade reali. Il candidato originale resta di 18.884,86 m; il riferimento di
guida, comprensivo delle manovre, misura circa 19.008,95 m. Le deviazioni locali
del riferimento di manovra sono dichiarate, senza modificare la fonte OSM.
La verifica documentale delle tre tappe e dell'aggancio iniziale resta in
`data/geography/circuit_maneuver_review.json`.

Il cambio fase richiede tutti i checkpoint nell'ordine, posizione entro 1 m dal
riferimento, quattro appoggi, auto diritta, velocità sotto 0,05 m/s, velocità
angolare sotto 0,08 rad/s e freno applicato per almeno 0,6 s. Il corpo fisico
rimane attivo. W/S azionano avanti/retro, A/D lo sterzo, Spazio il freno.
Il display indica la fase e il verso richiesto. PagSu/PagGiu non spostano
l'auto; R dichiara un recupero e invalida l'intero tentativo; N ricomincia
dalla partenza con riposizionamento esplicito.

La ricerca locale usa una bicicletta cinematica con sagoma 1,745 × 3,94 m,
margine di progetto di 10 cm e raggio minimo di riferimento di circa 5,56 m.
Questa ricerca propone una traiettoria: soltanto il test Godot può dimostrarne
l'esecuzione con la Yaris caricata. La guida automatizzata dei test usa pedali
e sterzo ordinari; in retro ripercorre la traiettoria dell'asse posteriore
registrata all'andata. A Canal usa una richiesta di circa 2 m/s prima della
salita, per mantenere slancio, conservando la stessa forza motrice del modello.
Il primo tentativo lento si arrestava in pendenza: nessun aumento della coppia
o della potenza è stato introdotto per superarlo.

```powershell
python tools/build_circuit_loop.py
godot --path . res://godot/scenes/circuit_loop.tscn
godot --headless --path . --script godot/tests/circuit_loop_check.gd -- --full --output=build/loop_validation/continuous
```

`--case=0`, `1`, `2`, `3` eseguono prove locali separate; `--hz=60` varia il
passo fisico. Le prove locali non sostituiscono il giro continuo. Risultati,
limiti e impronte sono in `reports/GIRO_COSTRUZIONE_VERIFICA.json`.
Anche un giro su questa superficie non completa la gita con sosta, discesa,
visita del borgo, seguito della passeggera e risalita: quella integrazione resta
da realizzare e verificare.
