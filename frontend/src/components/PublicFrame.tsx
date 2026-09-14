import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import "../landing.css";
import SiteHeader, { PUBLIC_LINKS } from "./SiteHeader";
import { useScrollProgress } from "./lp-motion";

/* Ramen kring de publika sidorna.
 *
 * Priser, om oss, hur det funkar, utbildning och kontakt ska vara rum i samma hus som startsidan, inte fem
 * hemsidor. Därför samma rad högst upp (SiteHeader), samma mörka grund med sitt korn och sitt ljus, samma
 * skrollskena i kanten - och en hjälte som är byggd som startsidans: en liten etikett, en stor rubrik som får
 * ta plats, och en ingress som säger vad rummet är till för.
 *
 * Det enda som skiljer sidorna åt är innehållet.
 */

export { PUBLIC_LINKS };

export default function PublicFrame({ kicker, title, lede, children, wide = false, aside, anchors, bare }: {
  kicker?: string; title?: any; lede?: any; children: any; wide?: boolean;
  /** sidan har ett eget huvud och vill inte ha ramens hjälte ovanför det */
  bare?: boolean;
  /** det som står bredvid rubriken: en siffra, en figur, ett par nycklar */
  aside?: any;
  /** avsnitt på sidan, till menyns andra spalt */
  anchors?: { href: string; label: string }[];
}) {
  const { pathname } = useLocation();
  const scrolled = useScrollProgress();
  useEffect(() => {
    document.body.classList.add("lp-dark");
    window.scrollTo(0, 0);
    return () => document.body.classList.remove("lp-dark");
  }, [pathname]);
  return (
    <div className="lp pub">
      <SiteHeader anchors={anchors} />

      <div className="lp-rail" aria-hidden="true">
        <div className="lp-rail-fill" style={{ transform: `scaleY(${scrolled})` }} />
      </div>

      {bare ? <div className="pub-bare" /> : (
        <header className="pub-hero">
          <div className="pub-hero-in">
            <div>
              {kicker && <p className="lp-eyebrow"><span className="dot" />{kicker}</p>}
              <h1 className="pub-h1">{title}</h1>
              {lede && <p className="pub-lede">{lede}</p>}
            </div>
            {aside && <div className="pub-hero-aside">{aside}</div>}
          </div>
        </header>
      )}

      <main className={`pub-body${wide ? " wide" : ""}`}>{children}</main>

      <footer className="pub-foot">
        <div className="pub-foot-in">
          <div className="pub-foot-brand">
            <span className="lp-logo" style={{ fontSize: 15 }}>
              <svg width="18" height="18" viewBox="0 0 22 22" aria-hidden="true">
                <path d="M3 15 H8 V7 H14 V15 H19" stroke="#6ee7a5" strokeWidth="2.3" fill="none"
                  strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              VVS Mängdning
            </span>
            <p>Mängden som ritningen redan säger. Varje meter med sitt belägg kvar.</p>
          </div>
          <nav aria-label="Sidor">
            <p className="lp-mono">Sidor</p>
            {PUBLIC_LINKS.map((l) => <Link key={l.to} to={l.to}>{l.label}</Link>)}
          </nav>
          <nav aria-label="Kom igång">
            <p className="lp-mono">Kom igång</p>
            <Link to="/login">Logga in</Link>
            <Link to="/utbildning">VVS-akademin</Link>
            <Link to="/kontakt">Kontakta oss</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}

/** En sektion med samma rytm som startsidans: etikett, rubrik, innehåll. */
export function PubSection({ id, kicker, title, lede, children, tight }: {
  id?: string; kicker?: string; title?: any; lede?: any; children?: any; tight?: boolean;
}) {
  return (
    <section id={id} className={`pub-sec${tight ? " tight" : ""}`}>
      {(kicker || title) && (
        <div className="pub-sec-head">
          {kicker && <div className="lp-kicker">{kicker}</div>}
          {title && <h2>{title}</h2>}
          {lede && <p className="pub-sec-lede">{lede}</p>}
        </div>
      )}
      {children}
    </section>
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

/* Löpande text som en uppslagen sida i stället för en spalt.
 *
 * En rubrik och styckena under den hör ihop, så de sätts ihop till ett avsnitt: rubriken står kvar i vänstra
 * spalten medan texten löper i den högra. Det som står före den första rubriken är ingressen och får hela
 * bredden. Grupperingen sker här och inte i varje sida, så en text som en administratör skriver i
 * innehållsverktyget får samma form som den inbyggda. */
export function Prose({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean);
  const lead: string[] = [];
  const secs: { h: string; ps: string[] }[] = [];
  for (const b of blocks) {
    if (b.startsWith("## ")) secs.push({ h: b.slice(3), ps: [] });
    else if (secs.length) secs[secs.length - 1].ps.push(b);
    else lead.push(b);
  }
  return (
    <>
      {!!lead.length && (
        <div className="prose-lead">
          <div className="say"><p>{lead[0]}</p></div>
          <div className="rest">{lead.slice(1).map((t, i) => <p key={i}>{t}</p>)}</div>
        </div>
      )}
      {secs.map((s, i) => (
        <section className="prose-sec" key={i}>
          <h2>{s.h}</h2>
          <div className="prose-col">{s.ps.map((t, k) => <p key={k}>{t}</p>)}</div>
        </section>
      ))}
    </>
  );
}
