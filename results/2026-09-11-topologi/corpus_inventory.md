# Korpusinventering - ritningsmappen på Drive

Rot: `Drawings` (`1XXbhHA7D52kBEMVKOdvU2yil2txTwWr6`), inventerad rekursivt 2026-09-11 ur 27 sparade listningar. **1520 filer** (843 MB) i 15 klasser; **500 logiska blad** i parningen.

Tre regler styr vad materialet får användas till, och de står här innan siffrorna:

1. **Facit går aldrig in i motorn.** Facit-arbetsböcker, Bluebeam-XML och CVAT-filer används bara till validering, rotorsaksanalys och generaliseringstest, efter en fryst blind körning. Inventeringen läser ur facit *vilket blad den namnger* (kolumnerna Document/Sidetikett) - inte en meter.
2. **Exponering är ett faktum, inte ett val.** Ett blad som någon gång legat i `data/validation_*`, `data/validation_set3`, `data/cvat` eller `data/styles` har varit med i en körning och är DEVELOPMENT. HOLDOUT kan bara vara sådant som bevisligen aldrig öppnats.
3. **Klassificeringen är en hypotes ur namn och mapp tills filen öppnats.** Kolumnen `verified` i manifestet säger vad filen själv visade när den öppnades. Den kunde bara fyllas för filer som finns lokalt (697 av 1520); Drive-API:et ger ingen kontrollsumma, så en Drive-fil utan lokal kopia är matchad på namn och storlek, inte på innehåll.

## 1. Mappträdet

