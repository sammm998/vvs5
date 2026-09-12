import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import "../landing.css";

/* Ramen kring de publika sidorna: samma mörka bakgrund, samma hörnknappar och samma sidfot som landningssidan,
 * så att priser, om oss, hur det funkar, utbildning och kontakt känns som rum i samma hus - inte som fem
 * hemsidor. Menyn är densamma överallt; den sida man står på är tänd. */

export const PUBLIC_LINKS: { to: string; label: string }[] = [
  { to: "/hur-det-funkar", label: "Hur det funkar" },
  { to: "/priser", label: "Priser" },
  { to: "/utbildning", label: "Utbildning" },
  { to: "/om-oss", label: "Om oss" },
  { to: "/dokumentation", label: "Dokumentation" },
  { to: "/kontakt", label: "Kontakta oss" },
];

export default function PublicFrame({ kicker, title, lede, children, wide = false }:
  { kicker: string; title: string; lede?: string; children: any; wide?: boolean }) {
  const { pathname } = useLocation();
  const [menu, setMenu] = useState(false);
  useEffect(() => {
    document.body.classList.add("lp-dark");
    window.scrollTo(0, 0);
    return () => document.body.classList.remove("lp-dark");
  }, [pathname]);
  return (
    <div className="lp docs pub">
      <div className="lp-corners">
        <button className="lp-pill" aria-expanded={menu} aria-label={menu ? "Stäng menyn" : "Öppna menyn"}
          onClick={() => setMenu((m) => !m)}>
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
            {menu
              ? <path d="M3 3 L13 13 M13 3 L3 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              : <path d="M2 4 H14 M2 8 H14 M2 12 H14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />}
          </svg>
          Meny
        </button>
        <Link className="lp-logo lp-pill static" to="/">
          <svg width="18" height="18" viewBox="0 0 22 22" aria-hidden="true">
            <path d="M3 15 H8 V7 H14 V15 H19" stroke="currentColor" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          VVS Mängdning
        </Link>
        <span className="lp-sp" />
        <nav className="pub-nav" aria-label="Publika sidor">
          {PUBLIC_LINKS.map((l) => (
            <Link key={l.to} to={l.to} className={pathname === l.to ? "on" : ""}>{l.label}</Link>
          ))}
        </nav>
        <Link className="lp-pill lp-start" to="/login">Logga in <span className="plus">→</span></Link>
      </div>
      {menu && (
        <div className="lp-menu">
          {PUBLIC_LINKS.map((l) => <Link key={l.to} to={l.to} onClick={() => setMenu(false)}>{l.label}</Link>)}
          <Link to="/login" onClick={() => setMenu(false)}>Logga in</Link>
        </div>
      )}

      <header className="docs-head">
        <p className="lp-mono">{kicker}</p>
        <h1>{title}</h1>
        {lede && <p className="docs-lede">{lede}</p>}
      </header>

      <main className={`pub-body${wide ? " wide" : ""}`}>{children}</main>

      <footer className="lp-wrap">
        <div className="lp-foot">
          <span className="lp-logo" style={{ fontSize: 14 }}>
            <svg width="18" height="18" viewBox="0 0 22 22" aria-hidden="true">
              <path d="M3 15 H8 V7 H14 V15 H19" stroke="#5b616c" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            VVS Mängdning
          </span>
          <span className="sp" />
          {PUBLIC_LINKS.map((l) => <Link key={l.to} to={l.to}>{l.label}</Link>)}
          <Link to="/login">Logga in</Link>
        </div>
      </footer>
    </div>
  );
}

/** En text som en administratör kan ha skrivit om i innehållsverktyget; annars den inbyggda. */
export function usePublished(slug: string): { title: string; body: string } | null {
  const [c, setC] = useState<{ title: string; body: string } | null>(null);
  useEffect(() => {
    fetch(`/api/public/content/${slug}`).then((r) => (r.ok ? r.json() : null)).then((j) => j && setC(j)).catch(() => { /* inbyggd text */ });
  }, [slug]);
  return c;
}

/** Enkel text i stycken: tomrad blir nytt stycke, rader som börjar med "## " blir mellanrubrik. */
export function Prose({ text }: { text: string }) {
  return (
    <>
      {text.split(/\n{2,}/).map((blk, i) =>
        blk.startsWith("## ") ? <h2 key={i}>{blk.slice(3)}</h2> : <p key={i}>{blk}</p>)}
    </>
  );
}
