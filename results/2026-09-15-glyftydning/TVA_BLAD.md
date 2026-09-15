# De två blad KORPUS.md lämnade oförklarade

**Datum:** 2026-09-15
**Blad:** `V-50-1-A0002` (skala CONFLICT, 0 m), `V-50-1-A0402` (TEXT_ONLY, 0 m)

KORPUS.md pekade ut dessa två som de enda bladen i planserien utan en uppenbar förklaring till noll meter.
Båda är nu genomgångna. De är olika fall.

## `V-50-1-A0002` — noll meter är rätt svar

Bladet är en planritning över Hus A, plan 0. Rören är ritade, som streckade linjer. Men bladet har
**noll hänvisningslinjer** (`leaders: 0`), och ingen beteckning står vid något rör.

De 23 "beteckningar" läsningen räknar kommer ur förklaringslistan uppe till höger — `S SPILLVATTENLEDNING`,
`KV KALLVATTENLEDNING`, `AV20-21`, `RV21` och så vidare. Det är en teckenförklaring, inte namn på det som är
ritat.

Bladet säger själv var rören namnges:

> FÖR LEDNINGAR UNDER BOTTENPLATTAN PLAN 1, SE RITN V-53-1-A0102

En mängdare som bara får det här bladet kan inte heller säga vad rören heter. **Noll meter är rätt svar**, och
det finns inget fel att rätta. Det som vore bättre är att säga varför: "rör ritade, ingen beteckning på
bladet" i stället för en tom lista.

## `V-50-1-A0402` — ett verkligt fel, och det är inte skalan

Bladet är plan 4 (tak) med ett stamstråk nere i mitten. 39 beteckningar, 15 hänvisningslinjer, 10 av dem
knutna till en beteckning — och **alla tio slutar i `NO_PIPE_ATTACHMENT`**, med skälet
`leader_endpoint_touches_no_pipe_geometry`. Noll rörfamiljer, noll fysiska rör, noll primitiv.

### Vad som faktiskt står där

Tre av ledarna slutar mitt i bläcket:

| Beteckning | Ledarens ände | Närmaste `V-53B--FE-_S1` |
|---|---|---|
| `S3-75` | (1038,12, 1109,06) | **0,97 pt** |
| `S3-110` | (1052,88, 1143,98) | **1,91 pt** |
| `S3-110` | (1137,66, 1012,94) | **3,71 pt** |

Räckvidden är `CONTACT_TOL (0,6) + min(0,5 · pennbredd, 0,5)`. Pennan är 0,72 pt, alltså 0,6 + 0,36 = **0,96
pt**. Den första missar med **0,01 pt**.

### Men toleransen är inte rotorsaken

Allt inom 6 pt från den änden, uppmätt:

```
 0,00 pt  längd 19,6   V-53B---T-N   w0,72     <- ledarens egen penna
 0,97 pt  längd  0,4   V-53B--FE-_S1 w0,72
 0,97 pt  längd  0,5   V-53B--FE-_S1 w0,72
 1,02 pt  längd  0,4   V-53B--FE-_S1 w0,72
 1,19 pt  längd  0,8   V-53B--FE-_S1 w1,08
 ... ytterligare nio, alla mellan 0,3 och 1,5 pt långa
```

Segmenten är **0,3 till 1,5 pt långa**. Det är ingen ledning. Det är omkretsen på en **symbol** — en
spillvattenluftare, ritad som en liten cirkel av ett trettiotal lösryckta småstreck, delvis på lagret
`spillvattenluftare` och delvis på `V-53B--FE-_S1`.

Läsningen har två vägar för just det här: `_enclosing_symbol` (ledaren slutar inne i en sluten symbol) och
`_marker_cluster` (det som slutar vid ett märke). Båda utgår från att symbolen är **en** bana. Här är cirkeln
uppdelad på ett trettiotal enskilda banor med ett segment var, så ingen enskild bana är sluten, och ingen av
vägarna öppnar sig. Närmiss-regeln (`NEAR_MISS` 6 pt) avstår också, och gör rätt i det: spridningen mellan de
närmaste punkterna är 8,5 pt, alltså långt mer än `NEAR_ONE` (2,5 pt) — det står flera ritade saker inom
räckhåll och bladet har inte sagt vilken.

**Rotorsak:** en symbol som ritats som en spridd skur av små streck känns varken igen som symbol eller som
sträcka, och en hänvisningslinje som pekar på den når därför ingenting. Röret fortsätter från symbolen.

Det är ett verkligt och generiskt fel. Det är också ett djupt fel — det rör symbolfamiljerna, inte en tolerans
— och det får ett eget varv.

## Vad som prövades och backades

Räckvidden mäts till linjens **mitt**, men bläcket ligger en halv pennbredd ut åt vardera hållet, och
`min(0,5 · pennbredd, 0,5)` stryper den halvan vid 0,5 pt. En 2,88 pt penna ritar ett band som når 1,44 pt ut;
en ledare som slutar inne i det bandet rör vid röret. Samma fil räknar redan utan tak på rad 541
(`tol + 0.5 * p.width` i `_collector_shaped`), så filen säger emot sig själv.

Taket togs bort och rutnätets sökradie vidgades så att en tjock penna hinner vägas. Det **ändrade ingenting på
A0402**: 0,5 · 0,72 = 0,36, alltså mindre än taket, så tunna pennor rör den inte.

Ändringen är **backad**. Den är fysiskt riktig, men den påverkar bara pennor över 1,0 pt, den är inte mätt mot
korpusen, och den hör inte ihop med felet den skulle laga. Den ligger kvar som en egen fråga att grinda för
sig, inte som en passagerare i ett annat varv.
