# Fynd: de W-blad som tappar mest

Uppdraget: gå igenom alla ritningar mot alla facit och rätta det som blir fel. Efter gate58 var täckningen
63,1 % och de fyra blad som tappade mest var W-50-1-A0113 (386 m saknas, 192 m falskt), A0111, A0134 och
A0132 - alla från samma kontor (268140), alla konturglyfer, samma lagerstandard.

Facit lästes först när läsningarna var körda; det som står här är rotorsaksanalys mot facit, inte regler ur
facit. Varje regel nedan mäts på bladets eget bläck och prövas i en egen syntetisk ritning.

## 0. Ett fel i måttstocken, inte i läsningen

A0113:s facit skriver `VS1-S13-12` där ritningen skriver `VS1-S13-12/W` (kontrollerat i bilden). A0134:s
facit skriver `VS1-S13-12/W` för samma slags rör, och alla tre skriver `VS1-S13-12 wallmounted` för en
tredje variant. Läsningen läser vad ritningen skriver - och fick 52 m "fel namn" och 81 m "saknat" för samma
rör. `facit_metrics.canon()` faller nu monteringssuffixen `/W`, `/WB` och ` wallmounted` till basen, som den
redan gjorde med isolerings- och ytskiktssuffix.

Omräkning av gate58 med den normaliseringen, utan att röra motorn:

| | gate58 (gammal måttstock) | gate58 (ny måttstock) |
|---|---:|---:|
| TÄCKNING | 63,08 % | **64,83 %** |
| FALSKHET | 18,00 % | **16,25 %** |
| beteckningsrecall | 71,8 % | 77,0 % |
| A0113 täckning / falskhet | 25,2 % / 37,1 % | 49,1 % / 13,3 % |

Nio blad rörde sig, alla W. Det är jämförelsegrunden för gate59.

## 1. Tillopp och retur: paret i samma penna (A0113)

VS1-pennan (`V-56B--FE--VS1-`, svart 1,44 streck-punkt) ritar 234 m på A0113; facit för VS1 är 226 m.
Läsningen ägde 139 m. De 95 oägda metrarna: 66 löper parallellt med en ägd linje på 17-19 pt avstånd, och
bland de *ägda* linjerna med samma identitet är det vanligaste inbördes avståndet 18-19 pt (674 + 492 pt
överlapp). Pennan ritar par - tillopp och retur - och etiketten sätts på den ena.

Regel (`pipes/ownership.py: _pair_unowned_runs`): pennans eget paravstånd mäts på det som redan är ägt
(toppen i fördelningen av avstånd mellan parallella ägda linjer med samma identitet; minst 40 pt eller tre
avstånd i stöd). Först då får en oägd ledning som löper parallellt med en ägd på det avståndet, längs minst
60 % av sin längd och där ingen andra identitet gör anspråk på mer än 15 %, ta identiteten -
`paired_run_at_the_drawings_pair_spacing`, med avstånd och andel som bevis. Ett streck i en streckad linje
räknas med halva glappet på var sida, så att fasen inte avgör andelen. Utan par i pennan paras ingenting.

Prov: `test_a_pipe_drawn_as_a_pair_is_named_on_both_lines.py` - returen tas, en linje på fel avstånd tas inte,
en linje mellan två identiteter tas inte.

A0113: 322,9 → 346,0 m ägda (VS1-S13-42: 35,8 → 49,0 av 73,8). Resten av VS1:s oägda meter ligger i
komponenter utan ägd granne alls (båda linjerna i paret oägda, eller ensamma stick till radiatorer) - det är
nästa fel, inte det här.

## 2. Bunten på två lager (A0134, A0132)

KV-, VV- och VVC-rören ritas i ett stråk om tre parallella linjer, 11 pt isär, och namnges av en staplad
etikett med tre rader och EN hänvisningslinje som slutar med ett streck över var linje. Läsningen fann två
kontakter på två lager (`V-52BB` och `V-52BC`), sökte den tredje bara på *samma penna som första kontakten*
och fann ingen bunt. `bundle_at` får nu leta partner på alla pennor hänvisningslinjen själv rörde vid.
Antalet måste fortfarande stämma exakt.

