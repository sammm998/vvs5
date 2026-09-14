# Plan: varje flik ett steg bättre, och läsningen mot facit

Skriven 2026-09-14, mot det systemet faktiskt gör i dag. Varje punkt är mätbar: den har ett läge nu, ett
mål, och ett sätt att se att målet nåtts. Ordningen är den jag tänker arbeta i.

---

## 0. Frågan först: borde inte bladen med facit ge exakt facit?

Nej - och det är viktigt att veta varför, för annars jagar vi fel siffra.

**Läget nu** (grind 61, 59 blad, blint mot 11 399 referensmeter):

| | |
|---|---:|
| täckning (ägda meter som facit också har) | **75,0 %** |
| falskhet (ägda meter facit inte har) | 19,5 % |
| blad över 90 % täckning | 12 |
| blad under 50 % | 6 |

**Tre skäl till att 100 % inte är målet, och ett till att 95 % är det.**

1. **Facit är en människas mängdning, inte ritningens sanning.** Vi har hittat och verifierat tre slag av fel i
   facit: A0113 skriver `VS1-S13-12` där ritningen skriver `VS1-S13-12/W` (måttstocken faller nu
   monteringssuffix); A0134 har ingen enda meter `VS1-S13-22` fast ritningen skriver ut beteckningen på
   bladet (kontrollerat i bilden); V-50-1-A0222 slutar mäta vid en vägg medan det ritade röret fortsätter
   åt höger. Det är inte fel i läsningen - det är två läsare som gjort olika.
2. **Mängdaren räknar sådant ritningen inte skriver.** Stigare, kopplingsledningar till apparater, påslag för
   böjar. Läsningen mäter det ritade och säger när den inte vet: `VERTICAL`, `SYMBOL`, `REAL_DESIGNATION_BOUNDARY`.
3. **Läsningen svarar hellre "vet inte" än fel.** En bunt som bladet inte avgör står kvar som fråga. Det sänker
   täckningen med flit.

**Målet är därför:** täckning ≥ 95 % och falskhet ≤ 5 % **på det ritningen själv skriver ut**, och varje
kvarvarande skillnad mot facit förklarad i reconciliation-rapporten med skäl och koordinat. Det är den
siffran jag kör mot nedan.

**Vägen dit, i storleksordning (mätt på grind 61):**

| Rotorsak | Vad det kostar nu | Status |
|---|---|---|
| Raden som föll ur förklaringslistan → fyra blad mätte noll | 161 m (0 → 165 m) | **klar** (commit 8143e59) |
| Självslingan i noden: böjar blev fyrarmade knutar | ~380 m | **klar** (ae66170) |
| DN-gränsen på en hel kedja: en etikett tar hela stråket | ~90 m falskt | nästa |
| Bunten som aldrig avgörs (VV1/VVC1 på ett lager) | ~120 m | regel skriven, grindas |
| Identiteten genom pennbyte (FE → KE, dolda ledningar) | ~60 m | utreds |
| Ägt utanför mängdarens markering (V-bladen) | ~200 m "falskt" | troligen facitfel, dokumenteras |

Arbetssättet ändras inte: blind körning, frysning, facit öppnas efteråt, en regel i taget, accept eller back.

---

## 1. Agent - egen flik, fristående

**Nu:** `/agent` är en väljare framför två agenter som bor i analysen och i projektet. Man måste ha ett projekt
och ett läst blad för att få fråga något.

**Mål:** en egen agent som inte vet något om projekt förrän du ger den något. Du släpper en PDF i chatten och
frågar. Den är inte samma agent som i analysen - den analysen har sina verktyg mot en färdig läsning; den här
har sina egna:

- `las_ritning(fil)` - kör läsningen på en uppladdad PDF och svarar med mängder, skala och vad som blev
  tvetydigt. Kostar credits som vilken läsning som helst, och går att öppna i Analys efteråt.
- `titta_i_filen(fil)` - vad filen är: sidor, ritningsnummer, skalans tillstånd, vilka beteckningar som står
  där. Billigt, ingen mätning.
- `mangder(fil)`, `jamfor(fil_a, fil_b)` - tabellen, och skillnaden mellan två revideringar.
- `rakna(uttryck)` - aritmetik med enheter. Aldrig ett tal som inte kommit ur en fil eller ur frågan.
- `material_pris(namn)`, `kalkyl(rader)` - mot materialregistret, för en snabb kostnadsfråga.