| Mapp | Filer |
|---|---:|
| Bluebeam - set 1 (lösa filer) | 93 |
| Bluebeam - set 1/clear | 23 |
| Bluebeam - set 2 (lösa filer) | 57 |
| Bluebeam - set 2/Without measurement | 19 |
| Bluebeam - set 3  (lösa filer) | 87 |
| Bluebeam - set 3 /Without measurement | 29 |
| CVAT (lösa filer) | 57 |
| CVAT/V-50-1-A0111_cvat_job3293971 | 1 |
| CVAT/V-50-1-A0112_cvat_job3293972 | 1 |
| CVAT/V-50-1-A0121_cvat_job3293973 | 1 |
| CVAT/V-50-1-A0123_cvat_job3293975 | 1 |
| CVAT/V-50-1-A0124_cvat_job3293976 | 1 |
| CVAT/V-50-1-A0211_cvat_job3293977 | 1 |
| CVAT/V-50-1-A0212_cvat_job3293978 | 1 |
| CVAT/V-50-1-A0221_cvat_job3293979 | 1 |
| CVAT/V-50-1-A0222_cvat_job3293980 | 1 |
| CVAT/V-50-1-A0223_cvat_job3293981 | 1 |
| CVAT/V-50-1-A0311_cvat_job3293982 | 1 |
| CVAT/V-50-1-A0312_cvat_job3293983 | 1 |
| CVAT/V-50-1-A0321_cvat_job3293984 | 1 |
| CVAT/V-50-1-A0322_cvat_job3293985 | 1 |
| CVAT/W-50-1-A-0011_cvat_job2947372 | 1 |
| CVAT/W-50-1-A-0013_cvat_job2945685 | 1 |
| CVAT/W-50-1-A-0014_cvat_job3045476 | 1 |
| CVAT/W-50-1-A-0021_cvat_job3045478 | 1 |
| CVAT/W-50-1-A-0022_cvat_job3045479 | 1 |
| CVAT/W-50-1-A-0023_cvat_job3045480 | 1 |
| CVAT/W-50-1-A-0024_cvat_job3045481 | 1 |
| CVAT/W-50-1-A-0031_cvat_job3045483 | 1 |
| CVAT/W-50-1-A-0032_cvat_job3045484 | 1 |
| CVAT/W-50-1-A-0033_cvat_job1641396 | 1 |
| CVAT/W-50-1-A-0033_cvat_job3005645 | 1 |
| CVAT/W-50-1-A-0034_cvat_job3045485 | 1 |
| CVAT/W-50-1-A-0111_cvat_job3045486 | 1 |
| CVAT/W-50-1-A-0112_cvat_job3045487 | 1 |
| CVAT/W-50-1-A-0113_cvat_job3045489 | 1 |
| CVAT/W-50-1-A-0114_cvat_job3045490 | 1 |
| CVAT/W-50-1-A-0123_cvat_job3045493 | 1 |
| CVAT/W-50-1-A-0133_cvat_job3045502 | 1 |
| CVAT/W-50-1-A-0134_cvat_job3144607 | 1 |
| Delivery Sheet.xlsx (lösa filer) | 1 |
| Other drawings (different format) (lösa filer) | 12 |
| Other drawings (different format)/Axis | 261 |
| Other drawings (different format)/Fyrens förskola | 25 |
| Other drawings (different format)/Fyrtornet 2 | 51 |
| Other drawings (different format)/Hamnmagasinet | 2 |
| Other drawings (different format)/Hyllie hybrid | 29 |
| Other drawings (different format)/Priorn | 15 |
| Other drawings (different format)/Ritningar | 14 |
| Other drawings (different format)/Rundstickan | 80 |
| Other drawings (different format)/SJÄLVSTYRELSEGÅRDEN | 12 |
| Other drawings (different format)/TOFTASKOLAN HUS B | 26 |
| Other drawings (different format)/Vinkelboda ombyggnad 2026 | 79 |
| Pipe studio - style-source-pdfs/01 - AutoCAD - pdfplot14-16 - Ghostscript 9.21 | 3 |
| Pipe studio - style-source-pdfs/02 - Sweco - AutoCAD MEP 2020 - pdfplot15 | 1 |
| Pipe studio - style-source-pdfs/03 - Sweco - AutoCAD 2023 - pdfplot16 - Hairline | 1 |
| Pipe studio - style-source-pdfs/04 - VVS Konsulterna - Revit - Bluebeam Brewery 5.0 | 1 |
| Pipe studio - style-source-pdfs/05 - Bengt Dahlgren - Ghostscript 9.21 | 2 |
| Pipe studio - style-source-pdfs/06 - PO Andersson - Ghostscript 9.21 | 1 |
| Pipe studio - style-source-pdfs/07 - Arildssons Rör - Ghostscript 9.21 | 1 |
| Pipe studio - style-source-pdfs/08 - PQR Malmö - Bluebeam Revu - Ghostscript 9.21 | 1 |
| Pipe studio - style-source-pdfs/09 - Rejlers - Bluebeam Revu - Ghostscript 9.21 | 1 |
| Pipe studio - style-source-pdfs/10 - Kjell Petersson - Bluebeam Revu - Ghostscript 9.21 | 1 |
| Pipe studio - style-source-pdfs/11 - Sweco - Bluebeam Brewery 5.0 - Uniform Stroke | 1 |
| Scales (lösa filer) | 8 |
| Style of drawings/1 | 42 |
| Style of drawings/10 | 1 |
| Style of drawings/11 | 1 |
| Style of drawings/12 | 29 |
| Style of drawings/13 | 50 |
| Style of drawings/2 | 5 |
| Style of drawings/3 | 5 |
| Style of drawings/4 | 6 |
| Style of drawings/5 | 11 |
| Style of drawings/6 | 5 |
| Style of drawings/7 | 261 |
| Style of drawings/8 | 4 |
| Style of drawings/9 | 8 |
| Test drawings (lösa filer) | 4 |
| Test drawings/DEMO | 5 |
| Test drawings/DEMO test | 5 |
| Video drawings (lösa filer) | 51 |

## 2. Klassificering

