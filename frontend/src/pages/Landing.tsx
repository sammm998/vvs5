import { useEffect } from "react";
import { Link } from "react-router-dom";
import "../landing.css";

/* The drawing in the hero is the product's own subject: a dash-dot waste run with a branch, two labels on
   leaders, and the marks the engine puts back on the paper. It draws itself in once, then the labels land. */
function Drawing() {
  return (
    <svg viewBox="0 0 1040 380" role="img" aria-label="Planritning där rören markerats och mätts">
      <defs>
        <linearGradient id="lpFade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#6ee7a5" stopOpacity="0.95" />
          <stop offset="1" stopColor="#6ee7a5" stopOpacity="0.55" />
        </linearGradient>
        <clipPath id="lpWipe" clipPathUnits="userSpaceOnUse">
          <rect className="lp-wipe" x="0" y="0" width="1040" height="380" />
        </clipPath>
      </defs>

      {/* the building, drawn faintly: this is what the engine must not measure */}
      <g stroke="#3a4049" strokeWidth="1.5" fill="none">
        <path d="M70 60 H620 V320 H70 Z" />
        <path d="M320 60 V320 M70 200 H320 M470 200 H620" />
        <path d="M660 60 H970 V190 H660 Z M660 230 H970 V320 H660 Z" />
      </g>
      <g stroke="#262b33" strokeWidth="1.1" fill="none">
        {[110, 150, 250, 290].map((y) => (
          <path key={y} d={`M86 ${y} H304`} />
        ))}
      </g>

      {/* the pipes, in the drawing's own dash-dot */}
      <g fill="none" strokeWidth="3.6" strokeLinecap="butt" clipPath="url(#lpWipe)">
        <path d="M120 260 H430 V140 H590 V96 H900" stroke="url(#lpFade)" strokeDasharray="20 7 3.5 7" />
        <path d="M430 260 H760 V236" stroke="#60a5fa" strokeOpacity="0.85" strokeDasharray="20 7 3.5 7" />
      </g>

      {/* connection circles where the runs stop */}
      <g className="lp-pop" fill="#07080a" stroke="#6ee7a5" strokeWidth="2.2">
        <circle cx="120" cy="260" r="5.5" />
        <circle cx="900" cy="96" r="5.5" />
      </g>
      <g className="lp-pop" fill="#07080a" stroke="#60a5fa" strokeWidth="2.2">
        <circle cx="760" cy="236" r="5.5" />
      </g>

      {/* labels on their leaders, the way the sheet writes them */}
      <g className="lp-pop" style={{ animationDelay: "1.65s" }}>
        <path d="M470 96 L560 100" stroke="#6ee7a5" strokeOpacity="0.5" strokeWidth="1.2" fill="none" />
        <path d="M372 74 H470" stroke="#6ee7a5" strokeOpacity="0.5" strokeWidth="1.2" fill="none" />
        <text x="372" y="66" fill="#f4f5f7" fontSize="16" fontFamily="ui-monospace, SFMono-Regular, monospace">
          S1-P5-110
        </text>
        <text x="372" y="92" fill="#8b929e" fontSize="14" fontFamily="ui-monospace, SFMono-Regular, monospace">
          24,8 m
        </text>
      </g>
      <g className="lp-pop" style={{ animationDelay: "1.85s" }}>
        <path d="M520 196 L600 258" stroke="#60a5fa" strokeOpacity="0.5" strokeWidth="1.2" fill="none" />
        <path d="M418 196 H520" stroke="#60a5fa" strokeOpacity="0.5" strokeWidth="1.2" fill="none" />
        <text x="418" y="188" fill="#f4f5f7" fontSize="16" fontFamily="ui-monospace, SFMono-Regular, monospace">
          KV1-X7-32
        </text>
        <text x="418" y="214" fill="#8b929e" fontSize="14" fontFamily="ui-monospace, SFMono-Regular, monospace">
          11,4 m
        </text>
      </g>

      {/* one run the drawing does not name: shown, never counted */}
      <g className="lp-pop" style={{ animationDelay: "2.05s" }}>
        <path d="M690 290 H950" stroke="#565d6a" strokeWidth="3.2" strokeDasharray="18 6 3 6" fill="none" />
        <text x="690" y="280" fill="#6a7280" fontSize="13.5" fontFamily="ui-monospace, SFMono-Regular, monospace">
          onämnd — redovisas, mäts inte
        </text>
      </g>
    </svg>
  );
}

function LineSample({ color, dash }: { color: string; dash: string }) {
  return (
    <svg width="104" height="12" viewBox="0 0 104 12" aria-hidden="true">
      <path d="M2 6 H102" stroke={color} strokeWidth="2.6" strokeDasharray={dash} strokeLinecap="round" fill="none" />
    </svg>
  );
}

