import { useCallback, useEffect, useImperativeHandle, useRef, useState, forwardRef } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

(pdfjsLib as any).GlobalWorkerOptions.workerSrc = workerUrl;

export type Layer = "pipes" | "ambiguous" | "unowned" | "designations" | "leaders" | "anchors";

export interface ViewerProps {
  data: ArrayBuffer | null;
  page: number;
  pipes: any[];
  ambiguous: any[];
  unowned: any[];
  designations: any[];
  leaders: any[];
  anchors: any[];
  selectedIdentity: string | null;
  selectedPipe: string | null;
  layers: Record<Layer, boolean>;
  onPipeClick: (pipe: any) => void;
  onPageCount: (n: number) => void;
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
  const sw = (pt: number) => pt / scale;
  return (
    <div className="viewer" ref={container}>
      <div className="page" style={{ width: w, height: h }}>
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
              return p.geometry.map((pl: number[][], k: number) => (
                <polyline key={`${p.physical_pipe_id}-${k}`} points={pl.map((q) => q.join(",")).join(" ")} fill="none"
                  stroke={sel ? "#ff2d00" : "#12a24b"} strokeWidth={sw(sel ? 5 : 3.2)} strokeOpacity={0.85} strokeLinecap="round" strokeLinejoin="round"
                  style={{ pointerEvents: "stroke", cursor: "pointer" }} onClick={() => props.onPipeClick(p)} />
              ));
            })}
            {props.layers.leaders && props.leaders.map((l) => (
              <polyline key={l.id} points={l.points.map((q: number[]) => q.join(",")).join(" ")} fill="none" stroke="#b000b0" strokeWidth={sw(1.2)} />
            ))}
            {props.layers.designations && props.designations.map((d) => (
              <rect key={d.id} x={d.bbox[0] - 1} y={d.bbox[1] - 1} width={d.bbox[2] - d.bbox[0] + 2} height={d.bbox[3] - d.bbox[1] + 2}
                fill="none" stroke={d.dn != null ? "#0b5cad" : "#c77800"} strokeWidth={sw(1)} />
            ))}
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
