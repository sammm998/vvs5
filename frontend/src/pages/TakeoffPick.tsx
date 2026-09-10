import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

/* Vilket blad ska mängdas? Projekten och deras ritningar, med den senaste först. */
export default function TakeoffPickPage() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.projects().then(async (ps: any[]) => {
      const out: any[] = [];
      for (const p of ps) {
        const full = await api.project(p.id).catch(() => null);
        (full?.drawings ?? []).forEach((d: any) => out.push({ ...d, project: p.name }));
      }
      setRows(out);
    }).catch((e) => setErr(e.message));
  }, []);
  return (
    <main>
      <p className="crumb">Mängda</p>
      <div className="head">
        <div>
          <h1>Mängda för hand</h1>
          <p className="lead">
            Mät, räkna och markera direkt på ett blad: längd, yta, volym och antal, med egen skala där bladet
            inte har någon. Det ligger vid sidan av läsningen och redovisas för sig.
          </p>
        </div>
      </div>
      <div className="rule" style={{ marginBottom: 20 }} />
      {err && <p className="error">{err}</p>}
      {!rows && <p className="muted">Laddar…</p>}
      {rows && !rows.length && <p className="muted">Ingen ritning uppladdad ännu. Lägg upp en under Projekt.</p>}
      <div className="list">
        {(rows ?? []).map((d) => (
          <article className="item" key={d.id}>
            <div className="no" />
            <div>
              <Link className="ttl" to={`/mangda/${d.id}`} style={{ fontSize: 18 }}>{d.filename.replace(/\.pdf$/i, "")}</Link>
              <div className="sub">{d.project} · {d.n_pages} {d.n_pages === 1 ? "sida" : "sidor"}</div>
            </div>
            <div className="meta"><Link className="when" to={`/mangda/${d.id}`}>Mängda →</Link></div>
          </article>
        ))}
      </div>
    </main>
  );
}
