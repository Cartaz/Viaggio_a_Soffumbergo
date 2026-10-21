# Segnaposto codificati del circuito

Primo passaggio visivo lungo tutti i settori A/B/C/V/D/E/F: **86 postazioni,
92 direzioni consultate, 78 panorami distinti** sui circa 18,9 km del candidato.
Le postazioni di base sono distanziate circa 250 m (massimo 266,9 m), con quattro
punti aggiuntivi sull'accesso a Valle e viste opposte negli abitati. La distanza
massima tra punto richiesto e panorama effettivamente mostrato è 18,24 m.

Questo è un inventario iniziale dell'ambiente, **non un censimento continuo**:
restano intervalli tra postazioni, curve cieche e parti nascoste da vegetazione
ed edifici. Le immagini mostrate risalgono a luglio 2022, maggio 2023, agosto
2024, marzo/aprile 2026. La data si conserva per ogni vista. Nessuna fotografia
Google è copiata, usata come texture o inclusa nella repository.

## Catalogo e codici

Aprire `reports/CATALOGO_SEGNAPOSTO.html`, utilizzabile anche offline, per cercare
codice o descrizione e filtrare per categoria. Il catalogo CSV è nello stesso
percorso. La ricetta completa è in `data/geography/circuit_placeholders.json`.

**1.238 elementi registrati**, di cui **1.164 visualizzati** in 169 settori:
896 sagome edilizie OSM (due classificate come torri) e 342 altri riferimenti visivi.
74 box edilizi interferiscono con strada/raccordi e rimangono nel catalogo
come conflitti da rivedere, anziché essere spostati o ridimensionati di nascosto.
Altri due edifici della fonte non hanno terreno completo agli angoli del box:
gli ID sono elencati nel rapporto. Nessuno riceve una quota zero sostitutiva.
Le 91 sagome del vecchio campione di Valle hanno una sola identità nel nuovo
catalogo; otto rientrano nei conflitti e non vengono disegnate nel nuovo strato.

| Gruppo | Codici di categoria | Elementi registrati |
| --- | --- | ---: |
| Edifici | BLD edificio, TWR torre/campanile, SHL tettoia/riparo | 902 |
| Alberi e vegetazione | TRE latifoglia, CON conifera, PAL palma, WOD gruppo di bosco, SHR arbusti, HDG siepe | 150 |
| Colture e suolo | VIN filari, GRS prato/campo, ROC affioramento | 46 |
| Bordi | WAL muro, FNC recinzione, GAT cancello, GRD guardrail | 67 |
| Impianti | POL palo, LMP lampione | 42 |
| Arredi | SGN segnale, BRD bacheca/pannello, BNH tavoli/panchine, PLN fioriera, BIN contenitore | 21 |
| Accessi | ACC accesso laterale da verificare, STP scala esterna | 10 |

Ogni elemento contiene codice, descrizione, categoria, settore, coordinate,
orientamento, primitive con dimensioni e colori, fonte, data e stato di verifica.
Le dimensioni dei prototipi sono **scelte grafiche**, non misure dedotte dalle foto.

Il campanile di Valle ripreso da due panorami riusa l'unica sagoma OSM
`way/36427963`, classificata come campanile nella fonte. Anche la torretta rossa
sotto il borgo riusa una sagoma OSM, in quel caso segnalata in conflitto con
la strada. Gli abbinamenti sono inferenze di contesto dichiarate nella configurazione;
non generano copie aggiuntive o misure ricavate dalla prospettiva.

- `PH-BLD-OSM-W…`: identità dell'edificio derivata dall'ID OSM. Pianta ridotta a
  rettangolo orientato, altezza assunta. Le viste vicine sono riferimenti di
  contesto: non certificano l'identificazione di ogni singola facciata.
- `PH-…-SV-…`: identità deterministica di un gruppo osservato, basata su panorama,
  categoria e direzione. La ripetizione dello stesso punto lungo il giro riusa
  il codice. Non è il conteggio dei singoli alberi o l'estensione reale del bosco.

