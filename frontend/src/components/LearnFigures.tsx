/* Levande infografik för akademin.
 *
 * Varje figur visar en sak som händer, inte en bild av den: vattnet rinner, hänvisningslinjen ritar sig själv,
 * pappret krymper och skalan går fel. Allt är SVG med CSS-animering, så det väger ingenting och stannar av sig
 * själv för den som bett om mindre rörelse.
 */

function Ttl({ x, y, t }: { x: number; y: number; t: string }) {
  return <text x={x} y={y} className="lfa-cap">{t}</text>;
}

/* ---------- 01 systemen: tryck mot självfall ---------- */
function Flow() {
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="Tryckledningar går åt alla håll, självfall måste luta">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      <Ttl x={30} y={40} t="TRYCK — GÅR ÅT ALLA HÅLL" />
      <path className="lfa-pipe kv" d="M40 70 H220 V120 H400 V70 H600" />
      <path className="lfa-pipe vv" d="M40 96 H196 V146 H400 V96 H600" />
      <Ttl x={30} y={196} t="SJÄLVFALL — MÅSTE LUTA HELA VÄGEN" />
      <path className="lfa-pipe s" d="M40 214 L600 262" />
      <circle className="lfa-drop" r="6" cx="0" cy="0">
        <animateMotion dur="3.4s" repeatCount="indefinite" path="M40 214 L600 262" />
      </circle>
      <g className="lfa-fall">
        <path d="M40 214 H600" />
        <path d="M600 214 V262" />
        <text x="606" y="244" className="lfa-cap">fall</text>
      </g>
      <g className="lfa-key">
        <circle cx="46" cy="278" r="4" className="dot kv" /><text x="58" y="282" className="lfa-cap">KV</text>
        <circle cx="106" cy="278" r="4" className="dot vv" /><text x="118" y="282" className="lfa-cap">VV</text>
        <circle cx="166" cy="278" r="4" className="dot s" /><text x="178" y="282" className="lfa-cap">SPILL</text>
      </g>
    </svg>
  );
}

/* ---------- 02 KV, VV, VVC i bunt ---------- */
function Bundle() {
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="Kallvatten, varmvatten och cirkulation dras i bunt">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      <path className="lfa-pipe kv" d="M60 96 H520" />
      <path className="lfa-pipe vv" d="M60 140 H520" />
      <path className="lfa-pipe vvc" d="M520 184 H60" />
      <path className="lfa-pipe vvc" d="M520 140 V184" />
      <g className="lfa-lbl">
        <text x="60" y="84" className="lfa-cap">KV — fram till tappstället</text>
        <text x="60" y="128" className="lfa-cap">VV — fram till tappstället</text>
        <text x="60" y="206" className="lfa-cap">VVC — tillbaka, så varmvattnet inte kallnar</text>
      </g>
      <g className="lfa-tap">
        <circle cx="520" cy="96" r="6" /><circle cx="520" cy="140" r="6" />
      </g>
      <g className="lfa-zoom">
        <rect x="250" y="72" width="120" height="132" rx="8" />
        <text x="256" y="234" className="lfa-cap">i schaktet ligger de några cm isär — bara etiketten skiljer dem åt</text>
      </g>
    </svg>
  );
}

/* ---------- 03 stammen: vatten ned, luft upp ---------- */
function Stack() {
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="Vatten faller i stammen medan luft går upp genom den">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      <g className="lfa-house"><path d="M180 40 H460 V270 H180 Z M180 110 H460 M180 180 H460" /></g>
      <path className="lfa-pipe s" d="M320 40 V270" />
      <path className="lfa-pipe s" d="M240 96 H320" />
      <path className="lfa-pipe s" d="M240 166 H320" />
      <circle className="lfa-drop" r="6" cx="0" cy="0">
        <animateMotion dur="2.2s" repeatCount="indefinite" path="M320 60 V264" />
      </circle>
      <g className="lfa-air">
        <path d="M356 260 V56" />
        <path d="M350 66 L356 52 L362 66" />
      </g>
      <Ttl x={372} y={70} t="LUFT UPP — ANNARS SUGS VATTENLÅSEN TOMMA" />
      <Ttl x={188} y={288} t="VATTEN NED MED SJÄLVFALL" />
    </svg>
  );
}

