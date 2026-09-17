# Bladet i skärmbilden: W-50-1-A0111, och varför 43 % av etiketterna aldrig når sitt rör

*2026-09-17, efter grind 91. Bladet är identifierat ur beteckningarna (`KV1-K5`, `KV1-R1`, `VP1-S13-22/W`,
`S3-R8`, `RAD101`, `AV611`) och ur referensens summa: 519,5 m, vilket stämmer på decimalen.*

## Din bedömning stämmer, och den är om något generös

| | |
|---|---|
| din uppskattning | 60–70 % |
| mätt täckning på bladet | **57,0 %** |
| falskt ägande | 14,0 % |
| referens | 519,5 m |
| vi äger av rätt namn | 295,8 m |

Bladet är korpusens näst sämsta och dess största (519 m; medianbladet är 130 m).

## De två felen du pekar på, var för sig

### 1. "some pipes is not annotated" — 223,6 m saknas

Tre beteckningar står på **noll** och är tillsammans 90 m, 40 % av allt som fattas:

| Beteckning | Referens | Vår | Vad som hände |
|---|---:|---:|---|
| `VS1-S13-22` | 38,2 | **0,0** | 1 ankare, VERIFIERAT — men ägandet gav det ingenting |
| `VP1-S13-54` | 26,1 | **0,0** | namnet lästes aldrig på bladet |
| `VP1-S13-22` | 25,8 | **0,0** | 1 ankare, ledarens ände når ingen rörgeometri |

Resten är stora delförluster: `VS1-S13-12` −33,9, `VV1-X7-16` −17,2, `KV1-X7-16` −16,7, `KV2-X31-16` −13,6,
`VV1-X31-16` −10,8, `VVC1-X7-16` −10,0.

### 2. "some wrong label assignments" — 72,8 m falskt

Sju beteckningar finns inte alls i referensen:

| Vår beteckning | Vår m | Referensen har |
|---|---:|---|
| `VV1-R1-18` | 5,3 | `VV1-R1-12`, `VV1-R1-15` |
| `KV2-R1-18` | 5,2 | `KV2-R1-12`, `KV2-R1-15` |
| `KV2-R1` (utan mått) | 4,4 | — |
| `KV1-K5-15` | 4,2 | `KV1-K5-12` |
| `VS1-` (avhugget namn) | 3,6 | — |
| `S3-R8-110` | 2,1 | `S3-R8-160` |

`18` där ritningen skriver `15`, `15` där den skriver `12`, `110` där den skriver `160`, och ett namn som
slutar mitt i. Det är glyfläsningen på strecktypsnitt (uppgift #49), inte tilldelningen.

Och fyra rader är för långa mot en riktig beteckning: `VV1-R1-15` +11,4, `KV2-X7-25` +9,4,
`KV1-X31-16` +6,9, `KV1-R1-15` +6,4.

---

## Rotorsaken, mätt

Bladet har **276 etikettankare**. Så här går de:

```
VERIFIERAT FÄSTE      157   57 %
TVETYDIGT FÄSTE        62   22 %
INGET FÄSTE            57   21 %
                     ----
icke-verifierade      119   43 %
```

**43 % av etiketterna blir aldrig ett svar.** Det är samma tal som täckningen, och det är ingen slump: en
etikett som inte når sitt rör ger inga meter.

### Varför de 57 utan fäste inte får något

Skälet är i samtliga fall `leader_endpoint_touches_no_pipe_geometry`. Frågan är vad som ligger där ledaren
slutar. Mätt:

| Avstånd från ledarens ände till närmaste **accepterade** rörstreck | antal |
|---|---:|
| under 3 pt | 3 |
| 3–8 pt | 0 |
| 8–20 pt | 14 |
| 20–60 pt | 19 |
| över 60 pt | 21 |

Median 34 pt, tre fjärdedelar över 18 pt, den längsta 215 pt. **Det är inte en toleransfråga.** Ledarna slutar
inte strax bredvid röret; de slutar någon annanstans.

Var? Närmaste ritade streck av något slag ligger på **0,04 pt** för hälften av dem — de står alltså mitt på
bläck. Vilket bläck:

| Vad ledarens ände faktiskt landar på | antal |
|---|---:|
| **ink klassat `IT_RUNS_FROM_A_LABEL_BLOCK`** (0,48- och grå-pennan) | **39** |
| `DRAWN_FIGURE_NOT_A_RUN` (ritad figur, t.ex. golvbrunn) | 7 |
| `A_LABEL_POINTED_AT_IT_AND_IT_WAS_NOT_TAKEN` | 5 |

De två största familjerna i den kategorin är bladets egna **T-lager** — `V-52B---T--V1--` (130,1 m) och
`V-56B---T--VS1--` (104,6 m). `T` i lagernamnet är ritningens egen beteckning för *text*: det är etikett- och
hänvisningslagret.

**Alltså: ledaren slutar på en annan ledare.** Det är stapeln — flera etikettrader som delar en gemensam
hänvisningsstam ned till röret. Läsningen följer varje rads egen korta ledare, landar på den gemensamma
stammen, hittar inget rör där och ger upp. Den fortsätter inte genom stammen.

PipeStudios spec beskriver just det: *"flera etikettrader kan dela en stapel av ledare; en gemensam linje kan
behöva delas"* (§8). VVS5 har samlarlinjer (`_collectors_at`) men de tar inte den här formen.

### Den andra posten: en regel som säger nej

24 ankare faller på `system_conflict` — en regel som vägrar fästet när rörets lagerklass namnger ett annat
system än etiketten. Åtta av dem är `S3-R8` mot `layer_class_52BB_is_KV_not_S`: en spillvattenetikett som
pekar på ett rör vars lagerklass läses som tappvatten. `S3-R8` har **25 av 27 ankare icke-verifierade** på det
här bladet.

Om lagerklassen på det här kontorets blad inte betyder vad regeln tror, är den regeln ett nej som kostar ett
helt system.

---

## Vad som ska göras, i ordning

1. **Stapeln: följ ledaren genom den gemensamma stammen.** 39 av 57 fästen faller på det, och det är samma
   mekanism som uppgift #82 (tvetydiga fästen) och #89 (etiketter som aldrig når ett rör). Egen grind.
2. **Systemkonflikten mot lagerklass: pröva om regeln är sann på W-serien.** 24 ankare på ett blad, varav
   hela `S3-R8`. Måste mätas innan den ändras — den infördes för att hindra ett annat fel.
3. **Glyfläsningen (#49):** `18`/`15`, `15`/`12`, `110`/`160` och avhuggna namn. 72,8 m falskt på det här
   bladet ensamt.

Alla tre har egna uppgifter och ska ha egen grind. Ingen av dem rör mätningen förrän den är mätt.