Esempio: **`PH-BNH-SV-0058F8CF62`**, tavoli/panchine sotto l'albero nella piazzetta
di Valle, vista `SV-048` verso sud, maggio 2023. La ricetta attuale è un box
2 × 0,8 × 0,8 m: è un riferimento di progetto, non la misura del tavolo reale.
La posizione del riferimento è stimata e deve essere affinata prima del modello
definitivo. Non rappresenta un'autorizzazione ad accedere a spazi privati.

## Nel prototipo

Le scene di costruzione, pratica e giro caricano lo strato insieme al terreno.
**F10** mostra codici vicini e la descrizione del riferimento più prossimo.
Il catalogo completo resta consultabile offline. F11 e gli altri controlli locali
rimangono quelli precedenti. Non occorre ricostruire strada o DTM per cambiare
una descrizione o un prototipo dell'ambiente.

I segnaposto sono visivi e privi di collisione finché collocazione e ingombro
non saranno verificati. Gli accessi sono marcatori ambra, non nuove strade.
Il prato sotto Valle rimane candidato; questo lavoro non conferma PV-01.

Le forme sono raggruppate per settore, tipo e materiale in `MultiMesh`; i dati
dei singoli elementi restano nei metadati dei nodi denominati con il codice.
Lo scaricamento del terreno libera anche i segnaposto. Le etichette sono limitate
ai sei riferimenti più vicini inquadrati dalla camera, con filtro di sovrapposizione
e margine per i comandi. Possono essere occultate dalle geometrie davanti a loro;
la scheda in basso e il catalogo consentono di leggere la descrizione completa.

## Rigenerazione

Prerequisiti: terreno, costruzione e raccordi locali già generati; Python con
NumPy, Shapely e pyproj. La procedura non scarica immagini e non legge né modifica
i raster originali.

```text
python tools/build_circuit_environment.py
python tools/check_project.py
python tools/validate_circuit_environment.py --project "C:\Giochi\Sviluppo\Viaggio a Soffumbergo" --godot PERCORSO_GODOT --blender PERCORSO_BLENDER
```

Il download cartografico separato è esplicito:
`python tools/fetch_circuit_environment.py --download`. La fonte OSM comprende
3.091 elementi regionali; solo quelli pertinenti vengono usati nel blockout.
Risposta originale in `build/streetview/`, provenienza e impronta pubbliche.
Le osservazioni manuali si aggiornano nei due CSV `streetview_views.csv` e
`streetview_observations.csv`. La sintassi `wall:R@180` indica un muro a destra
nella vista a 180°; la vista deve risultare effettivamente consultata nel registro.

La rigenerazione conserva i codici e non usa numeri casuali. Il catalogo include
le impronte degli input e del manifest stradale. In caso di terreno diverso,
lo strato non viene applicato a quote incompatibili. I box OSM non sono spostati
per nascondere conflitti; gli altri riferimenti hanno collocazione approssimativa
esplicita e restano fuori da asfalto, raccordi e un margine grafico di 0,5 m.

## Verifica e fase successiva

Evidenze in `reports/AMBIENTE_CIRCUITO_VERIFICA.json`: rigenerazione identica,
121 test Python, parser/formato/linter di tutti gli script, controlli Godot
su ogni settore dello strato e due immagini dal renderer con il modello finale.
Blender salva il progetto locale con strada, terreno e assemblaggio finale.
Il progetto `.blend` contiene asset privati e rimane sotto `build/`, fuori Git.

I controlli verificano identità, ricette, coordinate, rilascio dei settori,
assenza di collisioni inventate e presenza di Yaris/pennone/Bernie/Bianca attivi.
Non certificano facciate, posizione dei singoli alberi, larghezze stradali,
collisioni degli arredi o un giro fisico continuo.

La prossima passata deve infittire i riferimenti dove cambia l'ambiente,
risolvere i 74 conflitti partendo da Valle e controllare bivi e scarpate prima
di modificare la geometria stradale. Questo incremento conserva asfalto ribassato,
raccordi da 0,85 m, fisica della Yaris e originali DTM.
