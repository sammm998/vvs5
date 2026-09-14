# gate59: par i pennan, buntpartner på alla pennor, lagerklass - ACCEPT

**Ändring.** `pipes/ownership.py` (paret: en oägd ledning parallellt med en ägd på pennans eget paravstånd),
`semantics/attachment.py` (buntpartner söks på alla pennor hänvisningslinjen rörde; lagerklassen 52BB/52BC/52BD
namnger systemet före svansen). Commit 3ff12f2, ögonblicksbild i `hashmanifest-gate59.json`. Bakgrund och
diagnos i `FYND.md` §1-3.

**Körning.** Blind, 59 blad. Körningen avbröts efter 42 blad (behållaren startade om) och fortsattes på samma
frysta ögonblicksbild för de 17 som saknades (`gate_resume`); motorn är deterministisk och inget blad kördes
två gånger. Facit lästes först efter körningen. Jämförelsegrund: gate58 omräknad med den nya måttstocken
(monteringssuffix fallna, se `results/2026-09-12-lagerlost/GATE.md`).

| | gate58 (ny måttstock) | gate59 |
|---|---:|---:|
| referens | 11399,2 m | 11399,2 m |
| ägt | 7390,1 m | 8045,1 m |
| falskt | 1852,1 m | 2172,4 m |
| TÄCKNING | 64,83 % | **70,58 %** |
| FALSKHET | 16,25 % | 19,06 % |
| blad som rörde sig | | 28 |

Störst: W-50-1-A0134 +31,2 % täckning, A0132 +28,9 %, V-50-1-A0221 +27,0 %, W-50-1-A0124 +21,0 %,
A0131 +20,0 %, A0122 +18,9 %, A0214 +15,1 %. Tolv W-blad vann 7-31 % vardera.

**Blad som rörde sig åt fel håll, ett i taget.**

- **A och W-50-1-A0011 (samma ritning): −8,0 % täckning.** KV1-X31-16, 17,1 → 0 m. Etikettens hänvisningslinje
  slutar där en linje från `V-52BB-FE--V1-` och en från `V-52BB-FE--V2-` möts; båda lagren är tappkallvatten
  (52BB), klassen rankar dem lika, och det som förut avgjordes av svansen (V1) blev
  `several_vector_families_at_leader_no_token_discrimination`. Rotorsak i regeln, inte i bladet: klassen
  namnger systemets familj, svansen dess nummer. Rättat: klassmatch med rätt svans (`MATCH_CLASS_AND_TAIL`) går
  före klassmatch ensam. Prov: `test_two_layers_of_one_class_are_told_apart_by_their_tails.py`. Går i gate60.
- **V-50-1-A0222 +17,3 m falskt, V-50-1-A0221 +11,7 m falskt (och +15 m täckning), V-50-1-A0122 +17,6 m.**
  Alla tre VS21-S13-15, paret i VS2x-pennan. Kontroll mot mängdarens egna markeringar i bladet (de gula
  linjerna, mätningens färg i facit): på A0222 ligger **alla 12,4 m parade meter på gult** - mängdaren mätte
  dem. Det som ligger utanför gult är 27,8 m `chain_with_agreeing_anchors`, ägda redan i gate58 (83,6 m mot
  69,6 i facit), överst på bladet i ett par utan omgivning. Måttstocken räknar ägt över referensen som falskt,
  så de rätt parade metrarna hamnar i falskt-kolumnen för att bladet redan låg över. Paret är rätt; det som är
  fel på bladet är äldre och ett annat fel (ägt utanför mätningen, 24 m, nästa rotorsak på V-bladen).
