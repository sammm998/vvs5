import { useEffect, useState } from "react";
import { api } from "../api";

/* Antagandena mängden räknas ihop med. Inte regler för hur ritningen läses, utan för hur det lästa blir en
 * mängd: våningshöjden en stigare räknas som, var stigare räknas ifrån, och om rör i skrafferade ytor ingår.
 * De gäller för tjänsten; varje läsning kan avvika i sin egen vy, och exporten säger vad den räknat med. */
export function Assumptions() {
  const [s, setS] = useState<any>(null);
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.settings().then(setS).catch((e) => setErr(e.message)); }, []);
  if (err) return <p className="error">{err}</p>;
  if (!s) return <p className="muted">Laddar…</p>;
  const save = async (patch: any) => {
    setBusy(true); setErr(""); setSaved(false);
    try { setS(await api.setSettings(patch)); setSaved(true); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };
  return (
    <section className="card">
      <h3 style={{ marginTop: 0 }}>Antaganden för mängden</h3>
      <p className="muted">
        Ritningen anger nästan aldrig våningshöjden, så stigare räknas som antal tills en höjd är satt här.
        Rör i skrafferade ytor mäts alltid men ligger utanför den vågräta mängden om rutan är tom. Det som står
        här gäller varje ny läsning; den som tittar på en enskild läsning kan avvika för just den.
      </p>
      <div className="adm-form" style={{ marginTop: 10 }}>
        <label className="adm-field"><span>Våningshöjd för stigare (m)</span>
          <input value={s.floor_height_m ?? ""} placeholder="ej satt" disabled={busy}
            onChange={(e) => setS({ ...s, floor_height_m: e.target.value })}
            onBlur={(e) => save({ floor_height_m: e.target.value })} /></label>
        <label className="adm-field"><span>Stigare räknas från</span>
          <select value={s.riser_source} disabled={busy} onChange={(e) => save({ riser_source: e.target.value })}>
            <option value="labels">etiketter med dimension på raden under</option>
            <option value="symbols">ritade stigarsymboler</option>
          </select></label>
        <label className="small check" style={{ alignSelf: "end", paddingBottom: 8 }}>
          <input type="checkbox" checked={!!s.include_hatched} disabled={busy}
            onChange={(e) => save({ include_hatched: e.target.checked })} />
          {" "}Räkna med rör i skrafferade ytor
        </label>
      </div>
      {saved && <p className="muted small" style={{ marginBottom: 0 }}>Sparat. Gäller nästa läsning.</p>}

      <div className="rule" style={{ margin: "18px 0 14px" }} />
      <h3 style={{ marginTop: 0 }}>Vad läsningen kör</h3>
      <p className="muted">
        De två OCR-passen läser sidan som bild vid sidan av vektorkoden. De är avstängda som standard därför att
        de är mätta: korsprovet kan aldrig ändra ett mått (granskningen får inte röra läsningen) och kostade
        17 sekunder av 75 på ett A1-blad, och teckenhjälpen kostade 15–17 sekunder per blad utan att ändra
        mängden på något av de tre blad den provades på. Slå på dem om era ritningar läses sämre än så – det
        syns i granskningen, och analysen tar då ungefär dubbelt så lång tid.
      </p>
      <div className="adm-form" style={{ marginTop: 10 }}>
        <label className="small check">
          <input type="checkbox" checked={!!s.review_ocr} disabled={busy}
            onChange={(e) => save({ review_ocr: e.target.checked })} />
          {" "}Synagentens korsprov: läs sidan en gång till och varna för beteckningar vektorläsningen saknar
        </label>
        <label className="small check">
          <input type="checkbox" checked={!!s.ocr_assist} disabled={busy}
            onChange={(e) => save({ ocr_assist: e.target.checked })} />
          {" "}Teckenhjälp: låt OCR namnge tecken som streckläsaren inte kunde
        </label>
      </div>
    </section>
  );
}
