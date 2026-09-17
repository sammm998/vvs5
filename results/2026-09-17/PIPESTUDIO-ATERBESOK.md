# PipeStudio en gång till, och vad mätningen säger om det

*2026-09-17. Utgångspunkt: `S3-R8-160 ska gå hela vägen och även upp till strecket som visar S3-R8-110`.
Körningen som allt räknas ur är gate90 (blind, 59 blad, fryst före körning). Referensmåtten öppnades först
efteråt, och bara för rotorsak - aldrig in i motorn.*

---

## 1. Det utpekade röret: vad det faktiskt mäter

Bladet i skärmbilden är **blad A = W-50-1-A-0011** (samma rader: S3-R8-110 56,27 m / 34 etiketter,
S3-R8-160 16,99 m / 5 etiketter, S3-R8-75 22,51 m / 62 etiketter).

| beteckning | läst | referens | skillnad |
|---|---:|---:|---:|
| KV1-X31-16 | 17,22 | 17,40 | −0,18 |
| KV2-X31-16 | 33,11 | 33,40 | −0,29 |
| S1-P2-110 | 10,04 | 9,80 | +0,24 |
| S1-P2-75 | 3,74 | 4,70 | −0,96 |
| S3-P2-160 | 16,83 | 16,90 | −0,07 |
| S3-R8-110 | 56,27 | 59,80 | −3,53 |
| **S3-R8-160** | **16,99** | **16,30** | **+0,69** |
| S3-R8-75 | 22,51 | 21,30 | +1,21 |
| VV1-X31-16 | 33,92 | 34,10 | −0,18 |
| **summa** | **210,63** | **213,70** | −3,07 |

**S3-R8-160 går redan hela vägen.** Stråket är ett enda rör, `pp_304f64862dc4`, från x=373,4 till x=1250,6
längs y=906,8 - 877 pt = 15,47 m - plus benet ned till rörgenomföringen. Referensen mäter samma stråk som
15,5 m + 0,8 m = 16,3 m; läsningen ligger 0,69 m över, och det överskottet sitter i benet (1,45 m mätt mot
0,8 m) där mätningen går in i symbolen, inte i huvudstråket.

Och gränsen sitter där du pekar. Vid x=1250,64 finns i den rena filen `path_12f2853`: ett 5,69 pt långt
streck i 44° tvärs ledningen, änden på hänvisningslinjen från etiketten `S3-R8 110`. Läsningen satte sin
front exakt där (`REAL_DN_BOUNDARY`, nod 453), och referensens egen markering sitter vid samma tick. Det som
fortsätter åt höger är DN110, och det är vad både ritningen och mängdaren säger.

Så på just det röret finns ingen förlust att hämta. **Men felet du beskriver finns - någon annanstans, och
det är stort.**

---

## 2. Det mätta felet: metrarna ligger på fel dimension av rätt stam

Över hela korpusen, per blad och stam (`VS1-S13`, `KV1-X7`, `S3-R8` …):

```
flyttat inom samma stam        597,8 m       på 38 av 59 blad
  därav: klenare tar grövres   561,8 m       (94 %)
         grövre tar klenares    19,5 m       ( 3 %)

= 48,0 % av allt falskt ägande (1 244 m)
= 23,9 % av allt som saknas    (2 499 m)
=  5,2 % av referensen         (11 399 m)
```

Nästan hälften av allt falskt ägande i systemet är alltså inte fel rör, inte fel system, inte påhittad
geometri - det är **rätt stam med fel dimension**, och riktningen är nästan enhällig: den klenare
dimensionen äter den grövres stråk. De värsta:

| blad | stam | referens → läst |
|---|---|---|
| V-50-1-A0423 | VS21-S13 | `-15` 36,6 → **105,7**, `-22` 82,6 → **1,7** |
| W-50-1-A0132 | VS1-S13 | `-15` 15,3 → **49,2**, `-22` 61,9 → **20,3** |
| W-50-1-A0113 | VS1-S13 | `-54` 14,7 → **34,6**, `-22` 36,3 → **9,3** |
| V-50-1-B0114 | VS31-S13 | `-22` 0,0 → **46,7**, `-28` 29,8 → **0,0** |
| V-50-1-A0112 | VS21-S13 | `-15` 41,0 → **60,2**, `-22` 58,9 → **20,2** |

Mekanismen, avläst på W-50-1-A0132 (meter per skäl, ur bladets egen geometriinventering):

```
36,71 m  VS1-S13|DN12  chain_from_anchor
18,36 m  VS1-S13|DN15  chain_from_anchor
18,14 m  VS1-S13|DN15  unlabeled_branch_takes_the_only_junction_identity   <-- referens: 0 m
16,46 m  VS1-S13|DN22  chain_from_anchor                                   <-- referens: 61,9 m
```

