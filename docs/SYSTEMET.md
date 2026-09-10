# Så fungerar systemet

Det här är dokumentet man läser för att förstå vad VVS Mängdning gör, hur det gör det, vilka AI-modeller som
används och exakt var, och vad det aldrig gör. Det är skrivet efter koden, inte före den: varje påstående går
att slå upp i den fil som nämns.

Kompletterande dokument: `ARCHITECTURE.md` (läsvägen steg för steg), `ANALYSARKITEKTUR.md` (vad som bär och
brister, med mätningar), `LATHUND.md` (mängdningsstandarden och vad av den som är genomfört), `LIMITATIONS.md`
(kända begränsningar), `RORTYPER.md`, `FLERVAGSANALYS.md`.

---

## 1. Principen

En mängd finns bara där ritningen själv pekar.

Systemet läser en ritnings egna vektorer - linjerna CAD-programmet skrev in i PDF:en - och bygger identitet
bara där tre saker möts: en beteckning bladet skriver, en ritad hänvisningslinje från den, och den graf
geometrin bildar. **Aldrig närhet.** Ett rör som ligger nära en etikett men som ingen linje pekar på får inget
namn. Det redovisas som *onämnt* - med sina meter - i stället för att gissas.

Därför är `AMBIGUOUS` ett giltigt svar. Två etiketter som båda kan äga en sträcka ger en tvetydig sträcka, inte
en gissning. Fel säkerhet är värre än ett saknat svar, för ett saknat svar syns och ett felaktigt gör det inte.

Allt upptäcks per ritning. Vilken penna som ritar rör, hur beteckningarna är byggda, vilken skala bladet har,
vilka lager som är text - ingenting av det är inställt i förväg. Två kontor ritar olika, och systemet läser
varje blad på bladets egna villkor.

---

## 2. Vad som händer med en ritning

Läsvägen, i den ordning den körs (`engine/vvs_engine/pipeline.py`):

| Steg | Vad | Var |
|---|---|---|
| 1 | **Extraktion.** PDF:ens vektorobjekt läses råa: linjer, kurvor (plattade), transformationer, XObjects, lager (OCG), sökbar text. Annotationer - någons påskrift ovanpå ritningen, till exempel en Bluebeam-mängdning - läggs åt sidan och redovisas för sig; de är aldrig det ritaren ritade. | `pdf/extract.py` |
| 2 | **Text.** Sökbar text läses som text. CAD-text som exporterats som streck (SHX-typsnitt) sätts ihop till tecken av streckens form, mot generiska referensalfabet. Ett tecken som inte går att läsa blir `?` - det repareras aldrig ur ett förväntat ord. | `text/` |
| 3 | **Beteckningar.** Textrader blir block, block blir etiketter. Grammatiken - hur det här kontoret bygger sina koder (system, material, dimension, kvalificerare) - upptäcks ur bladets egna etiketter och dess beteckningslista. | `semantics/annotation.py`, `semantics/grammar.py`, `semantics/legend.py` |
| 4 | **Hänvisningslinjer.** Från varje etiketts kant följs de ritade linjerna ut i bladet: raka, böjda, delade. En etikett utan linje pekar inte på något. | `semantics/leaders.py` |
| 5 | **Vilka pennor ritar rör.** Linjernas ändar röstar på de familjer (lager + penna) de rör vid. En familj blir rörgeometri bara om den är kedjelik och har stöd - lagernamnet bär systemets kod, markeringsstreck, eller tillräckligt många etiketter. Läsningen körs två gånger: först obegränsat, sedan med de pennor som visade sig vara *skrivpennor* undantagna. Bladets egna etiketter avgör vilken läsning som står. | `pipeline.py` |
| 6 | **Kontakt.** Var linjen möter röret: direkt, via ett markeringsstreck, via en symbol (stigare, brunn), via en samlingslinje - ett kort streck på skrivpennan som samlar flera etiketter ned till ett rör. | `semantics/attachment.py` |
| 7 | **Topologi.** Rörgeometrin blir en graf: mikroglapp överbryggas, T-korsningar delas, och en korsning är inte en anslutning - en linje som passerar går in på ena sidan av noden och ut på den andra. | `pipes/representation.py` |
| 8 | **Ägande.** Varje kedja i grafen får en identitet från de etiketter som når den, eller står som tvetydig eller onämnd. Dimensionsbyten sätts bara vid ritade markeringsstreck. En stump kortare än kontakttoleransen bär aldrig ett namn vidare. | `pipes/ownership.py` |
| 9 | **Skala och mått.** Skalan läses ur skaltexten och verifieras mot den ritade skalstocken; skiljer de sig är det en konflikt och inte ett medelvärde. Horisontella meter mäts längs geometrin. Vertikala meter finns bara med uttryckligt stöd - en våningshöjd användaren anger, eller höjdangivelser på bladet. | `measure/` |
| 10 | **Avstämning och artefakter.** Allt bladet ritade summeras: mätt, tvetydigt, påpekat men onämnt, onämnt, bortvalt. Summan ska stämma med det ritade, och avvikelsen redovisas i stället för att justeras bort. Allt skrivs som filer så att varje meter går att spåra bakåt (`why`). | `reconcile.py`, `output/` |

