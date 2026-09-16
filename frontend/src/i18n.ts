/* Språket, med svenskan som nyckel.
 *
 * Gränssnittet är skrivet på svenska och ska fortsätta läsas på svenska i koden - en mängdare och en utvecklare
 * ska kunna tala om samma knapp. Därför är nyckeln den svenska texten själv, inte en uppfunnen kod: `t("Mängder")`
 * ger "Quantities" på engelska och "Mängder" på svenska, och en sträng som ingen hunnit översätta visas på
 * svenska i stället för att försvinna eller visa sin nyckel. Översättning blir något man lägger till, aldrig
 * något som kan gå sönder.
 *
 * Språkbytet laddar om sidan. Det är med avsikt: ett halvt omritat gränssnitt där några rader bytt språk och
 * andra inte är värre än att vänta en halv sekund, och en omladdning gör att varje sträng i appen - även de i
 * komponenter som inte lyssnar på något - kommer tillbaka på rätt språk.
 *
 * Talformatet följer med: svenska skriver 12,5 m och engelska 12.5 m. Det är inte en detalj i en mängd.
 */

export type Lang = "sv" | "en";

const KEY = "fc.lang";

function initial(): Lang {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "sv" || saved === "en") return saved;
  } catch { /* privat läge eller blockerad lagring: följ webbläsaren i stället */ }
  try {
    return navigator.language.toLowerCase().startsWith("sv") ? "sv" : "en";
  } catch { return "sv"; }
}

export const lang: Lang = initial();

export function setLang(next: Lang): void {
  if (next === lang) return;
  try { localStorage.setItem(KEY, next); } catch { /* kan inte sparas: språket gäller ändå den här sidan */ }
  location.reload();
}

/** Den svenska texten, eller dess engelska motsvarighet när en sådan finns. */
export function t(sv: string): string {
  if (lang === "sv") return sv;
  return EN[sv] ?? sv;
}

