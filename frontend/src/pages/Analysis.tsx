import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import PdfViewer, { Layer, ViewerHandle } from "../components/PdfViewer";
import QuantityTable from "../components/QuantityTable";
import { StatusBadge, STAGE_LABELS } from "../components/Status";

const ISSUE_LABELS: Record<string, string> = {
  unknown_glyph: "Okänt tecken", unknown_glyph_in_designation: "Olästa tecken i beteckningar",
  unknown_glyph_elsewhere: "Olästa tecken utanför beteckningarna", uncertain_designation: "Osäker beteckning",
  missing_dn: "Saknad DN", ambiguous_leader: "Tvetydig hänvisning",
  missing_leader: "Saknad hänvisningslinje", ambiguous_pipe_attachment: "Tvetydig röranslutning", missing_pipe_attachment: "Saknad röranslutning",
  unsupported_pipe_representation: "Rörrepresentation stöds ej", topology_conflict: "Topologikonflikt", branch_conflict: "Grenkonflikt", dn_conflict: "DN-konflikt",
  unowned_geometry: "Oidentifierad geometri", unsupported_structural_family: "Strukturfamilj stöds ej",
};
const LAYER_LABELS: Record<Layer, string> = { pipes: "PhysicalPipes", ambiguous: "Tvetydigt", unowned: "Oidentifierat", designations: "Beteckningar", leaders: "CAD-leaders", anchors: "Anslutningar" };

