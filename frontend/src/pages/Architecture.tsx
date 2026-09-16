import { Link } from "react-router-dom";
import PublicFrame from "../components/PublicFrame";

/* Arkitektursidan: hela huset ritat en gång, för den som vill veta vad som faktiskt kör.
 *
 * Skillnaden mot "Hur det funkar" är läsaren. Den sidan följer en ritning genom läsningen. Den här visar
 * delarna: vilka processer som finns, vad var och en äger, vad som mäts och mot vad, och vad ett blad kostar
 * oss i drift. Kostnaden är driftkostnad - vad vi betalar för att läsa ett blad - inte vad en användare
 * betalar. Den står här därför att en arkitektur utan sin kostnad är en halv ritning.
 *
 * Varje tal på sidan kommer ur en mätning i repot och står med sin källa. Ändras mätningen ska talet ändras.
 */

const LAYERS: { tag: string; h: string; p: string; items: string[] }[] = [
  {
    tag: "ENGINE · PYTHON", h: "Motorn",
    p: "Ett bibliotek utan webbserver, utan databas och utan nät. Den tar en PDF och lämnar artefakter. Allt som avgör en meter bor här, och ingenting här känner till en användare.",
    items: [
      "pdf/ - varje streck ur filen med penna, färg, lager, streckning och ursprung",
      "profile/ - bladets egna familjer: pennor, textstorlekar, ledarformer, skraffering",
      "text/ - bokstäver byggda tillbaka ur streck när CAD ritat dem i stället för att skriva dem",
      "semantics/ - beteckningar, förklaringslista, ledare och vad ledaren pekar på",
      "pipes/ - topologi, ägande, fronter: vem sträckan tillhör och var den slutar",
      "measure/ - skala, mätning, lodrätt, mängdrader",
      "review/ - agenter, OCR och syn som prövar det färdiga resultatet utan att flytta en meter",
      "rules.py - varje gräns läsningen följer, samlad och beskriven på ritningens språk",
    ],
  },
  {
    tag: "BACKEND · FASTAPI", h: "Tjänsten",
    p: "Konton, projekt, ritningar, jobb, resultat, exporter, credits och admin. Den kör motorn i en arbetartråd med en tidsbudget och skriver ned allt den får tillbaka.",
    items: [
      "auth, projekt och ritningar; lagring på disk eller objektlager",
      "jobb med strömmad status - varje steg syns medan det händer",
      "artefakter ut som de skrevs, plus exporter (CSV, XLSX, Bluebeam-markering, anbud)",
      "credits: vad en läsning drar, och återbetalning när den inte gav något",
      "admin: systemhälsa, rättelser, inlärning, regler, prissättning",
    ],
  },
  {
    tag: "FRONTEND · REACT", h: "Rummet",
    p: "Ritningen, mängden och beläggen bredvid varandra. Ingen siffra visas utan att gå att öppna: varje rad kan spåras till de vektorer den kom ur.",
    items: [
      "analysrummet: PDF-vy, lager, mängdtabell, tvetydigheter, agenten",
      "mängdningsverktyget: kalibrering, fångst, avdrag, markeringslista",
      "CAD-rummet: rita och redigera i stället för att ladda upp",
      "kalkyl och anbud, projektanalys över hela handlingen",
      "akademin och utbildningen",
    ],
  },
];

const READERS = [
  ["Geometrin", "Avgör allt den kan försvara. Säger TVETYDIGT när den inte kan. Ingen modell får röra det den avgjort."],
  ["Astra 6", "Får ett öppet fall och ritningens egna kandidater. Väljer en av dem eller svarar OKLART."],
  ["Claude", "Samma fråga, oberoende. Ser inte vad den andra svarat."],
  ["Enigheten", "Fallet avgörs bara när båda pekar på samma kandidat. Är de oense, eller svarar bara den ena, står fallet kvar tvetydigt."],
];

const COST = [
  ["Processor", "4 %", "17 s grundtid plus 1,5 s per tusen banor. Mediansidan 16 s."],
  ["Modellanrop", "88 %", "Bara öppna fall frågas. 39 % av bladen har några alls; där de finns är medianen 4 frågor."],
  ["Lagring", "8 %", "Artefakterna, 5,8 MB för mediansidan, sparade i tolv månader."],
];

