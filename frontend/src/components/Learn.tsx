import { useMemo, useState } from "react";
import { MODULES, readProgress, markDone, type Block, type Lesson, type Module } from "../learn";

/* VVS-akademin.
 *
 * En läsning tar en stund, och den stunden är en av få gånger någon sitter still framför verktyget. Det här är
 * vad de kan göra under tiden - och eftersom det som lärs ut är precis det verktyget arbetar med, blir en person
 * som gått igenom det bättre på att läsa vad verktyget svarar. Var lektion är märkt som gjord i webbläsaren, så
 * nästa ritning kan fortsätta där den förra slutade.
 */

/* ---------- the figures the lessons point at ---------- */

function FigDesignation() {
  return (
    <svg viewBox="0 0 520 168" role="img" aria-label="Beteckningen KV1-X31-16 uppdelad i sina tre delar">
      <g className="lf-mono">
        <text x="60" y="66" fontSize="34" fill="var(--ink)">KV1</text>
        <text x="146" y="66" fontSize="34" fill="var(--faint)">-</text>
        <text x="168" y="66" fontSize="34" fill="var(--ink)">X31</text>
        <text x="252" y="66" fontSize="34" fill="var(--faint)">-</text>
        <text x="274" y="66" fontSize="34" fill="var(--ink)">16</text>
      </g>
      {/* the three drops get shorter to the right, and each caption runs right from where its own drop lands,
          so no line ever crosses a line of text */}
      <g stroke="var(--line-2)" strokeWidth="1" fill="none">
        <path d="M92 82 V140" /><path d="M204 82 V112" /><path d="M298 82 V84" />
      </g>
      <g className="lf-mono" fontSize="12" fill="var(--muted)">
        <text x="102" y="144">system · tappkallvatten 1</text>
        <text x="214" y="116">material · ur bladets lista</text>
        <text x="308" y="88">dimension · 16 mm ytterdiameter</text>
      </g>
    </svg>
  );
}

function FigLeader() {
  return (
    <svg viewBox="0 0 520 190" role="img" aria-label="Etikett, hänvisningslinje och punkten där den landar">
      <rect x="10" y="12" width="500" height="166" rx="8" fill="#fbfbfb" stroke="var(--line)" />
      <path d="M60 132 H250 V86 H430" fill="none" stroke="#1f7a52" strokeWidth="3.4" strokeLinecap="round"
        strokeDasharray="16 6" />
      <g>
        <rect x="60" y="34" width="132" height="24" rx="4" fill="#fff" stroke="var(--line-2)" />
        <text x="70" y="51" className="lf-mono" fontSize="12.5" fill="var(--ink)">KV1-X31-16</text>
        <path d="M192 46 L250 86" stroke="#c026d3" strokeWidth="1.5" fill="none" />
        <circle cx="250" cy="86" r="4.6" fill="#fff" stroke="#c026d3" strokeWidth="2" />
      </g>
      <text x="264" y="76" className="lf-mono" fontSize="11" fill="var(--muted)">linjen slutar PÅ röret</text>
      <path d="M300 148 H430" fill="none" stroke="#c9c9c9" strokeWidth="3.4" strokeDasharray="16 6" />
      <text x="300" y="170" className="lf-mono" fontSize="11" fill="var(--faint)">ingen etikett · mängdas inte</text>
    </svg>
  );
}

/* ---------- the exercise: a small sheet to take off ---------- */

type Run = { id: string; d: string; answer: string | null; m: number };

const RUNS: Run[] = [
  { id: "a", d: "M100 250 H260 V160 H420", answer: "KV1-X31-16", m: 12.4 },
  { id: "b", d: "M100 288 H230 V330 H370", answer: "VV1-X31-16", m: 10.6 },
  { id: "c", d: "M450 92 H540 V240", answer: "S3-P2-110", m: 13.6 },
  { id: "d", d: "M400 330 H540", answer: null, m: 6.0 },
];
const CODES = ["KV1-X31-16", "VV1-X31-16", "S3-P2-110", "ingen beteckning"];
const HUE: Record<string, string> = {
  "KV1-X31-16": "#2563eb", "VV1-X31-16": "#c2410c", "S3-P2-110": "#15803d", "ingen beteckning": "#9b9b9b",
};

/** One of the sheet's own labels, with the line it draws to the run it names. */
function Label({ x, y, t, to }: { x: number; y: number; t: string; to: [number, number] }) {
  return (
    <g>
      <path d={`M${x + 112} ${y + 12} L${to[0]} ${to[1]}`} stroke="#c026d3" strokeWidth="1.3" fill="none" />
      <circle cx={to[0]} cy={to[1]} r="4.6" fill="#fff" stroke="#c026d3" strokeWidth="2" />
      <rect x={x} y={y} width="112" height="24" rx="4" fill="#fff" stroke="var(--line-2)" />
      <text x={x + 9} y={y + 16} className="lf-mono" fontSize="11.5" fill="var(--ink)">{t}</text>
    </g>
  );
}