- **W-50-1-A0122 +14,8 % falskt (VV1-X7-40 35 → 70 m), W-50-1-A0114 +10,1 % (VV1-X7-40 24 → 53 m).** Klassen
  gav VV1 sitt lager, men på det lagret ligger två linjer (VV1 och VVC1) och VV1 tog båda. Det är fallet i
  `test_two_rows_on_one_layer_share_its_lines_by_elimination.py` (commit feee378, efter ögonblicksbilden):
  två rader på ett lager med två linjer är en bunt inom lagret. Går i gate60. På A0134 lästes dessutom
  tredje raden VVC1 som VVE1 (sju av åtta) - C med rak rygg lästes som E; rättat i `text/recognize.py`
  (täckningsvillkoret, commit ce13db8), prov `test_a_letter_with_a_stroke_missing_is_another_letter.py`.

**Beslut: ACCEPT.** +5,75 % täckning; falskheten +2,8 % är till hälften måttstockens sätt att räkna rätt
parade meter på blad som redan låg över, till hälften VV1-dubbleringen som gate60 prövar.

**gate60** = gate59 + bunt inom lagret (feee378) + korsningsbryggan (f1d85d6) + täckningsvillkoret i
teckentydningen (ce13db8) + klass-och-svans. Rör sig ett blad åt fel håll delas grinden per regel.

# gate60: bunt inom lagret, korsningsbryggan, täckningsvillkoret, klass-och-svans - ACCEPT

**Ändring.** Fyra regler, alla ur W-bladen (`FYND.md` §2-4 och `results/2026-09-13-parade`):
`pipeline.py`/`semantics/attachment.py` - två rader på ett lager med två linjer är en bunt inom lagret som
avgörs genom uteslutning (feee378); `pipes/representation.py` - två fria ändar över ett streck av samma penna
tvärs glappet hör ihop (f1d85d6); `text/recognize.py` - den andel bläck som saknar motsvarighet i den andra
formen betalas för, så ett smalt C inte läses som E (ce13db8); `semantics/attachment.py` - klassmatch med rätt
svans går före klassmatch ensam (2e856c9). Ögonblicksbild: `hashmanifest-gate60.json`.

**Körning.** Blind, 59 blad. Avbröts av en omstart efter 44 blad och fortsattes på samma frysta ögonblicksbild
för de 15 som saknades; motorn är deterministisk och inget blad kördes två gånger. Facit lästes efteråt.

| | gate59 | gate60 |
|---|---:|---:|
| referens | 11399,2 m | 11399,2 m |
| ägt | 8045,1 m | 8166,5 m |
| falskt | 2172,4 m | 1997,3 m |
| TÄCKNING | 70,58 % | **71,64 %** |
| FALSKHET | 19,06 % | **17,52 %** |
| blad som rörde sig | | 14 |

**Vad som rörde sig.** Varje rört blad är VV1/VVC1 - buntregeln. Mönstret är detsamma överallt: VVC1 går från
MISSED till PARTIAL (tredje raden får äntligen en linje) och VV1 från OVER till PARTIAL (den tar inte längre
båda). A0122 +10,6 % täckning och −10,5 % falskhet, A0114 +8,8/−8,8, A0123 +8,0/−4,3.

Två blad ned: **A0124** −11,9 % täckning men −9,8 % falskhet (VV1-X7-40 48,6 → 1,5 m mot 31,9 i facit;
VVC1-X7-25 0 → 1,0 av 12,1) och **A0133** −4,1/−1,2 (VV1-X7-16 18,3 → 0 mot 16,5; VVC1-X7-16 0 → 8,5 av 16,7).
På båda slutar bunten oavgjord i stället för att en rad tar båda linjerna: bladet namnger ingen av dem för sig
och elimineringen har inget att gå på. Det är rätt svar på fel läge - hellre en fråga än fel visshet - och
nästa regel är hur bunten avgörs, inte att den tas bort.

A och W-50-1-A0011 (+8,0 %) är klass-och-svans: KV1-X31-16 tillbaka med 17,1 m, som väntat.

**Beslut: ACCEPT.** +1,06 % täckning och −1,54 % falskhet; de två bladen som gick ned bytte falska meter mot
öppna frågor.

