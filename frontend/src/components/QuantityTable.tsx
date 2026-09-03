import { useMemo, useState } from "react";

export const identityKey = (r: any) => `${r.base}|DN${r.dn ?? "?"}`;

export default function QuantityTable({ rows, selected, onSelect }: { rows: any[]; selected: string | null; onSelect: (key: string | null) => void }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState<{ k: string; dir: 1 | -1 }>({ k: "designation", dir: 1 });
  const list = useMemo(() => {
    let l = rows.filter((r) => (!q || r.designation.toLowerCase().includes(q.toLowerCase()) || String(r.dn).includes(q)) && (!status || r.state === status));
    l = [...l].sort((a, b) => { const va = a[sort.k], vb = b[sort.k]; return (va > vb ? 1 : va < vb ? -1 : 0) * sort.dir; });
    return l;
  }, [rows, q, status, sort]);
  const th = (k: string, label: string) => (
    <th onClick={() => setSort((s) => ({ k, dir: s.k === k ? (s.dir === 1 ? -1 : 1) : 1 }))}>{label}{sort.k === k ? (sort.dir === 1 ? " ▲" : " ▼") : ""}</th>
  );
  const tot = (f: string) => list.reduce((s, r) => s + (typeof r[f] === "number" ? r[f] : 0), 0);
  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <input placeholder="Sök beteckning/DN" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Alla status</option><option value="CONFIRMED">CONFIRMED</option><option value="AMBIGUOUS">AMBIGUOUS</option><option value="UNSUPPORTED_STYLE">UNSUPPORTED_STYLE</option>
        </select>
      </div>
      <table>
        <thead><tr>{th("designation", "Beteckning")}{th("dn", "DN")}{th("physical_pipe_count", "Antal")}{th("confirmed_horizontal_m", "Horisontellt")}{th("vertical_m", "Vertikalt")}{th("confirmed_total_m", "Totalt")}{th("ambiguous_m", "Tvetydigt")}{th("state", "Status")}</tr></thead>
        <tbody>
          {list.map((r) => (
            <tr key={identityKey(r)} className={`selectable ${selected === identityKey(r) ? "selected" : ""}`} onClick={() => onSelect(selected === identityKey(r) ? null : identityKey(r))}>
              <td>{r.designation}</td><td>{r.dn ?? "?"}</td><td className="num">{r.physical_pipe_count}</td>
              <td className="num">{r.confirmed_horizontal_m.toFixed(2)} m</td>
              <td className="num">{r.vertical_m === "UNKNOWN" ? <span className="muted">okänt</span> : `${Number(r.vertical_m).toFixed(2)} m`}</td>
              <td className="num">{r.confirmed_total_m.toFixed(2)} m</td>
              <td className="num">{r.ambiguous_m > 0 ? `${r.ambiguous_m.toFixed(2)} m` : "–"}</td>
              <td><span className={`badge ${r.state === "CONFIRMED" ? "ok" : r.state === "AMBIGUOUS" ? "warn" : "bad"}`}>{r.state}</span></td>
            </tr>
          ))}
        </tbody>
        <tfoot><tr><th>Summa</th><th></th><th className="num">{tot("physical_pipe_count")}</th><th className="num">{tot("confirmed_horizontal_m").toFixed(2)} m</th><th className="num">{tot("confirmed_vertical_m").toFixed(2)} m</th><th className="num">{tot("confirmed_total_m").toFixed(2)} m</th><th className="num">{tot("ambiguous_m").toFixed(2)} m</th><th></th></tr></tfoot>
      </table>
    </div>
  );
}
