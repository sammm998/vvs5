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

> **Rättelse.** Den första versionen av det här avsnittet räknade fyra luckor. Två av dem var fel, och båda
> felen var mina. Standardtabellerna FINNS byggda, och rivningsmarkeringarna finns inte i materialet - mitt
> ordsök räknade 29 träffar på `RIVNING` som alla satt inne i ordet BESK**RIVNING**.

**1. Omfattningsmarkeringar.** `BEF`, en hel kod inom parentes där förklaringen säger "( ) AVSER BEFINTLIGT",
`(PB)`/`(PWC)` för prefabricerade enheter. Ingen av dem är ny meter, och ingenting i geometrin skiljer dem från
det som ska byggas. **Byggt** - se nedan.

**2. Avslutande `L`/`V` på dimensionen** (`110L`, `100V` = luftning). **Byggt**, och det var värre än väntat:
`S01-P5-110L` delade sig i två rader under samma namn på flera blad, en med dimension och en utan, med 19,1 m
på oprissättbara rader.

**3. Standardtabeller för omärkt rör - fanns redan.** `semantics/declarations.py` läser bladets skrivna regel
(KOPPLINGSLEDNINGAR ... OM INGET ANNAT ANGES, med beteckningsstammar och talkolumner) och namnger de rör
ingen etikett når. I korpusen äger den regeln **1 674,7 m på 33 blad**. Jag redovisade den som en lucka och
det var fel.

Det som verkligen saknas är smalare: `TRIGGER_WORDS` känner en enda tabellsort. Kunskapsbasen nämner två till,
AVLOPPSANSLUTNINGAR och SCHAKTTABELL/STAMTABELL. Sökt i 55 blads verkliga text: **noll förekomster** av båda.
Att bygga dem nu vore att bygga mot ingenting.

**4. Rivningsmarkering och arbetsområde** - kryss längs en linje, och ombyggnadssetens streckade rektangel.
Geometri, inte text. Sökt i korpusen: **noll** förekomster av RIVAS, ARBETSOMR, DEMONTER, PREFAB och BEFINTLIG
i verklig text. Det finns alltså inget exempel att bygga mot och inget att pröva mot, och att skriva en
detektor blind bryter mot ordningen som gäller här: bevisa först, ändra sedan.

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
