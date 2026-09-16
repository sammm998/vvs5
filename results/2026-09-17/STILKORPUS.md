# PipeStudios stilkällor: vad de är och vad de duger till

Fjorton ritningar från elva producentkedjor, var mapp namngiven med CAD-program och PDF-skrivare. Materialet
ligger i git-ignorerade `data/styles/pipestudio/` och innehåller **inga facitmängder** - det är stilkällor, inte
mängdunderlag. Det avgör vad de kan och inte kan svara på.

## Vad filerna är

| mapp | fil | vägar | klipp | ord | typsnitt | producer / creator |
|---|---|---:|---:|---:|---:|---|
| 01 AutoCAD pdfplot14-16 | 10.pdf | 13 392 | 3 | 411 | 3 | Ghostscript 9.21 / Bluebeam Revu |
| 01 | V-50-1-A0101.pdf | 19 894 | **353** | 23 | 4 | pdfplot14.hdi / AutoCAD 2018 |
| 01 | W-50-1-A-0131.pdf | 36 718 | 5 | 5 | 1 | pdfplot16.hdi / AutoCAD 2023 |
| 02 Sweco AutoCAD MEP 2020 | V-50-1-A0122.pdf | 24 050 | 37 | 643 | 2 | pdfplot15.hdi / AutoCAD MEP 2020 |
| 03 Sweco AutoCAD 2023 Hairline | R9UHA10-CLB001-002.pdf | 18 901 | 79 | 108 | 3 | pdfplot16.hdi / AutoCAD 2023 |
| 04 VVS Konsulterna Revit | V50-1-0842 Plan B2 Del 42 | 15 369 | 146 | 740 | 4 | Bluebeam Brewery 5.0 / Stapler 2016 |
| 05 Bengt Dahlgren | 1760279_1.pdf | 17 189 | 2 | 659 | 4 | Ghostscript 9.21 |
| 05 | Löpöglan 2.pdf | 27 366 | 28 | 788 | 2 | macOS Quartz |
| 06 PO Andersson | Badskon 1.pdf | 13 783 | 7 | 1 878 | 1 | macOS Quartz |
| 07 Arildssons Rör | Bläckhornet.pdf | **75 164** | 3 | 1 668 | 3 | macOS Quartz |
| 08 PQR Malmö Bluebeam | 6.pdf | 24 599 | **4 513** | 343 | 4 | Ghostscript 9.21 / Bluebeam Revu |
| 09 Rejlers Bluebeam | 2.pdf | 8 554 | 3 | 660 | 4 | Ghostscript 9.21 / Bluebeam Revu |
| 10 Kjell Petersson Bluebeam | 10.pdf | 11 976 | 4 | 553 | 4 | Ghostscript 9.21 / Bluebeam Revu |
| 11 Sweco Bluebeam Uniform Stroke | R1502.pdf | 25 673 | 5 | **0** | **0** | Bluebeam Brewery 5.0 / Stapler 21 |

## Tre saker materialet säger direkt

**1. Tio av fjorton ritningar har inga lagernamn alls.** Bara 01 (två av tre), 02 och 03 bär CAD-lager. Motorns
hela pennbegrepp är `lager|s|bredd|färg` (`pen_key`), så på en lagerlös export krymper familjen till bredd och
färg - och antalet pennor är litet, mellan 3 och 20. Det är inte en kantfråga: det är majoriteten av det här
materialet, från åtta olika företag.

**2. `11 - Sweco - Uniform Stroke / R1502.pdf` är det urartade fallet, och det är verkligt.** 25 673 ritade
vägar, **noll ord, noll typsnitt, noll lagernamn**, och i praktiken **en enda penna**: 13 974 streck i bredd
0,36 svart, 20 i bredd 0,12, resten fyllda former utan penna. Mappen heter "Uniform Stroke" och det är precis
vad exporten gjort - den har jämnat bort pennsignalen. På det bladet kan motorn inte skilja system åt på penna
över huvud taget; allt måste komma ur etiketterna, geometrin och topologin. Det är takets höjd för dagens
arkitektur, mätt på en riktig fil.

**3. Klippning finns hos flera producenter, och PQR Malmö är en storm.** 4 513 klippbanor på ett blad, mot 353
på den näst värsta. Den klippmedvetna extraktionen (grind 80) har alltså material långt bortom korpusens
värsta fall att prövas mot.

Två randanmärkningar som är lätta att missta sig på: **ingen** av filerna använder PDF:ens streckmönster
(`dashes` är `[] 0` överallt) - streckade linjer ritas som korta separata segment, vilket är vad motorn redan
antar. Och texten finns i två helt skilda regimer: riktig text (Badskon 1 878 ord, Bläckhornet 1 668) mot
sprängd geometri (W-50-1-A-0131 har 5 ord, R1502 noll).

## Vad de kan svara på, och vad de inte kan

Utan facit går det **inte** att säga om metrarna blir rätt. Det som går att mäta är:

* **Läser motorn bladet alls** - skala funnen, beteckningar lästa, hänvisningar fästa, rör mätta, ingen krasch,
  inom tidsbudget. Öppen värld, elva producentkedjor.
* **Lagerlösheten**, mot den redan kända luckan (#60): åtta firmors riktiga lagerlösa exporter.
* **Klippningen** över producenter, som fortsättning på grind 80.

Ett fall bär däremot **facit**: `V-50-1-A0122` finns i korpusen med referensmängder, och stilkopian är en
**annan fil** (annan exportväg: pdfplot15 / AutoCAD MEP 2020). Samma ritning, två producenter, ett facit - det
är en riktig generaliseringsmätning med kontroll, inte en gissning. `W-50-1-A-0131` är bytesidentisk med
korpusens kopia och tillför därför ingenting. `V-50-1-A0101` är nytt och saknar facit.

## Ordning

Materialet är stilkällor i git-ignorerad `data/styles/pipestudio/`. Ingen produktionskod läser det, inga
koordinater eller filnamn därifrån hamnar i `vvs_engine/`, och kontamineringsskannern ska förbli PASS.