Efter mätningen kommer **granskningen** (`review/`): agenter som frågar om resultatet är trovärdigt - är det
ritade röret redovisat, finns bladets alla beteckningar i mängdtabellen, är längder och dimensioner fysiskt
rimliga, hänger nätet ihop, håller skalan. De ändrar ingenting; en granskning som kunde ändra resultatet skulle
dölja den oenighet den finns för att visa. En **domare** (`review/judge.py`) går igenom fynden och säger vad som
ska hända - utan modell, ur artefakterna, så samma läsning dömd två gånger ger samma domar.

**Determinism.** Samma blad läst två gånger ger samma signatur, och ett blad läst mellan två andra påverkas inte
av dem. Det prövas (`determinism.py`) och det gäller så länge ingen andra läsare kopplas in (se §3).

**Kontamineringsbrandväggen.** Produktionskoden får inte läsa facit eller referensritningar, och innehåller inga
ritningsspecifika literaler. Det skannas (`contamination.py`) och står som `PASS` i varje läsnings sammanfattning.

---

### 2b. Vad bladet förklarar i ord

En ritning kan säga en sak om rör utan att skriva den vid varje rör. Ett helt projekt skriver på varje blad
*"Kopplingsledningar från fördelare till apparat enligt tabell om inget annat anges"* och en tabell med
beteckningsstammen per system (VV01-X31, KV01-X31) och dimensionen per apparat (16), och drar sedan nittio korta
rör från fördelarskåpen till blandare, tvättställ och toaletter utan en enda etikett. Läsningen, som bara följer
hänvisningslinjer, ägde inget av det - fjortonhundra meter på trettiotre blad.

`semantics/declarations.py` läser den regeln av form och av ritspråkets få ord för den (ett stycke som nämner
kopplingsledningar och säger "enligt tabell" eller "om inget annat anges", och under det en rad stammar med
talkolumner). Ägandet (`pipes/ownership.py`) tillämpar den sist av allt och bara på geometri som ingen annan
läsning rört: en primitiv som är **oägd** - aldrig tvetydig, aldrig en som en etikett nått - på en penna vars
lagernamn bär det förklarade systemet får den förklarade identiteten. Ett lager som två förklarade system skulle
kunna heta får inget. Varje sådan meter märks `DECLARED_CONNECTION_PIPE_BY_SHEET_TABLE` och redovisas som
`declared_m` på mängdraden, med `label_count` 0, så att en människa ser skillnaden på ett rör som pekats ut och
ett rör som förklarats. Regeln som lästes skrivs till `drawing-declarations.json`.

Det är inget närmaste-antagande: det är ritningens egen regel, skriven i ord, för exakt de rör ritaren inte
namngett. Utan tabellen ägs ingenting.

### 2c. Vad som är ett rör: streck-prick, ventiler, dubbellinjer

Tre ritkonventioner som läsningen läser som geometri, inte som antaganden (`pipes/representation.py`,
`measure/measure.py`):

