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
