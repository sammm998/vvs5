# gate57: en kort rad tar riktning av närmaste säkra rad - ACCEPT (neutral)

**Ändring.** `text/strokes.py`: en rad med två eller tre tecken har för lite i sig för en egen vinkel och tar
den närmaste säkra radens riktning (minst fyra höga tecken, inom tolv H, i en riktning bladet skriver i) när den
ligger inom tjugo grader av sin egen. Bakgrund i `results/2026-09-11-priorn/FYND.md`: `VS` i 10° blev `?S`.

**Körning.** Blind, 59 blad, ögonblicksbild av motorn i `hashmanifest-gate57.json` (commit 130995a + strokes.py).
Facit lästes först efter körningen.

| | gate56 | gate57 |
|---|---:|---:|
| referens | 11399,2 m | 11399,2 m |
| ägt | 7195,4 m | 7195,4 m |
| falskt | 2053,5 m | 2053,5 m |
| TÄCKNING | 63,12 % | 63,12 % |
| FALSKHET | 18,01 % | 18,01 % |
| blad som rörde sig | | **0** |

Neutral på varje blad med referens; på Priorn-bladet (utan referens) läses `VS` som `VS`. Samma slags beslut
som gate54: en läsning läggs till där det inte fanns någon, och ingen läsning som fanns rörs.

**Beslut: ACCEPT.**

