# Alla ritningar med facit: vad som blir fel, och vilka regler som rättar det

Underlag: grind 74, 59 blad, 11 399 m i referensen. Tre mått läggs på varandra - rad mot rad
(`facit_metrics.py`), dragning mot rör (`pipe_audit.py`) och, på de fem blad som har mängdarens egna
mätlinjer, sträcka mot sträcka på ritningen (`markup_metrics.py`).

## Felen, vägda i meter

| vad som händer | rader | meter |
|---|---:|---:|
| raden finns men stråket slutar för tidigt (PARTIAL) | 197 | **1 718 saknas** |
| raden finns men stråket går för långt (OVER) | 174 | **1 407 för mycket** |
| beteckningen lästes, men inget rör fick meter | 86 | 275 saknas |
| beteckningen lästes aldrig | 68 | 286 saknas |
| namn referensen inte har (WRONG) | 86 | 312 för mycket |
| **summa** | | **2 372 saknas, 1 790 för mycket** |

Två saker syns direkt. Det är inte läsningen av namn som är problemet - 88 % av referensens beteckningar
hittas. Det är **utsträckningen**: var ett stråk börjar och slutar. Och saknat och överskott är nästan lika
stora, för det är till stor del *samma* meter som flyttat till grannbeteckningen.

Geometrin bakom det: **1 520 m ritade i en godtagen rörpenna utan ägare** och **442 m tvetydiga**. Det är
1 962 m av de 2 372 som fattas. Metrarna finns alltså på ritningen, i rätt penna, ordentligt inlästa - de har
bara ingen som äger dem.

## Vad som rättats den här omgången

**1. Ett bockmärke är litet.** Frågan "är den här klumpen ett bockmärke?" ställdes på tre ställen i
textläsningen och besvarades olika; ett snedstreck på 14 punkter blev ett märke, försvann ur geometrin, och
etiketten det tillhörde stod utan hänvisningslinje. På W-50-1-A-0033 flyttade det fem meter från S1-P2-75 till
S1-P2-110 medan summan såg rätt ut. Samma gräns på alla tre ställena nu. Grind 74 mot 72: FULL 173 → 177,
WRONG 88 → 86, falskhet 15,76 → 15,70 %. ACCEPT.

**2. En nolla ska säga varför.** 59 rader stod som BEKRÄFTAD med 0,00 m och en sträcka. Alla hade samma orsak:
beteckningens enda stråk är ritat helt inne i en skraffering. Nytt tillstånd `IN_HATCHED_AREA`, och tabellen
visar ett streck med förklaringen i stället för en nolla som ser ut som ett missat rör. Ingen meter flyttar.

## Två regler jag provade och lade ned

Det här är den nyttigaste delen av de markerade ritningarna: de säger nej lika tydligt som ja.

**"Räkna med de skrafferade metrarna."** 2 020 m ligger inne i skraffering och räknas inte. Frestande att
tro att de fattas. Mätt på de fem blad där mängdarens egna mätlinjer finns ligger **0,1-1,2 %** av hennes
meter inne i skraffering. Skrafferingen är hur ritningen säger att en del inte redovisas här, och den som
mängdar mäter inte där. Regeln som finns är rätt; det var bara redovisningen som var fel.

**"En oägd kedja med exakt en namngiven granne tar det namnet."** 85,8 % av den oägda geometrin på
W-50-1-A0133 hänger ihop med precis en namngiven identitet, och ingen annan gör anspråk. Det låter som ett
säkert svar. Mätt mot mängdarens markeringar hade det gett **rätt namn på 38,7 % av metrarna och fel på
54,7 %** - grannen är oftast en kort kopplingsstump (VV1-X31-16) och stråket den skulle döpa är stammen
(VV1-X7-16/W). Regeln hade skapat mer falskt än sant och är inte byggd.

## Nästa regel, och varför just den

Kvar står buntarna. På W-50-1-A0133 heter den oägda geometrin `VVC1-X7-16/W`, `VV1-X7-16/W`, `VV1-X7-25/W` -
kallvatten, varmvatten och cirkulation ritade som tre parallella linjer med en staplad etikett över sig. Av
bladets 121 hänvisningar är 28 tvetydiga, och skälen är `multi_row_token_match_not_unique`,
`multi_row_bundle_awaiting_elimination`, `multi_row_label_shares_one_run`: läsningen ser etiketterna, ser
linjerna, och vågar inte para ihop dem. Den håller inne med svaret, vilket är rätt så länge den inte vet - men
det är där metrarna ligger.

Prisbilden: 442 m tvetydiga direkt, och en stor del av de 1 520 oägda är resten av samma stråk. Det är den
enda kvarvarande posten i den storleksordningen, och den har en egen grind framför sig.

## Blad för blad

