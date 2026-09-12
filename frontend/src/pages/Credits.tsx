import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import Tilted from "../components/Tilted";

/* Credits: vad kontot har, vad en läsning kostar och vad som hänt med potten.
 *
 * Saldot är summan av raderna i reskontran och ingenting annat, så sidan visar raderna - varje läsning, varje
 * köp, varje återbetalning med sitt skäl. Den som undrar varför saldot hoppade upp ska kunna läsa det här, inte
 * behöva fråga. */

const DATE = new Intl.DateTimeFormat("sv-SE", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
const KIND: Record<string, string> = {
  prov: "Provcredits", kop: "Köp", lasning: "Läsning", syn: "Andra blick", aterbetalning: "Återbetalning", tilldelning: "Tilldelning",
};

export const fmtCredits = (v: number) => v.toLocaleString("sv-SE", { maximumFractionDigits: 2 });

export default function CreditsPage() {
  const [me, setMe] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState("");
  const [bought, setBought] = useState<any>(null);
  const load = () => api.credits().then(setMe).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  const buy = async (id: string) => {
    setBusy(id); setErr(""); setBought(null);
    try { const r = await api.buyCredits(id); setBought(r.entry); await load(); }
    catch (e: any) { setErr(e.message); } finally { setBusy(""); }
  };
  if (!me) return <main>{err ? <p className="error">{err}</p> : "Laddar…"}</main>;
  const p = me.prices;
  return (
    <main>
      <p className="crumb"><Link to="/projekt">Projekt</Link> / Credits</p>
      <div className="head">
        <div>
          <h1>Credits</h1>
          <p className="lead">
            {me.exempt
              ? "Det här kontot driver tjänsten och betalar inte för sina egna läsningar."
              : "En läsning kostar credits. Priset visas innan den körs, och en läsning som inte kunde ge en meter kostar ingenting."}
          </p>
        </div>
        <div className="row">
          <div className="stat">
            <div className="k">Saldo</div>
            <div className="v">{fmtCredits(me.balance)} <span className="unit">credits</span></div>
          </div>
        </div>
      </div>
      {err && <p className="error" style={{ marginTop: 18 }}>{err}</p>}
      {bought && (
        <p className="ok" style={{ marginTop: 18 }}>
          {bought.note}. Credits finns på kontot nu; fakturan skickas till kontots adress.
        </p>
      )}

      <div className="rule" />
      <h2>Vad en läsning kostar</h2>
      <p className="muted">
        Priset följer bladet: formatet och mängden bläck. Ett blad med fler än {Number(p.ink_step_paths).toLocaleString("sv-SE")} banor
        kostar {fmtCredits(p.ink_step_credits)} credit mer per påbörjat sådant steg, upp till {fmtCredits(p.ink_cap_credits)} credits.
        Priset står på ritningen innan du trycker på Analysera.
      </p>
      <div className="tablewrap">
        <table className="qty">
          <thead><tr><th>Format</th><th>A3 och mindre</th><th>A2</th><th>A1</th><th>A0</th><th>Större än A0</th><th>Andra blick (syn)</th></tr></thead>
          <tbody>
            <tr>
              <td>Credits per sida</td>
              {["A3", "A2", "A1", "A0", "A0+"].map((k) => <td key={k}>{fmtCredits(p.sheet[k])}</td>)}
              <td>{fmtCredits(p.vision_page)} per sida</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="rule" />
      <h2>Fyll på</h2>
      <p className="muted">Priser exklusive moms. Köpet faktureras; credits finns på kontot direkt.</p>
      <div className="grid4">
        {(p.packages || []).map((pk: any) => (
          <Tilted as="article" deg={2} lift={5} className="card" key={pk.id}>
            <div className="ttl">{pk.name}</div>
            <div className="big">{pk.credits.toLocaleString("sv-SE")} <span className="unit">credits</span></div>
            <div className="sub">{pk.kr.toLocaleString("sv-SE")} kr · {(pk.kr / pk.credits).toLocaleString("sv-SE", { maximumFractionDigits: 2 })} kr per credit</div>
            <p className="muted small">{pk.lead}</p>
            <button disabled={!!busy} onClick={() => buy(pk.id)}>{busy === pk.id ? "Registrerar…" : "Köp"}</button>
          </Tilted>
        ))}
      </div>

      <div className="rule" />
      <h2>Reskontra</h2>
      <div className="tablewrap">
        <table className="qty">
          <thead><tr><th>När</th><th>Vad</th><th>Credits</th><th>Skäl</th><th>Status</th></tr></thead>
          <tbody>
            {me.entries.map((e: any) => (
              <tr key={e.id}>
                <td>{DATE.format(new Date(e.created_at))}</td>
                <td>{KIND[e.kind] || e.kind}</td>
                <td style={{ color: e.credits < 0 ? "var(--red, #c0392b)" : "var(--green, #1b7f4b)" }}>{e.credits > 0 ? "+" : ""}{fmtCredits(e.credits)}</td>
                <td className="muted">{e.note}{e.ref && e.kind === "lasning" ? <> · <Link to={`/jobs/${e.ref}`}>läsningen</Link></> : null}</td>
                <td>{e.status || ""}</td>
              </tr>
            ))}
            {me.entries.length === 0 && <tr><td colSpan={5} className="empty">Ingenting har hänt än.</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}

/** Priset för ett blad, hämtat innan läsningen: används på projekt- och ritningssidan bredvid knappen. */
export function PriceTag({ drawingId, onQuote }: { drawingId: string; onQuote?: (q: any) => void }) {
  const [q, setQ] = useState<any>(null);
  useEffect(() => {
    let on = true;
    api.price(drawingId).then((r) => { if (on) { setQ(r); onQuote?.(r); } }).catch(() => { /* priset visas när det finns */ });
    return () => { on = false; };
  }, [drawingId]);
  if (!q || q.exempt) return null;
  return (
    <span className={`badge ${q.enough ? "" : "warn"}`} title={q.reason}>
      {fmtCredits(q.credits)} credits{q.enough ? "" : ` · saldo ${fmtCredits(q.balance)}`}
    </span>
  );
}
