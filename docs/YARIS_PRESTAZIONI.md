# Yaris Hybrid 116 CV — prestazioni e dinamica longitudinale

Verifica 20 ottobre 2026. Riferimento: XP210 europea 1.5 Hybrid MY2022,
dotazioni Trend italiane documentate separatamente. Escluse GR, Cross e Hybrid 130 MY24.

## Dati Toyota

| Dato | Valore | Provenienza |
| --- | --- | --- |
| Sistema ibrido | 85 kW / 116 CV DIN | Schede Italia e UK 2022 |
| 0–100 km/h | 9,7 s | Italia; UK 0–62 mph arrotondato |
| 80–120 km/h | 8,1 s | Presentazione europea definitiva luglio 2020 |
| Velocità massima | 175 km/h | Italia; UK 109 mph arrotondato |
| Termico | 1.490 cm³, tre cilindri, 120 Nm | Italia: 3.600–4.800 giri/min |
| Potenza termico | Italia 68 kW / 92 CV; UK 2022 67 kW / 91 CV, a 5.500 giri/min | Discrepanza delle schede conservata, non sommata |
| Motore elettrico MG2 | 59 kW, 141 Nm, sincrono a magneti permanenti | UK 2022 / Italia |
| Batteria | Ioni di litio, 48 celle, 177,6 V, 4,3 Ah | UK 2022 |
| Trasmissione | Trazione anteriore, e-CVT; differenziale 2,834:1 | UK 2022 |
| Massa a vuoto | UK 2022: 1.085–1.160 kg; scheda Italia: 1.085–1.165 kg | Intervalli di gamma, non peso esatto della singola Trend |
| Massa complessiva | 1.615 kg | Italia e UK |
| Aerodinamica | Cd 0,31 | UK 2022 |
| Pneumatici Trend | 195/55 R16 | Equipaggiamento MY22 Italia |
| Sterzata con 16″ | Diametro fra marciapiedi 10,4 m | Italia; raggio UK 5,2 m |
| Freni | Dischi anteriori ventilati, posteriori pieni; freno di stazionamento elettrico | UK 2022 |
| Sospensioni | MacPherson anteriori, assale torcente posteriore | UK 2022 |

Fonti primarie consultate:

