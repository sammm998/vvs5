# Tecken som läsaren inte kunde tyda

**Datum:** 2026-09-15
**Rör:** `engine/vvs_engine/pdf/glyphtext.py` (ny), `engine/vvs_engine/pdf/extract.py`, `backend/app/desk.py`
**Prov:** `engine/tests/test_a_font_without_a_character_table_is_read_anyway.py` (7)
**Kontamination:** PASS (66 filer, inga fynd)

## Vad som var fel

Ett PDF-typsnitt som bäddats in med `Identity-H` pekar ut sina tecken med glyfnummer. Vilket tecken ett
glyfnummer betyder står i typsnittets ToUnicode-tabell. Saknas den tabellen, eller är den utskriven men
ofullständig, kan läsaren inte säga vad som står. På skärmen står det rätt - glyferna ritas ändå - men texten
ur filen kommer ut som ersättningstecken.

På `V-56-1-A0101` kom hela fördelartabellens huvud ut så: `/lQJG` för `Längd(m)`, `,QM.YlUGH` för
`Inj.värde`. På åtta blad ur SJÄLVSTYRELSEGÅRDEN gällde det två enskilda glyfer, och just de två satt i ordet
`OBS:`, som blev `0BS` och ett styrtecken.

## Rotorsak

Läsaren säger själv vilka tecken den inte kunde tyda: `get_texttrace()` rapporterar dem som **U+FFFD**.
`get_text("text")` gör i stället en tyst gissning och skriver ut glyfnumret som om det vore ett tecken, vilket
är varför felet är svårt att se - `/lQJG` ser ut som text, inte som ett fel.

Vad glyfen föreställer står i det inbäddade typsnittet. Tabellen byggs baklänges ur det: för varje tecken,
vilken glyf typsnittet ritar det med. Då går även å, ä och ö tillbaka.

## Rättningen

Bara tecken som kom ut som U+FFFD slås upp. Ett tecken som läsaren kunde tyda rörs aldrig, oavsett vilket
typsnitt det står i.

Typsnittet ett otytt tecken kom ur pekas ut av namnet, och namnet håller dåligt:

* **De två vägarna in i filen stavar olika.** Sidans typsnittslista säger `Nimbus Sans Regular` där textraden
  säger `NimbusSans-Regular`, och ett utsnitt bär ett slumpat förled som `ABCDEF+`. Namnen jämförs därför
  skalade: förledet bort, bara bokstäver och siffror kvar.
* **Namnet är inte unikt.** Ett blad kan bära två typsnitt som båda heter `ArialMT`. Då frågas alla som bär
  namnet, och svaret gäller bara om de är överens - säger en tabell `m` och en annan `µ` om samma glyf, går
  det inte att veta och tecknet står kvar otytt.
* **Passar inget namn** men sidan bär bara ett enda inbäddat typsnitt, är det det tecknet kom ur.

Ett typsnitt packas upp först när ett otytt tecken faktiskt kommit ur det. Blad utan sådana tecken - de allra
flesta - betalar bara för en genomgång av textraderna.

## Tre försök som inte höll

1. **Läsbarhetsvakt.** Avkodad text jämfördes mot rå och den som såg mest läsbar ut behölls. `/lQJG` och
   `Längd` fick samma poäng när skiljetecken räknades; räknades bara bokstäver och siffror förvandlades
   `KV1-X31-25` till `hs1JuP1JOR`. Att väga läsbarhet mot läsbarhet går inte att få rätt.
2. **Namnet ensamt.** Två `ArialMT` på samma sida, ett trasigt och ett helt: tabellen från det trasiga lades
   på det hela och `Krets` blev `Ircrs`. Rättat av U+FFFD-villkoret, som aldrig rör ett tytt tecken.
3. **"ToUnicode saknas".** Byggde tabell bara när tabellen fattades helt. Missade de åtta bladen där tabellen
   fanns men två glyfer inte stod i den. Villkoret är vad läsningen gav, inte vad typsnittet lovar.

Det fjärde felet hittades inte i korpusen utan i provet: ett syntetiskt blad där listan sade
`Nimbus Sans Regular` och raden `NimbusSans-Regular`. Namnen möttes inte, och ingenting rättades.

## Omfattning - och en rättelse

Jag rapporterade tidigare i samtalet att felet gällde **10,1 % av alla ord** över 263 korpusblad. Den siffran
var fel. Mätt om:

| | |
|---|---|
| Filer genomsökta | 318 |
| Ord totalt | 146 687 |
| Ord som ser otydda ut | **26 (0,02 %)** |
| Blad med otydda tecken | **10** |
| Blad som rättningen når | **10 av 10** |

Det tidigare måttet räknade något annat - ord som innehöll tecken utanför det vanliga - och blandade ihop
"ser konstigt ut" med "gick inte att tyda".

## Vad rättningen är värd

**Inga meter.** Inget av de 26 orden är en rörbeteckning; de sitter i fördelartabeller, namnrutor och
anteckningar. Mätningen ändras inte på något blad.

Det den ger är läsbar text där en människa och agenten faktiskt läser: `titta_i_filen` visar namnrutan som
den står, fördelartabellens huvud går att läsa, och `OBS:` är ett ord i stället för ett styrtecken.

## Kostnad

Uppmätt påslag på `extract_document` över sex blad: **-1,2 % till 8,2 %**, medel ~3,5 %. Mätt mot enbart
`rawdict` ser påslaget ut som 77 %, men `rawdict` är en liten del av en läsning - det måttet är missvisande
och togs inte som grund.

## Vad som bevisar det

`test_a_font_without_a_character_table_is_read_anyway.py`, 7 prov:

* text ur ett typsnitt utan teckentabell kommer tillbaka, med svenska tecken och parenteser
* ett helt typsnitt med samma namn på samma sida rörs inte (försök 2)
* ett blad utan trasiga typsnitt ändras inte
* namnet får stavas olika på vägen in (det fjärde felet)
* två typsnitt som heter lika och ritar olika ger inget svar alls - tecknet står hellre otytt än fel
* ett blad utan otydda tecken packar aldrig upp ett typsnitt
* rättningen sitter i utvinningen, så motorn läser samma text som den som tittar i filen
