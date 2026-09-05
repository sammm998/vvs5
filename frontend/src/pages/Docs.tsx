import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

type Sec = { id: string; h: string; body: JSX.Element };

const SECTIONS: Sec[] = [
  {
    id: "principen",
    h: "Principen",
    body: (
      <>
        <p>
          Systemet mängdar rör ur en VVS-ritning genom att läsa ritningens egen vektorgeometri. Det gissar aldrig
          en identitet utifrån närhet. Ett rör får ett namn bara när en riktig ledarlinje går från en beteckning
          till just den geometrin — annars redovisas det som oidentifierat eller tvetydigt.
        </p>
        <p className="pull">Tvetydigt är ett giltigt svar. Fel säkerhet är det inte.</p>
        <p>
          Det betyder att en siffra som står i mängden alltid har ett belägg bakom sig, och att det som saknas
          syns i stället för att fyllas i. En mängdning som ser komplett ut men är gissad är värre än en som säger
          var den inte räcker till.
        </p>
      </>
    ),
  },
  {
    id: "vad-som-lases",
    h: "Vad som läses — och vad som inte gör det",
    body: (
      <>
        <p>
          Indata är en <b>vektor-PDF</b>, alltså en ritning exporterad ur CAD. Varje streck finns då som geometri
          med sin penna, färg och sitt lager. En skannad eller bildbaserad PDF avvisas med besked: där finns inga
          vektorkoder att läsa, bara bildpunkter, och att mäta på bildpunkter vore att gissa.
        </p>
        <p>
          Ingen OCR förekommer i mätvägen. Där texten är ritad som streck i stället för tecken byggs bokstäverna
          tillbaka ur streckens former. OCR används enbart som andrahandsutlåtande för tecken formigenkänningen
          inte kunde namnge, och bara när OCR-ordet stämmer tecken för tecken med det vektorläsningen redan läst.
        </p>
      </>
    ),
  },
  {
    id: "lasningen",
    h: "Läsningen, steg för steg",
    body: (
      <>
        <ol className="steps">
          <li>
            <b>Läser vektorn.</b> Varje väg, dess penna, färg, lager och ordning tas ur PDF:en. Sidramen känns
            igen på sin form och räknas aldrig som rör.
          </li>
          <li>
            <b>Bygger tillbaka texten.</b> Streck grupperas till tecken, tecken till rader. Ett tecken namnges
            genom att dess form jämförs med referensalfabet — det egna inbäddade typsnittet först, när ritningen
            har ett.
          </li>
          <li>
            <b>Läser beteckningslistan.</b> Sidans egen lista säger vilka koder som är system, vilka som är
            material och vilka som är komponenter. Listan skriver komponentfamiljer med platshållare —
            <code>BXXX GOLVBRUNN</code> — så <code>B1</code> och <code>B221BL</code> känns igen som just den
            posten och aldrig som rör.
          </li>
          <li>
            <b>Läser beteckningarna.</b> Grammatiken lärs per ritning:
            <code>SYSTEM+löpnummer – MATERIAL – DIMENSION [/ISOLERING]</code>. Dimensionen kan stå inline eller på
            raden under, understruken; båda formerna viks in i samma identitet.
          </li>
          <li>
            <b>Hittar ledarlinjerna.</b> Från etikettens understrykning, ram eller radbas ut till den geometri
            linjen faktiskt rör, eller till symbolen den slutar i. Linjer som bara är ramstumpar sorteras bort.
          </li>
          <li>
            <b>Väljer rörfamiljer.</b> Geometri grupperas på (lager, pennbredd, färg) — inte på streckmönster,
            eftersom linjetypen på svenska ritningar säger <i>var röret ligger i höjdled</i>, inte vilket system
            det är. Vilka familjer som är rör avgörs av var ritningens egna ledarlinjer slutar.
          </li>
          <li>
            <b>Bygger topologi och äger rören.</b> Identiteten bärs längs nätet från den etikett som pekar på det,
            till den gräns ritningen själv sätter: en dimensionsändring, en systemgräns, en gren utan stöd.
          </li>
          <li>
            <b>Mäter.</b> I skalstockens egen skala, verifierad mot skaltexten. Stigare räknas som antal; deras
            meter kräver en våningshöjd, och den frågar systemet efter i stället för att anta en.
          </li>
        </ol>
      </>
    ),
  },
  {
    id: "agenterna",
    h: "Flera vägar till samma svar",
    body: (
      <>
        <p>
          Efter första läsningen läses sidan om längs andra vägar, som självständiga agenter med var sin logik.
          De ska nå samma svar; där de inte gör det är det en upplysning.
        </p>
        <ul className="defs">
          <li><b>pointing</b> — läser genom det etiketten pekar på: ledarlinjens ände och de märken den slutar i.</li>
          <li><b>writing</b> — läser genom vad ritningen skriver: etiketter som ligger utmed en sträcka i stället för att peka på den.</li>
          <li><b>closure</b> — läser genom nätets slutenhet: en sträcka som bara kan höra till en identitet därför att allt annat runt den redan är namngivet.</li>
        </ul>
        <p>
          Sedan en <b>korsläsning</b> som ställer svaren mot varandra, och en <b>granskning</b> som listar varje
          sträcka utan namn och varje etikett som inte nådde ett rör, med skäl. En andra väg får lägga till det
          den första missade — men aldrig döpa om något den första redan avgjort.
        </p>
        <p className="note">
          En fjärde väg, som lät en ledarlinje som stannat strax före ett stråk nå fram ändå, byggdes och togs
          bort igen: den valde fel linje ur ett knippe parallella rör och sexdubblade felet på referensritning A.
          Vägar som inte håller finns dokumenterade i <code>docs/FLERVAGSANALYS.md</code> med sin uppmätta kostnad.
        </p>
      </>
    ),
  },
  {
    id: "vagrar",
    h: "Reglerna som vägrar",
    body: (
      <>
        <p>Det mesta av arbetet ligger i att inte mäta fel saker. Varje regel är mätt fram, inte antagen.</p>
        <ul className="defs">
          <li>
            <b>Ritade föremål.</b> Ett rör ritas som en linje i mitten; en radiator eller en luftvärmare ritas som
            sina två långsidor. Två linjer en läsare ska skilja åt kan inte ritas närmare än ungefär en millimeter
            papper — ett stråk som skuggas hela vägen av sin egen familj därifrån är en kontur, inte ett rör.
          </li>
          <li>
            <b>Dubbelritat.</b> Samma linje ritad två gånger på samma penna är ett rör, inte två. På vissa ark är
            12–28 % av geometrin dubbelritad.
          </li>
          <li>
            <b>Etiketterna måste nå fram.</b> Saknar de accepterade familjerna lagernamn och ritningens egna
            rörbeteckningar ändå inte når dem, är det fel geometri som accepterats — hade det varit rören hade
            etiketterna hittat dem.
          </li>
          <li>
            <b>Identitet som rinner för långt.</b> En identitet får löpa vidare genom en korsning, men bara inom
            räckhåll för vad etiketterna själva avgränsar.
          </li>
          <li>
            <b>Knippeetiketten.</b> Där en etikett namnger fler system än ritningen ritar linjer redovisas
            sträckan som delad — längden går inte att fördela utan att hitta på en regel, och riktningen är inte
            konstant mellan ritningar.
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "rattelser",
    h: "Rättelser, och vad de får lära ut",
    body: (
      <>
        <p>
          Fem saker går att ändra på en färdig läsning: rita ett rör motorn inte såg, förlänga ett förbi där det
          slutade, sudda det som mätts men inte är rör, flytta meter mellan beteckningar, eller sätta längden för
          hand. Rättelser läggs <i>ovanpå</i> läsningen — varje rad behåller motorns egen siffra, så det syns
          alltid vad som lästes och vad som ändrades.
        </p>
        <p>
          Vad en rättelse får lära ut är medvetet smalt. En läxa får bara avgöra ett fall som motorn själv kallat
          tvetydigt, till förmån för det svar en människa gav <i>i samma situation</i>. Den får aldrig skapa en
          sträcka, aldrig namnge geometri ingen ledarlinje nådde, aldrig röra något motorn är säker på, och aldrig
          erbjuda ett svar ritningens egna kandidater inte innehåller.
        </p>
        <p>
          Samma situation är en exakt träff, inte ett likhetsmått: pennan som geometrin är ritad med, skälet
          motorn gav upp, och beteckningens form med siffrorna borttagna. En situation som besvarats på två olika
          sätt lär ut ingenting — oenigheten är fyndet. Och förslag är förslag: mängden flyttar sig först när en
          människa godtar ett, och då som en rättelse i registret.
        </p>
      </>
    ),
  },
  {
    id: "belagg",
    h: "Beläggen",
    body: (
      <>
        <p>
          Varje mätt sträcka går att spåra bakåt. <b>Varför?</b> på en sträcka visar kedjan: beteckningen och dess
          källa, ledarlinjen och dess vägar i PDF:en, kontaktpunkten, de primitiver identiteten bars över, och
          gränsen som stoppade den.
        </p>
        <p>
          Varje körning skriver 29 artefakter: rörgeometri, topologi, fysiska rör, mängder, olösta fall,
          evidensgraf, korsläsning, granskning, avstämning, determinism, kontaminationsrapport, prestandarapport
          och fyra överlägg som PDF. Export finns som Excel, CSV, JSON, rapport och markerad PDF.
        </p>
      </>
    ),
  },
  {
    id: "validering",
    h: "Hur det valideras",
    body: (
      <>
        <p>Tre nivåer, och de körs om vid varje ändring som kan röra en siffra.</p>
        <ul className="defs">
          <li>
            <b>Facit.</b> Fyra ritningar handmängdade av en människa, med längd per beteckning. Systemet körs
            blint — hela vägen genom API:t som en användare gör det — och poängsätts först efteråt.
          </li>
          <li>
            <b>Stilbiblioteket.</b> Varje sida i varje ritning från elva projekterande kontor körs och jämförs
            mot förra körningen, så att en förbättring på ett ark inte tyst förstör ett annat.
          </li>
          <li>
            <b>Annoterade ark.</b> Handmarkerade masker per beteckning på fler ark, som oberoende svar på om
            rätt rör hittades på rätt plats.
          </li>
        </ul>
        <p className="note">
          Facit och annoteringar ligger utanför koden och läses aldrig av motorn. En kontaminationskontroll körs
          vid varje analys och intygar att produktionspaketet inte importerar valideringsdata.
        </p>
      </>
    ),
  },
  {
    id: "granser",
    h: "Vad systemet inte gör",
    body: (
      <>
        <ul className="defs">
          <li>Läser inte skannade ritningar. Utan vektorkoder finns inget att mäta.</li>
          <li>Antar ingen våningshöjd. Stigare räknas som antal tills du anger en höjd.</li>
          <li>Fördelar inte längden i en delad sträcka mellan systemen som delar den.</li>
          <li>Namnger inte geometri utifrån närhet, hur nära den än ligger.</li>
          <li>Låter inte en rättelse på en ritning bli en gissning på en annan.</li>
        </ul>
      </>
    ),
  },
];

export default function Docs() {
  const [active, setActive] = useState(SECTIONS[0].id);
  useEffect(() => {
    document.body.classList.add("lp-dark");
    return () => document.body.classList.remove("lp-dark");
  }, []);
  useEffect(() => {
    const io = new IntersectionObserver(
      (es) => es.forEach((e) => e.isIntersecting && setActive(e.target.id)),
      { rootMargin: "-20% 0px -70% 0px" },
    );
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) io.observe(el);
    });
    return () => io.disconnect();
  }, []);
  const nav = useMemo(() => SECTIONS.map((s) => ({ id: s.id, h: s.h })), []);
  return (
    <div className="lp docs">
      <div className="lp-corners">
        <Link className="lp-pill" to="/">← Tillbaka</Link>
        <span className="lp-logo lp-pill static">Dokumentation</span>
        <span className="lp-sp" />
        <Link className="lp-pill lp-start" to="/login">Starta projekt <span className="plus">+</span></Link>
      </div>

      <header className="docs-head">
        <p className="lp-mono">Dokumentation</p>
        <h1>Hur systemet läser en ritning</h1>
        <p className="docs-lede">
          Vad som läses, i vilken ordning, vad som får bli en siffra och vad som aldrig får det.
        </p>
      </header>

      <div className="docs-body">
        <nav className="docs-nav">
          {nav.map((n) => (
            <a key={n.id} href={`#${n.id}`} className={active === n.id ? "on" : ""}>{n.h}</a>
          ))}
        </nav>
        <main>
          {SECTIONS.map((s) => (
            <section key={s.id} id={s.id} className="docs-sec">
              <h2>{s.h}</h2>
              {s.body}
            </section>
          ))}
          <p className="docs-end">
            Frågor som inte besvaras här hör hemma i <code>docs/</code> i källkoden — där ligger rörtyperna,
            flervägsanalysen och körningarna över hela stilbiblioteket, med siffror.
          </p>
        </main>
      </div>
    </div>
  );
}
