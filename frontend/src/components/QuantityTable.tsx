import { useMemo, useState } from "react";
import { identityColor } from "./PdfViewer";

export const identityKey = (r: any) => `${r.base}|DN${r.dn ?? "?"}`;
const STATE_LABELS: Record<string, string> = { CONFIRMED: "BEKRÄFTAD", AMBIGUOUS: "TVETYDIG", UNSUPPORTED_STYLE: "EJ STÖDD STIL", RISER_LABELS_ONLY: "ENDAST STIGARE" };

export const riserCount = (r: any, source: string) => (source === "labels" ? r.riser_count_from_labels : r.riser_count) ?? 0;

export function withFloorHeight(rows: any[], floorHeight: number | null, includeHatched = false, riserSource = "labels"): any[] {
  // vertical metres are never assumed by the engine; with a user-given floor height each riser counts height metres.
  // pipe drawn inside hatched areas is measured but kept out of the total unless the takeoff includes those areas.
  return rows.map((r) => {
    const risers = riserCount(r, riserSource);
    const known = r.vertical_m !== "UNKNOWN" ? Number(r.vertical_m) : 0;
    const v = floorHeight && risers > 0 ? known + risers * floorHeight : (r.vertical_m === "UNKNOWN" ? null : known);
    const h = r.confirmed_horizontal_m + (includeHatched ? Number(r.in_hatched_area_m ?? 0) : 0);
    return { ...r, risers_calc: risers, horizontal_calc: h, vertical_calc: v, total_calc: h + (v ?? 0) };
  });
}

export default function QuantityTable({ rows, selected, onSelect, floorHeight, includeHatched, onIncludeHatched, riserSource }: { rows: any[]; selected: string | null; onSelect: (key: string | null) => void; floorHeight: number | null; includeHatched: boolean; onIncludeHatched: (v: boolean) => void; riserSource: string }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState<{ k: string; dir: 1 | -1 }>({ k: "designation", dir: 1 });
  const list = useMemo(() => {
    let l = withFloorHeight(rows, floorHeight, includeHatched, riserSource).filter((r) => (!q || r.designation.toLowerCase().includes(q.toLowerCase()) || String(r.dn).includes(q)) && (!status || r.state === status));
    l = [...l].sort((a, b) => { const va = a[sort.k], vb = b[sort.k]; return (va > vb ? 1 : va < vb ? -1 : 0) * sort.dir; });
    return l;
  }, [rows, q, status, sort, floorHeight, includeHatched, riserSource]);
  const hatchedTotal = rows.reduce((s, r) => s + Number(r.in_hatched_area_m ?? 0), 0);
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
        {hatchedTotal > 0 && (
          <label title="Rör som är ritade inuti skrafferade ytor (väggsnitt, angränsande ritningsdel). Mäts alltid, men räknas normalt inte in i mängden.">
            <input type="checkbox" checked={includeHatched} onChange={(e) => onIncludeHatched(e.target.checked)} />
            {` Räkna med skrafferade ytor (${hatchedTotal.toFixed(2)} m)`}
          </label>
        )}
      </div>
      <table>
        <thead><tr>{th("designation", "Beteckning")}{th("dn", "DN")}{th("label_count", "Beteckningar")}{th("physical_pipe_count", "Rörsträckor")}{th("confirmed_horizontal_m", "Horisontellt")}{th("vertical_calc", "Vertikalt")}{th("total_calc", "Totalt")}{th("ambiguous_m", "Tvetydigt")}{th("in_hatched_area_m", "Varav skrafferat")}{th("risers_calc", "Stigare")}{th("state", "Status")}</tr></thead>
        <tbody>
          {list.map((r) => (
            <tr key={identityKey(r)} className={`selectable ${selected === identityKey(r) ? "selected" : ""}`} onClick={() => onSelect(selected === identityKey(r) ? null : identityKey(r))}>
              <td><span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 2, background: identityColor(identityKey(r)), marginRight: 6, verticalAlign: "middle" }} />{r.designation}</td><td>{r.dn ?? "?"}</td><td className="num" title="Antal verifierade beteckningar på ritningen för denna identitet">{r.label_count ?? "–"}</td>
              <td className="num" title="Antal sammanhängande rörsträckor som nätet löser upp i (en sträcka bär oftast flera beteckningar)">{r.physical_pipe_count}</td>
              <td className="num">{r.horizontal_calc.toFixed(2)} m</td>
              <td className="num">{r.vertical_calc == null
                ? (r.risers_calc > 0
                  ? <span className="muted" title="Stigarna är hittade; ange våningshöjd för att räkna om dem till meter">{`${r.risers_calc} st × höjd`}</span>
                  : <span className="muted" title="Ritningen anger ingen höjd och inga stigare hittades">okänt</span>)
                : `${Number(r.vertical_calc).toFixed(2)} m`}</td>
              <td className="num">{r.total_calc.toFixed(2)} m</td>
              <td className="num">{r.ambiguous_m > 0 ? `${r.ambiguous_m.toFixed(2)} m` : "–"}</td>
              <td className="num">{(r.in_hatched_area_m ?? 0) > 0 ? `${Number(r.in_hatched_area_m).toFixed(2)} m` : "–"}</td>
              <td className="num" title={`Ritade stigarsymboler: ${r.riser_count ?? 0} · etiketter med dimension på raden under: ${r.riser_count_from_labels ?? 0}`}>{r.risers_calc > 0 ? r.risers_calc : "–"}</td>
              <td><span className={`badge ${r.state === "CONFIRMED" ? "ok" : r.state === "AMBIGUOUS" || r.state === "RISER_LABELS_ONLY" ? "warn" : "bad"}`}>{STATE_LABELS[r.state] ?? r.state}</span></td>
            </tr>
          ))}
        </tbody>
        <tfoot><tr><th>Summa</th><th></th><th className="num">{tot("label_count")}</th><th className="num">{tot("physical_pipe_count")}</th><th className="num">{tot("horizontal_calc").toFixed(2)} m</th><th className="num">{tot("vertical_calc").toFixed(2)} m</th><th className="num">{tot("total_calc").toFixed(2)} m</th><th className="num">{tot("ambiguous_m").toFixed(2)} m</th><th className="num">{tot("in_hatched_area_m").toFixed(2)} m</th><th className="num">{tot("risers_calc")}</th><th></th></tr></tfoot>
      </table>
    </div>
  );
}
