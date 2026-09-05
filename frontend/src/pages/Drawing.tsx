import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, fileSize } from "../api";
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
      <p className="crumb"><Link to={`/projects/${d.project_id}`}>Projekt</Link> / Ritning</p>
      <div className="head">
        <div>
          <h1>{d.filename.replace(/\.pdf$/i, "")}</h1>
          <p className="lead">
            {d.n_pages} {d.n_pages === 1 ? "sida" : "sidor"} · {fileSize(d.size_bytes)} · SHA-256 {d.sha256.slice(0, 12)}…
          </p>
        </div>
        <div className="row">
          <button className="secondary" onClick={async () => { const b = await api.fetchBlob(api.fileUrl(d.id)); window.open(URL.createObjectURL(b)); }}>Öppna PDF</button>
          <button onClick={async () => { await api.analyze(d.id); load(); }}>Ny analys</button>
        </div>
      </div>

      <div className="rule" />
      <div className="list">
        {d.jobs.map((j: any, i: number) => (
          <article className="item" key={j.id}>
            <div className="no">{String(i + 1).padStart(2, "0")}</div>
            <div>
              <Link className="ttl" to={`/jobs/${j.id}`} style={{ fontSize: 19 }}>
                {new Date(j.created_at).toLocaleString("sv-SE")}
              </Link>
              <div className="sub">{STAGE_LABELS[j.stage] || j.stage}</div>
              {j.status !== "COMPLETED" && j.status !== "FAILED" && (
                <div className="progress" style={{ maxWidth: 280, marginTop: 10 }}>
                  <div style={{ width: `${Math.round(j.progress * 100)}%` }} />
                </div>
              )}
              {j.error && <div className="error" style={{ marginTop: 6 }}>{j.error.split("\n")[0]}</div>}
            </div>
            <div className="meta">
              <StatusBadge job={j} />
              <Link className="when" to={`/jobs/${j.id}`}>{j.status === "COMPLETED" ? "Visa resultat →" : "Följ →"}</Link>
            </div>
          </article>
        ))}
        {d.jobs.length === 0 && <div className="empty">Ingen analys körd ännu.</div>}
      </div>
    </main>
  );
}
