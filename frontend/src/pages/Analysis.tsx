import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import PdfViewer, { Drawn, EditKind, Layer, ViewerHandle } from "../components/PdfViewer";
import QuantityTable from "../components/QuantityTable";
import AnalysisFilm from "../components/AnalysisFilm";
import Corrections, { Draft } from "../components/Corrections";
import LegendView from "../components/LegendView";
import Reasoning from "../components/Reasoning";
import AgentChat from "../components/AgentChat";
import { StatusBadge, stageText } from "../components/Status";

const VISION_LABELS: Record<string, string> = {
  missed_labels: "Beteckning som syns men inte lästes",
  missed_pipes: "Ritat rör som inget överlägg följer",
  overlay_wrong: "Överlägg som följer något annat än ett rör",
  paired_wall: "Två parallella linjer som är ett ritat föremål",
};

const ISSUE_LABELS: Record<string, string> = {
  unknown_glyph: "Okänt tecken", unknown_glyph_in_designation: "Olästa tecken i beteckningar",
  unknown_glyph_elsewhere: "Olästa tecken utanför beteckningarna", uncertain_designation: "Osäker beteckning",
  missing_dn: "Saknad DN", ambiguous_leader: "Tvetydig hänvisning",
  missing_leader: "Saknad hänvisningslinje", ambiguous_pipe_attachment: "Tvetydig röranslutning", missing_pipe_attachment: "Saknad röranslutning",
  unsupported_pipe_representation: "Rörrepresentation stöds ej", topology_conflict: "Topologikonflikt", branch_conflict: "Grenkonflikt", dn_conflict: "DN-konflikt",
  unowned_geometry: "Oidentifierad geometri", unsupported_structural_family: "Strukturfamilj stöds ej",
  drawn_outline: "Ritat föremål, inte rör", flow_beyond_labels: "Identitet nådde längre än beteckningarna",
};
// why a label never got a line to follow, said the way a person reads a drawing
const NO_LEADER_SV: Record<string, string> = {
  no_line_starts_at_this_label_at_all: "ingen linje utgår från etiketten",
  start_claimed_by_several_labels_at_once: "flera etiketter gör anspråk på samma linje",
  start_already_used_by_another_label_leader: "linjen används redan av en annan etikett",
  start_taken_by_a_label_with_a_better_claim: "en annan etikett hade starkare anspråk på linjen",
  start_grew_into_nothing: "linjen ledde ingenstans",
  line_from_the_label_is_shorter_than_the_label: "linjen är kortare än etiketten själv",
  the_row_rule_never_leaves_the_label: "radens linjal lämnar aldrig etiketten",
};

const LAYER_LABELS: Record<Layer, string> = { pipes: "Mätta rör", ambiguous: "Tvetydigt", unowned: "Oidentifierat", declined: "Bortvald geometri", designations: "Beteckningar", leaders: "CAD-leaders", anchors: "Anslutningar", inWall: "I vägg (räknas ej)" };
const LAYER_HINTS: Record<Layer, string> = {
  pipes: "Sträckor som fått en identitet och en längd, en färg per beteckning",
  ambiguous: "Ritad linje som kunde tillhöra mer än en beteckning — mäts inte",
  unowned: "Ritad linje i en accepterad rörfamilj som ingen beteckning nådde. Avstängt från början: det är ett fynd att titta på, inte ett fel i mätningen.",
  declined: "Ritad linje läsningen tittade på och inte tog som rör, med skälet",
  designations: "Alla lästa beteckningar på bladet",
  leaders: "Hänvisningslinjerna som ritningen drar från etikett till rör",
  anchors: "Där en beteckning faktiskt möter sitt rör",
  inWall: "Rör i vägg ritas alltid i det ej räknades färg — längden ligger utanför den horisontella mängden. Det här lagret gör dem tydligare och visar även etiketterna där.",
};

