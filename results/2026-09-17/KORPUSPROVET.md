# Alla ritningar mot facit och mot mängdarens egna streck

*Grind 91, 2026-09-17. Frysning `fbd37af0fadbec4a` (134 filer, commit `f7441eff31f1`) lades FÖRE körningen.
59 blad genom motorn utan att ett enda referensmått var i närheten; först därefter öppnades arbetsböckerna och
de markerade ritningarna.*

Fyra jämförelser gjordes, för de svarar på fyra olika frågor:

| | vad den jämför | svarar på |
|---|---|---|
| `gate_compare` | grind 91 mot grind 90 | rörde sig något av det vi byggt sedan sist? |
| `facit_metrics` | summa per beteckning mot arbetsboken | hur mycket meter, och under vilka namn? |
| `scorecard` | rad för rad, blad för blad | **vilken** rad skiljer sig, och med hur mycket? |
| `pipe_audit` | dragning för dragning | vilken enskild sträcka fattas, och varför? |
| `markup_metrics` | punkt för punkt mot mängdarens streck | ligger metrarna **på samma ställe på ritningen**? |

---

## 1. Grind 91 mot grind 90: ingenting rörde sig

```
gate90.json vs gate91.json: 59 gemensamma blad (av 59 respektive 59)
  referens    11399.2 ->   11399.2
  ägt          8900.2 ->    8900.2
  falskt       1244.1 ->    1244.1
  TÄCKNING    78.08% ->   78.08%
  FALSKHET    10.91% ->   10.91%
  blad som rörde sig: 0
```

Det är rätt utfall: sedan grind 90 har bara nivåtalens redovisning, radtabellen och markeringscensusen
byggts, och inget av det får röra en mätning. Nu är det bevisat och inte bara påstått.

## 2. Hela korpusen mot facit

```
59 blad, 11 399,2 m i referensen
  ägt av rätt namn      8 900,2 m     TÄCKNING        78,08 %
  falskt ägt            1 244,1 m     FALSKT ÄGANDE   10,91 %
  saknat                2 499,1 m

  namnen: 86,77 % av referensens beteckningar lästes, 85,20 % fick också meter
          80,44 % av våra beteckningar finns i referensen

  769 rader:  FULL 187   PARTIAL 201   OVER 153   MISSED 163   WRONG 65
```

**Det är inte exakt likadant, och avståndet dit är mätt.** För att bli det måste täckningen till ~100 % och
falskheten till ~0 %. Var de 22 procenten sitter står i avsnitt 4.

Per stil:

| Stil | Blad | Ref m | Ägt m | Falskt m | Täckning | Falskhet | Namn lästa |
|---|---:|---:|---:|---:|---:|---:|---:|
| V (textlager) | 29 | 5 849,9 | 4 614,1 | 688,1 | 78,9 % | 11,8 % | 79,5 % |
| W (konturglyfer) | 30 | 5 549,3 | 4 286,1 | 555,9 | 77,2 % | 10,0 % | 93,8 % |

## 3. Blad för blad

Sorterat efter täckning. Hela tabellen med varje beteckning finns i `gate91-scorecard.md`.

**Bäst — de här är i praktiken exakta:**

| Blad | Ref m | Ägt m | Täckning | Falskhet |
|---|---:|---:|---:|---:|
| C | 17,6 | 17,6 | 100,0 % | 0,6 % |
| W-50-1-A0021 | 31,7 | 31,5 | 99,4 % | 0,2 % |
| V-50-1-A0221 | 55,8 | 55,4 | 99,3 % | 0,0 % |
| A (= W-50-1-A0011) | 213,7 | 209,0 | 97,8 % | 1,2 % |
| E | 50,9 | 49,5 | 97,3 % | 1,8 % |
| W-50-1-A0033 | 35,1 | 33,8 | 96,2 % | 4,3 % |
| W-50-1-A0023 | 36,4 | 34,9 | 95,9 % | 3,5 % |
| V-50-1-A0211 | 107,2 | 102,2 | 95,4 % | 0,0 % |
| D | 112,9 | 106,1 | 94,0 % | 3,7 % |
| V-50-1-A0121 | 101,5 | 95,3 | 93,9 % | 0,6 % |

**Sämst — här ligger arbetet:**