| blad | facit m | saknas | överskott | tvetydigt | oägt | FULL/PART/OVER/MISS/WRONG |
|---|---:|---:|---:|---:|---:|---|
| V-50-1-B0122 | 517 | 189 | 105 | 10 | 173 | 4/7/12/10/3 |
| W-50-1-A0111 | 520 | 190 | 102 | 42 | 46 | 3/11/12/8/8 |
| W-50-1-A0113 | 516 | 154 | 92 | 22 | 41 | 5/16/10/13/3 |
| V-50-1-A0122 | 321 | 0 | 204 | 11 | 25 | 2/1/14/0/9 |
| V-50-1-A0423 | 157 | 89 | 75 | 1 | 9 | 2/2/1/0/1 |
| W-50-1-A0134 | 350 | 116 | 36 | 33 | 33 | 3/9/4/5/2 |
| W-50-1-A0132 | 452 | 86 | 63 | 14 | 16 | 8/6/7/1/0 |
| V-50-1-A0521 | 68 | 8 | 129 | 5 | 0 | 0/1/6/2/2 |
| W-50-1-A0131 | 201 | 89 | 43 | 11 | 33 | 5/8/2/6/3 |
| W-50-1-A0124 | 247 | 99 | 21 | 7 | 85 | 5/5/4/14/2 |
| V-50-1-A0422 | 175 | 43 | 75 | 24 | 38 | 2/1/4/3/3 |
| V-50-1-A0123 | 404 | 86 | 31 | 13 | 64 | 8/6/9/7/2 |
| V-50-1-A0412 | 474 | 91 | 24 | 33 | 28 | 4/4/4/5/0 |
| V-50-1-A0312 | 263 | 81 | 29 | 5 | 47 | 1/6/3/5/1 |
| V-50-1-B0114 | 156 | 49 | 62 | 3 | 17 | 2/2/2/1/2 |
| V-50-1-A0112 | 399 | 72 | 33 | 22 | 16 | 10/5/5/3/3 |
| V-50-1-A0522 | 263 | 30 | 76 | 2 | 12 | 2/4/8/1/4 |
| W-50-1-A0114 | 326 | 65 | 36 | 10 | 43 | 5/7/6/9/2 |
| V-50-1-A0124 | 252 | 76 | 23 | 8 | 61 | 3/11/3/9/4 |
| V-50-1-A0421 | 130 | 21 | 76 | 15 | 24 | 0/2/3/1/2 |
| W-50-1-A0122 | 334 | 57 | 40 | 9 | 4 | 7/5/4/6/3 |
| W-50-1-A0133 | 305 | 79 | 13 | 23 | 29 | 5/8/4/3/3 |
| V-50-1-A0212 | 366 | 51 | 32 | 7 | 11 | 3/9/3/5/2 |
| V-50-1-A0512 | 286 | 53 | 30 | 0 | 23 | 5/5/6/2/4 |
| W-50-1-A0213 | 212 | 51 | 30 | 2 | 59 | 3/4/3/1/0 |
| W-50-1-A0123 | 294 | 45 | 33 | 7 | 3 | 7/5/4/1/1 |
| V-50-1-A0121 | 102 | 0 | 61 | 4 | 5 | 0/0/7/0/2 |
| V-50-1-A0111 | 166 | 59 | 1 | 1 | 20 | 1/2/0/4/1 |
| W-50-1-A0121 | 171 | 44 | 15 | 6 | 106 | 7/7/2/3/0 |
| V-50-1-A0222 | 106 | 14 | 38 | 4 | 26 | 1/1/1/3/1 |
| V-50-1-A0322 | 255 | 23 | 26 | 7 | 49 | 3/4/2/2/2 |
| W-50-1-A0222 | 214 | 43 | 3 | 0 | 68 | 6/5/1/0/0 |
| V-50-1-A0311 | 130 | 23 | 13 | 6 | 2 | 1/0/0/1/2 |
| W-50-1-A0211 | 111 | 21 | 13 | 4 | 42 | 1/2/1/0/0 |
| V-50-1-A0511 | 63 | 17 | 16 | 34 | 22 | 2/1/2/2/1 |
| V-50-1-A0411 | 196 | 21 | 9 | 6 | 3 | 5/3/1/0/0 |
| V-50-1-A0323 | 124 | 19 | 6 | 0 | 11 | 1/1/0/2/0 |
| V-50-1-A0523 | 61 | 12 | 13 | 0 | 4 | 1/1/3/4/2 |
| V-50-1-B0112 | 84 | 14 | 9 | 1 | 0 | 1/2/1/0/1 |
| W-50-1-A0112 | 130 | 14 | 8 | 0 | 38 | 1/2/1/2/0 |
| W-50-1-A0032 | 56 | 10 | 9 | 1 | 0 | 0/2/1/0/0 |
| W-50-1-A0221 | 116 | 15 | 0 | 0 | 38 | 3/3/0/1/0 |
| W-50-1-A0214 | 102 | 10 | 2 | 3 | 37 | 2/2/0/3/0 |
| D | 113 | 7 | 4 | 0 | 3 | 5/2/0/2/0 |
| W-50-1-A0022 | 73 | 5 | 4 | 1 | 0 | 1/1/1/0/0 |
| W-50-1-A0024 | 57 | 4 | 4 | 0 | 0 | 0/1/2/0/0 |
| W-50-1-A0034 | 45 | 4 | 4 | 0 | 0 | 0/1/1/0/1 |
| A | 214 | 5 | 3 | 1 | 0 | 8/1/0/0/0 |
| W-50-1-A0011 | 214 | 5 | 3 | 1 | 0 | 8/1/0/0/0 |
| V-50-1-A0223 | 93 | 7 | 0 | 0 | 4 | 1/1/0/3/0 |
| V-50-1-A0221 | 56 | 0 | 6 | 1 | 66 | 0/0/1/0/0 |
| V-50-1-A0321 | 77 | 3 | 3 | 15 | 36 | 2/0/0/0/2 |
| W-50-1-A0033 | 35 | 1 | 2 | 0 | 0 | 1/1/1/1/1 |
| W-50-1-A0023 | 36 | 2 | 1 | 0 | 0 | 1/0/1/0/0 |
| E | 51 | 1 | 1 | 0 | 0 | 2/0/1/0/0 |
| V-50-1-A0211 | 107 | 0 | 1 | 0 | 1 | 1/0/0/0/0 |
| W-50-1-A0031 | 7 | 0 | 0 | 0 | 0 | 2/0/0/0/1 |
| W-50-1-A0021 | 32 | 0 | 0 | 5 | 1 | 3/0/0/0/0 |
| C | 18 | 0 | 0 | 0 | 0 | 2/0/0/0/0 |