export default function ArchitecturePage() {
  return (
    <PublicFrame kicker="Architecture" title={<>Hela systemet,<br />del för del</>}
      lede="Vad som kör, vad varje del äger, hur en mening blir en meter - och vad ett blad kostar oss i drift."
      anchors={[{ href: "#delar", label: "Delarna" }, { href: "#vagen", label: "Vägen genom systemet" },
                { href: "#lasare", label: "Läsarna" }, { href: "#matt", label: "Hur vi vet" },
                { href: "#kostnad", label: "Vad ett blad kostar" }]}
      aside={
        <div className="pub-keys">
          <div className="pub-key"><div className="n">3</div><div className="l">processer: motor, tjänst, rum</div></div>
          <div className="pub-key"><div className="n">2</div><div className="l">läsare som måste vara överens</div></div>
          <div className="pub-key"><div className="n">0,03 kr</div><div className="l">mediankostnad per blad</div></div>
        </div>
      } wide>

      <section className="pub-sec" id="delar">
        <div className="lp-kicker">Delarna</div>
        <h2>Tre saker, med en gräns mellan sig som hålls</h2>
        <p className="pub-p">
          Motorn vet ingenting om konton, tjänsten vet ingenting om geometri, och rummet räknar aldrig själv.
          Gränsen är inte en smaksak: den är det som gör att en mängd kan läsas om, av någon annan, och bli
          densamma. Motorn kan köras från ett terminalfönster utan att något av det andra finns.
        </p>
        <div className="pub-grid pub-three">
          {LAYERS.map((l) => (
            <div key={l.h} className="pub-card flat">
              <span className="lp-mono pub-tagline">{l.tag}</span>
              <h3>{l.h}</h3>
              <p>{l.p}</p>
              <ul className="pub-list">{l.items.map((i) => <li key={i}>{i}</li>)}</ul>
            </div>
          ))}
        </div>
      </section>

      <section className="pub-sec" id="vagen">
        <div className="lp-kicker">Vägen genom systemet</div>
        <h2>Från uppladdad fil till granskad mängd</h2>
        <ol className="pub-steps">
          <li className="pub-step"><span className="no">01</span><div>
            <h3>Filen läggs undan och ett jobb skapas</h3>
            <p>Tjänsten sparar ritningen, drar credits och lägger jobbet i kö. En skannad PDF avvisas direkt: där finns bara bildpunkter, och på bildpunkter gissar man.</p></div></li>
          <li className="pub-step"><span className="no">02</span><div>
            <h3>Arbetartråden kör motorn, med en tidsbudget</h3>
            <p>Varje steg strömmas ut medan det händer. Går bladet över tidsbudgeten avbryts det och säger det, i stället för att hålla arbetaren för alltid.</p></div></li>
          <li className="pub-step"><span className="no">03</span><div>
            <h3>Motorn skriver artefakter, inte slutsatser</h3>
            <p>Beteckningar, ledare, fästen, topologi, fysiska rör, fronter, mängdrader, bevisgraf, avstämning, determinism, kontaminationsrapport. Ungefär tjugo filer per blad, och mängden är bara en av dem.</p></div></li>
          <li className="pub-step"><span className="no">04</span><div>
            <h3>Granskningen prövar det färdiga</h3>
            <p>Agenter läser resultatet mot bladet, OCR läser texten en andra gång, och synläsaren tittar på sidan. Ingen av dem flyttar en meter - de läser, de mäter inte.</p></div></li>
          <li className="pub-step"><span className="no">05</span><div>
            <h3>Rummet visar mängden med sina belägg</h3>
            <p>Varje rad går att öppna: vilka rör, vilka etiketter, var de slutar och varför. Det tvetydiga står för sig och räknas inte in i tysthet.</p></div></li>
          <li className="pub-step"><span className="no">06</span><div>
            <h3>Rättelser sparas som rättelser</h3>
            <p>Det du ändrar skrivs som en ändring med ditt namn på, bredvid vad läsningen sa. Ingen siffra byts ut bakom ryggen på någon, och rättelserna är det som lär systemet nästa gång.</p></div></li>
        </ol>
      </section>

      <section className="pub-sec" id="lasare">
        <div className="lp-kicker">Läsarna</div>
        <h2>Två modeller, och regeln att de måste vara överens</h2>
        <p className="pub-p">
          En språkmodell får aldrig skapa geometri här. Den får se ett fall som geometrin själv förklarat öppet,
          tillsammans med de kandidater ritningen erbjuder, och välja en av dem. Ett svar som inte står i listan
          kastas, tecken för tecken.
        </p>
        <p className="pub-p">
          Med en enda modell finns ändå en risk kvar: ett öppet fall har flera rimliga svar, och en modell som
          gissar fel förvandlar ett ärligt tvetydigt fall till ett självsäkert fel. Det är den dyraste sortens
          fel i en mängdning, för det ser ut som ett svar. Därför frågas två, oberoende av varandra.
        </p>
        <div className="pub-reasons">
          {READERS.map(([who, what]) => <div key={who}><code>{who}</code><span>{what}</span></div>)}
        </div>
        <p className="pub-p">
          Kostnaden för det är två anrop i stället för ett på de fall som frågas alls, och vinsten är att en
          ensam modell inte kan skriva in ett fel. Går den ena inte att nå tystnar panelen i stället för att bli
          en ensam röst - fallet står kvar öppet, vilket är ett giltigt svar.
        </p>
      </section>

      <section className="pub-sec" id="matt">
        <div className="lp-kicker">Hur vi vet</div>
        <h2>59 blad med känd facit, mätta tre gånger om</h2>
        <p className="pub-p">
          Utvecklingen går i grindar. En ändring körs blint över hela korpusen, körningen fryses med en hash av
          källkoden, och först därefter öppnas referensmängderna. Blir ändringen sämre backas den - fyra av de
          senaste sju gjorde det.
        </p>
        <div className="pub-tablewrap">
          <table className="pub-table">
            <thead><tr><th>Mått</th><th>Vad det jämför</th><th>Var det står</th></tr></thead>
            <tbody>
              <tr><td>Rad mot rad</td><td>Meter per beteckning mot referensen</td><td>facit_metrics.py</td></tr>
              <tr><td>Dragning mot rör</td><td>Varje mätt sträcka mot varje fysiskt rör</td><td>pipe_audit.py</td></tr>
              <tr><td>Sträcka mot sträcka</td><td>Mängdarens egna mätlinjer mot vår geometri, på ritningen</td><td>markup_metrics.py</td></tr>
            </tbody>
          </table>
        </div>
        <p className="pub-p">
          Referensmaterialet ligger utanför källkoden och motorn kan inte nå det. En skanner går igenom motorns
          alla filer före varje körning och vägrar om något av referensens ordförråd har läckt in.
        </p>
      </section>

      <section className="pub-sec" id="kostnad">
        <div className="lp-kicker">Driftkostnad</div>
        <h2>Vad ett blad kostar oss</h2>
        <p className="pub-p">
          Det här är vad vi betalar för att läsa ett blad, inte vad någon betalar oss. Uppmätt på 305 blad, varje
          blad i en egen process, med två läsare inräknade. Kronorna kommer ur antaganden som står utskrivna i
          verktyget; byt ett antagande och talet räknas om.
        </p>
        <div className="pub-tablewrap">
          <table className="pub-table">
            <thead><tr><th>Blad</th><th>Kostnad</th><th>Vad som dominerar</th></tr></thead>
            <tbody>
              <tr><td>Mediansidan</td><td>0,03 kr</td><td>processortid; inga öppna fall att fråga om</td></tr>
              <tr><td>Blad som har öppna fall (39 %)</td><td>0,45 kr</td><td>modellanropen, median 4 frågor</td></tr>
              <tr><td>Snitt över alla blad</td><td>0,31 kr</td><td>dras upp av de täta bladen</td></tr>
              <tr><td>Tätaste bladet som mätts</td><td>6,36 kr</td><td>1,08 miljoner banor och 54 öppna fall</td></tr>
            </tbody>
          </table>
        </div>
        <div className="pub-reasons">
          {COST.map(([what, share, why]) => <div key={what}><code>{what} {share}</code><span>{why}</span></div>)}
        </div>
        <p className="pub-p">
          Processortiden räknas på en maskin med fyra kärnor vid 40 procents nyttjande, vilket ger 1,03 kr per
          kärntimme - tomgången ska bäras av de blad som faktiskt läses. Lagringen är artefakterna i tolv
          månader. Synläsaren är inte med i talen ovan: den kostar omkring 0,90 kr per sida och begärs för hand,
          inte automatiskt.
        </p>
        <p className="pub-p">
          Det betyder att kostnaden i praktiken styrs av hur mycket ritningen lämnar öppet, inte av hur stor den
          är. Ett blad som läsningen kan avgöra själv kostar ören. Varje gräns som skärps så att ett fall kan
          avgöras på ritningens egen geometri gör läsningen både bättre och billigare - det är samma arbete.
        </p>
        <p className="pub-cta">
          <Link className="lp-btn primary lg" to="/hur-det-funkar">Följ en ritning genom läsningen</Link>
          <Link className="lp-btn ghost lg" to="/dokumentation">Läs dokumentationen</Link>
        </p>
      </section>
    </PublicFrame>
  );
}
