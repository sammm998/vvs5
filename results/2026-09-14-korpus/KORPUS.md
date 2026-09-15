# Hela materialet läst

284 blad ur Driven, 289 sidor. Allt nedan kommer ur svepet (`sweep-gate69.json`), inget facit är inblandat —
den jämförelsen görs i sina egna grindar och hör inte hemma i en inventering av vad som lästes.

## Vad som gick att läsa

| | |
|---|---:|
| Blad totalt | 284 |
| Lästa | **271** |
| Ej lästa | 13 |
| Tid per blad | median 18,9 s · snitt 29,3 s · längst 244 s |
| Kontamineringsprov | **271 av 271 PASS** |

De 13 som inte gick:

* **4 saknar vektorritning** (`V-50-1-00 RIVNING`, `V-50-1-02 RIVNING`, `V-53-1-00 RIVNING`, `V-57.1-01-DEM`).
  Motorn vägrar läsa en inskannad bild, och det är rätt svar.
* **6 flersidiga handlingar hann inte klart** inom 240 s per sida (Badmössan, Badskon 1 och 2, Bläckhornet,
  Godsfinkan 2, Löpöglan 2). De läser 4–14 sidor av 21–84. Enstaka blad ur dem läses utan problem — det är
  handlingen som helhet som är för stor för en enda körning.
* **3 tog längre än 420 s** (`V-500-1-010-100`, `V-570-1-010-100`, `V-570-1-010-130`).

## Vad läsningen gav, per ritningsserie

Serien avgör vad ett blad ens kan ge. En håltagningsritning har inga rör att mäta.

| Serie | Blad | Utan mängdrader | Ritat rör | Mätt |
|---|---:|---:|---:|---:|
| **W-50-1** (plan) | 49 | **0** | 9 582 m | **72,0 %** |
| **V-50-1** (plan) | 85 | 11 (13 %) | 12 208 m | **72,8 %** |
| V-52-1 (plan) | 2 | 0 | 263 m | 74,6 % |
| V-53-1 | 14 | 2 | 793 m | 34,9 % |
| V-56-1 | 2 | 1 | 230 m | 0,7 % |
| V-57 (rivning) | 11 | 7 | 2 815 m | 5,6 % |
| V-50-6 (håltagning) | 14 | **14 (100 %)** | 201 m | 0 % |
| V-50-8 | 3 | 3 | 0 m | – |
| V-500-1 / V-520-1 / V-530-1 / V-570-1 | 9 | 1 | 0 m | – |

**På plansserierna mäts ungefär 72 % av det ritade röret.** Det är siffran som betyder något, för det är de
bladen produkten är till för.

## De 39 blad som gav noll rader

De är inte 39 misslyckanden. Fördelningen per serie: V-50-6 (14), V-50-1 (11), V-57 (7), V-50-8 (3),
V-53-1 (2), V-530-1 (1), V-56-1 (1).

Tre av dem öppnades och lästes i namnrutan:

* `V-50-6-B0114` — **"HÅL I TAK Ø105 mm"**. En håltagningsritning. Noll rörrader är rätt svar.
* `V-50-6-B0214` — samma serie, inget ritat rör alls.
* `V-50-8-B0001` — ventilbeteckningar (`AV201-42`, `BV201-40`, "MALT STÄNGD"). Ett schema, ingen plan.

Av de 11 i plansserien V-50-1 är sex utan ritat rör över huvud taget (`A0611`, `A0622`, `A0623`, `B0512`,
`B0514`, `B0522` — 2–3 beteckningar var, troligen snitt eller detaljer), två är håltagning (`010 HT`,
`020 HT`) och en är rivning. **Två återstår som värda att titta på:**

| Blad | Beteckningar | Ritat rör | Skala |
|---|---:|---:|---|
| `V-50-1-A0002` | 17 | 0 m | **CONFLICT** |
| `V-50-1-A0402` | 7 | 0 m | **TEXT_ONLY** |

Båda har beteckningar men inget bläck som blev rör, och båda har en skala motorn inte kunde fastställa.

**En slutsats jag först drog och sedan fick ta tillbaka:** siffran "30 av 39 blad har noll rörfamiljer" såg ut
som att pennsteget avvisade allt bläck på riktiga produktionsblad. Det gjorde det inte. Bladen har inga rör.
Namnrutan avgjorde saken på tre minuter; profilens siffror ensamma pekade åt fel håll.

## Skalan

| Tillstånd | Blad | Varav utan mängdrader |
|---|---:|---:|
| VERIFIED | 231 | 33 (14 %) |
| TEXT_ONLY | 17 | 5 (29 %) |
| CONFLICT | 15 | 2 (13 %) |
| NONE | 6 | **6 (100 %)** |
| BAR_ONLY | 1 | 1 |
| FROM_THE_SET | 1 | 1 |

Utan skala, ingen meter — det är väntat och riktigt. De sex NONE-bladen är de där skalstocken inte gick att
läsa och ingen skala stod skriven.

## Beteckningar

4 539 rörnamn lästes över korpusen; 2 252 av dem fick meter. På plansserierna med verifierad skala är andelen
**64 %**, med medianen 67 % per blad. 1 365 beteckningar fick ingen plats alls.

Tvetydigheten är liten i metrar räknat: **3,2 %** av allt ritat rör. Det stämmer med
`results/2026-09-15-tvetydighet/FYND.md`, där 75–100 % av de tvetydiga sträckorna visade sig ha en enda
kandidat — stumpar och grenar som hänger av ett känt stråk, inte hål mitt i det.

## Vad som står kvar

1. **`V-50-1-A0002` och `V-50-1-A0402`** — beteckningar finns, rör saknas, skalan är CONFLICT respektive
   TEXT_ONLY. De två är den enda återstående gruppen i plansserien som inte har en självklar förklaring.
2. **Flersidiga handlingar** hinner inte klart. Det är en körningsfråga, inte en läsfråga: enstaka blad ur
   samma handlingar läses på tjugo sekunder.
3. **V-53-1 på 34,9 % och V-56-1 på 0,7 %** är de två serier där mätningen ligger långt under plansseriernas
   72 %, utan att bladen saknar rör. De är nästa rotorsaksarbete.
