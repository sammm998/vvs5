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

## Vattengången: första försöket, mätt och backat

Riktningsspecifikationen säger att vattengången går före dimensionen. Den kopplades in på det ställe i ägandet
där dimensionen redan svarar - knuten, där en stams identitet rinner ut i en arm fram till dess ritade gräns.

Två fynd, i ordning.

**Vattengången fanns, men hade aldrig fått svara.** Bladen skriver `VG` i etikettblocken: 71 etiketter på blad
A, 46 på E, 8 på C. Signalen läste system som hela token - `S1`, `S3` - och `S1` finns inte bland
självfallssystemen, som stavas `S`. Löpnumret säger *vilken* stam, bokstäverna vilket *slags* system. Rättat
(`system_letters`) svarade vattengången 41 gånger på blad A och 30 på E.

**Och svaret blev sämre.** Mätt mot referensen, blad för blad:

| blad | täckning 67 → 68 | falskt 67 → 68 |
|---|---|---|
| A | 97,8 % → **92,1 %** | 1,2 % → **6,9 %** |
| E | 97,3 % → **92,2 %** | 1,8 % → **6,8 %** |
| C | 99,9 % → 99,9 % | 0,6 % → 0,6 % |

Ändringen backades.

**Varför den var fel, och vad det lär.** Regeln jämförde fel par. Vid knuten avgörs *sträckan fram till
stumpens ritade gräns*. Stumpens etikett beskriver inte den sträckan - den beskriver det som ligger **bortom**
gränsen, stigaren eller grenen som etiketten pekar på. Dess vattengång hör alltså till den andra sidan av
gränsen. Att väga den mot stammens vattengång är att jämföra två punkter som knuten inte ordnar.

Det är samma sak specifikationen själv säger med andra ord: *etiketten beskriver det som kommer efter den*. En
signal som är riktig i sak blir fel när den läggs på fel par av segment, och det syns bara genom att mäta.

Det utesluter också nästa kandidat: att låta det högst liggande stråket ta förbindelsen mellan två namngivna
stråk. På självfall är det **grövre** röret nedströms - flödet växer neråt - så "uppströms bär vidare" är
samma riktning som nyss förlorade metrar. Referensen säger tvärtom att det grövre bär vidare, och skälet är
ritat: en dimensionsändring ritas som en del, och där ingen del står ritad har stråket inte bytt dimension.

Kvar i trädet: `system_letters` (`S1` *är* ett självfallssystem - sant oberoende av referensen) och
`water_level`/`flows_downhill` med sina prov, eftersom de hör till `choose_segment`, där ramen stämmer.
Ägandeguarden och rördragningen genom `pipeline.py` är backade.

**Hela korpusen sa samma sak.** Grind 68 mot grind 67, 59 blad, 11 399 m i referensen:

| mått | grind 67 | grind 68 (vattengång) |
|---|---|---|
| täckning | **79,25 %** | 78,96 % |
| falskt ägande | **15,82 %** | 16,14 % |
| FULL / PARTIAL / OVER / MISSED / WRONG | **173** / **199** / **177** / **152** / 88 | 166 / 203 / 180 / 152 / 88 |

Sämre på varje mått. Backat.

## Staplingskonventionen: mätt, och korpusen kan inte avgöra

Användaren gav regeln: staplas flera beteckningar vid en hänvisningslinje är det översta röret det som ligger
längst bort, och det nedersta det närmaste. Den lades in som **sista** ledet i en kedja som redan fanns -
uteslutning (en linje som namnges för sig någon annanstans pinnar bunten) går före, och bladets egen vana
(ordningen läst ur de buntar bladet själv avgjort) går före den. Konventionen svarar bara när bladet inte sagt
någonting alls, och skälet heter då `multi_row_bundle_read_by_the_stacking_convention`.

Grind 69 mot grind 67, 59 blad:

| mått | grind 67 | grind 69 (konventionen) |
|---|---|---|
| täckning | 79,25 % | 79,23 % |
| falskt ägande | 15,82 % | 15,85 % |
| FULL / PARTIAL / OVER / MISSED / WRONG | 173 / 199 / 177 / 152 / 88 | **174** / 200 / **176** / **151** / 89 |
| beteckningar funna | 87,72 % | **87,87 %** |

**Två blad av 59 ändrades.** På det ena (V-50-1-A0123) blir en MISSED en OVER - röret hittas men dras för
långt - och täckningen stiger 0,2 procentenheter. På det andra (V-50-1-A0521) faller täckningen 4,3
procentenheter, och det bladet har redan 188 % falskt ägande: dess referens mäter en halvmeter där läsningen
äger femtiofem, så ingenting på det bladet väger något.

