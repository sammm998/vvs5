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
 */

type Props = {
  result: any;
  title?: string;
  onClose: () => void;
};

const REDUCED = () => typeof window !== "undefined"
  && window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

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
    view: (v: ViewName) => void; reset: () => void; setExploded: (v: boolean) => void;
  } | null>(null);
  const [exploded, setExploded] = useState(false);

  const qtyByDesignation = useMemo(() => {
    const m = new Map<string, any>();
    for (const q of result?.quantities ?? []) m.set(q.designation, q);
    return m;
  }, [result]);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const reduced = REDUCED();

    // ---- scen, ljus, mark ------------------------------------------------------------------------------
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#0f1216");
    scene.fog = new THREE.Fog("#0f1216", model.size.width * 1.6, model.size.width * 4.2);

    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, Math.max(400, model.size.width * 8));
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    el.appendChild(renderer.domElement);

    const hemi = new THREE.HemisphereLight("#dfe9f5", "#1a1f27", 1.15);
    scene.add(hemi);
    const key = new THREE.DirectionalLight("#ffffff", 2.1);
    const span = Math.max(model.size.width, model.size.depth, 6);
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
    const fill = new THREE.DirectionalLight("#9fc4ff", 0.5);
    fill.position.set(-span * 0.6, span * 0.4, -span * 0.5);
    scene.add(fill);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(span * 6, span * 6),
      new THREE.MeshStandardMaterial({ color: "#171b21", roughness: 0.96, metalness: 0.0 }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.02;
    ground.receiveShadow = true;
    scene.add(ground);

    const slab = new THREE.Mesh(
      new THREE.BoxGeometry(Math.max(model.size.width, 1) * 1.04, 0.12, Math.max(model.size.depth, 1) * 1.04),
      new THREE.MeshStandardMaterial({ color: "#e8ebef", roughness: 0.85, metalness: 0.02 }),
    );
    slab.position.y = -0.06;
    slab.receiveShadow = true;
    scene.add(slab);

    // ---- väggar ----------------------------------------------------------------------------------------
    const wallMat = new THREE.MeshStandardMaterial({ color: "#c8ccd2", roughness: 0.78, metalness: 0.04 });
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
    const pipeGroup = new THREE.Group();
    const pipeMeshes: { mesh: THREE.Mesh; pipe: ModelPipe; base: number }[] = [];
    const height = model.floorHeight * 0.82;
    model.pipes.forEach((p) => {
      const pts = p.path.map(([x, z]) => new THREE.Vector3(x, height, z));
      if (pts.length < 2) return;
      const curve = new THREE.CatmullRomCurve3(pts, false, "catmullrom", 0.02);
      const tubular = Math.min(600, Math.max(8, Math.round(p.meters * 3)));
      const geo = new THREE.TubeGeometry(curve, tubular, Math.max(0.01, p.radius), 10, false);
      const mat = new THREE.MeshStandardMaterial({ color: p.color, roughness: 0.35, metalness: 0.45 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.castShadow = true;
      mesh.userData.pipe = p;
      pipeGroup.add(mesh);
      pipeMeshes.push({ mesh, pipe: p, base: height });
      // stigare: ett lodrätt rör där läsningen räknat en
      if (p.risers > 0) {
        const at = p.path[0];
        const riser = new THREE.Mesh(
          new THREE.CylinderGeometry(Math.max(0.01, p.radius), Math.max(0.01, p.radius), model.floorHeight, 12),
          mat,
        );
        riser.position.set(at[0], model.floorHeight / 2, at[1]);
        riser.castShadow = true;
        riser.userData.pipe = p;
        pipeGroup.add(riser);
      }
    });
    scene.add(pipeGroup);

    // ---- kamera: en bana från rakt ovanifrån till perspektiv --------------------------------------------
    const target = new THREE.Vector3(0, model.floorHeight * 0.35, 0);
    const radius = Math.max(model.size.width, model.size.depth) * 0.95 + 6;
    const state = { theta: Math.PI * 0.25, phi: 0.02, dist: radius };
    const place = () => {
      const phi = Math.max(0.06, Math.min(Math.PI / 2 - 0.02, state.phi));
      camera.position.set(
        target.x + state.dist * Math.cos(phi) * Math.cos(state.theta),
        target.y + state.dist * Math.sin(phi),
        target.z + state.dist * Math.cos(phi) * Math.sin(state.theta),
      );
      camera.lookAt(target);
    };
    place();

    // ---- muskontroll: orbit, pan, zoom ------------------------------------------------------------------
    let dragging: "orbit" | "pan" | null = null;
    let lx = 0, ly = 0;
    const down = (e: PointerEvent) => {
      dragging = e.button === 2 || e.shiftKey ? "pan" : "orbit";
      lx = e.clientX; ly = e.clientY;
      (e.target as Element).setPointerCapture?.(e.pointerId);
    };
    const move = (e: PointerEvent) => {
      if (!dragging) return;
      const dx = e.clientX - lx, dy = e.clientY - ly;
      lx = e.clientX; ly = e.clientY;
      if (dragging === "orbit") {
        state.theta -= dx * 0.006;
        state.phi = Math.max(0.06, Math.min(Math.PI / 2 - 0.02, state.phi + dy * 0.005));
      } else {
        const k = state.dist * 0.0016;
        const right = new THREE.Vector3().subVectors(camera.position, target).cross(camera.up).normalize();
        target.addScaledVector(right, -dx * k);
        target.y = Math.max(0, target.y + dy * k);
      }
      place();
    };
    const up = () => { dragging = null; };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      state.dist = Math.max(2, Math.min(radius * 6, state.dist * (1 + Math.sign(e.deltaY) * 0.12)));
      place();
    };
    const dom = renderer.domElement;
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
      ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
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
    let raf = 0;
    const tick = (now: number) => {
      const t = RISE ? Math.min(1, (now - t0) / RISE) : 1;
      const e = easeOut(t);
      wallGroup.scale.y = Math.max(0.001, e);
      wallGroup.position.y = 0;
      pipeGroup.visible = t > 0.35;
      pipeGroup.scale.y = Math.max(0.001, easeOut(Math.max(0, (t - 0.35) / 0.65)));
      if (RISE) {
        state.phi = 0.02 + (0.62 - 0.02) * e;
        state.dist = radius * (1.35 - 0.35 * e);
        place();
      }
      if (t >= 1 && !ready) setReady(true);
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    api.current = {
      view: (v) => {
        const preset: Record<ViewName, [number, number]> = {
          topp: [Math.PI * 0.25, Math.PI / 2 - 0.03],
          perspektiv: [Math.PI * 0.25, 0.62],
          front: [Math.PI * 0.5, 0.12],
          sida: [0, 0.12],
        };
        const [th, ph] = preset[v];
        const from = { ...state };
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
      },
      reset: () => {
        target.set(0, model.floorHeight * 0.35, 0);
        state.theta = Math.PI * 0.25; state.phi = 0.62; state.dist = radius;
        place();
      },
      setExploded: (v: boolean) => {
        pipeGroup.position.y = v ? model.floorHeight * 1.15 : 0;
      },
    };

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
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
        <button className="secondary small" onClick={onClose}>Tillbaka till 2D</button>
      </div>
      <Drawing3DControls
        onView={(v) => api.current?.view(v)}
        onReset={() => api.current?.reset()}
        exploded={exploded}
        onExploded={setExploded}
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
                Mängden kommer från läsningens tabell, inte ur 3D-modellen.
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
