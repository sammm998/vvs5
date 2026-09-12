# gate54: siffervikning i skalförhållandet - ACCEPT

**Ändring.** Efter `1:` i en skalstämpel viks bokstäver som ser ut som siffror till siffror (O→0, S→5, I/l→1,
B→8, Z→2, G→6), bara i den positionen. Bakgrund i `FYND.md`: ett blad skrev SKALA 1:50, läsningen såg `1:S0`
och kastade raden.

**Körning.** Blind, 59 blad: de 33 som gate53 hade, plus 26 W-blad vars referens hämtats från Drive. Motorns
källa hashad i `hashmanifest-gate54.json`. Facit lästes först efter körningen.

## Mot gate53, blad för blad (33 gemensamma)

| | gate53 | gate54 |
|---|---:|---:|
| referens | 6245,0 m | 6245,0 m |
| ägt | 4965,8 m | 4965,7 m |
| falskt | 1503,6 m | 1503,6 m |
| TÄCKNING | 79,52 % | 79,52 % |
| FALSKHET | 24,08 % | 24,08 % |
| blad som rörde sig | | **0** |

Ändringen är neutral på varje blad som redan hade skala. Det är precis vad den ska vara: den lägger till en
läsning där det inte fanns någon, och rör inte en läsning som fanns.

**Beslut: ACCEPT.**

## Ny baslinje: W-stilen på 30 blad

Med de 26 nya W-bladen är W-stilen inte längre fyra blad utan trettio, och talet är ett annat:

| Stil | Blad | Ref m | Täckning | Falskhet | Bet. recall |
|---|---:|---:|---:|---:|---:|
| V (textlager) | 29 | 5849,9 | 78,8 % | 25,6 % | 80,8 % |
| W (konturglyfer) | 30 | 5549,3 | **46,3 %** | 10,0 % | 63,6 % |

Fyra W-blad läses till noll: `W-50-1-A0022`, `A0023`, `A0031`, `A0034` - de små SEWAGE-bladen (7-73 m
referens vardera). Spannet i övrigt är 18-99 %. `W-50-1-A0011` och `A` är samma blad och räknas två gånger i
W-raden; det ska rättas i parningen.

Den här baslinjen är den som nästa ändring i teckentydningen (schablontypsnittet, `FYND.md`) ska mätas mot.

---

# gate55: rutregeln för schablonbokstäver - REVERT

**Ändring.** Första formen av regeln i `text/strokes.py`: ett kluster som ryms i en teckenruta (≤ 1,3 H) är ett
tecken och byggs av alla sina bitar. Bakgrund i `FYND.md`.

**Körning.** Blind, 59 blad, samma indata som gate54. Motorns källa hashad i `hashmanifest-gate55.json`
(commit c7de2516153a + den ändrade `strokes.py`). Facit lästes först efter körningen.

## Mot gate54, blad för blad (59 gemensamma)

| | gate54 | gate55 |
|---|---:|---:|
| referens | 11399,2 m | 11399,2 m |
| ägt | 7183,4 m | 6822,7 m |
| falskt | 2053,5 m | 2083,6 m |
| TÄCKNING | 63,02 % | 59,85 % |
| FALSKHET | 18,01 % | 18,28 % |
| blad som rörde sig | | **21** |

Sju blad föll långt: `W-50-1-A0021` -98,6 pp, `E` -97,2, `W-50-1-A0024` -93,7, `W-50-1-A0033` -84,6,
`W-50-1-A0032` -82,8, `D` -70,7, `C` -60,9 (och +60,9 pp falskhet). Rotorsaken hittades på E och D innan
körningen var färdig: två smala tecken intill varandra - `75`, `D1`, `S1`, `IL` - ryms i samma ruta och
slukades till ett oläsligt tecken. Rutan säger att klustret är litet, inte att det är *ett* tecken.

**Beslut: REVERT** av den formen. Ersatt av regeln i commit ed14a8a (bitarna måste vara bitar: kortare än H
tvärs stapelriktningen, någon en bråkdel, åtskilda med glapp, lästa i en riktning bladet skriver i), som läser
E och D rad för rad som gate54 och mäts som gate56.

---

# gate56: schablonbokstäver, slutlig form - ACCEPT

**Ändring.** Regeln i `text/strokes.py` (commit ed14a8a): ett kluster som ryms i en teckenruta är ett tecken
när dess bitar är bitar och inte tecken i en rad - kortare än H tvärs stapelriktningen, någon en bråkdel,
åtskilda med glapp längs stapelriktningen - och läses tvärs den axeln i en riktning bladet skriver i.
Bakgrund i `FYND.md`; den första formen backades som gate55.

**Körning.** Blind, 59 blad, samma indata som gate54/55. Motorns källa hashad i `hashmanifest-gate56.json`
(commit 0c37d4b, 0 ändrade filer). Facit lästes först efter körningen.

## Mot gate54, blad för blad (59 gemensamma)

| | gate54 | gate56 |
|---|---:|---:|
| referens | 11399,2 m | 11399,2 m |
| ägt | 7183,4 m | 7195,4 m |
| falskt | 2053,5 m | 2053,5 m |
| TÄCKNING | 63,02 % | **63,12 %** |
| FALSKHET | 18,01 % | 18,01 % |
| utsträckning FULL / PARTIAL | 96 / 213 | **98** / 211 |
| blad som rörde sig | | **2** (A +2,8 pp, W-50-1-A0011 +2,8 pp - samma blad) |

Inget blad föll. Det bladet regeln skrevs för (V-50-1-A0001, Priorn) har ingen referens och räknas inte här;
där läses nu koden `S` i förklaringslistan och spillvattnet får meter (`FYND.md`).

**Beslut: ACCEPT.** Ny baslinje för nästa ändring: gate56.