Effekt ensam på A0134: 18 ankare från "not unique" till "awaiting elimination" - inga meter, för bladet
namnger ingen av linjerna för sig och elimineringen har inget att gå på.

## 3. Lagerklassen säger vilket system pennan ritar (A0134: 92 → 231 m)

`system_layer_rank` matchade det korta tecknet V1 i lagernamnets svans - som KV1 och VV1 båda slutar på -
på båda lagren, och ingen rad blev unik. Men lagren *heter* `V-52BB-FE--V1-` och `V-52BC-FE--V1-`: 52BB är
tappkallvatten och 52BC tappvarmvatten i BSAB 96, klassindelningen svenska VVS-lager bär i namnet. Det är
en nationell tabell, inte en ritnings vana.

Regel (`semantics/attachment.py`): `LAYER_CLASS = {52BB: KV, 52BC: VV, 52BD: VVC}` som en matchnivå mellan
bokstavsmatch och svansmatch; ett system som börjar på klassens bokstäver (VVC på ett varmvattenlager) hör dit
svagare; en beteckning av annan familj på en klassad penna är en konflikt även om svansen råkar passa; och det
lager två rader gör anspråk på tillhör den rad vars lager namnger den bäst. Utan klass i namnen avgörs
ingenting - samma som förut.

Prov: `test_a_layers_class_tells_the_rows_of_a_bundle_apart.py` - med klass tar varje rad sin linje, utan
klass står stråket kvar som tvetydigt. `test_boundary_rules.py` uppdaterat: KV1 på 52BB ger nu `52BB`, inte `V1`.

A0134: 91,8 → 231,3 m av 350 (VV1-X7-16: 0 → 29,5 av 26,7; KV1-X7-16: 0,1 → 19,2 av 26,4; 21 ankare
`multi_row_layer_token_bijection`). Kvar: VVC1 (tredje raden, ingen egen kontakt, ritad på varmvattnets lager)
och VS1-S13-35 (81 m, 3 m ägda - ett annat fel).

## Grinden

gate59 = de tre reglerna tillsammans, blint på 59 blad, mot gate58 med den nya måttstocken (avsnitt 0).
Frysning: `hashmanifest-gate59.json`. Beslut i `GATE.md` när körningen är klar. Rör sig ett blad åt fel håll
delas grinden per regel.

## 4. Korsningen som blev en knut (A0134: VS1-S13-35, 3 → 22 m)

VS1-S13-35 stannade efter 3 av 81 meter. Två fel på samma ställe, båda i grafen.

**Punkten som inte fick peka.** Streck-punkt-linjen bryts där en annan ledning korsar den, och glappet är
pennans eget. Den fria änden före glappet är *punkten*, och en punkt har ingen egen riktning - regeln lät den
aldrig göra anspråk. Bortom glappet börjar strecket i en nod den korsande linjen redan delar, och ett ensidigt
anspråk konkurrerade med varje annat anspråk på *noden*. Ingen gjorde anspråk, kedjan slutade.
Nu: en punkt som ett streck har tagit ärver streckets riktning och ser vidare (två hopp, för streck-punkt-punkt),
och ett ensidigt anspråk konkurrerar med anspråken på samma *stycke*, inte på samma nod.

**Korsningen som blev en knut.** Där två ledningar korsas och pennans bitar råkar nudda varandra blir det en nod
med fyra armar. En kedja som gick in svängde ut i den andra ledningen. Nu: en nod där varje arm har sin raka
fortsättning på andra sidan (samma linje inom kollineäritetstoleransen, fria ändarna åt var sitt håll) är två
linjer som korsas, inte en knut - de ligger på olika höjd, och ritningen säger inget om en förbindelse. Varje
rakt par får sin egen nod på samma ställe. Bryggorna som landar på en nod som redan slagits ihop följer med
dit den tog vägen (`_merge_nodes` med aliastabell), annars tappar den andra ledningen sin brygga.

