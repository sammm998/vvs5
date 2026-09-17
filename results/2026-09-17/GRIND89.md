# Grind 89 — förklaringslistans rättelse: ACCEPT, och en exakt nolla

```
gate87.json vs gate89.json: 59 gemensamma blad
  referens    11399.2 ->   11399.2
  ägt          8901.9 ->    8900.2
  falskt       1244.1 ->    1244.1
  TÄCKNING    78.09% ->   78.08%   (-0,01 pp)
  FALSKHET    10.91% ->   10.91%   (oförändrad)

  blad som rörde sig: 0
```

Frysning före körning: manifest `796cd69352cb3951`, commit `7a88d76e3865`, 0 ändrade filer utanför commit.

**ACCEPT.** Täckningen faller 0,01 procentenheter — 1,7 meter på 8 902 — vilket ligger under det mätta
brusgolvet på 0,02 pp. Falskheten står still. Inget blad rörde sig.

## Varför nollan är rätt utfall

Rättelsen (`opens_head`) säger att en kod ur beteckningslistan bara får äga ett beteckningshuvud när det som
följer inte är en bokstav. Den **släpper igenom mer**: en lista som förut kunde lägga veto mot ett system den
aldrig hört talas om gör det inte längre.

På korpusen kostar det ingenting, och det är i sig ett besked. De 59 bladens beteckningslistor är verkliga
listor med verkliga systemkoder, så `K` mot `KB1` uppstår inte där — koderna i listorna öppnar de huvuden de
ska öppna, och `opens_head` ger samma svar som prefixprovet gjorde. Rättelsen är alltså inert på det material
den prövades mot och verksam på det material som avslöjade felet.

Det är också varför den var svår att hitta. Ett fel som inte syns på 59 blad men raderar hela system på det
sextionde hittas inte genom att köra korpusen igen. Det hittades genom att en riktig ritning lästes fel i
produktion.

## Körningen överlevde en omstart

Behållaren startades om medan jag väntade på grinden. Körningen hade då skrivit färdigt `gate89.json`
(59 av 59 blad, 3,8 MB), så resultatet gick inte förlorat — bara väntandet. Poängsättningen gjordes efteråt
mot den frysta filen, vilket är samma ordning som alltid: blint kört, källan fryst före, facit sist.
