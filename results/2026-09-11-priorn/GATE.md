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