function Exercise() {
  const [picked, setPicked] = useState<string | null>(null);
  const [given, setGiven] = useState<Record<string, string>>({});
  const [checked, setChecked] = useState(false);
  const right = RUNS.filter((r) => given[r.id] === (r.answer ?? "ingen beteckning")).length;

  return (
    <div className="lf-ex">
      <div className="lf-ex-sheet">
        <svg viewBox="0 0 620 400" role="img" aria-label="Övningsblad med fyra sträckor">
          <rect x="6" y="6" width="608" height="388" rx="6" fill="#fff" stroke="var(--line-2)" />
          <g stroke="#e0e0e0" strokeWidth="1.6" fill="none">
            <path d="M60 50 H560 V360 H60 Z M300 50 V360 M60 210 H300 M420 50 V210 M420 210 H560" />
          </g>
          <g className="lf-mono" fontSize="10" fill="var(--faint)">
            <text x="62" y="38">ÖVNINGSBLAD · SKALA 1:50</text>
            <text x="470" y="38">4 STRÄCKOR</text>
          </g>
          {RUNS.map((r) => {
            const g = given[r.id];
            const ok = checked && g === (r.answer ?? "ingen beteckning");
            const bad = checked && g && !ok;
            const on = picked === r.id;
            return (
              <g key={r.id} onClick={() => setPicked(r.id)} style={{ cursor: "pointer" }}>
                {(on || ok) && (
                  <path d={r.d} fill="none" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round"
                    stroke={ok ? HUE[g] : "#0d0d0d"} strokeOpacity={ok ? 0.15 : 0.1} />
                )}
                <path d={r.d} fill="none" stroke="transparent" strokeWidth="22" />
                <path d={r.d} fill="none" strokeWidth={on ? 6 : 5} strokeLinecap="round" strokeLinejoin="round"
                  strokeDasharray="15 6"
                  stroke={bad ? "#a32020" : g ? HUE[g] : on ? "#0d0d0d" : "#b0b0b0"} />
              </g>
            );
          })}
          <Label x={72} y={104} t="KV1-X31-16" to={[260, 160]} />
          <Label x={72} y={196} t="VV1-X31-16" to={[230, 300]} />
          <Label x={330} y={62} t="S3-P2-110" to={[450, 92]} />
          <text x="400" y="316" className="lf-mono" fontSize="10.5" fill="var(--faint)">
            ingen etikett pekar hit
          </text>
        </svg>
      </div>
      <div className="lf-ex-side">
        <h4>{picked ? `Sträcka ${picked.toUpperCase()}` : "Välj en sträcka"}</h4>
        <p className="muted">
          {picked
            ? "Vilken beteckning namnger den? Följ hänvisningslinjen, inte närheten."
            : "Klicka på ett av de streckade rören i bladet."}
        </p>
        <div className="lf-ex-codes">
          {CODES.map((c) => (
            <button key={c} type="button" className={`secondary small${picked && given[picked] === c ? " on" : ""}`}
              disabled={!picked}
              onClick={() => picked && (setGiven({ ...given, [picked]: c }), setChecked(false))}>
              <i style={{ background: HUE[c] }} /> {c}
            </button>
          ))}
        </div>
        <div className="row" style={{ marginTop: 14 }}>
          <button type="button" onClick={() => setChecked(true)} disabled={Object.keys(given).length < RUNS.length}>
            Rätta
          </button>
          <button type="button" className="ghost small"
            onClick={() => { setGiven({}); setChecked(false); setPicked(null); }}>Börja om</button>
        </div>
        {checked && (
          <>
            <div className={`badge ${right === RUNS.length ? "ok" : "warn"}`} style={{ marginTop: 14 }}>
              {right} av {RUNS.length} rätt
            </div>
            <ul className="lf-ex-facit">
              {RUNS.map((r) => (
                <li key={r.id}>
                  <b>{r.id.toUpperCase()}</b> {r.answer ?? "ingen beteckning"}
                  <span className="muted"> · {r.answer ? `${r.m.toFixed(1).replace(".", ",")} m` : "mängdas inte"}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}

const FIGS: Record<string, () => JSX.Element> = {
  designation: FigDesignation, leader: FigLeader, exercise: Exercise,
};

/* ---------- the reader ---------- */

function Body({ b }: { b: Block }) {
  if (b.k === "p") return <p>{b.t}</p>;
  if (b.k === "note") return <p className="lf-note">{b.t}</p>;
  if (b.k === "ul") return <ul className="lf-ul">{b.t.map((x, i) => <li key={i}>{x}</li>)}</ul>;
  if (b.k === "terms") {
    return (
      <dl className="lf-terms">
        {b.t.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
      </dl>
    );
  }
  const F = FIGS[b.id];
  return (
    <figure className={`lf-fig${b.id === "exercise" ? " wide" : ""}`}>
      <div className="lf-fig-in">{F ? <F /> : null}</div>
      <figcaption>{b.caption}</figcaption>
    </figure>
  );
}

function QuizBox({ l, onPass }: { l: Lesson; onPass: () => void }) {
  const [pick, setPick] = useState<number | null>(null);
  if (!l.quiz) return null;
  const q = l.quiz;
  return (
    <div className="lf-quiz">
      <div className="lf-quiz-q">{q.q}</div>
      <div className="lf-quiz-opts">
        {q.options.map((o, i) => (
          <button key={i} type="button"
            className={`secondary${pick === null ? "" : i === q.answer ? " right" : pick === i ? " wrong" : ""}`}
            onClick={() => { setPick(i); if (i === q.answer) onPass(); }}>
            {o}
          </button>
        ))}
      </div>
      {pick !== null && (
        <p className={`lf-quiz-why${pick === q.answer ? " ok" : ""}`}>
          {pick === q.answer ? "Rätt. " : "Inte riktigt. "}{q.why}
        </p>
      )}
    </div>
  );
}

export default function Learn({ compact }: { compact?: boolean }) {
  const [prog, setProg] = useState<Record<string, boolean>>(() => readProgress());
  const [open, setOpen] = useState<string | null>(null);
  const flat = useMemo(() => MODULES.flatMap((m) => m.lessons.map((l) => ({ m, l }))), []);
  const done = flat.filter(({ l }) => prog[l.id]).length;
  const cur = open ? flat.find(({ l }) => l.id === open) : null;

  const finish = (id: string) => setProg(markDone(id));
  const nextOf = (id: string) => {
    const i = flat.findIndex(({ l }) => l.id === id);
    return i >= 0 && i + 1 < flat.length ? flat[i + 1] : null;
  };

  if (cur) {
    const nx = nextOf(cur.l.id);
    return (
      <div className={`learn${compact ? " compact" : ""}`}>
        <div className="lf-bar">
          <button className="ghost small" onClick={() => setOpen(null)}>← Alla delmoment</button>
          <span className="lf-crumb">{cur.m.title} · {cur.l.minutes} min</span>
        </div>
        <article className="lf-read">
          <h2>{cur.l.title}</h2>
          {cur.l.body.map((b, i) => <Body key={i} b={b} />)}
          <QuizBox l={cur.l} onPass={() => finish(cur.l.id)} />
          <div className="lf-foot">
            <button className={prog[cur.l.id] ? "secondary" : ""}
              onClick={() => { finish(cur.l.id); if (nx) setOpen(nx.l.id); else setOpen(null); }}>
              {prog[cur.l.id] ? (nx ? "Nästa delmoment" : "Klart") : "Markera som klar"}
            </button>
            {nx && <span className="muted">Härnäst: {nx.l.title}</span>}
          </div>
        </article>
      </div>
    );
  }

  return (
    <div className={`learn${compact ? " compact" : ""}`}>
      <div className="lf-hero">
        <div>
          <div className="lf-kicker">VVS-akademin</div>
          <h2>Lär dig läsa och mängda en rörritning</h2>
          <p className="muted">
            Sex delmoment, ett i taget. De sparas i den här webbläsaren, så du kan fortsätta där du slutade nästa
            gång en ritning läses.
          </p>
        </div>
        <div className="lf-ring" style={{ ["--p" as any]: `${Math.round((done / flat.length) * 100)}%` }}>
          <span>{done}<i>/{flat.length}</i></span>
        </div>
      </div>
      <div className="lf-mods">
        {MODULES.map((m: Module, mi) => {
          const d = m.lessons.filter((l) => prog[l.id]).length;
          return (
            <section key={m.id} className={`lf-mod${d === m.lessons.length ? " full" : ""}`}>
              <div className="lf-mod-no">{String(mi + 1).padStart(2, "0")}</div>
              <h3>{m.title}</h3>
              <p className="muted">{m.blurb}</p>
              <ol className="lf-less">
                {m.lessons.map((l) => (
                  <li key={l.id} className={prog[l.id] ? "done" : ""}>
                    <button className="ghost" onClick={() => setOpen(l.id)}>
                      <span className="tick" aria-hidden="true" />
                      <span className="nm">{l.title}</span>
                      <span className="mi">{l.minutes} min</span>
                    </button>
                  </li>
                ))}
              </ol>
            </section>
          );
        })}
      </div>
    </div>
  );
}
