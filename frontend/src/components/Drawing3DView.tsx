import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { buildModel, type BuildingModel, type ModelPipe, type ModelWall } from "../three/model";
import Drawing3DControls, { type ViewName } from "./Drawing3DControls";

/* Ritningen som byggnad.
 *
 * Egen modul, egen renderare, egna komponenter: 3D:n vet ingenting om läsningen mer än den modell den får, och
 * läsningen vet ingenting om 3D:n. Det som visas är ritningens egen geometri - rören med sin verkliga grovlek
 * och sitt namn, väggarna som enkla skivor där arkitektens bläck går - och mängderna kommer från samma tabell
 * som resten av systemet räknar ur. Ingenting mäts här.
 *
 * Övergången är fysisk: planen ligger kvar, väggarna reser sig ur den, kameran tiltar från rakt ovanifrån till
 * perspektiv. Den som slagit på reducerad rörelse får samma modell utan resan dit.
 *
 * Fyra saker gör modellen läsbar i stället för bara vacker:
 *
 *   * **Vyn ovanifrån går att vrida.** Rakt ovanifrån är kamerans upp-riktning parallell med blicken, och en
 *     kamera i det läget vet inte längre vad som är upp. Upp-vektorn vänds därför mjukt ned i planet ju
 *     brantare vyn blir och följer vridningen, så planen går att snurra hela varvet utan att bilden slår runt.
 *   * **Beteckningarna står i rummet.** Varje beteckning läsningen namngav får en skylt vid sitt rör, ritad
 *     ovanpå allt annat och alltid vänd mot betraktaren. Utan dem är modellen en samling färgade rör.
 *   * **Väggarna går att se igenom.** En installation ligger inne i huset; en modell som bara visar fasaden
 *     döljer det man kom för att se.
 *   * **Man kan gå in i den.** Gå-läget sätter kameran i ögonhöjd och låter tangenterna föra den genom
 *     byggnaden. Det finns ingen krockberäkning - man går rakt genom en vägg - för en plan ritad i ett plan
 *     har inga dörrar att hitta, och att fastna i en vägg vore sämre än att gå igenom den.
 */

type Props = {
  result: any;
  title?: string;
  onClose: () => void;
};

const REDUCED = () => typeof window !== "undefined"
  && window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

const EYE = 1.65;            // ögonhöjd i gå-läget, meter
const WALK = 2.8;            // meter i sekunden
const RUN = 7.0;
const MAX_LABELS = 260;      // skyltar ritas billigt men inte gratis

/** En skylt med beteckningen, ritad en gång som bild och sedan alltid vänd mot betraktaren. */
function labelSprite(text: string, color: string): THREE.Sprite {
  const font = 46, pad = 16, dot = 20;
  const probe = document.createElement("canvas").getContext("2d")!;
  probe.font = `600 ${font}px ui-monospace, SFMono-Regular, Menlo, monospace`;
  const tw = Math.ceil(probe.measureText(text).width);
  const c = document.createElement("canvas");
  c.width = tw + pad * 3 + dot;
  c.height = font + pad * 2;
  const g = c.getContext("2d")!;
  const r = c.height / 2;
  g.fillStyle = "rgba(10, 14, 19, 0.86)";
  g.beginPath();
  g.moveTo(r, 0); g.lineTo(c.width - r, 0); g.arc(c.width - r, r, r, -Math.PI / 2, Math.PI / 2);
  g.lineTo(r, c.height); g.arc(r, r, r, Math.PI / 2, -Math.PI / 2); g.closePath(); g.fill();
  g.fillStyle = color;
  g.beginPath(); g.arc(pad + dot / 2, r, dot / 2, 0, Math.PI * 2); g.fill();
  g.fillStyle = "#f2f5f8";
  g.font = `600 ${font}px ui-monospace, SFMono-Regular, Menlo, monospace`;
  g.textBaseline = "middle";
  g.fillText(text, pad * 2 + dot, r + 1);
  const tex = new THREE.CanvasTexture(c);
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: tex, transparent: true, depthTest: false, depthWrite: false,
  }));
  sprite.renderOrder = 10;
  sprite.userData.ratio = c.width / c.height;
  return sprite;
}

