# Grind 85 — mängdjournalen mot korpusen, och en rättelse jag måste göra

**ACCEPT, och en exakt nolla.** Journalen (c8631c1) ändrar ingen meter på något av de 59 bladen.

```
gate82.json vs gate85.json: 59 gemensamma blad
  referens    11399.2 ->   11399.2
  ägt          8901.9 ->    8901.9
  falskt       1244.1 ->    1244.1
  TÄCKNING    78.09% ->   78.09%
  FALSKHET    10.91% ->   10.91%
  blad som rörde sig: 0
```

Det var det förutsagda utfallet och det enda godtagbara: journalen skriver ned vad läsningen gjorde, den
rättar ingenting. En journal som hade flyttat en meter hade varit en bugg, inte en förbättring.

Frysning före körning: `results/hashmanifest.json`, manifest `589c8737005bad51`, commit `c8631c12ee01`,
0 ändrade filer utanför commit. Arbetsträdet har rört sig efter körningen (nästa steg byggdes medan grinden
gick), så manifestet gäller commit:en som processen laddade, inte trädet som det ser ut nu.

---

## Rättelse: de delade intervallen var inte dubbelräkning

I commit c8631c1 skrev jag att journalens första villkor brast på två W-blad och att alla delade intervall låg
under **olika** identiteter — "genuin dubbelräkning över mängdrader". **Det var fel, och felet var mitt
instruments.**

```
W-50-1-A0122: FAIL  poster 3007  intervall 2792  brott [('ett_intervall_en_agare', 9)]
W-50-1-A0121: FAIL  poster 2771  intervall 2657  brott [('ett_intervall_en_agare', 7)]
```

Jag mätte vad de nio fallen på A0122 faktiskt var, rör för rör, och de ser likadana ut allihop:

```
=== path_57668eeeee84#6
    pp_28dbc2c6ebc9 S2-P5|DN110  längd ur källsträckan  4,20 pt   (414,60 → 410,40)
    pp_6a8e193c2fde S2-P5|DN75   längd ur källsträckan 10,92 pt   (410,40 → 399,48)
    källsträcka 15,12 pt          summa rör 15,12 pt

=== path_c299f82180c0#0
    pp_0f89f5ad7894 KV1-X7-W|DN16  2,28 pt   (531,36 → 533,64)
    pp_a67a8777bc65 KV1-X7-W|DN20  3,72 pt   (527,64 → 531,36)
    källsträcka 6,00 pt            summa rör 6,00 pt
```

Rören äger **skilda, angränsande halvor** av en och samma dragna linje, och halvorna summerar exakt till
källsträckans längd. Ingen meter räknades två gånger. Det är ett T mitt på en sträcka: en huvudledning och en
gren möts, `split_t_junctions` delar linjen där, och `_apply_cuts` ger varje bit tillbaka sitt ursprungs `pid`
och `seg_index` — med flit, härkomsten ska inte gå förlorad.

Men då är `pid#seg_index` **inte** namnet på ett atomärt intervall. Det är namnet på källsträckan. Villkoret
"ett intervall, en ägare" ställdes alltså mot fel enhet och larmade på en ritning där ingenting var fel.

Jag borde ha mätt innan jag drog slutsatsen. Att två ägare bar *olika* identiteter såg ut som ett bevis för
dubbelräkning; det var lika förenligt med ett T, vilket är det vanligare fallet på en VVS-ritning.

---

## Vad som byggdes av rättelsen

`pipes.representation.interval_id(prim)` — biten skiljs på sin egen startpunkt, som delningen lägger i ordning
längs sträckan, så två bitar av samma källsträcka aldrig börjar på samma ställe. Namnet bär både härkomsten
(`pid#seg_index`) och var på sträckan biten börjar. `PhysicalPipe.source_intervals` bär dem vid sidan av
`source_segments`, som behåller sin betydelse.

`measure/commit.py` — den transaktionella tilldelningen (spec steg 7): anspråken samlas, hela tilldelningen ses
på en gång, en bit med två ägare räknas åt **ingen** av dem utan blir tvetydig med sina alternativ, och först
på det som blev kontrolleras villkoren. Att välja den ena ägaren vore en gissning som ser ut som ett besked.

`pdf/extract._user_unit` + `measure/scale.discover_scale` — sidans `/UserUnit`. Ingen av de 59 ritningarna
skriver någon, så spärren är inert på korpusen; den är provad mot en syntetisk sida i stället.

Grind 86 avgör de tre tillsammans.
