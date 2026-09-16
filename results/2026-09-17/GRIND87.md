# Grind 87 — profilen och releaseidentiteten, och det profilen genast fann

**ACCEPT, exakt nolla.** Ritningsprofilen och releaseidentiteten skrivs ned utan att verka, och gör som väntat
ingenting med mängden.

```
gate86.json vs gate87.json: 59 gemensamma blad
  referens    11399.2 ->   11399.2
  ägt          8901.9 ->    8901.9
  falskt       1244.1 ->    1244.1
  TÄCKNING    78.09% ->   78.09%
  FALSKHET    10.91% ->   10.91%
  blad som rörde sig: 0
```

Frysning före körning: manifest `9b1e0b752fe31555`, commit `4df2ee4f3960`, 0 ändrade filer utanför commit.

## Journalen på hela korpusen

```
journalkontroll: 59 blad, 0 FAIL, 0 omtvistade intervall
```

Första gången villkoren körts över allt. `ett_intervall_en_agare` håller på varje blad, och den
transaktionella spärren har inte ett enda fall att verka på. Före det atomära intervallet larmade villkoret på
två blad; det larmet var mitt instruments fel, inte motorns, och nu prövar det rätt enhet.

## Vad profilen fann direkt: korpusen är två ritkontor, inte ett

Varje blad är A1 med blandad text, och pappersfaktorn gick att **mäta** på alla 59. Utfallet är inte en
fördelning utan två punkter:

| grupp | blad | texthöjd | pappersfaktor |
|---|---:|---:|---:|
| V-serien | 29 | 11,0 pt | **1,000** |
| W-serien + A, C, D, E | 30 | 6,5 pt | **0,591** |

Ingenting däremellan. V-kontoret ritar på exakt den texthöjd motorns toleranser är skrivna för; W-kontoret
ritar 41 % mindre på samma pappersformat.

Det betyder att motorns punkttoleranser i dag är **rätt för halva korpusen och drygt 1,7 gånger för generösa
för den andra halvan**, mätt i vad ritaren menade. En hänvisningslinje som får sträcka sig sex punkter för att
nå ett rör sträcker sig på W-bladen lika långt som tio skulle göra på ett V-blad.

Det är inte ett litet sammanträffande att det är just W-bladen som bär nästan hela den öppna felkatalogen -
buntens etiketter, det frigjorda strecket, öarna, stråket som slutar vid en tvetydig knut. Att toleranserna
är för grova där är en hypotes som förklarar en del av det, och den går att pröva: faktorn 1,000 på V-serien
betyder att inga toleranser alls flyttas där, så halva korpusen är sin egen kontrollgrupp.

**Det är nästa grind, och det är därför profilen byggdes som mätning först och verkan sedan.** Att koppla in
faktorn direkt hade gjort den här mätningen omöjlig att lita på: man kan inte mäta ett blad med ett verktyg
som redan ändrat sig efter bladet.

## Övrigt profilen säger om korpusen

* **textläge blandat på alla 59** - varje blad bär både riktig text i filen och text ritad med streck. Att
  filens egen text vinner där båda finns (`_reading_quality`) är alltså inte en kantfall-regel utan gäller
  varje blad;
* **hårfina drag på alla 59** - varje ritning har bläck med bredd noll någonstans. Bläckkontraktet i
  `pipes/ink.py` är därför inte en förberedelse för en framtida stil utan något som används hela tiden;
* **kurvandel 0,9-6,9 %, median 3,1 %** - vilket är underlaget för beslutet att inte skriva om
  bezierapproximationen ännu: en underskattning på 0,12 % av kurvlängden är 0,013 % av allt bläck.
