import { Link, useParams } from "react-router-dom";
import PublicFrame, { PubSection } from "../components/PublicFrame";
import { MODULES } from "../learn";
import Lecture, { findLesson, findModule, FLAT } from "../components/Lecture";
import { CourseGrid, CourseView, useProgress, courseMinutes } from "../components/Academy";

/* VVS-akademin utåt.
 *
 * Kurserna och föreläsningarna är samma som i tjänsten (learn.ts), så sidan kan aldrig lova en kurs som inte
 * finns - och eftersom varje föreläsning nu har en egen adress går den att läsa, spara och dela utan konto.
 * Det är också det ärligaste sättet att visa vad utbildningen är: man får läsa den, inte bara läsa om den.
 * Kontot behövs för att stegen ska följa med mellan datorer.
 */

const BASE = "/utbildning";

/* ---------- katalogen ---------- */

export default function EducationPage() {
  const prog = useProgress(false);
  const lessons = FLAT.length;
  const minutes = MODULES.reduce((n, m) => n + courseMinutes(m), 0);
  return (
    <PublicFrame
      kicker="VVS-akademin"
      title={<>Lär dig läsa ritningen —<br />inte bara mängda den</>}
      lede="Från vad ett VVS-system är till att mängda ett övningsblad själv och få det rättat. Varje föreläsning har en egen sida, en levande figur och en kontrollfråga."
      anchors={[{ href: "#kurser", label: "Kurserna" }, { href: "#sa", label: "Så är den upplagd" }, { href: "#kontor", label: "För kontor" }]}
      aside={
        <div className="pub-keys">
          <div className="pub-key"><div className="n">{MODULES.length}</div><div className="l">kurser</div></div>
          <div className="pub-key"><div className="n">{lessons}</div><div className="l">föreläsningar</div></div>
          <div className="pub-key"><div className="n">{Math.round(minutes / 60)} h</div><div className="l">sammanlagt</div></div>
        </div>
      }>

      <PubSection id="kurser" kicker="Kursplanen" title={`${MODULES.length} kurser, i den ordning de bygger på varandra`}
        lede="Man läser inte en beteckning innan man vet vad ett system är. Ordningen är innehållets egen — men ingenting är låst, och du kan börja var du vill.">
        <CourseGrid base={BASE} prog={prog} />
      </PubSection>

      <PubSection id="sa" kicker="Så är den upplagd" title="Byggd för att göras, inte bläddras i">
        <div className="pub-grid pub-three">
          <div className="pub-card">
            <span className="no">01</span>
            <h3>En figur som rör sig</h3>
            <p>Varje föreläsning visar det den handlar om som en levande ritning — en ledarlinje som hittar sitt rör, en stigare som blir meter — i stället för att beskriva det i ord.</p>
          </div>
          <div className="pub-card">
            <span className="no">02</span>
            <h3>En kontrollfråga</h3>
            <p>Inte ett prov. En fråga som går att svara fel på, med förklaringen efteråt — för det är den man minns.</p>
          </div>
          <div className="pub-card">
            <span className="no">03</span>
            <h3>Övningar på riktiga blad</h3>
            <p>Samma slags ritningar som tjänsten läser: förklaringslistor, beteckningar, ledare, streckade rör. Ingen övning går att klara genom att gissa på det som ligger närmast.</p>
          </div>
        </div>
      </PubSection>

      <PubSection id="kontor" kicker="För kontor" title="Samma kurs för hela laget"
        lede="Varje inloggning på ett konto har sin egen kursgång och sina egna utmärkelser. Den som driver kontoret ser vilka moment som gåtts.">
        <p className="pub-cta">
          <Link className="lp-btn primary lg" to={`${BASE}/${MODULES[0].id}/${MODULES[0].lessons[0].id}`}>
            Läs första föreläsningen
          </Link>
          <Link className="lp-btn ghost lg" to="/kontakt">Utbildning för kontoret</Link>
        </p>
      </PubSection>
    </PublicFrame>
  );
}

/* ---------- en kurs ---------- */

export function EducationCoursePage() {
  const { modul } = useParams();
  const prog = useProgress(false);
  const found = findModule(modul);
  if (!found) return <NotFound />;
  return (
    <PublicFrame bare>
      <CourseView m={found.module} mi={found.mi} base={BASE} prog={prog} />
    </PublicFrame>
  );
}

/* ---------- en föreläsning ---------- */

export function EducationLessonPage() {
  const { modul, lektion } = useParams();
  const at = findLesson(modul, lektion);
  if (!at) return <NotFound />;
  return (
    <PublicFrame bare>
      <Lecture at={at} base={BASE} locked />
    </PublicFrame>
  );
}

function NotFound() {
  return (
    <PublicFrame kicker="VVS-akademin" title="Den föreläsningen finns inte"
      lede="Adressen pekar på något akademin inte har. Kurserna står kvar där de var.">
      <PubSection tight>
        <p className="pub-cta"><Link className="lp-btn primary lg" to={BASE}>Till kurserna</Link></p>
      </PubSection>
    </PublicFrame>
  );
}
