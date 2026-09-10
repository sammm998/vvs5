import { useCallback, useEffect, useImperativeHandle, useLayoutEffect, useMemo, useRef, useState, forwardRef } from "react";
import * as pdfjsLib from "pdfjs-dist";
import { ROLE_COLOR, ROLE_LABEL, legendOwner } from "../legend";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

(pdfjsLib as any).GlobalWorkerOptions.workerSrc = workerUrl;

export type Layer = "pipes" | "ambiguous" | "claimed" | "unowned" | "declined" | "designations" | "legend" | "leaders" | "anchors" | "inWall";
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

/** What the reading made of one piece of drawn ink, in the words a reader asks the question in. */
export type InkVerdict = {
  at: number[];
  kind: "matt" | "i-vagg" | "tvetydig" | "papekad" | "oidentifierad" | "bortvald" | "inget";
  title: string;
  detail: string;
  pipe?: any;
};

export interface ViewerProps {
  data: ArrayBuffer | null;
  page: number;
  pipes: any[];
  ambiguous: any[];
  unowned: any[];
  claimed: any[];
  designations: any[];
  legend?: { entries: any[] } | null;
  leaders: any[];
  anchors: any[];
  hatched?: any[];
  /** Ink that never became pipe: families weighed and set aside, and families no leader ever pointed at. */
  declined?: { family: string; kind: string; why_sv?: string; why?: string; layer?: string; style?: string; length_m?: number | null; segments: number[][] }[];
  /** One declined family picked out of the rest, so a reader can see which ink a row is talking about. */
  selectedDeclined?: string | null;
  selectedIdentity: string | null;
  selectedPipe: string | null;
  layers: Record<Layer, boolean>;
  onPipeClick: (pipe: any) => void;
  /** A click on ink with no edit mode active: what the reading made of it. */
  onInkClick?: (v: InkVerdict | null) => void;
  /** The standing answer, drawn on the sheet where it was asked. */
  ink?: InkVerdict | null;
  onPageCount: (n: number) => void;
  /** Which edit gesture is armed. Selecting runs still works; the gesture takes over the empty sheet. */
  editKind?: EditKind;
  /** The run being edited, for extend: its free ends get grab handles. */
  editPipe?: any | null;
  meterPerPt?: number | null;
  onDrawn?: (d: Drawn) => void;
  corrections?: { id: string; kind: string; designation: string | null; payload: any }[];
  /** What the reader drew in by hand: measured, marked or noted. Beside the reading, never in it. */
  markups?: { id: string; tool: string; points: number[][]; layer?: string; text?: string; measure?: any }[];
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

