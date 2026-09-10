import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import PdfViewer, { type ViewerHandle } from "../components/PdfViewer";

/* Mängda för hand: mät, räkna och markera direkt på bladet.
 *
 * Det här är mängdarens eget arbete och ligger vid sidan av läsningen, aldrig i den. Motorn mäter det ritaren
 * ritade; här mäter en människa det hon ser, och de två redovisas var för sig så att ingen behöver undra
 * vilket som är vilket.
 *
 * Måtten räknas på servern ur punkterna och den skala som gäller för bladet. Siffran som visas medan man ritar
 * är en förhandsvisning; den som sparas är serverns. Går skalan inte att läsa ur bladet mäter man upp den själv
 * - dra en linje över något vars längd är känd - och då står det uppmätt på varje rad den gäller.
 */

type Tool = "langd" | "polylinje" | "area" | "volym" | "antal" | "rektangel" | "moln" | "frihand" | "text" | null;

const TOOLS: { id: Exclude<Tool, null>; label: string; hint: string; kind: "langd" | "yta" | "antal" | "text" }[] = [
  { id: "langd", label: "Längd", hint: "Klicka längs det som ska mätas. Dubbelklick avslutar, Esc avbryter.", kind: "langd" },
  { id: "polylinje", label: "Polylinje", hint: "Samma som längd, för en sträcka med många knäckar.", kind: "langd" },
  { id: "frihand", label: "Frihand", hint: "Dra med musen längs en böjd sträcka.", kind: "langd" },
  { id: "area", label: "Yta", hint: "Klicka runt ytan; den sluts automatiskt.", kind: "yta" },
  { id: "rektangel", label: "Rektangel", hint: "Två hörn räcker för en rätvinklig yta.", kind: "yta" },
  { id: "volym", label: "Volym", hint: "En yta med djup: kvadratmetrarna blir kubikmeter.", kind: "yta" },
  { id: "moln", label: "Moln", hint: "Ringa in ett område som ska granskas.", kind: "yta" },
  { id: "antal", label: "Antal", hint: "Klicka på varje sak som ska räknas. Varje får sitt löpnummer.", kind: "antal" },
  { id: "text", label: "Anteckning", hint: "Klicka där anteckningen ska sitta och skriv den.", kind: "text" },
];

const n2 = (v: number | null | undefined, d = 2) =>
  v == null ? "–" : v.toLocaleString("sv-SE", { minimumFractionDigits: d, maximumFractionDigits: d });

function measureText(m: any): string {
  if (!m) return "";
  const bits: string[] = [];
  if (typeof m.m === "number") bits.push(`${n2(m.m)} m`);
  if (typeof m.kvm === "number") bits.push(`${n2(m.kvm)} m²`);
  if (typeof m.m3 === "number") bits.push(`${n2(m.m3)} m³`);
  if (typeof m.antal === "number") bits.push(`${m.antal} st`);
  if (!bits.length && m.langd_pt) bits.push(`${Math.round(m.langd_pt)} pt`);
  if (m.scale === "INGEN_SKALA") bits.push("ingen skala");
  if (m.scale === "UPPMÄTT") bits.push("uppmätt skala");
  return bits.join(" · ");
}

