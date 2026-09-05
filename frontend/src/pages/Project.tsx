import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, fileSize } from "../api";
import { StatusBadge } from "../components/Status";

const DATE = new Intl.DateTimeFormat("sv-SE", { day: "2-digit", month: "short", year: "numeric" });

export default function ProjectPage() {
  const { id } = useParams();
  const [project, setProject] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [picked, setPicked] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const load = () => api.project(id!).then(setProject).catch((e) => setErr(e.message));
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, [id]);
  const upload = async () => {
    const f = fileRef.current?.files?.[0]; if (!f) return;
    setBusy(true); setErr("");
    try { await api.upload(id!, f); fileRef.current!.value = ""; setPicked(""); load(); } catch (ex: any) { setErr(ex.message); } finally { setBusy(false); }
  };
  if (!project) return <main>{err ? <p className="error">{err}</p> : "Laddar…"}</main>;
  return (
    <main>
      <p className="crumb"><Link to="/projekt">Projekt</Link> / {project.name}</p>
      <div className="head">
        <div>
          <h1>{project.name}</h1>
          <p className="lead">{project.description || "Ritningar i projektet"}</p>
        </div>
        <div className="row">
          <input type="file" accept="application/pdf" ref={fileRef} id="pdf" className="file"
            onChange={(e) => setPicked(e.target.files?.[0]?.name ?? "")} />
          <label className="pick" htmlFor="pdf">{picked || "Välj PDF…"}</label>
          <button onClick={upload} disabled={busy || !picked}>{busy ? "Laddar upp…" : "Ladda upp"}</button>
        </div>
      </div>
      {err && <p className="error" style={{ marginTop: 18 }}>{err}</p>}

      <div className="rule" />
      <div className="list">
        {project.drawings.map((d: any, i: number) => (
          <article className="item" key={d.id}>
            <div className="no">{String(i + 1).padStart(2, "0")}</div>
            <div>
              <Link className="ttl" to={`/drawings/${d.id}`}>{d.filename.replace(/\.pdf$/i, "")}</Link>
              <div className="sub">
                {d.n_pages} {d.n_pages === 1 ? "sida" : "sidor"} · {fileSize(d.size_bytes)}
                {d.latest_job && <> · senast <Link to={`/jobs/${d.latest_job.id}`}>{DATE.format(new Date(d.latest_job.created_at))}</Link></>}
              </div>
            </div>
            <div className="meta">
              {d.latest_job ? <StatusBadge job={d.latest_job} /> : <span className="badge">Ej analyserad</span>}
              <button className="secondary small" onClick={async () => { const j = await api.analyze(d.id); window.location.href = `/jobs/${j.id}`; }}>Analysera</button>
            </div>
          </article>
        ))}
        {project.drawings.length === 0 && <div className="empty">Inga ritningar ännu — ladda upp den första.</div>}
      </div>
    </main>
  );
}
