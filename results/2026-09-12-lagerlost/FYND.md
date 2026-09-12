# Samma ritning, två exporter: 191 m med lager, 246 m utan

**Anmälan.** I produktion mätte ett blad 246 m där facit säger 213,7 och en tidigare läsning gav ~212. En
beteckning, `S3-R8-75`, stod på 157,6 m med 56 etiketter och 19 sträckor; överlägget följde långa linjer längs
väggarna - "tar med längst hela väggen där de inte rör".

## Vad det var

Bladet är `W-50-1-A0011`. Korpusen har det i CVAT-exporten (`data/cvat/CVAT/W-50-1-A-0011.pdf`, 467 kB), och
grinden läser den till 190,5 m. Filen som lästes i produktion är en annan export av samma ritning
(`data/styles/test/W-50-1-AAA-0011.pdf`, 655 kB, en anteckning), och den ger exakt produktionens tal: 245,69 m,
`S3-R8-75` 157,6 m.

Samma streck, samma pennor (12 531 banor svart 0,72, 3 672 beige fyllningar, 1 006 grå 0,72 ...). Skillnaden:

| | CVAT-exporten | AAA-exporten |
|---|---:|---:|
| banor | 25 225 | 25 231 |
| CAD-lager | **43** | **1 (tomt)** |
| optionellt innehåll | 43 | 0 |

Utan lager är en rörfamilj bara en penna. Den grå 0,72-pennan ligger i den lagrade exporten till 80 % på
konstruktionslager (`K-15S---EK_` 701 banor, `K-------EK_` 93 - de dolda pålbalkarna, streckade) och till en
liten del på rörlager (`V-53BB-FE--S3-` 76). I den lagerlösa exporten är allt detta en familj om 1 836
primitiver, och fjorton ledarspetsar från `S3-R8-75`-etiketter träffar den: rören *ligger på* pålbalkarna
("FÖRLÄGGS PÅ PÅLBALK"). Familjen röstas in som rörfamilj (54 röster, 14 ticks), och sedan rinner namnet:

| rör | m | bitar | av vad | skäl |
|---|---:|---:|---|---|
| pp_396b… | 63,96 | 28 | 18 av 28 längre än 60 pt, upp till 658 pt: rektangeln 424–1082 × 455–1315 | chain_before_first_anchor 12, collinear_through_junction 9, unlabeled_branch 6 |
| pp_6882… | 42,99 | 183 | 183 streck om 11 pt | chain_with_agreeing_anchors |

Det första röret är husets pålbalksram; det andra är ett rör. Samma penna, samma familj, olika ritsätt: streck
om 11 pt med 4,25 pt glapp mot heldragna linjer om flera hundra punkter.

Bevisat att det inte var något annat: projektkunskap från syskonblad (`known_families` från 4 och från alla 25
W-blad) ändrar inte A:s läsning (191,29 i båda fallen); andra läsaren var inte inblandad i återskapandet.

## Reglerna

Två, båda ur bladets eget bläck (`pipes/representation.py`, `pipes/ownership.py`, `pipes/frontier.py`,
`pipeline.py`):

1. **En lång heldragen linje i en streckad familj är ett annat ritsätt.** Tröskeln är familjens egen:
   åtta streck, eller fyra streck-och-glapp (`solid_long_threshold`), mätt på källsegmentet före T-delningarna
   (en balk som korsas av tio ledningar är tio korta bitar i grafen och en lång linje på pappret). Namnet
   rinner inte in i en sådan linje - inte längs kedjan bortom den yttersta etiketten, inte rakt genom en
   korsning, inte som onämnd gren - utan egen etikett; sitter en etikett på den heldragna delen är den
   röret där. Mellan två etiketter som är överens är kedjan röret vad den än är ritad med. Fronten säger
   `REPRESENTATION_TRANSITION` där namnet stannade.
2. **På ett blad utan lager är en penna som är blekare än ledarna inte en rörfamilj.** Vikten är bredd gånger
   mörkhet: grått (0,73) 0,72 väger 0,19, svart 0,48 väger 0,48. Ritaren ritar inte röret svagare än linjen
   som pekar på det. Regeln gäller bara familjer utan lagernamn; ett lager är bladets eget besked.

## Efter reglerna

| | facit | CVAT (lager) före | CVAT efter | AAA (lagerlös) före | AAA efter |
|---|---:|---:|---:|---:|---:|
| S3-R8-75 | 21,3 | 22,62 | 22,62 | **157,60** | **32,91** |
| S3-R8-110 | 59,8 | 56,21 | 56,21 | 46,84 | 46,84 |
| S3-R8-160 | 16,3 | 16,99 | 16,99 | 16,99 | 16,99 |
| S3-P2-160 | 16,9 | 16,83 | 16,83 | 15,27 | 16,82 |
| KV1-X31-16 | 17,4 | 17,09 | 17,09 | 0 | 0 |
| KV2-X31-16 | 33,4 | 26,86 | 26,86 | 4,18 | 11,14 |
| VV1-X31-16 | 34,1 | 33,91 | 33,91 | 4,81 | 4,81 |
| **summa** | **213,7** | 190,51 | 190,51 | 245,69 | 129,51 |

Den lagrade exporten läses exakt som förut. Den lagerlösa tappar 116 m falsk `S3-R8-75` och står nu *under*
facit i stället för över - för den missar rör, och det är nästa fel:

## Nästa fel på samma export: bunten i en penna

`KV1`, `KV2` och `VV1` ligger på tre lager i den lagrade exporten (`V-52BB-FE--V1-`, `-V2-`, `V-52BC-FE--V1-`)
och läses till 17 + 27 + 34 m. Utan lager är de en familj (svart 1,44) om tre parallella streckade linjer, och
etiketterna är staplade bunt-etiketter med antal: `2xKV1-X31 / 16`, `5xKV2-X31 / 16`. Läsningen ger 0 + 11 + 5 m
och lämnar 3 m tvetydigt per kod. Två saker saknas: att skilja tre parallella linjer i samma penna åt som tre
delfamiljer ur bladets eget avstånd mellan dem (mandatets *paired-wall / bundle spacing*), och att läsa
antalet i etiketten (`2x`, `5x`) som det antal rör koden gäller. `KV1-X31` läses dessutom utan sin DN, som
står på raden under prefixet - beteckningsgrammatiken behöver ta `Nx` som prefix.

Det är en egen ändring och en egen grind.

## Grindarna

- gate57: grannriktningsregeln för korta rader (`text/strokes.py`) - mäts först, för sig.
- gate58: de två reglerna här - mäts mot gate57.
