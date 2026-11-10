"""HTTP API for the viewer. Run: uvicorn peck_pilot.api:app"""
import os
import tempfile
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopAbs import TopAbs_REVERSED
from OCC.Core.TopLoc import TopLoc_Location

from peck_pilot import gcode
from peck_pilot.features import find_features
from peck_pilot.model import LABEL_NAMES
from peck_pilot.recognition import DEFAULT_WEIGHTS, InvalidPart, load_model, recognize
from peck_pilot.strategy import plan

PARTS_DIR = Path(__file__).resolve().parents[1] / "parts"
MAX_UPLOAD = 20 * 1024 * 1024
STEP_SUFFIXES = (".step", ".stp")
state = {}


@asynccontextmanager
async def lifespan(app):
    state["model"] = load_model(os.environ.get("PECK_PILOT_WEIGHTS", DEFAULT_WEIGHTS))
    yield


app = FastAPI(lifespan=lifespan)


def bundled_parts():
    return sorted(str(p.relative_to(PARTS_DIR)) for p in PARTS_DIR.rglob("*") if p.suffix.lower() in STEP_SUFFIXES)


def _mesh(face):
    loc = TopLoc_Location()
    tri = BRep_Tool.Triangulation(face, loc)
    trsf = loc.Transformation()
    vertices = []
    for i in range(1, tri.NbNodes() + 1):
        vertices += tri.Nodes().Value(i).Transformed(trsf).Coord()
    indices = []
    for i in range(1, tri.NbTriangles() + 1):
        a, b, c = tri.Triangles().Value(i).Get()
        # Reversed Faces need flipped winding so normals point out of the material.
        indices += [a - 1, c - 1, b - 1] if face.Orientation() == TopAbs_REVERSED else [a - 1, b - 1, c - 1]
    return vertices, indices


def analyze_file(path, name):
    rec = recognize(path, state["model"])
    features = find_features(rec)
    ops = plan(features)
    origin, size = gcode.stock(rec.solid)
    faces = []
    for i, face in enumerate(rec.faces):
        vertices, indices = _mesh(face)
        faces.append({"id": i, "label": int(rec.labels[i]), "confidence": round(float(rec.confidences[i]), 4),
                      "vertices": [round(v, 4) for v in vertices], "indices": indices})
    return {
        "name": name,
        "label_names": LABEL_NAMES,
        "faces": faces,
        "features": [{"id": k, **asdict(f)} for k, f in enumerate(features)],
        "operations": [{**asdict(op), "tool": asdict(op.tool)} for op in ops],
        "origin": origin,  # G54 in Part coordinates, so the UI can show Operations as the G-code does
        "gcode": gcode.generate(ops, origin, size, Path(name).stem),
    }


@app.get("/api/parts")
def parts():
    return bundled_parts()


@app.post("/api/analyze")
def analyze(part: str = Form(None), file: UploadFile = File(None)):
    if file is None:
        if part not in bundled_parts():  # also blocks path traversal: only listed files are readable
            raise HTTPException(404, "unknown part")
        return analyze_file(PARTS_DIR / part, part)

    if Path(file.filename or "").suffix.lower() not in STEP_SUFFIXES:
        raise HTTPException(415, "upload a .step or .stp file")
    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "file is larger than 20 MB")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "upload.step"
        path.write_bytes(data)
        try:
            return analyze_file(path, Path(file.filename).name)
        except InvalidPart as e:
            raise HTTPException(422, str(e))


WEB_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"
if WEB_DIST.is_dir():  # built viewer (npm run build); mounted last so /api routes win
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