* **Streck-prick-linjen** är ett rör. Pricken är en och en halv punkt lång och exportens avrundning vrider den
  några grader, så den har ingen riktning att lita på; strecket vars stråle den ligger på gör anspråk på den
  (`DOT_MAX`). Då är springan streck-till-prick en springa av linjens stil och bryggas, även där en prick
  saknas. Utan regeln blev nittio meter värmeledning tvåhundrafyrtiosju bitar.
* **En ventil i linjen** avslutar inte röret. Ritaren drar röret fram till ventilsymbolen, ritar ventilen med
  symbolpennan och drar vidare på andra sidan. Två fria, kollineära ändar med en liten symbol av en annan
  penna i springan (`SYMBOL_SPAN`, `SYMBOL_SIZE`) hör ihop: bryggan heter `symbol` i grafen och bär symbolens
  id.
* **Ett rör ritat som två linjer** är ett rör. Ett grövre rör ritas som sina två kanter några punkter isär,
  och etiketten med ett streck på var kant namnger båda. Två sträckor med samma namn och samma penna sida vid
  sida längs större delen av den kortare (`measure.measure.DOUBLE_LINE_MAX`) räknas en gång: den längre kanten bär
  metrarna, den andra redovisas som `double_line_m` på raden och i exporten. Två rör med samma namn som bara
  löper bredvid varandra en bit förblir två.

## 3. Vilka AI-modeller som används, och exakt hur

Det här är det viktigaste avsnittet att läsa rätt, så det är rakt.

**Mätningen använder ingen språkmodell.** Varje meter i mängdtabellen kommer ur geometri, hänvisningslinjer och
regler i Python. Ingenting i mätvägen når nätverket. Det är vad som gör läsningen deterministisk och möjlig att
spåra.

Det finns fyra ställen där en modell *kan* kopplas in, alla utanför mätvägen, alla avstängda utan nyckel, och
ingen av dem kan hitta på en meter:

### 3.1 Andra läsaren (`semantics/astra.py`, transport i `engine/tools/astra_transport.py`)

*Modell:* OpenAI, standard `gpt-6-astra` (miljövariabeln `VVS_SECOND_READER_MODEL`), via Responses-API:et.

*När:* bara för ett fall som motorn själv redan förklarat tvetydigt, och bara där ritningen erbjuder en kort
lista av verkliga kandidater. Frågan bär kandidaterna. Svaret måste vara en av dem, tecken för tecken -
`verify` vägrar allt annat. Modellen kan alltså aldrig namnge ett rör, en penna, en dimension eller en meter som
läsningen inte redan lagt fram; den kan bara göra `AMBIGUOUS` till ett av svaren som redan låg på bordet.

*Bevis:* varje avgjort fall skriver ned att en modell valde, mellan vilka kandidater och varför, så att en
läsare kan se det och säga emot.

*Av/på:* av utan `OPENAI_API_KEY`. Med nyckel: på. `VVS_SECOND_READER=false` stänger av oavsett; `true` tvingar
på bakom en proxy som fäster referensen. En läsning som rådfrågat den säger det, och påstår då inte
determinism.

### 3.2 Agenten (`backend/app/agent.py`, verktygen i `engine/vvs_engine/agent/tools.py`)

*Modell:* samma transport och modell som ovan (`agent_transport`).

*Delningen:* modellen bestämmer **vad** som ska frågas, verktygen bestämmer **vad svaret är**. Modellen ser
verktygens namn och deras svar - aldrig geometri den kunde hitta på ur. Varje siffra i chatten kommer ur ett
verktygsanrop över de artefakter mätningen skrev, så ett svar i chatten och en rad i mängdtabellen kan inte
skilja sig åt. 26 verktyg för en ritning (mängda, hitta rör, följ nätet, varför äger det här röret sina meter,
vad togs inte som rör, och fem `foresla_`-verktyg som bara föreslår), 8 för hela handlingen (projektagenten, `agent/project_tools.py`: hus, blad,
mängder per hus, versioner, ändringar, vad som bör tittas på).

*Förslag är ord.* Verktyg som föreslår en rättelse skriver ingenting: de säger vilken rättelse de skulle skriva
och vad läsningen säger att den kostar. Först när en människa godkänner körs samma anrop igen på servern, och
det som kommer ut är det som skrivs - metrarna i loggen är läsningens, aldrig modellens.

