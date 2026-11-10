import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type Face = { id: number; label: number; confidence: number; vertices: number[]; indices: number[] };
type Hole = { x: number; y: number; top_z: number; bottom_z: number; diameter: number; through: boolean };
type Feature = { id: number; label: number; faces: number[]; confidence: number; hole: Hole | null; reason: string | null };
type Tool = { number: number; kind: string; diameter: number };
type Operation = {
  tool: Tool; feature: number; cycle: string; x: number; y: number; r_plane: number; z: number;
  peck: number | null; rpm: number; feed: number; warning: string | null;
};
type Analysis = {
  name: string; label_names: string[]; faces: Face[]; features: Feature[]; operations: Operation[];
  origin: [number, number, number]; gcode: string;
};

const THROUGH_HOLE = 1, BLIND_HOLE = 12, STOCK = 24;
const UNPLANNED = new Set(["wrong label?", "failed geometry check", "needs another Setup", "no drill within tolerance", "too large to drill"]);

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const partSelect = $<HTMLSelectElement>("part-select");
const upload = $<HTMLInputElement>("upload");
const statusEl = $("status");
const viewer = $("viewer");
const legend = $("legend");
const selectionEl = $("selection");
const featuresEl = $("features");
const opsBody = $<HTMLTableElement>("operations").tBodies[0];
const gcodeEl = $("gcode");
const download = $<HTMLButtonElement>("download");

function labelColor(label: number): THREE.Color {
  if (label === THROUGH_HOLE) return new THREE.Color("#1f6feb");
  if (label === BLIND_HOLE) return new THREE.Color("#e8590c");
  if (label === STOCK) return new THREE.Color("#c9c9c4");
  return new THREE.Color().setHSL(((label * 47) % 360) / 360, 0.35, 0.6);
}

// Scene: Z up, to match the machine.
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor("#f6f6f4");
viewer.prepend(renderer.domElement);
const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a84, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
scene.add(sun);
const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 10_000);
camera.up.set(0, 0, 1);
const controls = new OrbitControls(camera, renderer.domElement);
const part = new THREE.Group();
scene.add(part);

new ResizeObserver(() => {
  const { clientWidth: w, clientHeight: h } = viewer;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}).observe(viewer);
renderer.setAnimationLoop(() => {
  sun.position.copy(camera.position);
  controls.update();
  renderer.render(scene, camera);
});

let current: Analysis | null = null;
let meshes: THREE.Mesh[] = [];
let featureOfFace: (number | undefined)[] = [];

function setStatus(text: string, error = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("error", error);
}

function buildPart(a: Analysis) {
  part.clear();
  meshes = a.faces.map((f) => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(f.vertices, 3));
    geometry.setIndex(f.indices);
    geometry.computeVertexNormals();
    const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
      color: labelColor(f.label), side: THREE.DoubleSide, roughness: 0.8, polygonOffset: true, polygonOffsetFactor: 1,
    }));
    mesh.userData.face = f.id;
    mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometry, 25), new THREE.LineBasicMaterial({ color: 0x3a3c40 })));
    part.add(mesh);
    return mesh;
  });

  const box = new THREE.Box3().setFromObject(part);
  const center = box.getCenter(new THREE.Vector3());
  const radius = box.getSize(new THREE.Vector3()).length() / 2;
  controls.target.copy(center);
  // Fit the bounding sphere in whichever field of view is narrower, so tall phone screens don't crop the Part.
  const vfov = THREE.MathUtils.degToRad(camera.fov);
  const hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
  const distance = (radius / Math.sin(Math.min(vfov, hfov) / 2)) * 1.1;
  camera.position.copy(center).add(new THREE.Vector3(1, -1.4, 1.1).normalize().multiplyScalar(distance));
  camera.near = radius / 100;
  camera.far = radius * 100;
  camera.updateProjectionMatrix();
}

