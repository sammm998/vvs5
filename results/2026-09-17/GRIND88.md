# Grind 88 — pappersfaktorn verkar: REVERT, men mekanismen är bevisad

**REVERT.** Falskheten steg, och kriteriet är att den ska falla.

```
gate87.json vs gate88.json: 59 gemensamma blad
  referens    11399.2 ->   11399.2
  ägt          8901.9 ->    8931.7
  falskt       1244.1 ->    1271.6
  TÄCKNING    78.09% ->   78.35%   (+0,26 pp)
  FALSKHET    10.91% ->   11.15%   (+0,24 pp)

  blad som rörde sig: 4
    W-50-1-A0214       täckning   -9.3%  falskhet   +9.3%
    W-50-1-A0133       täckning   +6.3%  falskhet   +0.8%
    W-50-1-A0111       täckning   +4.5%  falskhet   +0.2%
    W-50-1-A0124       täckning   -1.0%  falskhet   +5.8%
```

Brusgolvet är mätt till 0,02 procentenheter. 0,24 är tolv gånger det, alltså en verklig försämring och inte
slump. Två blad blev bättre, två sämre, och summan är åt fel håll.

## Kontrollgruppen höll, och det är det viktigaste i körningen

**Alla fyra blad som rörde sig är W-blad.** Ingen av V-seriens 29 ritningar ändrade en enda meter — precis
som förutsagt, eftersom deras faktor är 1,000 och inga toleranser alls flyttas där.

Det är ett starkare besked än siffrorna. Mekanismen gör exakt det den säger: den rör bara de blad vars profil
säger att de ska röras, och den rör inget annat. Det som är fel är inte hur faktorn kopplas in utan **vilka
regler den kopplas in på**.

## Rättelse: min första förklaring var fel, och mätningen tog den

Jag skrev först att skadan var räckviddsreglerna och att de regler som mäter **vad ritaren ritade** var den
sunda delen — att `NEAR_MISS` och dess likar absorberar slarv medan symbolstorlek och knippbredd är storheter
på papperet. Det lät rimligt och byggde på täckningssiffrorna.

Det höll inte. Jag läste fel nyckel ur mätningen (`falseness` i stället för `false_ownership`), fick noll
falskhet i varje ruta och drog slutsatsen ur täckningen ensam. Med rätt nyckel kördes de fyra blad som rörde
sig under varje delmängd:

| delmängd | täckning | falskt ägande |
|---|---:|---:|
| ingen (baslinjen) | 65,57 % | **12,97 %** |
| vad som ritats | 67,21 % | 14,11 % |
| räckvidd | 66,53 % | 14,14 % |
| båda | 68,16 % | 15,29 % |

**Båda delmängderna höjer falskheten, och med nästan exakt lika mycket** — 1,14 respektive 1,17
procentenheter, och de är additiva. Det finns ingen delmängd som förbättrar kriteriet. Min uppdelning i
"vad som ritats" och "räckvidd" var en berättelse jag byggde av halva mätningen.

Per blad separerar det ändå rent, och det är värt att ha skrivet:

| blad | ingen | vad som ritats | räckvidd |
|---|---|---|---|
| A0214 | 90,4 / 1,1 | 90,4 / 1,1 | **81,1 / 10,4** |
| A0133 | 74,2 / 5,4 | **80,4 / 6,2** | 74,2 / 5,4 |
| A0111 | 57,0 / 14,0 | **57,4 / 13,4** | 60,9 / 14,8 |
| A0124 | 62,9 / 25,1 | **61,9 / 30,8** | 62,9 / 25,1 |

Varje blad rörs av exakt en delmängd, aldrig av båda — så mekanismen är precis och går att resonera om. Men
bara en enda ruta i hela tabellen är strikt bättre än baslinjen (A0111 under "vad som ritats": +0,4 täckning,
−0,6 falskhet). En regel som hjälper ett blad av fyra är inte en regel.

## Vad som står kvar, och varför fältet finns kvar tomt

Ingen regel är märkt som pappersberoende. Det är ett **mätt** beslut och står som ett prov, så att en framtida
märkning inte kan ske i förbifarten.

Profilen, faktorn och `Rule.scales_with_paper` står kvar. Faktorn är inte felmätt — den är mätt på 59 blad och
skiljer två ritkontor åt utan ett enda undantag, och grind 88 visade att inkopplingen rör exakt de blad vars
faktor inte är 1 och inga andra. Det mätningen säger är något annat: **en tolerans i punkter är inte den
storhet pappersfaktorn hör hemma i.** Var den hör hemma vet jag inte, och det är bättre att skriva det än att
märka fler regler tills någon kombination råkar se bra ut på fyra blad.

Återgången är verifierad utan en egen korpuskörning: de fyra bladen under "ingen delmängd" ger exakt grind 87:s
siffror, blad för blad, på båda måtten.
