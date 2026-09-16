# Grind 86 — det atomära intervallet, den transaktionella tilldelningen och sidans egen enhet

**ACCEPT, och en exakt nolla igen.** Tre ändringar tillsammans, alla förutsagda som nollor på korpusen, och
det blev en nolla på varje siffra.

```
gate85.json vs gate86.json: 59 gemensamma blad
  referens    11399.2 ->   11399.2
  ägt          8901.9 ->    8901.9
  falskt       1244.1 ->    1244.1
  TÄCKNING    78.09% ->   78.09%
  FALSKHET    10.91% ->   10.91%
  blad som rörde sig: 0
```

Frysning före körning: manifest `43b23abcce89d825`, commit `a1926a5dc284`, 0 ändrade filer utanför commit.
Prov: 897 gröna. Kontamineringsskanning: PASS.

## Vad som ändrades, och varför var och en skulle bli en nolla

**Det atomära intervallet** (`pipes.representation.interval_id`). Ändrar bara vad journalens poster HETER,
inte hur mycket något är. Nollan var därför inte en förhoppning utan en följd — men den behövde ändå mätas,
eftersom `source_intervals` nu byggs i `_build_pipes` och en ändring där hade kunnat röra rören.

Vad den åstadkommer syns i stället i villkoret. Före: `ett_intervall_en_agare` brast på nio ställen på A0122
och sju på A0121, och jag läste det som dubbelräkning. Efter: PASS på hela korpusen, och de nio fallen visade
sig vara rättmätiga T-delningar vars halvor summerar exakt till källsträckan. Villkoret prövar nu rätt sak.

**Den transaktionella tilldelningen** (`measure/commit.py`). Spärren slår till när två rör gör anspråk på
samma bit. Det finns nu inte ett sådant fall på 59 blad — `n_disputed: 0`, `withheld_m: 0` på vart och ett —
så nollan var väntad. Spärren är för ritningen som ännu inte lästs, och den är provad mot sex syntetiska fall
i stället, inklusive det som säger vad den INTE får göra: två halvor av samma dragna linje är inte en tvist.

**Sidans `/UserUnit`** (`pdf/extract._user_unit`, `measure/scale.discover_scale`). Ingen av de 59 ritningarna
skriver någon `/UserUnit`, mätt över hela korpusen innan koden skrevs. Nollan var därför känd på förhand, och
provet är en syntetisk sida med `/UserUnit 2` som ska mäta dubbelt så långt — plus två prov som säger att ett
oläsbart eller icke-positivt värde behandlas som frånvarande, eftersom en gissad faktor som hela mängden
multipliceras med är värre än att inte veta.

## Att slå ihop tre ändringar i en grind

Det bryter mot en ändring per grind, och skälet är att alla tre var förutsagda nollor på mätbara grunder —
den första ändrar bara namn, den andra har noll fall att verka på, den tredje har noll blad att verka på.
Hade någon av dem flyttat en meter hade grinden inte kunnat säga vilken, och då hade de fått köras om var för
sig. Det gjorde den inte.

## Journalen på riktiga blad

```
takeoff-journal.json (blad A) -> state PASS, 1 371 poster, 1 329 intervall,
                                 0 brott, 0 omtvistade, 0 innehållna meter
```

1 371 poster mot 1 329 intervall: skillnaden är luckor, lodräta sträckor och dubbellinjers andra kanter, som
har egna poster med egen sort. Varje meter i mängdraden går tillbaka till en post, och summan stämmer på fem
millimeter.
