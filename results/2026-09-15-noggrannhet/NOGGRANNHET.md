# Var läsningen tappar och var den räknar fel

**Datum:** 2026-09-15 · **Grind:** `gate66.json` (blind körning, 59 blad) · **Poäng:** `gate66-facit-metrics.json`

Användaren: *"det blir fel i många ritningar, beteckningar missas, rör missas eller räknas fel."* Det här är
mätningen bakom den meningen.

## Vad som faktiskt händer

| mått | värde |
|---|---|
| blad | 59 |
| facit totalt | 11 399 m |
| täckning (meter vi äger som facit också har) | **78,9 %** |
| falskt ägande (meter vi äger som facit inte har) | **16,2 %** |
| beteckningar funna av facits | 87,9 % |
| av våra beteckningar finns i facit | 78,5 % |

Per beteckning: 171 FULL, 200 PARTIAL, 179 OVER, 150 MISSED, 88 WRONG.

## Skälen, rangordnade efter meter

| skäl | rader | tappade m | falska m |
|---|---:|---:|---:|
| `PARTIAL_EXTENT_UNDER_PROPAGATED` | 200 | 1 769 | 0 |
| `OVER_EXTENT_OVER_PROPAGATED` | 179 | 0 | 1 463 |
| `WRONG_NAME_NOT_IN_REFERENCE` | 88 | 0 | 318 |
| `MISSED_LABEL_NOT_READ` | 67 | 286 | 0 |
| `MISSED_LABEL_READ_NO_METRES` | 83 | 254 | 0 |

## Det som dominerar: fel dimension, inte tappade meter

En familj ensam står för **43 % av allt som tappas**:

| familj | rader | blad | facit m | vår m | tappat |
|---|---:|---:|---:|---:|---:|
| **VS-S13** | 82 | 38 | 2 877 | 1 844 | **1 033** |
| S-P5 | 61 | 34 | 709 | 437 | 272 |
| VV-X7 | 51 | 26 | 552 | 339 | 212 |
| KV-X7 | 54 | 24 | 590 | 414 | 176 |

Men läser man familjen som helhet i stället för rad för rad ser det annorlunda ut: över 46 blad är facit
4 728 m och vi äger 4 380 m — **93 %**. Metrarna är alltså funna och mätta. De är bokförda på **fel
dimension**.

Blad för blad, DN mot DN (facit → vår):

    V-50-1-A0423    15: 37→106     22: 83→2
    W-50-1-A0132    15: 15→49      22: 62→0
    W-50-1-A0134    35: 81→22      22: 0→12
    W-50-1-A0113    22: 36→0       54: 15→35

Det är värre för en kalkyl än en tappad meter. Summan ser rätt ut och varje prissatt rad är fel: DN22-rör
beställs som DN15.

## Rotorsaken, uppmätt på V-50-1-A0423

Bladet skriver stammen kort i nio etiketter (`VS21-S13`, utan mått) och i sin helhet i sex
(5 × `VS21-S13-15-F50`, 1 × `VS21-S13-22-F60`). Facit har 14 rader DN15 och 20 rader DN22.

Tre saker prövades och föll bort som förklaring:

1. **Etiketterna läses fel.** Nej — facit använder exakt samma namn som läsningen läser.
2. **Måttet på raden paras fel.** Nej — rutan är `VS21-S13  VS21-S13` med `15  15` under, en siffra per namn,
   och läsningen läser den rätt.
3. **Den korta etiketten gissar en dimension.** Nej — `complete_identities` fyller bara i ett mått när bladet
   säger stammen i exakt ett mått, och här säger det två. (En regel som lät tystnaden bli tvetydig också i
   sammanslagningen skrevs och **backades**: den var en nolländring på det här bladet, och en omätt ändring
   ska inte ligga kvar.)

Det som faktiskt händer står i rören:

    pp_ce6ff752ce14   VS21-S13-15-F50   47,62 m   300 primitiver, 351 noder   4 × DN15-etikett
    pp_d0817e8188a3   VS21-S13-15-F50   46,81 m   301 primitiver, 352 noder   4 × DN15-etikett

Facits hela DN15 är 37 m. Ett enda av de här rören är större än så. **Stammen i DN22 och dess grenar i DN15 är
sammanslagna till ett rör** — trehundra primitiver i en kedja — och eftersom fyra DN15-etiketter sitter på
kedjan och DN22-etiketten inte kommer med i sällskapet tar DN15 hela stråket.

`_merge_identity` vägrar redan när två mått är uttalade i samma sällskap. Problemet ligger före den: kedjan
delas aldrig vid dimensionsgränsen, så de två måtten hamnar aldrig i samma sällskap — det ena vinner för att
det andra inte är med.

## Nästa varv

Delningen av en kedja där två uttalade dimensioner av samma stam har var sitt fäste: stråket ska brytas mellan
dem, vid den ritade gränsen (bock, T, dimensionsbyte), inte tilldelas den dimension som råkar ha flest
etiketter. Det är `propagate`s frögrupper (`_SeedGroup`, `_outward_compatible`, kedjekoden) och det kräver en
egen mätt grind — 1 033 m i VS-S13 och sannolikt en stor del av de 1 463 falska metrarna hänger på den.

Det är samma fel som står som uppgift #63 och #67. Den här mätningen säger hur mycket det är värt och var det
sitter.