| Blad | Ref m | Ägt m | Täckning | Falskhet |
|---|---:|---:|---:|---:|
| V-50-1-A0423 | 156,6 | 63,8 | 40,8 % | 48,0 % |
| W-50-1-A0131 | 201,0 | 112,8 | 56,1 % | 21,4 % |
| W-50-1-A0111 | 519,5 | 295,8 | 57,0 % | 14,0 % |
| V-50-1-A0111 | 165,8 | 104,1 | 62,8 % | 0,5 % |
| W-50-1-A0124 | 246,7 | 155,1 | 62,9 % | 25,1 % |
| V-50-1-B0122 | 517,2 | 327,2 | 63,3 % | 19,9 % |
| W-50-1-A0134 | 350,0 | 224,0 | 64,0 % | 7,4 % |
| V-50-1-B0114 | 155,6 | 106,7 | 68,6 % | 39,9 % |
| V-50-1-A0312 | 262,6 | 181,2 | 69,0 % | 10,9 % |
| W-50-1-A0113 | 516,0 | 358,2 | 69,4 % | 17,8 % |

Ett blad sticker ut åt andra hållet: **V-50-1-A0122** har 96,3 % täckning men 30,0 % falskhet — det äger nästan
allt som ska ägas och en tredjedel till.

## 4. Var metrarna tar vägen — dragning för dragning

`pipe_audit` parar varje dragning mängdaren gjorde mot varje rör läsningen äger:

```
6 673 dragningar mot 3 010 rör

  SAME_RUN     1 503   3 395,9 m    samma sträcka
  MERGED         553   4 533,4 m    vi höll ihop vad mängdaren delade
  SPLIT           28     150,1 m    vi delade vad mängdaren höll ihop
  LONG_RUN       196     442,8 m    (vi mäter 1 462,0 m på dem)
  SHORT_RUN      108     385,1 m    (vi mäter 96,7 m på dem)
  MISSING_RUN  2 631   2 491,9 m    ingen motsvarighet alls hos oss
  EXTRA_RUN      563       0 m      (vi mäter 362,2 m som mängdaren inte har)
```

Och för de 2 491,9 saknade metrarna finns skälet:

| Varför metrarna saknas | m | andel |
|---|---:|---:|
| namnet lästes men just den dragningen fick inget rör | 2 089,3 | 84 % |
| namnet lästes inte alls | 402,6 | 16 % |
| allt annat (fronter: symbol, sluten slinga, gräns, tvetydig knut …) | ~288 | — |

Och den första raden måste delas, för den blandar ihop två helt olika fel:

| | m | dragningar | snittlängd |
|---|---:|---:|---:|
| beteckningen fick **noll meter alls** | 238,7 | 165 | 1,4 m |
| beteckningen fick meter, men **just den här dragningen saknas** | **1 850,6** | **2 142** | **0,86 m** |

**Det är de korta grenarna som fattas, inte stammarna.** En mätt dragning hos oss är i snitt 2,26 m
(`SAME_RUN`), en dragning vi höll ihop täcker 8,2 m av mängdarens (`MERGED`) — men de 2 142 dragningar som
inte har någon motsvarighet alls är i snitt 0,86 m. Mängdaren mäter varje kort avstick till en apparat för
sig; läsningen tar stammen och tappar avsticken. Det stämmer med radbilden: 201 rader är PARTIAL och saknar
tillsammans 1 771,6 m.

Fronterna — som säger var ett rör slutar och varför — står tillsammans för under 300 m. Stråken slutar alltså
inte för tidigt av redovisade skäl; det är grenarna ut från dem som aldrig blir rör.

Värst (saknade dragningar på rader som ändå fick meter): W-50-1-A0113 169,3 m, W-50-1-A0134 101,2 m,
W-50-1-A0132 96,5 m, V-50-1-A0423 91,2 m, W-50-1-A0122 91,0 m, W-50-1-A0111 90,8 m.

Det näst största: **597,5 m ligger på fel dimension av rätt stam**, och 561,6 av dem åt samma håll (den
klenare dimensionen tar den grövres stråk). Det är 48 % av allt falskt ägande. Se
`PIPESTUDIO-ATERBESOK.md` och uppgift #112.