*De färdiga frågorna* i panelen går rakt in i verktygen utan modell. De kan inte hitta på en siffra. Fritext
behöver modellen för att välja verktyg; det är hela skillnaden.

### 3.3 Vision (`review/vision.py`)

*Modell:* samma, med bilder (`vision_transport`). Sidan renderas som bild, rutas in, och modellen får se den
tillsammans med läsningens egna sträckor ritade ovanpå.

*Vad den får göra:* titta och säga. Fynden är ord: "här ser det ut som om..." De kan aldrig bli geometri -
`vision.look` har ingen väg in i en läsning. Risken är kostnad och tid, aldrig en fel meter.

### 3.4 OCR (`review/ocr_check.py`) - ingen språkmodell

`rapidocr-onnxruntime`, en lokal teckenigenkännare. Två användningar: som en oberoende andra läsning av bladets
text i granskningen (finns det beteckningar vektorläsningen missade?), och för att namnge de tecken
streckigenkännaren inte kunde. Den läser aldrig ritningen på egen hand; vektorgeometrin förblir mätningens källa.

### 3.5 Vad som *inte* är AI: inlärningen (`learning.py`, `corrections.py`)

Systemet "blir smartare" av rättelser, men inte genom träning och inte genom en modell. Regeln är smal och
uttalad:

En rättelse får göra exakt en sak på ett senare blad: **avgöra ett fall motorn själv redan markerat tvetydigt**,
till förmån för det svar en människa gav i samma situation. Den får aldrig skapa en sträcka, aldrig namnge
geometri ingen linje nådde, aldrig ändra en sträcka motorn är säker på, och aldrig rösta ned ritningen.

"Samma situation" är inte en likhetspoäng. Det är exakt träff på sex saker, alla lästa ur ritningen: pennan
(bredd och färg, utan lagret), hur bladet ritar sina hänvisningslinjer, motorns eget skäl att stanna,
beteckningens form (bokstäver och skiljetecken, inte siffror), fallets topologi (räknat, inte koordinater), och
vilka kandidater bladet erbjöd. Matchar inte alla sex talar lärdomen inte - två blad som bara liknar varandra
är två olika ritningar. Att bredda avtrycket kan bara få lärdomar att tala mer sällan, vilket är den riktning
det är säkert att ha fel åt.

Adminsidans "Inlärning" visar precis det: vilka lärdomar som finns, hur många gånger var och en talat, och
vilka rättelser som inte bar någon lärdom alls.

### 3.6 Nycklar

Ingen nyckel finns i repot, i en fil, i en logg eller i ett svar. `OPENAI_API_KEY` läses ur miljön i det
ögonblick anropet görs och läggs på tråden, ingen annanstans. Bakom en agentproxy som fäster referensen efter
att anropet lämnat maskinen skickas ingen nyckel alls härifrån.

---

## 4. Rättelser: vad en människa kan ändra, och vad det får lära ut

En människa som läser samma blad ser saker ritningen säger på sätt motorn inte har någon regel för ännu. Fem
sorters rättelse finns (`corrections.py`): förläng en sträcka, rita en ny, sudda, byt beteckning, sätt mängden
för hand. De läggs *ovanpå* läsningen, aldrig i den: motorns egen siffra står kvar bredvid den rättade
(`engine_total_m`), så det alltid syns vad som lästes och vad som ändrades. Varje rättelse går att ångra.

Rättelsen sparas med den **situation** den gjordes i (§3.5). Det är servern som läser av situationen ur sina
egna artefakter - en påhittad situation från klienten avvisas - för en tom situation skulle tyst stänga av hela
inlärningen.

Exporterna bär den rättade läsningen, med motorns siffra bredvid. En fil som visade en siffra läsaren redan
avvisat på skärmen, i det dokument de prissätter ur, vore fel sorts fil.

---

## 5. Projektanalysen: hela handlingen som en modell

En enkel analys läser en ritning och svarar med meter. Projektanalysen (`handling.py`, `backend/app/projects_api.py`)
läser alla blad i ett projekt och svarar med vad handlingen består av: hus, discipliner, skeden, versioner,
vad som hör ihop och vad som inte gick att avgöra.

