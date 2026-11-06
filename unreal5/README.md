> **Repository snapshot (6 novembre 2026):** questa cartella è una copia pubblicabile **dei sorgenti e della documentazione** dal progetto Unreal locale. NON contiene `Unreal/Content/` (oltre 6 GB), i 113 Landscape salvati, gli asset importati, i dati LiDAR grezzi, `terrain/`, `results/` o pacchetti Windows. I comandi e le verifiche descritti sotto si riferiscono all'ambiente locale completo e **non sono riproducibili da questa cartella da sola**. La cronologia tecnica sottostante arriva al 25 ottobre 2026. Vedi [rapporto di sincronizzazione](../docs/SINCRONIZZAZIONE_LOCALE_20261106.md).

# Viaggio a Soffumbergo — Unreal Engine 5.8

Decisione dell'utente del **22 ottobre 2026**: abbandonare Godot come motore di sviluppo e passare a Unreal Engine 5.8. Terreno e vegetazione saranno costruiti con strumenti procedurali di Unreal **sempre sulla base dei dati LiDAR**.

Installazione verificata: **Unreal Engine 5.8.4, build 58902052**. Target conservato dalla decisione più recente: **Windows, 3840×2160 a 60 FPS sulla RX 6800**; è un obiettivo da misurare sul gioco rappresentativo.

## Avvio

**25 ottobre, mattina:** la revisione diagnostica separata supera il [censimento PCG anche nel Windows](docs/CENSIMENTO_PCG_RUNTIME.md): tutte le 593.327 piante conservano conteggi e trasformazioni nei 113 settori. Scansioni e giri completi Editor/Windows passati, così come rientro dal prato e contatto/retromarcia a Cianal. Nessun rendering o attivazione automatica.

Stato corrente della strada e dei giri di prova: [Strada guidabile](docs/STRADA_GUIDABILE.md). La mappa `CircuitoGuidabile` è in collaudo; resta da convalidare il giro completo con rendering 4K nella versione corrente.

**Timeout del driver:** limitazione a60FPS e cattura continua dello SkyLight disattivata dagli avvii, mantenendo il cielo e la cattura iniziale. Comandi e F11 verificati anche nella distribuzione Windows esistente. Diagnosi, dump AMD0x141 e limiti delle prove: [Stabilità grafica](docs/STABILITA_GRAFICA.md).

**25 ottobre, notte:** dopo lo spegnimento improvviso del PC lo sviluppo prosegue senza rendering. Il [rilievo lontano](docs/PAESAGGIO_LONTANO.md) dei 113 settori è ora integrato e collaudato nel motore e nel Windows separato **e37b807b9236**: scansioni complete e giri fisici di 18,86 km, tre manovre e zero recuperi. Distribuzione4a conservata; aspetto e prestazioni della nuova candidata restano da provare. L'evento non ha una causa elettrica confermata; verifiche dell'alimentazione in [Stabilità grafica](docs/STABILITA_GRAFICA.md).

La candidata separata **9811cad1439f** estende il PCG nativo a 110 settori: **593.327 piante** salvate, ricaricate e controllate, con esclusioni di strada, strutture, acque e suoli gestiti. Conserva il raccordo di Costalunga della fd61 e tutte le quote/mesh parent. Passano 110.414 controlli di superficie e il giro fisico completo Editor corrente di 18,86 km, tre manovre e zero recuperi, senza rendering. Passano anche sette prove locali 4K/60, con tutte le 21 immagini viste: qualità di vegetazione, materiali/scarpate, visibilità lontana e asset/camere restano aperti. Non è ancora esportata o promossa; la distribuzione 4a resta attiva. Dettagli in [Vegetazione del territorio](docs/VEGETAZIONE_TERRITORIO.md) e [Strada guidabile](docs/STRADA_GUIDABILE.md). È in lavorazione una variante separata del materiale roccia/muschio sulla scarpata osservata di Costalunga, senza alterare le quote LiDAR.

- **Avvia percorso Soffumbergo.cmd** apre il percorso stradale in collaudo da Faedis. Usa il pacchetto stradale separato quando presente e altrimenti Unreal installato. Sulla corrente 4a sono verificati collisioni campionate, giro fisico Windows, comandi e rientro a 4K; giro grafico completo e prestazioni restano in collaudo. W/S o frecce, A/D o frecce, spazio frena, C cambia vista, R riparte, F11 cambia schermo e Esc esce.

- **Avvia territorio completo LiDAR.cmd** apre la nuova prova del territorio esteso: tutti i settori LiDAR sono disponibili al caricamento. Si parte dal punto diagnostico a Valle. Strada, vegetazione estesa e giro completo sono ancora in costruzione; questa prova non è già l'itinerario finito. Usa un pacchetto separato e conserva la prova iniziale con PCG.

