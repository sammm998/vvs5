import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import AgentChat from "../components/AgentChat";
import ProjectAgentChat from "../components/ProjectAgentChat";

/* Agenten som egen sida.
 *
 * Samma två agenter som bor i analysen och i projektet, men nådda från sidmenyn: välj en handling och fråga
 * om hela huset, eller välj ett läst blad och fråga om just det. Sidan äger ingen kunskap själv - den
 * skickar frågan dit beläggen finns. Ett blad som inte är läst går inte att fråga om; det står så i listan. */

const DATE = new Intl.DateTimeFormat("sv-SE", { day: "2-digit", month: "short" });

export default function AgentPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [pid, setPid] = useState<string>("");
  const [project, setProject] = useState<any>(null);
  const [job, setJob] = useState<{ id: string; name: string } | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => { api.projects().then((ps: any[]) => { setProjects(ps); if (ps.length && !pid) setPid(ps[0].id); }).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { if (!pid) return; setProject(null); setJob(null); api.project(pid).then(setProject).catch((e) => setErr(e.message)); }, [pid]);

  const drawings: any[] = project?.drawings ?? [];
  const readable = drawings.filter((d) => d.latest_job?.status === "COMPLETED");

  return (
    <main className="agentpage">
      <p className="crumb">Agent</p>
      <div className="head">
        <div>
          <h1>Fråga agenten</h1>
          <p className="lead">
            Agenten svarar ur det som redan lästs - handlingens blad, mängderna och beläggen bakom dem - och säger
            vilka blad svaret vilar på. Den hittar inte på en siffra: en fråga utan belägg får svaret att beläggen saknas.
          </p>
        </div>
      </div>
      {err && <p className="error">{err}</p>}
      {!projects.length && !err && <p className="muted">Inget projekt ännu. <Link to="/projekt">Lägg upp en handling</Link> så finns det något att fråga om.</p>}
      {projects.length > 0 && (
        <div className="agentgrid">
          <aside className="agentpick">
            <label className="field">
              <span>Handling</span>
              <select value={pid} onChange={(e) => setPid(e.target.value)}>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </label>
            <button className={`agentrow${!job ? " on" : ""}`} onClick={() => setJob(null)}>
              <b>Hela handlingen</b>
              <span className="muted small">{drawings.length} blad · {readable.length} lästa</span>
            </button>
            <div className="org" style={{ margin: "14px 0 6px" }}>Ett blad i taget</div>
            {!project && <p className="muted small">Laddar…</p>}
            {project && !drawings.length && <p className="muted small">Inga blad i handlingen.</p>}
            {drawings.map((d) => {
              const ok = d.latest_job?.status === "COMPLETED";
              return (
                <button key={d.id} className={`agentrow${job?.id === d.latest_job?.id && ok ? " on" : ""}`} disabled={!ok} title={ok ? "" : "Bladet är inte läst än"}
                  onClick={() => ok && setJob({ id: d.latest_job.id, name: (d.filename || "").replace(/\.pdf$/i, "") })}>
                  <b>{(d.filename || "").replace(/\.pdf$/i, "")}</b>
                  <span className="muted small">{ok ? `läst ${DATE.format(new Date(d.latest_job.created_at))}` : d.latest_job ? d.latest_job.status.toLowerCase() : "inte läst"}</span>
                </button>
              );
            })}
          </aside>
          <section className="agentroom">
            <div className="agentwho">
              {job ? <><b>{job.name}</b> <Link to={`/jobs/${job.id}`} className="small">öppna läsningen</Link></> : <><b>{project?.name ?? "…"}</b> {project && <Link to={`/projects/${project.id}/analys`} className="small">öppna projektanalysen</Link>}</>}
            </div>
            {job
              ? <AgentChat key={job.id} jobId={job.id} page={1} selection={{ pipeIds: [], bbox: null }} onHighlight={() => {}} />
              : pid ? <ProjectAgentChat key={pid} projectId={pid} /> : null}
          </section>
        </div>
      )}
    </main>
  );
}
