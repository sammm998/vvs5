import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { StatusBadge, STAGE_LABELS } from "../components/Status";

export default function DrawingPage() {
  const { id } = useParams();
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  const load = () => api.drawing(id!).then(setD).catch((e) => setErr(e.message));
  useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t); }, [id]);
  if (!d) return <main>{err ? <p className="error">{err}</p> : "Laddar…"}</main>;
  return (
    <main>
      <p><Link to={`/projects/${d.project_id}`}>← Projekt</Link></p>
      <h2>{d.filename}</h2>
      <div className="card row">
        <span>{d.n_pages} sida/sidor · {(d.size_bytes / 1024).toFixed(0)} kB · SHA-256 {d.sha256.slice(0, 12)}…</span>
        <a className="btn" href={api.fileUrl(d.id)} onClick={async (e) => { e.preventDefault(); const b = await api.fetchBlob(api.fileUrl(d.id)); window.open(URL.createObjectURL(b)); }}>Öppna PDF</a>
        <button onClick={async () => { await api.analyze(d.id); load(); }}>Ny analys</button>
      </div>
      <div className="card">
        <h3>Analyser</h3>
        <table>
          <thead><tr><th>Startad</th><th>Status</th><th>Förlopp</th><th>Resultat</th></tr></thead>
          <tbody>
            {d.jobs.map((j: any) => (
              <tr key={j.id}>
                <td>{new Date(j.created_at).toLocaleString("sv-SE")}</td>
                <td><StatusBadge job={j} /></td>
                <td style={{ minWidth: 200 }}>
                  <div className="progress"><div style={{ width: `${Math.round(j.progress * 100)}%` }} /></div>
                  <span className="muted">{STAGE_LABELS[j.stage] || j.stage}</span>
                  {j.error && <div className="error">{j.error.split("\n")[0]}</div>}
                </td>
                <td>{j.status === "COMPLETED" ? <Link to={`/jobs/${j.id}`}>Visa resultat</Link> : <Link to={`/jobs/${j.id}`}>Följ</Link>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
