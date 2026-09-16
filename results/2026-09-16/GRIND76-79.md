# Grind 76–79: fästet bundet till hänvisningslinjen

Frågan var din: *"det blir ett fel att den tar med när rör kopplas mot varandra som en anslutning, den ska bara
följa hänvisningslinjen som en anslutning."*

Den är riktig, och den rör en verklig lucka. Fyra kontaktsorter är bryggor: ledaren slutar i ett stigarmärke,
en ändcirkel, en liten armatur eller på en samlingslinje, och läsningen går vidare därifrån till det som rör
samma punkt. Landar en sådan brygga där flera rör kopplas ihop lämnade den dem allihop, och då var det
rör-mot-rör-kontakten som gav namnet.

**Omfattningen, mätt blint innan referensen öppnades:** 1 948 av 5 126 ankare (38,0 %) nådde sitt rör bara via
en brygga. `via_symbol` 1 773, `via_fitting` 68, `via_marker` 65, `via_collector` 44. Tyngst på W-50-1-A0111
(71), A0113 (53), A0122 (50) - samma blad som tappar mest meter.

## Fyra körningar

| | täckning | falskt ägande | recall | precision | FULL | PARTIAL | OVER | MISSED | WRONG |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **76** utgångsläget | 79,19 | 15,70 | 87,72 | 78,45 | 177 | 197 | 174 | 154 | 86 |
| **77** fråga vid ≥2 armar | 76,64 | **13,97** | 85,51 | 78,70 | 171 | 206 | **157** | 165 | 83 |
| **78** ...och direkt kontakt slår bryggan | 76,82 | 14,20 | 85,67 | 78,73 | 169 | 204 | 161 | 166 | 82 |
| **79** fråga vid ≥3 armar | **78,56** | 15,22 | 86,93 | **79,20** | 175 | 196 | 171 | 158 | **80** |

## Vad de säger

**Grind 77 gick för långt, och mätningen visade varför.** Två armar som möts i en punkt är geometriskt två
sträckor, men ett rör som svänger runt ett hörn ser precis likadant ut som två rör som kopplas ihop där.
Ritningen skiljer dem inte åt. Att fråga i det läget kostade 2,55 procentenheters täckning för 1,73 i falskt
ägande - fler riktiga meter förlorade än falska.

**Grind 78 visade att bryggan genom symbolen inte var problemet.** Att låta en direkt kontakt vid ledarens ände
slå ut det som bara går genom kopplingscirkeln flyttade 0,18 - inom bruset. Kostnaden satt i själva frågan.

**Grind 79 är den som accepteras.** Tre eller fler armar i punkten är en gren eller en knut, och där finns
verkligen ingenting ritat som säger vilken av dem etiketten menar. Två armar lämnas som förut, för där skulle
en fråga vara en gissning åt andra hållet.

    täckning  −0,63    falskt ägande  −0,48    precision  +0,75
    WRONG 86 → 80      OVER 174 → 171

Sex färre rader som fått meter som hör till en annan beteckning. Det är den dyraste sortens fel för den som
ska prissätta: en siffra som ser rätt ut och står på fel rad. De 0,63 procentenheter täckning det kostar
försvinner inte i tysthet - de står som tvetydiga, med sina kandidater kvar, där en granskare, en lärdom eller
läsarpanelen kan avgöra dem.

**Det här är en avvägning och inte en ren vinst.** Räknat bara i meter är utbytet fortfarande något negativt:
0,63 förlorade mot 0,48 vunna. Grind 77:s strängare regel finns kvar och går att sätta på om du hellre vill ha
färre falska meter än fler sanna - säg till, det är en rad.

## Ordning

Blint kört, källan fryst (`results/hashmanifest.json`, manifest 4f759682a2605f6d), och först därefter öppnades
referensen. 808 prov gröna. Kontamineringsskannern PASS: 67 filer, 0 fynd.
