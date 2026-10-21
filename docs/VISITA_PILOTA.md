# Discesa, camminata e risalita — prova 0.1

21 ottobre 2026. La nuova scena `godot/scenes/visit_pilot.tscn` estende la
sosta tecnica con due occupanti indipendenti, discesa assistita, movimento a
terra, seguito della compagna e ritorno alle pose di viaggio. **Non è ancora
la visita del borgo**, il collegamento al prato PV-01 o il completamento dell'anello.

## Avvio e comandi

Nella copia Windows aprire **Avvia visita di prova.cmd**. Guidare l'approccio,
attraversare i cinque checkpoint e confermare la sosta con E dopo l'arresto
stabile. Poi:

- **F** avvia la discesa soltanto con auto ferma, freno, quattro appoggi,
  assetto verticale e sosta confermata. Un secondo comando durante la transizione
  non crea altri personaggi.
- **Tab** alterna la camera fra i due protagonisti durante discesa/camminata.
- A terra, **WASD** muove il guidatore; la compagna segue la traccia percorsa,
  aggirando inizialmente il retro dell'auto. La prova limita l'allontanamento
  volontario a circa 12 m dall'auto, con collisioni attive.
- Vicino all'auto, **F** richiede il rientro. Entrambi devono essere entro 4 m;
  raggiungono in sequenza gli imbocchi delle guide e risalgono. I passaggi comuni
  vengono liberati prima di far avanzare il secondo personaggio.
- **E** torna alla guida soltanto quando entrambi hanno raggiunto le pose di
  viaggio. Durante discesa, camminata, raccolta e risalita la spinta resta bloccata
  e il freno applicato; il veicolo mantiene sospensioni e fisica attive.
- **R/N** eseguono il recupero già previsto, riuniscono le rappresentazioni,
  eliminano le guide e invalidano/ricominciano la prova secondo le regole esistenti.

L'eventuale punto di camminata dietro l'auto è soltanto un obiettivo tecnico.
Il rientro può anche annullare una passeggiata senza raggiungerlo: questo non
certifica una visita, un record o il completamento della gita. La scena di sola
sosta precedente rimane disponibile e conserva i personaggi a bordo.

## Proprietà della massa e appoggi

Durante la guida i componenti `driver` e `passenger` appartengono al corpo
equivalente del veicolo. Alla discesa nascono due `RigidBody3D` nella posizione
dei rispettivi baricentri e con la velocità del punto di supporto. Nello stesso
passaggio la loro massa viene rimossa dal veicolo e si ricalcolano baricentro
e inerzia. Con gli attuali parametri sperimentali sono due corpi da 85 kg:
auto/struttura passano da 1.605 a 1.435 kg, mentre il totale rimane 1.605 kg.
Questi valori provengono dal laboratorio, non sono misure reali dei personaggi.

Una guida motorizzata equivalente muove i corpi mediante forze, senza impostarne
la posizione a ogni fotogramma. La forza applicata a ciascun occupante ha una
reazione opposta applicata all'auto nello stesso punto mondiale: il peso non
scompare perché cambia proprietario. Il controllo PD e il limite di forza sono
parametri di prova; non rappresentano muscoli o una simulazione completa di presa.
Le guide visibili non hanno masse o collisioni aggiuntive.

Quando la discesa è terminata, il controllo assistito viene rilasciato e la
transizione aspetta i contatti effettivi col terreno. La camminata usa forze
orizzontali limitate dall'aderenza su capsule verticali; gravità e collisioni
restano attive. Non è un ragdoll o una simulazione di equilibrio anatomico.
La compagna segue punti registrati e non viene teletrasportata se incontra ostacoli.

Alla risalita il completamento richiede posizioni entro 4 cm e velocità sotto
0,08 m/s, oltre al ritorno delle pose visive importate. Il reinserimento conserva
la quantità di moto complessiva e il momento angolare del modello di inerzia
approssimato. Prima di eliminare i corpi si disattivano le loro forze e collisioni,
evitando un ultimo fotogramma di peso duplicato. Non si usa un timer per dichiarare
completata una transizione bloccata.

## Modelli e animazioni

Il repository pubblico usa sagome quadrupedi originali come segnaposto. La
variante Windows riutilizza a runtime copie dei modelli presenti di Bernie e
Bianca; gli originali seduti sono nascosti e poi ripristinati, senza modificare
GLB, fitting, esercizi o scena iniziale. Nessun asset privato viene pubblicato.

Le rotazioni degli arti accompagnano il movimento. Sui rig compatibili si usa
IK a due segmenti per le prese sui pioli; i bersagli fuori portata vengono limitati,
senza allungare ossa o modificare le pose di riposo. Traslazioni e scale iniziali
sono ripristinate a ogni passo per evitare accumulo numerico del risolutore.
Prese, contatti visivi, stoffa e passaggio dall'abitacolo restano un primo fitting
tecnico: non sono approvati come animazione finale o collisioni anatomiche complete.
Scalette, passo dei pioli e traiettorie sono accessori di gioco progettati.

## Verifiche riproducibili

```powershell
godot --headless --path . --script godot/tests/visit_mass_check.gd
godot --headless --fixed-fps 120 --path . --script godot/tests/visit_pilot_check.gd -- --fast-physics
godot --headless --fixed-fps 60 --path . --script godot/tests/visit_pilot_check.gd -- --fast-physics --hz=60
python tools/validate_visit_pilot.py --godot PERCORSO_GODOT --blender PERCORSO_BLENDER --capture
```

Il gate completo appartiene alla copia sorgente: ripete le regressioni della
sosta, della guida e della Yaris, poi prova massa, discesa/camminata/risalita
a 60/120 Hz e rendering. I 100 controlli di trasferimento coprono **20 cicli
di rappresentazione**, non 20 visite animate. Il test integrato guida fisicamente
fino alla piazzola, esegue un ciclo completo, poi prova un recupero durante una
seconda discesa. Nessun recupero viene contato come parte del tragitto guidato.

Si controllano anche carichi sulle quattro ruote con occupanti ancora sospesi
e dopo il loro appoggio al terreno, totalità della massa, reazioni della guida,
assenza di corpi/guide residui e lunghezze degli arti importati. Le acquisizioni
mostrano discesa, camminata e seguito. I test Windows possono essere eseguiti con
le animazioni complete; l'opzione diagnostica `--physics-only` disabilita soltanto
i callback visivi dell'auto durante il banco e va dichiarata nel resoconto.

Blender ricontrolla la geometria della piazzola tramite il gate precedente;
le nuove forze, transizioni e animazioni sono verificate in Godot, senza fingere
un nuovo collaudo anatomico Blender. Evidenze: `reports/VISITA_PILOTA_VERIFICA.json`.
Log, immagini e telemetrie rimangono sotto `build/`, fuori dal repository.

Restano aperti percorso pedonale documentato verso il borgo, navmesh/ostacoli
complessi, fitting finale di piedi/mani/porte, equilibrio dei personaggi e
integrazione con sosta obbligatoria, visita e ritorno dell'intera gita Python.
