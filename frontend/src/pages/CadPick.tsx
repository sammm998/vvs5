import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import DrawingUpload from "../components/DrawingUpload";

/* Vilken handling ska öppnas i CAD-rummet? Ritningarna med hur många frågor som står öppna på var och en -
 * och en väg att lägga upp en ny, för den som står här och har filen framför sig. */
export default function CadPickPage() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [err, setErr] = useState("");
  const nav = useNavigate();
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    api.projects().then(async (ps: any[]) => {
      const out: any[] = [];
      for (const p of ps) {
        const full = await api.project(p.id).catch(() => null);
        for (const d of full?.drawings ?? []) {
          // hur långt granskningen kommit är det som avgör vilket blad man öppnar härnäst, så det står i listan
          const marks = await api.allMarkups(d.id).catch(() => null);
          out.push({ ...d, project: p.name, counts: marks?.status_counts ?? {}, total: marks?.rows?.length ?? 0 });
        }
      }
      if (alive) setRows(out);
    }).catch((e) => alive && setErr(e.message));
    return () => { alive = false; };
  }, [tick]);
  return (
    <main>
      <p className="crumb">CAD</p>
      <div className="head">
        <div>
          <h1>CAD</h1>
          <p className="lead">
            Rita, mät och anteckna direkt på bladet, och arbeta i markeringslistan tills varje sak har ett svar.
            Det som ritas här ligger vid sidan av läsningen och rör den aldrig.
          </p>
        </div>
      </div>
      <div className="rule" style={{ marginBottom: 20 }} />
      <DrawingUpload verb="Öppna" onDone={(made) => {
        if (made.length === 1) nav(`/cad/${made[0].id}`);
        else { setRows(null); setTick((n) => n + 1); }
      }} />
      {err && <p className="error">{err}</p>}
      {!rows && <p className="muted">Laddar…</p>}
      {rows && !rows.length && <p className="muted">Ingen ritning uppladdad ännu. Lägg upp en här ovanför.</p>}
      <div className="list">
        {(rows ?? []).map((d) => (
          <article className="item" key={d.id}>
            <div className="no" />
            <div>
              <Link className="ttl" to={`/cad/${d.id}`} style={{ fontSize: 18 }}>{d.filename.replace(/\.pdf$/i, "")}</Link>
              <div className="sub">
                {d.project} · {d.n_pages} {d.n_pages === 1 ? "sida" : "sidor"}
                {d.total > 0 && <> · {d.total} markeringar
                  {d.counts.oppen ? ` · ${d.counts.oppen} öppna` : ""}
                  {d.counts.godkand ? ` · ${d.counts.godkand} godkända` : ""}</>}
              </div>
            </div>
            <div className="meta"><Link className="when" to={`/cad/${d.id}`}>Öppna →</Link></div>
          </article>
        ))}
      </div>
    </main>
  );
}