Slutsatsen är inte att regeln är fel. Slutsatsen är att **korpusen inte kan avgöra den**: den får svara på två
blad, och det ena är trasigt av andra skäl. Den ligger därför utanför trädet tills det finns ett blad där en
staplad etikett står över en bunt och referensen skiljer raderna åt. Att lägga in den på det här underlaget
vore att göra läsningen säkrare på en fråga mätningen inte har svarat på.

## Hänvisningslinjens slutstreck: rätt på ett blad, fel över korpusen

Korpusens största enskilda tapp ligger på V-50-1-A0423: DN22 har 82,6 m i referensen och fick 1,66, medan
DN15 har 36,6 och fick 105,72. Etiketterna följdes hela vägen ned. Fyra radiatoranslutningar drar sin
hänvisningslinje förbi stammen på väg till sitt eget stråk; ritaren sätter ett streck där linjen korsar och
ett streck där den slutar, och läsningen tog båda som fäste. En kedja med ett enda frö bekräftas i sin helhet,
så ett ensamt korsstreck gjorde trettiofem meter stam till radiatoranslutningens dimension.

Regeln som prövades: *har ritaren markerat var linjen slutar har hon sagt vad den pekar på, och då är
korsstrecken bara vägen dit.* På just det bladet gjorde den precis vad den skulle - 46,8 m falskt ägande bort,
noll täckning tappad.

Grind 70 mot grind 67, 59 blad:

| mått | grind 67 | grind 70 (slutstrecket) |
|---|---|---|
| täckning | **79,25 %** | 76,62 % |
| falskt ägande | 15,82 % | **14,86 %** |
| FULL / PARTIAL / OVER / MISSED / WRONG | **173** / **199** / 177 / 152 / 88 | 167 / 211 / **171** / **151** / 88 |

Den tog bort omkring 110 m falskt och kostade omkring 300 m riktigt. Tjugotvå blad ändrades, och de som
tappade mest tappade rejält: −50,5 m ägt på ett blad, −43,1 på ett annat, −42,6 på ett tredje. **Backad.**

Vad mätningen lär: slutstrecket är *inte* det som skiljer fallen åt. På de blad som tappade markerar ritaren
både slutet och de rör linjen korsar - och korsstrecken är då fästet, precis som över en bunt. Skillnaden mot
A0423 ligger någon annanstans, och tills den är hittad är "tvetydigt" fortfarande det riktiga svaret. Fyndet
om vad som *går fel* på A0423 står kvar: en enda svag etikett äger trettiofem meter stam genom
`chain_from_anchor`, och det är den regeln som ska prövas härnäst - inte fästet.

## Var de tappade metrarna faktiskt ligger

Efter tre backade regler slutade jag gissa vad som var fel och mätte i stället var metrarna tog vägen. På de
tio blad som tappar mest, med motorns egna tal ställda mot referensens summa:

| | meter |
|---|---:|
| referensen vill ha | 3 836 |
| läsningen äger | 3 019 |
| läsningen kallar tvetydigt | 187 |
| **ritat i en godtagen rörpenna, men ingen etikett äger det** | **1 085** |

Underskottet är 817 m. Det oägda bläcket i de pennor läsningen redan godtagit som rör är 1 085 m. **De
tappade metrarna är inte borta - de är ritade, i rätt penna, utan ägare.** Och de följer underskottet blad för
blad: 519 mot 367 ägt med 186 oägt; 517 mot 319 med 220 oägt; 516 mot 374 med 123 oägt.

### Varför de står oägda

Kedja för kedja, över de fem värsta bladen: **100 % av det oägda bläcket sitter i kedjor där ingen granne i
någon ände bär ett namn.** Det är alltså inte korsningen som inte kunde avgöra - det finns ingenting att
avgöra. Bläcket ligger som öar, frånkopplat från allt etiketterna nådde.

### Och öarna ligger inte långt bort

Avståndet från varje ö till närmaste namngivna streck **i samma penna**:

| avstånd | meter | andel |
|---|---:|---:|
| 0-2 pt - rör vid rör, grafen är bruten | 67,1 | 24,6 % |
| 2-6 pt - litet glapp | 38,1 | 13,9 % |
| 6-20 pt - en symbol eller del emellan | 20,5 | 7,5 % |
| 20-120 pt | 113,3 | 41,5 % |
| längre än 120 pt - en egen ö | 34,3 | 12,5 % |