Läsningen är billig med flit - den läser namnrutorna, inte geometrin, sekunder per blad - och den har en egen kö
så att den aldrig står bakom en halvtimmes mängdning.

**Ett före och ett efter får aldrig hittas på.** Ett par påstås bara när handlingarna själva bär ordningen: en
revisionsbeteckning, ett revisionsdatum, ett handlingsdatum eller ett skede. Ett tal i filnamnet är ingen
revision (`Hus A (2).pdf` är vad en webbläsare gör), och två handlingar från samma dag med samma status är två
discipliner i samma skede, inte två versioner. Det som inte går att ordna står som oklart, med vad det verkar
vara.

**Ändringsregistret** jämför två *läsningar*, inte två ritningar. Att en beteckning bara finns på ena bladet är
starkt. Att dess meter skiljer sig är svagt - två läsningar av samma oförändrade rör rör sig något - och under en
halvmeter eller fem procent räknas skillnaden inte som en ändring. Saknas läsningen på någon sida finns ingen
lista alls: att fylla i den saknade sidan med noll skulle göra hela den lästa sidan till "tillkommet".

Mängderna summeras **per hus och aldrig över projektet**: hus A och hus B har var sin beteckningslista.

Varje fält läsningen kom fram till går att rätta för hand, och rättelsen ligger kvar när analysen körs om. En
mapp som hette "Hus B" visade sig innehålla hus C:s ritningar - läsningen hade rätt och mappnamnet fel - men den
har inte alltid rätt.

---

## 6. Egna markeringar (mät, markera, anteckna)

Fliken **Markera** på en läsning låter mängdaren rita själv: längd, yta, antal, anteckning. Det ligger vid sidan
av läsningen, aldrig i den; de två redovisas var för sig (eget blad i Excel-filen, eget namn i JSON:en).

Måtten räknas på servern ur punkterna och bladets egen skala (`backend/app/markups.py`) - aldrig i webbläsaren,
för ett mått klienten räknar fram går inte att härleda till någonting. Utan en färdig läsning finns ingen
skala, och då står det "ingen skala" i stället för påhittade meter. En ytas omkrets räknas aldrig in i
meterraden. En struken markering står kvar i lagret så att den går att få tillbaka.

---

## 6b. Kalkyl och anbud

Knappen **Kalkylera →** i analysens flikrad (och på ritningssidan efter en färdig analys) leder till kalkylens
egen sida, `/jobs/{id}/kalkyl`. Den gör mängden till pris, i två steg som hålls isär så att varje krona går att
spåra till en rad på ritningen (`backend/app/calc.py`):

*Material.* Varje beteckning matchas mot materialboken (55 000 artiklar med nettopris). Bladets egen
förklaringslista säger vad materialkoden betyder ("R8 = LEDNINGAR AV ROSTFRIA RÖR"), men boken använder andra
ord ("rostfritt rör", "rf AISI 304", "EN1.4432"), så förklaringen läses först till en *materialklass* (pex,
koppar, rostfri, pp, pe, pvc, gjut, galv, stål) och boken söks på klassens egna ord, som metervara, i rätt
dimension - DN för plaströr och rostfria avloppsrör, ytterdiametern för övriga metallrör. Bland träffarna går
ett riktigt pris före ett tomt, sedan den som bär flest av förklaringens egna ord (står det RIR vinner
rör-i-rör), sedan det billigaste. Matchningen är ett förslag med alternativ bredvid - den som räknar väljer, och
valet sparas. Där förklaringen inte säger vad röret är gjort av föreslås inget: alternativen i rätt dimension
finns att välja bland, men ett rör i fel material prissatt med säker min är värre än en tom ruta, så raden står
som förbehåll tills någon valt.

*Arbete.* Timmarna kommer ur Normtid VVS (`vvs_engine/normtid.py`): grundtid per meter efter ytterdiameter och
material, tillägg för skarvmetod och höjd, avvikelseanalysens bedömning av objektet. Stigare räknas som en
våningshöjd där ritningen inte anger höjden. Där boken inte har någon tid står det, och timmen skrivs för hand -
en gissad normtid är värre än ingen, för den ser ut som ett besked. Tabellerna är avlästa ur boken och ska
kontrolleras mot utgåvan innan ett anbud lämnas; det står i gränssnittet.