- [Toyota UK, scheda 8 febbraio 2022](https://media.toyota.co.uk/wp-content/uploads/sites/5/pdf/220208M-Yaris-Tech-Spec.pdf), tre pagine.
- [Toyota Italia, scheda tecnica della generazione 116 CV](https://www.toyota.it/content/dam/toyota/nmsc/italy/gamma/pdf/scheda-tecnica/YARIS_Scheda_tecnica.pdf).
- [Toyota Europe, presentazione definitiva 27 luglio 2020](https://newsroom.toyota.eu/the-all-new-toyota-yaris/), ripresa 80–120 e descrizione del sistema.
- [Toyota Italia, equipaggiamenti MY22](https://www.toyota.it/content/dam/toyota/nmsc/italy/gamma/pdf/scheda-equipaggiamenti/YARIS_Scheda_equipaggiamento.pdf).

Le URL sono sensibili a maiuscole/minuscole e alcuni PDF vengono sostituiti:
il documento UK datato 2022 prevale sui documenti attuali con due motorizzazioni.
La presentazione preliminare precedente riportava 10,5 s: non è il riferimento
definitivo impiegato. L'energia nominale V×Ah è circa 0,764 kWh, calcolo
derivato, non energia utilizzabile o autonomia elettrica misurata.

Non sommare le potenze di picco termica ed elettrica: non sono disponibili
contemporaneamente nello stesso punto di funzionamento. Nemmeno i 120 e 141 Nm
sono una coppia totale all'asse. La e-CVT ripartisce potenza con un gruppo
planetario; il solo rapporto finale non consente di ricostruire la coppia alle
ruote o i giri motore. Non vengono inventate marce discrete o curve Toyota.

## Correzione applicata

La precedente spinta aveva già un limite di potenza, ma non era tarata.
Inoltre il piazzale finiva: la prova riprodotta nella copia Windows a 20 s
mostrava 125,9 km/h complessivi, di cui circa 117 km/h verticali, senza ruote
a terra. Il tachimetro confondeva la caduta con la velocità stradale. Questa
prova non ha riprodotto esattamente 500 km/h; ha identificato la stessa
classe di errore. Ora si mostra velocità tangente al supporto, oppure orizzontale
in volo; l'uscita dal piazzale ripristina esplicitamente la prova e la invalida.
Con appoggi validi si media la velocità tangente dei punti di contatto:
il dondolio del telaio sopra ruote frenate non diventa velocità stradale.
La velocità tridimensionale del corpo rimane nella telemetria diagnostica.

`yaris_powertrain.gd` applica una spinta alle sole ruote anteriori, limitata
da forza di partenza, potenza effettiva alle ruote, aderenza e riduzione della
spinta vicino alla velocità massima. La velocità del corpo non viene tagliata:
pendenza e inerzia restano fisiche. Retromarcia separata, rilascio resistente e
resistenza aerodinamica quadratica. Le resistenze esplicite sostituiscono lo
smorzamento globale del motore, evitando dissipazioni nascoste aggiuntive.

Sotto 0,5 m/s il freno usa una forza di contatto che compensa velocità e
gravità lungo il supporto, entro coppia frenante e aderenza disponibili.
Questo consente l'arresto in pendenza senza imporre velocità zero al corpo.
Il rilascio del pedale non attiva automaticamente questa compensazione.

Parametri dichiaratamente **stimati/tarati**, tutti in `data/config/yaris_performance.json`:
60 kW effettivi alle ruote, massimo di richiesta 6.500 N (poi limitato
dall'aderenza), CdA auto 0,62 m², coefficiente di rotolamento 0,013 e
160 N complessivi al rilascio. La zona di riduzione della spinta è un modello
di controllo, non una mappa elettronica Toyota. Retromarcia circa 21 km/h:
valore di progetto, nessun dato Toyota verificato per quel limite.

Il riferimento del banco è auto 1.150 kg più guidatore 75 kg, entro gli
intervalli pubblicati; non è il peso misurato della Trend dell'utente. Il
baricentro longitudinale dell'auto è stimato a −0,256 m, corrispondente a
circa 60% statico anteriore; il laboratorio usa la stessa stima. Posizione
del guidatore e masse della struttura restano quelle della rispettiva copia.

Albero/coffa aggiungono massa e un CdA stimato di 0,65 m². Il totale corrente
è 1.605 kg: non si deve forzare il mezzo modificato a ottenere i 9,7 s della
vettura di serie. Le masse dei protagonisti e della struttura sono provvisorie.
La frenata estrema del modello con carico alto può sollevare e ribaltare il
mezzo tramite le forze; il banco registra l'inclinazione e ripristina una posa
dichiarata prima della prova di retromarcia. Nessun evento artificiale di ribaltamento.

## Collaudo e limiti

`godot/tests/yaris_performance_check.gd` esegue accelerazione per 150 s,
coasting, frenata e retromarcia sul piazzale sintetico di 40 km, a 60 e 120 Hz.
Misura 0–100, 80–120, velocità terminale, contatti e assetto; separa serie e
carico. Tolleranze di accettazione: ±1 s sullo 0–100, ±0,6 s sulla ripresa,
±2 km/h sulla massima. I risultati effettivi sono nel rapporto pubblico
`reports/GUIDA_PILOTA_VERIFICA.json`; non confondere tolleranza con errore misurato.

Non è ancora una simulazione completa del sistema ibrido: mancano mappe
proprietarie, stato di carica, temperature, potenza continuativa sostenibile,
ABS/ESC e misura dell'aerodinamica della struttura. Sterzo, pneumatici e
sospensioni restano semplificati. I benchmark di serie non certificano il
comportamento del mezzo carico in curva, in discesa o su asfalto irregolare.

Per accelerare i collaudi si può usare `--fast-physics`: scheduler e scala
temporale crescono insieme, conservando il passo effettivo richiesto. Un
controllo confronta il cronometro integrato dal corpo con quello del banco.
`--physics-only` esclude solo gli aggiornamenti visivi, non l'integratore Jolt;
il rapporto lo dichiara. Le animazioni della variante locale hanno anche una
prova di percorrenza separata, precedente all'ultima correzione del freno statico.
