# Bladet som gav noll meter: vad som faktiskt hände

Rapporterat från produktion: ett blad där sidan skrev *"0 av 12 rörbeteckningar som ritningen skriver ut fick
meter (0 %). Av 0 m ritat rör bar 0 m en identitet och 0 m ingen alls"*, med banderollen *"Bladet bar 254
markeringar från AutoCAD SHX Text, Michal Nikolajuk"*.

Bladet är identifierat ur korpusen på den signaturen - 254 anteckningar, 250 från `AutoCAD SHX Text` och 4 från
`Michal Nikolajuk`:

    data/styles/src/00 - skalstockar/V-50-1-A0001.pdf
    Priorn 4, VS-system, hus A, plan 0, del 1 · Kallängens förskola, Malmö stad · Sweco · 2019-02-17
    A0, 2384 × 1684 pt · SKALA 1:50 (A1), med skalstock 0-5 m

## Roten: teckentydningen gör siffror till bokstäver

Ritningen är plottad från AutoCAD med SHX-text: bokstäverna är streck, inte tecken, och läses tillbaka form för
form. På det här typsnittet blandas formerna ihop, och det syns rakt igenom läsningen:

| på ritningen | läst som | var |
|---|---|---|
| `1:50` | `1:S0` | titelrutans skalruta |
| `50` | `SO` | titelrutans skalfält |
| `00` `01` | `OO` `O1` | titelrutans plan- och delfält |
| `VARMVATTENLEDNING 55°C` | `VARMVAT TENLEDNING SS°E` | förklaringslistan |
| `VVC` | `VVE` | förklaringslistan |
| `GIPSAVSKILJARE` | `GIPSAVSKIL?ARE` | förklaringslistan |

Alltså: **5 → S, 0 → O, C → E, J → ?**.

### Följd 1: skalan föll bort på en bokstav

Skalkoden matchade `1\s*[:;]\s*([0-9Oo]{1,4})` och vek `O` till `0`, men inte `S` till `5`. Raden `1:S0`
kastades, bladet blev skalalöst, och utan skala finns ingen meter - därav "0 av 12". Bladet var inte tomt:
det bar 27 282 pt ritat rör, det gick bara inte att räkna om till meter.

**Rättat.** Efter `1:` har grammatiken redan avgjort att det står ett tal; där är en bokstav som ser ut som en
siffra en siffra. `digits_from_glyphs` viker hela förväxlingsmängden (O→0, S→5, I/l→1, B→8, Z→2, G→6). Bladet
läser nu sin egen skala: `TEXT_ONLY`, 1:50, 56,69 pt/m.

### Följd 2: förklaringslistan tappade tre av sex ledningsslag

Listan på bladet säger under LEDNINGAR: **S** spillvatten, **KV** kallvatten, **VV** varmvatten, **VVC**
varmvattencirkulation, **VP** värmebärare primär, **VS** värmebärare sekundär.

Läsningen tog bara `KV`, `VV` och `VVE` (VVC felläst). **S, VP och VS saknas helt.** Därför är `S3-110`,
`S3-160`, `VS213`, `VS313-35`, `VP113` inte rörnamn för läsningen, deras hänvisningslinjer röstar aldrig, och
deras familjer blir aldrig rörfamiljer - trots att `V-53B--FE-_S1` (spillvattnet) fick **11 ändmarkeringar**,
flest på hela bladet.

Och det är inte listlogiken som brister, utan samma teckentydning. Kodkolumnen står på x=2044,3, beskrivningen
på x≈2110. Mätt rad för rad:

| rad | kod läst | beskrivning läst |
|---|---|---|
| S spillvatten | **nej** (ingen rad alls på y=85,4) | ja, `SPILLVAT TENLEDNING` |
| KV, VV, VVC | ja | ja |
| VP värmebärare primär | ja (y=286,3) | **nej** |
| VS värmebärare sekundär | **nej** | **nej** |

Enstaka rader faller alltså bort ur läsningen helt - ett ensamt `S` i SHX-text blir ingen rad. Listan parar
ihop det den får; den får bara inte allt.

*Inte rättat.* Nästa steg.

## Vad läsningen tog i stället

Sju familjer accepterades som rör. 76 % av bläcket i dem ligger på arkitektlager:

| lager | bredd | längd pt | vad det är |
|---|---|---|---|
| `A-40-P-0000-xxxx-A\|A-27B---E-N` | 0,36 | 11 182 | arkitektens väggar |
| `A-40-P-0000-xxxx-A\|A-U-----EEN` | 0,72 | 9 334 | arkitektens linjer |
| `V-56B--FE-_VS1` | 1,44 | 3 636 | värme |
| `V-52BC-FE-_V1` | 1,44 | 1 426 | tappvatten |
| `V-52BB-FE-_V1` | 1,44 | 1 344 | tappvatten |
| `V-56B--FE-_VP1` | 1,44 | 189 | värme |

## Hänvisningslinjerna träffar rören - de vägs bara inte

34 av 50 ankare säger `leader_endpoint_touches_no_pipe_geometry`. Mätt: **varje sådan spets ligger på 0,00 pt
från främmande bläck** (ledarens egna streck borträknade). Renderat och tittat på: ledaren från `S3-110` slutar
med en ändmarkering exakt på det grova streckade spillvattenröret.

Bläcket de träffar ligger till 24 av 33 på familjer som hålls utanför som "text och ramar". De fem familjerna
bär 29 932 pt, varav bara ~3 900 pt är den understrykning och ram regeln faktiskt hittade; **22 100 pt är
varken glyf eller understrykning**, med enskilda banor upp till 418 pt långa. Regeln undantar hela
lager-och-penna-familjen på grund av en understrykning. På en ritning som skriver sina etiketter med samma
penna på samma lager som rören går rören med.

Läsningen har redan en räddningsväg - en oinskränkt läsning som får ta över om den inskränkta rasar - men här
misslyckas båda: den oinskränkta placerar 4 av 19 rörnamn, den inskränkta färre. Uteslutningen är alltså inte
huvudorsaken på det här bladet, men den är ett verkligt fel för sig.

## Var bladet står nu

Med skalan läst ur stämpeln: 12 rörnamn, 1 med meter, 9,55 m bekräftat av 481 m ritat. Bladet är mätbart och
redovisas ärligt - men läsningen av det är fortfarande dålig, och det är förklaringslistan som är näst på tur.

## Att göra härnäst, i ordning

1. **Teckentydningen på det här typsnittet.** Två fel i ett: former förväxlas (5/S, 0/O, C/E, J) och korta
   rader faller bort helt (ett ensamt `S`). Det andra är det som kostar mest - utan koden S, VP och VS är tre av
   bladets fyra ledningsslag inte rör. Skalan är lagad i sin egen position; resten sitter kvar.
2. **Förklaringslistan mot vad bladet ritar.** När koderna läses ska listan också kunna ta en kod vars
   beskrivning föll bort, och tvärtom - en halv rad är mer än ingen rad.
3. **Undantaget för skrivpennor.** Undanta den anteckningsbläck som faktiskt hittats - understrykningen, ramen,
   glyferna - inte varje streck som råkar dela lager och penna med den.
4. **Arkitektlager som rörfamiljer.** 76 % av det tagna bläcket är väggar. De får sina röster av ledare som
   stryker förbi; en ändmarkering borde väga tyngre än en passage.