Sedan spill (kalkylmängd = netto + spill), påslag på material och arbete var för sig, och moms - allt utskrivet.
Det som sparas är valen och antagandena, aldrig resultatet: talen räknas om ur läsningen varje gång, med kundens
rättelser ovanpå, så kalkylen och bladet aldrig visar två olika meter.

**Anbudet** skrivs ur den sparade kalkylen som en formgiven PDF i A4, satt i Liberation Sans. Kroppen -
inledning, specifikation rad för rad, förutsättningar, avtalsvillkor, förbehåll, underskrift - flödas av PyMuPDF
Story; huvudet (mörkt block med anbudsnummer, datum, giltighet, beställare, referens), summeringskortet (exkl.
moms, moms, att betala) och foten med sidnummer ritas ovanpå med sid-API:et, eftersom Story ritar om ett blocks
bakgrund överst på varje följande sida. **Avtalsvillkoren** väljs i kalkylen: ABT 06, AB 04, ABS 18,
Hantverkarformuläret 17 eller inget; valet ger anbudet en villkorsrubrik med entreprenörens vanliga förbehåll under
det regelverket (ÄTA, garantitid, ansvar) - anbudets egna formuleringar, inte avtalstexten. Rader utan artikel
eller normtid står som förbehåll, liksom det onämnda röret och det som inte ingår (fittings, genomföringar,
isolering som egen post, rivning). **Förhandsgranskningen** i appen visar anbudets sidor som bilder ur samma PDF
som laddas ner (`/calc/anbud/sida-{n}.png`) - det dokument som skickas, inte en efterlikning av det.

## 7. Akademin

Nio kurser, tjugotvå steg, femton kunskapsfrågor och tre fristående övningar med facit
(`frontend/src/learn.ts`, `components/Learn*.tsx`). Kurserna tas i ordning - den man är på står öppen, de framför
är låsta tills den är gjord, men varje låst kurs går att öppna ändå.

Framstegen ligger på kontot (`backend/app/academy.py`), inte i webbläsaren, så man fortsätter där man slutade
även från en annan dator. Poängen räknas på servern ur stegen själva - rätt på första försöket är värt mer än
rätt till slut - och utmärkelserna prövas mot tabellen. Ett resultat klienten får bestämma är ett önskemål.

---

## 8. Adminsidan

Två halvor som aldrig får blandas ihop (`backend/app/admin.py`, `frontend/src/pages/Admin.tsx`).

*Läsningen:* överblick (läsningar, täckning, tid), kurvan per dygn - staplarna är hur mycket som lästs, linjen
hur långt läsningen kom; att staplarna växer säger något om marknadsföringen, att linjen sjunker säger att något
gått sönder - varje läsning, varje rättelse med sin situation, inlärningen, och vilka regler kunder flyttat.

*Företaget:* konton och planer, partners och ambassadörer med två procenttal (rabatten till kunden och
provisionen till partnern, satta var för sig), utbetalningar räknade i ören ur samma funktion som visar
provisionen - beloppet skrivs aldrig av från en skärm - kundvård, innehåll (CMS), A/B-prov med Wilson-intervall
så att ett prov utan tillräckligt underlag säger det, och heatmap.

Ingenting på adminsidan får avgöra hur en ritning läses. Den dagen en rabattsats kan flytta en meter går det
inte längre att svara på varför en mängd blev som den blev.

**Reglerna** (`rules.py`) är öppna: varje tröskel läsningen använder står med namn, förklaring, enhet,
standardvärde och tillåtet intervall, och går att flytta per konto. En flyttad regel gäller bara den som
flyttade den, och varje läsning skriver ned vilka regler den kördes med.

---

## 9. Säkerhet

* Inloggning med JWT; lösenord hashade med bcrypt.
* **Nyckeln som undertecknar bevisen** har ett standardvärde i källkoden, och tjänsten **vägrar starta på en
  driftplattform** så länge det står kvar (`config.demand_a_real_secret`). Ett bevis undertecknat med en publik
  sträng är inget bevis.
