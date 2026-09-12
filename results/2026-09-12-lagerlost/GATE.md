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


# gate58: lagerlös export - rören tar inte balkarna - ACCEPT

**Ändring.** `pipes/representation.py`, `pipes/ownership.py`, `pipes/frontier.py`, `pipeline.py` (commit 2cf2df0):
ett långt heldraget streck i en streckad rörfamilj är en representationsövergång (`REPRESENTATION_TRANSITION`),
identiteten stannar där; och en penna som är blekare än ledarpennan röstas inte in som rörfamilj på ett blad
utan lager. Bakgrund och diagnos i `FYND.md` (produktionsläsningen W-50-1-AAA-0011: 245,69 m → 129,51 m,
facit 213,7; S3-R8-75 157,6 m → 32,9 m, facit 21,3).

**Körning.** Blind, 59 blad, ögonblicksbild av motorn i `hashmanifest-gate58.json`. Facit lästes först efter körningen.

| | gate57 | gate58 |
|---|---:|---:|
| referens | 11399,2 m | 11399,2 m |
| ägt | 7195,4 m | 7190,7 m |
| falskt | 2053,5 m | 2051,5 m |
| TÄCKNING | 63,12 % | 63,08 % |
| FALSKHET | 18,01 % | 18,00 % |
| blad som rörde sig | | 2 (A0213 −0,8 %, A0111 −0,6 % täckning, −0,4 % falskhet) |

De två bladen som rörde sig är lagrade; där stannar en kedja nu vid ett långt heldraget streck som i själva
verket är rör (ett rör ritat heldraget mellan två streckade delar). Förlusten är 4,7 m av 11 399. Vinsten är på
den lagerlösa exporten, som saknar referens i gaten men har facit i produktionen (213,7 m): 245,69 → 129,51 m,
och den falska balkägandet på 130 m är borta. Nästa steg på det bladet är buntar i en penna (KV1/KV2/VV1) och
antalsprefix (`2x`, `5x`), inte denna regel.

**Beslut: ACCEPT.** Netto: −0,04 % täckning på lagrade blad, −130 m falskt på lagerlösa.