export default function AnalysisPage() {
  const { id } = useParams();
  const [job, setJob] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [pdf, setPdf] = useState<ArrayBuffer | null>(null);
  const [err, setErr] = useState("");
  const [tab, setTab] = useState<"mangder" | "ejlosta" | "granskning" | "oversikt" | "artefakter">("mangder");
  const [selIdent, setSelIdent] = useState<string | null>(null);
  const [selPipe, setSelPipe] = useState<any>(null);
  const [why, setWhy] = useState<any>(null);
  const [page, setPage] = useState(0);
  const [nPages, setNPages] = useState(1);
  const [floorHeight, setFloorHeight] = useState<string>(() => { try { return localStorage.getItem("vvs.floorHeight") ?? ""; } catch { return ""; } });
  const [includeHatched, setIncludeHatched] = useState<boolean>(() => { try { return localStorage.getItem("vvs.includeHatched") === "1"; } catch { return false; } });
  const [riserSource, setRiserSource] = useState<string>(() => { try { return localStorage.getItem("vvs.riserSource") ?? "labels"; } catch { return "labels"; } });
  const exportQuery = [floorHeight.trim() && !Number.isNaN(Number(floorHeight.replace(",", "."))) ? `floor_height=${Number(floorHeight.replace(",", "."))}` : "", includeHatched ? "include_hatched=true" : ""].filter(Boolean).join("&");
  const fh = floorHeight.trim() ? Number(floorHeight.replace(",", ".")) : NaN;
  const floorH = Number.isFinite(fh) && fh > 0 ? fh : null;
  const [layers, setLayers] = useState<Record<Layer, boolean>>({ pipes: true, ambiguous: true, unowned: true, designations: true, leaders: true, anchors: true });
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const viewer = useRef<ViewerHandle>(null);

  useEffect(() => {
    let t: any; let loaded = false;
    const poll = async () => {
      try {
        const j = await api.job(id!); setJob(j);
        if (j.status === "COMPLETED") {
          if (!loaded) {
            loaded = true;
            const r = await api.result(id!); setResult(r);
            const b = await api.fetchBlob(api.fileUrl(j.drawing_id)); setPdf(await b.arrayBuffer());
            setArtifacts(await api.artifacts(id!));
          }
        } else if (j.status !== "FAILED") t = setTimeout(poll, 1500);
      } catch (e: any) { setErr(e.message); }
    };
    poll();
    return () => clearTimeout(t);
  }, [id]);

  const onPipeClick = async (p: any) => {
    setSelPipe(p); setSelIdent(p.identity); setTab("mangder");
    try { setWhy(await api.why(id!, p.physical_pipe_id)); } catch { setWhy(null); }
  };
  const dl = async (path: string, name: string) => { const b = await api.fetchBlob(path); const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = name; a.click(); };

  if (err) return <main><p className="error">{err}</p></main>;
  if (!job) return <main>Laddar…</main>;
  if (job.status !== "COMPLETED") {
    return (
      <main>
        <p><Link to={`/drawings/${job.drawing_id}`}>← Ritning</Link></p>
        <div className="card">
          <h3>Analys pågår</h3>
          <div className="progress"><div style={{ width: `${Math.round(job.progress * 100)}%` }} /></div>
          <p><StatusBadge job={job} /> {STAGE_LABELS[job.stage] || job.stage}</p>
          {job.status === "FAILED" && <pre className="error">{job.error}</pre>}
        </div>
      </main>
    );
  }
  if (!result) return <main>Laddar resultat…</main>;
  const c = result.coverage;
  const pipesOnPage = result.pipes.filter((p: any) => p.page === page);
  const covWarn = c.designations > 0 && c.verified_attachments / Math.max(c.designations, 1) < 0.5;
  return (
    <div className="analysis">
      <div className="left">
        <div className="toolbar">
          <Link to={`/drawings/${job.drawing_id}`}>← Ritning</Link>
          <button className="secondary small" onClick={() => viewer.current?.zoomIn()}>Zooma in</button>
          <button className="secondary small" onClick={() => viewer.current?.zoomOut()}>Zooma ut</button>
          <button className="secondary small" onClick={() => viewer.current?.fitPage()}>Anpassa sida</button>
          <button className="secondary small" onClick={() => viewer.current?.fitWidth()}>Anpassa bredd</button>
          <button className="secondary small" onClick={() => viewer.current?.fullscreen()}>Helskärm</button>
          {nPages > 1 && <select value={page} onChange={(e) => setPage(Number(e.target.value))}>{Array.from({ length: nPages }, (_, i) => <option key={i} value={i}>Sida {i + 1}</option>)}</select>}
          {(Object.keys(LAYER_LABELS) as Layer[]).map((l) => (
            <label key={l} style={{ fontSize: 12 }}><input type="checkbox" checked={layers[l]} onChange={(e) => setLayers({ ...layers, [l]: e.target.checked })} /> {LAYER_LABELS[l]}</label>
          ))}
        </div>
        <PdfViewer ref={viewer} data={pdf} page={page} pipes={pipesOnPage} ambiguous={result.ambiguous_geometry} unowned={result.unowned_geometry}
          designations={result.designations} leaders={result.leaders} anchors={result.anchors} hatched={result.hatched_geometry ?? []} selectedIdentity={selIdent}
          selectedPipe={selPipe?.physical_pipe_id ?? null} layers={layers} onPipeClick={onPipeClick} onPageCount={setNPages} />
      </div>
      <div className="right">
        <div className="tabs">
          <button className={tab === "mangder" ? "active" : ""} onClick={() => setTab("mangder")}>Mängder</button>
          <button className={tab === "ejlosta" ? "active" : ""} onClick={() => setTab("ejlosta")}>Ej lösta ({result.issues.length})</button>
          <button className={tab === "granskning" ? "active" : ""} onClick={() => setTab("granskning")}>
            Granskning{result.review ? ` (${result.review.findings.filter((f: any) => f.severity !== "INFO").length})` : ""}
          </button>
          <button className={tab === "oversikt" ? "active" : ""} onClick={() => setTab("oversikt")}>Översikt</button>
          <button className={tab === "artefakter" ? "active" : ""} onClick={() => setTab("artefakter")}>Export</button>
        </div>
        {tab === "mangder" && (
          <div className="card">
            {covWarn && (
              <p className="badge warn">
                {`${c.verified_attachments} av ${c.designations} beteckningar nådde ett rör. Resten är legendtext, komponenttaggar eller etiketter vars hänvisningslinje inte når fram – se Granskning.`}
              </p>
            )}
            <div className="row" style={{ marginBottom: 8, alignItems: "center", gap: 8 }}>
              <label style={{ fontSize: 12 }}>Våningshöjd för stigare (m): <input style={{ width: 70 }} value={floorHeight} placeholder="t.ex. 2,8"
                onChange={(e) => { setFloorHeight(e.target.value); try { localStorage.setItem("vvs.floorHeight", e.target.value); } catch {} }} /></label>
              <label style={{ fontSize: 12 }}>Stigare räknas från:{" "}
                <select value={riserSource} onChange={(e) => { setRiserSource(e.target.value); try { localStorage.setItem("vvs.riserSource", e.target.value); } catch {} }}>
                  <option value="labels">etiketter med dimension på raden under</option>
                  <option value="symbols">ritade stigarsymboler</option>
                </select></label>
              <span className="muted" style={{ fontSize: 12 }}>Vertikalt = antal stigare × våningshöjd (ritningen anger ingen höjd). Rör i skrafferade ytor mäts alltid men räknas in bara om du kryssar i rutan.</span>
            </div>
            <QuantityTable rows={result.quantities} selected={selIdent} onSelect={(k) => { setSelIdent(k); setSelPipe(null); setWhy(null); }} floorHeight={floorH}
              includeHatched={includeHatched} onIncludeHatched={(v) => { setIncludeHatched(v); try { localStorage.setItem("vvs.includeHatched", v ? "1" : "0"); } catch {} }}
              riserSource={riserSource} />
            {why && (
              <div style={{ marginTop: 12 }}>
                <h4>Varför? {why.pipe.designation} DN{why.pipe.dn ?? "?"} · {typeof why.pipe.horizontal_m === "number" ? `${why.pipe.horizontal_m.toFixed(2)} m` : "ingen skala"}</h4>
                <p className="muted">Rör-id {why.pipe.physical_pipe_id} · {why.pipe.raw_pt.toFixed(1)} pt + {why.pipe.bridged_gap_pt.toFixed(1)} pt överbryggade mikrogap · {why.pipe.source_path_ids.length} PDF-objekt</p>
                {why.evidence_chain.map((e: any, i: number) => (
                  <div key={i} className="issue" onClick={() => e.designation && viewer.current?.zoomTo(e.designation.bbox)}>
                    <b>{e.designation?.text}</b> DN {e.dn ?? "?"} ({e.designation?.source}) → leader {e.leader?.family} ({e.leader?.n_segments} segment) → {e.attachment.state} ({e.attachment.reason})
                  </div>
                ))}
                <p className="muted">Skala: {why.scale.state} {why.scale.meters_per_pdf_point ? `${why.scale.meters_per_pdf_point.toFixed(6)} m/pt` : ""}</p>
              </div>
            )}
          </div>
        )}
        {tab === "ejlosta" && (
          <div className="card">
            {result.issues.map((it: any, i: number) => (
              <div key={i} className="issue" onClick={() => it.bbox && viewer.current?.zoomTo(it.bbox)}>
                <b>{ISSUE_LABELS[it.kind] || it.kind}</b> {it.text ? `· ${it.text}` : ""} {it.count ? `· ${it.count} st` : ""} {it.reason ? <span className="muted">({it.reason})</span> : ""}
                {it.count ? <span className="muted"> · {it.count} st</span> : ""} {it.length_pt ? <span className="muted"> · {it.length_pt} pt</span> : ""}
              </div>
            ))}
            {result.issues.length === 0 && <p className="muted">Inga olösta problem.</p>}
          </div>
        )}
        {tab === "granskning" && (
          <div className="card">
            {!result.review && <p className="muted">Granskningen kördes inte för det här jobbet.</p>}
            {result.review && (
              <>
                <p style={{ marginTop: 0 }}>
                  Oberoende granskning av resultatet: <b>{result.review.state === "OK" ? "inga anmärkningar" : result.review.state}</b>
                  {` · ${result.review.n_findings} fynd · agenter: ${result.review.agents.join(", ")}`}
                </p>
                {result.review.findings.map((f: any, i: number) => (
                  <div key={i} className="issue" style={{ cursor: f.bbox ? "pointer" : "default" }}
                    onClick={() => f.bbox && viewer.current?.zoomTo(f.bbox)}>
                    <span className={`badge ${f.severity === "ERROR" ? "bad" : f.severity === "WARN" ? "warn" : "ok"}`}>{f.severity}</span>
                    {` ${f.message}`}
                    <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                      {f.agent} · {f.code}
                      {f.detail?.examples ? ` · ${f.detail.examples.join(", ")}` : ""}
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}
        {tab === "oversikt" && (
          <div className="card">
            <div className="kpi">
              <div className="card"><div className="v">{c.designations}</div><div className="l">Vektorbeteckningar</div></div>
              <div className="card"><div className="v">{c.with_dn}</div><div className="l">DN</div></div>
              <div className="card"><div className="v">{c.leaders}</div><div className="l">CAD-leaders</div></div>
              <div className="card"><div className="v">{c.verified_attachments}</div><div className="l">Verifierade röranslutningar</div></div>
              <div className="card"><div className="v">{c.physical_pipes}</div><div className="l">PhysicalPipes</div></div>
              <div className="card"><div className="v">{result.totals.confirmed_horizontal_m.toFixed(1)} m</div><div className="l">Horisontellt</div></div>
              <div className="card"><div className="v">{result.totals.confirmed_vertical_m.toFixed(1)} m</div><div className="l">Vertikalt</div></div>
              <div className="card"><div className="v">{result.totals.confirmed_total_m.toFixed(1)} m</div><div className="l">Totalt</div></div>
              <div className="card"><div className="v">{result.totals.ambiguous_m.toFixed(1)} m</div><div className="l">Tvetydigt</div></div>
              <div className="card"><div className="v">{c.unowned_m ?? "?"} m</div><div className="l">Oidentifierad geometri</div></div>
              <div className="card"><div className="v">{c.unsupported_families}</div><div className="l">Unsupported styles</div></div>
              <div className="card"><div className="v">{c.ambiguous_attachments + c.no_attachments}</div><div className="l">Ej anslutna beteckningar</div></div>
            </div>
            <p style={{ marginTop: 12 }}>Indata: <b>ren vektor</b> ({result.input?.classification?.n_paths ?? "?"} vektorobjekt, {result.input?.classification?.n_chars ?? 0} söktecken) · Skala: <b>{result.scale.state}</b> ({result.scale.reason}) · Reconciliation: <b>{c.reconciliation}</b> · Determinism: <b>{c.determinism ?? "ej körd"}</b> · Contamination: <b>{c.contamination}</b></p>
            <p className="muted">Sida {result.page.width_pt}×{result.page.height_pt} pt ({result.page.format}) · analys {result.performance.total_seconds} s · {result.performance.counts.raw_vector_objects} vektorobjekt · {result.performance.counts.glyphs} glyfer i {result.performance.counts.glyph_families} familjer</p>
          </div>
        )}
        {tab === "artefakter" && (
          <div className="card">
            <h4>Export</h4>
            <div className="row">
              <button onClick={() => dl(api.exportUrl(id!, "pdf"), "markerad.pdf")}>Markerad PDF</button>
              <button onClick={() => dl(api.exportUrl(id!, "xlsx") + (exportQuery ? `?${exportQuery}` : ""), "mangder.xlsx")}>Excel</button>
              <button onClick={() => dl(api.exportUrl(id!, "csv") + (exportQuery ? `?${exportQuery}` : ""), "mangder.csv")}>CSV</button>
              <button onClick={() => dl(api.exportUrl(id!, "json"), "quantities.json")}>JSON</button>
              <button onClick={() => dl(api.exportUrl(id!, "report"), "analysrapport.md")}>Analysrapport</button>
            </div>
            <h4>Artefakter</h4>
            <table><tbody>{artifacts.map((a) => <tr key={a.name}><td><a href="#" onClick={(e) => { e.preventDefault(); dl(api.artifactUrl(id!, a.name), a.name); }}>{a.name}</a></td><td className="num muted">{(a.size / 1024).toFixed(0)} kB</td></tr>)}</tbody></table>
          </div>
        )}
      </div>
    </div>
  );
}