* Broms mot gissning: efter tio fel på en adress inom en kvart svarar tjänsten 429, också på rätt lösenord.
  Räknat per adress och per avsändare. En okänd adress kostar lika lång tid som en känd med fel lösenord, så
  svarstiden inte avslöjar vilka konton som finns.
* Varje id-bärande väg prövar ägarskap; en annan användares projekt, ritning, jobb, markering eller
  projektanalys svarar 404.
* Uppladdningar läses bit för bit och stoppas vid 200 MB innan de ligger i minnet. En lösenordsskyddad, tom
  eller icke-PDF avvisas med en mening. En stackspårning når aldrig felrutan.
* Lagrets nycklar och webbappens filvägar prövas mot roten *med avskiljaren emellan* - ett prefix utan
  avskiljare släpper igenom grannen.
* Adminvägar kräver rollen `admin` (partners ser sina egna rader via `current_staff`). Rollen kommer från
  servern, aldrig från webbläsaren.

---

## 10. Drift

En container (`Dockerfile`, `railway.json`): webbappen byggs, motorn och API:t installeras, och API:t serverar
webbappen själv. Lokalt: `docker compose up` ger PostgreSQL, API och nginx. Se `README.md` och `.env.example`.

Miljö som betyder något: `VVS_SECRET_KEY` (krävs i drift), `VVS_DATABASE_URL` (SQLite som standard, PostgreSQL
i compose), `VVS_STORAGE_ROOT`, `VVS_WORKER_THREADS` (mängdningens kö), `VVS_ANALYSIS_DEADLINE_S` (tidsbudget per
blad), `OPENAI_API_KEY` och `VVS_SECOND_READER` (§3), `VVS_RUN_REVIEW`/`VVS_REVIEW_OCR`/`VVS_OCR_ASSIST`
(granskningen).

SQLite körs i WAL-läge med väntetid, så att mätningens framsteg och API:ts läsningar samsas.

`/api/version` säger vilken byggning som kör och om en andra läsare kan nås - utan inloggning, för en läsning är
bara kontrollerbar om man kan säga vilken kod som gjorde den.

---

## 11. Hur det valideras, och var det står

Ett facit-set på 33 ritningar från flera kontor, med mängdarens egna utsättningar som referens, ligger utanför
repot och nås aldrig av produktionskoden. En grind kör hela setet genom den riktiga tjänsten - registrera,
ladda upp, mängda, läs av API:t - och poängsätts efteråt av ett skript som aldrig kör motorn.

Två tal bär: **täckning** (andel av facits meter läsningen äger under rätt namn) och **falskhet** (meter under
fel namn, i andel av facit). Bara de system facit faktiskt täcker poängsätts.

Senaste grinden: **56,1 % täckning, 12,4 % falskt**, 245 av 365 beteckningar rätt. Kurvan över de senaste
rättelserna gick 49,6 → 56,1 % täckning och 18,1 → 12,4 % falskt, och det är den andra siffran som varit
svårast att sänka - varje regel som tar bort påhittade meter prövas mot att den inte tar riktiga med sig.

Det som fattas i täckningen är till största delen det systemet vägrar gissa: rör som ingen hänvisningslinje når,
och blad exporterade utan lagernamn där väggar och rör ritas med samma penna. Där står metrarna som *onämnda*
med sina siffror, och en människa kan rita in dem med en rättelse som sedan lär ut det den kan.

Dessutom: närmare trehundra automatiska prov (motor, API, gränssnitt), ett rökprov som klickar igenom hela webbappen med
konsolen öppen, determinismprovet, kontamineringsskanningen, och en isolationsprövning som prövar varje
id-bärande väg med fel ägare.

---

## 12. Vad systemet inte gör

* Det läser inte skannade eller bildbaserade PDF:er. Det gissar aldrig ur bildpunkter.
* Det hittar inte på en anslutning där linjer bara korsas, en meter där ingen linje pekar, en vertikal längd
  utan höjd, en revision ur ett filnamn, eller ett före och ett efter ur två discipliner.
* Det låter ingen modell avgöra en meter, och ingen rättelse skapa en.
* Det mängdar inte fittings, genomföringar, isolering som egen post, status (nytt/befintligt/rivs) eller
  beställningsmängd i handelslängder. Det står i `LATHUND.md` vad som är gjort och vad som inte är det.
