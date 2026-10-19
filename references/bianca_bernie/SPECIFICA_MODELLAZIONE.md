# Specifica di modellazione — coppia ispirata a Bianca e Bernie

Revisione **2026-10-19**. Questa scheda integra [l'elenco dei riferimenti](README.md) e i vincoli di [../README.md](../README.md). Nessuna mesh finale è già stata modificata o verificata.

## Gerarchia dei vincoli

1. **Anatomia:** fotografia utente IMG_8548.webp; cranio, tronco compatto, zampe corte, coda sottile e vibrisse da topo reale. Scala uniforme a livello personaggio. Il rig non stira gli arti.
2. **Occhi:** soli elementi anatomici ingranditi, come IMG_8549.png; preservare sporgenza, orbite e movimento palpebre senza sostituire il muso con un volto umano.
3. **Identità narrativa:** prendere spunto dalla coppia Bianca/Bernie (1977 come riferimento primario, 1990 secondario) per *palette qualitativa*, asimmetrie espressive, accessori, costumi e comportamento.
4. **Funzione:** Bernie guida Yaris da seduto con appoggi, adattatori meccanici e pedali prolungati; Bianca viaggia sulla coffa e scende/risale da appoggi raggiungibili; entrambi si muovono a quattro zampe durante l'esplorazione.

### Guidatore — Bernie (Bernard)

- **Aspetto:** mantello marrone/grigio caldo, tono moderato; naso e zona del muso distinguibili; orecchie rotonde e membrana più rosata. Non fissare HEX senza un color reference affidabile.
- **Volto:** sopracciglia e palpebre trasmettono prudenza, attenzione e lieve apprensione. Occhi grandi ma non caricaturalmente sporgenti; sguardo concentrato sul percorso.
- **Accessori riconoscibili:** cappellino e capo/scialle rosso-aranciato come suggestione dal film, adattati alla seduta e al movimento quadrupede. Non devono coprire campo visivo o agganci del volante.
- **Forma:** corpo topo naturale; caratterizzazione ottenuta con materiali, accessori, comportamento e sfumature del muso, *non* mediante proporzioni umane o postura bipede obbligatoria.
- **Animazioni target:** vigilanza, sorpresa, controllo volante, uso delle prolunghe, discesa, trotto, sguardo alla compagna.

### Passeggera — Bianca (Miss Bianca)

- **Aspetto:** mantello chiaro tendente a crema/avorio, naso rosato, interne orecchie rosate; separazione qualitativa forte dal guidatore, senza imporre bianco piatto.
- **Volto:** occhi grandi, ciglia e pose palpebrali più eleganti, espressione curiosa e sicura. Differenze della testa sottili e compatibili con cranio di topo.
- **Accessori riconoscibili:** berretto/cappellino viola o rosa, fiocco/foulard morbido, **tenuta da picnic** prevista dal progetto. Accessori devono rimanere agganciati durante salto e salita alla coffa.
- **Forma:** stessa base anatomica quadrupede; distinzione ottenuta con stoffa, carattere, tinta e shape keys dei soli tratti non anatomici (palpebre/sorriso).
- **Animazioni target:** osservazione panoramica dalla coffa, reazione ai trasferimenti di carico, discesa con appoggi, camminata/trotto, sguardo al guidatore e picnic.

## Piano di lavoro Blender/Godot

| Fase | Artefatto | Verifica |
| --- | --- | --- |
| A | Raccolta locale privata dei riferimenti visualizzati dai link, nome fonte/anno e screenshot di confronto | Tracciabilità, nessun file Disney committato |
| B | Due silhouette quadrupedi A-pose derivanti dalle foto utente, non dai corpi bipedi Disney | Vista frontale, laterale, posteriore, 3/4, scala uniforme |
| C | Prove materiali + accessori **originali**, ispirati alla palette dei cel 1977 | Leggibilità dei due a distanze di gioco; niente campioni cromatici inventati |
| D | Rig con arti invariabili, eye rig, coda, vibrisse; costumi separati | Nessuna deformazione su seduta, quadrupedia, salita |
| E | Integrazione abitacolo (guidatore) e coffa (passeggera) | Pedali prolungati, seduta, appigli e collisioni coerenti |
| F | Revisione estetica con approvazione; controllo diritti prima di qualsiasi distribuzione | Checklist screenshot e licenze, test reale in editor |

**Pose di controllo minime:** riposo quadrupede, camminata/trotto, seduta guida, controllo dei pedali, frenata, arrampicata/discesa dalla coffa, postura nel prato, sguardi reciproci. Controllare le compenetrazioni di tessuti e corpo.

## Da evitare

- Allungare ossa, moltiplicare scala del solo busto, aggiungere mani antropomorfe, sostituire locomozione quadrupede con bipede esclusiva.
- Calcare un model sheet bidimensionale per ottenere un modello 3D Disney fedele; le prospettive non sono necessariamente ortografiche.
- Considerare la maquette d'asta una scansione 3D con misure: è una fotografia di oggetto.
- Trattare collegamenti a immagini come licenze per redistribuirle.

## Questioni da validare davanti agli editor

Silhouette finale rispetto alle due foto dell'utente, valori materiali sotto luci della scena, colori esatti, ingombri cappelli, fitting abiti, distanza dalla faccia al volante, cinematica scaletta-coffa, proprietà e licenze degli asset finali. Non marcare alcuna fase come completata fino a prova in Godot/Blender.
