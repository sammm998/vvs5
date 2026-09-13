# BUILDING_CAD_READY

**BUILDING_CAD_READY = YES** - med de avgränsningar som står i avsnitt 3.

Bygg-CAD:et är ett generellt 2D+3D-modelleringssystem för hela byggnaden: en gemensam objektmodell i
millimeter (`frontend/src/cad/building.ts`, speglad i `backend/app/cad_model.py`), ett transaktionssystem
med ångra/gör om, kroppar och snitt räknade analytiskt (`solids.ts` ↔ `cad_geom.py`), mängder ur samma fält
som ritar, kollisioner med hålförslag, ett ritbord med plan och 3D sida vid sida, ritningsblad, import och
export i öppna format, och en agent som föreslår men aldrig skriver. VVS-mängdningen är en disciplin bland
tio; ingen del av CAD:et är VVS-specifik.

## 1. Delsystemen

| Delsystem | Status | Belägg |
|---|---|---|
| Objektmodell: projekt, byggnad, nivåer, vyer, lager, material, entiteter (34 typer), relationer, ursprung | PASS | `core.test.ts` (46 kontroller), `cad_model.py` validerar samma dokument |
| Nivåer: användarens egna höjder, ingen påhittad våningshöjd; kopiera plan | PASS | `test_02_levels_are_what_the_user_says`; UI "Nivåer +", kopiera-knapp |
| Rutnät med etiketter, pelare bundna till rutnätet | PASS | `test_03_the_grid`, relation ATTACHED_TO_GRID |
| Kommandon: transaktioner, ångra/gör om, `touched`, revisionsräkning | PASS | `core.test.ts`: ångra tar bort dörr och fönster tillsammans; gör om lägger tillbaka |
| Spara/ladda med revisioner, återställning, optimistisk samtidighet (409) | PASS | `test_a_building_document_is_saved_with_its_history.py`, steg 28 |
| Arkitektur: vägg (tjocklek, justering, nivåer), dörr/fönster/öppning i vägg (andel längs väggen), glasfasad, bjälklag med hål, sadeltak med nock och lutning, undertak, rum, trappa, räcke | PASS | steg 05-12; väggen delas kring öppningar (3 stycken + över/under) |
| Konstruktion: pelare (rekt/cirkel/I/H/U/L/RHS), balk med stöd, grund (platta/sula/plint), fackverk | PASS | steg 13-15; HEA-balkens vikt räknas ur profilarean |
| Allmän 2D-CAD: linje, polylinje, rektangel, cirkel, båge, ellips, spline, text, mtext, mått, hänvisning, skraffering, block | PASS | verktygsraden; segment/grepp/flytt i `plan.ts` |
| Fångst: ändpunkt, mittpunkt, centrum, skärning, vinkelrät, nät, ortho; exakt inmatning (längd, Tab vinkel) | PASS | ritbordet (Playwright: fyra väggar med skrivna längder) |
| 3D-editor (three.js): standardvyer, orto/perspektiv, gizmo som flyttar objekt, sektionsbox, genomskinlighet per disciplin, tråd, val | PASS | `BuildingView3D.tsx`; Playwright-skärmdumpar |
| 2D↔3D: samma objekt-id; ändring i 3D blir samma transaktion som i 2D | PASS | `on3dMove` → `Tx("Flytta i 3D")` |
| Snitt och fasader ur modellen, med nock i taket; egna vyer (section/elevation) | PASS | steg 27; sektionen tål ett hörn eller en kant på linjen |
| Ritningsblad A0-A4 med vyportar i egen skala och namnruta; PDF ur bladet | PASS | steg 27 (`A-40-1-001`, 1:100 / 1:50 på samma blad) |
| Måttsättning: associativa mått som följer objektet; taggad text som visar objektets fält | PASS | `apply()` räknar om mått med `refs`; `tagText()` |
| MEP: rör, kanal (rekt/rund), kabelstege, elrör med gemensam väg; utrustning med anslutningar; apparater; anslutningar och T-stycken härledda ur lägena | PASS | `connections()`; steg 20/23 |
| Kollisioner mellan discipliner med allvarlighet; hålförslag som kräver godkännande; godkänt hål tar bort kollisionen | PASS | steg 25-26 |
| Mängder för hela byggnaden: antal, m, m², m³, kg per grupp och material; ingen vikt utan densitet; server = webbläsare grupp för grupp | PASS | steg 24 (handräkning: 31,14 m², 115,5 m², 21 m) |
| Kostnadskoppling till kalkylen | PASS (avgränsat) | mängderna har samma gruppnycklar som kalkylens rader; inga priser i CAD:et |
| Filter: lager, disciplin, skede, dölj/isolera per vy | PASS | `visibleIn()` |
| Underlag: PDF-sida eller bild; verifierad skala ur läst handling, uppmätt med två punkter, eller okalibrerad (märkt) | PASS | `test_an_underlay_without_a_scale_says_so`; Playwright-kalibrering |
| Import: DXF (R12-entiteter, $INSUNITS), SVG (former, path med räta stycken), IFC (väggar, bjälklag, pelare, balkar, tak, rör, kanaler, dörrar/fönster genom öppningar, våningar), GLB/GLTF/OBJ/STL som referensnät | PASS | `test_what_was_exported_comes_back_as_the_same_house`; steg 29 |
| Export: IFC 4 (våningar, öppningar, fyllnad, material, Pset), GLB, SVG, DXF, PDF med namnruta och skalstock | PASS | `test_every_export_opens`; IFC-guid stabila och giltiga |
| Agent: typade verktyg (17), förslag med spöke och godkännande, aldrig ett påhittat mått, aldrig en skrivning i bladet | PASS | `test_the_drawing_board_agent_proposes_and_never_writes.py`; steg 28 |
| Ursprung på varje objekt (USER_MODELLED, IMPORTED_IFC, IMPORTED_DXF, DETECTED_FROM_PDF, AGENT_CREATED_APPROVED, USER_CORRECTED) | PASS | validering avvisar okända; steg 29 kontrollerar mängden |
| Validering: fel avvisas med besked (422 + lista), samma frågor i webbläsare och server | PASS | `test_a_broken_model_is_refused_with_the_reasons` |
| Prestanda: 5 733 objekt - validering 32 ms, kroppar 348 ms, mängder 255 ms, sektion 253 ms, kollisioner 824 ms, ångra 136 ms | PASS | `perf.test.ts` |
| Hela-huset-E2E, 29 steg | PASS | `test_a_whole_house_from_first_wall_to_ifc.py` |

