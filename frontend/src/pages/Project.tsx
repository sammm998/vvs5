import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { StatusBadge } from "../components/Status";

export default function ProjectPage() {
  const { id } = useParams();
  const [project, setProject] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const load = () => api.project(id!).then(setProject).catch((e) => setErr(e.message));
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, [id]);
  const upload = async () => {
    const f = fileRef.current?.files?.[0]; if (!f) return;
    setBusy(true); setErr("");
    try { await api.upload(id!, f); fileRef.current!.value = ""; load(); } catch (ex: any) { setErr(ex.message); } finally { setBusy(false); }
  };
  if (!project) return <main>{err ? <p className="error">{err}</p> : "Laddar…"}</main>;
  return (
    <main>
      <p><Link to="/projekt">← Projekt</Link></p>
      <h2>{project.name}</h2>
      <p className="muted">{project.description}</p>
      <div className="card row">
        <input type="file" accept="application/pdf" ref={fileRef} />
        <button onClick={upload} disabled={busy}>{busy ? "Laddar upp…" : "Ladda upp VVS-PDF"}</button>
        {err && <span className="error">{err}</span>}
      </div>
      <div className="card">
        <table>
          <thead><tr><th>Ritning</th><th>Sidor</th><th>Storlek</th><th>Senaste analys</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {project.drawings.map((d: any) => (
              <tr key={d.id}>
                <td><Link to={`/drawings/${d.id}`}>{d.filename}</Link></td>
                <td>{d.n_pages}</td>
                <td>{(d.size_bytes / 1024).toFixed(0)} kB</td>
                <td>{d.latest_job ? <Link to={`/jobs/${d.latest_job.id}`}>{new Date(d.latest_job.created_at).toLocaleString("sv-SE")}</Link> : <span className="muted">–</span>}</td>
                <td>{d.latest_job ? <StatusBadge job={d.latest_job} /> : <span className="muted">Ej analyserad</span>}</td>
                <td><button className="small" onClick={async () => { const j = await api.analyze(d.id); window.location.href = `/jobs/${j.id}`; }}>Analysera</button></td>
              </tr>
            ))}
            {project.drawings.length === 0 && <tr><td colSpan={6} className="muted">Inga ritningar ännu.</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