/* ---------- 04 beteckningen sätts ihop ---------- */
function Code() {
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="Beteckningen KV1-X31-16 byggs ihop av sina tre delar">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      <g className="lfa-code">
        <g className="p1"><text x="180" y="120" className="lfa-big">KV1</text></g>
        <g className="p2"><text x="292" y="120" className="lfa-big">X31</text></g>
        <g className="p3"><text x="404" y="120" className="lfa-big">16</text></g>
        <g className="dash"><text x="268" y="120" className="lfa-big dim">-</text><text x="380" y="120" className="lfa-big dim">-</text></g>
      </g>
      <g className="lfa-code-cap">
        <g className="p1"><path d="M212 140 V186" /><text x="222" y="190" className="lfa-cap">SYSTEM · tappkallvatten 1</text></g>
        <g className="p2"><path d="M324 140 V222" /><text x="334" y="226" className="lfa-cap">MATERIAL · står i bladets lista</text></g>
        <g className="p3"><path d="M424 140 V258" /><text x="434" y="262" className="lfa-cap">DIMENSION · 16 mm</text></g>
      </g>
    </svg>
  );
}

/* ---------- 05 DN mot dy ---------- */
function DnDy() {
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="DN mäter ungefär insidan, dy mäter utsidan">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      <g transform="translate(150 150)">
        <circle r="74" className="lfa-wall" /><circle r="58" className="lfa-bore" />
        <g className="lfa-meas dy"><path d="M-74 104 H74" /><path d="M-74 96 V112" /><path d="M74 96 V112" /></g>
        <text x="0" y="136" className="lfa-cap mid">dy — ytterdiameter</text>
        <text x="0" y="-96" className="lfa-cap mid">plast och koppar</text>
      </g>
      <g transform="translate(450 150)">
        <circle r="74" className="lfa-wall" /><circle r="58" className="lfa-bore" />
        <g className="lfa-meas dn"><path d="M-58 104 H58" /><path d="M-58 96 V112" /><path d="M58 96 V112" /></g>
        <text x="0" y="136" className="lfa-cap mid">DN — ungefär insidan</text>
        <text x="0" y="-96" className="lfa-cap mid">stål och gjutjärn</text>
      </g>
      <text x="320" y="284" className="lfa-cap mid">samma tal, två olika mått — fel material i kalkylen, inte fel längd</text>
    </svg>
  );
}

/* ---------- 06 bladets delar tänds i tur och ordning ---------- */
function Sheet() {
  const parts = [
    { d: "M40 40 H600 V250 H40 Z", t: "PLANEN", x: 48, y: 34 },
    { d: "M440 190 H596 V246 H440 Z", t: "STÄMPELN", x: 448, y: 184 },
    { d: "M46 46 H150 V150 H46 Z", t: "FÖRKLARINGSLISTAN", x: 54, y: 168 },
    { d: "M200 214 H330 V244 H200 Z", t: "SKALSTOCKEN", x: 208, y: 262 },
  ];
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="Ritningens delar, en i taget">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      <g className="lfa-house"><path d="M40 40 H600 V250 H40 Z M300 40 V250 M40 150 H300" /></g>
      {parts.map((p, i) => (
        <g key={p.t} className="lfa-part" style={{ animationDelay: `${i * 1.5}s` }}>
          <path d={p.d} />
          <text x={p.x} y={p.y} className="lfa-cap">{p.t}</text>
        </g>
      ))}
    </svg>
  );
}

