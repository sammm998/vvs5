import { useEffect, useState } from "react";
import { api } from "../api";

/* Kalkylen: från mängd till pris, och anbudet.
 *
 * Två steg som hålls isär så att varje krona går att spåra till en rad på ritningen. Material: varje
 * beteckning matchas mot materialboken och får ett FÖRSLAG med alternativ bredvid - den som räknar väljer.
 * Arbete: timmarna kommer ur Normtid VVS, med tillägg och avvikelseanalys utskrivna. Där boken inte har någon
 * tid står det, och timmen skrivs för hand.
 *
 * Talen räknas om på servern varje gång ur läsningen med rättelserna ovanpå. Det som sparas är valen.
 */

const kr = (v: number | null | undefined) =>
  v == null ? "–" : `${v.toLocaleString("sv-SE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kr`;
const num = (v: number | null | undefined, d = 2) =>
  v == null ? "–" : v.toLocaleString("sv-SE", { maximumFractionDigits: d });

export default function Calc({ jobId }: { jobId: string }) {
  const [under, setUnder] = useState<any>(null);
  const [A, setA] = useState<any>(null);
  const [ov, setOv] = useState<Record<string, { artikel?: string; timmar?: number }>>({});
  const [calc, setCalc] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    api.calcUnderlag(jobId).then((u) => {
      setUnder(u);
      api.calc(jobId).then((c) => {
        if (c.status === "SAVED") { setA(c.assumptions); setCalc(c); setSaved(c.saved_at); }
        else setA(u.defaults);
      }).catch(() => setA(u.defaults));
    }).catch((e) => setErr(e.message));
  }, [jobId]);

  const run = async (save = false) => {
    if (!A) return;
    setBusy(true); setErr("");
    try {
      const r = save ? await api.calcSave(jobId, { assumptions: A, overrides: ov })
                     : await api.calcPreview(jobId, { assumptions: A, overrides: ov });
      setCalc(r);
      if (save) setSaved(r.saved_at);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const openPdf = async () => {
    try {
      const blob = await api.fetchBlob(api.anbudPdfUrl(jobId));
      window.open(URL.createObjectURL(blob), "_blank");
    } catch (e: any) { setErr(e.message); }
  };
  const showHtml = async () => {
    try {
      const blob = await api.fetchBlob(api.anbudHtmlUrl(jobId));
      setPreview(await blob.text());
    } catch (e: any) { setErr(e.message); }
  };

  if (!A) return <div className="card"><p className="muted">{err || "Laddar underlaget…"}</p></div>;
  const T = calc?.totals;
  const set = (k: string, v: any) => setA({ ...A, [k]: v });
  const sup: string[] = A.supplements ?? [];
  const groups: Record<string, any[]> = {};
  (under?.normtid?.supplements ?? []).forEach((s: any) => { (groups[s.group] ??= []).push(s); });

  return (
    <div className="card calc">
      <p className="muted" style={{ marginTop: 0 }}>
        Material ur materialboken, timmar ur Normtid VVS, allt utskrivet rad för rad. Talen räknas ur läsningen
        med dina rättelser ovanpå. {under?.normtid?.warning}
      </p>

      <div className="adm-form">
        <label className="adm-field"><span>Timpris kr/h</span><input type="number" value={A.timpris} onChange={(e) => set("timpris", Number(e.target.value))} /></label>
        <label className="adm-field"><span>Spill %</span><input type="number" value={A.spill_pct} onChange={(e) => set("spill_pct", Number(e.target.value))} /></label>
        <label className="adm-field"><span>Påslag material %</span><input type="number" value={A.paslag_material_pct} onChange={(e) => set("paslag_material_pct", Number(e.target.value))} /></label>
        <label className="adm-field"><span>Påslag arbete %</span><input type="number" value={A.paslag_arbete_pct} onChange={(e) => set("paslag_arbete_pct", Number(e.target.value))} /></label>
        <label className="adm-field"><span>Moms %</span><input type="number" value={A.moms_pct} onChange={(e) => set("moms_pct", Number(e.target.value))} /></label>
        <label className="adm-field"><span>Våningshöjd m (stigare)</span><input type="number" step="0.1" value={A.floor_height_m} onChange={(e) => set("floor_height_m", Number(e.target.value))} /></label>
      </div>

      <details style={{ marginTop: 10 }}>
        <summary className="muted small">Tillägg och avvikelseanalys (Normtid VVS)</summary>
        {Object.entries(groups).map(([g, items]) => (
          <div key={g} className="row" style={{ marginTop: 6, gap: 8 }}>
            <span className="muted small" style={{ minWidth: 150 }}>{g}</span>
            {items.map((s: any) => (
              <label key={s.id} className="small check">
                <input type="checkbox" checked={sup.includes(s.id)}
                  onChange={(e) => set("supplements", e.target.checked ? [...sup, s.id] : sup.filter((x) => x !== s.id))} />
                {" "}{s.label} +{Math.round(s.pct * 100)} %
              </label>
            ))}
          </div>
        ))}
        {(under?.normtid?.factors ?? []).map((f: any) => (
          <div key={f.id} className="row" style={{ marginTop: 6, gap: 8 }}>
            <span className="muted small" style={{ minWidth: 150 }} title={`${f.less} / ${f.normal} / ${f.more}`}>{f.label}</span>
            <select value={(A.factors ?? {})[f.id] ?? 0} onChange={(e) => set("factors", { ...(A.factors ?? {}), [f.id]: Number(e.target.value) })}>
              {f.scale.map((v: number) => <option key={v} value={v}>{v > 0 ? `+${v}` : v} %</option>)}
            </select>
          </div>
        ))}
      </details>

      <details style={{ marginTop: 8 }}>
        <summary className="muted small">Anbudets huvud</summary>
        <div className="adm-form" style={{ marginTop: 6 }}>
          <label className="adm-field"><span>Vårt företag</span><input value={A.company ?? ""} onChange={(e) => set("company", e.target.value)} /></label>
          <label className="adm-field"><span>Beställare</span><input value={A.customer ?? ""} onChange={(e) => set("customer", e.target.value)} /></label>
          <label className="adm-field"><span>Referens</span><input value={A.reference ?? ""} onChange={(e) => set("reference", e.target.value)} /></label>
          <label className="adm-field"><span>Giltigt i dagar</span><input type="number" value={A.valid_days} onChange={(e) => set("valid_days", Number(e.target.value))} /></label>
        </div>
        <label className="adm-field" style={{ marginTop: 6 }}><span>Inledning</span>
          <textarea rows={3} value={A.intro ?? ""} onChange={(e) => set("intro", e.target.value)} /></label>
      </details>

      <div className="row" style={{ marginTop: 12 }}>
        <button onClick={() => run(false)} disabled={busy}>{busy ? "Räknar…" : calc ? "Räkna om" : "Kalkylera"}</button>
        {calc && <button className="secondary" onClick={() => run(true)} disabled={busy}>Spara kalkyl</button>}
        {saved && <>
          <button className="secondary" onClick={openPdf}>Anbud som PDF</button>
          <button className="ghost small" onClick={showHtml}>Förhandsgranska</button>
          <span className="muted small">sparad {new Date(saved).toLocaleString("sv-SE")}</span>
        </>}
      </div>
      {err && <p className="error">{err}</p>}

      {calc && (
        <>
          <div className="adm-stats" style={{ marginTop: 14 }}>
            <div className="adm-stat"><div className="k">Material</div><div className="v">{kr(T.material_kr)}</div></div>
            <div className="adm-stat"><div className="k">Timmar</div><div className="v">{num(T.timmar, 1)}</div><div className="s">{kr(T.arbete_kr)} arbete</div></div>
            <div className="adm-stat"><div className="k">Exkl. moms</div><div className="v">{kr(T.netto_kr)}</div><div className="s">påslag {kr(T.paslag_material_kr + T.paslag_arbete_kr)}</div></div>
            <div className="adm-stat good"><div className="k">Anbudssumma inkl. moms</div><div className="v">{kr(T.brutto_kr)}</div></div>
            {(T.utan_artikel > 0 || T.utan_normtid > 0) && (
              <div className="adm-stat bad"><div className="k">Att välja</div><div className="v">{T.utan_artikel + T.utan_normtid}</div>
                <div className="s">{T.utan_artikel} utan artikel · {T.utan_normtid} utan normtid</div></div>
            )}
          </div>

          <div className="tablewrap" style={{ marginTop: 12 }}>
            <table className="qty">
              <thead><tr><th>Beteckning</th><th>Artikel (nettopris/m)</th><th className="num">Kalkylmängd</th>
                <th className="num">Material</th><th className="num">Normtid</th><th className="num">Timmar</th>
                <th className="num">Arbete</th><th className="num">Summa</th></tr></thead>
              <tbody>
                {calc.rows.map((r: any) => (
                  <tr key={r.designation} className={!r.artikel || r.timmar == null ? "pa-weak" : ""}>
                    <td className="lf-mono"><b>{r.designation}</b><div className="muted small">DN{r.dn ?? "?"} · {r.material_ord.join(" ") || r.material_kod}</div></td>
                    <td>
                      <select value={ov[r.designation]?.artikel ?? r.artikel?.a ?? ""}
                        onChange={(e) => setOv({ ...ov, [r.designation]: { ...ov[r.designation], artikel: e.target.value || undefined } })}>
                        <option value="">{r.alternativ.length ? "– välj artikel –" : "ingen träff i boken"}</option>
                        {r.alternativ.map((a: any) => <option key={a.a} value={a.a}>{a.n} · {kr(a.netto)}</option>)}
                        {r.artikel && !r.alternativ.some((a: any) => a.a === r.artikel.a) && <option value={r.artikel.a}>{r.artikel.n} · {kr(r.artikel.netto)}</option>}
                      </select>
                    </td>
                    <td className="num">{num(r.kalkyl_m)} m<div className="muted small">{num(r.horisontellt_m)} + {r.stigare} st</div></td>
                    <td className="num">{kr(r.material_kr)}</td>
                    <td className="muted small">{r.normtid_kalla}{r.steg?.grundtid_per_m ? ` · ${r.steg.grundtid_per_m} h/m` : ""}</td>
                    <td className="num">
                      <input type="number" step="0.1" style={{ width: 78, textAlign: "right" }}
                        value={ov[r.designation]?.timmar ?? r.timmar ?? ""}
                        placeholder={r.timmar == null ? "ange" : ""}
                        onChange={(e) => setOv({ ...ov, [r.designation]: { ...ov[r.designation], timmar: e.target.value === "" ? undefined : Number(e.target.value) } })} />
                    </td>
                    <td className="num">{kr(r.arbete_kr)}</td>
                    <td className="num"><b>{kr(r.summa_kr)}</b></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {calc.caveats?.length > 0 && (
            <div className="pa-unread" style={{ marginTop: 10 }}>
              <b>Förbehåll som följer med anbudet</b>
              <ul style={{ margin: "6px 0 0 16px" }}>{calc.caveats.map((c: string) => <li key={c} className="small">{c}</li>)}</ul>
            </div>
          )}
          <p className="muted small">Ändrade artiklar eller timmar räknas in när du trycker Räkna om eller Spara kalkyl.</p>
        </>
      )}

      {preview && (
        <div className="card" style={{ marginTop: 12, padding: 0, overflow: "hidden" }}>
          <div className="row" style={{ justifyContent: "space-between", padding: "8px 12px" }}>
            <b>Anbudet</b><button className="ghost small" onClick={() => setPreview(null)}>Stäng</button>
          </div>
          <iframe title="Anbud" srcDoc={preview} style={{ width: "100%", height: 720, border: 0 }} />
        </div>
      )}
    </div>
  );
}
