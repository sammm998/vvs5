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