/* ---------- 07 skalan: pappret krymper, den utskrivna skalan blir fel ---------- */
function Scale() {
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="Skalstocken följer pappret, den utskrivna skalan gör det inte">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      {/* the sheet, printed smaller than it was drawn: the bar shrinks with the paper, the words do not */}
      <g className="lfa-shrink">
        <rect className="lfa-sheet" x="40" y="34" width="290" height="150" rx="4" />
        <text x="56" y="66" className="lfa-mono">SKALA 1:50</text>
        <g className="lfa-bar">
          <path d="M56 110 H300" />
          {[0, 48.8, 97.6, 146.4, 195.2, 244].map((x, i) => <path key={i} d={`M${56 + x} 98 V122`} />)}
        </g>
        <text x="56" y="146" className="lfa-cap">0</text>
        <text x="272" y="146" className="lfa-cap">15 m</text>
      </g>
      <g className="lfa-arrow">
        <path d="M348 110 H392" /><path d="M382 102 L392 110 L382 118" />
      </g>
      <g className="lfa-said">
        <text x="410" y="70" className="lfa-cap">SÄGER 1:50</text>
        <text x="410" y="96" className="lfa-cap warn">men pappret är halverat</text>
        <text x="410" y="128" className="lfa-cap">SKALSTOCKEN</text>
        <text x="410" y="154" className="lfa-cap ok">krympte med — den gäller</text>
      </g>
      <text x="40" y="236" className="lfa-cap">Ett A1-blad utskrivet på A3: allt är hälften så stort.</text>
      <text x="40" y="262" className="lfa-cap">Den utskrivna skalan står kvar och blir fel.</text>
      <text x="40" y="288" className="lfa-cap ok">Skalstocken ligger på samma papper och kan inte ljuga.</text>
    </svg>
  );
}

/* ---------- 08 stigaren: en ring i planen är en våning i sektionen ---------- */
function Riser() {
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="En ring i planen är en ledning som går mellan våningar">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      <Ttl x={40} y={38} t="PLAN" />
      <g className="lfa-house"><path d="M40 50 H280 V250 H40 Z" /></g>
      <path className="lfa-pipe s" d="M70 200 H160 V130" />
      <g className="lfa-ring"><circle cx="160" cy="122" r="11" /></g>
      <Ttl x={176} y={126} t="STIGARE" />
      <Ttl x={370} y={38} t="SEKTION" />
      <g className="lfa-house"><path d="M370 50 H600 V250 H370 Z M370 116 H600 M370 182 H600" /></g>
      <path className="lfa-pipe s riser" d="M470 246 V60" />
      <g className="lfa-floor"><path d="M470 246 H600" /><path d="M470 182 H600" /><path d="M470 116 H600" /></g>
      <text x="500" y="278" className="lfa-cap">höjden står inte på ritningen — antalet räknas, höjden matas in</text>
    </svg>
  );
}

/* ---------- 09 lagren separerar ---------- */
function Layers() {
  const L = [
    { t: "BYGGNAD", d: "M0 0 H240 V150 H0 Z M120 0 V150 M0 80 H120", c: "b" },
    { t: "SPILLVATTEN", d: "M20 120 H140 V40 H220", c: "s" },
    { t: "TAPPVATTEN", d: "M20 60 H100 V130 H220", c: "kv" },
    { t: "TEXT OCH LEDARLINJER", d: "M40 24 H130 M130 30 L100 60", c: "t" },
  ];
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="Varje sorts geometri på sitt eget lager">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      <g className="lfa-deck">
        {L.map((l, i) => (
          <g key={l.t} className={`lfa-layer ${l.c}`} style={{ animationDelay: `${i * 0.25}s` }}
            transform={`translate(${170 + i * 34} ${34 + i * 56})`}>
            <path className="plate" d="M0 0 H240 V150 H0 Z" />
            <path className="art" d={l.d} />
            <text x="252" y="86" className="lfa-cap">{l.t}</text>
          </g>
        ))}
      </g>
    </svg>
  );
}

