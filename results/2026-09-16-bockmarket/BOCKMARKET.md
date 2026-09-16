# Hänvisningslinjen som lästes som ett bockmärke

**W-50-1-A-0033**, bladet i skärmbilden. Summan stämde på decimalen - 35,12 m mot facits 35,1 - och ändå var
måttet fel, för metrarna låg på fel dimension:

| beteckning | facit | läsningen (grind 72) | avvikelse |
|---|---:|---:|---:|
| S1-P2-110 | 11,1 | 16,5 | **+49 %** |
| S1-P2-160 | 4,1 | 3,3 | −19 % |
| S1-P2-75 | 19,9 | 15,3 | **−23 %** |
| summa | 35,1 | 35,1 | 0 % |

Fem meter hade flyttat från den klenare dimensionen till den grövre. En summa som stämmer medan raderna inte
gör det är värre än en summa som är fel: den ser riktig ut.

## Vad som hände

Etiketten `S1-P2-75 / VG+1.71` vid (920, 1039) har en ram runt sina två rader och drar sin hänvisningslinje
från ramens övre högra hörn: ett enda snedstreck på 14,4 punkter ned till det lodräta röret vid x = 972, med
ett litet kryss där det landar.

Textläsningen plockar bort *bockmärken* ur geometrin innan hänvisningslinjerna letas fram - pilstrecket vid en
linjes ände och krysset över den är märken, inte ritade ledningar. Frågan "är den här klumpen ett märke?"
ställdes på **tre** ställen i `text/vector_text.py` och besvarades olika:

* två av dem krävde att klumpen var högst 12 punkter stor,
* det tredje - det som körs först - krävde ingenting alls om storleken.

Snedstrecket på 14,4 punkter gick igenom det tredje, blev ett märke och försvann ur geometrin. Kvar åt
etiketten fanns bara dess egen ram, vars underkant togs för hänvisningslinje; den slutar i tomma luften och
fästet blev `NO_PIPE_ATTACHMENT · leader_endpoint_touches_no_pipe_geometry`.

Därmed hade det lodräta röret ingen egen etikett. Grannstråkets kedja - `S1-P2-110`, med fem etiketter mot det
här rörets noll - fortsatte då rakt genom knuten och tog det: `collinear_through_junction`,
`through_junction_up_to_tick_boundary`. Två av bladets 32 hänvisningar föll så.

Bladets egen statistik säger samma sak: 29 av 32 hänvisningslinjer har formen
`straight|diagonal|underline_end|end-tick|w0.48` - exakt det snedstreck som här blev ett märke. Två hade
formen `row_underline`, och det är de två som fallerade.

## Ändringen

Samma gräns på alla tre ställena. `MARK_MAX_PT = 12.0` får ett namn, står i regelregistret som
*"Hur stort ett bockmärke får vara"*, och används av alla tre frågorna. Ingen ny tröskel, ingen justerad
siffra: en inkonsekvens i koden borttagen.

    engine/vvs_engine/text/vector_text.py   MARK_MAX_PT, _is_mark och de två andra ställena
    engine/vvs_engine/rules.py              text.vector_text.MARK_MAX_PT
    engine/tests/test_a_leader_is_not_a_tick.py   5 prov

## Bladet efteråt

| beteckning | facit | före | efter |
|---|---:|---:|---:|
| S1-P2-110 | 11,1 | 16,5 | **12,6** |
| S1-P2-160 | 4,1 | 3,3 | 3,3 |
| S1-P2-75 | 19,9 | 15,3 | **19,4** |

Hänvisningar utan rör: 3 → 1. Täckning +11,6 %, falskhet −11,1 %.

## Grind 74 mot grind 72 - hela korpusen, 59 blad

|  | grind 72 | grind 74 |
|---|---:|---:|
| TÄCKNING | 79,23 % | 79,19 % |
| FALSKHET | 15,76 % | **15,70 %** |
| BETECKNING RECALL | 87,56 % | **87,72 %** |
| BETECKNING PRECISION | 78,31 % | **78,45 %** |
| FULL | 173 | **177** |
| PARTIAL | 199 | **197** |
| OVER | 176 | **174** |
| MISSED | 153 | 154 |
| WRONG | 88 | **86** |

Ägda metrar 9 031,8 → 9 027,1 (−4,7). Falska 1 797,1 → 1 789,8 (−7,3). Ändringen lämnar alltså ifrån sig mer
falskt än sant, vilket ingen av de fyra föregående grindarna gjorde, och fyra rader till landar rätt.

Åtta blad rörde sig:

| blad | täckning | falskhet |
|---|---:|---:|
| W-50-1-A0033 | **+11,6 %** | **−11,1 %** |
| W-50-1-A0032 | −7,6 % | +7,7 % |
| W-50-1-A0133 | −5,3 % | −1,8 % |
| W-50-1-A0134 | +1,9 % | −1,9 % |
| V-50-1-A0111 | +1,4 % | −1,4 % |
| V-50-1-A0411 | +1,1 % | ±0 % |
| V-50-1-A0211 | +0,4 % | +1,0 % |
| W-50-1-A0121 | ±0 % | +2,8 % |

**Kostnaden står på två blad.** På A0133 gick 10 fästen från säkra till tvetydiga (96 → 86 säkra, 18 → 28
tvetydiga): ett streck som förr togs bort som märke är nu en linje till, och där två linjer konkurrerar om
samma etikett håller läsningen inne med svaret. Det är rätt beteende - tvetydigt är ett giltigt svar - men det
kostade ~15 m sanna metrar på det bladet, mest `VVC1-X7-16` (18,5 → 6,7) och `VV1-X7-16` (8,0 → 0,0). På A0032
tog i stället DN110 mer av det som är DN160. Båda är bokförda som egen uppgift.

Prov: 773 gröna (768 + 5 nya). Determinism på A0033: fyra körningar, samma hash. Kontamination: PASS.

**ACCEPT.**
