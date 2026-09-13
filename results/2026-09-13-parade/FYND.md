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