/* ---------- 10 hänvisningslinjen ritar sig själv, och missar ---------- */
function Leader() {
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="En hänvisningslinje som träffar röret, och en som inte gör det">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      <g>
        <path className="lfa-pipe kv" d="M60 120 H300" />
        <rect className="lfa-tag" x="60" y="52" width="132" height="26" rx="4" />
        <text x="70" y="70" className="lfa-mono sm">KV1-X31-16</text>
        <path className="lfa-lead draw" d="M192 66 L214 120" />
        <circle className="lfa-hit" cx="214" cy="120" r="5" />
        <text x="60" y="160" className="lfa-cap ok">slutar PÅ röret — sträckan får sitt namn</text>
      </g>
      <g transform="translate(0 118)">
        <path className="lfa-pipe kv" d="M60 120 H300" />
        <rect className="lfa-tag" x="60" y="52" width="132" height="26" rx="4" />
        <text x="70" y="70" className="lfa-mono sm">KV1-X31-16</text>
        <path className="lfa-lead draw miss" d="M192 66 L212 102" />
        <circle className="lfa-miss" cx="212" cy="102" r="5" />
        <text x="60" y="160" className="lfa-cap warn">slutar i luften — sträckan blir onämnd</text>
      </g>
      <g className="lfa-split-rule"><path d="M330 40 V270" /></g>
      <text x="352" y="150" className="lfa-cap">
        För ögat är skillnaden några millimeter.
      </text>
      <text x="352" y="176" className="lfa-cap">
        För varje mängdning är den skillnaden mellan
      </text>
      <text x="352" y="202" className="lfa-cap">
        en sträcka som räknas och en som inte gör det.
      </text>
    </svg>
  );
}

/* ---------- 11 mängden räknas fram ---------- */
function Takeoff() {
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="En sträcka spåras och metrarna räknas fram">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      <g className="lfa-house"><path d="M40 40 H400 V260 H40 Z M220 40 V260" /></g>
      <path className="lfa-pipe kv ghost" d="M70 220 H180 V90 H370" />
      <path className="lfa-pipe kv trace" d="M70 220 H180 V90 H370" />
      <g className="lfa-tally">
        <rect x="430" y="70" width="176" height="64" rx="10" />
        <text x="446" y="102" className="lfa-num">17,10 m</text>
        <text x="446" y="122" className="lfa-cap">KV1-X31-16</text>
      </g>
      <g className="lfa-tally two">
        <rect x="430" y="150" width="176" height="64" rx="10" />
        <text x="446" y="182" className="lfa-num">2 st</text>
        <text x="446" y="202" className="lfa-cap">stigare — höjd matas in</text>
      </g>
    </svg>
  );
}

/* ---------- 12 egenkontrollen ---------- */
function Checks() {
  const rows: [string, number, boolean][] = [
    ["täckning · hur mycket av det ritade fick ett namn", 0.86, true],
    ["rimlighet · meter mot husets storlek", 0.72, true],
    ["systembalans · KV mot VV", 0.34, false],
    ["ändar · varje sträcka slutar i något", 0.94, true],
  ];
  return (
    <svg viewBox="0 0 640 300" role="img" aria-label="Fyra egenkontroller som fångar nästan alla fel">
      <rect className="lfa-paper" x="6" y="6" width="628" height="288" rx="10" />
      {rows.map(([t, v, ok], i) => (
        <g key={t} transform={`translate(40 ${58 + i * 58})`}>
          <text x="0" y="-8" className="lfa-cap">{t}</text>
          <rect className="lfa-track" x="0" y="0" width="560" height="10" rx="5" />
          <rect className={`lfa-fill${ok ? "" : " bad"}`} x="0" y="0" height="10" rx="5"
            style={{ ["--w" as any]: `${v * 560}px`, animationDelay: `${i * 0.25}s` }} />
        </g>
      ))}
      <text x="40" y="288" className="lfa-cap warn">en balans som halkar är nästan alltid sträckor utan namn</text>
    </svg>
  );
}

const FIGS: Record<string, () => JSX.Element> = {
  flow: Flow, bundle: Bundle, stack: Stack, code: Code, dndy: DnDy, sheet: Sheet,
  scale: Scale, riser: Riser, layers: Layers, leader: Leader, takeoff: Takeoff, checks: Checks,
};

export default function LearnFigure({ id }: { id: string }) {
  const F = FIGS[id];
  return F ? <div className="lfa"><F /></div> : null;
}

export const FIGURE_IDS = Object.keys(FIGS);
