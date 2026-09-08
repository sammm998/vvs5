import { useEffect, useState } from "react";
import { api } from "../api";
import { AGENTS, AGENT_SV, frameSays } from "../agents";

/* How the reading got to its answer, from the first pass over the PDF to the last verdict.
 *
 * Every stage says what it found and hands that on to the next; the numbers are the ones the reading actually
 * worked from, not a retelling. After them the review agents speak: they never touch the measurement, they only
 * say whether they believe it, so a disagreement stays visible instead of being averaged away.
 */

type Frame = { stage: string; at: number; [k: string]: any };

const SEV: Record<string, string> = { ERROR: "bad", WARN: "warn", INFO: "ok" };

export default function Reasoning({ jobId, result }: { jobId: string; result: any }) {
  const [frames, setFrames] = useState<Frame[]>([]);
  useEffect(() => {
    let live = true;
    api.film(jobId).then((f: any) => { if (live && Array.isArray(f.frames)) setFrames(f.frames); }).catch(() => { /* the account is a view */ });
    return () => { live = false; };
  }, [jobId]);
  const byStage: Record<string, Frame> = {};
  for (const f of frames) byStage[f.stage] = f;
  const findings = result?.review?.findings ?? [];
  const byAgent = new Map<string, any[]>();
  for (const f of findings) {
    const k = f.agent;
    if (!byAgent.has(k)) byAgent.set(k, []);
    byAgent.get(k)!.push(f);
  }
  const sr = result?.coverage?.second_reader;

  return (
    <div className="sheetview">
      <div className="card reasoning">
        <h3>Så kom läsningen fram till svaret</h3>
        <p className="muted">
          Varje steg lämnar sitt fynd vidare till nästa. Granskarna längst ned rör aldrig mätningen — de säger
          bara om de tror på den, så att en oenighet syns istället för att jämnas ut.
        </p>

        <ol className="steps">
          {AGENTS.map((s, i) => {
            const f = byStage[s.stage];
            const lines = frameSays(s.stage, f, result);
            const done = !!f || s.stage === "MEASURING";
            return (
              <li key={s.stage} className={done ? "done" : "pending"}>
                <div className="stepno">{i + 1}</div>
                <div className="stepbody">
                  <div className="stepwho">{s.who}</div>
                  <h4>{s.title}</h4>
                  <p className="asks">”{s.asks}”</p>
                  {lines.length
                    ? lines.map((l, j) => <p key={j} className="says">{l}</p>)
                    : <p className="says muted">Steget lämnade inget att visa på det här bladet.</p>}
                  {i < AGENTS.length - 1 && <div className="handoff">lämnar vidare till {AGENTS[i + 1].who}</div>}
                </div>
              </li>
            );
          })}
        </ol>

        <h3>Granskarna</h3>
        {byAgent.size === 0 && <p className="muted">Ingen granskning finns sparad för det här jobbet.</p>}
        {[...byAgent.entries()].map(([agent, fs]) => (
          <div key={agent} className="agentcard">
            <div className="agenthead">
              <b>{AGENT_SV[agent] ?? agent}</b>
              <span className={`badge ${SEV[fs[0].severity] ?? "ok"}`}>
                {fs.some((f: any) => f.severity === "ERROR") ? "invänder" : fs.some((f: any) => f.severity === "WARN") ? "reserverar sig" : "noterar"}
              </span>
            </div>
            {fs.map((f: any, i: number) => (
              <p key={i} className="says">{f.message}</p>
            ))}
          </div>
        ))}

        <div className="agentcard">
          <div className="agenthead">
            <b>Andraläsaren</b>
            <span className={`badge ${sr?.consulted ? "warn" : "ok"}`}>{sr?.consulted ? "tillfrågad" : "ej tillfrågad"}</span>
          </div>
          <p className="says">
            {sr?.consulted
              ? `Tillfrågad i ${sr.calls ?? "?"} fall som läsningen själv inte kunde avgöra. Varje svar prövades mot ritningens egna kandidater innan det fick flytta en meter.`
              : "Läsningen behövde ingen andra mening på det här bladet: varje identitet vilar på en beteckning, en ritad hänvisningslinje och den graf geometrin bildar."}
          </p>
        </div>
      </div>
    </div>
  );
}