function buildLegend(a: Analysis) {
  const counts = new Map<number, number>();
  a.faces.forEach((f) => counts.set(f.label, (counts.get(f.label) ?? 0) + 1));
  legend.replaceChildren(...[...counts.keys()].sort((x, y) => x - y).map((label) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="swatch" style="background:#${labelColor(label).getHexString()}"></span>`;
    li.append(a.label_names[label]);
    return li;
  }));
}

const fmt = (n: number) => n.toFixed(3);

function holeText(h: Hole) {
  return `Ø${h.diameter.toFixed(2)} ${h.through ? "through" : `blind, ${(h.top_z - h.bottom_z).toFixed(2)} deep`}`;
}

function buildLists(a: Analysis) {
  const order = (f: Feature) => (f.hole ? 0 : UNPLANNED.has(f.reason ?? "") ? 1 : 2);
  featuresEl.replaceChildren(...[...a.features].sort((x, y) => order(x) - order(y)).map((f) => {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.feature = String(f.id);
    b.innerHTML = `<span class="swatch" style="background:#${labelColor(f.label).getHexString()}"></span>`;
    b.append(`${a.label_names[f.label]}${f.hole ? ` ${holeText(f.hole)}` : ""}`);
    const reason = document.createElement("span");
    reason.className = `reason${UNPLANNED.has(f.reason ?? "") ? " unplanned" : ""}`;
    reason.textContent = f.reason ?? "planned";
    b.append(reason);
    b.onclick = () => select(f.id);
    li.append(b);
    return li;
  }));

  const [ox, oy, oz] = a.origin;
  opsBody.replaceChildren(...a.operations.flatMap((op) => {
    const tr = document.createElement("tr");
    tr.dataset.feature = String(op.feature);
    tr.tabIndex = 0;
    const cells = [`T${op.tool.number} ${op.tool.kind} Ø${op.tool.diameter}`, op.cycle, fmt(op.x - ox), fmt(op.y - oy),
      fmt(op.z - oz), op.peck ? fmt(op.peck) : "", String(op.rpm), op.feed.toFixed(1)];
    tr.replaceChildren(...cells.map((c) => Object.assign(document.createElement("td"), { textContent: c })));
    tr.onclick = () => select(op.feature);
    tr.onkeydown = (e) => { if (e.key === "Enter") select(op.feature); };
    if (!op.warning) return [tr];
    const warn = document.createElement("tr");
    warn.className = "warning";
    warn.dataset.feature = String(op.feature);
    warn.innerHTML = `<td colspan="8"></td>`;
    warn.firstElementChild!.textContent = `⚠ ${op.warning}`;
    return [tr, warn];
  }));
}

function select(featureId: number | undefined, faceId?: number) {
  if (!current) return;
  const feature = featureId === undefined ? undefined : current.features[featureId];
  const faces = new Set(feature ? feature.faces : faceId !== undefined ? [faceId] : []);
  // Ghost everything else so the selection stands out, even holes hidden inside the Part.
  meshes.forEach((m, i) => {
    const ghost = faces.size > 0 && !faces.has(i);
    const mat = m.material as THREE.MeshStandardMaterial;
    // Selected Faces turn yellow like the selected rows; tinting the label color could mimic another label.
    mat.color.set(faces.has(i) ? 0xffc400 : labelColor(current!.faces[i].label));
    if (mat.transparent !== ghost) mat.needsUpdate = true;
    mat.transparent = ghost;
    mat.opacity = ghost ? 0.12 : 1;
    mat.depthWrite = !ghost;
    const edges = (m.children[0] as THREE.LineSegments).material as THREE.LineBasicMaterial;
    edges.transparent = ghost;
    edges.opacity = ghost ? 0.25 : 1;
    edges.needsUpdate = true;
  });
  document.querySelectorAll<HTMLElement>("[data-feature]").forEach((el) =>
    el.classList.toggle("selected", feature !== undefined && el.dataset.feature === String(feature.id)));
  document.querySelector(`#features [data-feature="${feature?.id}"]`)?.scrollIntoView({ block: "nearest" });

  if (feature) {
    const ops = current.operations.filter((o) => o.feature === feature.id).length;
    selectionEl.textContent = `${current.label_names[feature.label]}${feature.hole ? `, ${holeText(feature.hole)}` : ""}. `
      + `${feature.faces.length} Face${feature.faces.length > 1 ? "s" : ""}, lowest confidence ${(feature.confidence * 100).toFixed(1)}%. `
      + (feature.reason ? `Not planned: ${feature.reason}.` : `${ops} Operations.`);
  } else if (faceId !== undefined) {
    const f = current.faces[faceId];
    selectionEl.textContent = `Face ${f.id}: ${current.label_names[f.label]} (${(f.confidence * 100).toFixed(1)}% confidence).`;
  } else {
    selectionEl.textContent = "Click a Face or a row below.";
  }
}

// Click (not drag) on the model selects the Face's Machining Feature.
const raycaster = new THREE.Raycaster();
let down = { x: 0, y: 0 };
renderer.domElement.addEventListener("pointerdown", (e) => (down = { x: e.clientX, y: e.clientY }));
renderer.domElement.addEventListener("pointerup", (e) => {
  if (Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4) return;
  const rect = renderer.domElement.getBoundingClientRect();
  raycaster.setFromCamera(new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1,
    -((e.clientY - rect.top) / rect.height) * 2 + 1), camera);
  const hit = raycaster.intersectObjects(meshes, false)[0];
  const faceId = hit?.object.userData.face as number | undefined;
  select(faceId === undefined ? undefined : featureOfFace[faceId], faceId);
});

async function analyze(body: FormData, label: string) {
  setStatus(`Analyzing ${label}…`);
  partSelect.disabled = upload.disabled = true;
  try {
    const res = await fetch("/api/analyze", { method: "POST", body });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? res.statusText);
    current = data as Analysis;
    featureOfFace = [];
    current.features.forEach((f) => f.faces.forEach((i) => (featureOfFace[i] = f.id)));
    buildPart(current);
    buildLegend(current);
    buildLists(current);
    gcodeEl.textContent = current.gcode;
    download.disabled = false;
    select(undefined);
    const planned = current.features.filter((f) => f.hole && !f.reason).length;
    setStatus(`${current.name}: ${current.faces.length} Faces, ${planned} hole${planned === 1 ? "" : "s"} planned, `
      + `${current.operations.length} Operation${current.operations.length === 1 ? "" : "s"}`);
  } catch (err) {
    setStatus(`Could not analyze ${label}: ${(err as Error).message}`, true);
  } finally {
    partSelect.disabled = upload.disabled = false;
  }
}

partSelect.onchange = () => {
  const body = new FormData();
  body.append("part", partSelect.value);
  analyze(body, partSelect.value);
};

upload.onchange = () => {
  const file = upload.files?.[0];
  if (!file) return;
  const body = new FormData();
  body.append("file", file);
  analyze(body, file.name);
  upload.value = "";
};

download.onclick = () => {
  if (!current) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([current.gcode], { type: "text/plain" }));
  a.download = `${current.name.replace(/\.[^.]+$/, "").replace(/[^\w-]+/g, "_")}.nc`;
  a.click();
  URL.revokeObjectURL(a.href);
};

(async () => {
  try {
    const parts: string[] = await (await fetch("/api/parts")).json();
    partSelect.replaceChildren(...parts.map((p) => Object.assign(document.createElement("option"), { value: p, textContent: p })));
    if (parts.length) partSelect.onchange!(new Event("change"));
  } catch {
    setStatus("Could not reach the API. Is uvicorn running?", true);
  }
})();