| Klass | Filer | Betydelse |
|---|---:|---|
| OTHER_FORMAT_PDF | 604 | PDF under *Other drawings (different format)*: elva projektmappar med andra konsulters ritsätt |
| STYLE_PDF | 428 | PDF under *Style of drawings 1-13*: stilprover, till stor del speglingar av andra mappar |
| CLEAN_ORIGINAL_CANDIDATE | 72 | PDF i `clear`, `Without measurement` eller med suffixet `- clean`: kandidat till ren original |
| MARKED_REFERENCE_CANDIDATE | 71 | PDF i roten av en Bluebeam-mapp: kandidat till mängdad referens |
| XLSX_FACIT | 71 | Bluebeams mängdlista exporterad till Excel: facit |
| BLUEBEAM_XML | 71 | Bluebeams markeringsexport: facit med koordinater |
| CVAT_SOURCE_PDF | 57 | PDF i CVAT-mappen: bladet som CVAT-jobbet ritats på |
| VIDEO_DRAWING_PDF | 51 | PDF under *Video drawings*: en handling utan seriebeteckning (1760268-1760318) |
| CVAT_REFERENCE | 33 | `annotations.xml` från ett CVAT-jobb: etiketterade former |
| PROCESSED_XLSX | 23 | `_processed.xlsx`: bearbetad facit - ett genererat mellanled, inte en källa |
| TEST_DRAWING | 14 | PDF under *Test drawings* (DEMO, DEMO test, lösa) |
| STYLE_SOURCE_PDF | 14 | PDF under *Pipe studio - style-source-pdfs*: elva exportkedjor (konsult, CAD, PDF-motor) |
| SCALE_STUDY_PDF | 8 | PDF under *Scales*: skalstocksstudier |
| OTHER | 2 | annat |
| OTHER_DOCUMENT | 1 | `Delivery Sheet.xlsx` |

## 3. Dubbletter: vilka mappar som är samma filer

Samma namn och samma storlek på flera ställen räknas som samma fil (hash bekräftar det där en lokal kopia finns). Samma namn med annan storlek är två versioner - typiskt en ren och en markerad.

| Identiska filer | Mappar |
|---:|---|
| 251 | Other drawings (different format)/Axis = Style of drawings/7 |
| 49 | Other drawings (different format)/Fyrtornet 2 = Style of drawings/13 = Video drawings |
| 26 | Bluebeam - set 3 /Without measurement = Other drawings (different format)/Rundstickan |
| 20 | Bluebeam - set 1/clear = CVAT = Style of drawings/1 |
| 19 | Bluebeam - set 2/Without measurement = CVAT = Style of drawings/1 |
| 14 | Other drawings (different format)/Priorn = Style of drawings/12 |
| 9 | Other drawings (different format)/Axis = Other drawings (different format)/Ritningar = Style of drawings/7 |
| 2 | Bluebeam - set 3 /Without measurement = Other drawings (different format)/Rundstickan = Style of drawings/2 |
| 2 | Other drawings (different format) = Other drawings (different format)/Ritningar = Style of drawings/8 |
| 1 | Bluebeam - set 1/clear = CVAT = Pipe studio - style-source-pdfs/01 - AutoCAD - pdfplot14-16 - Ghostscript 9.21 = Scales = Style of drawings/1 |
| 1 | Other drawings (different format) = Style of drawings/3 |
| 1 | Other drawings (different format) = Style of drawings/4 |

Dubblettstatus över alla filer: IDENTICAL_IN_2_PLACES 536, UNIQUE 406, IDENTICAL_IN_3_PLACES 183, 2_VERSIONS_BY_SIZE_x3 102, 2_VERSIONS_BY_SIZE 63, 3_VERSIONS_BY_SIZE 59, 2_VERSIONS_BY_SIZE_x2 40, 3_VERSIONS_BY_SIZE_x2 34, 33_VERSIONS_BY_SIZE 33, 3_VERSIONS_BY_SIZE_x3 21, IDENTICAL_IN_4_PLACES 16, 4_VERSIONS_BY_SIZE 15, 2_VERSIONS_BY_SIZE_x5 5, 3_VERSIONS_BY_SIZE_x5 5, 4_VERSIONS_BY_SIZE_x2 2.

## 4. Parningen per logiskt blad

71 blad har både en ren kandidat och minst en referens (facit-xlsx, Bluebeam-XML, markerad PDF eller CVAT). **Alla 71 är DEVELOPMENT.** 287 blad är oexponerade, och inget av dem har facit.