export default function Drawing3DView({ result, title, onClose }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const [model] = useState<BuildingModel>(() => buildModel(result));
  // Det man pekat på: ett rör med sin mängdrad, eller en vägg med sina mått. Ingenting annat är byggt, så
  // ingenting annat kan pekas på.
  const [picked, setPicked] = useState<
    | { kind: "ror"; pipe: ModelPipe; qty: any }
    | { kind: "vagg"; wall: ModelWall }
    | null>(null);
  const [ready, setReady] = useState(false);
  const api = useRef<{
    view: (v: ViewName) => void; reset: () => void; spin: (dir: -1 | 1) => void;
    setExploded: (v: boolean) => void; setLabels: (v: boolean) => void; setXray: (v: boolean) => void;
    setWalking: (v: boolean) => void;
  } | null>(null);
  const [exploded, setExploded] = useState(false);
  const [labels, setLabels] = useState(true);
  const [xray, setXray] = useState(false);
  const [walking, setWalking] = useState(false);

  const qtyByDesignation = useMemo(() => {
    const m = new Map<string, any>();
    for (const q of result?.quantities ?? []) m.set(q.designation, q);
    return m;
  }, [result]);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const reduced = REDUCED();
    const span = Math.max(model.size.width, model.size.depth, 6);

    // ---- scen, ljus, mark ------------------------------------------------------------------------------
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#131820");
    scene.fog = new THREE.Fog("#131820", span * 1.8, span * 5.0);

    const camera = new THREE.PerspectiveCamera(46, 1, 0.08, Math.max(400, span * 8));
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    el.appendChild(renderer.domElement);
    const dom = renderer.domElement;
    dom.tabIndex = 0;

    const hemi = new THREE.HemisphereLight("#e9f1fb", "#232a34", 1.55);
    scene.add(hemi);
    const key = new THREE.DirectionalLight("#ffffff", 2.3);
    key.position.set(span * 0.5, span * 0.9, span * 0.4);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.camera.near = 0.5;
    key.shadow.camera.far = span * 4;
    const s = span * 0.8;
    key.shadow.camera.left = -s; key.shadow.camera.right = s;
    key.shadow.camera.top = s; key.shadow.camera.bottom = -s;
    key.shadow.bias = -0.0008;
    scene.add(key);
    const fill = new THREE.DirectionalLight("#b9d4ff", 0.6);
    fill.position.set(-span * 0.6, span * 0.4, -span * 0.5);
    scene.add(fill);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(span * 6, span * 6),
      new THREE.MeshStandardMaterial({ color: "#1b212a", roughness: 0.96, metalness: 0.0 }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.02;
    ground.receiveShadow = true;
    scene.add(ground);

    const slab = new THREE.Mesh(
      new THREE.BoxGeometry(Math.max(model.size.width, 1) * 1.04, 0.12, Math.max(model.size.depth, 1) * 1.04),
      new THREE.MeshStandardMaterial({ color: "#eef1f5", roughness: 0.85, metalness: 0.02 }),
    );
    slab.position.y = -0.06;
    slab.receiveShadow = true;
    scene.add(slab);

    // ---- väggar ----------------------------------------------------------------------------------------
    const wallMat = new THREE.MeshStandardMaterial({ color: "#d6dae0", roughness: 0.78, metalness: 0.04 });
    const wallGroup = new THREE.Group();
    const wallGeo = new THREE.BoxGeometry(1, 1, 1);
    const walls = new THREE.InstancedMesh(wallGeo, wallMat, Math.max(1, model.walls.length));
    walls.castShadow = true; walls.receiveShadow = true;
    const dummy = new THREE.Object3D();
    model.walls.forEach((w, i) => {
      const dx = w.b[0] - w.a[0], dz = w.b[1] - w.a[1];
      const len = Math.hypot(dx, dz) || 0.01;
      dummy.position.set((w.a[0] + w.b[0]) / 2, w.height / 2, (w.a[1] + w.b[1]) / 2);
      dummy.rotation.set(0, Math.atan2(-dz, dx), 0);
      dummy.scale.set(len, w.height, Math.max(0.05, w.thickness));
      dummy.updateMatrix();
      walls.setMatrixAt(i, dummy.matrix);
    });
    walls.instanceMatrix.needsUpdate = true;
    wallGroup.add(walls);
    scene.add(wallGroup);

    // ---- rör -------------------------------------------------------------------------------------------
    // Ett DN16-rör är åtta millimeter i radie. På ett trettio meter brett hus är det ett hårstrå som försvinner
    // mot en vägg, så det ritas med en minsta grovlek som går att se och att peka på. Måttet i panelen är
    // ritningens; grovleken på skärmen är läsbarhet, och panelen säger det.
    const minR = Math.max(0.018, span * 0.0011);
    const pipeGroup = new THREE.Group();
    const labelGroup = new THREE.Group();
    const height = model.floorHeight * 0.82;
    const longest = new Map<string, { pipe: ModelPipe; at: [number, number] }>();
    model.pipes.forEach((p) => {
      const pts = p.path.map(([x, z]) => new THREE.Vector3(x, height, z));
      if (pts.length < 2) return;
      const curve = new THREE.CatmullRomCurve3(pts, false, "catmullrom", 0.02);
      const tubular = Math.min(600, Math.max(8, Math.round(p.meters * 3)));
      const geo = new THREE.TubeGeometry(curve, tubular, Math.max(minR, p.radius), 10, false);
      const mat = new THREE.MeshStandardMaterial({ color: p.color, roughness: 0.35, metalness: 0.45 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.castShadow = true;
      mesh.userData.pipe = p;
      pipeGroup.add(mesh);
      // stigare: ett lodrätt rör där läsningen räknat en
      if (p.risers > 0) {
        const at = p.path[0];
        const riser = new THREE.Mesh(
          new THREE.CylinderGeometry(Math.max(minR, p.radius), Math.max(minR, p.radius), model.floorHeight, 12),
          mat,
        );
        riser.position.set(at[0], model.floorHeight / 2, at[1]);
        riser.castShadow = true;
        riser.userData.pipe = p;
        pipeGroup.add(riser);
      }
      // var beteckningen ska stå: mitt på den längsta sträcka den har
      const mid = p.path[Math.floor(p.path.length / 2)];
      const seen = longest.get(p.designation);
      if (p.designation && (!seen || p.meters > seen.pipe.meters)) {
        longest.set(p.designation, { pipe: p, at: [mid[0], mid[1]] });
      }
    });
    scene.add(pipeGroup);

    // Varje beteckning får en skylt - det är hela poängen med att kunna läsa modellen - och de långa sträckorna
    // får en till, så att ett rör som går genom hela huset är namngivet där man råkar titta.
    const placed: { sprite: THREE.Sprite; primary: boolean }[] = [];
    const put = (text: string, color: string, x: number, z: number, primary: boolean) => {
      if (placed.length >= MAX_LABELS) return;
      const sp = labelSprite(text, color);
      sp.position.set(x, height + 0.34, z);
      labelGroup.add(sp);
      placed.push({ sprite: sp, primary });
    };
    // en skylt per beteckning är det som måste synas; de långa sträckorna får en extra där man råkar titta
    for (const [des, { pipe, at }] of longest) {
      put(pipe.dn ? `${des} · DN${pipe.dn}` : des, pipe.color, at[0], at[1], true);
    }
    for (const p of [...model.pipes].sort((a, b) => b.meters - a.meters).slice(0, 90)) {
      if (!p.designation || p.inWall || p.meters < 4) continue;
      const q = p.path[Math.floor(p.path.length / 4)];
      put(p.designation, p.color, q[0], q[1], false);
    }
    labelGroup.visible = false;          // skyltarna kommer när väggarna rest sig
    scene.add(labelGroup);

    // ---- kamera: en bana från rakt ovanifrån till perspektiv --------------------------------------------
    const target = new THREE.Vector3(0, model.floorHeight * 0.35, 0);
    const radius = Math.max(model.size.width, model.size.depth) * 0.95 + 6;
    const state = { theta: Math.PI * 0.25, phi: 0.02, dist: radius };
    const TOP = Math.PI / 2 - 0.004;
    const place = () => {
      const phi = Math.max(0.05, Math.min(TOP, state.phi));
      camera.position.set(
        target.x + state.dist * Math.cos(phi) * Math.cos(state.theta),
        target.y + state.dist * Math.sin(phi),
        target.z + state.dist * Math.cos(phi) * Math.sin(state.theta),
      );
      // Ju brantare vyn, desto mindre duger en lodrät upp-vektor: rakt ovanifrån är den parallell med blicken
      // och kameran vet inte längre vad som är upp. Den vänds därför mjukt ned i planet och följer vridningen,
      // så att vyn ovanifrån går att snurra hela varvet utan att bilden slår runt.
      const k = Math.max(0, Math.min(1, (phi - 1.05) / (TOP - 1.05)));
      camera.up.set(-Math.cos(state.theta) * k, 1 - k * 0.999, -Math.sin(state.theta) * k).normalize();
      camera.lookAt(target);
    };
    place();

    // ---- gå-läget: kameran i ögonhöjd, tangenterna för den ----------------------------------------------
    const walker = { on: false, yaw: Math.PI * 0.25, pitch: 0, pos: new THREE.Vector3() };
    const keys = new Set<string>();
    const placeWalk = () => {
      camera.up.set(0, 1, 0);
      camera.position.copy(walker.pos);
      const dir = new THREE.Vector3(
        Math.cos(walker.pitch) * Math.cos(walker.yaw),
        Math.sin(walker.pitch),
        Math.cos(walker.pitch) * Math.sin(walker.yaw),
      );
      camera.lookAt(walker.pos.clone().add(dir));
    };
    // Med låst pekare tar canvasen musen, och då går ingen knapp i gränssnittet att klicka på. Enda vägen ut
    // är då Esc, som webbläsaren själv fångar - så när låset släpps lämnar vi gå-läget. Annars sitter man fast
    // i en modell vars "Sluta gå" inte går att träffa.
    const lockChange = () => {
      if (walker.on && document.pointerLockElement !== dom) setWalking(false);
    };
    document.addEventListener("pointerlockchange", lockChange);

    const enterWalk = () => {
      walker.on = true;
      walker.yaw = state.theta + Math.PI;
      walker.pitch = -0.04;
      walker.pos.set(target.x, EYE, target.z);
      pipeGroup.position.y = 0;
      placeWalk();
      dom.requestPointerLock?.();
    };
    const leaveWalk = () => {
      walker.on = false;
      keys.clear();
      if (document.pointerLockElement === dom) document.exitPointerLock?.();
      place();
    };
    const keyDown = (e: KeyboardEvent) => {
      if (!walker.on) return;
      if (e.key === "Escape") { setWalking(false); return; }
      const k = e.key.toLowerCase();
      keys.add(k);
      if (["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright", " "].includes(k)) e.preventDefault();
    };
    const keyUp = (e: KeyboardEvent) => keys.delete(e.key.toLowerCase());
    window.addEventListener("keydown", keyDown);
    window.addEventListener("keyup", keyUp);

    // ---- muskontroll: orbit, pan, zoom - och blicken i gå-läget -----------------------------------------
    let dragging: "orbit" | "pan" | null = null;
    let lx = 0, ly = 0;
    const down = (e: PointerEvent) => {
      if (walker.on) {
        if (document.pointerLockElement !== dom) dom.requestPointerLock?.();
        return;
      }
      dragging = e.button === 2 || e.shiftKey ? "pan" : "orbit";
      lx = e.clientX; ly = e.clientY;
      (e.target as Element).setPointerCapture?.(e.pointerId);
    };
    const move = (e: PointerEvent) => {
      if (walker.on) {
        if (document.pointerLockElement !== dom) return;
        walker.yaw += e.movementX * 0.0026;
        walker.pitch = Math.max(-1.35, Math.min(1.35, walker.pitch - e.movementY * 0.0022));
        placeWalk();
        return;
      }
      if (!dragging) return;
      const dx = e.clientX - lx, dy = e.clientY - ly;
      lx = e.clientX; ly = e.clientY;
      if (dragging === "orbit") {
        state.theta -= dx * 0.006;
        state.phi = Math.max(0.05, Math.min(TOP, state.phi + dy * 0.005));
      } else {
        const k = state.dist * 0.0016;
        const right = new THREE.Vector3().subVectors(camera.position, target)
          .cross(new THREE.Vector3(0, 1, 0)).normalize();
        target.addScaledVector(right, -dx * k);
        target.y = Math.max(0, target.y + dy * k);
      }
      place();
    };
    const up = () => { dragging = null; };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      if (walker.on) return;
      state.dist = Math.max(2, Math.min(radius * 6, state.dist * (1 + Math.sign(e.deltaY) * 0.12)));
      place();
    };
    dom.addEventListener("pointerdown", down);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    dom.addEventListener("wheel", wheel, { passive: false });
    dom.addEventListener("contextmenu", (e) => e.preventDefault());

    // ---- val av objekt ---------------------------------------------------------------------------------
    const ray = new THREE.Raycaster();
    const ndc = new THREE.Vector2();
    let hi: THREE.Mesh | null = null;
    // väggarna delar material, så den utpekade lyfts fram med sin egen instansfärg
    const plainWall = new THREE.Color("#ffffff");
    const litWall = new THREE.Color("#9fd8e6");
    let lastWall = -1;
    const click = (e: PointerEvent) => {
      const r = dom.getBoundingClientRect();
      // i gå-läget siktar man med blicken: strålen går ur mitten av bilden
      if (walker.on) ndc.set(0, 0);
      else ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(ndc, camera);
      // rören först: de är smala och ligger ovanpå, så en träff på ett rör är alltid den som menades
      const hit = ray.intersectObjects(pipeGroup.children, false)[0];
      if (hi) { (hi.material as THREE.MeshStandardMaterial).emissive?.setHex(0x000000); hi = null; }
      walls.setColorAt(lastWall >= 0 ? lastWall : 0, plainWall);
      if (lastWall >= 0 && walls.instanceColor) walls.instanceColor.needsUpdate = true;
      lastWall = -1;
      if (hit) {
        const mesh = hit.object as THREE.Mesh;
        hi = mesh;
        (mesh.material as THREE.MeshStandardMaterial).emissive?.setHex(0x2b4a6b);
        const pipe = mesh.userData.pipe as ModelPipe;
        setPicked({ kind: "ror", pipe, qty: qtyByDesignation.get(pipe.designation) ?? null });
        return;
      }
      const wallHit = ray.intersectObject(walls, false)[0] as THREE.Intersection | undefined;
      const id = wallHit?.instanceId;
      if (id != null && model.walls[id]) {
        lastWall = id;
        walls.setColorAt(id, litWall);
        if (walls.instanceColor) walls.instanceColor.needsUpdate = true;
        setPicked({ kind: "vagg", wall: model.walls[id] });
        return;
      }
      setPicked(null);
    };
    dom.addEventListener("click", click as any);

    // ---- storlek ---------------------------------------------------------------------------------------
    const resize = () => {
      const w = el.clientWidth || 1, h = el.clientHeight || 1;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);

    // ---- resan: väggarna reser sig, kameran tiltar ------------------------------------------------------
    const RISE = reduced ? 0 : 1500;
    const t0 = performance.now();
    let last = performance.now();
    let wantLabels = true;
    let raf = 0;
    const tick = (now: number) => {
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      const t = RISE ? Math.min(1, (now - t0) / RISE) : 1;
      const e = easeOut(t);
      wallGroup.scale.y = Math.max(0.001, e);
      wallGroup.position.y = 0;
      pipeGroup.visible = t > 0.35;
      pipeGroup.scale.y = Math.max(0.001, easeOut(Math.max(0, (t - 0.35) / 0.65)));
      labelGroup.visible = wantLabels && t >= 1;
      if (RISE && !walker.on && t < 1) {
        state.phi = 0.02 + (0.62 - 0.02) * e;
        state.dist = radius * (1.35 - 0.35 * e);
        place();
      }
      if (walker.on) {
        const speed = (keys.has("shift") ? RUN : WALK) * dt;
        const fx = Math.cos(walker.yaw), fz = Math.sin(walker.yaw);
        let mx = 0, mz = 0;
        if (keys.has("w") || keys.has("arrowup")) { mx += fx; mz += fz; }
        if (keys.has("s") || keys.has("arrowdown")) { mx -= fx; mz -= fz; }
        if (keys.has("a") || keys.has("arrowleft")) { mx += fz; mz -= fx; }
        if (keys.has("d") || keys.has("arrowright")) { mx -= fz; mz += fx; }
        const len = Math.hypot(mx, mz);
        if (len > 0) {
          walker.pos.x += (mx / len) * speed;
          walker.pos.z += (mz / len) * speed;
          walker.pos.y = EYE;
          placeWalk();
        }
      }
      // Skyltarna hålls lika stora på skärmen oavsett avstånd - en skylt som växer med avståndet blir en
      // skylt som täcker huset - och de som skulle hamna ovanpå varandra tas bort. En trave namn är inte
      // läsbarare än inget namn alls, så den som ligger närmast får platsen och resten väntar på sin vinkel.
      if (labelGroup.visible) {
        const vh = 2 * Math.tan((camera.fov * Math.PI / 180) / 2);
        const kept: [number, number][] = [];
        const v = new THREE.Vector3();
        const order = placed
          .map((q) => ({ ...q, d: camera.position.distanceTo(q.sprite.position) }))
          .sort((a, b) => (a.primary === b.primary ? a.d - b.d : a.primary ? -1 : 1));
        for (const { sprite, d } of order) {
          const h = Math.max(0.16, d * vh * 0.026);
          sprite.scale.set(h * (sprite.userData.ratio as number), h, 1);
          v.copy(sprite.position).project(camera);
          if (v.z > 1 || Math.abs(v.x) > 1.25 || Math.abs(v.y) > 1.25) { sprite.visible = false; continue; }
          const sx = v.x * 0.5 * el.clientWidth, sy = v.y * 0.5 * el.clientHeight;
          const room = kept.every(([kx, ky]) => Math.abs(kx - sx) > 120 || Math.abs(ky - sy) > 26);
          sprite.visible = room;
          if (room) kept.push([sx, sy]);
        }
      }
      if (t >= 1 && !ready) setReady(true);
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    const glideTo = (th: number, ph: number) => {
      const from = { theta: state.theta, phi: state.phi };
      const start = performance.now();
      const glide = (now: number) => {
        const t = Math.min(1, (now - start) / (reduced ? 1 : 520));
        const e = easeOut(t);
        state.theta = from.theta + (th - from.theta) * e;
        state.phi = from.phi + (ph - from.phi) * e;
        place();
        if (t < 1) requestAnimationFrame(glide);
      };
      requestAnimationFrame(glide);
    };

    api.current = {
      // Ovanifrån behåller den vridning man redan har: att trycka på knappen ska lyfta blicken, inte vrida
      // huset tillbaka till ett väderstreck man aldrig valde.
      view: (v) => {
        const preset: Record<ViewName, [number, number]> = {
          // rakt ovanifrån läggs planen rakt i rutan: närmaste kvartsvarv, så bladet inte står på diagonalen
          topp: [Math.round(state.theta / (Math.PI / 2)) * (Math.PI / 2), TOP],
          perspektiv: [Math.PI * 0.25, 0.62],
          front: [Math.PI * 0.5, 0.12],
          sida: [0, 0.12],
        };
        const [th, ph] = preset[v];
        glideTo(th, ph);
      },
      spin: (dir) => glideTo(state.theta + dir * Math.PI / 4, state.phi),
      reset: () => {
        target.set(0, model.floorHeight * 0.35, 0);
        state.theta = Math.PI * 0.25; state.phi = 0.62; state.dist = radius;
        place();
      },
      setExploded: (v: boolean) => {
        if (!walker.on) pipeGroup.position.y = v ? model.floorHeight * 1.15 : 0;
      },
      setLabels: (v: boolean) => { wantLabels = v; labelGroup.visible = v; },
      setXray: (v: boolean) => {
        wallMat.transparent = v;
        wallMat.opacity = v ? 0.26 : 1;
        wallMat.depthWrite = !v;
        wallMat.needsUpdate = true;
        walls.castShadow = !v;
      },
      setWalking: (v: boolean) => { if (v) enterWalk(); else if (walker.on) leaveWalk(); },
    };

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      document.removeEventListener("pointerlockchange", lockChange);
      if (document.pointerLockElement === dom) document.exitPointerLock?.();
      window.removeEventListener("keydown", keyDown);
      window.removeEventListener("keyup", keyUp);
      dom.removeEventListener("pointerdown", down);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      dom.removeEventListener("wheel", wheel);
      dom.removeEventListener("click", click as any);
      renderer.dispose();
      scene.traverse((o: any) => { o.geometry?.dispose?.(); o.material?.dispose?.(); });
      el.removeChild(renderer.domElement);
    };
    // modellen byggs en gång per öppning; resten är imperativt inuti scenen
  }, [model]);

  useEffect(() => { api.current?.setExploded(exploded); }, [exploded]);
  useEffect(() => { api.current?.setLabels(labels); }, [labels]);
  useEffect(() => { api.current?.setXray(xray); }, [xray]);
  useEffect(() => { api.current?.setWalking(walking); }, [walking]);

  return (
    <div className="d3-wrap" role="dialog" aria-label="Ritningen i tre dimensioner">
      <div ref={host} className="d3-canvas" />
      <div className="d3-top">
        <div className="d3-title">
          <b>{title || "Ritningen i 3D"}</b>
          <span className="muted small">
            {model.stats.walls} väggdelar · {model.stats.pipes} rörsträckor · {model.stats.metres} m
            {model.scaled ? "" : " · bladet saknar skala, måtten är ritningens punkter"}
          </span>
        </div>
        <button className="secondary small" onClick={() => { setWalking(false); onClose(); }}>Tillbaka till 2D</button>
      </div>
      {walking && <div className="d3-cross" aria-hidden="true" />}
      <Drawing3DControls
        onView={(v) => api.current?.view(v)}
        onReset={() => api.current?.reset()}
        onSpin={(d) => api.current?.spin(d)}
        exploded={exploded}
        onExploded={setExploded}
        labels={labels}
        onLabels={setLabels}
        xray={xray}
        onXray={setXray}
        walking={walking}
        onWalk={setWalking}
      />
      {picked && (
        <aside className="d3-info">
          <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
            <b>{picked.kind === "ror" ? (picked.pipe.designation || "Rör") : "Vägg"}</b>
            <button className="ghost small" onClick={() => setPicked(null)}>Stäng</button>
          </div>
          {picked.kind === "ror" ? (
            <>
              <table className="qty"><tbody>
                <tr><td>Typ</td><td className="num">{picked.pipe.inWall ? "Rör genom vägg" : "Rör"}</td></tr>
                {picked.pipe.system && <tr><td>System</td><td className="num">{picked.pipe.system}</td></tr>}
                <tr><td>Dimension</td><td className="num">DN{picked.pipe.dn ?? "?"}</td></tr>
                <tr><td>Denna sträcka</td><td className="num">{picked.pipe.meters.toFixed(2)} m</td></tr>
                <tr><td>Höjd över golv</td><td className="num">{(model.floorHeight * 0.82).toFixed(2)} m</td></tr>
                {picked.qty && <>
                  <tr><td>Hela beteckningen</td><td className="num">{Number(picked.qty.confirmed_total_m ?? 0).toFixed(2)} m</td></tr>
                  <tr><td>Sträckor</td><td className="num">{picked.qty.physical_pipe_count}</td></tr>
                  <tr><td>Etiketter</td><td className="num">{picked.qty.label_count ?? 0}</td></tr>
                  {picked.qty.riser_count > 0 && <tr><td>Stigare</td><td className="num">{picked.qty.riser_count}</td></tr>}
                </>}
              </tbody></table>
              <p className="muted small" style={{ marginBottom: 0 }}>
                Mängden kommer från läsningens tabell, inte ur 3D-modellen. Ett tunt rör ritas grövre än det är
                för att synas; dimensionen ovan är ritningens.
              </p>
            </>
          ) : (
            <>
              <table className="qty"><tbody>
                <tr><td>Typ</td><td className="num">Vägg</td></tr>
                <tr><td>Längd</td><td className="num">
                  {Math.hypot(picked.wall.b[0] - picked.wall.a[0], picked.wall.b[1] - picked.wall.a[1]).toFixed(2)} m
                </td></tr>
                <tr><td>Tjocklek</td><td className="num">{(picked.wall.thickness * 1000).toFixed(0)} mm</td></tr>
                <tr><td>Höjd</td><td className="num">{picked.wall.height.toFixed(2)} m</td></tr>
                <tr><td>Yta, en sida</td><td className="num">
                  {(Math.hypot(picked.wall.b[0] - picked.wall.a[0], picked.wall.b[1] - picked.wall.a[1])
                    * picked.wall.height).toFixed(2)} m²
                </td></tr>
              </tbody></table>
              <p className="muted small" style={{ marginBottom: 0 }}>
                Väggen är rest ur arkitektens streck och har ingen mängd i läsningen. Höjden är den antagna
                våningshöjden, tjockleken avståndet mellan väggens två linjer.
              </p>
            </>
          )}
        </aside>
      )}
      {!ready && <div className="d3-loading"><span /></div>}
    </div>
  );
}