export default function TakeoffPage() {
  const { id } = useParams();
  const drawingId = id!;
  const [drawing, setDrawing] = useState<any>(null);
  const [data, setData] = useState<ArrayBuffer | null>(null);
  const [page, setPage] = useState(0);
  const [nPages, setNPages] = useState(1);
  const [tool, setTool] = useState<Tool>("langd");
  const [draft, setDraft] = useState<{ points: number[][]; meters: number } | null>(null);
  const [list, setList] = useState<any>(null);
  const [presets, setPresets] = useState<any[]>([]);
  const [layer, setLayer] = useState("Mängdning");
  const [designation, setDesignation] = useState("");
  const [text, setText] = useState("");
  const [props, setProps] = useState<{ multiplikator?: number; tillagg_m?: number; djup_m?: number }>({});
  const [calibrating, setCalibrating] = useState(false);
  const [calLength, setCalLength] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const viewer = useRef<ViewerHandle>(null);

  useEffect(() => {
    api.drawing(drawingId).then(setDrawing).catch((e) => setErr(e.message));
    api.fetchBlob(api.fileUrl(drawingId)).then((b) => b.arrayBuffer()).then(setData).catch((e) => setErr(e.message));
    api.toolPresets().then((d) => setPresets(d.rows)).catch(() => { /* verktygslådan är en hjälp */ });
  }, [drawingId]);

  const load = () => api.markups(drawingId, page).then(setList).catch((e) => setErr(e.message));
  useEffect(() => { load(); setDraft(null); }, [drawingId, page]);

  const mpp = list?.meters_per_pdf_point ?? null;
  const kind = TOOLS.find((t) => t.id === tool)?.kind ?? "langd";

  const save = async () => {
    if (!tool || !draft) return;
    setBusy(true); setErr("");
    try {
      await api.addMarkup(drawingId, {
        page, tool, layer: layer.trim() || "Mängdning", designation: designation.trim() || null,
        points: draft.points, text: tool === "text" ? text : "",
        props: Object.fromEntries(Object.entries(props).filter(([, v]) => v != null && !Number.isNaN(v))),
      });
      setDraft(null); setText("");
      await load();
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const calibrate = async () => {
    if (!draft || draft.points.length < 2) return;
    const len = Number(calLength.replace(",", "."));
    if (!len || len <= 0) { setErr("Skriv hur lång sträckan är i meter"); return; }
    setBusy(true); setErr("");
    try {
      const pts = [draft.points[0], draft.points[draft.points.length - 1]];
      await api.setCalibration(drawingId, { page, points: pts, length_m: len, note: "" });
      setCalibrating(false); setDraft(null); setCalLength("");
      await load();
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const remove = async (mid: string) => {
    try { await api.deleteMarkup(drawingId, mid); await load(); } catch (e: any) { setErr(e.message); }
  };

  const applyPreset = (p: any) => {
    setTool(p.tool); setLayer(p.layer); setDesignation(p.designation ?? ""); setProps(p.props ?? {});
  };
  const savePreset = async () => {
    const name = (designation || layer || tool || "Verktyg").toString();
    try {
      await api.addToolPreset({ name, tool, layer, designation: designation || null, props });
      setPresets((await api.toolPresets()).rows);
    } catch (e: any) { setErr(e.message); }
  };

  const rows: any[] = list?.rows ?? [];
  const byLayer = useMemo(() => {
    const g: Record<string, any[]> = {};
    rows.forEach((r) => { (g[r.layer] ||= []).push(r); });
    return Object.entries(g);
  }, [rows]);

  const preview = draft && (
    calibrating ? `${Math.round(Math.hypot(draft.points[draft.points.length - 1][0] - draft.points[0][0],
      draft.points[draft.points.length - 1][1] - draft.points[0][1]))} punkter`
      : kind === "antal" ? `${draft.points.length} st`
      : kind === "yta" ? (draft.points.length >= 3 ? "yta – räknas när den sparas" : "minst tre punkter")
      : mpp ? `${n2(draft.meters)} m` : `${draft.points.length} punkter · ingen skala`);

  return (
    <main className="takeoff">
      <p className="crumb">
        <Link to="/mangda">Mängda</Link>
        {drawing && <> · <Link to={`/drawings/${drawingId}`}>{drawing.filename.replace(/\.pdf$/i, "")}</Link></>}
      </p>
      <div className="head">
        <div>
          <h1>Mängda</h1>
          <p className="lead">
            Mät, räkna och markera för hand direkt på bladet. Måtten räknas på servern ur punkterna och bladets
            skala. {list?.scale_source === "UPPMÄTT" ? "Skalan är uppmätt av dig."
              : list?.scale_source === "LÄSNINGEN" ? "Skalan kommer ur läsningen av bladet."
              : "Bladet har ingen skala ännu – mät upp den, så blir punkterna meter."}
          </p>
        </div>
        <div className="row">
          <button className={calibrating ? "" : "secondary"} onClick={() => { setCalibrating(!calibrating); setDraft(null); }}>
            {calibrating ? "Avbryt kalibrering" : "Kalibrera skala"}
          </button>
          <button className="secondary" onClick={async () => {
            const b = await api.fetchBlob(api.markupsCsvUrl(drawingId, page));
            const u = URL.createObjectURL(b); const a = document.createElement("a");
            a.href = u; a.download = "markeringar.csv"; a.click(); URL.revokeObjectURL(u);
          }}>Lista som CSV</button>
        </div>
      </div>
      <div className="rule" style={{ marginBottom: 18 }} />
      {err && <p className="error">{err}</p>}

      <div className="tk-grid">
        <div className="tk-sheet">
          <div className="toolbar">
            <button className="secondary small" onClick={() => viewer.current?.zoomOut()}>−</button>
            <button className="secondary small" onClick={() => viewer.current?.zoomIn()}>+</button>
            <button className="secondary small" onClick={() => viewer.current?.fitPage()}>Sida</button>
            <button className="secondary small" onClick={() => viewer.current?.fitWidth()}>Bredd</button>
            <button className="secondary small" onClick={() => viewer.current?.fullscreen()}>Helskärm</button>
            {nPages > 1 && (
              <select value={page} onChange={(e) => setPage(Number(e.target.value))}>
                {Array.from({ length: nPages }, (_, i) => <option key={i} value={i}>Sida {i + 1}</option>)}
              </select>
            )}
            <span className="spacer" />
            <span className="muted small">{list ? `${rows.length} markeringar` : "…"}</span>
          </div>
          <PdfViewer
            ref={viewer} data={data} page={page} pipes={[]} ambiguous={[]} unowned={[]} claimed={[]}
            designations={[]} leaders={[]} anchors={[]} declined={[]} selectedIdentity={null} selectedPipe={null}
            layers={{ pipes: false, ambiguous: false, unowned: false, claimed: false, designations: false,
                      leaders: false, hatched: false, declined: false } as any}
            onPipeClick={() => { /* ingen läsning här */ }} onPageCount={setNPages}
            editKind={(calibrating || tool ? "draw" : null) as any}
            meterPerPt={mpp}
            onDrawn={(d: any) => setDraft({ points: d.points, meters: d.meters })}
            markups={rows}
          />
        </div>

        <aside className="tk-side">
          <section className="card">
            <h3 style={{ marginTop: 0 }}>{calibrating ? "Kalibrera skalan" : "Verktyg"}</h3>
            {calibrating ? (
              <>
                <p className="muted small">
                  Dra en linje över något vars längd du vet – en dörr, ett modulmått, skalstocken – och skriv vad
                  den är i meter. Alla mått på sidan räknas om.
                </p>
                <label className="adm-field"><span>Sträckans längd i meter</span>
                  <input value={calLength} onChange={(e) => setCalLength(e.target.value)} placeholder="t.ex. 1,0" /></label>
                <div className="row" style={{ marginTop: 10 }}>
                  <button disabled={!draft || busy} onClick={calibrate}>Spara skalan</button>
                  {list?.calibration && (
                    <button className="ghost small" disabled={busy}
                      onClick={async () => { await api.clearCalibration(drawingId, page); await load(); }}>
                      Ta bort uppmätt skala
                    </button>
                  )}
                </div>
              </>
            ) : (
              <>
                <div className="tk-tools">
                  {TOOLS.map((t) => (
                    <button key={t.id} className={tool === t.id ? "" : "secondary"} onClick={() => { setTool(t.id); setDraft(null); }}>
                      {t.label}
                    </button>
                  ))}
                </div>
                <p className="muted small">{TOOLS.find((t) => t.id === tool)?.hint}</p>
                <div className="tk-fields">
                  <label className="adm-field"><span>Lager</span>
                    <input value={layer} onChange={(e) => setLayer(e.target.value)} list="tk-layers" />
                    <datalist id="tk-layers">{(list?.layers ?? []).map((l: string) => <option key={l} value={l} />)}</datalist>
                  </label>
                  <label className="adm-field"><span>Beteckning</span>
                    <input value={designation} onChange={(e) => setDesignation(e.target.value)} placeholder="t.ex. VS21-S13-22" /></label>
                  <label className="adm-field"><span>Multiplikator</span>
                    <input type="number" step="0.1" value={props.multiplikator ?? ""} placeholder="1"
                      onChange={(e) => setProps({ ...props, multiplikator: e.target.value === "" ? undefined : Number(e.target.value) })} /></label>
                  {kind === "langd" && (
                    <label className="adm-field"><span>Tillägg m</span>
                      <input type="number" step="0.1" value={props.tillagg_m ?? ""} placeholder="0"
                        onChange={(e) => setProps({ ...props, tillagg_m: e.target.value === "" ? undefined : Number(e.target.value) })} /></label>
                  )}
                  {kind === "yta" && (
                    <label className="adm-field"><span>Djup m</span>
                      <input type="number" step="0.1" value={props.djup_m ?? ""} placeholder="0"
                        onChange={(e) => setProps({ ...props, djup_m: e.target.value === "" ? undefined : Number(e.target.value) })} /></label>
                  )}
                  {tool === "text" && (
                    <label className="adm-field"><span>Text</span>
                      <input value={text} onChange={(e) => setText(e.target.value)} /></label>
                  )}
                </div>
                <div className="row" style={{ marginTop: 10 }}>
                  <button disabled={!draft || busy} onClick={save}>{busy ? "Sparar…" : "Spara markering"}</button>
                  {draft && <button className="ghost small" onClick={() => setDraft(null)}>Rensa</button>}
                  <button className="ghost small" onClick={savePreset}>Spara som verktyg</button>
                  {preview && <span className="muted small">{preview}</span>}
                </div>
                {presets.length > 0 && (
                  <div className="tk-presets">
                    {presets.map((p) => (
                      <span key={p.id} className="tk-preset">
                        <button className="ghost small" onClick={() => applyPreset(p)}>{p.name}</button>
                        <button className="ghost small x" title="Ta bort"
                          onClick={async () => { await api.deleteToolPreset(p.id); setPresets((await api.toolPresets()).rows); }}>✕</button>
                      </span>
                    ))}
                  </div>
                )}
              </>
            )}
          </section>

          <section className="card">
            <h3 style={{ marginTop: 0 }}>Summor</h3>
            <div className="adm-stats">
              <div className="adm-stat"><div className="k">Längd</div><div className="v">{n2(list?.totals?.m)}</div><div className="s">meter</div></div>
              <div className="adm-stat"><div className="k">Yta</div><div className="v">{n2(list?.totals?.kvm)}</div><div className="s">m²</div></div>
              <div className="adm-stat"><div className="k">Volym</div><div className="v">{n2(list?.totals?.m3)}</div><div className="s">m³</div></div>
              <div className="adm-stat"><div className="k">Antal</div><div className="v">{list?.totals?.antal ?? 0}</div><div className="s">stycken</div></div>
            </div>
            {list?.unscaled > 0 && (
              <p className="muted small" style={{ marginBottom: 0 }}>
                {list.unscaled} markeringar saknar skala och räknas inte in i metrarna. Kalibrera bladet.
              </p>
            )}
          </section>

          <section className="card">
            <h3 style={{ marginTop: 0 }}>Markeringar</h3>
            {!rows.length && <p className="muted" style={{ marginBottom: 0 }}>Inga ännu. Välj ett verktyg och rita på bladet.</p>}
            {byLayer.map(([lay, items]) => (
              <div key={lay} className="tk-layer">
                <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
                  <b>{lay}</b>
                  <span className="muted small">
                    {n2(list.by_layer?.[lay]?.m)} m · {n2(list.by_layer?.[lay]?.kvm)} m² · {list.by_layer?.[lay]?.antal ?? 0} st
                  </span>
                </div>
                <table className="qty">
                  <tbody>
                    {items.map((r: any) => (
                      <tr key={r.id}>
                        <td className="lf-mono">{r.seq ? `${r.seq}. ` : ""}{r.designation || r.tool}
                          {r.text && <div className="muted small">{r.text}</div>}</td>
                        <td className="num">{measureText(r.measure)}</td>
                        <td className="num"><button className="ghost small" onClick={() => remove(r.id)}>Ta bort</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </section>
        </aside>
      </div>
    </main>
  );
}
