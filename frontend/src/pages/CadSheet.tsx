import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import {
  type Entity, type Layer, type Pt, type Sheet, type Snap, type SnapSettings,
  SNAP_LABEL, bboxOf, constrain, defaultSnaps, dist, fmtM, gripsOf, hits, insideBox, lengthM, moveEntity,
  segmentsOf, snapPoint, uid, worldSize,
} from "../cad/model";

/* CAD-rummet: ritbordet.
 *
 * Här laddas ingenting upp. Ett blad börjar tomt - ett pappersformat, en skala - och blir en ritning genom att
 * någon ritar den. Ritobjekten ligger i byggets millimeter, så en vägg som är tre meter är tre meter vare sig
 * bladet skrivs ut i 1:50 eller 1:100.
 *
 * Tre saker gör skillnaden mellan en rityta och ett ritbord: objektfångst, låsta vinklar och exakt inmatning.
 * Utan dem möts två linjer nästan, och nästan går inte att mäta. Med dem är en slinga sluten, ett hörn ett
 * hörn, och en sträcka precis 3 200 mm därför att någon skrev 3200 och tryckte Enter.
 *
 * Det ritade mäts av mängdningens mätmotor på servern, aldrig här. Siffran som står medan man drar är en
 * förhandsvisning; den som gäller är serverns, för en meter ska betyda samma sak i båda rummen.
 */

type Tool = "valj" | "linje" | "polylinje" | "ror" | "rektangel" | "cirkel" | "bage" | "text" | "matt";

const TOOLS: { id: Tool; label: string; key: string; hint: string }[] = [
  { id: "valj", label: "Välj", key: "V", hint: "Klicka på ett objekt, eller dra en ruta. Dra i objektet för att flytta det, i en greppunkt för att ändra formen." },
  { id: "linje", label: "Linje", key: "L", hint: "Klicka start och slut. Skriv ett tal för exakt längd, Tab för vinkel." },
  { id: "polylinje", label: "Polylinje", key: "P", hint: "Klicka punkt för punkt. Enter eller dubbelklick avslutar, C sluter slingan." },
  { id: "ror", label: "Rör", key: "R", hint: "Som polylinje, men bär beteckning och dimension - det som mängdas." },
  { id: "rektangel", label: "Rektangel", key: "K", hint: "Två motstående hörn." },
  { id: "cirkel", label: "Cirkel", key: "C", hint: "Centrum, sedan radien." },
  { id: "bage", label: "Båge", key: "B", hint: "Centrum, startpunkt, slutpunkt." },
  { id: "text", label: "Text", key: "T", hint: "Klicka där texten ska stå och skriv den." },
  { id: "matt", label: "Mått", key: "M", hint: "Två punkter; måttet skrivs ut på bladet." },
];

const COLORS = ["#111111", "#c0392b", "#1f6feb", "#0b7285", "#b58900", "#7048e8", "#2f9e44", "#868e96"];
const PAPERS = ["A0", "A1", "A2", "A3", "A4"];
const RATIOS = [20, 25, 50, 100, 200, 500];

type View = { s: number; ox: number; oy: number };   // bildpunkter per millimeter, och var origo ligger