/** Ett tal som språket skriver det: 12,5 på svenska, 12.5 på engelska. */
export function num(v: number, decimals = 2): string {
  return v.toLocaleString(lang === "sv" ? "sv-SE" : "en-GB",
    { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export const locale = () => (lang === "sv" ? "sv-SE" : "en-GB");

/* ---------------------------------------------------------------------------------------------------------
 * Ordboken. En rad per sträng, svensk nyckel först.
 *
 * Saknas en rad visas svenskan - det är felfallet, och det är ofarligt. Lägg till raden när strängen dyker upp
 * på en sida som ska gå att läsa på engelska.
 * --------------------------------------------------------------------------------------------------------- */
const EN: Record<string, string> = {
  // --- meny och ram -------------------------------------------------------------------------------------
  "Hur det funkar": "How it works",
  "Priser": "Pricing",
  "Utbildning": "Training",
  "Om oss": "About",
  "Dokumentation": "Documentation",
  "Kontakta oss": "Contact",
  "Kontakt": "Contact",
  "Logga in": "Sign in",
  "Logga ut": "Sign out",
  "Plattformen": "The platform",
  "Projekt": "Projects",
  "Mängda ett blad": "Take off a sheet",
  "Mängda": "Take-off",
  "Material": "Materials",
  "Credits": "Credits",
  "Administration": "Administration",
  "Agent": "Agent",
  "Lär dig VVS": "Learn HVAC",
  "Svenska": "Swedish",
  "Engelska": "English",
  "Språk": "Language",
  "till startsidan": "to the start page",

  // --- arkitektursidan ----------------------------------------------------------------------------------
  "Hela systemet,": "The whole system,",
  "del för del": "part by part",
  "Vad som kör, vad varje del äger, hur en mening blir en meter - och vad ett blad kostar oss i drift.":
    "What runs, what each part owns, how a sentence becomes a metre - and what a sheet costs us to operate.",
  "Delarna": "The parts",
  "Vägen genom systemet": "The path through the system",
  "Läsarna": "The readers",
  "Hur vi vet": "How we know",
  "Vad ett blad kostar": "What a sheet costs",
  "processer: motor, tjänst, rum": "processes: engine, service, room",
  "läsare som måste vara överens": "readers that must agree",
  "mediankostnad per blad": "median cost per sheet",
  "Tre saker, med en gräns mellan sig som hålls": "Three things, with a boundary between them that holds",
  "Motorn": "The engine",
  "Tjänsten": "The service",
  "Rummet": "The room",
  "Från uppladdad fil till granskad mängd": "From uploaded file to reviewed quantity",
  "Två modeller, och regeln att de måste vara överens": "Two models, and the rule that they must agree",
  "59 blad med känd facit, mätta tre gånger om": "59 sheets with a known reference, measured three ways",
  "Vad ett blad kostar oss": "What a sheet costs us",
  "Driftkostnad": "Operating cost",
  "Följ en ritning genom läsningen": "Follow a drawing through the reading",
  "Läs dokumentationen": "Read the documentation",
  "Mått": "Measure",
  "Vad det jämför": "What it compares",
  "Var det står": "Where it lives",
  "Rad mot rad": "Row against row",
  "Dragning mot rör": "Run against pipe",
  "Sträcka mot sträcka": "Stretch against stretch",
  "Meter per beteckning mot referensen": "Metres per designation against the reference",
  "Varje mätt sträcka mot varje fysiskt rör": "Every measured stretch against every physical pipe",
  "Mängdarens egna mätlinjer mot vår geometri, på ritningen":
    "The estimator's own measuring lines against our geometry, on the drawing",
  "Blad": "Sheet",
  "Kostnad": "Cost",
  "Vad som dominerar": "What dominates",
  "Mediansidan": "The median sheet",
  "Blad som har öppna fall (39 %)": "Sheets with open cases (39 %)",
  "Snitt över alla blad": "Mean across all sheets",
  "Tätaste bladet som mätts": "Densest sheet measured",
  "processortid; inga öppna fall att fråga om": "processor time; no open cases to ask about",
  "modellanropen, median 4 frågor": "the model calls, median 4 questions",
  "dras upp av de täta bladen": "pulled up by the dense sheets",
  "1,08 miljoner banor och 54 öppna fall": "1.08 million paths and 54 open cases",
  "Processor": "Processor",
  "Modellanrop": "Model calls",
  "Lagring": "Storage",
  "Geometrin": "The geometry",
  "Enigheten": "The agreement",

  // --- mängdtabellen ------------------------------------------------------------------------------------
  "Mängder": "Quantities",
  "Beteckning": "Designation",
  "Etiketter": "Labels",
  "Sträckor": "Runs",
  "Horisontellt": "Horizontal",
  "Vertikalt": "Vertical",
  "Totalt": "Total",
  "Tvetydigt": "Ambiguous",
  "Skrafferat": "Hatched",
  "Stigare": "Risers",
  "Status": "State",
  "Summa": "Sum",
  "Sök beteckning/DN": "Search designation/DN",
  "Alla status": "All states",
  "Räkna med skrafferade ytor": "Include hatched areas",
  "Räkna med förklarade kopplingsledningar": "Include declared connection pipes",
  "ANTAGANDEN": "ASSUMPTIONS",
  "våningshöjd ej satt": "storey height not set",
  "stigare ur etiketter": "risers from labels",
  "okänt": "unknown",
  "BEKRÄFTAD": "CONFIRMED",
  "TVETYDIG": "AMBIGUOUS",
  "INGEN SKALA": "NO SCALE",
  "EJ STÖDD STIL": "UNSUPPORTED STYLE",
  "ENDAST STIGARE": "RISERS ONLY",
  "I SKRAFFERAD YTA": "IN HATCHED AREA",
  "Ritningen anger ingen höjd och inga stigare hittades":
    "The drawing states no height and no risers were found",
  "Stigarna är hittade; ange våningshöjd för att räkna om dem till meter":
    "The risers are found; set a storey height to turn them into metres",

  // --- arkitektursidans brödtext ------------------------------------------------------------------------
  "4 %": "4 %",
  "8 %": "8 %",
  "88 %": "88 %",
  "Astra 6": "Astra 6",
  "Claude": "Claude",
  "pdf/ - varje streck ur filen med penna, färg, lager, streckning och ursprung": "pdf/ - every stroke from the file with its pen, colour, layer, dash pattern and provenance",
  "profile/ - bladets egna familjer: pennor, textstorlekar, ledarformer, skraffering": "profile/ - the sheet's own families: pens, text sizes, leader shapes, hatching",
  "text/ - bokstäver byggda tillbaka ur streck när CAD ritat dem i stället för att skriva dem": "text/ - letters rebuilt from strokes where CAD drew them instead of writing them",
  "semantics/ - beteckningar, förklaringslista, ledare och vad ledaren pekar på": "semantics/ - designations, the legend, leaders and what a leader points at",
  "pipes/ - topologi, ägande, fronter: vem sträckan tillhör och var den slutar": "pipes/ - topology, ownership, frontiers: who owns a run and where it ends",
  "measure/ - skala, mätning, lodrätt, mängdrader": "measure/ - scale, measurement, vertical, quantity rows",
  "review/ - agenter, OCR och syn som prövar det färdiga resultatet utan att flytta en meter": "review/ - agents, OCR and vision that test the finished result without moving a metre",
  "rules.py - varje gräns läsningen följer, samlad och beskriven på ritningens språk": "rules.py - every limit the reading follows, gathered and described in the drawing's language",
  "auth, projekt och ritningar; lagring på disk eller objektlager": "auth, projects and drawings; storage on disk or in an object store",
  "jobb med strömmad status - varje steg syns medan det händer": "jobs with streamed status - each step is visible while it happens",
  "artefakter ut som de skrevs, plus exporter (CSV, XLSX, Bluebeam-markering, anbud)": "artifacts as they were written, plus exports (CSV, XLSX, Bluebeam markup, tender)",
  "credits: vad en läsning drar, och återbetalning när den inte gav något": "credits: what a reading draws, and a refund when it gave nothing",
  "admin: systemhälsa, rättelser, inlärning, regler, prissättning": "admin: system health, corrections, learning, rules, pricing",
  "analysrummet: PDF-vy, lager, mängdtabell, tvetydigheter, agenten": "the analysis room: PDF view, layers, quantity table, ambiguities, the agent",
  "mängdningsverktyget: kalibrering, fångst, avdrag, markeringslista": "the take-off tool: calibration, snapping, deductions, markup list",
  "CAD-rummet: rita och redigera i stället för att ladda upp": "the CAD room: draw and edit instead of uploading",
  "kalkyl och anbud, projektanalys över hela handlingen": "costing and tender, project analysis across the whole set",
  "akademin och utbildningen": "the academy and the training",
  "Ett bibliotek utan webbserver, utan databas och utan nät. Den tar en PDF och lämnar artefakter. Allt som avgör en meter bor här, och ingenting här känner till en användare.": "A library with no web server, no database and no network. It takes a PDF and leaves artifacts. Everything that decides a metre lives here, and nothing here knows about a user.",
  "Konton, projekt, ritningar, jobb, resultat, exporter, credits och admin. Den kör motorn i en arbetartråd med en tidsbudget och skriver ned allt den får tillbaka.": "Accounts, projects, drawings, jobs, results, exports, credits and admin. It runs the engine in a worker thread with a time budget and writes down everything it gets back.",
  "Ritningen, mängden och beläggen bredvid varandra. Ingen siffra visas utan att gå att öppna: varje rad kan spåras till de vektorer den kom ur.": "The drawing, the quantity and the evidence side by side. No figure is shown that cannot be opened: every row can be traced back to the vectors it came from.",
  "Avgör allt den kan försvara. Säger TVETYDIGT när den inte kan. Ingen modell får röra det den avgjort.": "Decides everything it can defend. Says AMBIGUOUS when it cannot. No model may touch what it has decided.",
  "Får ett öppet fall och ritningens egna kandidater. Väljer en av dem eller svarar OKLART.": "Gets an open case and the drawing's own candidates. Picks one of them or answers UNCLEAR.",
  "Samma fråga, oberoende. Ser inte vad den andra svarat.": "The same question, independently. It does not see what the other answered.",
  "Fallet avgörs bara när båda pekar på samma kandidat. Är de oense, eller svarar bara den ena, står fallet kvar tvetydigt.": "The case is settled only when both point at the same candidate. If they disagree, or only one answers, the case stays ambiguous.",
  "17 s grundtid plus 1,5 s per tusen banor. Mediansidan 16 s.": "17 s of base time plus 1.5 s per thousand paths. The median sheet 16 s.",
  "Bara öppna fall frågas. 39 % av bladen har några alls; där de finns är medianen 4 frågor.": "Only open cases are asked about. 39 % of sheets have any at all; where they do, the median is 4 questions.",
  "Artefakterna, 5,8 MB för mediansidan, sparade i tolv månader.": "The artifacts, 5.8 MB for the median sheet, kept for twelve months.",
  "Motorn vet ingenting om konton, tjänsten vet ingenting om geometri, och rummet räknar aldrig själv. Gränsen är inte en smaksak: den är det som gör att en mängd kan läsas om, av någon annan, och bli densamma. Motorn kan köras från ett terminalfönster utan att något av det andra finns.": "The engine knows nothing about accounts, the service knows nothing about geometry, and the room never computes anything itself. The boundary is not a matter of taste: it is what lets a take-off be read again, by someone else, and come out the same. The engine runs from a terminal without any of the rest existing.",
  "Filen läggs undan och ett jobb skapas": "The file is put away and a job is created",
  "Tjänsten sparar ritningen, drar credits och lägger jobbet i kö. En skannad PDF avvisas direkt: där finns bara bildpunkter, och på bildpunkter gissar man.": "The service stores the drawing, draws credits and queues the job. A scanned PDF is refused outright: there are only pixels there, and on pixels one guesses.",
  "Arbetartråden kör motorn, med en tidsbudget": "The worker thread runs the engine, on a time budget",
  "Varje steg strömmas ut medan det händer. Går bladet över tidsbudgeten avbryts det och säger det, i stället för att hålla arbetaren för alltid.": "Each step is streamed out while it happens. A sheet that runs past the budget is stopped and says so, instead of holding the worker forever.",
  "Motorn skriver artefakter, inte slutsatser": "The engine writes artifacts, not conclusions",
  "Beteckningar, ledare, fästen, topologi, fysiska rör, fronter, mängdrader, bevisgraf, avstämning, determinism, kontaminationsrapport. Ungefär tjugo filer per blad, och mängden är bara en av dem.": "Designations, leaders, attachments, topology, physical pipes, frontiers, quantity rows, evidence graph, reconciliation, determinism, contamination report. About twenty files per sheet, and the quantity is only one of them.",
  "Granskningen prövar det färdiga": "The review tests the finished result",
  "Agenter läser resultatet mot bladet, OCR läser texten en andra gång, och synläsaren tittar på sidan. Ingen av dem flyttar en meter - de läser, de mäter inte.": "Agents read the result against the sheet, OCR reads the text a second time, and the vision reader looks at the page. None of them moves a metre - they read, they do not measure.",
  "Rummet visar mängden med sina belägg": "The room shows the quantity with its evidence",
  "Varje rad går att öppna: vilka rör, vilka etiketter, var de slutar och varför. Det tvetydiga står för sig och räknas inte in i tysthet.": "Every row opens: which pipes, which labels, where they end and why. The ambiguous stands apart and is never counted in silently.",
  "Rättelser sparas som rättelser": "Corrections are saved as corrections",
  "Det du ändrar skrivs som en ändring med ditt namn på, bredvid vad läsningen sa. Ingen siffra byts ut bakom ryggen på någon, och rättelserna är det som lär systemet nästa gång.": "What you change is written as a change with your name on it, beside what the reading said. No figure is swapped behind anyone's back, and the corrections are what teach the system next time.",
  "En språkmodell får aldrig skapa geometri här. Den får se ett fall som geometrin själv förklarat öppet, tillsammans med de kandidater ritningen erbjuder, och välja en av dem. Ett svar som inte står i listan kastas, tecken för tecken.": "A language model may never create geometry here. It is shown a case the geometry itself declared open, together with the candidates the drawing offers, and picks one of them. An answer that is not on the list is thrown away, character by character.",
  "Med en enda modell finns ändå en risk kvar: ett öppet fall har flera rimliga svar, och en modell som gissar fel förvandlar ett ärligt tvetydigt fall till ett självsäkert fel. Det är den dyraste sortens fel i en mängdning, för det ser ut som ett svar. Därför frågas två, oberoende av varandra.": "With a single model one risk remains: an open case has several reasonable answers, and a model that guesses wrong turns an honestly ambiguous case into a confident error. That is the most expensive kind of error in a take-off, because it looks like an answer. So two are asked, independently of each other.",
  "Kostnaden för det är två anrop i stället för ett på de fall som frågas alls, och vinsten är att en ensam modell inte kan skriva in ett fel. Går den ena inte att nå tystnar panelen i stället för att bli en ensam röst - fallet står kvar öppet, vilket är ett giltigt svar.": "The cost is two calls instead of one on the cases that are asked about at all, and the gain is that a single model cannot write an error in. If one cannot be reached the panel falls silent rather than becoming a lone voice - the case stays open, which is a valid answer.",
  "Utvecklingen går i grindar. En ändring körs blint över hela korpusen, körningen fryses med en hash av källkoden, och först därefter öppnas referensmängderna. Blir ändringen sämre backas den - fyra av de senaste sju gjorde det.": "Development goes in gates. A change is run blind across the whole corpus, the run is frozen with a hash of the source, and only then are the reference quantities opened. A change that measures worse is reverted - four of the last seven were.",
  "Referensmaterialet ligger utanför källkoden och motorn kan inte nå det. En skanner går igenom motorns alla filer före varje körning och vägrar om något av referensens ordförråd har läckt in.": "The reference material lives outside the source and the engine cannot reach it. A scanner walks every file of the engine before each run and refuses if any of the reference's vocabulary has leaked in.",
  "Det här är vad vi betalar för att läsa ett blad, inte vad någon betalar oss. Uppmätt på 305 blad, varje blad i en egen process, med två läsare inräknade. Kronorna kommer ur antaganden som står utskrivna i verktyget; byt ett antagande och talet räknas om.": "This is what we pay to read a sheet, not what anyone pays us. Measured over 305 sheets, one process each, with two readers counted. The kronor come from assumptions written out in the tool; change an assumption and the figure is recomputed.",
  "Processortiden räknas på en maskin med fyra kärnor vid 40 procents nyttjande, vilket ger 1,03 kr per kärntimme - tomgången ska bäras av de blad som faktiskt läses. Lagringen är artefakterna i tolv månader. Synläsaren är inte med i talen ovan: den kostar omkring 0,90 kr per sida och begärs för hand, inte automatiskt.": "Processor time is costed on a four-core machine at 40 % utilisation, which gives 1.03 kr per core-hour - the idle time is carried by the sheets that actually run. Storage is the artifacts for twelve months. The vision reader is not in the figures above: it costs about 0.90 kr per page and is asked for by hand, not automatically.",
  "Det betyder att kostnaden i praktiken styrs av hur mycket ritningen lämnar öppet, inte av hur stor den är. Ett blad som läsningen kan avgöra själv kostar ören. Varje gräns som skärps så att ett fall kan avgöras på ritningens egen geometri gör läsningen både bättre och billigare - det är samma arbete.": "So the cost is governed in practice by how much the drawing leaves open, not by how big it is. A sheet the reading can settle on its own costs pennies. Every limit tightened so that a case can be decided on the drawing's own geometry makes the reading both better and cheaper - it is the same work.",
  "Det finns en människa i slingan, på ett ställe: där läsningen säger TVETYDIGT. Det hon avgör sparas som en rättelse bredvid vad läsningen sa, och blir en lärdom som får avgöra samma sorts fall på ett annat blad - samma penna, samma ledarform, samma skäl, samma etikettform. Aldrig mer än så: en rättelse får aldrig skapa en sträcka eller ändra något motorn är säker på.": "There is a human in the loop, in one place: where the reading says AMBIGUOUS. What they decide is saved as a correction beside what the reading said, and becomes a lesson allowed to settle the same kind of case on another sheet - same pen, same leader shape, same reason, same label shape. Never more than that: a correction may never create a run or change something the engine is sure of.",
};

/** Hur många strängar som har en engelsk motsvarighet - för dokumentationen och för den som fyller på. */
export const translated = () => Object.keys(EN).length;