Prov: `test_a_run_goes_straight_through_a_crossing_whose_pieces_touch.py` (den etiketterade ledningen ägs hela
vägen, den korsande får inget namn) och `test_a_run_broken_where_another_line_crosses_goes_on.py`.

## 5. En förbindelse går före ett avstånd (parregelns spärr)

Med kedjan hel tog VS1-S13-35 22 m - och stannade vid en DN-gräns läsningen själv hade ritat: stigaren (DN35)
svängde ned i en vågrät ledning som parregeln redan hade gett DN22, för att en DN22-ledning låg på paravståndet
under den. På A0134 har VS1-S13-22 inte en meter i facit; läsningen hade 23,6.

Regel: grannen tvärs över glappet säger vilket par det är, grannen i noden säger vad ledningen sitter ihop med.
En oägd ledning som delar nod med en namngiven av *annan* identitet är knutens sak att avgöra, inte parets.
Prov: `test_a_run_joined_to_a_named_pipe_is_not_paired_away.py` (grafen byggd för hand, med och utan stigaren).

A0134 efter båda: 210,0 → 218,0 m ägda (VS1-S13-35: 3,4 → 22,1; VS1-S13-22: 11,7 och inte 23,6).
Kvar på den ledningen: fronten vid x=1295 där stigarens hörn möter den vågräta - `AMBIGUOUS_JUNCTION`, fyra
armar, och den vågräta oägd. Det är knutregeln, nästa rotorsak.

## 6. En linjes två ändar är två ställen (A0134: 218 → 259 m av 350)

De rundade böjarna exporteras som kedjor av mycket korta stycken - en tiondels punkt långa. Nodbygget slår ihop
ändpunkter inom 0,15 pt, och ett stycke kortare än så fick **båda** sina ändar i samma nod. Noden räknade
stycket två gånger: en vanlig böj kom ut som en fyrarmad knut, identiteten stannade där, och fronten skrevs
`UNOWNED_CONTINUATION` med grad fyra och tvåhundra oägda punkter bortom sig.

Mätt: 2 417 sådana slingor på A0134 och 2 337 på A0113, varav ~2 300 respektive ~2 250 blåste upp en nods grad.

Regel: nodbygget håller isär ett styckes egna ändar (`find_node(..., not_prim=...)`). Allt annat i toleransen
slås ihop som förut. Efter: 41 slingor kvar på A0134 (äkta nollängdsstycken).

Prov: `test_a_short_piece_has_two_ends.py` - en böj ritad som CAD-exporten ritar den är en kedja med två fria
ändar, ingen knut; före regeln gav samma böj graderna [1, 1, 2, 4, 4] med två slingor.

A0134: 218,0 → 258,7 m ägda av 350 (VS1-S13-12: 13,6 → 57,1; VS1-S13-12/W: 47,0 → 56,6). Några KV-rader
tappade meter (KV1-X7-16/W 19,2 → 13,0) - grinden avgör nettot.

## 7. Fyra blad som mätte noll: en rad som föll ur registret

W-50-1-A0022, A0023, A0031 och A0034 - spillvattenplaner under bottenplatta - läste 37-40 beteckningar var och
mätte **noll meter** av 161 i facit. Ingen rörfamilj valdes, varje ledare stod som
`leader_endpoint_touches_no_pipe_geometry`, och hela bladet föll.

Kedjan bakåt: rörfamiljerna röstas fram av bladets egna etiketter, men bara etiketter som *namnger rör* får
rösta, och en beteckning vars system inte står i bladets förklaringslista räknas inte som rörnamn. Bladets
lista säger `S1 SPILLVATTEN, ALLMÄNT I MARK` - men läsningen hade gjort `S1` till en **rubrik**, inte en post.
Utan S1 i vokabulären var `S1-P2-160` okänt, röstade inte, ingen penna blev rör, inget mättes.