**gate61** = självslingan i noden (en linjes två ändar är två ställen), korsningen som delas i två linjer,
punktens anspråk framåt och parspärren vid en knut. A0134 lokalt: 218,0 → 258,7 m av 350.

# gate61: självslingan i noden, korsningen som två linjer, punktens anspråk, parspärren - ACCEPT

**Ändring.** `pipes/representation.py`: en linjes två ändar är två ställen hur kort linjen än är (nodbygget
höll inte isär dem, och de tiondels punkter en rundad böj exporteras som blev självslingor som gjorde böjen
till en fyrarmad knut - 2 417 på W-50-1-A0134); en nod där varje arm har sin raka fortsättning på andra sidan
delas i en nod per linje; en punkt som ett streck tagit ärver riktningen och ser vidare; ett ensidigt anspråk
konkurrerar med anspråken på samma stycke, inte på samma nod. `pipes/ownership.py`: en oägd ledning som delar
nod med en namngiven av annan identitet är knutens sak, inte parets. Commits f1d85d6, e7118ee, ae66170.

| | gate60 | gate61 |
|---|---:|---:|
| ägt | 8166,5 m | 8550,8 m |
| falskt | 1997,3 m | 2218,8 m |
| TÄCKNING | 71,64 % | **75,01 %** |
| FALSKHET | 17,52 % | 19,46 % |
| blad som rörde sig | | 42 |

Störst uppåt: W-50-1-A0211 +50,8 % täckning och −8,0 % falskhet, V-50-1-A0323 +16,8, W-50-1-A0222 +15,1,
V-50-1-B0114 +15,0, A0134 +13,4. Fem blad ned, alla under 6 %.

**Vad falskheten kostar, och varför den inte backas.** Med kedjorna hela genom böjar rinner identiteten längre,
och där två etiketter med olika DN sitter på samma kedja tar den ena allt: A0132 VS1-S13-15 13 → 49 m mot 15 i
facit medan VS1-S13-22 föll 20 → 0,3 mot 62. Samma på V-50-1-B0112 och A0422. Det är inte geometrin som är fel -
en linjes två ändar *är* två ställen - utan gränsen mellan två frön på en kedja som förut var två kedjor. Att
backa en riktig geometri för att dölja en gränsregel vore att byta ett synligt fel mot ett gömt.

