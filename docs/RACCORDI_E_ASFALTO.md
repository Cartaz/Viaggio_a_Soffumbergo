# Asfalto e uscita recuperabile dal circuito

La strada principale usa un materiale procedurale grigio asfalto, opaco, con
graniglia attenuata in distanza. È una scelta visiva del prototipo; il manto
delle strade reali resta da confrontare con Street View e sopralluogo.

L'asfalto è stato abbassato sulle facce del terreno derivato, con soli **2 cm**
di separazione tecnica per evitare superfici sovrapposte. Il ribassamento lungo
l'asse è circa **48 cm**. Una raccordatura larga **0,85 m per lato** collega il
bordo al terreno: meno di metà della larghezza nominale della Yaris, 1,745 m.
Le 352 tessere di terreno, l'asse originale e i 41 raster restano invariati.

La quota della raccordatura segue un'interpolazione cubica a derivata nulla
agli estremi. La triangolazione si conforma alle singole facce del terreno a
2 m, così il suolo non attraversa facce lunghe della fascia. La precisione
geometrica è 0,1 mm. La continuità non elimina pendii naturali o ostacoli reali
ancora da censire; larghezza stradale e sistemazione restano di progetto.

Asfalto sul layer 4, raccordi sull'8, terreno sull'1: la Yaris usa tutti e tre.
Strada e raccordi condividono la residenza del settore e il confronto T li
rimuove entrambi. I checkpoint distinguono ancora l'asfalto dalla fascia.

```powershell
python tools/build_circuit_construction.py
python tools/check_circuit_construction.py
python tools/build_circuit_practice.py
python tools/build_circuit_loop.py
python tools/build_circuit_shoulders.py
python tools/check_circuit_shoulders.py
python tools/validate_circuit_shoulders.py --godot PERCORSO_GODOT --blender PERCORSO_BLENDER --project "C:\Giochi\Sviluppo\Viaggio a Soffumbergo" --capture
```

Tutte le nuove prove 3D usano esclusivamente il progetto Windows con **Yaris
finale, pennone/coffa pirata e Bianca/Bernie**, verificati tramite gli asset
caricati e visibili. Il controllo interrompe il collaudo se manca l'insieme
approvato. I modelli privati non vengono pubblicati.

Il controllo senza finestra confronta 29.877 raggi stradali e 4.820 raggi sui
raccordi con quote interpolate indipendentemente, a 60/120 Hz. Verifica anche
fronti float32 locali e 191 giunzioni della raccordatura. Una guida di 200 m
esce oltre 4 m dall'asse su entrambi i lati, attraversa fascia e terreno e
rientra usando solo pedali e sterzo. Verifica appoggi, assetto e assenza di
recuperi. Il progetto Blender include la stessa assemblatura finale esportata
localmente da Godot. Evidenze: `reports/RACCORDI_ASFALTO_VERIFICA.json`.

La prova visibile salta la scansione geometrica completa e avvia la guida in
circa 3 secondi nel collaudo registrato. L'auto viene mostrata dopo il caricamento
della strada; durante la preparazione compare un messaggio esplicito.
I derivati, le immagini e il progetto Blender restano in `build/`, fuori Git.
La sincronizzazione conserva impostazioni, modelli e personaggi privati.

Prossima attività: [revisione strada con Street View](REVISIONE_STRADA_STREETVIEW.md),
un tratto alla volta. Nessuna larghezza o quota viene dedotta da una prospettiva
e nessuna immagine Google viene inserita nella repository pubblica.
