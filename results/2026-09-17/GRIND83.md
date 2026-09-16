# Grind 83: luftningsbokstaven — REVERT av den form som kördes

Blint kört, källan frusen före: manifest `a3f1a03545a65c24`, commit `19b7c9d`.

## Förutsägelsen, och att den var fel

Jag skrev före körningen att 19,1 m skulle lämna dimensionslösa rader. Det gjorde de inte. **6,1 m flyttade
sig, 13,0 m stod kvar**, och totalen blev **sämre**:

| | gate82 | gate83 | skillnad |
|---|---:|---:|---:|
| COVERAGE | 78,09 | 78,09 | 0,00 |
| FALSE_OWNERSHIP | 10,91 | **10,96** | **+0,05** |
| TEXT_PRECISION | 80,44 | **80,32** | **−0,12** |
| falska meter | 1 244,1 | 1 249,5 | +5,4 |
| meter under fel namn | 262,1 | 267,5 | **+5,4** |

Brusgolvet är 0,02 procentenheter, så +0,05 är verkligt och åt fel håll.

## Varför, exakt

    V-50-1-A0311
       S1-P5-110    referens 21,1 m   vårt 0,0    MISSED
       S1-P5-110L   referens  0,0 m   vårt 10,6 -> 17,3   WRONG

Mängdaren skrev `S1-P5-110`. **`110L` är inget namn i referensen** - luftledningen mängdas under den bara
siffran. Jag läste dimensionen rätt och lät bokstaven stå kvar i NAMNET, så rättningen hällde mer meter i en
beteckning som inte finns, medan den riktiga stod på noll. En halv rättning är värre än ingen alls här: den
gjorde raden större och mer fel samtidigt.

Motorn hade redan skrivit ut regeln jag bröt mot, i `Designation.aside`: *"An aside is not part of a name: two
pipes of the same system and the same dimension are the same pipe to a takeoff whether or not one of them
carries a note."* Luftningens bokstav är precis en sådan not.

## Beslut

**REVERT av den form som kördes.** Grinden har rätt och jag hade fel om orsaken.

Rättningen är inte tillbakatagen utan **fullbordad**: `strip_vent()` lyfter bokstaven ur namnet och behåller
den som en egenskap hos röret, så `S1-P5-110L` mängdas som `S1-P5-110` och bär `vent="L"`. Den formen grindas
som 84. Går den inte hem tas hela ändringen bort.

Att 13,0 m inte flyttade sig på A0512 och A0522 är en andra fråga som står obesvarad: där kommer dimensionen
troligen från raden under och inte från den inbyggda token, och den vägen rörde den här ändringen inte.
