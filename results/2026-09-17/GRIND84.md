# Grind 84: luftningsbokstaven ur namnet — REVERT, och hela ändringen tas bort

Blint kört, källan frusen före. Det här är tredje formen av samma rättning, och den är sämst av tre.

## Tre former, tre mätningar

| | FALSE_OWNERSHIP | ägda meter | meter under fel namn |
|---|---:|---:|---:|
| **gate82** - bokstaven olästs, namnet som ritat | **10,91** | **8 901,9** | **262,1** |
| gate83 - dimensionen läst, bokstaven kvar i namnet | 10,96 | 8 901,9 | 267,5 |
| gate84 - dimensionen läst, bokstaven ur namnet | 11,08 | 8 888,0 | 281,4 |

Utgångsläget är bäst. Båda mina rättningar gör korpusen sämre, och den andra är sämre än den första.

## Varför - premissen var fel

Grind 83 lärde mig att mängdaren skriver `S1-P5-110`, inte `110L`. Jag drog slutsatsen att bokstaven aldrig
hör till namnet. **Grind 84 visar att referensen skriver det på båda sätten:**

    V-50-1-A0512   referens  S1-P5-110L   8,0 m     <- facit SKRIVER 110L
    V-50-1-A0522   referens  S1-P5-110L   9,8 m     <- facit SKRIVER 110L
    V-50-1-A0311   referens  S1-P5-110   21,1 m     <- facit skriver 110
    V-50-1-A0511   referens  S1-P5-110    3,8 m     <- facit skriver 110

Samma projekt, samma system, samma dimension - och mängdaren har skrivit luftningen på ett sätt på två blad
och på ett annat sätt på två andra. Att normalisera bort bokstaven lagar då två blad och förstör två.
A0511 gick från MISSED till FULL; A0512 och A0522 gick från nästan rätt till MISSED med metrarna under ett
namn referensen inte har.

**Det finns ingen normalisering som är rätt på alla fyra bladen**, för källan är inte konsekvent.

## Beslut

**REVERT av hela ändringen.** `strip_vent`, `dimension_figure` och `vent`-fältet är borttagna. Motorn läser
`110L` som förut: bokstaven blir inte en dimension, och namnet står som ritningen skrev det.

Det är inte ett nederlag utan rätt svar på vad mätningen visade. Den ursprungliga formen behåller namnet som
ritat, och eftersom referensen ibland skriver `110L` är det namnet rätt oftare än något jag kan räkna fram.

## Vad som står kvar olöst, och var det hör hemma

Defekten jag pekade ut är verklig: 19,1 m ligger på rader utan dimension, och en rad utan DN går inte att
prissätta. Men den ska inte lösas i NAMNET, för namnet är det enda som binder raden till mängdförteckningen.
Den hör hemma i identiteten: `110` och `110L` bör vara **en** identitet med luftningen som egenskap, på samma
sätt som isoleringssuffixen redan viks ihop av `canon(fold=True)`. Då spelar det ingen roll vilket av de två
sätten mängdaren råkade skriva på ett visst blad.

Det är en större ändring som rör både motorns identitet och poängsättningens vikning, och den kräver att
referensens egen inkonsekvens hanteras uttryckligen. Den står som ogjord.

## Vad grinden var värd

Tre blinda körningar för att ta bort en rättning. Det är billigt: hade den gått ut hade fyra blads mängder
blivit fel på ett sätt som ingen siffra på skärmen hade visat.