- **Avvia terreno LiDAR.cmd** apre la prova di guida sul terreno reale con vegetazione PCG. W/S o frecce avanti/indietro, A/D o frecce per sterzare, spazio freno, C cambia vista, R riparte dal punto iniziale, F11 alterna lo schermo intero, Esc esce. Il programma usa il pacchetto Windows creato e collaudato localmente; in sua assenza usa l'installazione Unreal.
- **Apri Unreal.cmd** apre il progetto nell'editor, sulla prima scena di terreno LiDAR.
- **Avvia laboratorio Unreal.cmd** apre il laboratorio interattivo ereditato dal confronto: W accelera, spazio frena, A/D sterzano, C cambia camera. Richiede Unreal installato; non è una build esportata.
- Progetto: `Unreal/SoffumbergoLab.uproject`. Il nome interno del modulo è conservato per riutilizzare i riferimenti agli asset del prototipo.

## Prima migrazione

La base C++/Chaos, i materiali e gli asset importati della Yaris Hybrid MAH con coffa pirata e i due occupanti provengono dal prototipo locale già disponibile. Questa copia è separata dal confronto e dal laboratorio Godot. I personaggi importati sono una base tecnica storica, non una nuova approvazione artistica o anatomica.

Il nuovo importatore prepara un **Landscape nativo** da un ritaglio LiDAR di **252×252 metri**, 505×505 campioni a passo 0,5 m. Nessun rumore, riempimento o ricampionamento delle quote. Origine, assi, datum e errore di quantizzazione sono registrati in `terrain/valle_first/manifest.json`.

Il plugin **PCG** è attivo. Il nuovo grafo `/Game/Procedural/PCG_ValleVegetazione` genera realmente **132 alberi, 274 arbusti e 1.115 ciuffi d'erba** nel ritaglio iniziale, filtrando copertura OSM, esclusioni e pendenza. Sei mesh originali sono create proceduralmente dentro Unreal, con tre livelli di dettaglio. La rigenerazione con lo stesso seme è identica; un seme diverso cambia la disposizione e ripristinare quello originale la ricostruisce. Nessuna istanza nei campioni controllati supera la maschera consentita. Il grafo iniziale di solo campionamento è conservato.

Il Landscape supera la rilettura di tutti i **255.025 campioni**, senza differenze nel dato R16 importato, e **81/81 raggi di collisione**, con errore massimo di circa **0,142 mm** sui punti di prova. Tre esecuzioni reali Chaos a 120 Hz verificano tenuta da fermo, breve avanzamento, retromarcia e arresto con quattro ruote in contatto alla fine. Usano la Yaris con coffa e due occupanti, sul terreno salvato e senza il piazzale sintetico. Questi controlli riguardano soltanto il punto e le manovre di prova, non la strada completa o la taratura fisica definitiva.

Evidenze: `results/landscape_collision.json`, `results/vegetation_generation.json`, `results/lidar_vehicle_checks.json`. Stato e attività successive in [Sviluppo Unreal](docs/SVILUPPO_UNREAL.md). La qualità artistica finale, il borgo, la carreggiata, l'intero anello e il target 4K/60 restano da verificare.

La prova Windows esportata supera anche le tre manovre con rendering 4K e passo variabile, nel profilo bilanciato C usato dal lanciatore. L'avvio normale senza specificare la mappa è verificato. Il gioco manuale ha un limite di 60 FPS. Nella diagnostica della sola scena statica, il profilo C misura circa 69 FPS medi a 4K nativo con Lumen attivo; sono stati misurati 60 secondi dopo 30 di riscaldamento. Non è il collaudo del gioco completo né una certificazione di 60 FPS stabili.

## Direzione del territorio

**Territorio esteso importato:** 113 Landscape nativi da 504 m, quote e fori NoData riletti senza differenze. La variante stradale contiene carreggiata, banchine e tre ponti attraversati con impalcati separati; un quarto ponte osservato è adiacente al bivio. Il controllo corrente supera 110.236 sonde stradali, mentre il giro completo resta in collaudo. Prove Windows del territorio originale e limiti in [Territorio completo](docs/TERRITORIO_COMPLETO.md); stato della nuova variante in [Strada guidabile](docs/STRADA_GUIDABILE.md).

1. DTM LiDAR → quote, scala e pendenze del terreno.
2. Copertura del suolo verificata e, se disponibili, DSM/nuvole classificate → maschere della vegetazione.
3. PCG → distribuzione ripetibile di alberi, arbusti, erba e dettagli, con esclusioni per strada, borgo, prato e percorsi pedonali.
4. Misure sul contenuto rappresentativo → densità, distanza di visibilità, livelli di dettaglio e suddivisione del mondo.

I DTM disponibili descrivono il suolo nudo. Non permettono di conoscere da soli specie, posizione esatta e altezza degli alberi: tali dettagli saranno vincolati ad altre fonti quando disponibili e dichiarati procedurali negli altri casi. Il DTM non certifica la carreggiata, i ponti o i muri.

Dettagli e attività aperte: [Terreno e vegetazione](docs/TERRENO_E_VEGETAZIONE.md). La nuova decisione supera le indicazioni storiche «nessuna migrazione» nei documenti del confronto. Quei file conservano le evidenze precedenti e non vengono riscritti.

## Conservazione

La copia precedente in `C:\Giochi\Sviluppo\Viaggio a Soffumbergo` e il prototipo in `C:\Giochi\Sviluppo\Soffumbergo-Unreal-5-8` sono conservati. Nessun file di `sources/` modificato. Asset privati, LiDAR, cache e output generati rimangono locali; nessuna pubblicazione o modifica della visibilità GitHub.
