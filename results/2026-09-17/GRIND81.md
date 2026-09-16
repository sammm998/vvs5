# Grind 81: ordningsfri buntutjämning — ACCEPT

Blint kört på 59 blad. Källan frusen **före** körningen: manifest `07c6784c45704a84`, commit `3f66826`,
noll ändrade filer utanför commit. Referensen öppnad först efteråt.

Den här grinden prövar en rättning som inte är gjord för att flytta tal. Buntutjämningen avgjordes av i vilken
ordning en `set` av systemnamn råkade itereras, alltså av processens slumpade strängnycklar. Samma fil, samma
kod, olika process, olika meter. Rättningen räknar i rundor mot en ögonblicksbild och lägger ihop slutsatserna
med mängdoperationer, som inte bryr sig om ordning; där en runda säger emot sig själv avgörs ingenting.

## Talen

|  | gate80 | frö 0 | **gate81** | 81 mot 80 | 81 mot frö 0 |
|---|---:|---:|---:|---:|---:|
| COVERAGE | 78,02 | 78,04 | **78,09** | +0,07 | +0,05 |
| FALSE_OWNERSHIP | 10,95 | 10,93 | **10,91** | −0,04 | −0,02 |
| ägda meter | 8 893,4 | 8 895,9 | **8 901,9** | +8,5 | +6,0 |
| falska meter | 1 248,3 | 1 245,8 | **1 244,1** | −4,2 | −1,7 |
| saknade meter | 2 505,8 | 2 503,3 | **2 497,3** | −8,5 | −6,0 |
| för långt stråk | 986,3 | 983,8 | **982,0** | −4,3 | −1,8 |

`frö 0` är samma motorkod som gate80 under `PYTHONHASHSEED=0` - alltså gate80 utan myntet. Den kolumnen är
rätt jämförelse för rättningen, för mellan den och gate81 ligger ingenting annat än rättningen.

Rör för rör: 3 010 rör mot 3 011, SAME_RUN 1 503 mot 1 508, MISSING_RUN 2 631 mot 2 633, EXTRA_RUN 563 mot 563.
Praktiskt taget oförändrat, vilket är vad man vill se av en rättning som inte rör geometrin.

## Vad som rörde sig, och en förutsägelse som slog fel

Jag skrev innan körningen att grinden borde flytta **ingenting**, eftersom bara ett blad av 59 var
frökänsligt mellan gate80 och frö 0. Det stämde inte. **Tre blad ändrades:**

    W-50-1-A0111       Δägt  +5,0   Δfalskt  −5,0     bättre
    W-50-1-A0222       Δägt  +3,5   Δfalskt  +0,7     bättre
    W-50-1-A0122       Δägt  −2,5   Δfalskt  +2,5     sämre

Skälet till att jag hade fel är värt att skriva ned: rättningen gör inte bara valet upprepbart, den **avstår**
där den gamla koden gissade. Ett blad kan alltså ändras utan att ha varit frökänsligt mellan just de två frön
jag råkade jämföra - det räcker att utjämningen där nådde en slutsats som inte följer av villkoren.
Frökänslighet mellan två godtyckliga frön är en undre gräns för hur många blad myntet rörde, inte en övre.

`W-50-1-A0122` är bladet jag pekade ut i förväg som det som skulle bli sämre, och det blev det. Där låser
rättningen in den gren som ligger längre från referensen. Ingen av grenarna var förtjänad förut; nu följer
den som väljs av ordningsfri slutledning ur bladets egna etiketter, och att referensen säger något annat är
ett fynd om den bunten - inte ett myntkast.

## Beslut

**ACCEPT**, men på rätt grund. Täckningen upp 0,07 och falskt ägande ned 0,04 mot gate80; två av tre ändrade
blad blev bättre och nettot är +6,0 ägda meter mot frö 0. Det är i rätt riktning - men brusgolvet är 0,02
procentenheter, så en förändring på 0,05 är inte ett resultat man ska luta sig mot. **Motiveringen är inte
talen utan upprepbarheten:** samma ritning ger samma mängd i varje process, vilket den inte gjorde förut,
och det är bevisat i fyra frön med bitidentisk utdata (`fa59d3e4f64f`) på ett riktigt blad.

Att talen dessutom inte blev sämre är villkoret för att rättningen får stå kvar, inte skälet till att den gjordes.

## Prov

833 gröna. Kontamineringsskannern PASS. Sju nya prov för ordningsoberoendet, ett av dem över en processgräns
med åtta frön; lägger man tillbaka den gamla utjämningen faller två av dem.