**Nästan halva det oägda bläcket ligger inom tjugo punkter från ett namngivet stråk i samma penna**, en
fjärdedel av det så nära som två punkter. På papperet hänger de ihop. I läsningens graf gör de inte det.

### Vad det betyder för vad som ska byggas härnäst

Felet ligger inte i vilket segment en etikett beskriver. Det har tre mätningar nu sagt: vattengången,
slutstrecket och staplingsordningen ändrade alla någon promille åt fel eller inget håll. Felet ligger i att
**grafen inte kopplar ihop det ritningen kopplar ihop** - och därför har namnet ingenstans att ta vägen.

Det är en annan sorts arbete: sammanfogningen (glapp, symboler, pennbyten), inte ägandet. Och det har ett
mått att arbeta mot som inte kräver referensen alls - oägt bläck inom tjugo punkter från ett namngivet stråk
i samma penna är en siffra läsningen kan räkna själv, blad för blad, och som ska gå mot noll.

## Bläckets bredd som beröringstolerans: backad, och mönstret blev synligt

Nodbygget slog bara ihop ändar inom en tiondels punkt. Toleransen togs i stället ur pennans egen bredd -
1,44 punkters penna lägger bläck 0,72 punkter åt vardera hållet, så två ändar närmare än så överlappar i
tryck - med spärren att toleransen aldrig får vara vidare än de stycken den slår ihop (en radie exporteras som
tiondels punkt långa bitar och skulle annars kollapsa till en nod; det provet fångade det direkt).

Grind 71 mot grind 67, 59 blad:

| mått | grind 67 | grind 71 (bläckets bredd) |
|---|---|---|
| täckning | **79,25 %** | 76,57 % |
| falskt ägande | 15,82 % | **14,27 %** |
| FULL / PARTIAL / OVER / MISSED / WRONG | **173** / **199** / 177 / 152 / 88 | 166 / 217 / **167** / **151** / 89 |

Cirka 306 m täckning bort för cirka 177 m mindre falskt. **Backad.**

### Mönstret i fyra mätningar

| grind | ändring | täckning | falskt |
|---|---|---|---|
| 68 | vattengången vid knuten | −0,29 | +0,32 |
| 69 | staplingsordningen | −0,02 | +0,03 |
| 70 | hänvisningslinjens slutstreck | **−2,63** | −0,96 |
| 71 | bläckets bredd som beröring | **−2,68** | −1,55 |

Varje ändring som *begränsar* vad läsningen får äga tar bort mer riktigt än falskt - ungefär två meter riktigt
per meter falskt. Läsningen lutar alltså redan åt att hellre ta än att avstå, och den lutningen är
nettopositiv mot facit som det mäts. Det betyder inte att den är rätt: den betyder att vägen framåt är
**additiv**. Det som ska byggas är regler som ger namn åt det oägda bläcket, inte regler som tar namn ifrån
det ägda.

Och beröringstoleransen var tänkt som additiv men mätte som begränsande, av ett skäl värt att komma ihåg:
grafen används också för att *avgöra vilka pennor som är rör*. En vidare tolerans ändrade den bedömningen och
tappade en penna på ett blad - sjuttiofem meter bläck föll ur läsningen innan ägandet ens började. Nästa
försök ska därför hålla familjeurvalet på den snäva toleransen och vidga den först när pennorna är valda.

## Skrivpennan som togs för rör: godtagen

Användaren pekade på två ställen där läsningen säger *"ritad som rör, men ingen beteckning nådde hit"*. Spåret
gick till pennan, och läsningen hade rätt i andra halvan av meningen och fel i den första.

På W-50-1-A0132 ligger **249,4 m** i en penna som tagits som rörgeometri med **noll röster, noll streck från
någon hänvisningslinje och noll bekräftade meter**. Vad släppte in den? Ett lagernamn som följer samma mall
som rörlagrens - `V-53BB--T--S1--` mot rörens `V-53BB-FE--S2-`. Och vad är den? Varenda ett av dess 4 228
streck börjar eller slutar vid en beteckningsruta. Det är bladets hänvisningslinjer.

Skillnaden står i bladet självt och behöver ingen tröskel:

| penna | streck som går från en etikett | bekräftade meter |
|---|---:|---:|
| `V-56B--FE--VS1-` (1,44) | 46,7 % | 130,0 |
| `V-52BC-FE--V1-` (1,44) | 46,3 % | 109,1 |
| `V-53BB-FE--S2-` (2,04) | 50,5 % | 50,7 |
| `V-52BB-FE--V1-` (1,44) | 57,8 % | 101,6 |
| **`V-53BB--T--S1--` (0,72)** | **100,0 %** | **0,0** |
| **`V-56B--KE--VS1--` (0,72)** | **100,0 %** | **0,0** |

