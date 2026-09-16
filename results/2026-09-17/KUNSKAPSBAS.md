# Den svenska VVS-kunskapsbasen mot motorn: vad som redan finns, vad som fattas

`swedish-vvs-drawings` är en kunskapsbas över svensk ritpraxis - systembeteckningar, etikettgrammatik,
linjetyper, streckmarkering, symboler, ritningsnummer - byggd ur SIS 32260, Bygghandlingar 90 och AMA plus en
genomgång av riktiga blad från nio projektörskontor 2018-2026. 24 JSON-tabeller, sex referenstexter, fem skript.

Den leder med samma regel som motorn redan drivs av: **förklaringen på bladet går före tabellen, och en miss i
tabellen är okänd - inte ogiltig.** Det är ett gott tecken, och det gjorde granskningen enkel: frågan blev inte
"är det här sant" utan "gör vi redan det här".

## Vad som redan finns i motorn

Jag prövade påstående för påstående mot koden i stället för att anta. Det mesta var på plats:

| Kunskapsbasen säger | Motorn |
|---|---|
| Cirkulerande system är par: VP, VS, KB, KM, ÅV, FV, FK, KP, VÅV, FJV, FJK | `CIRCULATING_SYSTEMS` - **exakt samma mängd, åt båda hållen** |
| KV, VV, VVC, S, D bär alltid egen etikett; leta ingen tvilling | `OWN_LABEL_SYSTEMS` - exakt samma |
| Självfallssystem: S och kontorsvarianterna SA, SP, SF, samt D | `GRAVITY_SYSTEMS` - exakt samma |
| Bara VG bär fallriktning; CL är monteringshöjd och säger ingenting | `VG_TAGS` mot `CL_TAGS`, med just den skillnaden utskriven |
| `Nx` framför koden är ett antal, inte dekoration | `strip_count_prefix`, `multiplier` på beteckningen, och `multi_row_parallel_count_bijection` som kräver att antalet stämmer med antalet ritade parallella rör |
| Å Ä Ö är lagliga i systemkoder; att vika till ASCII förstör beteckningar | `[A-ZÅÄÖ]` genomgående i grammatiken |
| Löser signalerna inte tvisten: närmaste segment, låg konfidens, syns för granskning | `_nearest()` i `direction.py`, med skälet utskrivet i klartext |
| Etiketten kan vara delad över rader; gruppera per hänvisning före tolkning | radgruppering per block och ledare |

Det här är inte sammanträffanden - riktningskaskaden vattengång → dimension → läge är samma ordning som
kunskapsbasens 1-2-3. Den tidigare PipeStudio-överföringen har uppenbarligen redan burit över det mesta.

## Vad kunskapsbasen säger som motorn INTE får ta

En av kunskapsbasens regler är uttryckligen förbjuden i det här arbetet: **"den större dimensionen är uppströms
och etiketten hör till den mindre"**. Det är precis den `större-DN-vinner`-regel som din specifikation
förbjöd att importera. Den står kvar i kunskapsbasen som regel 2, och den tas inte in.

Fallriktning ur vattengång är däremot inte samma sak: `VG+1.91` är ett tryckt tal på bladet, alltså bevis, och
den vägen är redan implementerad.

## Vad som fattas, och vad det kostar

Fyra saker hittade jag inte i läsningen alls:

1. **Omfattningsmarkeringar.** `BEF` = befintlig installation, en hel kod inom parentes `(S1)` där
   förklaringen säger "( ) AVSER BEFINTLIGT", `(PB)`/`(PWC)` = prefabricerat badrum vars rör är
   fabriksleverans. Ingen av dem är ny meter att bygga, och **ingenting i geometrin skiljer dem** från det som
   ska byggas. Räknas de in blir mängden för stor; undantas de i tysthet blir den för liten. Båda felen ser
   likadana ut på skärmen: inget.
2. **Rivningsmarkering** - linje med upprepade kryss, och ombyggnadssetens streckade ARBETSOMRÅDE. Geometri,
   inte text.
3. **Avslutande `L`/`V` på dimensionen** (`110L`, `100V` = luftning) - accepteras som siffra och röret flaggas
   som luftledning.
4. **Standardtabeller för omärkt rör** - KOPPLINGSLEDNINGAR, AVLOPPSANSLUTNINGAR, SCHAKTTABELL ger dimensioner
   per apparattyp och per våning. En läsning som bara läser etiketter tappar allt det.

## Vad som är gjort här

Punkt 1, klassificeringen, som en ren modul med prov: `vvs_engine/semantics/scope.py`.

Den avgör ingenting på egen hand. **Markeringen betyder det förklaringen säger att den betyder**, och hittar
läsningen en markering som bladet inte förklarar blir raden `OKAND_MARKERING` och går till granskning - den
räknas varken som ny eller undantas. En ensam bokstav inom parentes sist i en beteckning behandlas dessutom
inte som omfattning alls om förklaringen inte nämnt just den, eftersom ritspråket använder samma plats för
annat - luftningens `L` bland annat.

Nio prov täcker: omarkerad rad är ny; oförklarad parentes är okänd och går till granskning; förklarad parentes
tros; prefab när förklaringen definierar `PB`; oförklarad tvåbokstavskod gissas inte till prefab; rivning och
befintligt är olika svar; `(S1)` och `S1` är samma identitet i två omfattningar; vanliga förklaringsrader blir
inte råkade markeringar; ingen förklaring alls är inget fel.

**Modulen är ännu inte inkopplad i läsningen.** Den klassificerar, men ingen mängdrad bär omfattning än. Att
koppla in den ändrar mängder och ska därför grindas för sig - det är nästa steg, inte gjort.
