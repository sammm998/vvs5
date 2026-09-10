import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Accounts, Content, Crm, Experiments, Heatmap, Partners } from "../components/AdminBusiness";
import { Corrections, Learning, Readings, RulesMoved } from "../components/AdminReading";

/* Att driva tjänsten.
 *
 * Sidan är delad i två halvor som aldrig får blandas ihop. Den vänstra handlar om läsningen: vad som lästs, hur
 * det gick, vad kunder rättat och vad rättelserna lärt. Den högra handlar om företaget: konton, planer,
 * partners, provision, innehåll och prov.
 *
 * Ingenting på den här sidan får avgöra hur en ritning läses. Den dagen en rabattsats kan flytta en meter går
 * det inte längre att svara på varför en mängd blev som den blev, och hela systemet står och faller på att den
 * frågan går att besvara.
 */

type Tab = "overblick" | "lasningar" | "rattelser" | "inlarning" | "regler"
  | "konton" | "partners" | "crm" | "innehall" | "prov" | "heatmap";

const TABS: { id: Tab; label: string; group: string }[] = [
  { id: "overblick", label: "Överblick", group: "Läsningen" },
  { id: "lasningar", label: "Läsningar", group: "Läsningen" },
  { id: "rattelser", label: "Rättelser", group: "Läsningen" },
  { id: "inlarning", label: "Inlärning", group: "Läsningen" },
  { id: "regler", label: "Flyttade regler", group: "Läsningen" },
  { id: "konton", label: "Konton", group: "Företaget" },
  { id: "partners", label: "Partners", group: "Företaget" },
  { id: "crm", label: "Kundvård", group: "Företaget" },
  { id: "innehall", label: "Innehåll", group: "Företaget" },
  { id: "prov", label: "A/B-prov", group: "Företaget" },
  { id: "heatmap", label: "Heatmap", group: "Företaget" },
];

const pct = (v: number | null | undefined) =>
  v == null ? "–" : `${(v * 100).toFixed(1).replace(".", ",")} %`;
const num = (v: number | null | undefined, d = 0) =>
  v == null ? "–" : v.toLocaleString("sv-SE", { maximumFractionDigits: d });

function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: string }) {
  return (
    <div className={`adm-stat${tone ? ` ${tone}` : ""}`}>
      <div className="k">{label}</div>
      <div className="v">{value}</div>
      {sub && <div className="s">{sub}</div>}
    </div>
  );
}

/* Kurvan som säger om läsningen blir bättre, inte om marknadsföringen gör det.
 *
 * Två serier i samma bild med avsikt: staplarna är hur mycket som lästs, linjen är hur långt läsningen kom.
 * De rör sig oberoende av varandra, och det är just när de gör det man vill veta om det - en månad med dubbelt
 * så många läsningar och sjunkande täckning är en månad då något gick sönder. */