Kolumnerna i `corpus_pairing.csv`: DRAWING_ID, CLEAN_PDF, MARKED_PDF, FACIT_XLSX, BLUEBEAM_XML, CVAT, OTHER_REFERENCE, REVISION, EXPOSURE, STATUS, VALIDATION_SET, CONTENT_CHECK. REVISION är tom överallt: revisionen står i ritningshuvudet och kan bara läsas genom att öppna bladet; V-bladen bär sin revision i textlagret (läsbar), W-bladen som konturglyfer (kräver motorns glyfläsning).

| DRAWING_ID | Ren PDF | Markerad | Facit xlsx | BB-XML | CVAT | Innehållskontroll |
|---|---|---|---|---|---|---|
| V-50-1-A0111 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0112 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0121 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0122 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0123 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0124 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0211 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0212 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0221 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0222 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0223 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0311 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0312 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0321 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0322 | Bluebeam - set 3 /Without measurement | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0323 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0411 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0412 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0421 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0422 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0423 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0511 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0512 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0521 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0522 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-A0523 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-B0112 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-B0114 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| V-50-1-B0122 | Bluebeam - set 3 /Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort |
| W-50-1-A0011 | Bluebeam - set 1/W-50-1-A-0011 - clean.pdf | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: inget textlager att läsa ritningshuvudet ur (konturglyfer) |
| W-50-1-A0012 | Bluebeam - set 1/clear | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: inget textlager att läsa ritningshuvudet ur (konturglyfer) |
| W-50-1-A0013 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: inget textlager att läsa ritningshuvudet ur (konturglyfer) |
| W-50-1-A0014 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_VERIFIED_BY_CONTENT: inget textlager att läsa ritningshuvudet ur (konturglyfer) |
| W-50-1-A0021 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0022 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0023 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0024 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0031 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0032 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0033 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0034 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0111 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0112 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0113 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0114 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0121 | Bluebeam - set 1/clear | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0122 | Bluebeam - set 1/clear | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0123 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0124 | Bluebeam - set 1/clear | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0131 | Bluebeam - set 1/clear | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0132 | Bluebeam - set 1/clear | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0133 | Bluebeam - set 1/clear | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0134 | Bluebeam - set 2/Without measurement | ja | ja | ja | ja | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0211 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0213 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0214 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0221 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0222 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0223 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0224 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0231 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0232 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0233 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0234 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0311 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0313 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0314 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0331 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0332 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_VERIFIED_BY_CONTENT: inget textlager att läsa ritningshuvudet ur (konturglyfer) |
| W-50-1-A0333 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |
| W-50-1-A0334 | Bluebeam - set 2/Without measurement | ja | ja | ja | - | PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt |

Innehållskontrollens utfall: **37** × PAIR_PARTLY_VERIFIED: inget textlager att läsa ritningshuvudet ur (konturglyfer); facit ej lokalt; **29** × PAIR_VERIFIED_BY_CONTENT: ren kandidat bär annoteringar som motorn bevisligen tar bort; **5** × PAIR_VERIFIED_BY_CONTENT: inget textlager att läsa ritningshuvudet ur (konturglyfer).

## 5. Vad som visade sig när filerna öppnades

