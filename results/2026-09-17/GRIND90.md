# Grind 90 — bläckandelsprovet ovillkorligt: ACCEPT, och en nolla som förklarar sig

```
gate89.json vs gate90.json: 59 gemensamma blad
  referens    11399.2 ->   11399.2
  ägt          8900.2 ->    8900.2
  falskt       1244.1 ->    1244.1
  TÄCKNING    78.08% ->   78.08%
  FALSKHET    10.91% ->   10.91%

  blad som rörde sig: 0
```

Frysning före körning: manifest `947cf3bd551259f0`, commit `7e66dfee253a`, 0 ändrade filer utanför commit.

**ACCEPT.** Jag skrev i commit:en att risken var verklig — ändringen släpper in fler pennor som rörkandidater
på varje blad, och halva korpusen var inte kontrollgrupp den här gången. Den risken visade sig inte finnas.

## Varför ingenting rörde sig

Provet säger: en penna vars hänvisningslinjer är mindre än hälften av vad den ritar är inte bladets ledarpenna.
Förut gällde det bara i räddningsläsningen; nu alltid.

Att det inte rör ett enda blad betyder att på alla 59 sammanfaller de två frågorna. En penna som bär minst en
fjärdedel av bladets ledare är där **också** en penna vars ledare är merparten av vad den ritar — alltså en
riktig ledarpenna, och provet friar den inte. Spärren slår bara till där en penna drar ledare *och mycket
annat*, och det är den lagerlösa exporten, som korpusen inte innehåller.

Det är samma mönster som grind 89: en ändring som är inert på det material den prövas mot och verksam på det
material som avslöjade behovet. Skillnaden mot en verkningslös ändring är att man kan säga **var** den verkar,
och visa det.

## Vad den gjorde med bladet som avslöjade felet

Löpöglan 2 har inget facit, så det här är en redovisning och inte en grind:

```
mängd            121,14 m  ->  124,45 m
rörfamiljer             2  ->  5           (0,72-pennan insläppt, men också arkitektens 0,51)
ritat bläck         652 m  ->  4 158 m     varav 4 043 utan ägare
S1 får rader          nej  ->  ja          men en meter styck
```

**Pennan släpps in, och det var rätt fråga att ställa — men det som saknades låg inte bara där.**
1 260 m rörbläck var uteslutet; nu är det med i det som övervägs, och ändå blir det inte till mängd. Felet
efter det här sitter längre ned: ledarna når fram, identiteten fästs, men stråken bryts direkt. Det är nästa
sak att gräva i, och den har inget med pennvalet att göra.

Att ändringen samtidigt släppte in arkitektens egen 0,51-penna som rörkandidat är trubbigt och syns i att det
"ritade" bläcket sexdubblades. Det kostade ingenting på korpusen, men det är en lös ände: en penna blir
kandidat på att en ledare råkat peka på den, och den tröskeln är svagare än den borde vara.