export default function CadSheetPage() {
  const { id } = useParams();
  const sheetId = id!;
  const nav = useNavigate();
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);

  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [layers, setLayers] = useState<Layer[]>([]);
  const [ents, setEnts] = useState<Entity[]>([]);
  const [cur, setCur] = useState("");                     // aktivt lager
  const [tool, setTool] = useState<Tool>("valj");
  const [draft, setDraft] = useState<Pt[]>([]);
  const [sel, setSel] = useState<string[]>([]);
  const [snaps, setSnaps] = useState<SnapSettings>(defaultSnaps);
  const [ortho, setOrtho] = useState(0);                  // 0 av, 90 ortho, 45 polär
  const [view, setView] = useState<View>({ s: 0.02, ox: 40, oy: 40 });
  const [hover, setHover] = useState<Snap | null>(null);
  const [typed, setTyped] = useState("");                 // exakt längd medan man ritar
  const [typedAngle, setTypedAngle] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState<"" | "sparar" | "sparat">("");
  const [designation, setDesignation] = useState("");
  const [dn, setDn] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const past = useRef<Entity[][]>([]);
  const future = useRef<Entity[][]>([]);
  const drag = useRef<{ kind: "pan" | "move" | "grip" | "box"; from: Pt; screen: [number, number];
                        ids?: string[]; grip?: { id: string; i: number }; box?: [Pt, Pt] } | null>(null);
  const dirty = useRef(false);

  // ---------------------------------------------------------------- hämta och spara

  useEffect(() => {
    api.cadSheet(sheetId).then((s: Sheet) => {
      setSheet(s);
      setLayers(s.content.layers);
      setEnts(s.content.entities);
      setCur(s.content.layers[0]?.id ?? "l0");
    }).catch((e) => setErr(e.message));
  }, [sheetId]);

  const push = useCallback((next: Entity[]) => {
    past.current = [...past.current.slice(-80), ents];
    future.current = [];
    setEnts(next);
    dirty.current = true;
  }, [ents]);

  const undo = useCallback(() => {
    const prev = past.current.pop();
    if (!prev) return;
    future.current = [ents, ...future.current.slice(0, 80)];
    setEnts(prev); dirty.current = true; setDraft([]);
  }, [ents]);

  const redo = useCallback(() => {
    const [next, ...rest] = future.current;
    if (!next) return;
    past.current = [...past.current, ents];
    future.current = rest;
    setEnts(next); dirty.current = true; setDraft([]);
  }, [ents]);

  // Autospar: bladet är någons arbete och ska inte kunna gå förlorat för att en flik stängdes. Fördröjningen
  // är till för att ett streck inte ska bli ett anrop - den som ritar drar många streck i följd.
  useEffect(() => {
    if (!sheet || !dirty.current) return;
    const t = setTimeout(async () => {
      dirty.current = false;
      setSaving("sparar");
      try {
        const s = await api.cadSave(sheetId, { content: { version: 1, layers, entities: ents } });
        setSheet(s); setSaving("sparat");
        setTimeout(() => setSaving(""), 1400);
      } catch (e: any) { setErr(e.message); setSaving(""); }
    }, 700);
    return () => clearTimeout(t);
  }, [ents, layers, sheet, sheetId]);

  // ---------------------------------------------------------------- värld och skärm

  const toScreen = useCallback((p: Pt): [number, number] => [p[0] * view.s + view.ox, p[1] * view.s + view.oy], [view]);
  const toWorld = useCallback((x: number, y: number): Pt => [(x - view.ox) / view.s, (y - view.oy) / view.s], [view]);
  const tol = 10 / view.s;                                 // fångstavstånd: tio bildpunkter, i millimeter

  const fit = useCallback(() => {
    const el = wrap.current;
    if (!el || !sheet) return;
    const r = el.getBoundingClientRect();
    const [w, h] = worldSize(sheet);
    const s = Math.min((r.width - 60) / w, (r.height - 60) / h);
    setView({ s, ox: (r.width - w * s) / 2, oy: (r.height - h * s) / 2 });
  }, [sheet]);

  useLayoutEffect(() => { if (sheet) fit(); }, [sheet?.id, fit]);

  // ---------------------------------------------------------------- ritning

  const paint = useCallback(() => {
    const c = canvas.current, el = wrap.current;
    if (!c || !el || !sheet) return;
    const r = el.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (c.width !== Math.round(r.width * dpr) || c.height !== Math.round(r.height * dpr)) {
      c.width = Math.round(r.width * dpr); c.height = Math.round(r.height * dpr);
      c.style.width = `${r.width}px`; c.style.height = `${r.height}px`;
    }
    const g = c.getContext("2d");
    if (!g) return;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, r.width, r.height);

    // pappret
    const [w, h] = worldSize(sheet);
    const o = toScreen([0, 0]), e2 = toScreen([w, h]);
    g.fillStyle = "#ffffff";
    g.fillRect(o[0], o[1], e2[0] - o[0], e2[1] - o[1]);
    g.strokeStyle = "#c9d3dd"; g.lineWidth = 1;
    g.strokeRect(o[0] + 0.5, o[1] + 0.5, e2[0] - o[0], e2[1] - o[1]);

    // rutnätet: grovt när man är utzoomad, fint när man är nära
    if (snaps.grid > 0) {
      let step = snaps.grid;
      while (step * view.s < 8) step *= 5;
      g.save();
      g.beginPath();
      g.rect(o[0], o[1], e2[0] - o[0], e2[1] - o[1]);
      g.clip();
      g.strokeStyle = "#eef2f6"; g.lineWidth = 1;
      for (let x = 0; x <= w; x += step) {
        const sx = Math.round(toScreen([x, 0])[0]) + 0.5;
        g.beginPath(); g.moveTo(sx, o[1]); g.lineTo(sx, e2[1]); g.stroke();
      }
      for (let y = 0; y <= h; y += step) {
        const sy = Math.round(toScreen([0, y])[1]) + 0.5;
        g.beginPath(); g.moveTo(o[0], sy); g.lineTo(e2[0], sy); g.stroke();
      }
      g.restore();
    }

    const byId = new Map(layers.map((l) => [l.id, l]));
    const selected = new Set(sel);
    const drawEnt = (en: Entity, ghost = false) => {
      const l = byId.get(en.layer);
      if (l && !l.visible) return;
      const col = l?.color ?? "#111";
      g.strokeStyle = ghost ? "#1f6feb" : col;
      g.fillStyle = ghost ? "#1f6feb" : col;
      g.lineWidth = Math.max(1, (l?.width ?? 0.35) * (sheet.scale_ratio ?? 50) * view.s);
      g.setLineDash(ghost ? [6, 4] : []);
      if (en.type === "text") {
        const p = toScreen(en.p[0] ?? [0, 0]);
        const px = Math.max(9, (en.h ?? 2.5) * (sheet.scale_ratio ?? 50) * view.s);
        g.font = `${px}px var(--mono, ui-monospace), monospace`;
        g.fillText(en.text ?? "", p[0], p[1]);
      } else {
        g.beginPath();
        for (const [a, b] of segmentsOf(en)) {
          const A = toScreen(a), B = toScreen(b);
          g.moveTo(A[0], A[1]); g.lineTo(B[0], B[1]);
        }
        g.stroke();
        if (en.type === "matt" as any || en.type === "dim") {
          const [a, b] = [en.p[0], en.p[1]];
          if (a && b) {
            const M = toScreen([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]);
            g.font = "11px ui-monospace, monospace";
            g.fillText(fmtM(dist(a, b)), M[0] + 4, M[1] - 4);
          }
        }
      }
      if (selected.has(en.id)) {
        g.setLineDash([]);
        g.strokeStyle = "#1f6feb"; g.lineWidth = 1;
        const [x0, y0, x1, y1] = bboxOf(en);
        const A = toScreen([x0, y0]), B = toScreen([x1, y1]);
        g.strokeRect(A[0] - 3, A[1] - 3, B[0] - A[0] + 6, B[1] - A[1] + 6);
        g.fillStyle = "#1f6feb";
        for (const gp of gripsOf(en)) {
          const P = toScreen(gp);
          g.fillRect(P[0] - 3, P[1] - 3, 6, 6);
        }
      }
      g.setLineDash([]);
    };

    for (const en of ents) drawEnt(en);

    // det som håller på att ritas
    if (draft.length) {
      const pts = hover && tool !== "text" ? [...draft, hover.p] : draft;
      const ghost: Entity = tool === "rektangel" && pts.length >= 2
        ? { id: "_", type: "rect", layer: cur, p: [pts[0], pts[pts.length - 1]] }
        : tool === "cirkel" && pts.length >= 2
          ? { id: "_", type: "circle", layer: cur, p: [pts[0]], r: dist(pts[0], pts[pts.length - 1]) }
          : tool === "bage" && pts.length >= 2
            ? arcFromPoints(pts, cur)
            : { id: "_", type: "polyline", layer: cur, p: pts };
      drawEnt(ghost, true);
      if (pts.length >= 2) {
        const a = pts[pts.length - 2], b = pts[pts.length - 1];
        const B = toScreen(b);
        g.fillStyle = "#0b7285";
        g.font = "12px ui-monospace, monospace";
        const ang = (Math.atan2(b[1] - a[1], b[0] - a[0]) * 180 / Math.PI + 360) % 360;
        g.fillText(`${fmtM(dist(a, b))}  ${ang.toFixed(1)}°`, B[0] + 12, B[1] - 10);
      }
    }

    // markeringsrutan
    if (drag.current?.kind === "box" && drag.current.box) {
      const [a, b] = drag.current.box;
      const A = toScreen(a), B = toScreen(b);
      g.strokeStyle = "#1f6feb"; g.setLineDash([4, 3]); g.lineWidth = 1;
      g.strokeRect(Math.min(A[0], B[0]), Math.min(A[1], B[1]), Math.abs(B[0] - A[0]), Math.abs(B[1] - A[1]));
      g.fillStyle = "rgba(31,111,235,0.07)";
      g.fillRect(Math.min(A[0], B[0]), Math.min(A[1], B[1]), Math.abs(B[0] - A[0]), Math.abs(B[1] - A[1]));
      g.setLineDash([]);
    }

    // fångstmarkören: den som ritar ska se vad hon fick, inte gissa
    if (hover && hover.kind !== "fri") {
      const P = toScreen(hover.p);
      g.strokeStyle = "#e8590c"; g.lineWidth = 1.6;
      g.beginPath();
      if (hover.kind === "andpunkt") g.strokeRect(P[0] - 5, P[1] - 5, 10, 10);
      else if (hover.kind === "mittpunkt") { g.moveTo(P[0] - 6, P[1] + 4); g.lineTo(P[0], P[1] - 6); g.lineTo(P[0] + 6, P[1] + 4); g.closePath(); g.stroke(); }
      else if (hover.kind === "centrum" || hover.kind === "kvadrant") { g.arc(P[0], P[1], 5.5, 0, Math.PI * 2); g.stroke(); }
      else if (hover.kind === "skarning") { g.moveTo(P[0] - 6, P[1] - 6); g.lineTo(P[0] + 6, P[1] + 6); g.moveTo(P[0] + 6, P[1] - 6); g.lineTo(P[0] - 6, P[1] + 6); g.stroke(); }
      else if (hover.kind === "vinkelrat") { g.strokeRect(P[0] - 5, P[1] - 5, 10, 10); g.moveTo(P[0] - 5, P[1] + 5); g.lineTo(P[0] + 5, P[1] + 5); g.stroke(); }
      else { g.arc(P[0], P[1], 3.5, 0, Math.PI * 2); g.stroke(); }
    }
  }, [sheet, layers, ents, sel, draft, hover, tool, cur, view, snaps, toScreen]);

  useEffect(() => { paint(); }, [paint]);
  useEffect(() => {
    const on = () => paint();
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, [paint]);

  // ---------------------------------------------------------------- pekaren

  const snapAt = useCallback((x: number, y: number): Snap => {
    const raw = toWorld(x, y);
    const ref = draft.length ? draft[draft.length - 1] : null;
    const s = snapPoint(raw, ents, layers, snaps, tol, ref);
    if (s.kind === "fri" && ref && ortho) return { p: constrain(ref, raw, ortho), kind: "fri" };
    return s;
  }, [toWorld, draft, ents, layers, snaps, tol, ortho]);

  const onMove = (ev: React.PointerEvent) => {
    const r = canvas.current!.getBoundingClientRect();
    const x = ev.clientX - r.left, y = ev.clientY - r.top;
    const d = drag.current;
    if (d) {
      const w = toWorld(x, y);
      if (d.kind === "pan") {
        setView((v) => ({ ...v, ox: v.ox + (x - d.screen[0]), oy: v.oy + (y - d.screen[1]) }));
        d.screen = [x, y];
      } else if (d.kind === "box") {
        d.box = [d.from, w]; paint();
      } else if (d.kind === "move" && d.ids) {
        const dx = w[0] - d.from[0], dy = w[1] - d.from[1];
        d.from = w;
        setEnts((cur2) => cur2.map((en) => (d.ids!.includes(en.id) ? moveEntity(en, dx, dy) : en)));
        dirty.current = true;
      } else if (d.kind === "grip" && d.grip) {
        const s = snapAt(x, y);
        setEnts((cur2) => cur2.map((en) => {
          if (en.id !== d.grip!.id) return en;
          if (en.type === "circle" || en.type === "arc") return { ...en, p: [s.p] };
          const p = en.p.slice(); p[d.grip!.i] = s.p;
          return { ...en, p };
        }));
        dirty.current = true;
      }
      return;
    }
    setHover(snapAt(x, y));
  };

  const finishDraft = useCallback((pts: Pt[], closed = false) => {
    if (!pts.length) return;
    const base = { id: uid(), layer: cur } as const;
    let en: Entity | null = null;
    if (tool === "linje" && pts.length >= 2) en = { ...base, type: "line", p: pts.slice(0, 2) };
    else if ((tool === "polylinje" || tool === "ror") && pts.length >= 2)
      en = { ...base, type: tool === "ror" ? "pipe" : "polyline", p: pts, closed,
             ...(tool === "ror" ? { designation: designation.trim() || undefined, dn: dn ? Number(dn) : undefined } : {}) };
    else if (tool === "rektangel" && pts.length >= 2) en = { ...base, type: "rect", p: [pts[0], pts[1]] };
    else if (tool === "cirkel" && pts.length >= 2) en = { ...base, type: "circle", p: [pts[0]], r: dist(pts[0], pts[1]) };
    else if (tool === "bage" && pts.length >= 3) en = arcFromPoints(pts, cur);
    else if (tool === "matt" && pts.length >= 2) en = { ...base, type: "dim", p: [pts[0], pts[1]] };
    else if (tool === "text" && pts.length >= 1 && text.trim())
      en = { ...base, type: "text", p: [pts[0]], text: text.trim(), h: 2.5 };
    if (en) push([...ents, en]);
    setDraft([]); setTyped(""); setTypedAngle(null);
  }, [tool, cur, ents, push, designation, dn, text]);

  const onDown = (ev: React.PointerEvent) => {
    const r = canvas.current!.getBoundingClientRect();
    const x = ev.clientX - r.left, y = ev.clientY - r.top;
    (ev.target as Element).setPointerCapture?.(ev.pointerId);
    if (ev.button === 1 || ev.altKey) {                       // panorera
      drag.current = { kind: "pan", from: toWorld(x, y), screen: [x, y] };
      return;
    }
    if (ev.button !== 0) return;
    const s = snapAt(x, y);
    if (tool === "valj") {
      const grip = sel.flatMap((id) => {
        const en = ents.find((e) => e.id === id);
        if (!en) return [];
        return gripsOf(en).map((gp, i) => ({ id, i, d: dist(gp, s.p) }));
      }).sort((a, b) => a.d - b.d)[0];
      if (grip && grip.d <= tol) {
        past.current = [...past.current, ents]; future.current = [];
        drag.current = { kind: "grip", from: s.p, screen: [x, y], grip: { id: grip.id, i: grip.i } };
        return;
      }
      const hit = [...ents].reverse().find((en) => {
        const l = layers.find((k) => k.id === en.layer);
        return l?.visible !== false && !l?.locked && hits(en, s.p, tol);
      });
      if (hit) {
        const next = ev.shiftKey ? (sel.includes(hit.id) ? sel.filter((i) => i !== hit.id) : [...sel, hit.id]) : (sel.includes(hit.id) ? sel : [hit.id]);
        setSel(next);
        past.current = [...past.current, ents]; future.current = [];
        drag.current = { kind: "move", from: s.p, screen: [x, y], ids: next };
      } else {
        if (!ev.shiftKey) setSel([]);
        drag.current = { kind: "box", from: s.p, screen: [x, y], box: [s.p, s.p] };
      }
      return;
    }
    // rita
    const pts = [...draft, s.p];
    if (tool === "linje" && pts.length === 2) return finishDraft(pts);
    if (tool === "rektangel" && pts.length === 2) return finishDraft(pts);
    if (tool === "cirkel" && pts.length === 2) return finishDraft(pts);
    if (tool === "bage" && pts.length === 3) return finishDraft(pts);
    if (tool === "matt" && pts.length === 2) return finishDraft(pts);
    if (tool === "text") return finishDraft(pts);
    setDraft(pts);
  };

  const onUp = () => {
    const d = drag.current;
    drag.current = null;
    if (d?.kind === "box" && d.box) {
      const [a, b] = d.box;
      const box: [number, number, number, number] = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
      const inside = ents.filter((en) => {
        const l = layers.find((k) => k.id === en.layer);
        return l?.visible !== false && !l?.locked && insideBox(en, box);
      }).map((en) => en.id);
      if (inside.length) setSel((s) => Array.from(new Set([...s, ...inside])));
      paint();
    }
    if (d?.kind === "move" || d?.kind === "grip") dirty.current = true;
  };

  const onDouble = () => { if (draft.length >= 2) finishDraft(draft); };

  const onWheel = (ev: React.WheelEvent) => {
    const r = canvas.current!.getBoundingClientRect();
    const x = ev.clientX - r.left, y = ev.clientY - r.top;
    const k = Math.exp(-(ev.deltaMode === 1 ? ev.deltaY * 16 : ev.deltaY) * 0.0016);
    setView((v) => {
      const s = Math.min(4, Math.max(0.0008, v.s * k));
      return { s, ox: x - (x - v.ox) * (s / v.s), oy: y - (y - v.oy) * (s / v.s) };
    });
  };

  // ---------------------------------------------------------------- tangenter

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const t = ev.target as HTMLElement;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      const k = ev.key;
      if ((ev.ctrlKey || ev.metaKey) && k.toLowerCase() === "z") { ev.preventDefault(); if (ev.shiftKey) redo(); else undo(); return; }
      if ((ev.ctrlKey || ev.metaKey) && k.toLowerCase() === "y") { ev.preventDefault(); redo(); return; }
      if (k === "Escape") { setDraft([]); setTyped(""); setTypedAngle(null); setSel([]); return; }
      if (k === "Delete" || k === "Backspace") {
        if (sel.length) { ev.preventDefault(); push(ents.filter((e) => !sel.includes(e.id))); setSel([]); }
        return;
      }
      if (k === "Enter") {
        if (typed && draft.length) { ev.preventDefault(); applyTyped(); return; }
        if (draft.length >= 2) { ev.preventDefault(); finishDraft(draft); }
        return;
      }
      if (k === "Tab" && draft.length) { ev.preventDefault(); setTypedAngle((a) => (a === null ? "" : a)); return; }
      if (/^[0-9.,]$/.test(k) && (draft.length || tool !== "valj")) {
        if (typedAngle !== null) setTypedAngle((a) => (a ?? "") + k.replace(",", "."));
        else setTyped((v) => v + k.replace(",", "."));
        return;
      }
      if (k === "Backspace") { setTyped((v) => v.slice(0, -1)); return; }
      if (k === "F8") { ev.preventDefault(); setOrtho((o) => (o === 90 ? 0 : 90)); return; }
      if (k === "F3") { ev.preventDefault(); setSnaps((s) => ({ ...s, on: !s.on })); return; }
      if (k.toLowerCase() === "c" && draft.length >= 3 && (tool === "polylinje" || tool === "ror")) {
        ev.preventDefault(); finishDraft(draft, true); return;
      }
      const hit = TOOLS.find((x) => x.key.toLowerCase() === k.toLowerCase());
      if (hit && !ev.ctrlKey && !ev.metaKey) { setTool(hit.id); setDraft([]); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo, sel, ents, push, draft, typed, typedAngle, tool, finishDraft]);

  /** Exakt inmatning: ett tal är en längd i millimeter från förra punkten, Tab lägger till en vinkel. */
  const applyTyped = () => {
    const from = draft[draft.length - 1];
    if (!from) return;
    const len = parseFloat(typed);
    if (!isFinite(len) || len <= 0) return;
    const base = hover?.p ?? from;
    let ang = typedAngle !== null && typedAngle !== "" ? parseFloat(typedAngle) * Math.PI / 180
      : Math.atan2(base[1] - from[1], base[0] - from[0]);
    if (!isFinite(ang)) ang = 0;
    const p: Pt = [from[0] + len * Math.cos(ang), from[1] + len * Math.sin(ang)];
    const pts = [...draft, p];
    setTyped(""); setTypedAngle(null);
    if (tool === "linje" || tool === "rektangel" || tool === "cirkel" || tool === "matt") finishDraft(pts);
    else setDraft(pts);
  };

  // ---------------------------------------------------------------- lager och egenskaper

  const addLayer = () => {
    const l: Layer = { id: uid(), name: `Lager ${layers.length + 1}`, color: COLORS[layers.length % COLORS.length],
                       visible: true, locked: false, width: 0.35 };
    setLayers([...layers, l]); setCur(l.id); dirty.current = true;
  };
  const patchLayer = (id: string, ch: Partial<Layer>) => {
    setLayers(layers.map((l) => (l.id === id ? { ...l, ...ch } : l))); dirty.current = true;
  };
  const dropLayer = (id: string) => {
    if (layers.length < 2) return;
    push(ents.filter((e) => e.layer !== id));
    const rest = layers.filter((l) => l.id !== id);
    setLayers(rest); if (cur === id) setCur(rest[0].id);
  };

  const selEnts = ents.filter((e) => sel.includes(e.id));
  const patchSel = (ch: Partial<Entity>) => push(ents.map((e) => (sel.includes(e.id) ? { ...e, ...ch } : e)));

  const setPaper = async (ch: { paper?: string; scale_ratio?: number }) => {
    try {
      const s = await api.cadSave(sheetId, ch);
      setSheet(s); setTimeout(fit, 0);
    } catch (e: any) { setErr(e.message); }
  };

  /** Sparat innan något hämtas från servern: utskriften ska visa det som står på skärmen, inte det som stod. */
  const save = async () => {
    dirty.current = false;
    const s = await api.cadSave(sheetId, { content: { version: 1, layers, entities: ents } });
    setSheet(s);
    return s;
  };

  /** En fil bakom inloggning öppnas genom att hämtas med sitt bevis och visas ur minnet. */
  const open = async (url: string, download?: string) => {
    try {
      const b = await api.fetchBlob(url);
      const u = URL.createObjectURL(b);
      if (download) {
        const a = document.createElement("a");
        a.href = u; a.download = download; a.click();
      } else {
        window.open(u, "_blank");
      }
      setTimeout(() => URL.revokeObjectURL(u), 60000);
    } catch (e: any) { setErr(e.message); }
  };

  const print = async () => {
    setBusy(true); setErr("");
    try {
      await save();
      const out = await api.cadPrint(sheetId);
      nav(`/mangda/${out.drawing_id}`);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const total = useMemo(() => ents.reduce((s, e) => s + lengthM(e), 0), [ents]);
  const hint = TOOLS.find((t) => t.id === tool)?.hint ?? "";

  if (!sheet) return <main className="wrap"><p className="muted">{err || "Öppnar bladet…"}</p></main>;

  return (
    <main className="wrap cad-page">
      <div className="row between">
        <div>
          <h1 style={{ marginBottom: 2 }}>{sheet.name}</h1>
          <p className="muted small" style={{ margin: 0 }}>
            {sheet.paper} · 1:{sheet.scale_ratio} · {ents.length} objekt · {total.toFixed(2)} m ritat
            {saving && <span className="badge small" style={{ marginLeft: 8 }}>{saving === "sparar" ? "sparar…" : "sparat"}</span>}
          </p>
        </div>
        <div className="row" style={{ gap: 6 }}>
          <Link className="secondary small" to="/cad">Alla blad</Link>
          <button className="secondary small" onClick={() => save().then(() => open(api.cadPdfUrl(sheetId)))}>PDF</button>
          <button className="secondary small" onClick={() => save().then(() => open(api.cadDxfUrl(sheetId), `${sheet.name}.dxf`))}>DXF</button>
          <button className="small" onClick={print} disabled={busy}>{busy ? "Trycker…" : "Tryck och mängda"}</button>
        </div>
      </div>

      <div className="cad-grid">
        <div className="cad-board">
          <div className="cad-toolbar">
            {TOOLS.map((t) => (
              <button key={t.id} className={tool === t.id ? "small" : "secondary small"}
                      title={`${t.label} (${t.key})`}
                      onClick={() => { setTool(t.id); setDraft([]); setSel([]); }}>{t.label}</button>
            ))}
            <span className="cad-sep" />
            <button className={ortho === 90 ? "small" : "secondary small"} title="Lås till 90° (F8)"
                    onClick={() => setOrtho(ortho === 90 ? 0 : 90)}>Ortho</button>
            <button className={ortho === 45 ? "small" : "secondary small"} title="Lås till 45°"
                    onClick={() => setOrtho(ortho === 45 ? 0 : 45)}>45°</button>
            <button className={snaps.on ? "small" : "secondary small"} title="Objektfångst (F3)"
                    onClick={() => setSnaps({ ...snaps, on: !snaps.on })}>Fångst</button>
            <span className="cad-sep" />
            <button className="ghost small" onClick={undo} title="Ångra (Ctrl+Z)">Ångra</button>
            <button className="ghost small" onClick={redo} title="Gör om (Ctrl+Shift+Z)">Gör om</button>
            <button className="ghost small" onClick={fit}>Passa in</button>
          </div>
          <div className="cad-canvas" ref={wrap}>
            <canvas ref={canvas}
                    onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp}
                    onDoubleClick={onDouble} onWheel={onWheel}
                    onContextMenu={(e) => { e.preventDefault(); setDraft([]); }} />
          </div>
          <div className="cad-status">
            <span>{hover ? `${(hover.p[0] / 1000).toFixed(3)} , ${(hover.p[1] / 1000).toFixed(3)} m` : "–"}</span>
            <span className="muted">{hover && hover.kind !== "fri" ? SNAP_LABEL[hover.kind] : "fri"}</span>
            {draft.length > 0 && <span className="badge small">{draft.length} punkter</span>}
            {typed && <span className="badge small">längd {typed} mm{typedAngle !== null ? ` · vinkel ${typedAngle || "?"}°` : ""} · Enter</span>}
            <span className="muted small cad-hint">{hint}</span>
          </div>
        </div>

        <aside className="cad-side">
          <div className="card">
            <h3>Bladet</h3>
            <div className="row" style={{ gap: 8 }}>
              <label className="small">Format
                <select value={sheet.paper} onChange={(e) => setPaper({ paper: e.target.value })}>
                  {PAPERS.map((p) => <option key={p}>{p}</option>)}
                </select>
              </label>
              <label className="small">Skala 1:
                <select value={sheet.scale_ratio} onChange={(e) => setPaper({ scale_ratio: Number(e.target.value) })}>
                  {RATIOS.map((r) => <option key={r}>{r}</option>)}
                </select>
              </label>
            </div>
            <p className="muted small" style={{ marginBottom: 0 }}>
              Ritobjekten ligger i byggets millimeter. Byter du skala ändras pappret, inte väggarna.
            </p>
          </div>

          <div className="card">
            <div className="row between"><h3 style={{ margin: 0 }}>Lager</h3><button className="ghost small" onClick={addLayer}>Nytt</button></div>
            {layers.map((l) => (
              <div key={l.id} className={`cad-layer${cur === l.id ? " on" : ""}`}>
                <button className="ghost small pick" title="Rita på det här lagret" onClick={() => setCur(l.id)}>{cur === l.id ? "●" : "○"}</button>
                <input value={l.name} onChange={(e) => patchLayer(l.id, { name: e.target.value })} />
                <input type="color" value={l.color} onChange={(e) => patchLayer(l.id, { color: e.target.value })} />
                <button className="ghost small" title={l.visible ? "Dölj" : "Visa"} onClick={() => patchLayer(l.id, { visible: !l.visible })}>{l.visible ? "👁" : "–"}</button>
                <button className="ghost small" title={l.locked ? "Lås upp" : "Lås"} onClick={() => patchLayer(l.id, { locked: !l.locked })}>{l.locked ? "🔒" : "🔓"}</button>
                <button className="ghost small" title="Ta bort lagret och det som ritats på det" onClick={() => dropLayer(l.id)}>×</button>
              </div>
            ))}
          </div>

          {(tool === "ror" || selEnts.some((e) => e.type === "pipe")) && (
            <div className="card">
              <h3>Röret</h3>
              <div className="row" style={{ gap: 8 }}>
                <label className="small">Beteckning
                  <input value={designation} placeholder="VS21-S13-22" onChange={(e) => setDesignation(e.target.value)} />
                </label>
                <label className="small">DN
                  <input value={dn} placeholder="22" style={{ width: 70 }} onChange={(e) => setDn(e.target.value)} />
                </label>
              </div>
              {selEnts.some((e) => e.type === "pipe") && (
                <button className="secondary small" style={{ marginTop: 8 }}
                        onClick={() => patchSel({ designation: designation.trim() || undefined, dn: dn ? Number(dn) : undefined })}>
                  Sätt på markerade
                </button>
              )}
            </div>
          )}

          {tool === "text" && (
            <div className="card">
              <h3>Texten</h3>
              <input value={text} placeholder="Skriv texten…" onChange={(e) => setText(e.target.value)} style={{ width: "100%" }} />
              <p className="muted small" style={{ marginBottom: 0 }}>Klicka sedan på bladet där den ska stå.</p>
            </div>
          )}

          <div className="card">
            <h3>Fångst</h3>
            <div className="cad-snaps">
              {(Object.keys(snaps.kinds) as (keyof typeof snaps.kinds)[]).map((k) => (
                <label key={k} className="check small">
                  <input type="checkbox" checked={snaps.kinds[k]}
                         onChange={(e) => setSnaps({ ...snaps, kinds: { ...snaps.kinds, [k]: e.target.checked } })} />
                  {SNAP_LABEL[k]}
                </label>
              ))}
            </div>
            <label className="small" style={{ display: "block", marginTop: 8 }}>Rutnät (mm)
              <input value={snaps.grid} style={{ width: 90 }}
                     onChange={(e) => setSnaps({ ...snaps, grid: Math.max(0, Number(e.target.value) || 0) })} />
            </label>
          </div>

          {selEnts.length > 0 && (
            <div className="card">
              <h3>Markerat ({selEnts.length})</h3>
              <div className="tablewrap">
                <table className="qty">
                  <tbody>
                    {selEnts.slice(0, 8).map((e) => (
                      <tr key={e.id}>
                        <td>{e.type}</td>
                        <td className="lf-mono">{e.designation ?? "–"}</td>
                        <td className="num">{e.type === "text" ? "" : `${lengthM(e).toFixed(3)} m`}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="row" style={{ gap: 6, marginTop: 8 }}>
                <label className="small">Lager
                  <select value={selEnts[0].layer} onChange={(e) => patchSel({ layer: e.target.value })}>
                    {layers.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                  </select>
                </label>
                <button className="ghost small" onClick={() => { push(ents.filter((e) => !sel.includes(e.id))); setSel([]); }}>Ta bort</button>
                <button className="ghost small" onClick={() => {
                  const copies = selEnts.map((e) => ({ ...e, id: uid(), p: e.p.map(([x, y]) => [x + 500, y + 500] as Pt) }));
                  push([...ents, ...copies]); setSel(copies.map((c) => c.id));
                }}>Kopiera</button>
              </div>
            </div>
          )}

          {sheet.summary && sheet.summary.rows.length > 0 && (
            <div className="card">
              <h3>Bladets mängd</h3>
              <p className="muted small" style={{ marginTop: 0 }}>Räknad på servern av samma mätmotor som mängdningen.</p>
              <div className="tablewrap">
                <table className="qty">
                  <thead><tr><th>Beteckning</th><th className="num">Antal</th><th className="num">Meter</th></tr></thead>
                  <tbody>
                    {sheet.summary.rows.map((r) => (
                      <tr key={r.key}><td className="lf-mono">{r.key}</td><td className="num">{r.n}</td><td className="num">{r.m.toFixed(2)}</td></tr>
                    ))}
                  </tbody>
                  <tfoot><tr><th>Summa</th><th className="num">{sheet.summary.entities}</th><th className="num">{sheet.summary.total_m.toFixed(2)}</th></tr></tfoot>
                </table>
              </div>
            </div>
          )}
          {err && <p className="error">{err}</p>}
        </aside>
      </div>
    </main>
  );
}

/** Bågen genom centrum, start och slut: radien är avståndet till startpunkten, vinklarna är de två punkternas. */
function arcFromPoints(pts: Pt[], layer: string): Entity {
  const [c, a, b] = pts;
  const r = dist(c, a);
  const deg = (p: Pt) => (Math.atan2(p[1] - c[1], p[0] - c[0]) * 180) / Math.PI;
  const a0 = deg(a), a1 = b ? deg(b) : a0 + 90;
  return { id: uid(), type: "arc", layer, p: [c], r, a0, a1: a1 < a0 ? a1 + 360 : a1 };
}
