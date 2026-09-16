# Etapperna i genomförandespecifikationen: vad som är byggt, vad som är mätt, vad som inte går här

Specen delar arbetet i fyra etapper. Det här dokumentet går igenom dem punkt för punkt och säger för varje
sak **var den står i koden**, **vad som mätte den**, eller **varför den inte går att bygga med det material
som finns här**. Det tredje är lika viktigt som de två första: en punkt som inte kan prövas får inte redovisas
som stödd.

Två saker gäller genomgående.

**En etapp är inte klar för att koden finns.** Specens egen definition (avsnitt N) kräver implementation,
gröna prov, nya beteendeprov och **sparade verkliga före/efter-resultat**. En ändring utan grind är därför
inte redovisad som klar här, hur färdig koden än ser ut.

**Där underlaget saknas står det.** Två saker går inte att bygga i den här miljön: etikettmodellen
(`model_dynamic.onnx` finns inte på maskinen) och stil 3 mot verkliga blad (EON-blad med jämförelsematerial
finns inte). Båda står som ogjorda, inte som stödda.

---

## Etapp 0 — lås baslinjen

| punkt | var | tillstånd |
|---|---|---|
| inventera pipeline och versionsberoenden | `docs/SYSTEMET.md`, `docs/KARTA.md`, `SYSTEM_AUDIT.md` | **byggd** |
| manifest före analys (kod, konfiguration, PDF-SHA, sidnummer, flaggor) | `engine/tools/freeze.py`, `results/hashmanifest.json` | **byggd**, och körs före varje grind |
| kör A/B/C som utvecklingsbaslinje | `engine/tools/gate_run.py`, 59 blad | **byggd** |
| syntetiska fall: klippning, rotation, överlappande system, hårfin penna, korsning, T-gren, ledare, reducering, tvilling, flera skalregioner | `engine/tests/` | **byggd**, alla tio |
| oberoende testmanifest per projekt/dokument | `engine/vvs_engine/release.py: independent_sources()` | **byggd** |

Provmatrisens tre saknade fall byggdes i `test_three_sheets_the_test_matrix_was_missing.py`: hårfin penna
(rå `0 w` i innehållsströmmen, eftersom PyMuPDF normaliserar `finish(width=0)` till 1,0), två skalregioner,
överlappande system.

Till dem kom de **metamorfiska** proven som avsnitt M frågar efter
(`test_the_same_drawing_said_in_another_way.py`): en dragen linje skriven i två eller tre kollineära bitar,
ritad åt andra hållet, med etiketterna i omvänd ordning. Alla ger samma mängd på millimetern. Ett av proven
säger också var gränsen går: att dela en **streckad** linje är inte samma ritning - strecken börjar om vid
delningen och bläcket blir verkligen ett annat, mätt till 52 mm på provbladet.

**Ogjort:** raster-DPI som metamorfisk omskrivning. Motorn läser vektorgeometri och vägrar raster, så
omskrivningen har inget att ändra.

---

## Etapp 1 — rätt geometri och rätt mätning

| punkt | var | grind |
|---|---|---|
| synlighet (klippning) | `pdf/extract.py`, klippbindningen bevisad mot renderaren | grind 80 ACCEPT: falskt ägande 15,22 → 10,95 |
| koordinater: rotation, transform, CropBox | `pdf/extract.py:_read_page` (`page.rotation_matrix`) | elva av bladen är vridna 270° och läses rätt |
| koordinater: `/UserUnit` | `pdf/extract.py:_user_unit`, `measure/scale.py:discover_scale` | grind 86 - inert på korpusen, provad syntetiskt |
| dubbletter | `pipes/representation.py:collect_prims`, `duplicate_overlaps` | mätt: redovisas, dras inte av, och skälet står i koden |
| atomära intervall | `pipes/representation.py:interval_id` | grind 86 |
| transaktionell ägartilldelning | `measure/commit.py` | grind 86 |
| mängdjournal | `measure/journal.py` | grind 85 ACCEPT, exakt nolla |
| korrekta mätetal | `engine/tools/facit_metrics.py` | textmått skilt från längdmått, `N/A` i stället för 100 % |

**Det atomära intervallet** var ett verkligt fel i mitt eget instrument, inte i motorn. `pid#seg_index` är
namnet på källsträckan; när ett T delas mitt på en linje behåller båda bitarna det namnet, och villkoret
"ett intervall, en ägare" larmade på nio ställen där ingenting var fel. Bitarna ägde skilda, angränsande
halvor som summerade exakt till källsträckans längd. `interval_id` skiljer dem på startpunkten.

**Den transaktionella tilldelningen** är specens steg 7: hela tilldelningen ses på en gång, och en bit som två
rör båda gör anspråk på räknas åt **ingen** av dem - den blir tvetydig med sina alternativ och sitt skäl. På
dagens korpus slår spärren aldrig till, vilket är avsikten; den finns för ritningen som ännu inte lästs.

**Steg 8 - "beräkna mängd från den committade intervalljournalen" - är byggt annorlunda än ordalydelsen, och
det är avsiktligt.** Mängdraden räknas fortfarande av `aggregate` och journalen kontrollerar att de två
stämmer på fem millimeter. Det är strängare än att räkna raden ur journalen: en enda källa kan inte vara
oense med sig själv, så villkoret vore vakuöst.

**Ogjort med mätt skäl:** adaptiv bezierapproximation med angiven felgräns (avsnitt E). Nuvarande
`flatten_bezier` delar varje kurva i åtta raka bitar. Mätt på tre W-blad underskattar det kurvlängden med
0,12 % av kurvlängden, vilket är **0,013 % av allt ritat bläck** - i storleksordningen en meter på hela
korpusens 10 157 m. Det är inte noll och står därför kvar som en punkt, men fler punkter per kurva flyttar
grafnoder och kräver en egen grind; att bunta den med tilldelningen hade gjort båda omöjliga att avgöra.

