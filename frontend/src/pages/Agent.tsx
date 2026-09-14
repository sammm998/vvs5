import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

/* Agenten som egen plats.
 *
 * Inte analysens agent bakom en projektväljare: den här börjar tomt. Du drar in en handling i samtalet och
 * frågar. Filen blir en riktig ritning på ditt eget skrivbord - samma motor, samma credits, samma artefakter -
 * så svaret går att öppna i Analys och räkna vidare på, utan att du har lagt upp ett projekt.
 *
 * Samma löfte som överallt: modellen väljer vilken fråga som ställs till ritningen, verktygen svarar ur det som
 * lästs, och en siffra utan belägg blir "det står inte i handlingen".
 */

type Fil = { id: string; filnamn: string; sidor: number; storlek: number; jobb?: { id: string; status: string; steg: string; andel: number } | null };
type Msg = { role: "user" | "agent"; text: string; tools?: any[]; jobs?: string[] };

const START = [
  "Vad är det här för blad?",
  "Läs ritningen och visa mängderna",
  "Vad kunde inte avgöras?",
  "Vad kostar rören enligt materialboken?",
];

function kb(n: number) {
  return n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} kB`;
}

function lage(f: Fil) {
  const j = f.jobb;
  if (!j) return { txt: "inte läst", cls: "" };
  if (j.status === "COMPLETED") return { txt: "läst", cls: "ok" };
  if (j.status === "FAILED") return { txt: "läsningen gick inte", cls: "bad" };
  return { txt: `läser · ${Math.round((j.andel || 0) * 100)} %`, cls: "run" };
}

export default function AgentPage() {
  const [files, setFiles] = useState<Fil[]>([]);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);
  const [err, setErr] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const pick = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try { setFiles((await api.deskFiles()).filer || []); } catch (e: any) { setErr(e.message); }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  // en läsning tar en stund; så länge någon fil läser frågar sidan om läget, sedan slutar den
  useEffect(() => {
    const reading = files.some((f) => f.jobb && (f.jobb.status === "QUEUED" || f.jobb.status === "RUNNING"));
    if (!reading) return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [files, load]);

  const take = async (list: FileList | File[]) => {
    const arr = Array.from(list).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (!arr.length) { setErr("Agenten läser PDF. Spara om filen som PDF och släpp den igen."); return; }
    setErr("");
    for (const f of arr) {
      try {
        const up = await api.deskUpload(f);
        setFiles((x) => [...x, up]);
        setMsgs((m) => [...m, { role: "user", text: `📄 ${up.filnamn} · ${up.sidor} sid` }]);
      } catch (e: any) { setErr(e?.message || "filen kunde inte tas emot"); }
    }
  };

  const send = async (q: string) => {
    const fraga = q.trim();
    if (!fraga || busy) return;
    setText(""); setErr("");
    const historik: any[] = [];
    setMsgs((m) => [...m, { role: "user", text: fraga }]);
    setBusy(true);
    try {
      const r = await api.deskAsk({ fraga, filer: files.map((f) => f.id), historik });
      setMsgs((m) => [...m, { role: "agent", text: r.svar || "(inget svar)", tools: r.verktyg ?? [], jobs: r.startade_lasningar ?? [] }]);
      if (r.filer) setFiles(r.filer);
    } catch (e: any) {
      setErr(e?.message || "agenten kunde inte svara");
    } finally { setBusy(false); }
  };

  const read = files.filter((f) => f.jobb?.status === "COMPLETED");

  return (
    <main className="agentpage"
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); take(e.dataTransfer.files); }}>
      <p className="crumb">Agent</p>
      <div className="head">
        <div>
          <h1>Agenten</h1>
          <p className="lead">
            Släpp en ritning i samtalet och fråga. Agenten läser den med samma motor som analysen, svarar ur det
            som står i handlingen och säger vad den inte kunde avgöra. Den hittar inte på en siffra.
          </p>
        </div>
      </div>
      {err && <p className="error">{err}</p>}

      <div className={`deskwrap${over ? " over" : ""}`}>
        <section className="deskchat">
          {!msgs.length && (
            <div className="deskempty">
              <p className="muted">Inget i samtalet ännu.</p>
              <div className="deskstart">
                {START.map((s) => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}
              </div>
              <p className="muted small">Du kan dra in en PDF var som helst på sidan.</p>
            </div>
          )}
          {msgs.map((m, i) => (
            <div key={i} className={`bubble ${m.role}`}>
              <div className="txt">{m.text}</div>
              {!!m.jobs?.length && (
                <p className="small muted">Läsningen är startad. Den syns bland filerna här bredvid när den är klar.</p>
              )}
              {!!m.tools?.length && (
                <details className="tools">
                  <summary>{m.tools.length} verktygsanrop</summary>
                  {m.tools.map((t: any, k: number) => (
                    <pre key={k} className="tool"><b>{t.namn}</b>({JSON.stringify(t.argument)}){"\n"}
                      {JSON.stringify(t.resultat, null, 1).slice(0, 1400)}</pre>
                  ))}
                </details>
              )}
            </div>
          ))}
          {busy && <div className="bubble agent"><div className="txt muted">tänker…</div></div>}
          <div ref={end} />
        </section>

        <aside className="deskfiles">
          <div className="org">Filer i samtalet</div>
          {!files.length && <p className="muted small">Inga filer ännu. Dra in en PDF, eller välj en nedan.</p>}
          {files.map((f) => {
            const l = lage(f);
            return (
              <div key={f.id} className="deskfile">
                <div className="nm" title={f.filnamn}>{f.filnamn}</div>
                <div className="muted small">{f.sidor} sid · {kb(f.storlek)} · <span className={`st ${l.cls}`}>{l.txt}</span></div>
                {f.jobb?.status === "COMPLETED" && (
                  <div className="row small">
                    <Link to={`/jobs/${f.jobb.id}`}>Öppna i analysen</Link>
                    <Link to={`/mangda/${f.id}`}>Mängda</Link>
                  </div>
                )}
              </div>
            );
          })}
          <input ref={pick} type="file" accept="application/pdf" multiple hidden
                 onChange={(e) => { if (e.target.files) take(e.target.files); e.currentTarget.value = ""; }} />
          <button className="ghost" onClick={() => pick.current?.click()}>Välj fil…</button>
          {read.length > 1 && (
            <button className="ghost" onClick={() => send(`Jämför ${read[0].filnamn} med ${read[1].filnamn}`)}>
              Jämför de två senast lästa
            </button>
          )}
          <p className="muted small" style={{ marginTop: 10 }}>
            En läsning kostar credits, precis som i analysen. Filerna ligger på ditt konto och syns inte bland
            projekten.
          </p>
        </aside>
      </div>

      <form className="deskask" onSubmit={(e) => { e.preventDefault(); send(text); }}>
        <button type="button" className="ghost attach" title="Bifoga PDF" onClick={() => pick.current?.click()}>＋</button>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Fråga om ritningen…" disabled={busy} />
        <button type="submit" disabled={busy || !text.trim()}>Fråga</button>
      </form>
    </main>
  );
}
