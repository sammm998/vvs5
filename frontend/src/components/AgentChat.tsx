import { useEffect, useRef, useState } from "react";
import { api } from "../api";

/* The agent, working against the reading rather than against a picture of it.
 *
 * Every number it says came out of a tool call over the artifacts the measurement wrote, so what it answers here
 * and what the takeoff table says are the same thing. The tools it used are shown under each answer, and the
 * runs it rests on can be lit up on the sheet - a claim you cannot point at is not an answer.
 */

type Msg = { role: "user" | "agent"; text: string; tools?: any[]; ids?: string[] };

/* A first question is the hardest one to write, so the ones worth asking are on the surface - grouped the way a
   reader thinks: what does it measure, what should I check, what does this drawing say. */
const QUICK: { grupp: string; fragor: string[] }[] = [
  { grupp: "Mängd", fragor: ["Mängda per system", "Mängda per dimension", "Visa hur mängden räknades"] },
  { grupp: "Kontroll", fragor: ["Hitta fel i läsningen", "Var byter rören dimension?", "Vilka rörändar är fria?",
                                "Var är samma linje ritad två gånger?"] },
  { grupp: "Ritningen", fragor: ["Förklara beteckningarna", "Hur lästes skalan?"] },
];

export default function AgentChat({ jobId, page, selection, onHighlight }: {
  jobId: string;
  page: number;
  selection: { pipeIds: string[]; bbox: number[] | null };
  onHighlight: (ids: string[]) => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [listening, setListening] = useState(false);
  const [speak, setSpeak] = useState(false);
  const rec = useRef<any>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const send = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    setText(""); setErr("");
    setMsgs((m) => [...m, { role: "user", text: question }]);
    setBusy(true);
    try {
      const r = await api.agent(jobId, {
        question, page,
        pipe_ids: selection.pipeIds.length ? selection.pipeIds : undefined,
        bbox: selection.bbox ?? undefined,
      });
      const ids: string[] = r.markera?.ror_id ?? [];
      setMsgs((m) => [...m, { role: "agent", text: r.svar || "(inget svar)", tools: r.verktyg ?? [], ids }]);
      if (ids.length) onHighlight(ids);
      if (speak && r.svar) {
        try {
          const u = new SpeechSynthesisUtterance(r.svar);
          u.lang = "sv-SE";
          window.speechSynthesis.speak(u);
        } catch { /* a browser without speech simply stays quiet */ }
      }
    } catch (e: any) {
      setErr(e?.message || "agenten kunde inte svara");
    } finally {
      setBusy(false);
    }
  };

  /* Voice in: the browser's own recogniser, so nothing is uploaded to reach it. */
  const toggleMic = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { setErr("den här webbläsaren har ingen taligenkänning"); return; }
    if (listening) { rec.current?.stop(); setListening(false); return; }
    const r = new SR();
    r.lang = "sv-SE"; r.interimResults = true; r.continuous = false;
    r.onresult = (e: any) => {
      const said = Array.from(e.results).map((x: any) => x[0].transcript).join("");
      setText(said);
      if (e.results[e.results.length - 1].isFinal) { setListening(false); send(said); }
    };
    r.onerror = () => setListening(false);
    r.onend = () => setListening(false);
    rec.current = r;
    setListening(true);
    r.start();
  };

  const nSel = selection.pipeIds.length;
  return (
    <div className="agentchat">
      <div className="agentctx">
        <span className="dotlive" />
        <span>Sida {page + 1}</span>
        {nSel > 0 && <span className="sel">{nSel} markerade rör</span>}
        {selection.bbox && !nSel && <span className="sel">markerat område</span>}
        {msgs.length > 0 && (
          <button className="ghost small clear" onClick={() => { setMsgs([]); setErr(""); }}>Rensa</button>
        )}
      </div>

      <div className="agentlog">
        {msgs.length === 0 && (
          <div className="agentintro">
            <h4>Fråga ritningen</h4>
            <p>
              Varje siffra agenten säger kommer ur ett verktygsanrop mot läsningen — den räknar aldrig själv,
              och den hittar inte på ett rör-id. Markera något i ritningen först, så vet den vad ”det här” är.
            </p>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`abub ${m.role}`}>
            <div className="who">{m.role === "user" ? "Du" : "Agenten"}</div>
            <p>{m.text}</p>
            {m.tools && m.tools.length > 0 && (
              <details className="atools">
                <summary>{m.tools.length} verktygsanrop</summary>
                {m.tools.map((t: any, j: number) => (
                  <div key={j} className="atool">
                    <code>{t.namn}({Object.entries(t.argument || {}).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ")})</code>
                  </div>
                ))}
              </details>
            )}
            {m.ids && m.ids.length > 0 && (
              <button className="showbtn" onClick={() => onHighlight(m.ids!)}>
                Visa {m.ids.length} {m.ids.length === 1 ? "sträcka" : "sträckor"} på ritningen
              </button>
            )}
          </div>
        ))}
        {busy && <div className="abub agent"><div className="who">Agenten</div><p className="dots"><i /><i /><i /></p></div>}
        {err && <p className="error">{err}</p>}
        <div ref={end} />
      </div>

      <div className="agentquick">
        {QUICK.map((g) => (
          <div key={g.grupp} className="qgroup">
            <span className="qlabel">{g.grupp}</span>
            {g.fragor.map((q) => (
              <button key={q} className="chipbtn" onClick={() => send(q)} disabled={busy}>{q}</button>
            ))}
          </div>
        ))}
      </div>

      <div className="agentbar">
        <textarea rows={2} value={text} placeholder="Skriv en fråga, eller tryck på Tala…"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text); } }} />
        <div className="agentbtns">
          {/* words rather than glyphs: an emoji that a machine has no font for is a blank button */}
          <button className={`pillbtn${listening ? " on" : ""}`} onClick={toggleMic}
            title={listening ? "Lyssnar — tryck för att sluta" : "Tala i stället för att skriva"}>
            {listening ? "Lyssnar" : "Tala"}
          </button>
          <button className={`pillbtn${speak ? " on" : ""}`} onClick={() => setSpeak(!speak)}
            title={speak ? "Svaren läses upp" : "Läs upp svaren"}>Röst</button>
          <button className="ask" onClick={() => send(text)} disabled={busy || !text.trim()}>Fråga</button>
        </div>
      </div>
    </div>
  );
}