export default function AnalysisPage() {
  const { id } = useParams();
  const [job, setJob] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [pdf, setPdf] = useState<ArrayBuffer | null>(null);
  const [err, setErr] = useState("");
  const [tab, setTab] = useState<"mangder" | "agent" | "ejlosta" | "granskning" | "oversikt" | "artefakter" | "rattelser">("mangder");
  // what the agent means by "this": the runs the reader has clicked, and the box they dragged
  const [agentIds, setAgentIds] = useState<string[]>([]);
  // The three things a reader comes here for, and they are not the same thing: what the drawing says its codes
  // mean, the sheet with the reading drawn on it, and how the reading got there. Each had to be dug out of the
  // side panel before; each is a view of its own now.
  const [view, setView] = useState<"forklaring" | "analys" | "resonemang">("analys");
  const [selIdent, setSelIdent] = useState<string | null>(null);
  const [selPipe, setSelPipe] = useState<any>(null);
  const [why, setWhy] = useState<any>(null);
  const [page, setPage] = useState(0);
  // The quantity table has more columns than any fixed panel width fits, so the split is the reader's to set:
  // wide drawing while tracing a run, wide table while reading the takeoff. The choice is remembered.
  const [corrections, setCorrections] = useState<any[]>([]);
  const [vision, setVision] = useState<any>(null);
  const [visionBusy, setVisionBusy] = useState(false);
  const [drawKind, setDrawKind] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState<boolean>(() => {
    try { return localStorage.getItem("vvs.panelOpen") !== "0"; } catch { return true; }
  });
  const setOpen = (v: boolean) => {
    setPanelOpen(v);
    try { localStorage.setItem("vvs.panelOpen", v ? "1" : "0"); } catch { /* private window */ }
  };
  const [draft, setDraft] = useState<Draft>(null);
  const [panel, setPanel] = useState<number>(() => {
    const v = Number((() => { try { return localStorage.getItem("vvs.panel"); } catch { return null; } })());
    return v >= 360 && v <= 1400 ? v : 480;
  });
  const dragging = useRef(false);
  const [nPages, setNPages] = useState(1);
  const [floorHeight, setFloorHeight] = useState<string>(() => { try { return localStorage.getItem("vvs.floorHeight") ?? ""; } catch { return ""; } });
  const [includeHatched, setIncludeHatched] = useState<boolean>(() => { try { return localStorage.getItem("vvs.includeHatched") === "1"; } catch { return false; } });
  const [riserSource, setRiserSource] = useState<string>(() => { try { return localStorage.getItem("vvs.riserSource") ?? "labels"; } catch { return "labels"; } });
  // the export has to be given the same choices the table is showing, or the file states a different quantity
  const exportQuery = [
    floorHeight.trim() && !Number.isNaN(Number(floorHeight.replace(",", "."))) ? `floor_height=${Number(floorHeight.replace(",", "."))}` : "",
    includeHatched ? "include_hatched=true" : "",
    `riser_source=${riserSource}`,
  ].filter(Boolean).join("&");
  const fh = floorHeight.trim() ? Number(floorHeight.replace(",", ".")) : NaN;
  const floorH = Number.isFinite(fh) && fh > 0 ? fh : null;
  // The question a reader opens this page with is "did it get the pipes?", and that is a question about the
  // drawing with the reading on top of it - not about leaders, label boxes and attachment marks, which cover the
  // sheet so thickly that the runs underneath cannot be seen at all. They are diagnostics, and they start off.
  // The sheet opens showing what was measured. Ink the reading accepted as pipe but no label reached is a real
  // finding and has its own switch - shown first it reads as a fault, and a grey tangle over a good reading is
  // the fastest way to make a correct answer look wrong.
  const [layers, setLayers] = useState<Record<Layer, boolean>>({ pipes: true, ambiguous: true, unowned: false, declined: false, designations: false, leaders: false, anchors: false, inWall: false });
  // which bortvald family the reader is pointing at, so the sheet can show that ink and not all of it at once
  const [selDeclined, setSelDeclined] = useState<string | null>(null);
  const [layersOpen, setLayersOpen] = useState(false);
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
            try { setCorrections(await api.corrections(j.drawing_id)); } catch { /* corrections are optional */ }
          }
        } else if (j.status !== "FAILED") t = setTimeout(poll, 1500);
      } catch (e: any) { setErr(e.message); }
    };
    poll();
    return () => clearTimeout(t);
  }, [id]);

  const onPipeClick = async (p: any) => {
    setSelPipe(p); setSelIdent(p.identity);
    // while correcting, the click picks the run to correct: staying on the takeoff tab would hide the tools
    if (tab !== "rattelser") setTab("mangder");
    try { setWhy(await api.why(id!, p.physical_pipe_id)); } catch { setWhy(null); }
  };
  useEffect(() => {
    const move = (e: MouseEvent) => {
      if (!dragging.current) return;
      e.preventDefault();
      setPanel(Math.min(Math.max(window.innerWidth - e.clientX, 300), Math.max(window.innerWidth - 420, 300)));
    };
    const up = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.classList.remove("resizing");
      try { localStorage.setItem("vvs.panel", String(panel)); } catch { /* private window */ }
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    return () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
  }, [panel]);

  const dl = async (path: string, name: string) => { const b = await api.fetchBlob(path); const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = name; a.click(); };

  if (err) return <main><p className="error">{err}</p></main>;
  if (!job) return <main>Laddar…</main>;
  if (job.status !== "COMPLETED") {
    return (
      <main>
        <p className="crumb"><Link to={`/drawings/${job.drawing_id}`}>Ritning</Link> / Analys</p>
        <div className="head">
          <div>
            <h1>Läser ritningen</h1>
            <p className="lead">{stageText(job.stage) || job.stage}</p>
          </div>
          <StatusBadge job={job} />
        </div>
        <div className="rule" style={{ marginBottom: 26 }} />
        {job.status === "FAILED"
          ? <pre className="error">{job.error}</pre>
          : <AnalysisFilm jobId={id!} stage={job.stage} progress={job.progress} />}
      </main>
    );
  }
  if (!result) return <main>Laddar resultat…</main>;
  const c = result.coverage;
  const pipesOnPage = result.pipes.filter((p: any) => p.page === page);
  const covWarn = c.designations > 0 && c.verified_attachments / Math.max(c.designations, 1) < 0.5;
  const viewtabs = (
    <div className="viewtabs">
      <button className={view === "forklaring" ? "active" : ""} onClick={() => setView("forklaring")}>
        Förklaringslista{result.legend?.entries?.length ? ` (${result.legend.entries.length})` : ""}
      </button>
      <button className={view === "analys" ? "active" : ""} onClick={() => setView("analys")}>Analys</button>
      <button className={view === "resonemang" ? "active" : ""} onClick={() => setView("resonemang")}>Agenternas resonemang</button>
      <span className="spacer" />
      <StatusBadge job={job} />
    </div>
  );
  if (view === "forklaring") {
    return (
      <div className="workspace">
        {viewtabs}
        <LegendView legend={result.legend ?? { entries: [] }} designations={result.designations}
          quantities={result.quantities} />
      </div>
    );
  }
  if (view === "resonemang") {
    return (
      <div className="workspace">
        {viewtabs}
        <Reasoning jobId={id!} result={result} onZoom={(b) => { setView("analys"); setTimeout(() => viewer.current?.zoomTo(b), 60); }} />
      </div>
    );
  }
  return (
    <div className="workspace">
    {viewtabs}
    <div className={`analysis${panelOpen ? "" : " closed"}`}
      style={{ gridTemplateColumns: `minmax(0, 1fr) 6px ${panel}px` }}>
      <div className="left">
        {!panelOpen && (
          <button className="secondary small reopen" onClick={() => setOpen(true)}>Visa mängder</button>
        )}
        {/* One line of controls, because every line here is a line the drawing does not get. The eight layer
            switches used to wrap onto a second row and push the sheet down the page; they live behind one
            control now, which says how many are on. */}
        <div className="toolbar">
          <Link to={`/drawings/${job.drawing_id}`} className="back">← Ritning</Link>
          <span className="seg zoomseg">
            <button onClick={() => viewer.current?.zoomOut()} title="Zooma ut">−</button>
            <button onClick={() => viewer.current?.zoomIn()} title="Zooma in">+</button>
            <button onClick={() => viewer.current?.fitPage()} title="Hela sidan">Sida</button>
            <button onClick={() => viewer.current?.fitWidth()} title="Full bredd">Bredd</button>
          </span>
          <button className="secondary small" onClick={() => viewer.current?.fullscreen()}>Helskärm</button>
          {nPages > 1 && <select value={page} onChange={(e) => {
            // the selected run belongs to the page it was found on; carrying it across would put its ends,
            // and any correction dragged from them, on geometry that is not it
            setPage(Number(e.target.value)); setSelPipe(null); setWhy(null);
          }}>{Array.from({ length: nPages }, (_, i) => <option key={i} value={i}>Sida {i + 1}</option>)}</select>}
          <span className="spacer" />
          <div className="layerpop">
            <button className={`secondary small${layersOpen ? " on" : ""}`} onClick={() => setLayersOpen(!layersOpen)}>
              Lager · {(Object.keys(LAYER_LABELS) as Layer[]).filter((l) => layers[l]).length}
            </button>
            {layersOpen && (
              <div className="pop" onMouseLeave={() => setLayersOpen(false)}>
                {(Object.keys(LAYER_LABELS) as Layer[]).map((l) => (
                  <label key={l} title={LAYER_HINTS[l]}>
                    <input type="checkbox" checked={layers[l]} onChange={(e) => setLayers({ ...layers, [l]: e.target.checked })} />
                    <span>{LAYER_LABELS[l]}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>
        <PdfViewer ref={viewer} data={pdf} page={page} pipes={pipesOnPage} ambiguous={result.ambiguous_geometry} unowned={result.unowned_geometry}
          designations={result.designations} leaders={result.leaders} anchors={result.anchors} hatched={result.hatched_geometry ?? []} selectedIdentity={selIdent}
          declined={[...(result.declined_geometry?.families ?? []), ...(result.declined_geometry?.unconsidered ?? [])]} selectedDeclined={selDeclined}
          selectedPipe={selPipe?.physical_pipe_id ?? null} layers={layers} onPipeClick={onPipeClick} onPageCount={setNPages}
          editKind={(drawKind === "extend" || drawKind === "draw" || drawKind === "erase" ? drawKind : null) as EditKind}
          editPipe={selPipe} meterPerPt={result.scale?.meters_per_pdf_point ?? null}
          onDrawn={(d: Drawn) => setDraft({ points: d.points, meters: d.meters, hits: d.hits })}
          corrections={corrections.filter((c: any) => !c.undone && c.page === page)} />
      </div>
      <div className="splitter" role="separator" aria-orientation="vertical" aria-label="Dra för att ändra bredd"
        onMouseDown={() => { dragging.current = true; document.body.classList.add("resizing"); }}
        onDoubleClick={() => setPanel(380)} />
      {/* the chat is a conversation, so it fills its column and scrolls inside itself; every other tab is a
          document and scrolls the column */}
      <div className={`right${tab === "agent" ? " agentmode" : ""}`}>
        <div className="panelbar">
          <button className="ghost small" onClick={() => setPanel(Math.max(300, panel - 120))}
            title="Smalare">−</button>
          <button className="ghost small" onClick={() => setPanel(Math.min(Math.max(window.innerWidth - 420, 300), panel + 120))}
            title="Bredare">+</button>
          <button className="ghost small" onClick={() => setPanel(380)} title="Återställ bredden">Återställ</button>
          <span className="spacer" />
          <button className="ghost small" onClick={() => setOpen(false)} title="Stäng fältet">Stäng ✕</button>
        </div>
        <div className="tabs">
          <button className={tab === "mangder" ? "active" : ""} onClick={() => setTab("mangder")}>Mängder</button>
          <button className={tab === "agent" ? "active" : ""} onClick={() => setTab("agent")}>Agent</button>
          <button className={tab === "ejlosta" ? "active" : ""} onClick={() => setTab("ejlosta")}>Ej lösta ({result.issues.filter((i: any) => i.severity === "blocking").length})</button>
          <button className={tab === "granskning" ? "active" : ""} onClick={() => setTab("granskning")}>
            Granskning{result.review ? ` (${result.review.findings.filter((f: any) => f.severity !== "INFO").length})` : ""}
          </button>
          <button className={tab === "rattelser" ? "active" : ""} onClick={() => setTab("rattelser")}>
            Rätta{corrections.filter((c: any) => !c.undone).length ? ` (${corrections.filter((c: any) => !c.undone).length})` : ""}
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
            {/* Two settings and a paragraph explaining them used to stand between the reader and the numbers they
                came for. They are still one click away, and the summary line says what they are set to. */}
            <details className="settings">
              <summary>
                Antaganden <span className="muted">· våningshöjd {floorHeight ? `${floorHeight} m` : "ej satt"} · stigare ur
                  {riserSource === "labels" ? " etiketter" : " ritade symboler"}</span>
              </summary>
              <div className="body">
                <label>Våningshöjd för stigare (m)
                  <input style={{ width: 84 }} value={floorHeight} placeholder="t.ex. 2,8"
                    onChange={(e) => { setFloorHeight(e.target.value); try { localStorage.setItem("vvs.floorHeight", e.target.value); } catch { /* private window: the setting just does not persist */ } }} /></label>
                <label>Stigare räknas från
                  <select value={riserSource} onChange={(e) => { setRiserSource(e.target.value); try { localStorage.setItem("vvs.riserSource", e.target.value); } catch { /* private window: the setting just does not persist */ } }}>
                    <option value="labels">etiketter med dimension på raden under</option>
                    <option value="symbols">ritade stigarsymboler</option>
                  </select></label>
                <p className="muted">Vertikalt = antal stigare × våningshöjd; ritningen anger ingen höjd. Rör i
                  skrafferade ytor mäts alltid men räknas in bara om du kryssar i rutan nedan.</p>
              </div>
            </details>
            <QuantityTable rows={result.quantities} selected={selIdent} onSelect={(k) => { setSelIdent(k); setSelPipe(null); setWhy(null); }} floorHeight={floorH}
              pipes={result.pipes} meterPerPt={result.scale?.meters_per_pdf_point ?? null} onPipeClick={onPipeClick}
              includeHatched={includeHatched} onIncludeHatched={(v) => { setIncludeHatched(v); try { localStorage.setItem("vvs.includeHatched", v ? "1" : "0"); } catch { /* private window: the setting just does not persist */ } }}
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
        {tab === "agent" && (
          <AgentChat jobId={id!} page={page}
            selection={{ pipeIds: selPipe ? [selPipe.physical_pipe_id] : agentIds, bbox: null }}
            onHighlight={(ids) => {
              setAgentIds(ids);
              const first = result.pipes.find((p: any) => p.physical_pipe_id === ids[0]);
              if (first) { setSelIdent(first.identity); viewer.current?.zoomTo(first.bbox ?? null); }
            }}
            onChanged={async () => {
              setCorrections(await api.corrections(job.drawing_id));
              setResult(await api.result(id!));
            }} />
        )}
        {tab === "ejlosta" && (() => {
          const blocking = result.issues.filter((i: any) => i.severity === "blocking");
          const advisory = result.issues.filter((i: any) => i.severity !== "blocking");
          const row = (it: any, i: number) => (
            <div key={i} className="issue" onClick={() => it.bbox && viewer.current?.zoomTo(it.bbox)}>
              <b>{ISSUE_LABELS[it.kind] || it.kind}</b> {it.text ? `· ${it.text}` : ""} {it.reason ? <span className="muted">({String(it.reason).split(", ").map((r: string) => NO_LEADER_SV[r] || r).join("; ")})</span> : ""}
              {it.count ? <span className="muted"> · {it.count} st</span> : ""} {it.length_pt ? <span className="muted"> · {it.length_pt} pt</span> : ""}
            </div>
          );
          return (
            <>
              <div className="card">
                <h3>Att åtgärda <span className="badge warn">{blocking.length}</span></h3>
                <p className="muted" style={{ marginTop: 0 }}>Rör som ritningen namnger men som inte fått en meter.</p>
                {blocking.map(row)}
                {blocking.length === 0 && <p className="muted">Inget. Varje rör ritningen namnger har fått sin längd.</p>}
              </div>
              <div className="card">
                <h3>Noterat <span className="badge">{advisory.length}</span></h3>
                <p className="muted" style={{ marginTop: 0 }}>Sådant mängden överlever: en etikett till för en sträcka som redan är mätt, tecken utanför beteckningarna.</p>
                {advisory.map(row)}
                {advisory.length === 0 && <p className="muted">Inget noterat.</p>}
              </div>
              {result.reading_review && (() => {
                const rv = result.reading_review;
                const lg = rv.legend || {};
                const groups: [string, string, any[]][] = [
                  ["Geometri som etiketterna pekar på men som inte togs som rör", "rejected_families_labels_point_at", rv.rejected_families_labels_point_at || []],
                  ["Sträckor som slutar mot varandra över ett glapp som inte överbryggades", "possible_lost_continuity", rv.possible_lost_continuity || []],
                  ["Samma ritade linje i mer än en rörfamilj", "possible_double_counted_geometry", rv.possible_double_counted_geometry || []],
                  ["Ritningsstilar som ingen etikett nådde", "unsupported_style_candidates", rv.unsupported_style_candidates || []],
                ];
                const lost = rv.pipe_labels_with_no_leader || [];
                const n = groups.reduce((t, g) => t + g[2].length, 0);
                return (
                  <div className="card">
                    <h3>Vad läsningen själv frågar sig <span className="badge">{n}</span></h3>
                    <p className="muted" style={{ marginTop: 0 }}>
                      Sätt att en mängd kan bli tyst för kort utan att något ser fel ut. Inget av det är något motorn
                      kan avgöra själv — det står här för att det ska synas i stället för att saknas.
                    </p>
                    <div className="issue">
                      <b>Ritningens egen beteckningslista</b>{" "}
                      {lg.found
                        ? <span className="muted">{lg.entries} poster · system {(lg.systems || []).join(", ") || "inga"} · komponenter {(lg.components || []).join(", ") || "inga"}</span>
                        : <span className="muted">hittades inte på den här sidan — läsningen gick på mönsterstatistik i stället</span>}
                    </div>
                    {groups.map(([title, key, list]) => list.length > 0 && (
                      <div key={key} className="issue">
                        <b>{title}</b> <span className="muted">· {list.length} st</span>
                        <div className="muted" style={{ fontSize: 12 }}>
                          {list.slice(0, 3).map((x: any, i: number) => (
                            <div key={i}>{x.family ? x.family.slice(-34) : ""} {x.gap_pt ? `· glapp ${x.gap_pt} pt` : ""} {x.leader_ends ? `· ${x.leader_ends} ledaravslut` : ""}</div>
                          ))}
                          {list.length > 3 && <div>… och {list.length - 3} till</div>}
                        </div>
                      </div>
                    ))}
                    {lost.length > 0 && (
                      <div className="issue">
                        <b>Rörbeteckningar utan ledare</b>{" "}
                        <span className="muted">· {rv.n_pipe_labels_with_no_leader} st · en beteckning utan linje att följa
                          får ingen identitet, och röret den pekar på blir omätt</span>
                        <div className="muted" style={{ fontSize: 12 }}>
                          {lost.slice(0, 6).map((x: any, i: number) => (
                            <div key={i}>{x.text} — {(x.reasons || []).map((r: string) => NO_LEADER_SV[r] || r).join("; ")}</div>
                          ))}
                          {lost.length > 6 && <div>… och {rv.n_pipe_labels_with_no_leader - 6} till</div>}
                        </div>
                      </div>
                    )}
                    {n === 0 && lost.length === 0 && <p className="muted">Inget av de här fallen finns på den här sidan.</p>}
                  </div>
                );
              })()}
              {(() => {
                const dg = result.declined_geometry;
                if (!dg || (!dg.families?.length && !dg.unconsidered?.length)) return null;
                const t = dg.totals || {};
                // the ink worth a second look first: a pipe-named layer nothing pointed at, before one the
                // reading already knows carries this drawing's own labels and frames
                const unc = (dg.unconsidered ?? []).filter((f: any) => f.on_a_pipe_like_layer)
                  .sort((a: any, b: any) => Number(a.why !== "NO_LEADER_EVER_CAME_NEAR_IT") - Number(b.why !== "NO_LEADER_EVER_CAME_NEAR_IT")
                    || (b.length_m ?? 0) - (a.length_m ?? 0));
                return (
                  <div className="card">
                    <h3>Bortvald geometri <span className="badge">{dg.families.length}</span></h3>
                    <p className="muted" style={{ marginTop: 0 }}>
                      Ritad linje som läsningen tittade på och inte tog som rör. Oftast rätt — väggar, stomme och
                      raster ritas med samma penna som rören — men den försvinner tyst, och då ser en bortvald vägg
                      likadan ut som ett missat rör. Klicka på en rad för att se just den linjen på ritningen.
                      {t.length_m != null && <> Totalt {t.length_m} m{t.length_m_with_a_leader_end ? `, varav ${t.length_m_with_a_leader_end} m i familjer som en ledare faktiskt tog i` : ""}.</>}
                    </p>
                    {[...dg.families, ...unc].map((f: any) => (
                      <div key={f.family} className="issue" style={{ cursor: "pointer", background: selDeclined === f.family ? "#ecfeff" : undefined }}
                        onClick={() => { setSelDeclined(selDeclined === f.family ? null : f.family); setLayers({ ...layers, declined: true }); }}>
                        <b>{f.layer || `penna ${f.width}`}</b>{" "}
                        <span className="muted">{f.length_m != null ? `${f.length_m} m` : `${f.length_pt} pt`} · {f.n_segments} streck
                          {f.leader_ends_touching ? ` · ${f.leader_ends_touching} ledaravslut tar i den` : ""}
                          {f.on_a_pipe_like_layer ? " · lagernamn av samma sort som rörens" : ""}</span>
                        <div className="muted" style={{ fontSize: 12 }}>{f.why_sv}{f.segments_truncated ? " · visar en del av strecken" : ""}</div>
                      </div>
                    ))}
                    {t.unconsidered_length_m != null && (
                      <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
                        Därutöver {t.unconsidered_length_m} m ritad linje som ingen ledare kom i närheten av —
                        stomme, raster, ramar och text. {t.unconsidered_length_m_on_a_pipe_like_layer
                          ? `Av den ligger ${t.unconsidered_length_m_on_a_pipe_like_layer} m på lager namngivna som rörens; de står i listan ovan.`
                          : "Inget av den ligger på ett lager namngivet som rörens."}
                        {" "}Utan en beteckning som pekar dit har en sträcka ingen identitet och kan inte mätas.
                        {t.filled_shapes_length_m ? ` Ritningen har dessutom ${t.filled_shapes_length_m} m fylld yta — rum, möbler, raster — som aldrig är rör.` : ""}
                      </p>
                    )}
                  </div>
                );
              })()}
              <div className="card">
                <h3>Andra åsikt: titta på ritningen</h3>
                <p className="muted" style={{ marginTop: 0 }}>
                  Läsningen är gjord ur vektorn. Det den inte kan göra är att märka att en hel rörfamilj aldrig
                  togs med, eller att överlägget följer en vägg. Det ser man genom att titta. Blicken får peka ut
                  <b> en ruta</b> ur ett rutnät som läsningen ritat — aldrig en koordinat den hittar på — och sedan
                  läses den rutan ur vektorerna: vilken familj bläcket ligger i, vad läsningen gjorde med det, och
                  varför det inte finns meter där. Blicken säger var. Vektorerna säger varför. Bara det andra är
                  ett svar, och ingetdera blir någonsin en meter.
                </p>
                <button className="secondary" disabled={visionBusy} onClick={async () => {
                  setVisionBusy(true);
                  try { setVision(await api.vision(id!, page)); }
                  catch (e: any) { setVision({ error: e.message }); }
                  finally { setVisionBusy(false); }
                }}>{visionBusy ? "Tittar…" : `Titta på sida ${page + 1}`}</button>
                {vision?.error && <p className="error">{vision.error}</p>}
                {vision && !vision.error && (
                  <>
                    <p className="muted">{vision.asked ? `${vision.n_findings} iakttagelser` : vision.note}</p>
                    {(vision.findings || []).map((f: any, i: number) => {
                      const a = f.vector_account;
                      return (
                        <div key={i} className="issue" style={{ cursor: f.bbox ? "pointer" : undefined }}
                          onClick={() => f.bbox && viewer.current?.zoomTo(f.bbox)}>
                          <b>{VISION_LABELS[f.kind] || f.kind}</b>
                          {f.tile && <span className="muted"> · ruta {f.tile}</span>}
                          <div className="muted">{f.detail}{f.where && !f.tile ? ` — ${f.where}` : ""}</div>
                          {a && !a.error && (
                            <div style={{ marginTop: 6, fontSize: 12 }}>
                              <div><b>Vad vektorerna säger:</b> {a.verdict}</div>
                              <div className="muted" style={{ marginTop: 2 }}>
                                {a.measured_runs_drawn_m > 0 ? `${a.measured_runs_drawn_m} m mätt rör i rutan · ` : ""}
                                {a.n_designations} beteckningar · {a.n_leaders_ending_here} ledare slutar där
                                {a.inside_a_wall ? " · rutan ligger i en vägg" : ""}
                              </div>
                              {(a.families || []).slice(0, 3).map((fam: any, k: number) => (
                                <div key={k} className="muted">{fam.length_m} m — {fam.role}
                                  {fam.why ? ` (${fam.why})` : ""} · {String(fam.family).slice(-30)}</div>
                              ))}
                            </div>
                          )}
                          {a?.error && <div className="muted" style={{ fontSize: 12 }}>{a.error}</div>}
                        </div>
                      );
                    })}
                  </>
                )}
              </div>
            </>
          );
        })()}
        {tab === "rattelser" && (
          <Corrections drawingId={job.drawing_id} jobId={id!} page={page} quantities={result.quantities}
            corrections={corrections} draft={draft} kind={drawKind} pipe={selPipe} proposals={result.proposals ?? []}
            onKindChange={setDrawKind} onDraftClear={() => setDraft(null)}
            onChanged={async () => {
              setCorrections(await api.corrections(job.drawing_id));
              setResult(await api.result(id!));
            }} />
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
              {(() => {
                // length the drawing puts inside walls: drawn, measured, and outside the horizontal quantity by
                // design. Stated rather than hidden, because a number that is left out silently is a number a
                // reader will one day find and not be able to place.
                const inWall = (result.quantities || []).reduce((t: number, r: any) => t + (r.in_hatched_area_m || 0), 0);
                return inWall > 0.005
                  ? <div className="card"><div className="v">{inWall.toFixed(1)} m</div><div className="l">I vägg (utanför mängden)</div></div>
                  : null;
              })()}
              {(() => {
                const tags = (result.designations || []).filter((d: any) => d.names_a_pipe === false).length;
                return tags > 0
                  ? <div className="card"><div className="v">{tags}</div><div className="l">Komponentbeteckningar</div></div>
                  : null;
              })()}
            </div>
            <p style={{ marginTop: 12 }}>Indata: <b>ren vektor</b> ({result.input?.classification?.n_paths ?? "?"} vektorobjekt, {result.input?.classification?.n_chars ?? 0} söktecken) · Skala: <b>{result.scale.state}</b> ({result.scale.reason}) · Reconciliation: <b>{c.reconciliation}</b> · Determinism: <b>{c.determinism ?? "ej körd"}</b> · Contamination: <b>{c.contamination}</b> · Andraläsare: <b>{c.second_reader?.consulted ? `tillfrågad (${c.second_reader.asked} fall, ${c.second_reader.settled} avgjorda)` : "ej tillfrågad"}</b> · Motor: <b>{result.build?.engine ?? "?"}</b> (bygge <code>{result.build?.build ?? "okänt"}</code>)</p>
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
    </div>
  );
}
