import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { STAGE_LABELS, stageText } from "./Status";
import { AGENTS, frameSays } from "../agents";

type Frame = { stage: string; at: number; [k: string]: any };

const ORDER = ["READING_PDF", "RECONSTRUCTING_TEXT", "READING_DESIGNATIONS", "FINDING_LEADERS",
  "RESOLVING_PIPE_REPRESENTATION", "BUILDING_PHYSICAL_PIPES", "MEASURING"];

/* One colour per identity, stable across frames, so a run keeps its colour as the reading fills in. */
function hue(key: string) {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) % 360;
  return h;
}

export default function AnalysisFilm({ jobId, stage: rawStage, progress }: { jobId: string; stage: string; progress: number }) {
  // a stage may carry a detail after its name; the film compares against the name
  const stage = (rawStage || "").split(" ")[0];
  const [frames, setFrames] = useState<Frame[]>([]);
  const [tick, setTick] = useState(0);
  // when this view first saw each stage - a frame that was already there when the page opened is not animated in
  const seen = useRef<Record<string, number>>({});
  const mounted = useRef(0);
  const box = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(760);

  // A frame only lands when a stage finishes, so the film is fetched when the stage moves rather than on a
  // timer; the slow heartbeat is there in case a stage name repeats or a poll was lost.
  useEffect(() => {
    let live = true;
    const get = async () => {
      try {
        const f = await api.film(jobId);
        if (live && Array.isArray(f.frames)) setFrames(f.frames);
      } catch { /* the film is a view; a failed fetch just means the next one */ }
    };
    get();
    // a stage lands when it finishes, so the film is fetched when the stage moves - but the readers are talking
    // to each other while it runs, and a line that arrives six seconds after it was said is not a conversation
    const beat = setInterval(get, stage === "COMPLETED" || stage === "FAILED" ? 6000 : 1500);
    return () => { live = false; clearInterval(beat); };
  }, [jobId, stage]);

  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 90);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const on = () => setW(box.current?.clientWidth ?? 760);
    on();
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);

  useEffect(() => {
    if (!mounted.current) mounted.current = performance.now();
    const first = performance.now() - mounted.current < 400;
    for (const f of frames) {
      if (seen.current[f.stage] == null) seen.current[f.stage] = first ? 0 : performance.now();
    }
  }, [frames]);

  const by = useMemo(() => Object.fromEntries(frames.map((f) => [f.stage, f])), [frames]);
  const page = by.READING_PDF?.page ?? { w: 842, h: 595 };
  const scale = Math.min(w / page.w, 1.6);
  const H = page.h * scale;

  // each stage's shapes are drawn in over a beat rather than appearing whole; a stage already finished when the
  // page opened is simply there, because animating history would hide what the reader came to see
  const beat = (name: string) => {
    const at = seen.current[name];
    if (at == null) return 0;
    if (at === 0) return 1;
    return Math.max(0, Math.min(1, (performance.now() - at) / 1400 + 0.08));
  };
  const cut = (list: any[] | undefined, name: string): any[] =>
    !list ? [] : list.slice(0, Math.ceil(list.length * beat(name)));

  void tick;   // the interval above is what re-runs beat() while a stage draws in
  const measured = by.MEASURING?.quantities ?? [];
  const total = by.MEASURING?.total_m ?? 0;
  const running = stage !== "COMPLETED" && stage !== "FAILED";
  // the sweep is the reading's own pace made visible: it crosses the sheet while a stage works, and stops when
  // there is nothing left to read
  const sweepY = running ? ((performance.now() / 2600) % 1) * page.h : 0;
  const talk = AGENTS.map((a) => ({ stage: a.stage, who: a.who, lines: frameSays(a.stage, by[a.stage]) }))
    .filter((t) => t.lines.length > 0)
    .map((t, i, all) => ({ ...t, next: i < all.length - 1 ? all[i + 1].who : null }));
  const spoken = new Set(talk.map((t) => t.stage));
  const nextUp = AGENTS.find((a) => !spoken.has(a.stage));
  // what the reading is doing right now, said in the words of whoever is doing it
  const nowWho = AGENTS.find((a) => a.stage === stage)?.who ?? nextUp?.who ?? null;
  const nowAsks = AGENTS.find((a) => a.stage === stage)?.asks ?? nextUp?.asks ?? stageText(rawStage) ?? null;

  return (
    <div className="film">
      <div className="film-stage" ref={box}>
        <svg width={page.w * scale} height={H} viewBox={`0 0 ${page.w} ${page.h}`} role="img"
          aria-label="Ritningen fylls i medan den läses">
          <rect x="0" y="0" width={page.w} height={page.h} fill="#fff" stroke="#e6e6e6" />
          {cut(by.RESOLVING_PIPE_REPRESENTATION?.families, "RESOLVING_PIPE_REPRESENTATION").flatMap((f: any, fi: number) =>
            (f.segs ?? []).map((s: number[], i: number) => (
              <line key={`g${fi}-${i}`} x1={s[0]} y1={s[1]} x2={s[2]} y2={s[3]} stroke="#d7d7d7" strokeWidth={0.7 / scale} />
            )))}
          {cut(by.RECONSTRUCTING_TEXT?.rows, "RECONSTRUCTING_TEXT").map((b: number[], i: number) => (
            <rect key={`t${i}`} x={b[0]} y={b[1]} width={Math.max(b[2] - b[0], 0.6)} height={Math.max(b[3] - b[1], 0.6)}
              fill="#0d0d0d" opacity="0.13" />
          ))}
          {cut(by.READING_DESIGNATIONS?.labels, "READING_DESIGNATIONS").map((l: any, i: number) => (
            <rect key={`d${i}`} x={l.b[0] - 0.6} y={l.b[1] - 0.6} width={Math.max(l.b[2] - l.b[0] + 1.2, 1)}
              height={Math.max(l.b[3] - l.b[1] + 1.2, 1)} fill="none" stroke="#0d0d0d" strokeWidth={0.6 / scale} opacity="0.7" />
          ))}
          {cut(by.FINDING_LEADERS?.leaders, "FINDING_LEADERS").map((pts: number[][], i: number) => (
            <polyline key={`l${i}`} points={pts.map((p) => p.join(",")).join(" ")} fill="none"
              stroke="#c026d3" strokeWidth={0.7 / scale} opacity="0.5" />
          ))}
          {cut(by.BUILDING_PHYSICAL_PIPES?.pipes, "BUILDING_PHYSICAL_PIPES").map((p: any, i: number) => (
            <polyline key={`p${i}`} points={p.p.map((q: number[]) => q.join(",")).join(" ")} fill="none"
              stroke={`hsl(${hue(p.i)} 68% 42%)`} strokeWidth={2.4 / scale} strokeLinecap="round" strokeLinejoin="round" />
          ))}
          {running && (
            <>
              <defs>
                <linearGradient id="sweep" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#0d0d0d" stopOpacity="0" />
                  <stop offset="82%" stopColor="#0d0d0d" stopOpacity="0.05" />
                  <stop offset="100%" stopColor="#0d0d0d" stopOpacity="0.16" />
                </linearGradient>
              </defs>
              <rect x="0" y={Math.max(0, sweepY - page.h * 0.34)} width={page.w}
                height={Math.min(page.h * 0.34, sweepY)} fill="url(#sweep)" />
              <line x1="0" y1={sweepY} x2={page.w} y2={sweepY} stroke="#0d0d0d" strokeWidth={0.9 / scale} opacity="0.5" />
            </>
          )}
        </svg>
      </div>

      {/* what the readers are saying to each other while it runs: each stage reports what it found from its own
          frame, then hands the sheet to the next. Nothing here is written for the screen - the numbers are the
          ones the reading is working from. */}
      <div className="film-talk">
        {talk.length === 0 && <p className="muted">Läser in bladet…</p>}
        {talk.map((t, i) => (
          <div key={`${t.stage}-${i}`} className={`bubble${i === talk.length - 1 ? " fresh" : ""}`}>
            <div className="who">{t.who}</div>
            {t.lines.map((l, j) => <p key={j}>{l}</p>)}
            {t.next && <div className="handoff">lämnar vidare till {t.next}</div>}
          </div>
        ))}
        {running && nowWho && (
          <div className="bubble waiting">
            <div className="who">{nowWho}</div>
            {nowAsks && <p className="asking">”{nowAsks}”</p>}
            <p className="dots"><i /><i /><i /></p>
          </div>
        )}
      </div>

      <div className="film-side">
        <div className="film-total">
          <div className="v">{total ? `${total.toFixed(1).replace(".", ",")} m` : "—"}</div>
          <div className="l">mätt hittills</div>
        </div>
        <ol className="film-stages">
          {ORDER.map((st) => {
            const done = !!by[st];
            const now = st === stage;
            const f = by[st];
            const count = f?.n ?? f?.quantities?.length ?? f?.families?.length;
            return (
              <li key={st} className={done ? "done" : now ? "now" : ""}>
                <span className="dot" />
                <span className="nm">{STAGE_LABELS[st] ?? st}</span>
                {count != null && <span className="ct">{count}</span>}
              </li>
            );
          })}
        </ol>
        {measured.length > 0 && (
          <ul className="film-q">
            {measured.slice(0, 10).map((q: any) => (
              <li key={q.d}>
                <span className="sw" style={{ background: `hsl(${hue(q.d)} 68% 42%)` }} />
                <span className="dq">{q.d}</span>
                <span className="mq">{q.m.toFixed(2).replace(".", ",")}</span>
              </li>
            ))}
          </ul>
        )}
        <div className="progress"><div style={{ width: `${Math.round(progress * 100)}%` }} /></div>
      </div>
    </div>
  );
}
