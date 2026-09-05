import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "../landing.css";
import LandingScene from "../components/LandingScene";
import { useCountUp, useInView, useScrollProgress } from "../components/lp-motion";

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

function Figure({ to, suffix, decimals, label }: { to: number; suffix?: string; decimals?: number; label: string }) {
  const { ref, seen } = useInView<HTMLDivElement>();
  const n = useCountUp(to, seen);
  return (
    <div ref={ref} className={`lp-fig${seen ? " in" : ""}`}>
      <div className="n">{n.toFixed(decimals ?? 0).replace(".", ",")}{suffix ?? ""}</div>
      <div className="l">{label}</div>
    </div>
  );
}

function Figures() {
  return (
    <section className="lp-wrap">
      <div className="lp-figures">
        <Figure to={15.63} decimals={2} suffix=" m" label="samlad avvikelse mot facit över fyra referensritningar" />
        <Figure to={377} label="sidor i stilbiblioteket, körda sida för sida vid varje ändring" />
        <Figure to={69} label="tester som måste hålla innan en siffra får ändras" />
        <Figure to={0} label="gissningar — identitet endast via riktiga ledarlinjer, aldrig närmaste rör" />
      </div>
    </section>
  );
}

export default function Landing() {
  useEffect(() => {
    document.body.classList.add("lp-dark");
    return () => document.body.classList.remove("lp-dark");
  }, []);
  const [menu, setMenu] = useState(false);
  const scrolled = useScrollProgress();
  return (
    <div className="lp">
      <div className="lp-corners">
        <button className="lp-pill" aria-expanded={menu} aria-label={menu ? "Stäng menyn" : "Öppna menyn"}
          onClick={() => setMenu(!menu)}>
          <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true">
            {menu
              ? <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.5" />
              : <path d="M2 4.5h12M2 11.5h12" stroke="currentColor" strokeWidth="1.5" />}
          </svg>
        </button>
        <span className="lp-logo lp-pill static">
          <svg width="16" height="16" viewBox="0 0 22 22" aria-hidden="true">
            <path d="M3 15 H8 V7 H14 V15 H19" stroke="#6ee7a5" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          VVS Mängdning
        </span>
        <span className="lp-sp" />
        <Link className="lp-pill lp-start" to="/login">
          Starta projekt <span className="plus">+</span>
        </Link>
      </div>

      <div className="lp-rail" aria-hidden="true">
        <div className="lp-rail-fill" style={{ transform: `scaleY(${scrolled})` }} />
      </div>
      <div className="lp-scrollpct" aria-hidden="true">Skroll · {Math.round(scrolled * 100)} %</div>

      {menu && (
        <div className="lp-menu">
          <a href="#hur" onClick={() => setMenu(false)}>Så fungerar det</a>
          <a href="#ror" onClick={() => setMenu(false)}>Rörtyper</a>
          <a href="#belagg" onClick={() => setMenu(false)}>Beläggen</a>
          <Link to="/dokumentation" onClick={() => setMenu(false)}>Dokumentation</Link>
          <Link to="/login" onClick={() => setMenu(false)}>Logga in</Link>
        </div>
      )}

      <header className="lp-stage">
        <div className="lp-stage-art" aria-hidden="true">
          <video className="lp-video" src="/hero.mp4" autoPlay muted loop playsInline preload="auto" />
          <div className="lp-stage-draw"><Drawing /></div>
        </div>
        <h1 className="lp-huge">
          Mängden som<br />ritningen<br />redan säger
        </h1>
        <div className="lp-stage-foot">
          <p className="lp-mono">
            AI-plattform för VVS-mängdning ur ren vektor.<br />
            Ingen OCR i mätvägen — identitet endast via ledarlinjer.
          </p>
          <a className="lp-mono lp-arrow" href="#hur">Se hur det läser <span>→</span></a>
        </div>
      </header>

      <section className="lp-band">
        <p className="lp-band-lede">
          Ladda upp en VVS-ritning. Systemet läser sidans egen beteckningslista, följer varje ledarlinje till det
          rör den pekar på, och mäter i ritningens egen skala.
        </p>
        <div className="lp-screens">
          <figure>
            <div className="lp-screen"><Drawing /></div>
            <figcaption><b>Mängdning</b> beteckningsdriven tolkning direkt på ritningen</figcaption>
          </figure>
          <figure>
            <div className="lp-screen lp-screen-table">
              <div className="lp-row head"><span>Beteckning</span><span>Sträckor</span><span>Totalt</span></div>
              {[["S3-R8-110", "5", "46,39"], ["KV1-X31-16", "3", "17,11"], ["VV1-X31-16", "5", "33,92"],
                ["S3-R8-75", "20", "22,42"], ["S1-P2-110", "1", "9,64"]].map((r) => (
                <div className="lp-row" key={r[0]}><span>{r[0]}</span><span>{r[1]}</span><span>{r[2]}</span></div>
              ))}
              <div className="lp-row sum"><span>Summa</span><span>34</span><span>212,57</span></div>
            </div>
            <figcaption><b>Mängder</b> varje meter med sitt belägg kvar</figcaption>
          </figure>
          <figure>
            <div className="lp-screen lp-screen-check">
              <div className="lp-row head"><span>Beteckning</span><span>Facit</span><span>Vårt</span><span>Avvikelse</span></div>
              {[["KV1-X31-16", "17,40", "17,10", "−0,30"], ["S3-R8-160", "16,30", "16,43", "+0,13"],
                ["VV1-X31-16", "34,10", "33,92", "−0,18"]].map((r) => (
                <div className="lp-row" key={r[0]}><span>{r[0]}</span><span>{r[1]}</span><span>{r[2]}</span><span>{r[3]}</span></div>
              ))}
              <div className="lp-ok">3,69 m samlad avvikelse på 213,70 m</div>
            </div>
            <figcaption><b>Facitkontroll</b> varje körning mäts mot handmängdad ritning</figcaption>
          </figure>
        </div>
      </section>

      <Figures />

      <LandingScene />

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
          <Link to="/dokumentation">Dokumentation</Link>
          <Link to="/login">Logga in</Link>
        </div>
      </footer>
    </div>
  );
}