const LINES: { code: string; name: string; line: string; color: string; dash: string }[] = [
  { code: "KV / VV / VVC", name: "Tappkall-, tappvarm- och cirkulationsvatten", line: "Heldragen, över golv", color: "#6ee7a5", dash: "" },
  { code: "S", name: "Spillvatten — självfall, ofta gjutjärn i stam och PP liggande", line: "Streckad i eller under golv", color: "#f0abfc", dash: "14 6" },
  { code: "D / DR", name: "Dagvatten och dränering", line: "Streckad, grövre dimensioner", color: "#fcd34d", dash: "14 6" },
  { code: "VS / VP", name: "Värme sekundär och primär, fram- och returledning", line: "Punktstreckad under tak", color: "#60a5fa", dash: "16 5 3 5" },
  { code: "KB / KM", name: "Köldbärare och kylsystem", line: "Punktstreckad, egen penna", color: "#67e8f9", dash: "16 5 3 5" },
  { code: "SP / G / TA", name: "Sprinkler, gas och tryckluft", line: "Egen linjetyp per system", color: "#fb923c", dash: "20 5 3 5 3 5" },
];

export default function Landing() {
  useEffect(() => {
    document.body.classList.add("lp-dark");
    return () => document.body.classList.remove("lp-dark");
  }, []);
  return (
    <div className="lp">
      <nav className="lp-nav">
        <span className="lp-logo">
          <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
            <path d="M3 15 H8 V7 H14 V15 H19" stroke="#6ee7a5" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="3" cy="15" r="2" fill="#6ee7a5" />
            <circle cx="19" cy="15" r="2" fill="#6ee7a5" />
          </svg>
          VVS Mängdning
        </span>
        <span className="lp-links">
          <a href="#hur">Så fungerar det</a>
          <a href="#ror">Rörtyper</a>
          <a href="#belagg">Beläggen</a>
        </span>
        <span className="lp-sp" />
        <Link className="lp-btn ghost" to="/login">
          Logga in
        </Link>
      </nav>

      <header className="lp-hero lp-wrap">
        <span className="lp-eyebrow lp-rise">
          <span className="dot" />
          Läser vektorn i PDF:en — ingen OCR i mätvägen
        </span>
        <h1 className="lp-rise d1">
          Mängda rören ur ritningen.
          <br />
          <span className="soft">Inte ur en gissning.</span>
        </h1>
        <p className="lp-lede lp-rise d2">
          Ladda upp en VVS-ritning. Systemet läser sidans egen beteckningslista, följer varje ledarlinje till
          det rör den pekar på, och mäter i ritningens egen skala. Det som ritningen inte säger blir aldrig en
          siffra — det blir en fråga.
        </p>
        <div className="lp-cta lp-rise d3">
          <Link className="lp-btn primary lg" to="/login">
            Kom igång
          </Link>
          <a className="lp-btn ghost lg" href="#hur">
            Se hur det läser
          </a>
        </div>
        <p className="lp-under lp-rise d3">Svenska ritningar · DWG-exporterad PDF · svar på minuter</p>

        <div className="lp-shot lp-rise d4">
          <div className="lp-shot-inner">
            <div className="lp-shot-bar">
              <span>V-50-1-A0122 · Plan 1 · Skala 1:50 verifierad mot skalstocken</span>
              <span className="lp-tag">4 system · 12 rörfamiljer</span>
            </div>
            <Drawing />
          </div>
        </div>
      </header>

      <section className="lp-wrap">
        <div className="lp-figures">
          <div>
            <div className="n">15,6 m</div>
            <div className="l">samlad avvikelse mot facit över fyra referensritningar</div>
          </div>
          <div>
            <div className="n">215</div>
            <div className="l">sidor i stilbiblioteket, körda sida för sida vid varje ändring</div>
          </div>
          <div>
            <div className="n">100 %</div>
            <div className="l">av det markerade rörnätet ägt på tre av fyra referensritningar</div>
          </div>
          <div>
            <div className="n">0</div>
            <div className="l">gissningar — identitet endast via riktiga ledarlinjer, aldrig närmaste rör</div>
          </div>
        </div>
      </section>

      <section className="lp-sec lp-wrap" id="hur">
        <div className="lp-sec-head">
          <div className="lp-kicker">Så fungerar det</div>
          <h2>Ritningen får berätta själv</h2>
          <p>
            Ingen mall, inget lagerantagande, ingen inlärd ritningsstil. Varje sida analyseras på sina egna
            villkor — och läses sedan om längs andra vägar för att se om svaren håller.
          </p>
        </div>
        <div className="lp-steps">
          {[
            ["01", "Läser vektorn", "Varje streck, dess penna, färg och lager tas direkt ur PDF:en. Text som ritats som streck byggs tillbaka till bokstäver."],
            ["02", "Hittar beteckningslistan", "Sidans egen lista uppe till höger säger vilka koder som är system och vilka som är objekt. Ritningens ordbok, inte vår."],
            ["03", "Följer ledarlinjerna", "Från etikettens understrykning eller ram till den geometri linjen faktiskt rör — eller symbolen den slutar i."],
            ["04", "Mäter och granskar", "I skalstockens egen skala. Sedan en granskning som listar varje rör och varje etikett som inte nåddes, med skäl."],
          ].map(([no, h, p]) => (
            <div className="lp-step" key={no}>
              <div className="no">{no}</div>
              <h3>{h}</h3>
              <p>{p}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="lp-sec lp-wrap" id="ror">
        <div className="lp-sec-head">
          <div className="lp-kicker">Rörtyper</div>
          <h2>Alla system på sidan, var för sig</h2>
          <p>
            Svensk ritstandard låter linjetypen berätta var röret ligger och beteckningen vilket system det är.
            Systemet läser båda — och håller isär tappvatten, spillvatten, värme och kyla i mängden.
          </p>
        </div>
        <div className="lp-legend">
          <table>
            <thead>
              <tr>
                <th>Linje</th>
                <th>Beteckning</th>
                <th>System och hur det ritas</th>
              </tr>
            </thead>
            <tbody>
              {LINES.map((l) => (
                <tr key={l.code}>
                  <td className="line">
                    <LineSample color={l.color} dash={l.dash} />
                  </td>
                  <td className="code">{l.code}</td>
                  <td>
                    {l.name} — <span style={{ color: "var(--lp-faint)" }}>{l.line}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="lp-under" style={{ marginTop: 16 }}>
          Linjetyperna följer svensk praxis (över golv heldragen, i eller under golv streckad, under tak
          punktstreckad). Men avgörandet tas alltid mot sidans egen beteckningslista — det är därför andra
          kontors stilar också går att läsa.
        </p>
      </section>

      <section className="lp-sec lp-wrap" id="belagg">
        <div className="lp-sec-head">
          <div className="lp-kicker">Beläggen</div>
          <h2>Varje meter går att spåra tillbaka</h2>
          <p>Klicka på en rad i mängden och se exakt vilken etikett, vilken ledarlinje och vilka streck som gav den.</p>
        </div>
        <div className="lp-grid">
          {[
            ["Bevis per rad", "Etikett, ledarlinje, kontaktpunkt och varje streck som räknades — med sidkoordinater."],
            ["Flera läsningar", "Sidan läses om längs vägar med andra bevis. Där de säger emot varandra lämnar röret mängden."],
            ["Granskningslista", "Rör ingen väg namngav och etiketter ingen väg placerade, var och en med sitt skäl."],
            ["Skalan verifierad", "Utskriven skala kontrolleras mot skalstocken på pappret innan en enda meter räknas."],
            ["Markerad PDF", "Samma ritning tillbaka med varje rör färgat efter identitet och det onämnda i grått."],
            ["Excel och CSV", "Mängden ut i det format kalkylen redan använder, med beläggen kvar i filen."],
          ].map(([h, p]) => (
            <div className="lp-card" key={h}>
              <div className="ic">
                <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
                  <path d="M2 11 L6 4 L10 9 L14 3" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <h3>{h}</h3>
              <p>{p}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="lp-sec lp-wrap">
        <div className="lp-quote">
          <p>
            “Tvetydigt är ett giltigt svar. Fel säkerhet är det inte. Där ritningen inte säger vilket rör en
            etikett menar får du frågan — inte en siffra som ser rätt ut.”
          </p>
          <p className="who">Principen hela motorn är byggd kring</p>
        </div>
      </section>

      <section className="lp-close lp-wrap">
        <h2>Ladda upp en ritning och se vad den säger</h2>
        <p>Ta en sida du redan mängdat för hand. Jämför. Det är den enda rimliga första körningen.</p>
        <div className="lp-cta">
          <Link className="lp-btn primary lg" to="/login">
            Kom igång
          </Link>
        </div>
      </section>

      <footer className="lp-wrap">
        <div className="lp-foot">
          <span className="lp-logo" style={{ fontSize: 14 }}>
            <svg width="18" height="18" viewBox="0 0 22 22" aria-hidden="true">
              <path d="M3 15 H8 V7 H14 V15 H19" stroke="#5b616c" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            VVS Mängdning
          </span>
          <span className="sp" />
          <a href="#hur">Så fungerar det</a>
          <a href="#ror">Rörtyper</a>
          <Link to="/login">Logga in</Link>
        </div>
      </footer>
    </div>
  );
}
