# Pratica sul circuito — 21 ottobre 2026

La Yaris può essere guidata sulla superficie di costruzione dell'anello, in
**dieci tratti di allenamento**. I cambi di tratto sono riposizionamenti espliciti;
non equivalgono a superare i raccordi, le inversioni o a completare la gita.
Il candidato originale, le tappe e i tornanti rimangono conservati.

## Avvio e comandi

In Windows aprire **Avvia pratica circuito.cmd**. Nel progetto sorgente aprire
`godot/scenes/circuit_practice.tscn` e premere F6 dopo la rigenerazione.
La partenza iniziale è C1, sulla salita verso Valle.

| Comando | Azione |
| --- | --- |
| W/S, A/D, Spazio | Avanti/retro, sterzo, freno |
| PagSu / PagGiu | Tratto precedente/successivo, con riposizionamento dichiarato |
| R | Recupero oltre l'ultimo punto accettato; il tentativo rimane non valido |
| N | Nuovo tentativo del tratto |
| M / C | Mappa con freno / ritorno alla vista che segue l'auto |
| F11 / Esc | Schermo intero / uscita |

Le strisce ambra diventano verdi attraversandole in ordine e nel verso corretto.
L'arrivo richiede tutti i punti e un arresto sulle ruote negli ultimi metri.
Il completamento vale solo per il tratto. La visita e la sosta del prototipo
precedente restano in scene separate; nessun salvataggio della gita è introdotto.

## Tratti e inversioni

L'asse di costruzione misura 18.884,86 m in pianta. La pratica usa 18.668,86 m,
con 216 m complessivi di margini alle estremità: 6 m alle divisioni ordinarie,
18 m vicino alle inversioni. L'auto parte due metri dopo l'inizio e si arresta
prima del termine. I margini non sono tagli all'itinerario originale.

| Tratti | Ambito |
| --- | --- |
| A1, A2, A3 | Uscita Faedis, percorso verso Campeglio e ripartenza |
| B1 | Monte San Lorenzo–Colloredo |
| C1 | Salita verso Valle, circa 4,39 km utilizzabili |
| V1, V2 | Andata e ritorno verso la piazza, con arresto prima dell'inversione |
| D1 | Strada per Valle verso Costalunga |
| E1 | Ramo di ritorno verso Canal di Grivò |
| F1 | Rientro verso Faedis |

La revisione documentale è in `data/geography/circuit_maneuver_review.json`:

- **Faedis:** il candidato va e torna sul ramo di CIR-02, mentre le istruzioni
  riportano uscita e due svolte a sinistra. L'aggancio al panorama va riesaminato;
  non si assume automaticamente che la strada reale richieda un'inversione.
- **Campeglio:** il dossier comprende tappa e ripartenza da via Paolo Diacono.
  Il punto preciso e lo spazio di manovra rimangono da verificare.
- **Valle:** andata e ritorno sono già espliciti nei dati di V; la possibilità
  di manovrare in piazza è sconosciuta. La tappa non conferma il prato PV-01.
- **Canal di Grivò:** il dossier distingue la deviazione al segnaposto da un
  tornante della discesa. Raccordo e manovra restano da verificare.

Questa è una classificazione basata sui documenti disponibili, non un nuovo
sopralluogo. Nessuna inversione viene cancellata o trasformata in un piazzale.

## Raccordi di progetto

Il primo tentativo di guida lunga ha trovato un blocco nel settore C, circa
2,21 km dopo l'inizio del tratto: uno spigolo dell'asse non offriva spazio
sufficiente al veicolo. Il generatore aggiunge ora allargamenti dichiarati nei
soli nove passaggi con cambio di direzione fra 60° e 150°; alcune posizioni sono
ripercorse. Raggio di progetto 4,25 m, da non leggere come misura della strada.
Le quattro inversioni a 180° sono escluse. Le collisioni dell'auto e i controlli
fisici rimangono attivi; nessuna forza guida il corpo lungo una traiettoria.

Il contorno della fascia viene ripulito entro 1 mm, conservandone la topologia
e senza modificare l'asse. Questo elimina vertici quasi coincidenti che
generavano triangoli troppo sottili per la collisione. Godot e Blender ricevono
coordinate locali calcolate prima della conversione a float32; le verifiche
controllano anche i fronti dopo questa conversione.

La sistemazione del terreno comprende la fascia allargata e i raccordi esterni.
Il controllo geometrico verifica anche ogni vertice stradale e centro dei
triangoli rispetto al terreno a 2 m. Il DTM e i derivati precedenti di guida,
sosta e visita rimangono invariati. [Costruzione e limiti](COSTRUZIONE_CIRCUITO.md).

## Rigenerazione e collaudo

```powershell
python tools/build_circuit_construction.py
python tools/check_circuit_construction.py
python tools/build_circuit_practice.py
python tools/check_project.py
python tools/validate_circuit_construction.py --godot <Godot.exe> --blender <Blender.exe> --input-dir "C:\Giochi\Sviluppo\Viaggio a Soffumbergo\DTM Completi" --capture --practice
python tools/sync_circuit_construction_local.py --target "C:\Giochi\Sviluppo\Viaggio a Soffumbergo" --godot <Godot.exe>
```

`practice.json` conserva l'impronta del manifest di costruzione: se cambia la
strada, la pratica deve essere rigenerata. Non interpreta come pronta una
geometria di generazione precedente. Gli output rimangono locali sotto `build/`.

Il controllo dell'avanzamento usa una finestra di distanza lungo l'asse: un ramo
vicino di un tornante non può rubare il progresso. I checkpoint direzionali
mantengono il controllo delle discontinuità; R non ripristina la validità.
Prima di una partenza o recupero vengono caricate le collisioni e verificato un
contatto stradale. Il corpo è congelato soltanto durante il riposizionamento;
durante la guida si muove tramite forze, sospensioni e contatti ordinari.

Le prove automatiche applicano pedali e sterzo, senza spostare il corpo durante
l'intervallo misurato. Registrano contatti a ogni passo e raggi sul centro e
sulle quattro proiezioni delle ruote a 10 Hz, anche negli allargamenti. I dati
di ciascun tratto sono separati: non si sommano i riposizionamenti a una guida
continua. Le prove accelerate mantengono il passo logico a 60/120 Hz.
Risultati reali in [PRATICA_CIRCUITO_VERIFICA.json](../reports/PRATICA_CIRCUITO_VERIFICA.json).

Il collaudo a 120 Hz ha percorso tutti i dieci tratti per intero e attraversato
90 punti, con 239.220 raggi di verifica della superficie. Nessun recupero o
riposizionamento durante gli intervalli misurati, nessuna perdita di appoggio
e nessuna proiezione di ruota fuori dalla superficie ai campioni. Scarto massimo
dall'asse circa 1,065 m; somma dei tempi simulati 4.783,91 s. A 60 Hz passano
le porzioni finali dei dieci tratti, per 27 punti e 34.540 raggi. Questi sono
percorsi separati e non costituiscono una gita continua con visita.

Da completare: manovre reali, larghezze documentate, scarpate, muri, drenaggi,
barriere, guida continua con sosta e visita. Nessun test di pratica autorizza a
dichiarare pronto il viaggio completo o a distribuire i raster/asset privati.