Varför blev S1 en rubrik: en post paras ihop med sin beskrivning till höger, och kandidaterna hämtas ur ett
index med tvåpunktsband, en bandbredd åt vardera hållet. Beskrivningsraden `SPILLVATTEN, ALLMÄNT I MARK` ritas
med en hög bit i sig (`TT`-ligaturen bryter raden) och hamnar 2,1 pt högre än koden - inom det villkor som
avgör (sex tiondels radhöjd) men *utanför* indexet, på grund av var avrundningen råkade falla. D1 och S2 klarade
sig, S1 föll. Indexet var smalare än villkoret det tjänar.

Regel (`semantics/legend.py`): bandets räckvidd räknas ur villkoret (`0.6·h`), inte ur en konstant.

| blad | läst före | läst nu | facit |
|---|---:|---:|---:|
| W-50-1-A0022 | 0 m | 71,7 m | 72,8 m |
| W-50-1-A0023 | 0 m | 42,6 m | 36,4 m |
| W-50-1-A0031 | 0 m | 6,9 m | 7,0 m |
| W-50-1-A0034 | 0 m | 44,1 m | 44,6 m |

Fyra blad från noll till nära facit. Hela sviten: 531. Brandväggen: PASS.

## 8. Skrafferade ytor: 1 074 meter som facit är oense om

Ett rör som går inne i en skrafferad yta mäts men läggs utanför den horisontella mängden och redovisas för sig
(`in_hatched_area_m`; kryssrutan "Räkna med skrafferade ytor" i tabellen tar med den). Skälet står i
`profile/hatch.py`: skraffering markerar ofta det som ligger utanför entreprenaden.

Över korpusen är det **1 074 m på 26 blad** av 10 883 ägda. Frågan är om facit räknar dem, och svaret är olika
på olika blad:

| blad | referens | ägt | i skraffering | saknas mot facit |
|---|---:|---:|---:|---:|
| W-50-1-A0124 | 247 | 81 | 149 | 166 |
| W-50-1-A0114 | 326 | 223 | 130 | 103 |
| W-50-1-A0131 | 201 | 112 | 118 | 89 |
| W-50-1-A0121 | 171 | 127 | 106 | 45 |
| E | 51 | 49 | 40 | 1 |

På E stämmer den nuvarande regeln på metern: skrafferingen ligger som band runt bladets egen del - de
angränsande delarna av byggnaden - och rören som löper in i dem fortsätter ut ur bladet. Mängdaren räknade
insidan. På A0124 täcker skrafferingen bladets *egen* plan, väggar och golv, och de röda (undantagna) rören är
mitt i installationen. Där räknade mängdaren dem.

Prövade skiljelinjer som **inte** håller: om etiketten själv står inne i skrafferingen (gäller båda bladen: 40 m
på E, 145 m på A0124), och hur stor andel av bladets rör som ligger i skraffering (45 % mot 64 %).

Alltså: ingen ändring. Att slå på inräkning skulle rätta A0124 och förstöra E. Det som behövs är ett kännetecken
i ritningen som skiljer "angränsande del" från "vägg och golv i den här delen" - orienteringsplanen i hörnet
pekar ut bladets egen del, och det är nästa sak att pröva. Tills dess står valet hos den som räknar, och
tabellen visar summan.

**Mätt, inte antaget** (gate62, 59 blad): att räkna in varje skrafferad meter ger täckning 76,82 → 79,76 % och
falskhet 19,68 → **26,83 %**. Tre meter vunna kostar sju falska. Och även på bladen där facit räknar dem är det
inte rena vinster: A0124 ägt 80,7 → 151,5 m men falskt 21,2 → 99,7 - av de 149 metrarna hör 71 hemma i facit
och 78 gör det inte. Det är inte en tröskel som sitter fel utan en identitetsfråga: metrarna inne i
skrafferingen får fel namn. Regeln står alltså kvar som den är, och kryssrutan är kvar där valet hör hemma.


## 9. Var de 200 metrarna på W-50-1-A0111 ligger