Bladet har **36 etiketter på DN12, 4 på DN15 och 1 på DN22**. Stammen är namngiven en gång; grenarna är
namngivna överallt. Där en onämnd kedja möter en korsning med exakt en bekräftad identitet tar den det namnet
(`unlabeled_branch_takes_the_only_junction_identity`) - och den enda identiteten vid en sådan korsning är
nästan alltid en gren, inte stammen. Så grenens namn vandrar upp i stammen, och stammen står kvar med sina
16 meter.

---

## 3. Vad PipeStudio har som vi inte har

### 3.1 TEE-regeln i `landing_candidates` — värd att bygga

Originalets ord, ur `vectorascore/associate.py` rad 1087:

> *"At a TEE - two collinear pieces (the main) and one or more branches - the label names a branch: the main
> keeps its own designation straight past the junction, the branch's label sits at its foot."*

Och mekaniken: har landningen tre eller fler kandidater och finns **exakt ett kollinjärt par** bland dem, är
det paret stammen - och etiketten får bara namnge grenarna.

Det är precis motsatsen till det som händer på A0132. VVS5 har en del av det: `passes_through` hindrar en
kedja från att ta namnet när en *annan onämnd* arm fortsätter rakt igenom noden. Det som saknas är fallet där
kandidaten själv är grenen: en identitet som bara *slutar* i korsningen (en arm) mot en kedja som fortsätter
ut i nätet.

Det här är en riktig kandidatändring, och den ska ha en egen grind. Den är inte gjord här: den kräver att
geometrin läses blad för blad först, och en gissning på det här stället kostar mer än den ger.

### 3.2 Markeringen tvärs röret utan hänvisningslinje — mätt, och **inte** värd att bygga

PipeStudio klassar en markering på längden: `bucket.tick_rel_min` 1,2–3,0 gånger rörbredden. VVS5 ser bara
ticks som hör till en hänvisningslinje. Frågan var om det finns ensamma reduktionsstreck vi missar.

Nytt verktyg, `engine/tools/tick_census.py`, blint på fyra blad:

| blad | streck tvärs ett mätt rör | med ledare | utan |
|---|---:|---:|---:|
| A | 4 | 3 | 1 |
| W-50-1-A0132 | 4 | 0 | 4 |
| W-50-1-A0113 | 22 | 2 | 20 |
| W-50-1-A0134 | 3 | 0 | 3 |

Och tittar man på vad de *är*: de ligger på lagren `A-A-NTA-T2N`, `K-------Y1-`, `A-46C---E-E` - arkitektens
skraffering. A0113:s tjugo sitter på rad vid x=1404,6 med 3,96 pt mellanrum: ett skrafferingsmönster som
korsar ett KV1-rör. Ett enda streck i hela urvalet ser ut som en verklig reduktionsmarkering (blad A vid
(1031,5, 906,8), på rörets eget lager, 6,08 pt mot 2,04 pt penna).

**Slutsats: att göra sådana streck till gränser skulle klippa stråk vid varje skrafferingskorsning.** Regeln
importeras inte. Måttet är skälet, inte smaken - och det är därför censusen ligger kvar i `tools/`, så att
svaret går att räkna om på ett blad med en annan stil.

### 3.3 `short_only` — noterad, inte prövad

> *"an uninsulated split-form label names a short piece: where its mark also touches a long run, the run
> belongs to the insulated label further along"*

Samma familj av fel som 3.1 (uppgift #92: `VS1-S13-12` tar 36 m av `VS1-S13-35`). Kräver att delad
skrivform och isoleringsbeteckning hålls isär i evidensen innan den går att pröva.

---

## 4. Vad som gjordes i den här omgången

* **Nivåtalen syns där de står.** `VG+1,54` hör till punkten, inte till stråket - en självfallsledning
  faller. Ankaret bär nu sina nivåtal hela vägen ut till bladet, det finns ett eget lager för dem, och
  "Varför?"-rutan redovisar nivåerna längs det valda röret och fallet mellan högsta och lägsta. Tre prov
  håller att ingenting av det rör en vågrät meter.
* **`engine/tools/tick_census.py`** - markeringarna tvärs ett rör, räknade blint.
* Inget i motorns tilldelning ändrades, så gate90 står kvar: täckning 78,08 %, falskt ägande 10,91 %.

## 5. Näst på tur

1. **TEE-regeln (3.1).** Läs A0132 och V-50-1-A0423 blad för blad, formulera villkoret på ritad evidens
   (kollinjärt par = stammen; en arm = gren), grind mot gate90. Potentialen är mätt: 598 m, varav 562 m åt
   ett och samma håll.
2. Uppgift #92 och #93 hör till samma fel och bör avgöras i samma grind.
