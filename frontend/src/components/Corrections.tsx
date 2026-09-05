import { useState } from "react";
import { api } from "../api";

type Draft = { points: number[][] } | null;

const KINDS: { k: string; label: string; help: string }[] = [
  { k: "extend", label: "Förläng rör", help: "Rita vidare där sträckan fortsätter men motorn slutade." },
  { k: "draw", label: "Rita rör", help: "Rita en sträcka motorn inte såg alls." },
  { k: "erase", label: "Sudda", help: "Rita över det som mätts men inte är rör." },
  { k: "retag", label: "Byt beteckning", help: "Flytta meter från en beteckning till en annan." },
  { k: "quantity", label: "Rätta mängd", help: "Sätt längden för hand när ritningen säger något annat." },
];

export default function Corrections({ drawingId, jobId, page, quantities, corrections, draft, drawing,
  proposals = [], onDrawingChange, onDraftClear, onChanged }: {
    drawingId: string; jobId: string; page: number; quantities: any[];
    corrections: any[]; draft: Draft; drawing: string | null; proposals?: any[];
    onDrawingChange: (kind: string | null) => void; onDraftClear: () => void; onChanged: () => void;
  }) {
  const [designation, setDesignation] = useState("");
  const [from, setFrom] = useState("");
  const [meters, setMeters] = useState("");
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const kind = drawing;
  const needsLine = kind === "extend" || kind === "draw" || kind === "erase";
  const ready = !!kind && !!designation && (needsLine ? !!draft : !!meters) && (kind !== "retag" || !!from);

  const save = async () => {
    if (!kind || !ready) return;
    setBusy(true); setErr("");
    try {
      const payload: any = needsLine ? { points: draft!.points } : {};
      if (kind === "retag") { payload.from = from; payload.meters = Number(meters.replace(",", ".")) || 0; }
      if (kind === "quantity" || (kind === "erase" && !draft)) payload.meters = Number(meters.replace(",", ".")) || 0;
      await api.addCorrection(drawingId, {
        kind, designation, page, payload, note: note || null, job_id: jobId,
        // the situation the correction was made in, so a later reading can tell this case from a similar-looking one
        situation: { family_style: "", reason: "", designation_shape: "" },
      });
      setNote(""); setMeters(""); onDraftClear(); onDrawingChange(null); onChanged();
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const live = corrections.filter((c) => !c.undone);

  return (
    <>
      {proposals.length > 0 && (
        <div className="card">
          <h3>Från tidigare rättelser <span className="badge">{proposals.length}</span></h3>
          <p className="muted" style={{ marginTop: 0 }}>
            Förslag, inte beslut. En läxa får bara tala där motorn själv kallade fallet tvetydigt, och bara med ett
            svar ritningen erbjuder. Mängden flyttar sig först när du säger till.
          </p>
          {proposals.map((pr: any) => (
            <div key={pr.case} className="issue done-row">
              <div>
                <b>{pr.answer}</b>
                <div className="muted">{pr.why} · {pr.times} gång{pr.times === 1 ? "" : "er"}</div>
              </div>
              <button className="secondary small" onClick={async () => {
                await api.addCorrection(drawingId, {
                  kind: "retag", designation: pr.answer, page, job_id: jobId, payload: {},
                  situation: pr.situation, note: "godtaget förslag från en tidigare rättelse",
                });
                onChanged();
              }}>Använd</button>
            </div>
          ))}
        </div>
      )}
      <div className="card">
        <h3>Rätta läsningen</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Det du ändrar läggs ovanpå motorns läsning. Motorns egen siffra står kvar på varje rad, så det syns
          alltid vad som lästes och vad som rättades.
        </p>
        <div className="row" style={{ marginBottom: 14 }}>
          {KINDS.map((k) => (
            <button key={k.k} className={kind === k.k ? "" : "secondary"} onClick={() => {
              onDrawingChange(kind === k.k ? null : k.k); onDraftClear();
            }}>{k.label}</button>
          ))}
        </div>
        {kind && (
          <>
            <p className="muted" style={{ marginTop: 0 }}>{KINDS.find((k) => k.k === kind)!.help}</p>
            {needsLine && (
              <p className="muted">
                {draft ? `${draft.points.length} punkter ritade.` : "Klicka längs sträckan på ritningen, dubbelklicka för att avsluta."}
              </p>
            )}
            <div className="field">
              <label htmlFor="c-des">{kind === "retag" ? "Till beteckning" : "Beteckning"}</label>
              <input id="c-des" list="c-des-list" value={designation} onChange={(e) => setDesignation(e.target.value)}
                placeholder="t.ex. S3-R8-110" />
              <datalist id="c-des-list">
                {quantities.map((q) => <option key={q.designation} value={q.designation} />)}
              </datalist>
            </div>
            {kind === "retag" && (
              <div className="field">
                <label htmlFor="c-from">Från beteckning</label>
                <input id="c-from" list="c-des-list" value={from} onChange={(e) => setFrom(e.target.value)} />
              </div>
            )}
            {(kind === "retag" || kind === "quantity" || (kind === "erase" && !draft)) && (
              <div className="field">
                <label htmlFor="c-m">Meter</label>
                <input id="c-m" value={meters} onChange={(e) => setMeters(e.target.value)} placeholder="0,00" />
              </div>
            )}
            <div className="field">
              <label htmlFor="c-note">Varför</label>
              <input id="c-note" value={note} onChange={(e) => setNote(e.target.value)}
                placeholder="Valfritt, men det är detta som gör rättelsen begriplig sen" />
            </div>
            {err && <p className="error">{err}</p>}
            <button onClick={save} disabled={!ready || busy}>{busy ? "Sparar…" : "Spara rättelse"}</button>
          </>
        )}
      </div>

      <div className="card">
        <h3>Rättelser <span className="badge">{live.length}</span></h3>
        {live.length === 0 && <p className="muted">Inga ännu. Motorns läsning står som den är.</p>}
        {live.map((c) => (
          <div key={c.id} className="issue done-row">
            <div>
              <b>{KINDS.find((k) => k.k === c.kind)?.label ?? c.kind}</b> · {c.designation}
              {c.payload?.meters != null && <> · {String(c.payload.meters).replace(".", ",")} m</>}
              {c.payload?.from && <> · från {c.payload.from}</>}
              {c.note && <div className="muted">{c.note}</div>}
            </div>
            <button className="ghost small"
              onClick={async () => { await api.undoCorrection(drawingId, c.id); onChanged(); }}>Ångra</button>
          </div>
        ))}
      </div>
    </>
  );
}