**Beslut: ACCEPT.** +3,37 % täckning; DN-gränsen på en hel kedja är nästa regel (uppgift #67).

**gate62** = raden som föll ur förklaringslistan (fyra blad från noll till facit) och buntens radordning ur
bladets egna avgjorda buntar.

# gate62: raden ur förklaringslistan, buntens radordning - ACCEPT

**Ändring.** `semantics/legend.py`: indexet över kod/beskrivning-par nådde färre band än villkoret det tjänar
(räckvidden är nu `0,6·h/2 + 2` band), så avloppsbladens förklaringslista lästes tom och fyra blad fick noll
meter. `pipeline.py`: en bunt med flera rader avgörs, när varken eliminering eller bladets samstämmighet räcker,
av den radordning bladets egna redan avgjorda buntar visar (minst två vittnen, skäl
`multi_row_bundle_settled_by_the_sheets_own_row_order`). Commit 8143e59 och 410bbe3.

| | gate61 | gate62 |
|---|---:|---:|
| ägt | 8550,8 m | 8756,7 m |
| falskt | 2218,8 m | 2243,3 m |
| TÄCKNING | 75,01 % | **76,82 %** |
| FALSKHET | 19,46 % | 19,68 % |
| beteckningsåterkallelse | 83,94 % | 86,46 % |
| blad som rörde sig | | 10 |

De fyra avloppsbladen: W-50-1-A0022 0 → 68,1 m (facit 72,8), A0023 0 → 36,4 (36,4), A0031 0 → 4,1 (7,0),
A0034 0 → 41,1 (44,6). Radordningen: A/W-50-1-A0011 189,0 → 202,6 (213,7), W-50-1-A0133 179,9 → 199,5
(305,1), D +1,8 %. Ingen minskning på något blad; falskheten +0,22 procentenheter, allt på de fyra bladen som
förut inte ägde något alls (4–7 m var).

**Beslut: ACCEPT.** +1,81 % täckning, +2,5 % beteckningsåterkallelse.

**gate63** = parentesen som lästes som I (`160(L)` → `160ILI`, `KV/VV(1-2)-X31` → ingenting), bladets
kompakta kopplingsledningstabell, och den bäst namngivna pennan tar den förklarade ledningen.

# gate63: parentesen, den korta tabellen, tillägget som inte döper - ACCEPT

**Ändring.** `text/vector_text.py`: den strukturella parentesregeln tar även en grund båge när strecket är tunt
och kröningen sitter mitt på kordan, och sidan avgörs av bågens riktning på sidan i stället för av ritordningen.
`semantics/declarations.py`: regelraden känns igen genom läsningens egna tvillingfel (0/O, I/1, oläst tecken),
fyra stammar skrivna som ett ord (`KV/VV(1-2)-X31`) blir fyra, klasserna på raden under blir kolumner, och
måttet `16(15)` är 16. `pipes/ownership.py`: när regeln förklarar flera system tar den penna vars lager namnger
systemet bäst ledningen; lika bra namn ger fortfarande ingenting. `semantics/annotation.py`: ett tillägg i
parentes på måttraden är en anteckning, inte en del av namnet. Commit 42494e5.

| | gate62 | gate63 |
|---|---:|---:|
| ägt | 8 756,7 m | 9 097,7 m |
| falskt | 2 243,3 m | 2 263,8 m |
| TÄCKNING | 76,82 % | **79,81 %** |
| FALSKHET | 19,68 % | 19,86 % |
| beteckningsåterkallelse | 86,46 % | 87,87 % |
| beteckningsprecision | 77,54 % | 78,48 % |
| blad som rörde sig | | 14 |

Störst: W-50-1-A0213 +31,8 % täckning och −3,9 % falskhet (94 → 161 m av 212), A0124 +27,1 (81 → 148 av 247),
A0222 +19,7 (127 → 169), A0133 +14,0 (200 → 242), A0114 +11,8 (223 → 261). Blad A 202,6 → **208,8 av 213,7**
(97,7 % täckning, 1,2 % falskt). Två blad ned: A0122 −0,4 % täckning och +2,1 % falskhet, A0134 +2,9 % falskhet
- båda från förklarade kopplingsledningar som tar någon meter för mycket.

**Beslut: ACCEPT.** +2,99 % täckning för +0,18 % falskhet.

**gate64** = måttraden som bär en klass med en siffra i.

# gate64: måttraden med en klass - ACCEPT (oförändrade meter, en felaktig rubrik färre)

**Ändring.** `semantics/annotation.py`: en måttrad får bära ett tillägg som själv har en siffra, när tillägget
börjar med en bokstav - "22-F60" är dimension 22 med isolerklass F60. Ett kryss följt av siffror är ett andra
mått och ingen klass, så "600X300" är fortfarande ingen måttrad. Commit efter gate63.

| | gate63 | gate64 |
|---|---:|---:|
| ägt | 9 097,7 m | 9 097,9 m |
| falskt | 2 263,8 m | 2 263,7 m |
| TÄCKNING | 79,81 % | 79,81 % |
| FALSKHET | 19,86 % | 19,86 % |
| beteckningsprecision | 78,48 % | **78,59 %** |
| felaktiga namn (WRONG) | 95 | **94** |
| blad som rörde sig | | 0 |

**Beslut: ACCEPT.** Inga meter rör sig, och det är väntat: på V-50-1-A0423, där felet upptäcktes, läses
beteckningen `VS21-S13-22-F60` nu rätt men blocket får fortfarande ingen hänvisningslinje (FYND §11), så
metrarna sitter kvar hos grenarna. Det som ändras är att en rubrik som inte fanns i facit försvinner och
precisionen stiger. En läsning som namnger röret rätt är bättre än en som inte gör det, även när meterna ännu
hindras av ett annat fel - och utan regressioner är det ingen anledning att backa.

**gate65** = baslinjebiten som svänger ned i hänvisningslinjen: fyra beteckningar på en rad, en linje under dem
ritad i bitar på var sitt systemlager, och noll hänvisningslinjer för hela blocket (FYND §11).

# gate65: baslinjen som svänger ned - ACCEPT som sista utväg

**Ändring.** `semantics/leaders.py`: en bit av radens baslinje vars ände fortsätter i exakt en linje som lämnar
radens riktning ger en start vid hörnet, och bitens eget spann längs raden följer med. `pipeline.py`: det
spannet avgör vilken av radens beteckningar hänvisningen talar för - motsvarigheten till regeln för staplade
rader med var sin understrykning.

**Först för brett, sedan snävat.** Med böjen som ett anspråk bland andra blev det täckning +0,10 % och falskhet
+0,37 %: femton blad rörde sig, de flesta åt fel håll, därför att etiketter som redan hade en hänvisningslinje
fick en andra. Med böjen sist i ordningen och överhoppad för ett block som redan fått en linje:

| | gate64 | gate65 (brett) | gate65 (sista utväg) |
|---|---:|---:|---:|
| TÄCKNING | 79,81 % | 79,91 % | **79,82 %** |
| FALSKHET | 19,86 % | 20,23 % | **19,93 %** |
| beteckningsåterkallelse | 87,87 % | 87,87 % | **88,03 %** |
| beteckningsprecision | 78,48 % | 78,48 % | **78,62 %** |
| blad som rörde sig | | 15 | 4 |

**Var falskheten hamnar.** Av de 8,8 m som tillkommer ligger **8,8 m på `VS21-S13-15`** - en beteckning som på
vart och ett av de bladen redan låg över facit (A0121 37,3 mot 15,4; A0112 64,0 mot 41,0; A0311 110,0 mot 108,4).
Regeln ger alltså en riktig hänvisningslinje, och metrarna rinner sedan iväg längs en kedja där en känd brist -
DN-gränsen på en hel kedja, uppgift #67 - låter en identitet ta hela stråket. Det som är nytt och rätt syns på
andra sidan: en beteckning gick från MISSED till PARTIAL, återkallelsen steg 0,16 % och precisionen 0,14 %.

**Beslut: ACCEPT.** En läsning som låter fyra etiketter namnge sitt rör är bättre än en som låter dem tiga, och
den falskhet som följer är #67:s att bära, inte hänvisningslinjens.

**gate66** = förklaringslistan som intygar sig själv (#76), funnen i korpussvepet utanför de 59 bladen.

# gate66: en lista får inte vouchera för sig själv - ACCEPT

**Fyndet.** `R9UHA10-CLB001-004.pdf` läste 113 beteckningar, hittade 76 hänvisningslinjer, och gav **0 meter**.
Alla 38 pennfamiljer stod som `not_examined`. Ritningen är från ett annat kontor än de 59 grindbladen, och
felet fanns bara därför att svepet läser mer än grinden gör.

**Rotorsak.** Bladets egen förklaringslista avgör vilka koder som är rörbeteckningar. Regeln är med flit smal:
den gäller bara när listan bevisligen känner igen bladets ordförråd, mätt som antalet kända systemkoder. Men
listans rader läses som beteckningar de också, och en rad i listan stämmer med listan av bara farten. Det här
bladets lista handlar om ventiler och material (`SA01`, `SPO1`, `P1`, `R61`, `S13` …). Dess tolv egna rader gav
tolv "kända" koder, villkoret var uppfyllt - och sedan refuserades varenda rörbeteckning bladet faktiskt ritar:
`KV01`, `VV01`, `VVC01`, `VS21`, `SP01`, `AV201`. Utan rörnamn kom inga röster fram till pennfamiljerna, och
utan familjer fanns ingen geometri att mäta. Listan hade voucherat för sig själv.

**Ändringen.** `semantics/legend.py`: `DrawingLegend.holds(bbox)` säger om en etikett står inne i listans egen
ruta. Maskineriet fanns redan, i två kopior inuti `assign_roles`; de använder nu samma regel.
`pipeline.py`: frågan "känner listan det här bladet?" ställs bara till etiketter **utanför** listans ruta.
Ligger alla kända koder i listan säger listan ingenting om bladet, och då stänger den inte ute någonting.

| | före | efter |
|---|---:|---:|
| R9UHA10-CLB001-004: rader | 0 | **10** |
| R9UHA10-CLB001-004: bekräftade meter | 0,0 | **180,2** |
| R9UHA10-CLB001-004: täckning | 0,0 % | 23,8 % |

**Grinden.** `gate66` mot `gate65`: **0 blad rörde sig**. TÄCKNING 79,82 %, FALSKHET 19,93 %, återkallelse
88,03 %, precision 78,62 % - identiska siffror. Inget av de 59 referensbladen har en lista som bara handlar om
komponenter, så regeln var overksam där. Vinsten ligger utanför den mätta mängden och kostar ingenting på den.

**Beslut: ACCEPT.** Regressionerna står i `test_a_list_does_not_vouch_for_itself.py`: listans egna rader gör den
inte kunnig, en lista som känner etiketterna ute på planen stänger fortfarande ute det den aldrig nämner, en
beteckning utan ruta vägs som förut, och en lånad lista har ingen ruta att diskvalificera med.

**gate67** = DN-gränsen på en hel kedja (#67), som nu är den enskilt största posten i felkatalogen.

# gate67: flödesbudget graderad efter dimensionsstegen - REVERT

**Idén.** FYND §13 mätte riktningen i felet: den minsta dimensionen i en stam propagerar för långt tre gånger så
ofta som den största (37,9 % mot 12,4 %), och den största är den som saknar mest (−813 m). Alltså borde en liten
dimension inte få rinna lika långt genom en knut som en grov. Budgeten graderades efter bladets egen
dimensionsstege: grövsta storleken behöll hela `FLOW_LIMIT`, finaste fick en bråkdel.

**Mätningen.**

| | gate66 | gate67 |
|---|---:|---:|
| TÄCKNING | 79,82 % | **79,44 %** |
| FALSKHET | 19,93 % | **19,47 %** |
| beteckningsåterkallelse | 88,03 % | 87,87 % |
| beteckningsprecision | 78,62 % | 78,48 % |
| blad som rörde sig | | 20 |

**Beslut: REVERT.** Bytet är 0,38 täckning mot 0,46 falskhet - och det räcker inte, för **både återkallelse och
precision faller**. En ändring som ökar precisionen betalar för sig; den här tar bort meter i ungefär samma
blandning som de redan låg i. Det syns tydligast på `W-50-1-A0211`: −18,8 % täckning utan att en enda falsk
meter försvinner. Där skär regeln rakt igenom något riktigt.

Vad mätningen faktiskt lär: riktningen i §13 är verklig, men **flödesbudgeten är fel ställe att lägga den på**.
Budgeten väger en identitets hela sammanhängande stråk mot dess egna etiketter, och den vet ingenting om var
gränsen mot grannen går. En regel som ska säga "den grövre äger stammen" måste stå i knuten, där de två
dimensionerna faktiskt möts - vilket är vad gate68 provar.

**gate68** = ett stråk som byter dimension: den grövre bär böjen (från produktionsbladet W-50-1-A0032).