CAD-provsviten: 42 prov i 6 filer, alla gröna (`test_the_building_model_holds_together`,
`test_a_building_document_is_saved_with_its_history`, `test_a_building_leaves_as_ifc_and_comes_back`,
`test_the_drawing_board_agent_proposes_and_never_writes`, `test_the_building_model_stays_fast_with_thousands_of_objects`,
`test_a_whole_house_from_first_wall_to_ifc`). Hela motorns provsvit: se avsnitt 4.

## 2. Vad som gäller överallt

- **Ingen påhittad dimension.** Nivåhöjder, väggtjocklekar, dörrmått, rördimensioner kommer från användaren,
  filen eller läsningen. Agentens skapande verktyg kräver måtten; saknas ett är svaret en fråga
  (`fraga_anvandaren`). Ett underlag utan skala ritas men märks; ett material utan densitet ger ingen vikt.
- **En sanning.** Relationer (HOSTED_BY, SUPPORTED_BY, CONNECTS_TO, BOUNDED_BY, ATTACHED_TO_GRID) härleds ur
  objektens fält; inget lagras dubbelt. Mängder räknas ur samma fält som ritar.
- **Ingen instabil CSG.** Väggar delas kring öppningar i stycken; snitt är planet mot fotavtrycket; taket är
  ett prisma per takfall med plan överkant.
- **Millimeter, lokal origo i 3D** (modellens mitt), y uppåt; IFC speglar y till norr uppåt; enheter i filer
  läses (DXF $INSUNITS, SVG fysisk bredd) och antaganden sägs.
- **Server = webbläsare.** `cad_geom.py` är en spegel av `solids.ts`; ett prov jämför varje kropp i samma
  hus; `cli.ts` låter Python-prov fråga exakt samma kod som ritbordet kör.

## 3. Avgränsningar (medvetna, dokumenterade)

| Vad | Läge |
|---|---|
| DWG | Stöds inte; det är ett slutet format. Svaret till användaren säger "spara som DXF eller IFC". |
| IFC-import: rotationer i IfcLocalPlacement, kurvade profiler, IfcMappedItem | Placeringar läses som förskjutningar; svängda profiler blir konturer; det som inte har en rak extrusion blir polylinje och räknas i `skipped`. |
| Lutande tak vid IFC-import | Blir ett platt tak med takets totalhöjd som tjocklek (BRep-låda); nock och lutning återskapas inte. |
| Trappor: L- och U-form | Modellen bär `kind`, kroppen ritas rak (`stairSolids`). |
| Väggar möts inte med geriskarv i 3D | Två väggars fotavtryck överlappar i hörnet; mängderna räknar centrumlinjelängd × höjd, det vanliga i kalkyl. |
| Constraints (parametriska villkor) | Rutnätsbindning och stöd finns som relationer; ett generellt villkorssystem (lika, parallell, låst avstånd) finns inte. |
| Samarbete i realtid | Stabila id, version per objekt och optimistisk samtidighet finns; ingen liveöverföring mellan klienter. |
| 3D-nät som referens mängdas inte | Avsiktligt: en importerad fil är en bild av något, inte en byggmodell. |
| Agentens fria text kräver modelltransporten (`OPENAI_API_KEY` vid anropet) | De färdiga frågorna och alla verktyg går utan modell; loopen är provad med en spelad modell. |

## 4. Provsviten i sin helhet

Hela motorns provsvit (`engine/tests`, minus den 29-stegs E2E som körs för sig) kördes efter sista
ändringen: se `fullsuite.txt` i den här mappen för utfallet. Kontaminationsskanningen av
`engine/vvs_engine` är PASS (65 filer, 0 fynd, ingen beroende av valideringsdata).

## 5. Var saker ligger

- Kärna (TypeScript): `frontend/src/cad/{building,commands,solids,quantities,clash,plan,tools,cli,perf.test,core.test,house.fixture}.ts`
- Ritbordet: `frontend/src/pages/BuildingCad.tsx`, `BuildingCadPanels.tsx`, `frontend/src/components/BuildingView3D.tsx`
- Server: `backend/app/{cad,cad_model,cad_geom,cad_export,cad_import,cad_agent}.py`
- Prov: `engine/tests/test_the_building_model_*`, `test_a_building_*`, `test_the_drawing_board_agent_*`, `test_a_whole_house_*`
