import { Link } from "react-router-dom";
import PublicFrame from "../components/PublicFrame";
import { MODULES } from "../learn";

/* Utbildning: akademin utåt. Modulerna och delmomenten är samma som i tjänsten (learn.ts), så sidan kan aldrig
 * lova en kurs som inte finns. Att gå dem kräver ett konto - delmomenten sparas per person. */

export default function EducationPage() {
  const lessons = MODULES.reduce((n, m) => n + m.lessons.length, 0);
  const minutes = MODULES.reduce((n, m) => n + m.lessons.reduce((k, l) => k + l.minutes, 0), 0);
  return (
    <PublicFrame kicker="Utbildning" title="Lär dig läsa ritningen - inte bara mängda den"
      lede={`${MODULES.length} moduler, ${lessons} delmoment, ungefär ${Math.round(minutes / 60)} timmar. Från vad ett VVS-system är till att mängda ett övningsblad själv och få det rättat.`}>
      <section className="pub-sec">
        <div className="pub-grid pub-three">
          <div className="pub-card flat"><h3>Medan läsningen kör</h3><p>En läsning tar ett par minuter. Delmomenten är gjorda för att gå under tiden, och sparas så att nästa ritning fortsätter där den förra slutade.</p></div>
          <div className="pub-card flat"><h3>På riktiga blad</h3><p>Övningarna använder samma slags ritningar som tjänsten läser: förklaringslistor, beteckningar, ledare, streckade rör. Det du lär dig är det du sedan granskar.</p></div>
          <div className="pub-card flat"><h3>Rättat, inte betygsatt</h3><p>Mängdar du ett övningsblad får du se vad du missade och varför - samma belägg som motorn visar för sina egna meter.</p></div>
        </div>
      </section>

      <section className="pub-sec">
        <div className="lp-kicker">Kursplanen</div>
        <h2>Modulerna, i den ordning de bygger på varandra</h2>
        <ol className="pub-modules">
          {MODULES.map((m, i) => (
            <li key={m.id} className="pub-module">
              <div className="pub-module-head">
                <span className="no">{String(i + 1).padStart(2, "0")}</span>
                <div>
                  <h3>{m.title}</h3>
                  <p>{m.blurb}</p>
                </div>
                <span className="lp-mono pub-tagline">{m.lessons.length} delmoment · {m.lessons.reduce((k, l) => k + l.minutes, 0)} min</span>
              </div>
              <ul className="pub-lessons">
                {m.lessons.map((l) => <li key={l.id}><span>{l.title}</span><span className="lp-mono">{l.minutes} min</span></li>)}
              </ul>
            </li>
          ))}
        </ol>
      </section>

      <section className="pub-sec">
        <div className="lp-kicker">För kontor</div>
        <h2>Samma kurs för hela laget</h2>
        <p className="pub-p">
          Varje inloggning på ett konto har sin egen kursgång och sina egna belöningar. Den som driver kontoret ser
          vilka moment som gåtts. Vill ni ha ett upplägg med handledning på egna ritningar - hör av er.
        </p>
        <p className="pub-cta">
          <Link className="lp-btn primary lg" to="/login">Börja med första modulen</Link>
          <Link className="lp-btn ghost lg" to="/kontakt">Utbildning för kontoret</Link>
        </p>
      </section>
    </PublicFrame>
  );
}
