import { useCallback, useEffect, useMemo, useState } from "react";
import { MODULES, markDone, readProgress, type Block, type Lesson, type Quiz } from "../learn";
import LearnFigure from "./LearnFigures";
import { Exercise } from "./Learn";

/* Akademin som en guide ovanpå det man höll på med.
 *
 * Att trycka på "Lär mig om VVS" mitt i en läsning ska inte ta bort läsningen. Det här lägger sig över den:
 * ett steg i taget, en levande figur som visar vad steget handlar om, två rader som säger det, och en
 * kontrollfråga innan man går vidare. Läsningen fortsätter bakom, och att stänga kostar ingenting.
 */

type Step = { lesson: Lesson; module: string; i: number; n: number };

/** The lesson in full, for the reader who wants the whole thing rather than the two lines of the step. */
function More({ body }: { body: Block[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="wz-more">
      <button className="ghost small" onClick={() => setOpen(!open)}>
        {open ? "Dölj hela avsnittet" : "Läs hela avsnittet"}
      </button>
      {open && (
        <div className="wz-more-body">
          {body.map((b, i) => {
            if (b.k === "p") return <p key={i}>{b.t}</p>;
            if (b.k === "note") return <p key={i} className="lf-note">{b.t}</p>;
            if (b.k === "ul") return <ul key={i} className="lf-ul">{b.t.map((x, j) => <li key={j}>{x}</li>)}</ul>;
            if (b.k === "terms") {
              return (
                <dl key={i} className="lf-terms">
                  {b.t.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
                </dl>
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
}

function QuizStep({ q, onPass }: { q: Quiz; onPass: () => void }) {
  const [pick, setPick] = useState<number | null>(null);
  return (
    <div className="wz-quiz">
      <div className="wz-quiz-q">{q.q}</div>
      <div className="wz-quiz-opts">
        {q.options.map((o, i) => (
          <button key={i} type="button"
            className={`secondary${pick === null ? "" : i === q.answer ? " right" : pick === i ? " wrong" : ""}`}
            onClick={() => { setPick(i); if (i === q.answer) onPass(); }}>
            <span className="k">{String.fromCharCode(65 + i)}</span>{o}
          </button>
        ))}
      </div>
      {pick !== null && (
        <p className={`wz-why${pick === q.answer ? " ok" : ""}`}>
          <b>{pick === q.answer ? "Rätt." : "Inte riktigt."}</b> {q.why}
        </p>
      )}
    </div>
  );
}

export default function LearnWizard({ open, onClose, start }: {
  open: boolean; onClose: () => void; start?: string;
}) {
  const steps: Step[] = useMemo(() => {
    const out: Step[] = [];
    for (const m of MODULES) for (const l of m.lessons) out.push({ lesson: l, module: m.title, i: 0, n: 0 });
    return out.map((s, i) => ({ ...s, i, n: out.length }));
  }, []);
  const [at, setAt] = useState(0);
  const [prog, setProg] = useState<Record<string, boolean>>(() => readProgress());

  // opening picks up where the last drawing left off, so a wizard is a course and not a loop
  useEffect(() => {
    if (!open) return;
    const p = readProgress();
    setProg(p);
    const want = start ? steps.findIndex((s) => s.lesson.id === start) : -1;
    setAt(want >= 0 ? want : Math.min(steps.findIndex((s) => !p[s.lesson.id]) + 0 || 0, steps.length - 1));
  }, [open, start, steps]);

  const go = useCallback((d: number) => setAt((v) => Math.max(0, Math.min(steps.length - 1, v + d))), [steps.length]);

  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") go(1);
      if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", k);
    document.body.classList.add("wz-open");
    return () => { window.removeEventListener("keydown", k); document.body.classList.remove("wz-open"); };
  }, [open, onClose, go]);

  if (!open) return null;
  const s = steps[at];
  const l = s.lesson;
  const done = steps.filter((x) => prog[x.lesson.id]).length;
  const finish = () => setProg(markDone(l.id));

  return (
    <div className="wz" role="dialog" aria-modal="true" aria-label="VVS-akademin">
      <div className="wz-scrim" onClick={onClose} />
      <div className="wz-panel">
        <header className="wz-head">
          <div>
            <div className="wz-kicker">{s.module} · steg {at + 1} av {s.n}</div>
            <h2>{l.title}</h2>
          </div>
          <div className="wz-headr">
            <span className="wz-count">{done}/{s.n} klara</span>
            <button className="ghost small" onClick={onClose} aria-label="Stäng">✕</button>
          </div>
        </header>

        <div className="wz-rail" aria-hidden="true">
          {steps.map((x, i) => (
            <button key={x.lesson.id} type="button"
              className={`wz-dot${i === at ? " on" : ""}${prog[x.lesson.id] ? " done" : ""}`}
              title={x.lesson.title} onClick={() => setAt(i)} />
          ))}
        </div>

        <div className="wz-body">
          <div className="wz-fig">
            {l.fig === "exercise" ? <Exercise /> : <LearnFigure id={l.fig || ""} />}
          </div>
          <div className="wz-say">
            {(l.short ?? []).map((t, i) => <p key={i}>{t}</p>)}
            <More body={l.body} />
            {l.quiz && <QuizStep q={l.quiz} onPass={finish} />}
            {!l.quiz && (
              <button className={prog[l.id] ? "secondary small" : "small"} onClick={finish}>
                {prog[l.id] ? "Markerad som klar" : "Jag har läst det här"}
              </button>
            )}
          </div>
        </div>

        <footer className="wz-foot">
          <button className="secondary" onClick={() => go(-1)} disabled={at === 0}>← Tillbaka</button>
          <div className="wz-prog"><div style={{ width: `${((at + 1) / s.n) * 100}%` }} /></div>
          {at < s.n - 1
            ? <button onClick={() => { finish(); go(1); }}>Nästa →</button>
            : <button onClick={() => { finish(); onClose(); }}>Klart</button>}
        </footer>
      </div>
    </div>
  );
}