Bladet är korpusens största enskilda tapp: facit 519,5 m, ägt 298,4 (gate62). Uppmätt på det ritade:

| | meter |
|---|---:|
| bekräftat | 366 |
| tvetydigt | 42 |
| oägt, på pennor som togs som rör | 186 |
| förkastade pennor (V-lager) | 82 |

De 186 oägda metrarna ligger inte i utkanten utan på egna pennor: `V-52B---T--V2--` 74,6 m, `V-56B--FE--VS1-`
33,8, `V-56B--KE--VS1--` 30,9, `V-56B---T--VP1--` 26,2. Lagernamnen namnger system (V2, VS1, VP1) - men ingen
etikett når dem.

Två hypoteser prövade och **förkastade**:

- *Identiteten fortsätter i en annan penna* (uppgift #63). Om den oägda pennan mötte den ägda ände mot ände
  skulle identiteten kunna löpa vidare. Mätt: bara **1,5 m** oägd längd ligger vid en sådan skarv där lagret
  dessutom namnger samma system (`V-56B--KE--VS1--` möter `V-56B--FE--VS1-`, exakt lagerträff). Resten möts
  aldrig.
- *Den oägda pennan går parallellt med den ägda* (samma rör ritat två gånger). Mätt på `V-52B---T--V2--`: av
  74,6 m löper **2,7 m** parallellt med en ägd linje inom 60 pt. Pennan ritar egen sträckning, inte en kopia.

Det som återstår är alltså inte en sakfråga om geometri utan om vem som får namnge: 186 m rör som ritningen
ritar på lager som namnger systemet, utan att någon etikett pekar på dem. En regel som gav dem systemets namn
utan dimension skulle inte matcha facit ändå - facit skriver `KV2-X7-32`, inte `KV2-X7`.

Och bredvid det: **67 av 324 etiketter** på bladet slutar utan att röra något rör. De ligger inte nästan rätt -
medianavståndet från en fäst etikett till närmaste rör är 1,2 pt, från en fästlös 27,7 pt. Där de landar finns
ritat något på en *finare* penna (0,48 pt på samma V-lager) som förkastats med skälet NO_CONTINUOUS_RUN: 82 m på
V-lager, varav 52 m har etikettändar på sig.

Men den pennan ritar inte rör. Klumpar man ihop dess streck faller `V-56B--FE--VS1-` 0,48 pt sönder i **26
klumpar**, var och en 128 streck om 0,55 pt i en låda på ~50x50 pt: apparatsymboler, inte sträckor. Etiketterna
som landar där pekar på en apparat - en radiator, en värmeväxlare - och en apparat är ingen rörsträcka.
NO_CONTINUOUS_RUN är alltså rätt beslut, och de 67 fästlösa etiketterna är till stor del etiketter som inte
namnger något rör. Tråden är stängd; det som återstår på A0111 är de 186 oägda metrarna ovan.


## 10. Vad ritningen säger och vad mängdaren räknade: de förklarade kopplingsledningarna

Facit är inte en sanning om ritningen, det är en export av någons markeringar: kolumnerna i `facit.xlsx` heter
Sidetikett, Färg, Kommentarer, Längd. Ett rör som ingen markerade finns inte i facit även om det står ritat.

Det syns tydligast på de blad där läsningen äger flera gånger facit:

| blad | facit | ägt | kvot |
|---|---:|---:|---:|
| V-50-1-A0521 | 68,5 | 239,8 | 3,50 |
| V-50-1-A0321 | 76,9 | 213,2 | 2,77 |
| V-50-1-A0421 | 129,9 | 246,9 | 1,90 |
| V-50-1-A0121 | 101,5 | 192,3 | 1,89 |
| V-50-1-A0122 | 321,1 | 524,1 | 1,63 |
| V-50-1-A0221 | 55,8 | 85,0 | 1,52 |

Sex blad av 59. På A0521 äger `KV01-X31-16` 71,8 m **utan en enda etikett** - varenda meter kommer ur bladets
egen tabell "KOPPLINGSLEDNINGAR FRÅN FÖRDELARE TILL APPARAT ENLIGT TABELL" - och facit har 0,5 m. Läsningen gör
rätt: regeln står på bladet. Mängdaren valde att inte mäta dem där.

**Mätt över korpusen** (gate63, 59 blad):

| | täckning | falskhet |
|---|---:|---:|
| allt förklarat räknas (förval) | **79,81 %** | 19,86 % |
| förklarat utan egen etikett räknas bort | 72,25 % | 18,04 % |
| allt förklarat räknas bort | 66,80 % | 16,09 % |

De förklarade metrarna bär 1 483 m rätt mot 429 m fel. Förvalet står alltså kvar - men på ett enskilt blad kan
det vara tvärtom: A0521 tappar 112,6 m falskt och 0,5 m rätt om de räknas bort. Därför är det ett val i
tabellen, "Räkna med förklarade kopplingsledningar", vid sidan av det för skrafferade ytor, och exporten följer
skärmen.


## 11. Fyra beteckningar på en rad, en linje under dem - och ingen hänvisning alls

V-50-1-A0423 är korpusens värsta enskilda överdrag: `VS21-S13-15` får 111,8 m mot facit 36,6, medan stammen
`VS21-S13-22-F60` står på 1,7 m mot facit 82,6. Åttio meter under fel rubrik.

Etiketten ser ut så här:

```
VS21-S13   SF01-P5  SF01-P5  S01-P5
──────────────────────────────────      <- en linje, som svänger ned till röret i vänsterkanten
 22-F60     110L     110L     110
```

Två fel, båda generiska:

1. **Måttraden med en klass i.** "22-F60" är dimension 22 med isolerklass F60, men regeln för en måttrad krävde
   att tillägget efter siffran var sifferfritt. Raden lästes som en egen beteckning, och `VS21-S13` blev kvar
   utan dimension. Rättat: ett tillägg som börjar med en bokstav får bära en siffra ("22-F60", "-PE1"), medan ett
   kryss följt av siffror är ett andra mått och ingen klass ("600X300"). Beteckningen läses nu rätt.

2. **Linjen under raden är ritad i bitar, en per beteckning, var och en på sitt eget systems lager.** Mätt:
   `V-56B---T-_VS2x-` 1109,9-1159,3 (under VS21-S13), `V-53BB--T-_SFxx` 1159,4-1197,5 och 1197,4-1235,4 (under
   de två SF01), `V-53BBB-T-_Sxx` 1235,4-1268,4 (under S01). Bitarna möts, men kedjebygget kräver samma penna,
   så det stannar efter 33 pt. Och bitens vänstra ände är ingen fri ände - den svänger ned i hänvisningslinjen -
   så regeln "raden är skriven på en linje som fortsätter till röret" hittar ingen start. Blocket får **noll**
   hänvisningslinjer, och fyra beteckningar blir utan ankare.

Att bitarna ligger på systemets eget lager är för övrigt ritningens egen upplysning om vilken beteckning som
äger vilken bit - och därmed vilken av de fyra hänvisningen talar för.

Nästa steg, med egen grind: låt en baslinjebit som svänger ned i en linje ge en start vid hörnet, och låt den
starten bära bitens x-spann så att bara beteckningen ovanför biten äger hänvisningen. Motsvarande regel finns
redan för staplade rader med var sin understrykning (`_rows_owning_leader`); det som saknas är den för rader som
står bredvid varandra.
---

## §12 Förklaringslistan som intygar sig själv - och de elva bladen som ger noll meter

Grinden läser 59 blad. Korpussvepet (`engine/tools/corpus_sweep.py`) läser de 284 unika ritnings-PDF:er som
ligger lokalt, utan facit och utan jämförelse, och skriver vad läsningen själv säger. Det är där det här
fyndet kom ifrån: ett fel som inte finns på något av grindbladen, men på ritningar från ett annat kontor.

**`R9UHA10-CLB001-004.pdf`: 113 beteckningar, 76 hänvisningslinjer, 0,0 m.**

Kedjan bakåt:

1. `pipe-code-anchors.json`: alla 76 ankare står som `NO_PIPE_ATTACHMENT`, skäl
   `leader_endpoint_touches_no_pipe_geometry`. Hänvisningslinjerna hittades alltså - de landade bara inte på
   någon rörgeometri.
2. `drawing-profile.json`: `representation_families: []`. Det finns ingen rörgeometri att landa på.
3. Men `tick_votes` är full av lager som uppenbart är rörlager: `V-52B-FE-_V01-KV--` (12 märken),
   `V-52B-FE-_V01-VV--` (11), `V-56B--FE-_-VS21--` (10), `V-52B-FE-_V01-VVC01--` (6). Ledarna *rör* rören.
4. `votes` är däremot tom. Skillnaden mellan de två räkningarna är en enda rad i `pipeline.py`: rösterna räknas
   bara för en hänvisningslinje vars etikettblock innehåller ett **rörnamn** (`pipe_labels`). Bladet hade inga.
5. `pipe_labels` utesluter koder som bladets egen förklaringslista aldrig nämner (`_unknown_to_the_legend`).
   Bladets lista är en komponent- och materiallista: `SA01`, `SPO1`, `P1`, `P2`, `R1`, `R61`, `S13`, `HSP`.
   Den nämner inte `KV01`, `VV01`, `VVC01`, `VS21`, `SP01` eller `AV201` - alltså inte ett enda rör på bladet.

Regeln har ett skyddsvillkor just för det här: den gäller bara när listan bevisligen känner igen bladets
ordförråd, minst tre kända systemkoder. Villkoret var uppfyllt - och det var där felet satt. **Listans egna
rader läses som beteckningar de också.** Alla tolv "kända" koder visade sig ligga på x ≈ 2049, det vill säga
inne i listans egen kolumn:

    SAO1L [2049.6, 359.2 …]   R71 [2049.2, 577.2 …]   S1  [2049.6, 591.5 …]   P1 [2049.2, 504.4 …]
    SA01  [2049.6, 344.9 …]   R2  [2049.2, 548.0 …]   R61 [2049.2, 562.7 …]   S2 [2049.6, 605.8 …]
    SPO1L [2049.6, 402.0 …]   R1  [2049.2, 533.2 …]   S13 [2049.6, 634.5 …]   P2 [2049.2, 518.7 …]

Ingen enda av dem står ute på ritningen. Listan hade intygat sin egen kompetens, och på den grunden raderat
bladets alla rör.

**Rättningen** är att ställa frågan till etiketterna ute på planen: `DrawingLegend.holds(bbox)` säger om en
etikett ligger inne i listans ruta, och `_unknown_to_the_legend` räknar bara kända koder utanför den. Ligger
alla kända koder i listan säger listan ingenting om bladet, och stänger inte ute något. Maskineriet fanns redan
i `assign_roles`, i två kopior; de går nu genom samma regel.

Efter: **10 rader, 180,2 m bekräftat**, täckning 23,8 %. Grind 66 rörde noll av de 59 referensbladen
(TÄCKNING 79,82 %, FALSKHET 19,93 % - identiskt med gate65), så vinsten är gratis. ACCEPT.

### Vad svepet i övrigt visar hittills

Av de 29 första ritningarna ger **elva noll meter**, och de gör det av olika skäl - det är fyra separata
uppgifter, inte en:

| skäl | blad | vad läsningen säger |
|---|---|---|
| listan intygade sig själv | `R9UHA10-CLB001-004` | 113 beteckningar, 0 m → **rättat, 180,2 m** |
| skalan står i konflikt | `V-530-1-010-100`, `V-520-1-010-100` | `scale_state: CONFLICT`, rader finns men inga meter |
| skalan saknas | `V-50-8-B0001` (64 bet.), `V-50-8-001` (86 bet., `TEXT_ONLY`) | inget att mäta med |
| skala verifierad, ändå noll | `V-50-6-B0214`, `V-50-6-B0314`, `V-50-1-B0514`, `V-50-1-020 HT` | samma klass som §12 ovan, ännu inte rotorsakad |

Dessutom: en ritning (`V-500-1-010-100.pdf`) låste svepet i sju minuter utan att skriva en rad, och en
(`V-53-1-00 RIVNING.pdf`) gick inte att läsa alls. Den första bär nu en egen process med tidsgräns och blir en
`TIMEOUT`-rad i stället för en körning som står still.


## §13 Den minsta dimensionen äter den största: 628 meter för mycket, 813 meter som saknas

`OVER_EXTENT_OVER_PROPAGATED` är den största posten i felkatalogen - 213 beteckningar, **1 858 m för mycket**
fördelat över gate66. Uppgift #67 beskrev den som "när böjen kopplas ihop tar en etikett hela stråket". Det
stämmer på enskilda blad, men det är inte formen på felet. Formen går att mäta.

**Mätningen.** För varje blad, gruppera referensens beteckningar på stam - allt utom sista talet, alltså system
och material (`VS1-S13-12`, `VS1-S13-15`, `VS1-S13-22` → stammen `VS1-S13`). Behåll de stammar där bladet
skriver mer än en dimension, och fråga var i storleksordningen felen ligger. 519 beteckningar över 59 blad:

| plats i stammen | n | OVER | överskott | saknat (PARTIAL) |
|---|---:|---:|---:|---:|
| **minsta dimensionen** | 177 | 67 (37,9 %) | **+627,6 m** | −235,4 m |
| mellanliggande | 165 | 59 (35,8 %) | +328,5 m | −459,2 m |
| **största dimensionen** | 177 | 22 (12,4 %) | +177,6 m | **−813,0 m** |

Det är inte slumpmässig spridning. Den minsta dimensionen i ett system propagerar för långt tre gånger så ofta
som den största, och den största saknar tre och en halv gång så mycket som den minsta. **Den lilla äter den
stora.** Det stämmer med hur rör dras: stammen går från stigaren och avgreningarna blir mindre, avgreningarnas
etiketter är fler och sitter närmare den ritade geometrin, och deras identitet rinner uppströms in i stammen.

**Två hypoteser som mätningen förkastade.**

*"En ensam etikett växer för långt."* Tvärtom: beteckningar med en enda etikett är OVER i 16,0 % av fallen och
bär 77,6 m överskott; de med tre eller fler är OVER i 26,2 % och bär 383,3 m. Ett enskilt blad kan se ut så -
`W-50-1-A0132` har en `VS1-S13-15` som växer 33,1 m ur en enda etikett längst ned till vänster, tvärs över hela
bladet - men korpusen säger nej.

*"Etiketten fastnade på fel linje i paret."* Också nej, åtminstone inte på A0132. Bladets enda
`VS1-S13-22/W`-etikett sitter på (1504, 398) och dess hänvisningslinje slutar med ett ändmärke på
**(1394,04, 300,16)**, mitt på den lodräta linjen - `VERIFIED_PIPE_ATTACHMENT`, avstånd 0,84 pt. Fästet är rätt.
Kedjan klipps vid etikettens eget märke (`REAL_DN_BOUNDARY`, `from_dn: 22, to_dn: 12`), och nedanför märket ägs
samma linje av `VS1-S13-12` med **fyra egna etiketter** längs sig. Läsningen gör alltså det den ska på den
linjen; de 61,9 m facit ger DN 22 ligger inte där.

**Vad som därmed står kvar som nästa grind.** Vid en knut där en märkt kedja möter en gren med en annan märkt
dimension ska den *mindre* dimensionen inte fortsätta in i den grövre stammen. Ett rör blir inte grövre
nedströms en avgrening, och när två märkta storlekar möts vid en knut är det den grövre som äger stammen.
Regeln kommer ur hur rör dras och ur bladets egna två etiketter - ingen ritningsspecifik konstant - och den har
en mätbar riktning att gå åt: 813 m saknade meter på de grövsta dimensionerna.
