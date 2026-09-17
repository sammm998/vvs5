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

## Vad utfallet säger om vilka regler som är fel

Det som ser motsägelsefullt ut - att både täckning OCH falskhet steg - är i själva verket ledtråden.
A0214 tappar 9,3 procentenheters täckning och får 9,3 tillbaka som falskhet. Det är inte två fel utan ett:
när en hänvisningslinje som stannar strax intill sitt rör inte längre når fram, blir stråket inte oägt - det
tas av **en annan** etikett. Meterna byter rad i stället för att försvinna.

Det pekar på räckviddsreglerna, och där är hypotesen faktiskt fel i sak:

* **vad ritaren RITADE** - symbolens storlek, märkets storlek, knippets bredd, dubbellinjens avstånd - är
  storheter på papperet och skalas med papperet. Ritar kontoret 41 % mindre är symbolerna 41 % mindre;
* **hur långt läsningen är villig att sträcka sig** - `NEAR_MISS`, `NEAR_ONE`, `COLLECTOR_MAX`,
  `DASH_GAP_MAX`, `CLOSE_ON_OWNED_TOL` - är något annat. De absorberar slarv, och slarv skalar inte med
  papperet. En ritare som drar en hänvisningslinje ett par punkter kort gör det för att handen gled, inte för
  att bladet är litet.

Jag märkte alla nio som pappersberoende utan att skilja de två sorterna åt. Det var en generalisering jag inte
hade underlag för, och grinden hittade den.

## Vad som står kvar

Profilen, faktorn och `Rule.scales_with_paper` står kvar och är oförändrade - de mäter rätt och kopplar in
rätt. Det som ändras är märkningen, och nästa grind prövar den smalare hypotesen: bara det som ritaren ritade
skalar, aldrig hur långt läsningen får gissa.