## 5. Mot mängdarens egna streck: ligger metrarna på rätt ställe?

Fem ritningar har mängdarens markeringar i filen. Här provpunktas varje mätlinje och frågan är vad läsningen
äger *just där* — det skiljer "vi tappade röret" från "vi kallade det något annat".

| Blad | mängdarens m | samma namn | annat namn | inget ägande | samma namn |
|---|---:|---:|---:|---:|---:|
| **C** | 17,7 | 17,7 | 0,1 | 0,0 | **100 %** |
| **A** | 213,4 | 204,5 | 7,9 | 1,0 | **96 %** |
| **E** | 50,6 | 48,4 | 2,2 | 0,0 | **96 %** |
| **D** | 113,2 | 106,8 | 4,3 | 2,0 | **94 %** |
| **W-50-1-A0133** | 305,0 | 174,8 | 72,9 | 57,4 | **57 %** |

De fyra första ligger i praktiken på mängdarens egna streck. På A är hela avvikelsen 4,7 m av `S3-R8-110` som
vi kallar `S3-R8-75` plus en decimeter här och där; ingenting saknas.

A0133 är den andra sortens blad, och felen där är entydiga:

| Mängdarens beteckning | deras m | samma | annat namn | inget |
|---|---:|---:|---:|---:|
| `VS1-S13-35/W` | 70,6 | 33,3 | **36,7** (varav 36,3 som `VS1-S13-12/W`) | 0,5 |
| `VS1-S13-12/W` | 76,2 | 46,6 | 6,0 | **23,7** |
| `VVC1-X7-16/W` | 16,8 | 3,7 | 1,4 | **11,8** |
| `VV1-X7-16/W` | 16,5 | 0,0 | 6,7 (som `VV1-X31-16`) | **9,8** |
| `VP1-S13-42/W` | 13,2 | 6,6 | 0,0 | **6,6** |

Det är parallellbunten, geometriskt bevisad: `VS1-S13-35` och `VS1-S13-12` löper sida vid sida, och 36 m av
den grövre får den klenares namn. Uppgift #92, nu mätt på ritningen och inte bara i summan.

En rad är inte vårt fel: mängdaren skrev `VS1-S13-12 wallmounted` på 10,4 m och `VS1-S13-12/W` på 76,2 m.
Vi läser bådas rör som `VS1-S13-12/W`. Den skillnaden är i arbetsboken, inte i ritningen.

---

## 6. Vad "exakt likadant" kräver

Målet är rimligt — fyra blad är redan där (94–100 % på mängdarens egna streck). Men korpusen som helhet
ligger på 78 %, och de 22 procenten är inte ett jämnt brus utan tre högar:

1. **1 851 m i 2 142 korta grenar** (snitt 0,86 m) på beteckningar som redan har meter, plus 239 m på
   beteckningar som fick noll. Det är den största enskilda posten, och den handlar om avsticken ut från
   stammen - inte om att hitta stammen. Uppgifterna #82, #89 och #88 rör alla den här.
2. **598 m: rätt stam, fel dimension**, 94 % åt samma håll. Parallellbunten är mekanismen (#92, #93, #94,
   #60), TEE-regeln är en del av svaret (#112).
3. **403 m: namnet lästes inte alls.** Glyfläsningen (#49) och V-stilens textlager.

Tar man de tre är 3 090 m av 2 499 saknade plus 1 244 falska adresserade — alltså i stort sett hela avståndet
till exakt. Ingen av dem kräver en ny sorts motor; alla tre har en mätt mekanism och en namngiven uppgift.

**Ingen av dem är gissningar om var felet sitter.** Varje siffra i den här rapporten kommer ur en blind
körning som frystes innan referensen öppnades, och varje jämförelse går att köra om med ett kommando.

## 7. Filerna

| Fil | Vad |
|---|---|
| `gate91.json` | den blinda körningen, 59 blad |
| `gate91-facit-metrics.md` / `.json` | betyget per blad och stil |
| `gate91-scorecard.md` / `.json` | **varje rad på varje blad**, referens mot vår |
| `gate91-pipe-audit.md` / `.json` | varje dragning mot varje rör, med skäl |
| `gate91-markup-metrics.txt` | mot mängdarens egna streck, fem blad |
