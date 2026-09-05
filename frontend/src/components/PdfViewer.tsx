import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, forwardRef } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

(pdfjsLib as any).GlobalWorkerOptions.workerSrc = workerUrl;

export type Layer = "pipes" | "ambiguous" | "unowned" | "designations" | "leaders" | "anchors";
export type EditKind = "extend" | "draw" | "erase" | null;

/** What a finished edit gesture produced: the line drawn, and what it does to the measurement. */
export interface Drawn {
  points: number[][];
  meters: number;
  /** erase only: the runs the stroke actually crossed, so the panel can name them. */
  hits?: string[];
}

// one colour per identity; none dark enough to read as the drawing's own black line work (same order as the engine palette)
const PALETTE = ["#0d9a1a", "#0059e6", "#d91a1a", "#8c00b3", "#009999", "#cc7300", "#4d4de6", "#99591a", "#e6007f", "#1a734d", "#808000", "#73bf00"];
export function identityColor(key: string): string {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

const len = (a: number[], b: number[]) => Math.hypot(b[0] - a[0], b[1] - a[1]);
const pathLen = (pts: number[][]) => pts.slice(1).reduce((s, q, i) => s + len(pts[i], q), 0);

/** Distance from point p to the segment ab. */
function segDist(p: number[], a: number[], b: number[]): number {
  const vx = b[0] - a[0], vy = b[1] - a[1];
  const L2 = vx * vx + vy * vy;
  if (L2 < 1e-9) return len(p, a);
  let t = ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p[0] - (a[0] + t * vx), p[1] - (a[1] + t * vy));
}

export interface ViewerProps {
  data: ArrayBuffer | null;
  page: number;
  pipes: any[];
  ambiguous: any[];
  unowned: any[];
  designations: any[];
  leaders: any[];
  anchors: any[];
  hatched?: any[];
  selectedIdentity: string | null;
  selectedPipe: string | null;
  layers: Record<Layer, boolean>;
  onPipeClick: (pipe: any) => void;
  onPageCount: (n: number) => void;
  /** Which edit gesture is armed. Selecting runs still works; the gesture takes over the empty sheet. */
  editKind?: EditKind;
  /** The run being edited, for extend: its free ends get grab handles. */
  editPipe?: any | null;
  meterPerPt?: number | null;
  onDrawn?: (d: Drawn) => void;
  corrections?: { id: string; kind: string; designation: string | null; payload: any }[];
}

export interface ViewerHandle {
  zoomIn(): void; zoomOut(): void; fitPage(): void; fitWidth(): void; fullscreen(): void;
  zoomTo(bbox: number[]): void;
}

