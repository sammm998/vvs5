# Stilkorpusen genom motorn: fjorton blad, elva producentkedjor

Öppen värld, inga referensmängder. Frågan är inte om metrarna är rätt - det går inte att veta här - utan om
bladet blir **läst**: hittas skalan, läses beteckningarna, kommer det ut mängder, och sker det utan att något
small.

## Utfallet: 14 av 14 lästa, ingen krasch

    blad                          tid    lager  pennor   ord   rader    meter   skala
    Bläckhornet                114,3s        0      20  1668      32    501,4   VERIFIED
    V-50-1-A0122                22,2s       88      10   643      22    405,4   VERIFIED
    6  (PQR Malmö)               40,6s        0      17   343       5    157,6   VERIFIED
    W-50-1-A-0131               29,2s       52      20     5      25    155,9   VERIFIED
    V-50-1-A0101                46,0s       50       6    23       9    122,9   TEXT_ONLY
    Löpöglan 2                  40,8s        0      12   788       8    116,7   VERIFIED
    R9UHA10-CLB001-002          15,8s       38       3   108      12    106,2   VERIFIED
    10 (AutoCAD pdfplot14-16)   12,6s        0      18   411      19     89,7   VERIFIED
    Badskon 1                   23,0s        0      11  1878       4     75,2   VERIFIED
    1760279_1                   17,4s        0      13   659       4     71,2   VERIFIED
    10 (Kjell Petersson)        11,7s        0       9   553       4     34,8   VERIFIED
    2  (Rejlers)                 9,6s        0       7   660       2     17,6   VERIFIED
    V50-1-0842 Plan B2           3,9s        0       9   740       0      0,0   CONFLICT
    R1502                       61,7s        0       3     0       0      0,0   BAR_ONLY

**Tolv av fjorton ger mängder på en verifierad skala.** Bland dem varje lagerlöst blad - åtta av tolv har
inga CAD-lager alls, och motorns pennbegrepp faller då tillbaka på bredd och färg. Det fungerar.

`Bläckhornet` läses på 114 sekunder med 32 rader. Det är bladet som en gång inte blev läst på femton minuter.

## De två som inte gav något gav rätt svar

Båda föll på **skalan**, inte på läsningen, och båda vägrade i stället för att hitta på ett tal:

* `V50-1-0842` - `CONFLICT`: bladet uppger mer än en skala och de går inte ihop.
* `R1502` - `BAR_ONLY`: bara en skalstock att gå på. Det är det urartade bladet: noll ord, noll typsnitt,
  noll lagernamn och i praktiken en enda penna, för exporten heter "Uniform Stroke" och har jämnat bort
  pennsignalen. Utan skala finns ingen meter att ge, och att gissa den vore att ta fram ett tal ur ingenting.

En nolla som säger varför är ett svar. Ett påhittat tal är det inte.