* **231 lokala PDF-filer bär annoteringar**, och av dem är 45 "rena" kandidater. `Bluebeam - set 3 /Without measurement` är inte utan påskrift: varje V-blad där bär 12-53 `Square`-annoteringar. Bluebeam-mappens rotfiler bär 14-315 `PolyLine`-annoteringar - det är själva mängdningen.
* **`data/validation_set3/<blad>/clean.pdf` är Drive-mappens *markerade* fil**, inte `Without measurement`-filen (V-50-1-A0111: 529 119 byte = `Bluebeam - set 3 /V-50-1-A0111.pdf`; `Without measurement` är 318 941 byte och ligger lokalt som `data/styles/test/V-50-1-A0111.pdf`). Alla tidigare grindkörningar på set 3 har alltså läst den markerade filen.
* **Motorn tar bort annoteringsbläcket innan bladet läses**, och det är kontrollerat på varje annoterad lokal fil: 231 filer ger exakt samma vägar, segment och bläcklängd med och utan annoteringar; 0 filer där motorn läser annoteringsbläck. Grindresultaten mäter därför ritningen under påskriften, inte påskriften - men protokollet ska ändå köra på `Without measurement`-filen, och den finns lokalt för alla 29 V-blad.
* **W-bladen (Bluebeam set 1-2, CVAT) är rena på riktigt**: 0 annoteringar i 42 av 42 CVAT-PDF:er, och `clear`/`Without measurement`-filerna är bytevis samma filer som CVAT-PDF:erna. Undantag: `Bluebeam - set 1/clear/W-50-1-A-0012.pdf` bär 7 annoteringar (lokalt `validation_C/marked_v1.pdf`), och `clear/W-50-1-A-0113.pdf` saknar lokal kopia.
* **W-bladen har inget textlager för ritningshuvudet** (5-20 ord ur revisionstabellen; allt annat är konturglyfer). Ritningsnumret kan inte bekräftas ur textlagret; parningen vilar där på facit-arbetsbokens Document-kolumn (bekräftad för de 4 lokala) och på namnet (de 37 som saknar lokal facit).
* **Facit lokalt**: 34 av 71 xlsx (29 V + A/C/D/E), 0 av 71 Bluebeam-XML. De 37 W-bladen utanför A/C/D/E har aldrig poängsatts; deras facit ligger bara på Drive.
* **CVAT**: 33 jobb, alla med bildnamn som bekräftar bladet; men bara 0-2 former per fil - exporterna bär etikettlistan (D1-E4-110, FJV1-S6-50/W, KV1-E13-75 ...) och nästan ingen geometri. Som referens för utsträckning är de i praktiken tomma.
* **4 PDF:er i TOFTASKOLAN HUS B är rasterskanningar** (`RIVNING`, `DEM`): motorn avvisar dem med UnsupportedInputError, vilket är rätt svar.

## 6. Exponering och holdout

* DEVELOPMENT: 213 blad (alla med lokal kopia i `data/`).
* UNEXPOSED_SO_FAR: 287 blad, fördelade: Other drawings (different format)/Axis 247, Other drawings (different format)/Fyrens förskola 21, Style of drawings/12 13, (rot) 6.
* **Inget oexponerat blad har facit.** TRUE HOLDOUT är därför blockerat tills facit produceras för oexponerat material. Kandidater, i ordning efter hur olika de är utvecklingsmaterialet: *Fyrens förskola* (21 blad, egen konsult), *Style of drawings/12* (13 blad som inte speglas lokalt), *Vinkelboda ombyggnad 2026* (79 blad utan seriebeteckning) och *Hyllie hybrid* (28). *Axis* (247) är samma exportkedja som Rundstickan/set 3 och duger som holdout bara för generalisering inom stil, inte mellan stilar.
* Innan ett sådant blad körs ska motorn frysas och hashas (`hashmanifest-baseline.json`), bladet hashas, körningen göras blind, och facit läsas först därefter. Den ordningen är inte förhandlingsbar.

## 7. Filer

* `corpus_manifest.json` / `.csv` - en rad per Drive-post: file_id, path, filename, extension, mime, size, modified, parent_folders, logical_project, drawing_number, revision, classification, validation_role, local_copy, sha256, hash_source, verified, duplicate_status.
* `corpus_pairing.csv` - en rad per logiskt blad (se §4).
* `corpus_verification.json` - vad varje lokal fil visade när den öppnades: sidor, annoteringar per typ, textlager, om motorn läser samma bläck utan annoteringarna, vilket blad facit/CVAT namnger.
* `local-corpus-hashes.json` - sha256 för alla 452 lokala filer; `drive-listings/` - råa Drive-svar.
* Byggs om med `python3 engine/tools/corpus_manifest.py && python3 engine/tools/corpus_verify.py && python3 engine/tools/corpus_inventory.py`.