  // A drawing opens showing the whole drawing. Landing at an arbitrary zoom means the first thing a reader does
  // is hunt for the sheet, and the question they came to answer - did it get the pipes? - is about all of it.
  //
  // It keeps fitting while the frame is still settling: the panel beside it is draggable, the window resizes, and
  // a fit computed against a container that had not reached its height yet leaves the sheet floating in an empty
  // box. The moment the reader zooms or drags themselves, the zoom is theirs and this stops.
  const auto = useRef(true);
  useEffect(() => { auto.current = true; }, [props.page, doc]);
  useEffect(() => {
    if (!vp || !doc || !auto.current) return;
    fit("page");
  }, [vp, doc, props.page, fit]);
  useEffect(() => {
    const el = container.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => { if (auto.current) fit("page"); });
    ro.observe(el);
    return () => ro.disconnect();
  }, [fit]);

  useImperativeHandle(ref, () => ({
    zoomIn: () => { auto.current = false; setScale((s) => Math.min(s * 1.25, 12)); },
    zoomOut: () => { auto.current = false; setScale((s) => Math.max(s / 1.25, 0.1)); },
    fitPage: () => { auto.current = true; fit("page"); },
    fitWidth: () => { auto.current = false; fit("width"); },
    fullscreen: () => container.current?.requestFullscreen?.(),
    /* Go to a run: near enough to work on, and without losing where it is.
     *
     * A run already on screen is only scrolled to - re-scaling the sheet under a reader who can already see the
     * thing they asked for is disorienting, and it costs a full re-render of the page. One that is off screen,
     * or too small to work on, is scaled to fill about a third of the frame and then centred. Either way the
     * sheet moves smoothly and a ring lands on the run, so the eye follows rather than searches.
     */
    zoomTo: (bbox: number[]) => {
      const el = container.current;
      if (!el || !vp || !bbox) return;
      auto.current = false;
      const cw = el.clientWidth, ch = el.clientHeight;
      const bw = Math.max(bbox[2] - bbox[0], 8), bh = Math.max(bbox[3] - bbox[1], 8);
      // the size a run wants to be worked on at: filling about half the frame, with room around it
      const want = Math.max(0.05, Math.min(cw / (bw * 2.2), ch / (bh * 2.2), 8));
      const fits = bw * scale <= cw * 0.9 && bh * scale <= ch * 0.9;
      // Closer than the run needs is the reader's own choice and is left alone; further away is not, because
      // then the thing they asked to see is a few pixels of a whole sheet. A run too big for the frame is
      // pulled back until it fits, however close the reader was.
      const s = !fits ? want : (want > scale ? want : scale);
      const centre = () => {
        const pe = pageEl.current;
        if (!pe) return;
        const r = pe.getBoundingClientRect();
        const vr = el.getBoundingClientRect();
        // the run's middle, in the frame's own coordinates, brought to the middle of the frame
        el.scrollTo({ left: el.scrollLeft + (r.left + (bbox[0] + bbox[2]) / 2 * s) - (vr.left + cw / 2),
                      top: el.scrollTop + (r.top + (bbox[1] + bbox[3]) / 2 * s) - (vr.top + ch / 2),
                      behavior: "smooth" });
      };
      setFlash({ x: (bbox[0] + bbox[2]) / 2, y: (bbox[1] + bbox[3]) / 2, r: Math.max(bw, bh) / 2 + 6, at: Date.now() });
      if (s === scale) { centre(); return; }
      setScale(s);
      requestAnimationFrame(() => requestAnimationFrame(centre));
    },
  }), [vp, fit, scale]);

  /* Zoom and pan, the way a drawing is read.
   *
   * A takeoff is done at 400 % on one corner and then at 30 % to see where that corner was, and doing that with
   * the browser's own zoom scales the whole application - the panel, the table, the toolbar - so the reader
   * loses the numbers they are checking the drawing against. So the sheet zooms on its own: the wheel scales it
   * about the point under the pointer, and dragging moves it. Nothing else on the page moves.
   */
  const pageEl = useRef<HTMLDivElement | null>(null);
  const [panning, setPanning] = useState(false);
  const [flash, setFlash] = useState<{ x: number; y: number; r: number; at: number } | null>(null);
  const pan = useRef<{ x: number; y: number; l: number; t: number } | null>(null);
  // where the pointer was over the sheet when a zoom began, kept until the new size has been laid out
  const hold = useRef<{ px: number; py: number; cx: number; cy: number } | null>(null);

  const zoomAt = useCallback((factor: number, cx: number, cy: number) => {
    const el = container.current, pe = pageEl.current;
    if (!el || !pe) return;
    auto.current = false;
    const r = pe.getBoundingClientRect();
    setScale((s) => {
      const next = Math.min(12, Math.max(0.05, s * factor));
      hold.current = { px: (cx - r.left) / s, py: (cy - r.top) / s, cx, cy };
      return next;
    });
  }, []);

  // after the sheet has been laid out at its new size, put the held point back under the pointer
  useLayoutEffect(() => {
    const el = container.current, pe = pageEl.current, hcur = hold.current;
    if (!el || !pe || !hcur) return;
    hold.current = null;
    const r = pe.getBoundingClientRect();
    el.scrollLeft += (r.left + hcur.px * scale) - hcur.cx;
    el.scrollTop += (r.top + hcur.py * scale) - hcur.cy;
  }, [scale]);

  const onWheel = useCallback((e: React.WheelEvent) => {
    if (e.shiftKey) return;                       // shift-wheel keeps the browser's own sideways scroll
    e.preventDefault();
    zoomAt(Math.exp(-e.deltaY * 0.0016), e.clientX, e.clientY);
  }, [zoomAt]);

  // Dragging pans, except while a correction is being drawn - then the drag is the drawing. The middle button
  // always pans, so a reader in the middle of an edit can still move the sheet.
  // A press is not yet a drag. Capturing the pointer on the way down retargets everything that follows to the
  // frame, so the click never reaches the run under the finger - and picking a run by clicking it, which is
  // what the correction panel asks you to do, did nothing at all. The pan starts when the hand actually moves.
  const PAN_SLOP = 4;
  const panDown = (e: React.PointerEvent) => {
    if (e.button !== 1 && (e.button !== 0 || kind)) return;
    const el = container.current;
    if (!el) return;
    pan.current = { x: e.clientX, y: e.clientY, l: el.scrollLeft, t: el.scrollTop };
  };
  const panMove = (e: React.PointerEvent) => {
    const el = container.current, p = pan.current;
    if (!el || !p) return;
    const dx = e.clientX - p.x, dy = e.clientY - p.y;
    if (!panning) {
      if (Math.abs(dx) < PAN_SLOP && Math.abs(dy) < PAN_SLOP) return;
      auto.current = false;
      setPanning(true);
      (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
    }
    el.scrollLeft = p.l - dx;
    el.scrollTop = p.t - dy;
  };
  const panUp = (e: React.PointerEvent) => {
    if (!pan.current) return;
    pan.current = null;
    if (panning) {
      setPanning(false);
      (e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);
    }
  };

  // the wheel listener has to be non-passive to be allowed to hold the page still while the sheet zooms
  useEffect(() => {
    const el = container.current;
    if (!el) return;
    const stop = (ev: WheelEvent) => { if (!ev.shiftKey) ev.preventDefault(); };
    el.addEventListener("wheel", stop, { passive: false });
    return () => el.removeEventListener("wheel", stop);
  }, []);

  const w = vp ? vp.w * scale : 0, h = vp ? vp.h * scale : 0;
  const sw = (pt: number) => pt / scale;                     // a screen-constant width in page units
  const mpp = props.meterPerPt ?? 0;
  const metres = (pts: number[][]) => pathLen(pts) * mpp;
  const fmt = (m: number) => `${m.toFixed(2).replace(".", ",")} m`;

  /** The ends of the run being extended: where a drag may start. */
  const handles: number[][] = useMemo(() => {
    // a run belongs to the page it was found on: its ends mean nothing over another page's geometry, and a drag
    // from one would file a correction against this page using the other page's coordinates
    if (kind !== "extend" || !props.editPipe || (props.editPipe.page ?? 0) !== props.page) return [];
    const out: number[][] = [];
    for (const pl of props.editPipe.geometry ?? []) {
      if (pl.length >= 2) { out.push(pl[0]); out.push(pl[pl.length - 1]); }
    }
    return out;
  }, [kind, props.editPipe, props.page]);

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
    // pipe inside a hatched area is measured but kept out of the row's horizontal metres, so erasing over it
    // would subtract length the row never held. Those segments are skipped by their own coordinates.
    const hatch = new Set((props.hatched ?? []).map((g: any) =>
      `${Math.round(g.x0 * 20)},${Math.round(g.y0 * 20)},${Math.round(g.x1 * 20)},${Math.round(g.y1 * 20)}`));
    const isHatched = (a: number[], b: number[]) => {
      const k1 = `${Math.round(a[0] * 20)},${Math.round(a[1] * 20)},${Math.round(b[0] * 20)},${Math.round(b[1] * 20)}`;
      const k2 = `${Math.round(b[0] * 20)},${Math.round(b[1] * 20)},${Math.round(a[0] * 20)},${Math.round(a[1] * 20)}`;
      return hatch.has(k1) || hatch.has(k2);
    };
    for (const p of props.pipes) {
      if (only && p.identity !== only) continue;
      for (const pl of p.geometry ?? []) {
        if (pl.length < 2) continue;
        const xs = pl.map((q: number[]) => q[0]), ys = pl.map((q: number[]) => q[1]);
        if (Math.max(...xs) < bx[0] || Math.min(...xs) > bx[2] || Math.max(...ys) < bx[1] || Math.min(...ys) > bx[3]) continue;
        for (let i = 1; i < pl.length; i++) {
          const a = pl[i - 1], b = pl[i];
          if (stroke.some((q) => segDist(q, a, b) <= r)) {
            if (isHatched(a, b)) continue;
            segs.push([a, b]);
            m += len(a, b) * mpp;
            hits.add(p.designation ?? p.identity);
          }
        }
      }
    }
    return { segs, meters: m, hits: [...hits] };
  }, [kind, stroke, props.pipes, props.editPipe, props.hatched, scale, mpp]);

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

  /* What the reading made of the ink under the cursor.
   *
   * "Varför är det röret inte markerat?" is the question a reader asks of a drawing, and until now the answer
   * lived in five separate layers they had to know to switch on and then hunt through. Every one of those layers
   * is already in the result, so the question can simply be asked of the sheet: click the line, and the reading
   * says which of its answers this ink got - measured, in a wall, ambiguous, pointed at but unnamed, drawn pipe
   * no label reached, ink weighed and set aside as not pipe, or nothing kept here at all.
   */
  const askInk = (pt: number[]): InkVerdict => {
    const tol = sw(7);
    let bestD = Infinity;
    let best: InkVerdict | null = null;
    const take = (d: number, v: InkVerdict) => { if (d <= tol && d < bestD) { bestD = d; best = v; } };
    const m = (x: number) => `${x.toFixed(2).replace(".", ",")} m`;

    for (const p of props.pipes) {
      for (const pl of p.geometry as number[][][]) {
        for (let i = 1; i < pl.length; i++) {
          take(segDist(pt, pl[i - 1], pl[i]), {
            at: pt, kind: "matt", pipe: p,
            title: `Mätt: ${p.identity ?? "rör"}`,
            detail: `${typeof p.horizontal_m === "number" ? m(p.horizontal_m) : "ingen skala"} · sträcka ${p.physical_pipe_id?.slice(-8) ?? ""}`,
          });
        }
      }
    }
    for (const g of props.hatched ?? []) {
      take(segDist(pt, [g.x0, g.y0], [g.x1, g.y1]), {
        at: pt, kind: "i-vagg",
        title: `I vägg: ${g.identity ?? "rör"}`,
        detail: "Mätt, men längden i en skrafferad yta ligger utanför den horisontella mängden. Kryssa i \u201erräkna med skrafferade ytor\u201d för att ta med den.",
      });
    }
    for (const g of props.ambiguous) {
      take(segDist(pt, [g.x0, g.y0], [g.x1, g.y1]), {
        at: pt, kind: "tvetydig",
        title: "Tvetydig",
        detail: `Kunde tillhöra ${(g.candidates || []).join(" eller ") || "mer än en beteckning"}. Ritningen avgör det inte, så sträckan mäts inte. Skäl: ${g.reason || "okänt"}.`,
      });
    }
    for (const g of props.claimed ?? []) {
      take(segDist(pt, [g.x0, g.y0], [g.x1, g.y1]), {
        at: pt, kind: "papekad",
        title: "Påpekad men onämnd",
        detail: `${(g.claimed_by || []).join(", ") || "En beteckning"} pekar hit, men läsningen kunde inte ge sträckan till en enda identitet. Den finns på ritningen och mäts inte.`,
      });
    }
    for (const g of props.unowned) {
      take(segDist(pt, [g.x0, g.y0], [g.x1, g.y1]), {
        at: pt, kind: "oidentifierad",
        title: "Ritad som rör, men ingen beteckning nådde hit",
        detail: "Läsningen tog den här pennan som rörgeometri, men ingen hänvisningslinje slutar på den här sträckan. Utan en etikett som pekar på den har den inget namn — och utan namn ingen mängd.",
      });
    }
    for (const f of props.declined ?? []) {
      for (const g of f.segments) {
        take(segDist(pt, [g[0], g[1]], [g[2], g[3]]), {
          at: pt, kind: "bortvald",
          title: f.kind === "not_examined" ? "Aldrig vägd som rör" : "Bortvald: inte rör",
          // the layer name is what a draughtsman recognises; the stroke style is an internal key and only noise here
          detail: `${f.why_sv || f.why || "inget skäl noterat"}${f.layer ? ` · lager ${f.layer}` : ""}`,
        });
      }
    }
    // a measured run already answers when it is clicked - it selects itself and opens "Varför?" - so the card
    // stays out of the way there and speaks for everything else
    const v = best as InkVerdict | null;
    if (v && v.kind === "matt" && props.layers.pipes) return v;
    return v ?? {
      at: pt, kind: "inget", title: "Ingen sparad geometri här",
      detail: "Läsningen har inget kvar på den här punkten. Zooma in och klicka närmare linjen, eller slå på fler lager för att se vad som finns.",
    };
  };

  // draw is click-to-place: a run the engine never saw has no end to grab
  const click = (e: React.MouseEvent) => {
    if (!vp) return;
    if (!kind) {
      // reading the point while it is still an event, as everywhere else here
      const pt = at(e);
      const v = askInk(pt);
      // the pipe's own click has already selected it and opened the evidence panel; no card on top of that
      props.onInkClick?.(v.kind === "matt" && props.layers.pipes ? null : v);
      return;
    }
    if (kind !== "draw") return;
    // The point is read here and not inside the update. A functional update is called by React when it gets
    // round to it, which is after the event has been handed back - and then currentTarget is null and reading
    // the sheet's rectangle off it throws, taking the whole page with it. An event is only an event during its
    // own handler.
    const pt = at(e);
    setPending((q) => [...q, pt]);
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
      if (e.key === "Enter") finish();
      if (e.key === "Backspace") { e.preventDefault(); setPending((q) => q.slice(0, -1)); }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
    // finish() reads the points placed so far, so the listener has to be rebound as they are placed
  }, [kind, pending, mpp, props.onDrawn]);

  // the rubber band: from the last placed point (or the grabbed end) to where the hand is
  const band = pending.length > 0 && cursor ? [pending[pending.length - 1], cursor] : null;
  const liveM = band ? metres(kind === "draw" ? [...pending, cursor!] : band) : (kind === "erase" ? erased.meters : 0);
  const cur = kind === "extend" ? (pending.length ? "crosshair" : "default") : kind ? "crosshair" : undefined;

  return (
    <div className="viewer" ref={container} onWheel={onWheel}
      onPointerDown={panDown} onPointerMove={panMove} onPointerUp={panUp} onPointerCancel={panUp}>
      <div ref={pageEl} className={`page${kind ? " editing" : ""}${panning ? " panning" : ""}`}
        style={{ width: w, height: h, cursor: panning ? "grabbing" : cur }}
        onClick={click} onDoubleClick={finish} onMouseDown={down} onMouseMove={move} onMouseUp={up}
        onMouseLeave={() => { setCursor(null); if (stroke) up(); }}>
        <canvas ref={canvasRef} />
        {vp && (
          <svg width={w} height={h} viewBox={`0 0 ${vp.w} ${vp.h}`} style={{ pointerEvents: "none" }}>
            {/* Ink the reading declined, drawn faintly so it never competes with a measured run: it is here to
                say "this was looked at and read as something other than pipe", not to be read as a quantity. */}
            {props.layers.declined && (props.declined ?? []).map((f) =>
              f.segments.map((g, i) => {
                const on = props.selectedDeclined === f.family;
                // ink the reading never weighed is drawn fainter than ink it weighed and set aside: the two are
                // different answers and should not look like the same one
                const seen = f.kind !== "not_examined";
                return <line key={`d${f.family}-${i}`} x1={g[0]} y1={g[1]} x2={g[2]} y2={g[3]}
                  stroke={on ? "#0891b2" : "#94a3b8"} strokeWidth={sw(on ? 3 : 1.6)}
                  strokeDasharray={on ? undefined : `${sw(3)} ${sw(3)}`} strokeOpacity={on ? 0.95 : seen ? 0.5 : 0.28} />;
              }))}
            {props.layers.unowned && props.unowned.map((g, i) => (
              <line key={`u${i}`} x1={g.x0} y1={g.y0} x2={g.x1} y2={g.y1} stroke="#8a8f99" strokeWidth={sw(2)} strokeOpacity={0.8} />
            ))}
            {/* A line a designation's leader reaches that the reading could not give to one identity. It is not
                measured and it must not be invisible either: hidden, a drawn and labelled pipe looks missing. */}
            {props.layers.claimed && (props.claimed ?? []).map((g, i) => (
              <line key={`c${i}`} x1={g.x0} y1={g.y0} x2={g.x1} y2={g.y1} stroke="#a855f7" strokeWidth={sw(3)}
                strokeOpacity={0.9} strokeDasharray={`${sw(7)} ${sw(4)}`}>
                <title>{`Påpekad av ${(g.claimed_by || []).join(", ")} — läsningen kunde inte avgöra vilken`}</title>
              </line>
            ))}
            {props.layers.ambiguous && props.ambiguous.map((g, i) => (
              <line key={`a${i}`} x1={g.x0} y1={g.y0} x2={g.x1} y2={g.y1} stroke="#ff9500" strokeWidth={sw(3)} strokeOpacity={0.9} />
            ))}
            {flash && (
              <circle key={flash.at} className="focusring" cx={flash.x} cy={flash.y} r={flash.r}
                fill="none" stroke="#ff5a3d" strokeWidth={sw(2.5)} />
            )}
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
            {/* The part of a run that lies inside a wall is drawn length that the horizontal quantity already
                leaves out, so it may not wear the run's colour: painted over in the colour of what is not
                counted, always, whatever else is switched on. The layer switch only makes it louder. */}
            {(props.hatched ?? []).map((g, i) => (
              <line key={`h${i}`} x1={g.x0} y1={g.y0} x2={g.x1} y2={g.y1}
                stroke={props.layers.inWall ? "#6b7280" : "#c4c8cf"} strokeWidth={sw(props.layers.inWall ? 3.6 : 3.4)}
                strokeDasharray={`${sw(4)} ${sw(3)}`} strokeOpacity={props.layers.inWall ? 0.95 : 0.85} />
            ))}
            {/* Nothing the reading found is hidden. What sits over a hatched wall used to disappear unless the
                "i vägg" layer was on, and a label the reading did read then looked exactly like one it had
                missed. The wall still matters - the length there is outside the quantity - so it is said by
                drawing it faintly, the same way the pipe itself is. */}
            {props.layers.leaders && props.leaders.map((l) => (
              <polyline key={l.id} points={l.points.map((q: number[]) => q.join(",")).join(" ")} fill="none"
                stroke="#b000b0" strokeWidth={sw(1.2)}
                strokeOpacity={l.in_wall && !props.layers.inWall ? 0.3 : 1} />
            ))}
            {props.layers.designations && props.designations.map((d) => (
              <rect key={d.id} x={d.bbox[0] - 1} y={d.bbox[1] - 1} width={d.bbox[2] - d.bbox[0] + 2} height={d.bbox[3] - d.bbox[1] + 2}
                fill="none" stroke={!d.names_a_pipe ? "#9aa3af" : d.dn != null ? "#0b5cad" : "#c77800"}
                strokeOpacity={d.in_wall && !props.layers.inWall ? 0.35 : 1}
                strokeWidth={sw(1)} strokeDasharray={d.names_a_pipe ? undefined : `${sw(3)} ${sw(2)}`} />
            ))}
            {/* Every label on the sheet coloured by what the drawing's own designation list says its code is: a
                pipe system, a fitting, a material - or nothing, when the list does not carry the code at all.
                It is the fastest way to see whether the list was read the way the sheet meant it. */}
            {props.layers.legend && (() => {
              const entries = props.legend?.entries ?? [];
              const box = entries.map((e: any) => e.bbox).filter((b: number[]) => b && (b[2] - b[0]) > 0);
              return (
                <g>
                  {box.map((b: number[], i: number) => (
                    <rect key={`lgb${i}`} x={b[0] - 1.5} y={b[1] - 1.5} width={b[2] - b[0] + 3} height={b[3] - b[1] + 3}
                      fill="#0d0d0d" fillOpacity={0.05} stroke="#0d0d0d" strokeOpacity={0.3} strokeWidth={sw(0.8)} />
                  ))}
                  {props.designations.map((d) => {
                    const e = legendOwner(entries, d.text || "");
                    const c = e ? (ROLE_COLOR[e.role] ?? ROLE_COLOR.unused) : "#c026d3";
                    return (
                      <g key={`lg${d.id}`}>
                        <title>{e ? `${e.code} — ${e.description || "ingen förklaring"} · ${ROLE_LABEL[e.role] ?? e.role}` : `${d.text} står inte i förklaringslistan`}</title>
                        <rect x={d.bbox[0] - 1.5} y={d.bbox[1] - 1.5} width={d.bbox[2] - d.bbox[0] + 3} height={d.bbox[3] - d.bbox[1] + 3}
                          fill={c} fillOpacity={0.13} stroke={c} strokeWidth={sw(1.2)}
                          strokeDasharray={e ? undefined : `${sw(3)} ${sw(2)}`} />
                      </g>
                    );
                  })}
                </g>
              );
            })()}
            {(props.corrections ?? []).map((c) => (
              (c.payload?.points?.length ?? 0) >= 2 && (
                <polyline key={c.id} points={c.payload.points.map((q: number[]) => q.join(",")).join(" ")} fill="none"
                  stroke={c.kind === "erase" ? "#b42318" : "#0d0d0d"} strokeWidth={sw(4)} strokeOpacity={0.9}
                  strokeDasharray={c.kind === "erase" ? `${sw(6)} ${sw(4)}` : undefined}
                  strokeLinecap="round" strokeLinejoin="round" />
              )
            ))}

            {/* the reader's own markups: teal so they never read as the reading's colours or the drawing's black */}
            {(props.markups ?? []).map((m) => {
              const pts = m.points || [];
              const me = m.measure || {};
              const label = typeof me.kvm === "number" ? `${me.kvm.toFixed(2)} m²`
                : typeof me.m === "number" ? `${me.m.toFixed(2)} m`
                : typeof me.antal === "number" ? `${me.antal} st` : (m.text || "");
              const anchor = pts[0];
              if (m.tool === "antal") {
                return (
                  <g key={m.id}>
                    {pts.map((q, i) => <circle key={i} cx={q[0]} cy={q[1]} r={sw(5)} fill="#0b7285" fillOpacity={0.85} stroke="#fff" strokeWidth={sw(1.2)} />)}
                    {anchor && <text x={anchor[0] + sw(8)} y={anchor[1] - sw(6)} fontSize={sw(11)} fill="#0b7285" fontFamily="ui-monospace, monospace">{label}</text>}
                  </g>
                );
              }
              if (m.tool === "text") {
                return anchor ? (
                  <g key={m.id}>
                    <circle cx={anchor[0]} cy={anchor[1]} r={sw(3)} fill="#0b7285" />
                    <text x={anchor[0] + sw(6)} y={anchor[1] - sw(4)} fontSize={sw(11)} fill="#0b7285" fontFamily="ui-monospace, monospace">{m.text}</text>
                  </g>
                ) : null;
              }
              const closed = m.tool === "area" || m.tool === "rektangel" || m.tool === "moln";
              return pts.length >= 2 ? (
                <g key={m.id}>
                  {closed
                    ? <polygon points={pts.map((q) => q.join(",")).join(" ")} fill="#0b7285" fillOpacity={0.12} stroke="#0b7285" strokeWidth={sw(2.5)} strokeLinejoin="round" />
                    : <polyline points={pts.map((q) => q.join(",")).join(" ")} fill="none" stroke="#0b7285" strokeWidth={sw(3.5)} strokeOpacity={0.9} strokeLinecap="round" strokeLinejoin="round" />}
                  {anchor && <text x={anchor[0] + sw(6)} y={anchor[1] - sw(6)} fontSize={sw(11)} fill="#0b7285" fontFamily="ui-monospace, monospace">{label}</text>}
                </g>
              ) : null;
            })}

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

            {/* A ring says a label's leader ended here. It is not a claim that a pipe was measured: a component
                tag reaches a floor drain or a mixer, and a leader ending inside a wall reaches length the
                quantity already excludes. Both used to be drawn exactly like an attachment to a measured run. */}
            {/* The answer, where the question was asked. It sits on the sheet because that is where the reader is
                looking, and it takes pointer events so the close button can be pressed. */}
            {props.ink && (() => {
              // the box has to be told its height, so it is worked out from the text rather than guessed at:
              // a card that is too short spills its words onto the drawing underneath
              const W = sw(300);
              const H = sw(46 + Math.ceil(props.ink.detail.length / 44) * 17 + Math.ceil(props.ink.title.length / 34) * 6);
              const x = Math.max(sw(6), Math.min(props.ink.at[0] + sw(14), (vp?.w ?? 0) - W - sw(6)));
              const y = Math.max(sw(6), Math.min(props.ink.at[1] - sw(10), (vp?.h ?? 0) - H - sw(6)));
              const hue = { matt: "#12a24b", "i-vagg": "#6b7280", tvetydig: "#ff9500", papekad: "#a855f7",
                oidentifierad: "#8a8f99", bortvald: "#0891b2", inget: "#9aa3af" }[props.ink.kind];
              return (
                <g style={{ pointerEvents: "auto" }}>
                  <circle cx={props.ink.at[0]} cy={props.ink.at[1]} r={sw(6)} fill="none" stroke={hue} strokeWidth={sw(2)} />
                  <foreignObject x={x} y={y} width={W} height={H}>
                    <div className="inkcard" style={{ borderLeftColor: hue, fontSize: sw(12.5) }}>
                      <button type="button" className="x" onClick={() => props.onInkClick?.(null)} aria-label="Stäng">✕</button>
                      <b style={{ color: hue }}>{props.ink.title}</b>
                      <p>{props.ink.detail}</p>
                    </div>
                  </foreignObject>
                </g>
              );
            })()}
            {props.layers.anchors && props.anchors.map((a) => (
              <circle key={a.id} cx={a.endpoint[0]} cy={a.endpoint[1]} r={sw(a.names_a_pipe === false ? 2.5 : 4)} fill="none"
                stroke={a.names_a_pipe === false ? "#9aa3af"
                  : a.state === "VERIFIED_PIPE_ATTACHMENT" ? "#12a24b" : a.state === "AMBIGUOUS_PIPE_ATTACHMENT" ? "#ff9500" : "#b42318"}
                strokeOpacity={a.in_wall && !props.layers.inWall ? 0.35 : 1}
                strokeWidth={sw(a.names_a_pipe === false ? 1 : 1.5)}
                strokeDasharray={a.names_a_pipe === false ? `${sw(2)} ${sw(2)}` : undefined} />
            ))}
          </svg>
        )}
      </div>
    </div>
  );
});

export default PdfViewer;