function Trend({ rows }: { rows: any[] }) {
  const W = 720, H = 190, P = 30;
  if (!rows.length) return <p className="muted">Inga läsningar i perioden.</p>;
  const maxR = Math.max(1, ...rows.map((r) => r.readings));
  const x = (i: number) => P + (i * (W - 2 * P)) / Math.max(1, rows.length - 1);
  const bw = Math.max(2, (W - 2 * P) / rows.length - 2);
  const withCov = rows.map((r, i) => [i, r.coverage] as const).filter(([, c]) => c != null);
  const line = withCov.map(([i, c], k) => `${k ? "L" : "M"}${x(i).toFixed(1)},${(H - P - (c as number) * (H - 2 * P)).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="adm-trend" role="img" aria-label="Läsningar och täckning per dygn">
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1={P} x2={W - P} y1={H - P - f * (H - 2 * P)} y2={H - P - f * (H - 2 * P)} className="grid" />
          <text x={4} y={H - P - f * (H - 2 * P) + 4} className="ax">{Math.round(f * 100)}%</text>
        </g>
      ))}
      {rows.map((r, i) => (
        <g key={r.day}>
          <rect x={x(i) - bw / 2} width={bw} y={H - P - (r.readings / maxR) * (H - 2 * P) * 0.85}
            height={(r.readings / maxR) * (H - 2 * P) * 0.85} className="bar" />
          {r.failed > 0 && (
            <rect x={x(i) - bw / 2} width={bw} y={H - P - (r.failed / maxR) * (H - 2 * P) * 0.85}
              height={(r.failed / maxR) * (H - 2 * P) * 0.85} className="bar bad" />
          )}
        </g>
      ))}
      {line && <path d={line} className="cov" />}
      {withCov.map(([i, c]) => <circle key={i} cx={x(i)} cy={H - P - (c as number) * (H - 2 * P)} r="2.5" className="covdot" />)}
      <text x={P} y={H - 8} className="ax">{rows[0].day}</text>
      <text x={W - P} y={H - 8} textAnchor="end" className="ax">{rows[rows.length - 1].day}</text>
    </svg>
  );
}

function Overview() {
  const [o, setO] = useState<any>(null);
  const [t, setT] = useState<any>(null);
  const [days, setDays] = useState(30);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.adm(`overview?days=${days}`).then(setO).catch((e) => setErr(e.message));
    api.adm(`timeline?days=${Math.max(days, 30)}`).then(setT).catch(() => { /* kurvan är inte livsviktig */ });
  }, [days]);
  if (err) return <p className="error">{err}</p>;
  if (!o) return <p className="muted">Laddar…</p>;
  const r = o.readings, a = o.accounts;
  return (
    <>
      <div className="row" style={{ marginBottom: 14 }}>
        <label>Period
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>7 dygn</option><option value={30}>30 dygn</option><option value={90}>90 dygn</option>
          </select>
        </label>
      </div>
      <div className="adm-stats">
        <Stat label="Läsningar" value={num(r.total)} sub={`${num(r.done)} klara · ${num(r.failed)} misslyckade`}
          tone={r.failed > r.done * 0.1 ? "bad" : ""} />
        <Stat label="Täckning i snitt" value={pct(r.mean_coverage)}
          sub="andel rörnamn på bladet som fick meter" tone={(r.mean_coverage ?? 1) < 0.6 ? "bad" : "good"} />
        <Stat label="Onämnt rör" value={pct(r.mean_unowned_share)} sub="ritat rör som ingen beteckning nådde" />
        <Stat label="Median­tid" value={r.median_seconds ? `${num(r.median_seconds, 1)} s` : "–"} sub="per blad" />
        <Stat label="Konton" value={num(a.total)} sub={`${num(o.users.active)} har läst i perioden`} />
        <Stat label="Månadsintäkt" value={`${num(a.mrr_kr, 0)} kr`} sub="aktiva konton" tone="good" />
        <Stat label="Rättelser" value={num(o.corrections.total)} sub={`av ${num(o.corrections.people)} personer`} />
        <Stat label="Ritningar" value={num(o.drawings)} sub={`${num(o.projects)} projekt`} />
      </div>

      <section className="card" style={{ marginTop: 16 }}>
        <h3 style={{ marginTop: 0 }}>Läsningar och täckning per dygn</h3>
        <p className="muted">
          Staplarna är hur mycket som lästs, den röda delen är det som misslyckades, linjen är hur långt
          läsningen kom. Att staplarna växer säger något om marknadsföringen. Att linjen sjunker säger att
          något gått sönder, och det är den enda av de två som är brådskande.
        </p>
        {t && <Trend rows={t.rows} />}
      </section>

      <div className="adm-two" style={{ marginTop: 16 }}>
        <section className="card">
          <h3 style={{ marginTop: 0 }}>Planer</h3>
          <table className="qty"><tbody>
            {Object.entries(a.by_plan).map(([k, v]: any) => (
              <tr key={k}><td>{k}</td><td className="num">{num(v)}</td></tr>
            ))}
            {!Object.keys(a.by_plan).length && <tr><td className="empty">Inga konton upplagda ännu.</td></tr>}
          </tbody></table>
        </section>
        <section className="card">
          <h3 style={{ marginTop: 0 }}>Rättelser efter slag</h3>
          <table className="qty"><tbody>
            {Object.entries(o.corrections.by_kind).map(([k, v]: any) => (
              <tr key={k}><td>{k}</td><td className="num">{num(v)}</td></tr>
            ))}
            {!Object.keys(o.corrections.by_kind).length && <tr><td className="empty">Ingen har rättat något ännu.</td></tr>}
          </tbody></table>
        </section>
      </div>
    </>
  );
}

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>(() => {
    try { return (localStorage.getItem("vvs.admtab") as Tab) || "overblick"; } catch { return "overblick"; }
  });
  const [role, setRole] = useState<string | null>(null);
  const groups = useMemo(() => {
    const g: Record<string, typeof TABS> = {};
    TABS.forEach((t) => { (g[t.group] ||= []).push(t); });
    return Object.entries(g);
  }, []);

  useEffect(() => { api.myRole().then((r) => setRole(r.role)).catch(() => setRole("member")); }, []);
  const pick = (t: Tab) => { setTab(t); try { localStorage.setItem("vvs.admtab", t); } catch { /* privat läge */ } };

  if (role === null) return <main><p className="muted">Laddar…</p></main>;
  if (role !== "admin") {
    return (
      <main>
        <p className="crumb">Administration</p>
        <h1>Det här är administratörens sidor</h1>
        <p className="lead">
          Ditt konto är {role === "partner" ? "en partner" : "en medlem"}. Partners når sin egen provision under
          Partners; resten kräver administratörsbehörighet.
        </p>
        {role === "partner" && <div style={{ marginTop: 18 }}><Partners /></div>}
      </main>
    );
  }

  return (
    <main className="admin">
      <p className="crumb">Administration</p>
      <div className="head">
        <div>
          <h1>Att driva tjänsten</h1>
          <p className="lead">
            Vänstra halvan är läsningen: vad som lästs, hur det gick och vad kunderna rättat. Högra halvan är
            företaget. Ingenting härifrån avgör hur en ritning läses.
          </p>
        </div>
      </div>

      <div className="adm-tabs">
        {groups.map(([g, items]) => (
          <div key={g} className="grp">
            <span className="lbl">{g}</span>
            {items.map((t) => (
              <button key={t.id} className={tab === t.id ? "on" : ""} onClick={() => pick(t.id)}>{t.label}</button>
            ))}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 16 }}>
        {tab === "overblick" && <Overview />}
        {tab === "lasningar" && <Readings />}
        {tab === "rattelser" && <Corrections />}
        {tab === "inlarning" && <Learning />}
        {tab === "regler" && <RulesMoved />}
        {tab === "konton" && <Accounts />}
        {tab === "partners" && <Partners />}
        {tab === "crm" && <Crm />}
        {tab === "innehall" && <Content />}
        {tab === "prov" && <Experiments />}
        {tab === "heatmap" && <Heatmap />}
      </div>
    </main>
  );
}