Samma löfte som överallt: modellen väljer fråga, motorn ger svar, och ett tal utan belägg blir "det står inte
i handlingen". Filer ligger på användaren, inte på ett projekt, och kan flyttas in i ett projekt efteråt.

**Klart när:** man kan dra in en PDF i chatten, fråga "hur många meter VS1 finns här", få ett svar med
belägg och en knapp till analysen - utan att ha skapat ett projekt.

## 2. Analys - fliken där arbetet görs

**Nu:** ritningen till vänster, mängder/agent/rätta/markera/översikt/export/kalkyl till höger, tre vyflikar
över ritningen. Det fungerar, men tre saker skaver.

1. **Det tvetydiga är gömt i en lista.** En sträcka som inte mättes syns bara om man letar. Mål: ett lager över
   ritningen som visar exakt var läsningen stannade och varför (fronterna finns redan som data), med filter per
   skäl och en knapp "visa nästa fråga" som panorerar dit.
2. **Rättelsen ska vara ett klick.** I dag: välj rad, välj verktyg, rita. Mål: klicka på en tvetydig sträcka,
   välj bland de kandidater ritningen faktiskt erbjuder, klart - och nästa liknande fall föreslås automatiskt
   ("samma penna, samma glapp, 14 ställen till").
3. **Vad kostade bladet.** Credits per blad står i en annan flik. Mål: en rad i huvudet: tid, credits, andel
   mätt, andel frågor.

## 3. CAD - ritbordet

**Nu:** hel byggmodell (36 entitetstyper), 2D+3D, snitt, blad, IFC/DXF/SVG/GLB in och ut, kollisioner,
mängder, agent som föreslår. Avgränsningarna står i `BUILDING_CAD_READY.md`.

**Nästa tre steg, i ordning:**
1. **Underlaget och läsningen möts.** Lägg en läst ritning som underlag och låt de lästa rören bli riktiga
   rörobjekt i modellen med ett klick ("ta in det lästa"). I dag är underlag och läsning två världar.
2. **Villkor (constraints).** Lika längd, parallell, låst avstånd - det som gör en modell redigerbar i stället
   för omritad. Rutnätsbindning finns redan som relation.
3. **Geringar i hörn och lutande tak vid IFC-import** - de två avgränsningar som syns mest i mängderna.

## 4. Mängda - handmängdningen

**Nu:** kalibrering, snap, ortho, avdrag, djup, markeringslista, export. I nivå med Bluebeam för det vanliga.

**Nästa:** (a) mät mot den lästa geometrin - snap till ett läst rör och få dess längd i stället för att följa
det för hand; (b) mallar per system (färg, enhet, påslag) som följer med projektet; (c) två personer på samma
blad utan att skriva över varandra (versionsfält finns).

## 5. Kalkyl och anbud

**Nu:** mängder → rader → anbud i webbläsaren, ABT 06/AB 04-neutralt, PDF med sidbildsförhandsgranskning.

**Nästa:** (a) prisbanken som egen sak med historik per artikel; (b) ett anbud som kan revideras (v2 mot v1 med
skillnaden i klartext); (c) täckningsbidrag per system, inte bara totalt.

## 6. Projekt och projektanalys

**Nu:** handlingen som modell, blad för blad, med korsvis kontroll mellan bladen.

**Nästa:** (a) revideringar: två versioner av samma blad, vad ändrades i mängd; (b) en kvalitetssiffra per
handling ("81 % av bladen lästa, 6 blad med frågor") på förstasidan; (c) export av hela handlingens mängder
i ett kalkylark med bladkolumn.

## 7. Material, Credits, Admin, Lär dig VVS

- **Material:** registret finns. Nästa: koppla artikel till beteckningsmönster så att en läsning kan föreslå
  artikel direkt.
- **Credits:** priset per blad är kalibrerat (`KOSTNAD.md`). Nästa: visa vad nästa läsning *kommer* att kosta
  innan man trycker, ur bladets storlek.
- **Admin:** överblick, rättelser, inlärning, affiliate, CRM, CMS, A/B. Nästa: en hälsosida som visar grindarnas
  historik - täckning och falskhet över tid, per ritningskontor.
- **Lär dig VVS:** moduler och progress finns. Nästa: låt en lektion peka på ett riktigt blad i systemet.

---

## Ordning

1. Fristående agent (denna vecka).
2. DN-gränsen och bunten - de två regler som ger mest mot facit.
3. Analysfliken: fronterna som lager, rättelse på ett klick.
4. CAD: ta in det lästa i modellen.
5. Resten i tur och ordning ovan.