En ledning passerar ofta nära en etikett - men aldrig alla. Där varenda streck gör det skriver pennan.

Grind 72 mot grind 67, 59 blad:

| mått | grind 67 | grind 72 (skrivpennan) |
|---|---|---|
| täckning | 79,25 % | 79,23 % |
| falskt ägande | 15,82 % | **15,76 %** |
| FULL / PARTIAL / OVER / MISSED / WRONG | 173 / 199 / 177 / 152 / 88 | 173 / 199 / **176** / 153 / 88 |

**Godtagen.** En enda rad i hela korpusen bytte klass - en rad som ägde 8,9 m mot en referens på 2,5 och nu
äger noll - och ägda meter ändrades på ett enda blad, med 2,5 av 11 399. Det är den första ändringen på fem
grindar som inte kostar något, och dess värde ligger inte i måttet: den slutar kalla tvåhundrasjuttio meter
hänvisningslinje för rör.


## Rättelse: fem tabeller jämförde mot fel grind

Meterfälten i grindtabellerna ovan är riktiga, men raden `FULL / PARTIAL / OVER / MISSED / WRONG` för grind 67
var i fem av dem hämtad ur den här rapportens **inledande** tabell, som gäller grind **66**. Grind 67:s egna
klasser är **173 / 199 / 177 / 152 / 88**. Tabellerna är rättade.

Vad rättelsen ändrar i besluten: ingenting. Grind 68, 70 och 71 backades på täckning och falskhet, som var
riktiga. Grind 69 står kvar utanför trädet, och mot rätt jämförelse är den om möjligt ännu plattare än jag
skrev. Grind 72 är godtagen som metralneutral, vilket den är - men påståendet "FULL-rader 171 → 173" var fel:
de var 173 före och 173 efter. Ändringens värde ligger i vad den slutar kalla rör, inte i klasserna.

## Referensrader som skriver flera system på en rad

`facit_metrics.py` jämför namn mot namn. En referensrad som skriver `VV01/KV01-X31-16` namnger rör som ritas
tillsammans och mängdas på en rad; läsningen skriver dem som var sin rad med rätt meter på var och en. Namn
mot namn saknades referensraden helt (106,6 m "tappade") och våra två rader stod som namn referensen inte har
(109,9 m "falska") - på ett blad där ingenting var fel.

Verktyget väger nu ihop våra rader till referensens egen rad, men **bara när referensen inte också mängdar
medlemmarna var för sig**. Gör den det - och på just det bladet gör den det - finns två slags rader med samma
namn och namnet ensamt kan inte skilja dem åt. Då vägs ingenting ihop: hellre en rad som inte går att
poängsätta än en poäng som ser bra ut. Över korpusen är ändringen därför en nolla i dag, och den ligger där
för de blad där referensen skriver ihop utan att också skriva isär.

## Fungerar det oavsett stil? Mätt per stil, grind 72

| stil | blad | facit m | täckning | falskt ägande | beteckningar funna | av våra finns i facit |
|---|---:|---:|---:|---:|---:|---:|
| **W** (konturglyfer) | 30 | 5 549 | 78,2 % | **10,6 %** | **94,4 %** | 78,1 % |
| **V** (textlager) | 29 | 5 850 | 80,2 % | **20,6 %** | **80,5 %** | 78,5 % |

Svaret är nej, inte likvärdigt. Bladen med konturglyfer läser sina beteckningar nästan perfekt och äger nästan
inget falskt; bladen med textlager tappar var femte beteckning och har dubbelt så mycket falskt ägande. Det är
inte en gradskillnad utan två olika problem.

Och V-bladens svaghet har en adress. Av allt läsningen kallar beteckning saknar 41,5 % en hänvisningslinje -
men de flesta av dem *ska* sakna den: `EI60` är en brandklass, `TS101` en komponent, `RAD102-10-400X2300` en
radiator, `AV611-10` en ventil. De är märkning, inte rörnamn. Kvar blir de som är rörnamn:

    V-50-1-A0123    SF01-P5 × 11   (facit vill ha SF1-P5-110, 26,5 m)
    V-50-1-B0122    S01-P3 × 8, S01-P5 × 3
    V-50-1-A0422    S01-P5 × 5

Elva etiketter för samma stam på ett blad, ingen av dem når ett rör. Det är nästa lever, och det är den
additiva sorten: fler placerade etiketter ger täckning utan att ta ifrån någon annan rad.
