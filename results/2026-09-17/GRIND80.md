# Grind 80: klippmedveten extraktion — ACCEPT

Blint kört på 59 blad. Källan frusen **före** körningen den här gången (manifest `e14c46459cd95572`, commit
`3b16dcb`, noll oincheckade filer) — felet jag redovisade i `results/2026-09-16/GRIND76-79.md` är rättat.
Referensen öppnades först efteråt.

| | täckning | falskt ägande | textrecall | precision | FULL | PARTIAL | OVER | MISSED | WRONG |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **79** utgångsläget | 78,56 | 15,22 | 86,93 | 79,20 | 175 | 196 | 171 | 158 | 80 |
| **80** klippmedveten | 78,02 | **10,95** | 86,93 | **80,58** | **187** | 202 | **153** | 161 | **65** |

**Falskt ägande föll 4,27 procentenheter. Täckningen föll 0,54.** Åtta falska meter bort per riktig meter
förlorad. Textrecallen står still på decimalen — inga beteckningar slutade läsas, bara mätas.

## Vilka meter försvann, och varför

| | gate79 | gate80 | skillnad |
|---|---:|---:|---:|
| ägda meter | 8 955,8 | 8 893,4 | −62,4 |
| falska meter | 1 735,2 | 1 248,3 | **−487,0** |
| för långt stråk på en rad referensen har | 1 432,7 | 986,3 | −446,4 |
| meter under ett namn referensen inte har | 302,5 | 262,1 | −40,4 |

De 487 metrarna är alltså nästan uteslutande *stråk som ritats längre än de är* — inte påhittade rör. Det är
precis vad dold xref-geometri gör: den fortsätter ledningen ut ur planens ram, och mätningen följde med.

Rad för rad: **47 rader hamnade närmare referensen (481 m närmare), 15 längre ifrån (58 m).** De grövsta:

    blad            beteckning       referens   gate79   gate80
    V-50-1-A0521    KV1-X31-16            0,5     55,2      0,4
    V-50-1-A0421    KV1-X31-16           42,4     76,0     38,7
    V-50-1-A0222    VS21-S13-15          69,6     99,5     65,2
    V-50-1-A0521    VV1-X31-16            0,5     31,7      0,4
    V-50-1-A0122    SF1-P5-110           14,5     33,1      3,1

Den första raden är hela felet i miniatyr: mängdaren mätte en halv meter KV1-X31-16 på A0521, vi mätte 55.
Femtiofyra av dem ritades aldrig på det papperet.

Rör för rör (`pipe_audit.py`) säger samma sak från andra hållet: 3 114 → 3 011 rör, varav **EXTRA_RUN 642 → 563**
(rör utan någon motsvarighet alls i referensen) och **LONG_RUN 214 → 195**. MISSING_RUN gick *ned* med 10 — tio
mätta dragningar hittade en partner när det falska röret slutade konkurrera.

Där det blev sämre är det samma mekanism som slår för hårt: `V-50-1-A0322 VS21-S13-15` gick från 88,3 (ref 82,5)
till 64,5. Ett stråk som fortsätter förbi klippkanten klipps nu vid kanten, och när mängdaren räknat med
fortsättningen blir vi korta. Det är bladkopplingsfrågan, och den är inte löst här — klippgränsen är en
stoppgräns för den här vyn, och det står utskrivet i koden.

## Vad som ändrades i motorn

`engine/vvs_engine/pdf/extract.py` `_read_page`: `get_drawings(extended=True)`, varje väg bunden till sin
styrande klippbana, varje segment skuret mot den så att **den synliga delen** behålls — inte ett ja/nej.
Snabbvägarna först (helt innanför → orört; rektangel → Liang-Barsky; shapely bara för äkta polygoner).
`RawPath` bär rågeometrin vid sidan av den synliga, så härkomsten inte går förlorad.

Bindningen bevisades mot renderaren **innan** en rad i motorn ändrades (`results/2026-09-17/KLIPP.md`).
Två av mina tre mätningar av hur mycket som är dolt var fel, och renderaren fällde den andra.

I korpusen: **24 blad har klippbanor, 16 107 vägar ligger helt utanför dem och 963 skärs.** Tyngdpunkten är
tolv V-blad; W-serien har en handfull skurna vägar var.

## Ett fel som grinden avslöjade, och som inte är mitt

> **Rättelse, skriven efteråt.** Avsnittet nedan sa först att en ritnings läsning beror på vilka ritningar som
> lästes före den i samma process. Det stämmer inte. Jag hade bara varierat processen, och tog sammanträffandet
> för ett samband. Det verkliga felet står under rubriken efter, och det är värre.

Elva blad ändrade tal. Tio är V-blad med verklig klippning. Det elfte, **W-50-1-A0122, har ingen klippning alls**
— och flyttade ändå 2,5 m. Jag jagade det i stället för att skriva av det.

## Samma ritning, olika process, olika meter

`PYTHONHASHSEED=3` ensamt ger gate80:s läsning av W-50-1-A0122. Frö 0, 1, 2 och 4 ger en annan. Inget grannblad,
ingen varm cache, samma fil och samma kod - bara vilken process läsningen råkade köra i.

Orsaken sitter i `pipeline.py`, i buntutjämningen som avgör vilken linje i en staplad etikett som är vilken:

    for sysname in set(systems):          # ordningen = Pythons slumpade strängnycklar
        takers = [pc for pc in pieces if sysname in domain.get(pc, ())]
        if len(takers) == 1 and len(domain[takers[0]]) > 1:
            domain[takers[0]] = {sysname}   # ...och det här ändrar vad nästa varv läser

Domänerna lästes medan de ändrades, så vilken fixpunkt utjämningen landade på berodde på i vilken ordning
villkoren råkade prövas - och den ordningen kom från processen. Funktionens egen beskrivning lovar motsatsen:
*"Where all of it still leaves a choice, nothing is assigned. That is the ordinary outcome and it is honest."*
Den gjorde det inte; den utsåg en vinnare i tysthet.

Åtta frön på samma fall:

    frö 0 -> VV1     frö 4 -> VV1
    frö 1 -> VV1     frö 5 -> VVC1
    frö 2 -> VV1     frö 6 -> VVC1
    frö 3 -> VVC1    frö 7 -> VVC1

**Varför determinismprovet aldrig såg det.** `run_determinism` läser om bladet med vägar och spann omkastade,
men alla fyra omläsningarna sker i SAMMA process, med samma hashfrö. Provet frågade "spelar ordningen på
bladets objekt någon roll?" och svarade ärligt nej. Det frågade aldrig om processen spelar roll.

**Vad det betyder för den här grinden.** gate79 och gate80 kördes var för sig, i var sin process, med var sitt
godtyckliga frö. Skillnaden mellan dem innehåller alltså både klippningen och det här bruset, och raden
`W-50-1-A0122` i bladtabellen ovan förklaras av bruset, inte av klippning. Hur stort bruset är mäts separat
(två körningar av den orättade motorn under frö 0 och frö 3) och redovisas i grind 81.

## Beslut

**ACCEPT.** Villkoret var att falskt ägande faller och täckningen i stort står kvar. Falskt ägande föll 4,27
mot 0,54 i täckning, precisionen steg, FULL steg med 12 och WRONG föll med 15, och rör för rör föll EXTRA_RUN
med 79. Mängdarens referens innehåller inte osynligt rör, och de meter som försvann var till 89 % stråk som
ritats förbi planens ram.

## Prov

826 gröna (808 tidigare + 8 klippgeometri + 6 mätetal + 4 projektprior). Kontamineringsskannern PASS.