---

## Etapp 2 — stil 2 och stil 3

| punkt | var | tillstånd |
|---|---|---|
| ritningsprofil | `profile/style_profile.py` | **byggd och mätt, verkar inte ännu** |
| pappersfaktor | `style_profile.paper_factor`, `tolerance_scale()` | **byggd**, begränsad till [0,35, 2,5], och den rör aldrig meter per punkt |
| native-text-först | `semantics/annotation.py:_reading_quality` | **byggd**: filens egen text slår återskapade glyfer |
| lokal familjekalibrering | `pipes/representation.py:describe_family` | **delvis**: streck och gap mäts per familj ur ritningen |
| streckmönster | `describe_family`, `build_graph` | **delvis**: mönstret återskapas och används för att brygga, men delar inte familjen |
| kandidatbaserad anknytning | `semantics/attachment.py` | **byggd** |
| explicit osäkerhet | AMBIGUOUS genom hela kedjan | **byggd** |
| hårfin penna | `pipes/ink.py` | **byggd som bläckkontrakt**, men inget eget hårfin-läge |
| stil 2 på riktiga medföljande blad | `results/2026-09-17/STILKORPUS.md` | **byggd**: 14 av 14 lästa, 12 med verifierad skala, 2 ärliga skalvägringar |
| stil 3 på verkliga EON-blad | — | **går inte här**: blad med jämförelsematerial finns inte |

Profilen mäter sidstorlek och pappersformat, sidans egen enhet, vridning, textläge (native / glyfer / blandat
/ okänt), texthöjden i de rader som blev beteckningar, breddfördelning, färger, lager, hårfinhetsandel,
kurvandel, andel stängda vägar, och om bredder alls särskiljer familjer.

Tre gränser står i koden och i proven, inte bara i ett beslut:

* **pappersfaktorn justerar toleranser och säger ingenting om meter per punkt.** Skalan kommer ur bladets
  skaltext eller skalstock och ingen annanstans ifrån;
* **en texthöjd som ger en orimlig faktor ger ingen faktor alls**, inte en avhuggen;
* **ett litet pappersformat ensamt är inget skäl att skala.** En ritning som ritats för A3 från början har
  text i A3-storlek och faktorn 1; att anta att varje A3 är en förminskad A1 vore en gissning.

Att låta faktorn verka ändrar varje läsning på varje blad och är sitt eget steg med sin egen grind.

---

## Etapp 3 — kontrollerat lärande och valfri AI

| punkt | var | tillstånd |
|---|---|---|
| rättelsen som eget, återställbart lager | `backend/app/db.py:Correction`, `corrections.py` | **byggd** |
| vad en rättelse får lära | `learning.py` | **byggd**: bara avgöra ett fall motorn själv kallat AMBIGUOUS, på exakt match i sex delar |
| en rättad dimension ändrar ingen global tolerans | `learning.py` (rättelser rör aldrig regler) | **byggd strukturellt** |
| releaseidentitet (kod, regler, profil, renderare, textläsare, flaggor, dokument, modell) | `release.py:ReleaseIdentity`, skriven i `summary.json` | **byggd** |
| cachen invalideras av varje del | `ReleaseIdentity.covers()` | **byggd**: bara identisk nyckel får återanvändas |
| versionsstyrd aktivering och rollback | `release.py:RuleChange` | **byggd** |
| stilundantag med mätt konflikt | `RuleChange.exception_is_warranted` | **byggd** |
| global regression före aktivering | `release.py:Regression` | **byggd som förfarande**, kopplad till grindkörningen för hand |
| begränsat AI-kontrakt | `agent/`, andraläsaren | **byggd**: bara bland kandidater ritningen själv erbjuder |
| valfri etikettmodell (ONNX) | — | **går inte här**: `model_dynamic.onnx` finns inte på maskinen |
| projektpriorn räknar källor, inte körningar | `backend/app/jobs.py` | **byggd**, grind 82 |

`RuleChange` håller förfarandet, inte omdömet. Den avgör inte om en regressionskörning är bra nog - den vägrar
att kalla något aktiverat som inte gått igenom stegen, och den kan alltid säga vilken version som gällde och
vilka tal en återgång ska sätta. Det tillståndet gör omöjligt behöver ingen disciplin upprätthålla:

* en ändring på för tunt underlag avslås - **två omkörningar av samma PDF är ett dokument, inte två**;
* en generell regel som gör en annan stil sämre avslås: då är den inte generell;
* ett stilundantag kräver **både** att den gemensamma regeln mätt skadar en annan stil **och** att undantaget
  hjälper den avsedda - annars blir varje stil sin egen regel och det finns ingen gemensam läsning kvar;
* en oprövad ändring kan inte aktiveras; en aktiverad ändring lämnar ifrån sig talen att gå tillbaka till.

---

## Vad som återstår, med skäl

1. **Pappersfaktorn får verka** på toleranserna. Egen grind. Störst enskild kvarvarande post i etapp 2.
2. **Adaptiv bezierapproximation.** Mätt effekt 0,013 % av ritat bläck. Egen grind.
3. **Hårfin-läge och streckmönster som familjedelare.** Kräver stil 3-blad för att gå att avgöra.
4. **Regressionen kopplad till `RuleChange` i kod.** I dag körs grinden för hand och utfallet förs in.
5. **Etikettmodellen och stil 3 mot verkliga blad.** Blockerade av material som inte finns här.

Och den öppna listan av enskilda läsningsfel - punkterna om bunten, den dolda pennan, öarna och de tvetydiga
fästena - som är mätningsarbete på riktiga blad snarare än etapparbete.