const PdfViewer = forwardRef<ViewerHandle, ViewerProps>(function PdfViewer(props, ref) {
  const container = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [doc, setDoc] = useState<any>(null);
  const [scale, setScale] = useState(0.5);
  const [vp, setVp] = useState<{ w: number; h: number } | null>(null);
  const renderTask = useRef<any>(null);

  // --- edit gesture state -------------------------------------------------
  const [pending, setPending] = useState<number[][]>([]);   // the line being built (draw, extend)
  const [cursor, setCursor] = useState<number[] | null>(null);
  const [stroke, setStroke] = useState<number[][] | null>(null);  // the eraser stroke while the button is down
  const kind = props.editKind ?? null;

  useEffect(() => { setPending([]); setStroke(null); }, [kind, props.editPipe?.physical_pipe_id, props.page]);

  useEffect(() => {
    if (!props.data) return;
    let cancelled = false;
    pdfjsLib.getDocument({ data: props.data.slice(0) }).promise.then((d) => { if (!cancelled) { setDoc(d); props.onPageCount(d.numPages); } });
    return () => { cancelled = true; };
  }, [props.data]);

  const render = useCallback(async () => {
    if (!doc || !canvasRef.current) return;
    const page = await doc.getPage(props.page + 1);
    const viewport = page.getViewport({ scale, rotation: page.rotate });
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d")!;
    canvas.width = Math.floor(viewport.width); canvas.height = Math.floor(viewport.height);
    setVp({ w: viewport.width / scale, h: viewport.height / scale });
    if (renderTask.current) { try { renderTask.current.cancel(); } catch { /* ignore */ } }
    renderTask.current = page.render({ canvasContext: ctx, viewport });
    try { await renderTask.current.promise; } catch { /* cancelled */ }
  }, [doc, props.page, scale]);

  useEffect(() => { render(); }, [render]);

  const fit = useCallback((mode: "page" | "width") => {
    if (!vp || !container.current) return;
    const cw = container.current.clientWidth - 30, ch = container.current.clientHeight - 30;
    setScale(mode === "width" ? cw / vp.w : Math.min(cw / vp.w, ch / vp.h));
  }, [vp]);

  useImperativeHandle(ref, () => ({
    zoomIn: () => setScale((s) => Math.min(s * 1.25, 12)),
    zoomOut: () => setScale((s) => Math.max(s / 1.25, 0.1)),
    fitPage: () => fit("page"),
    fitWidth: () => fit("width"),
    fullscreen: () => container.current?.requestFullscreen?.(),
    zoomTo: (bbox: number[]) => {
      if (!container.current || !vp) return;
      const cw = container.current.clientWidth, ch = container.current.clientHeight;
      const bw = Math.max(bbox[2] - bbox[0], 20), bh = Math.max(bbox[3] - bbox[1], 20);
      const s = Math.min(cw / (bw * 4), ch / (bh * 4), 8);
      setScale(s);
      setTimeout(() => {
        const cx = (bbox[0] + bbox[2]) / 2 * s, cy = (bbox[1] + bbox[3]) / 2 * s;
        container.current!.scrollTo({ left: cx - cw / 2 + 12, top: cy - ch / 2 + 12 });
      }, 80);
    },
  }), [vp, fit]);

  const w = vp ? vp.w * scale : 0, h = vp ? vp.h * scale : 0;
  const sw = (pt: number) => pt / scale;                     // a screen-constant width in page units
  const mpp = props.meterPerPt ?? 0;
  const metres = (pts: number[][]) => pathLen(pts) * mpp;
  const fmt = (m: number) => `${m.toFixed(2).replace(".", ",")} m`;

  /** The ends of the run being extended: where a drag may start. */
  const handles: number[][] = useMemo(() => {
    if (kind !== "extend" || !props.editPipe) return [];
    const out: number[][] = [];
    for (const pl of props.editPipe.geometry ?? []) {
      if (pl.length >= 2) { out.push(pl[0]); out.push(pl[pl.length - 1]); }
    }
    return out;
  }, [kind, props.editPipe]);

  /** What the eraser stroke is currently over: those segments, and the metres they carry. */
  const erased = useMemo(() => {
    const empty = { segs: [] as number[][][], meters: 0, hits: [] as string[] };
    if (kind !== "erase" || !stroke || stroke.length === 0) return empty;
    const r = sw(7);
    const bx = [Math.min(...stroke.map((p) => p[0])) - r, Math.min(...stroke.map((p) => p[1])) - r,
                Math.max(...stroke.map((p) => p[0])) + r, Math.max(...stroke.map((p) => p[1])) + r];
    const segs: number[][][] = [];
    const hits = new Set<string>();
    let m = 0;
    // the eraser only takes from the run you picked: one correction, one designation, an exact metre count
    const only = props.editPipe?.identity ?? null;
    for (const p of props.pipes) {
      if (only && p.identity !== only) continue;
      for (const pl of p.geometry ?? []) {
        if (pl.length < 2) continue;
        const xs = pl.map((q: number[]) => q[0]), ys = pl.map((q: number[]) => q[1]);
        if (Math.max(...xs) < bx[0] || Math.min(...xs) > bx[2] || Math.max(...ys) < bx[1] || Math.min(...ys) > bx[3]) continue;
        for (let i = 1; i < pl.length; i++) {
          const a = pl[i - 1], b = pl[i];
          if (stroke.some((q) => segDist(q, a, b) <= r)) {
            segs.push([a, b]);
            m += len(a, b) * mpp;
            hits.add(p.designation ?? p.identity);
          }
        }
      }
    }
    return { segs, meters: m, hits: [...hits] };
  }, [kind, stroke, props.pipes, props.editPipe, scale, mpp]);

  // --- pointer plumbing ---------------------------------------------------
  const at = (e: React.MouseEvent): number[] => {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    return [Number(((e.clientX - r.left) / scale).toFixed(2)), Number(((e.clientY - r.top) / scale).toFixed(2))];
  };

  const down = (e: React.MouseEvent) => {
    if (!kind || !vp) return;
    const pt = at(e);
    if (kind === "extend") {
      // a drag may only start at an end of the run: that is what "extend" means
      const near = handles.find((q) => len(q, pt) <= sw(11));
      if (near) { e.preventDefault(); setPending([near]); }
      return;
    }
    if (kind === "erase") { e.preventDefault(); setStroke([pt]); }
  };

  const move = (e: React.MouseEvent) => {
    if (!kind || !vp) return;
    const pt = at(e);
    setCursor(pt);
    if (kind === "erase" && stroke) {
      // one point every few screen pixels: enough to follow the hand, few enough to test cheaply
      if (len(stroke[stroke.length - 1], pt) >= sw(4)) setStroke([...stroke, pt]);
    }
  };

  const up = () => {
    if (kind === "extend" && pending.length === 1 && cursor && len(pending[0], cursor) > sw(6)) {
      const pts = [pending[0], cursor];
      props.onDrawn?.({ points: pts, meters: metres(pts) });
      setPending([]);
      return;
    }
    if (kind === "extend") { setPending([]); return; }
    if (kind === "erase" && stroke) {
      if (erased.segs.length > 0) props.onDrawn?.({ points: stroke, meters: erased.meters, hits: erased.hits });
      setStroke(null);
    }
  };

  // draw is click-to-place: a run the engine never saw has no end to grab
  const click = (e: React.MouseEvent) => {
    if (kind !== "draw" || !vp) return;
    setPending((q) => [...q, at(e)]);
  };
  const finish = () => {
    if (kind !== "draw" || pending.length < 2) return;
    props.onDrawn?.({ points: pending, meters: metres(pending) });
    setPending([]);
  };

  useEffect(() => {
    if (kind !== "draw") return;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPending([]);
      if (e.key === "Enter") { setPending((q) => { if (q.length >= 2) props.onDrawn?.({ points: q, meters: metres(q) }); return []; }); }
      if (e.key === "Backspace") { e.preventDefault(); setPending((q) => q.slice(0, -1)); }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [kind, mpp]);

  // the rubber band: from the last placed point (or the grabbed end) to where the hand is
  const band = pending.length > 0 && cursor ? [pending[pending.length - 1], cursor] : null;
  const liveM = band ? metres(kind === "draw" ? [...pending, cursor!] : band) : (kind === "erase" ? erased.meters : 0);
  const cur = kind === "extend" ? (pending.length ? "crosshair" : "default") : kind ? "crosshair" : undefined;

  return (
    <div className="viewer" ref={container}>
      <div className={`page${kind ? " editing" : ""}`} style={{ width: w, height: h, cursor: cur }}
        onClick={click} onDoubleClick={finish} onMouseDown={down} onMouseMove={move} onMouseUp={up}
        onMouseLeave={() => { setCursor(null); if (stroke) up(); }}>
        <canvas ref={canvasRef} />
        {vp && (
          <svg width={w} height={h} viewBox={`0 0 ${vp.w} ${vp.h}`} style={{ pointerEvents: "none" }}>
            {props.layers.unowned && props.unowned.map((g, i) => (
              <line key={`u${i}`} x1={g.x0} y1={g.y0} x2={g.x1} y2={g.y1} stroke="#8a8f99" strokeWidth={sw(2)} strokeOpacity={0.8} />
            ))}
            {props.layers.ambiguous && props.ambiguous.map((g, i) => (
              <line key={`a${i}`} x1={g.x0} y1={g.y0} x2={g.x1} y2={g.y1} stroke="#ff9500" strokeWidth={sw(3)} strokeOpacity={0.9} />
            ))}
            {props.layers.pipes && props.pipes.map((p) => {
              const sel = props.selectedPipe === p.physical_pipe_id || (props.selectedIdentity !== null && props.selectedIdentity === p.identity);
              const dim = props.selectedIdentity !== null && !sel;
              const pick = kind === "erase" || kind === "draw" ? "none" : "stroke";
              return p.geometry.map((pl: number[][], k: number) => {
                const pts = pl.map((q) => q.join(",")).join(" ");
                return (
                  <g key={`${p.physical_pipe_id}-${k}`}>
                    {/* a wider invisible line over the same path: a run is a hairline on screen and picking one
                        should not ask for that precision */}
                    <polyline points={pts} fill="none" stroke="transparent" strokeWidth={sw(14)}
                      strokeLinecap="round" strokeLinejoin="round"
                      style={{ pointerEvents: pick, cursor: "pointer" }} onClick={() => props.onPipeClick(p)} />
                    <polyline points={pts} fill="none"
                      stroke={sel ? "#ff2d00" : identityColor(p.identity)} strokeWidth={sw(sel ? 5 : 3.2)}
                      strokeOpacity={dim ? 0.25 : 0.85} strokeLinecap="round" strokeLinejoin="round"
                      style={{ pointerEvents: "none" }} />
                  </g>
                );
              });
            })}
            {props.layers.pipes && (props.hatched ?? []).map((g, i) => (
              <line key={`h${i}`} x1={g.x0} y1={g.y0} x2={g.x1} y2={g.y1} stroke="#6b7280" strokeWidth={sw(3.4)} strokeDasharray={`${sw(4)} ${sw(3)}`} strokeOpacity={0.95} />
            ))}
            {props.layers.leaders && props.leaders.map((l) => (
              <polyline key={l.id} points={l.points.map((q: number[]) => q.join(",")).join(" ")} fill="none" stroke="#b000b0" strokeWidth={sw(1.2)} />
            ))}
            {props.layers.designations && props.designations.map((d) => (
              <rect key={d.id} x={d.bbox[0] - 1} y={d.bbox[1] - 1} width={d.bbox[2] - d.bbox[0] + 2} height={d.bbox[3] - d.bbox[1] + 2}
                fill="none" stroke={d.dn != null ? "#0b5cad" : "#c77800"} strokeWidth={sw(1)} />
            ))}
            {(props.corrections ?? []).map((c) => (
              (c.payload?.points?.length ?? 0) >= 2 && (
                <polyline key={c.id} points={c.payload.points.map((q: number[]) => q.join(",")).join(" ")} fill="none"
                  stroke={c.kind === "erase" ? "#b42318" : "#0d0d0d"} strokeWidth={sw(4)} strokeOpacity={0.9}
                  strokeDasharray={c.kind === "erase" ? `${sw(6)} ${sw(4)}` : undefined}
                  strokeLinecap="round" strokeLinejoin="round" />
              )
            ))}

            {/* what the eraser is over right now, struck through in red as the hand moves */}
            {erased.segs.map(([a, b], i) => (
              <line key={`x${i}`} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke="#b42318" strokeWidth={sw(6)} strokeOpacity={0.85} strokeLinecap="round" />
            ))}
            {stroke && stroke.length > 1 && (
              <polyline points={stroke.map((q) => q.join(",")).join(" ")} fill="none" stroke="#b42318"
                strokeWidth={sw(14)} strokeOpacity={0.16} strokeLinecap="round" strokeLinejoin="round" />
            )}

            {/* the ends of the selected run: grab one and pull */}
            {handles.map((q, i) => (
              <g key={`hd${i}`}>
                <circle cx={q[0]} cy={q[1]} r={sw(8)} fill="#ffffff" fillOpacity={0.85} stroke="#ff2d00" strokeWidth={sw(2)} />
                <circle cx={q[0]} cy={q[1]} r={sw(2.6)} fill="#ff2d00" />
              </g>
            ))}

            {/* the line being made */}
            {pending.length > 1 && (
              <polyline points={pending.map((q) => q.join(",")).join(" ")} fill="none" stroke="#0d0d0d"
                strokeWidth={sw(4)} strokeLinecap="round" strokeLinejoin="round" />
            )}
            {band && (
              <line x1={band[0][0]} y1={band[0][1]} x2={band[1][0]} y2={band[1][1]} stroke="#0d0d0d"
                strokeWidth={sw(4)} strokeDasharray={`${sw(6)} ${sw(4)}`} strokeLinecap="round" />
            )}
            {pending.map((q, i) => (
              <circle key={`pp${i}`} cx={q[0]} cy={q[1]} r={sw(3)} fill="#0d0d0d" />
            ))}

            {/* the running length, at the hand, so the metre is visible before it is saved */}
            {cursor && mpp > 0 && (band || (kind === "erase" && erased.meters > 0)) && (
              <g transform={`translate(${cursor[0] + sw(12)}, ${cursor[1] - sw(10)})`}>
                <rect x={0} y={sw(-13)} width={sw(kind === "erase" ? 88 : 74)} height={sw(19)} rx={sw(4)}
                  fill={kind === "erase" ? "#b42318" : "#0d0d0d"} fillOpacity={0.92} />
                <text x={sw(7)} y={sw(0.5)} fill="#fff" fontSize={sw(12)} fontFamily="ui-monospace, SFMono-Regular, monospace">
                  {kind === "erase" ? `− ${fmt(liveM)}` : `+ ${fmt(liveM)}`}
                </text>
              </g>
            )}

            {props.layers.anchors && props.anchors.map((a) => (
              <circle key={a.id} cx={a.endpoint[0]} cy={a.endpoint[1]} r={sw(4)} fill="none"
                stroke={a.state === "VERIFIED_PIPE_ATTACHMENT" ? "#12a24b" : a.state === "AMBIGUOUS_PIPE_ATTACHMENT" ? "#ff9500" : "#b42318"} strokeWidth={sw(1.5)} />
            ))}
          </svg>
        )}
      </div>
    </div>
  );
});

export default PdfViewer;
