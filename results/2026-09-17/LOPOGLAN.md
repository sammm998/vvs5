# Löpöglan 2: tre fel på ett osett blad, i den ordning de sitter

En ritning ur den öppna världen, uppladdad efter att den lästs i produktion: 8 mängdrader och 116,66 m på ett
blad med 652 ritade meter — och läsningen rapporterade samtidigt **full täckning**.

Bladet är specens egen stilreferens `lopoglan-booklet` (Bengt Dahlgren, Ghostscript 9.21, "Löpöglan 2.pdf").
A1, 2384×1684 pt, ett enda lager med 27 366 vägar. Ingen av de 59 bladen i utvecklingskorpusen bär ett
KB-system, så ingenting av det som mätts säger något om den här ritningen.

Läsningen reproducerades lokalt, rad för rad identisk med produktionens.

---

## Fel 1 — pennan som skriver etiketterna ritar också rören

**Störst, och först i kedjan.**

Bladet är lagerlöst, så pennan *är* familjen. Bläcket fördelar sig så här:

| bredd | segment | längd pt | ≈ meter |
|---:|---:|---:|---:|
| 0,51 | 14 643 | 113 653 | 2 005 |
| **0,72** | **17 338** | **71 416** | **1 260** |
| 1,41 | 3 383 | 30 700 | 542 |
| 0,99 | 417 | 3 601 | 64 |

Motorn valde `0,99` och `1,41` som rörfamiljer — tillsammans 605 m — och skrev om `0,72`:

```json
"annotation_layers": {"|s|w0.72|c(0.0, 0.0, 0.0)": 413}
```

413 anteckningsobjekt på pennan räckte för att döma hela den som skrift. Men det är den pennan rören är
ritade med. Mätt på ledarnas ändpunkter, som är det enda beviset som räknas:

```
S1-ledare som INTE når rör          S1-ledare som NÅR rör
  [742.71, 664.69]  0,72: 1           [1031.13, 776.05]  0,72: 41
  [739.59, 614.29]  0,72: 3           [ 791.67, 715.18]  0,72: 34
  [724.74, 614.29]  0,72: 1           [ 584.40, 734.74]  0,72:  2
```

**Varje** ändpunkt landar på 0,72 — både de nio som misslyckas och de fyra som verifierar. De fyra som gick
igenom råkade landa där 0,72-bläcket är tätt nog att en granne i en annan penna fanns inom räckhåll.

Specens egen stilreferens säger det rent ut: `pipes 0.72, grid lines 0.27`.

Det här är samma klass av fel som den lagerlösa exporten och väggen som behandlas olika per kontor: **på ett
lagerlöst blad bär en penna flera roller, och att döma hela pennan efter sin tydligaste roll kastar bort allt
annat den ritar.** Fixen får därför inte vara att räkna 0,72 som rör — den måste skilja glyfer och ledare från
rörgeometri *inom* en penna, och den måste gå genom korpusgrinden.

## Fel 2 — bokstaven K raderade varje system som inte började på K

Rättat i commit `7a88d76`, och beskrivet där. Kort: namnrutans handlingsförteckning (`A`, `L`, `K`, `KP`,
`E`, `VVS`) lästes som beteckningslista; `K` fick äga `KB1`, `KB2`, `KV2` på rent prefix, befordrades till
systemkod av just de etiketterna, och användes sedan som vit lista. De åtta raderna i mängden var inte de
åtta system motorn kunde mäta — det var de åtta som råkade börja på K.

Mätt efter rättelsen: S1 går från 0 av 15 lästa rörnamn till 15 av 15, VS från 0 av 2 till 2 av 2.

**Det löste inte mängden.** S1:s ankare säger `leader_endpoint_touches_no_pipe_geometry` på nio av tretton,
före som efter — för att rörgeometrin ligger i en penna som aldrig övervägdes. Fel 2 satt efter fel 1.

## Fel 3 — nollan läses som bokstaven O

Ritningen skriver `KB2-09-20`; tabellen säger `KB2-O9-20`. Fem av åtta rader. En rad som heter `KB1-O9-32`
matchar ingen prislista.

Alla rörnamn på bladet är **ritade som streck** — den sökbara texten är arkitektens (rumsnamn, areor,
ljudkrav, måttkedjor) och innehåller inte en enda VVS-beteckning. Hela läsningen av namnen går därför genom
glyfläsaren, och det här är den tydligaste formförväxlingen som setts.

Värt att notera om källbiblioteket: `lopoglan-booklet` klassas där som `text_mode: "text"`. Det stämmer för
bladet som helhet och är vilseledande för det som räknas. Ett textläge som mäts på all text döljer att
etiketterna är streck.

---

## Täckningssiffran, som är det farligaste

| | före rättelsen | efter |
|---|---:|---:|
| rörnamn | 9 | 67 |
| med meter | 9 | 7 |
| **share** | **1,00** | **0,104** |
| utan ägare | 552 m av 652 | 554 m av 652 |

Före sa bladet **full täckning** medan 85 % av det ritade röret saknade ägare — för de raderade etiketterna
räknades aldrig som saknade. Talet som skulle ha larmat var det som såg bäst ut. Efter rättelsen visar det hur
illa det står, vilket är hela poängen med att ha det.
