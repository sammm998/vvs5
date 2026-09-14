/* Vad plattformen består av, som innehåll i stället för som sidor.
 *
 * Startsidan visar funktionerna, och varje funktion har en egen sida. Båda läser härifrån, så en funktion kan
 * aldrig utlovas på startsidan utan att ha en sida - och en sida kan aldrig säga något annat än kortet som
 * ledde dit. Det som står här är det systemet faktiskt gör; siffrorna är uppmätta och står i results/.
 */

export type Step = { n: string; h: string; p: string; art: string };
export type Key = { n: string; l: string };
export type Slab = { kicker: string; h: string; p: string; bullets?: string[]; art: string };

export type Feature = {
  slug: string;
  nav: string;            // kort namn i menyer och kort
  kicker: string;
  title: string;          // sidans rubrik, får radbrytas med \n
  lede: string;
  /** en rad på startsidans kort */
  card: string;
  art: string;            // vilken figur kortet och hjälten ritar
  accent: string;
  keys: Key[];
  slabs: Slab[];
  steps: { title: string; lede: string; items: Step[] };
  /** vart man går för att använda den */
  to: string;
  toLabel: string;
};

export const FEATURES: Feature[] = [
  {
    slug: "mangdning",
    nav: "Mängdning",
    kicker: "Läsningen",
    title: "Mängden som ritningen\nredan säger",
    lede: "Ladda upp en VVS-ritning. Systemet läser bladets egen beteckningslista, följer varje hänvisningslinje till det rör den pekar på, och mäter i ritningens egen skala. Varje meter behåller sitt belägg.",
    card: "Beteckning, ledare, rör, skala — en mängd där varje rad går att öppna.",
    art: "read",
    accent: "#6ee7a5",
    keys: [
      { n: "80,1 %", l: "av referensens meter återfunna över 59 uppmätta blad" },
      { n: "0", l: "gissningar — identitet endast via riktiga ledarlinjer" },
      { n: "589", l: "tester som måste hålla innan en siffra får ändras" },
    ],
    slabs: [
      {
        kicker: "Identitet",
        h: "Ett rör får sitt namn av en linje, aldrig av närheten",
        p: "Det närmaste röret är nästan alltid fel rör. För varje beteckning söks den hänvisningslinje ritaren faktiskt drog — rak, bruten, i flera delar — och den följs till sin spets. Träffar den ingenting står beteckningen kvar utan meter, och det syns.",
        bullets: [
          "Bladets egen förklaringslista avgör vilka koder som namnger rör",
          "Texten byggs tillbaka även när CAD ritat bokstäverna som streck",
          "En kontakt är inte en anslutning förrän den är verifierad",
        ],
        art: "leader",
      },
      {
        kicker: "Utsträckning",
        h: "Inget rör slutar tyst",
        p: "Från fästpunkten följs röret genom böjar, avgreningar, exportglapp och streckmönster — bara över verifierade fysiska kopplingar. Där det slutar skrivs varför: dimensionen byter, systemet byter, geometrin tar slut, avgreningen är tvetydig.",
        bullets: [
          "En korsning är inte en koppling",
          "Sexton skäl en sträcka kan sluta av, alla utskrivna",
          "Det tvetydiga står som tvetydigt och mäts inte",
        ],
        art: "frontier",
      },
      {
        kicker: "Mätning",
        h: "Skalan tas ur bladet, aldrig ur ett antagande",
        p: "Stämpel, skalstock eller måttsättning — och när de är oense står konflikten kvar i svaret. Rör som ligger i skrafferad vägg redovisas för sig, så du själv väljer om de ska räknas. Vertikalt utan höjdbesked står som okänt, inte som noll.",
        bullets: [
          "Två parallella linjer som ritar ett rör blir ett rör",
          "Skrafferad vägg hittas oavsett hur kontoret lagt sina lager",
          "Ingen mätning på bildpunkter: en skannad PDF avvisas med besked",
        ],
        art: "scale",
      },
    ],
    steps: {
      title: "Från streck till meter",
      lede: "Sex steg, i den ordning motorn faktiskt går.",
      items: [
        { n: "01", h: "Ritningen öppnas som vektorer", p: "Varje streck med sin penna, färg, sitt lager och sin streckning.", art: "read" },
        { n: "02", h: "Bladet får en profil", p: "Vilka pennor, texter, streckmönster och ritsätt just det här bladet använder.", art: "read" },
        { n: "03", h: "Beteckningarna läses", p: "Text där det är text, återbyggda tecken där CAD ritat dem som streck.", art: "leader" },
        { n: "04", h: "Ledarna följs", p: "Från varje beteckning till det rör linjen pekar på, och ingen annanstans.", art: "leader" },
        { n: "05", h: "Röret följs ut", p: "Genom böjar och grenar, bara över kopplingar som går att belägga.", art: "frontier" },
        { n: "06", h: "Mängden skrivs", p: "Med skalan ur bladet och belägget kvar för varje rad.", art: "scale" },
      ],
    },
    to: "/login",
    toLabel: "Läs en ritning",
  },
  {
    slug: "cad",
    nav: "CAD",
    kicker: "Ritbordet",
    title: "Rita hela byggnaden,\ninte bara rören",
    lede: "Ett fullständigt CAD-rum i webbläsaren: väggar, dörrar, fönster, bjälklag, tak, rum och trappor; pelare, balkar, plattor och grund; rör, kanaler, kabelstegar och utrustning med sina anslutningar.",
    card: "Väggar, stomme och installationer i en modell — med mängder som följer med.",
    art: "cad",
    accent: "#60a5fa",
    keys: [
      { n: "7", l: "faser byggda: arkitektur, konstruktion, vyer, MEP, mängder, import, export" },
      { n: "2D ↔ 3D", l: "samma modell, synkad åt båda håll" },
      { n: "IFC", l: "in och ut, tillsammans med DXF, SVG och GLB" },
    ],
    slabs: [
      {
        kicker: "Modellen",
        h: "En byggnad, inte en samling streck",
        p: "Nivåer, rutnät och lager håller ihop det. En vägg vet att den är en vägg, ett rum vet vilka väggar som omsluter det, och ett rör vet vad det är anslutet till. Därför kan mängderna räknas ur modellen i stället för att mätas av den.",
        bullets: ["Ångra och gör om genom hela sessionen", "Revisioner sparas, ingenting skrivs över", "Kommandorad för den som hellre skriver än klickar"],
        art: "cadmodel",
      },
      {
        kicker: "Vyerna",
        h: "Plan, sektion, fasad och 3D — samma modell",
        p: "Ändra i planen och sektionen följer med. Måttsättning och annotering hör till vyn, inte till geometrin, så ett mått ljuger aldrig om modellen. Blad läggs ut för utskrift när ritningen ska lämna skärmen.",
        bullets: ["3D-editor byggd på three.js", "Kollisionskontroll mellan installation och stomme", "Underlag från PDF, bild eller DXF att rita ovanpå"],
        art: "views",
      },
    ],
    steps: {
      title: "Så kommer du igång",
      lede: "Från tomt blad till en modell med mängder.",
      items: [
        { n: "01", h: "Lägg upp nivåer och rutnät", p: "Våningshöjder och axlar först — allt annat hänger på dem.", art: "cad" },
        { n: "02", h: "Rita eller importera stommen", p: "Väggar och bjälklag för hand, eller ett underlag att rita ovanpå.", art: "cadmodel" },
        { n: "03", h: "Dra installationerna", p: "Rör, kanaler och stegar med sina anslutningar och dimensioner.", art: "views" },
        { n: "04", h: "Läs av mängderna", p: "De räknas ur modellen och uppdateras medan du ritar.", art: "cadmodel" },
      ],
    },
    to: "/cad",
    toLabel: "Öppna CAD-rummet",
  },
  {
    slug: "3d",
    nav: "3D",
    kicker: "Modellen",
    title: "Se ritningen\nsom en byggnad",
    lede: "När läsningen är klar reser sig planen. Rören lyfter från pappret med sina höjder, stigarna går genom bjälklagen, och du ser var systemet faktiskt går — inte bara var linjerna ligger.",
    card: "Planen reser sig: rör med höjd, stigare genom bjälklag, system för system.",
    art: "three",
    accent: "#a78bfa",
    keys: [
      { n: "1 klick", l: "från mängdtabellen till samma rör i modellen" },
      { n: "Per system", l: "tänd och släck KV, VV, VS, spill var för sig" },
      { n: "Höjder", l: "ur bladets egna CL- och VG-angivelser" },
    ],
    slabs: [
      {
        kicker: "Sambandet",
        h: "Samma rör i tabellen och i rummet",
        p: "Markera en rad i mängden och röret tänds i modellen. Klicka i modellen och raden rullar fram. Det är samma geometri hela vägen — ingen separat modell som kan hamna ur fas med mängden.",
        bullets: ["Lager att tända och släcka per system", "Stigare ritas som stigare, inte som punkter", "Det tvetydiga syns i sin egen färg"],
        art: "link3d",
      },
    ],
    steps: {
      title: "Så används den",
      lede: "Tre saker 3D-vyn är bra på.",
      items: [
        { n: "01", h: "Förstå ett schakt", p: "Var stigarna går och hur många de är, på en gång.", art: "three" },
        { n: "02", h: "Hitta det orimliga", p: "Ett rör som går genom ett bjälklag där inget schakt finns syns direkt.", art: "link3d" },
        { n: "03", h: "Visa någon annan", p: "En modell övertygar en beställare snabbare än en tabell.", art: "three" },
      ],
    },
    to: "/login",
    toLabel: "Se en läsning i 3D",
  },
  {
    slug: "mangda",
    nav: "Mängda",
    kicker: "För hand",
    title: "Mängda själv,\nmed verktyg som håller",
    lede: "Ibland ska man mäta för hand: en handling som inte är vektor, en del motorn lämnar tvetydig, eller en kontroll av det som redan lästs. Verktyget är byggt för att stå i nivå med det en mängdare är van vid.",
    card: "Kalibrering, fångst, ortho, avdrag och en markeringslista som går att redigera.",
    art: "measure",
    accent: "#fbbf24",
    keys: [
      { n: "Kalibrering", l: "mot ett känt mått på bladet" },
      { n: "Fångst", l: "mot ändpunkt, mitt, skärning och ortho" },
      { n: "Avdrag", l: "ytor och längder som ska bort ur summan" },
    ],
    slabs: [
      {
        kicker: "Arbetsbordet",
        h: "Ritningen är sidan, inte en panel bland andra",
        p: "PDF:en tar hela ytan. Verktygslådan ligger i kanten, markeringslistan i en egen flik, och det du mätt står kvar mellan sessionerna. Mätningar du gör kan läggas bredvid motorns egna, så de går att jämföra rad för rad.",
        bullets: ["Längd, area, antal och djup", "Redigera en markering i efterhand, inte rita om den", "Exporteras tillsammans med den lästa mängden"],
        art: "bench",
      },
    ],
    steps: {
      title: "Så mäter du",
      lede: "Fyra steg, samma som på papper.",
      items: [
        { n: "01", h: "Kalibrera", p: "Dra längs ett känt mått och skriv vad det är.", art: "measure" },
        { n: "02", h: "Välj verktyg", p: "Längd, area, antal — och fångst om linjerna ska mötas exakt.", art: "measure" },
        { n: "03", h: "Mät", p: "Ortho håller linjen rak när ritningen är det.", art: "bench" },
        { n: "04", h: "Rätta och räkna", p: "Justera det som blev fel och läs summan per grupp.", art: "bench" },
      ],
    },
    to: "/mangda",
    toLabel: "Öppna mängdningen",
  },
  {
    slug: "agent",
    nav: "Agenten",
    kicker: "Samtalet",
    title: "Fråga ritningen,\nfå svar med belägg",
    lede: "Släpp in en PDF i samtalet och fråga. Agenten svarar ur det som står i handlingen, säger vad den inte kunde avgöra, och hittar aldrig på en siffra. Samma motor som analysen, samma artefakter, samma credits.",
    card: "Släpp in en ritning och fråga. Svaret kommer ur handlingen, inte ur en gissning.",
    art: "agent",
    accent: "#f0abfc",
    keys: [
      { n: "Verktyg", l: "modellen väljer frågan, verktygen svarar ur det lästa" },
      { n: "Ingen geometri", l: "en språkmodell får aldrig hitta på koordinater eller meter" },
      { n: "Spårbart", l: "varje verktygsanrop går att fälla ut och läsa" },
    ],
    slabs: [
      {
        kicker: "Gränsen",
        h: "Modellen väljer frågan — ritningen ger svaret",
        p: "Agenten får välja vilken fråga som ställs till bladet och hur svaret formuleras. Den får aldrig välja ett tal. Alla siffror kommer ur samma deterministiska läsning som mängdtabellen, och en siffra utan belägg blir «det står inte i handlingen».",
        bullets: ["Jämför två blad mot varandra", "Fråga varför en rad ser ut som den gör", "Starta en läsning mitt i samtalet"],
        art: "chat",
      },
    ],
    steps: {
      title: "Bra frågor att börja med",
      lede: "Fyra som visar vad den är till för.",
      items: [
        { n: "01", h: "Vad är det här för blad?", p: "System, skala, vad handlingen omfattar.", art: "agent" },
        { n: "02", h: "Visa mängderna", p: "Rad för rad, med det som inte kunde avgöras för sig.", art: "chat" },
        { n: "03", h: "Vad kunde inte avgöras?", p: "Listan över det tvetydiga, och varför.", art: "chat" },
        { n: "04", h: "Vad kostar rören?", p: "Mot materialboken, med priserna synliga.", art: "agent" },
      ],
    },
    to: "/agent",
    toLabel: "Öppna agenten",
  },
  {
    slug: "kalkyl",
    nav: "Kalkyl",
    kicker: "Anbudet",
    title: "Från mängd\ntill anbud",
    lede: "Mängden är halva jobbet. Kalkylen tar rören, lägger på material, arbete och påslag, och gör ett anbud du kan granska i webbläsaren innan det lämnar huset — neutralt mot AB 04 och ABT 06.",
    card: "Material, arbete och påslag ovanpå mängden — och ett anbud att granska på skärmen.",
    art: "calc",
    accent: "#fb923c",
    keys: [
      { n: "Materialbok", l: "priser per beteckning, som du kan flytta" },
      { n: "AB 04 / ABT 06", l: "avtalsformen bor i kalkylen, aldrig i geometrin" },
      { n: "Förhandsgranskning", l: "anbudet sida för sida innan det laddas ner" },
    ],
    slabs: [
      {
        kicker: "Uppdelningen",
        h: "Geometrin är neutral, kalkylen tar ställning",
        p: "Samma ritning ger samma rör oavsett entreprenadform. Det är först i kalkylen avtalsformen betyder något, och det är därför en ändring där aldrig kan flytta en meter i mängden.",
        bullets: ["Påslag per post eller över hela anbudet", "Arbetstid per meter och dimension", "Exporteras som PDF och som kalkylblad"],
        art: "tender",
      },
    ],
    steps: {
      title: "Så byggs anbudet",
      lede: "Fyra steg från läst ritning till lämnat pris.",
      items: [
        { n: "01", h: "Mängden in", p: "Rören som lästes, med det tvetydiga markerat.", art: "calc" },
        { n: "02", h: "Material på", p: "Ur materialboken, med priser du själv styr.", art: "calc" },
        { n: "03", h: "Arbete och påslag", p: "Per post eller över hela anbudet.", art: "tender" },
        { n: "04", h: "Granska och lämna", p: "Sida för sida på skärmen, sedan som PDF.", art: "tender" },
      ],
    },
    to: "/login",
    toLabel: "Öppna kalkylen",
  },
  {
    slug: "utbildning",
    nav: "Utbildning",
    kicker: "VVS-akademin",
    title: "Lär dig läsa ritningen,\ninte bara mängda den",
    lede: "Nio kurser och tjugotvå föreläsningar, från vad ett VVS-system är till att mängda ett övningsblad själv och få det rättat. Varje föreläsning har en egen sida, en levande figur och en kontrollfråga.",
    card: "Nio kurser om att läsa en rörritning — med figurer som rör sig och övningar som rättas.",
    art: "learn",
    accent: "#67e8f9",
    keys: [
      { n: "9", l: "kurser i den ordning de bygger på varandra" },
      { n: "22", l: "föreläsningar, var och en med en egen sida" },
      { n: "2 h", l: "sammanlagt, gjort för att gå i småbitar" },
    ],
    slabs: [
      {
        kicker: "Formen",
        h: "Byggd för att göras, inte bläddras i",
        p: "Varje föreläsning visar det den handlar om som en levande ritning i stället för att beskriva det i ord, och avslutas med en fråga som går att svara fel på. Övningarna använder samma slags blad som tjänsten läser — ingen av dem går att klara genom att gissa på det som ligger närmast.",
        bullets: ["Stegen sparas på kontot, inte i webbläsaren", "Läs utan konto, spara med", "Samma kurs för hela kontoret"],
        art: "academy",
      },
    ],
    steps: {
      title: "Vad du kan efteråt",
      lede: "Fyra saker kursen faktiskt lär ut.",
      items: [
        { n: "01", h: "Läsa en beteckning", p: "System, material, dimension och isolering på tre sekunder.", art: "learn" },
        { n: "02", h: "Hitta i bladet", p: "Namnruta, förklaringslista, skalstock, sektioner.", art: "academy" },
        { n: "03", h: "Mängda i ordning", p: "Vad som räknas, vad som inte gör det, och varför.", art: "learn" },
        { n: "04", h: "Granska en maskinmängd", p: "Se var den är säker och var den inte är det.", art: "academy" },
      ],
    },
    to: "/utbildning",
    toLabel: "Till akademin",
  },
];

export const featureBySlug = (slug?: string) => FEATURES.find((f) => f.slug === slug) ?? null;
