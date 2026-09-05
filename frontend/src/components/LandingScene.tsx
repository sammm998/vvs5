import { useSectionProgress } from "./lp-motion";

/** The stages the scene walks through as the reader scrolls, in the order the engine does them. */
const BEATS = [
  ["Läser vektorn", "Varje streck, dess penna, färg och lager tas direkt ur PDF:en."],
  ["Bygger tillbaka texten", "Bokstäver som ritats som streck sätts ihop till ord igen."],
  ["Följer ledarlinjerna", "Från etikettens understrykning till den geometri linjen faktiskt rör."],
  ["Äger rören", "Identiteten bärs längs nätet till den gräns ritningen själv sätter."],
  ["Mäter i skalstockens skala", "Och redovisar varje meter med sitt belägg."],
];

const RUNS: { d: string; c: string; m: number }[] = [
  { d: "M120 300 H360 V186 H620", c: "#6ee7a5", m: 24.8 },
  { d: "M120 372 H468 V300", c: "#60a5fa", m: 18.2 },
  { d: "M620 186 H812 V402 H520", c: "#f0abfc", m: 31.4 },
  { d: "M240 300 V444 H520", c: "#fbbf24", m: 12.1 },
];

const WORDS = [
  [148, 268, 74], [402, 154, 62], [648, 154, 58], [176, 340, 66], [500, 268, 70],
  [700, 370, 54], [268, 412, 60], [560, 434, 66], [820, 268, 48], [360, 154, 44],
];

/** A short window of the scroll, eased, so each beat has its own stretch of the page. */
const win = (p: number, a: number, b: number) => Math.min(1, Math.max(0, (p - a) / (b - a)));

export default function LandingScene() {
  const { ref, p } = useSectionProgress<HTMLElement>();
  const beat = Math.min(BEATS.length - 1, Math.floor(p * BEATS.length * 0.999));

  const text = win(p, 0.02, 0.24);
  const words = win(p, 0.18, 0.40);
  const leaders = win(p, 0.36, 0.58);
  const pipes = win(p, 0.52, 0.80);
  const measure = win(p, 0.76, 0.96);

  return (
    <section className="lp-scene" ref={ref} id="hur">
      <div className="lp-scene-pin">
        <div className="lp-scene-grid">
          <div className="lp-scene-art">
            <svg viewBox="0 0 940 520" role="img" aria-label="Ritningen läses steg för steg medan sidan skrollas">
              {/* the sheet */}
              <g stroke="#1b1f26" strokeWidth="1.4" fill="none" opacity={0.5 + 0.5 * text}>
                <path d="M60 90 H880 V470 H60 Z M60 250 H520 M520 90 V470 M700 250 H880 M700 340 H880" />
              </g>
              {/* text rows found */}
              <g fill="#e8ecf1">
                {WORDS.map(([x, y, w], i) => {
                  const k = win(words, i / WORDS.length * 0.75, i / WORDS.length * 0.75 + 0.3);
                  return <rect key={i} x={x} y={y} width={(w as number) * k} height="7" rx="1" opacity={0.12 + 0.2 * k} />;
                })}
              </g>
              {/* leaders reaching from the labels to the runs */}
              <g stroke="#c026d3" strokeWidth="1.3" fill="none" opacity={0.7}>
                {[["M186 275 L246 299"], ["M436 161 L468 300"], ["M690 161 L622 187"], ["M300 419 L340 373"]].map((d, i) => {
                  const k = win(leaders, i * 0.12, i * 0.12 + 0.5);
                  return <path key={i} d={d[0]} pathLength={1} strokeDasharray="1" strokeDashoffset={1 - k} />;
                })}
              </g>
              {/* the runs, drawing themselves */}
              <g fill="none" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round">
                {RUNS.map((r, i) => {
                  const k = win(pipes, i * 0.1, i * 0.1 + 0.62);
                  return (
                    <path key={i} d={r.d} stroke={r.c} pathLength={1} strokeDasharray="1"
                      strokeDashoffset={1 - k} opacity={0.35 + 0.65 * k} />
                  );
                })}
              </g>
              {/* the one the sheet never names */}
              <path d="M700 434 H860" stroke="#4b5160" strokeWidth="3" strokeDasharray="9 6"
                opacity={0.25 + 0.55 * pipes} fill="none" />
              <text x="700" y="422" fill="#5b616c" fontSize="13" opacity={0.3 + 0.7 * pipes}
                fontFamily="ui-monospace, SFMono-Regular, monospace">onämnd — redovisas, mäts inte</text>
            </svg>
          </div>

          <div className="lp-scene-side">
            <ol className="lp-beats">
              {BEATS.map(([h, s], i) => (
                <li key={h} className={i === beat ? "on" : i < beat ? "past" : ""}>
                  <span className="no">{String(i + 1).padStart(2, "0")}</span>
                  <span>
                    <b>{h}</b>
                    <em>{s}</em>
                  </span>
                </li>
              ))}
            </ol>
            <div className="lp-tally">
              {RUNS.map((r, i) => {
                const k = win(measure, i * 0.12, i * 0.12 + 0.55);
                return (
                  <div key={i} className="lp-tally-row">
                    <span className="sw" style={{ background: r.c, opacity: 0.25 + 0.75 * k }} />
                    <span className="dq">{["S1-P2-110", "KV1-X31-16", "VV1-X31-16", "S3-R8-75"][i]}</span>
                    <span className="mq">{(r.m * k).toFixed(1).replace(".", ",")} m</span>
                  </div>
                );
              })}
              <div className="lp-tally-row sum">
                <span className="dq">Summa</span>
                <span className="mq">{(RUNS.reduce((s, r) => s + r.m, 0) * measure).toFixed(1).replace(".", ",")} m</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
