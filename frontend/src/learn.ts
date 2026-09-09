/* VVS-akademin: vad en mängdare behöver kunna, i delmoment som går att göra en i taget.
 *
 * En läsning tar en stund, och den stunden är en av de få gånger en person sitter still framför verktyget. Det
 * här är vad de kan göra under tiden: lära sig systemen, beteckningen, bladet, hur en ritning ritas och hur en
 * mängd tas fram för hand - och sedan mängda ett övningsblad själv och få rättat.
 *
 * Innehållet är skrivet för svensk VVS-praxis och håller sig till det som gäller oavsett kontor. Där ett kontor
 * kan göra på flera sätt står det uttryckligen att det är så.
 */

export type Block =
  | { k: "p"; t: string }
  | { k: "ul"; t: string[] }
  | { k: "terms"; t: [string, string][] }
  | { k: "note"; t: string }
  | { k: "fig"; id: string; caption: string };

export type Quiz = { q: string; options: string[]; answer: number; why: string };

export type Lesson = { id: string; title: string; minutes: number; body: Block[]; quiz?: Quiz };

export type Module = { id: string; title: string; blurb: string; lessons: Lesson[] };

export const MODULES: Module[] = [
  {
    id: "system",
    title: "Systemen",
    blurb: "Vad ett VVS-system är, vilka som finns och vad som skiljer dem åt.",
    lessons: [
      {
        id: "system-vad",
        title: "Vad VVS omfattar",
        minutes: 4,
        body: [
          { k: "p", t: "VVS står för värme, ventilation och sanitet. På en rörritning är det rören som räknas, och de delar upp sig i några få familjer som beter sig helt olika. Att veta vilken familj en ledning tillhör är det första en mängdare gör, för det avgör både material, dimension och hur den får dras." },
          { k: "terms", t: [
            ["Tappvatten", "Kallt och varmt vatten fram till tappstället. Står under tryck, kan gå i vilken riktning som helst och behöver inte fall."],
            ["Spillvatten", "Avlopp från toaletter, tvättställ och golvbrunnar. Går med självfall, alltså alltid nedåt, och måste luftas."],
            ["Dagvatten", "Regn och smältvatten från tak och mark. Också självfall, men skilt från spillvattnet."],
            ["Värme", "Radiator- eller golvvärmekretsar, fram- och returledning i par."],
            ["Kyla", "Komfortkyla, ofta isolerad hela vägen eftersom kondens annars droppar."],
            ["Sprinkler", "Eget system med egna regler, ritas oftast på egen ritning."],
          ] },
          { k: "note", t: "Självfall mot tryck är den viktigaste skillnaden. En tryckledning kan gå upp, ned och runt hörn hur som helst. En självfallsledning måste luta hela vägen, och därför bestämmer den var allt annat får plats." },
        ],
        quiz: {
          q: "En ledning på ritningen går uppåt genom tre våningar utan att luta. Vilket system kan den inte tillhöra?",
          options: ["Tappkallvatten", "Spillvatten", "Värme framledning", "Komfortkyla"],
          answer: 1,
          why: "Spillvatten går med självfall och måste luta hela vägen. En stigande spillvattenledning finns bara som en stigare med luftning, aldrig som en transportsträcka.",
        },
      },
      {
        id: "system-kv-vv",
        title: "KV, VV och VVC",
        minutes: 4,
        body: [
          { k: "p", t: "Tappvattnet delas i tre ledningar som nästan alltid går tillsammans, och som därför är lätta att blanda ihop i en bunt på ritningen." },
          { k: "terms", t: [
            ["KV", "Tappkallvatten. Går från inkommande servis ut till varje tappställe."],
            ["VV", "Tappvarmvatten. Från beredare eller växlare ut till tappstället."],
            ["VVC", "Varmvattencirkulation. Går tillbaka från de yttersta tappställena så att varmvattnet inte hinner kallna i ledningen."],
          ] },
          { k: "p", t: "VVC är klenare än VV, ofta en dimension mindre, och finns bara där sträckan är så lång att väntetiden annars blir för lång. Ser du VV utan VVC på en lång sträcka är det värt en fråga till konstruktören." },
          { k: "note", t: "I en bunt ligger KV och VV parallellt med några centimeters mellanrum. Geometrin ensam kan inte säga vilken som är vilken — bara etiketten och dess hänvisningslinje kan det. Det är därför en mängdning aldrig får gissa på närhet." },
        ],
        quiz: {
          q: "Två parallella ledningar går genom ett schakt. Den ena är märkt VV1-X31-16. Vad är den andra troligen?",
          options: ["En dagvattenledning", "KV eller VVC", "En radiatorretur", "En sprinklerledning"],
          answer: 1,
          why: "Tappvatten dras i bunt. Bredvid en VV ligger nästan alltid KV, och på längre sträckor även VVC.",
        },
      },
      {
        id: "system-avlopp",
        title: "Spillvatten och luftning",
        minutes: 4,
        body: [
          { k: "p", t: "En spillvattenledning gör två saker samtidigt: den för bort vatten och den släpper in luft. Utan luft suger vattenpelaren tomt vattenlåsen och lukten kommer upp i rummet." },
          { k: "ul", t: [
            "Liggande ledningar läggs med fall, typiskt 1:100 för grova och brantare för klena.",
            "Stående ledningar kallas stammar. En stam fortsätter ofta upp över tak som luftning.",
            "Golvbrunnar, tvättställ och WC ansluter till stammen via kortare grenledningar.",
            "Rensmöjlighet ska finnas: rensrör eller rensbrunn där ledningen ändrar riktning.",
          ] },
          { k: "note", t: "På ritningen känns spillvattnet igen på grova dimensioner — 75, 110, 160 — och på att sträckorna slutar i brunnar och stammar snarare än i tappställen." },
        ],
      },
    ],
  },
  {
    id: "beteckning",
    title: "Beteckningen",
    blurb: "Hur en rörbeteckning är uppbyggd, och hur du läser den på tre sekunder.",
    lessons: [
      {
        id: "bet-delar",
        title: "Beteckningens delar",
        minutes: 5,
        body: [
          { k: "p", t: "En beteckning på en rörritning är inte ett namn utan en formel. Den skrivs i samma ordning varje gång och varje del svarar på en fråga." },
          { k: "fig", id: "designation", caption: "KV1-X31-16: system, material, dimension." },
          { k: "terms", t: [
            ["Systemkod", "Vilket system: KV1, VV1, S3, D1, VS21. Siffran skiljer flera system av samma slag åt."],
            ["Materialkod", "Vad röret är gjort av: X31 för PEX, R8 för rostfritt, P2 för PP-avlopp, S6 för stål. Koden står i bladets egen förklaringslista."],
            ["Dimension", "Rörets storlek. För tappvatten oftast ytterdiameter, för avlopp den nominella storleken."],
            ["Tillägg", "Ibland /W för isolering, ibland en bokstav för utförande. Också det står i listan."],
          ] },
          { k: "note", t: "Materialkoderna är inte standard mellan kontor. Samma X31 kan betyda olika saker i två projekt. Därför läser man alltid bladets egen förklaringslista först, aldrig ur minnet." },
        ],
        quiz: {
          q: "Vad är dimensionen i S3-R8-110?",
          options: ["S3", "R8", "110", "Det står inte"],
          answer: 2,
          why: "Sista talet är dimensionen. S3 är systemet, R8 materialet.",
        },
      },
      {
        id: "bet-dim",
        title: "DN, dy och vad talet betyder",
        minutes: 5,
        body: [
          { k: "p", t: "Samma tal på ritningen kan betyda två olika mått, och skillnaden är inte liten." },
          { k: "terms", t: [
            ["DN", "Nominell dimension. Ett namn på storleken, ungefär den inre. DN25 är alltså ungefär 25 mm inuti, men ytterdiametern beror på materialet."],
            ["dy", "Ytterdiameter i millimeter. Används för plaströr och kopparrör: 16, 20, 25, 32, 40, 50, 63, 75, 90, 110, 160."],
          ] },
          { k: "p", t: "Tappvatten i plast och koppar anges nästan alltid i ytterdiameter. Avlopp i plast likaså: 75, 110 och 160 är ytterdiametrar. Stål och gjutjärn anges i DN. Ett rör märkt 110 är därför grovt, ett märkt 16 är en tappvattenledning fram till ett tvättställ." },
          { k: "note", t: "Att blanda ihop DN och dy ger fel material i kalkylen, inte fel längd. Längden mäts ur ritningen och påverkas inte — men priset per meter gör det." },
        ],
        quiz: {
          q: "Ett tappvattenrör är märkt 16. Vad handlar det rimligen om?",
          options: ["En stamledning för hela huset", "En anslutning fram till ett tappställe", "En dagvattenledning", "En sprinklerledning"],
          answer: 1,
          why: "16 mm ytterdiameter är den klenaste vanliga tappvattendimensionen och används på de sista metrarna fram till ett tappställe.",
        },
      },
    ],
  },
  {
    id: "bladet",
    title: "Bladet",
    blurb: "Vad en rörritning består av, och var du hittar det du behöver.",
    lessons: [
      {
        id: "blad-delar",
        title: "Ritningens delar",
        minutes: 5,
        body: [
          { k: "p", t: "Ett blad ser rörigt ut tills man vet att det alltid består av samma sex saker." },
          { k: "terms", t: [
            ["Stämpeln", "Nere till höger: vem som ritat, projektnummer, ritningsnummer, skala, datum och revidering."],
            ["Skalan", "Både utskriven (1:50) och ofta ritad som en skalstock. De två ska säga samma sak."],
            ["Förklaringslistan", "Beteckningslistan: kolumnen med koder och vad de betyder. Den är bladets ordbok."],
            ["Planen", "Själva byggnaden med rören ritade i den."],
            ["Etiketterna", "Beteckningarna ute i planen, var och en med en hänvisningslinje till sitt rör."],
            ["Noterna", "Textrutor med villkor: fall, isolering, samordning. De mängdas inte, men de påverkar."],
          ] },
          { k: "note", t: "Förklaringslistan står ibland bara på ett blad i handlingen och gäller ändå för alla. Hittar du ingen lista på bladet du håller på med: leta i omgången innan du gissar vad koderna betyder." },
        ],
        quiz: {
          q: "Bladet du mängdar har ingen förklaringslista. Vad gör du?",
          options: [
            "Gissar utifrån vad koderna brukar betyda",
            "Letar upp listan på ett annat blad i handlingen",
            "Hoppar över alla beteckningar du inte känner igen",
            "Mäter allt som är ritat, oavsett beteckning",
          ],
          answer: 1,
          why: "En handling skriver sin lista en gång. Att gissa ur minnet är det enda alternativ som ger fel utan att synas.",
        },
      },
      {
        id: "blad-skala",
        title: "Skalan och skalstocken",
        minutes: 4,
        body: [
          { k: "p", t: "Allt du mäter går genom skalan, så den är det första som ska kontrolleras. 1:50 betyder att en centimeter på pappret är femtio centimeter i verkligheten." },
          { k: "ul", t: [
            "Läs den utskrivna skalan i stämpeln.",
            "Mät skalstocken på pappret och kontrollera att den stämmer.",
            "Säger de två emot varandra: mät inte. Ta reda på vilken som gäller först.",
            "En utskrift som skalats om i skrivaren gör den utskrivna skalan fel och skalstocken rätt.",
          ] },
          { k: "note", t: "Ett vanligt fel: bladet är A1 men skrivs ut på A3. Då är den utskrivna skalan kvar men allt är hälften så stort. Skalstocken följer med i krympningen och är därför den man ska lita på." },
        ],
        quiz: {
          q: "Utskriven skala säger 1:50, skalstocken mäter upp till 1:100. Vad gäller?",
          options: ["1:50, det står ju skrivet", "1:100, skalstocken följer pappret", "Medelvärdet", "Inget — ta reda på varför de skiljer sig"],
          answer: 3,
          why: "Skalstocken följer visserligen pappret, men en konflikt kan också betyda att fel skalstock ritats. En mängd byggd på en oklar skala är fel i varje rad.",
        },
      },
      {
        id: "blad-hojder",
        title: "Höjder, stigare och sektioner",
        minutes: 5,
        body: [
          { k: "p", t: "En plan visar bara två dimensioner. Det som går upp och ned måste sägas med text eller ritas i en sektion." },
          { k: "terms", t: [
            ["Stigare", "En ledning som går lodrätt mellan våningar. Ritas som en liten cirkel eller ring där den passerar planet."],
            ["VG", "Vattengång: höjden på ledningens insida botten. Används för självfallsledningar."],
            ["CL", "Centrumlinje: höjden på rörets mitt. Används för tryckledningar."],
            ["Sektion", "En genomskärning av byggnaden, ritad separat, där det lodräta syns."],
          ] },
          { k: "note", t: "Ritningen anger nästan aldrig våningshöjden. Därför kan ingen — varken en människa eller ett program — räkna om ett antal stigare till meter utan att någon anger höjden. Antalet stigare räknas, höjden matas in." },
        ],
      },
    ],
  },
  {
    id: "rita",
    title: "Att rita",
    blurb: "Hur en rörritning byggs upp i CAD, och vad som gör den läsbar.",
    lessons: [
      {
        id: "rita-lager",
        title: "Lager, pennor och linjetyper",
        minutes: 5,
        body: [
          { k: "p", t: "Allt på ett blad ligger på ett lager, och lagret är ritarens sätt att säga vad geometrin är. Ett välritat blad kan tändas och släckas system för system." },
          { k: "ul", t: [
            "Ett lager per system: tappvatten för sig, spillvatten för sig, byggnaden för sig.",
            "Pennbredden säger vikt: rören grövre än byggnaden, byggnaden grövre än hjälplinjer.",
            "Linjetypen säger art: heldragen för synlig, streckad för dold eller under golv, streck-punkt för centrumlinje.",
            "Text och hänvisningslinjer på egna lager, aldrig på rörlagret.",
          ] },
          { k: "note", t: "En export som lägger allt på ett lager med en penna är fortfarande läsbar för ögat, men den har kastat bort ritarens egna uppgifter om vad som är vad. Det är den enskilt största orsaken till att en ritning blir svår att mängda." },
        ],
        quiz: {
          q: "Varför ska hänvisningslinjer ligga på ett eget lager?",
          options: [
            "För att de ska skrivas ut i annan färg",
            "För att de inte ska förväxlas med rör",
            "För att de ska kunna raderas snabbt",
            "Det spelar ingen roll",
          ],
          answer: 1,
          why: "En hänvisningslinje är ritad med samma sorts streck som ett rör. Ligger den på rörlagret går den inte att skilja från en ledning, varken för en människa eller för en maskin.",
        },
      },
      {
        id: "rita-etikett",
        title: "Etiketten och hänvisningslinjen",
        minutes: 5,
        body: [
          { k: "p", t: "Etiketten är det enda stället där ritningen säger vad en ledning är. Allt som mängdas hänger på att den går att koppla till rätt streck." },
          { k: "fig", id: "leader", caption: "Etikett, hänvisningslinje och den punkt där den landar på röret." },
          { k: "ul", t: [
            "Sätt etiketten utanför tät geometri, inte ovanpå den.",
            "Dra hänvisningslinjen så att den slutar på röret, inte bredvid det.",
            "Sätt gärna en liten markering där linjen möter röret.",
            "En etikett per sträcka mellan förgreningar; byter röret dimension ska den nya storleken sägas.",
            "Låt inte två etiketter peka på samma streck med olika beteckning.",
          ] },
          { k: "note", t: "Den vanligaste bristen i verkliga handlingar är en hänvisningslinje som slutar i luften några millimeter från röret. För ögat spelar det ingen roll. För varje automatisk mängdning betyder det att sträckan blir onämnd." },
        ],
        quiz: {
          q: "Etiketten står nära röret men har ingen hänvisningslinje. Vad är problemet?",
          options: [
            "Inget, närheten räcker",
            "Det syns inte vilket av flera rör den menar",
            "Etiketten blir svårläst",
            "Skalan blir fel",
          ],
          answer: 1,
          why: "I en bunt ligger flera rör inom några millimeter. Utan en ritad linje finns det inget som säger vilket av dem etiketten namnger — och att välja det närmaste är en gissning.",
        },
      },
    ],
  },
  {
    id: "mangda",
    title: "Att mängda",
    blurb: "Hur en mängd tas fram, rad för rad, och vad som inte räknas.",
    lessons: [
      {
        id: "mangd-ordning",
        title: "Arbetsordningen",
        minutes: 6,
        body: [
          { k: "p", t: "En mängdning görs i samma ordning varje gång. Ordningen är inte en vana — varje steg vilar på det förra." },
          { k: "ul", t: [
            "1. Kontrollera skalan mot skalstocken.",
            "2. Läs förklaringslistan och skriv upp vilka koder som är system.",
            "3. Gå igenom etiketterna och para ihop varje med sin sträcka.",
            "4. Mät sträckorna horisontellt, beteckning för beteckning.",
            "5. Räkna stigare per beteckning.",
            "6. Summera, och notera vad som inte gick att avgöra.",
          ] },
          { k: "note", t: "Punkt sex är den som skiljer en användbar mängd från en vacker. En rad du är osäker på ska stå som osäker, inte som ett tal." },
        ],
      },
      {
        id: "mangd-vad",
        title: "Vad som räknas och vad som inte gör det",
        minutes: 5,
        body: [
          { k: "terms", t: [
            ["Räknas", "Horisontell rörlängd i planen, mätt i skalan, per beteckning och dimension."],
            ["Räknas separat", "Stigare, som antal. De blir meter först när någon anger våningshöjden."],
            ["Räknas oftast inte", "Rör inne i vägg eller i skrafferad yta. De mäts men redovisas för sig."],
            ["Räknas aldrig", "Hänvisningslinjer, måttlinjer, byggnadens egna linjer, symboler."],
          ] },
          { k: "p", t: "Utöver längden behöver kalkylen antal: böjar, förgreningar, ventiler, brunnar. De räknas som stycken och hämtas ur symbolerna, inte ur längden." },
          { k: "note", t: "Spill och kapning läggs på i kalkylen, inte i mängden. Mängden ska vara vad ritningen visar; påslaget är ett antagande och hör hemma där antaganden syns." },
        ],
        quiz: {
          q: "En sträcka på 4,2 m går genom en skrafferad vägg. Hur redovisas den?",
          options: [
            "Räknas in i den horisontella längden",
            "Mäts och redovisas separat som rör i vägg",
            "Stryks helt",
            "Räknas som stigare",
          ],
          answer: 1,
          why: "Rör i vägg mäts men särredovisas, eftersom de flesta kalkyler prissätter dem annorlunda — eller inte alls.",
        },
      },
      {
        id: "mangd-kontroll",
        title: "Att kontrollera sin egen mängd",
        minutes: 5,
        body: [
          { k: "p", t: "Det finns fyra kontroller som fångar nästan alla fel, och de tar tillsammans några minuter." },
          { k: "ul", t: [
            "Täckning: hur mycket av det ritade röret har fått en beteckning? Ligger mycket kvar omärkt har något missats.",
            "Rimlighet: stämmer metrarna med husets storlek? En våning på 400 m² har sällan 20 m tappvatten.",
            "Systembalans: KV och VV följs oftast åt. Är den ena hälften så lång som den andra: leta.",
            "Ändar: varje sträcka ska sluta i något — ett tappställe, en stam, en brunn, en stigare. En ände i tomma luften är ett avbrott i läsningen.",
          ] },
          { k: "note", t: "Den sista kontrollen är den bästa. Fria rörändar pekar nästan alltid på antingen ett verkligt förhållande — en anslutning — eller på att sträckan tappats bort mitt i." },
        ],
        quiz: {
          q: "Din mängd visar 180 m KV1 och 42 m VV1 på samma våningsplan. Vad gör du?",
          options: [
            "Levererar — så står det på ritningen",
            "Kontrollerar VV1: tappvarmvatten följer normalt kallvattnet",
            "Dubblar VV1 på känsla",
            "Stryker KV1",
          ],
          answer: 1,
          why: "KV och VV dras i bunt fram till tappställena. En fjärdedel så mycket VV betyder oftast att en del av sträckorna inte kopplats till sin beteckning.",
        },
      },
    ],
  },
  {
    id: "ovning",
    title: "Övning: mängda ett blad",
    blurb: "Ett litet blad att mängda själv, med rättning direkt.",
    lessons: [
      {
        id: "ovning-1",
        title: "Läs bladet och mät",
        minutes: 10,
        body: [
          { k: "p", t: "Nedan står ett övningsblad i skala 1:50. Det har tre beteckningar, en förklaringslista och en sträcka som ingen etikett namnger. Klicka på en sträcka för att markera den, och para ihop den med rätt beteckning." },
          { k: "fig", id: "exercise", caption: "Övningsbladet. Klicka på en sträcka och välj vilken beteckning den hör till." },
          { k: "note", t: "Den grå sträckan hör inte till någon beteckning. Att lämna den omärkt är rätt svar — inte att gissa den till närmaste kod." },
        ],
      },
    ],
  },
];

export const ALL_LESSONS = MODULES.flatMap((m) => m.lessons.map((l) => ({ ...l, module: m.id })));

const KEY = "vvs.learn";

export function readProgress(): Record<string, boolean> {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}

export function markDone(lessonId: string, done = true) {
  const p = readProgress();
  if (done) p[lessonId] = true; else delete p[lessonId];
  try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* private window: progress just does not persist */ }
  return p;
}
