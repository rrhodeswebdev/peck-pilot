import pytest
from fastapi.testclient import TestClient
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from test_features import DEEP, THROUGH, plate
from test_recognition import PUBLISHED_WEIGHTS

from peck_pilot import api

pytestmark = pytest.mark.skipif(not PUBLISHED_WEIGHTS.with_suffix(".ckpt.index").exists(),
                                reason="published weights not present")


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("PECK_PILOT_WEIGHTS", str(PUBLISHED_WEIGHTS))
        with TestClient(api.app) as c:
            yield c


def test_lists_bundled_parts(client):
    assert "upstream/1_true.stp" in client.get("/api/parts").json()


def test_analyzes_a_bundled_part(client):
    body = client.post("/api/analyze", data={"part": "upstream/1_true.stp"}).json()
    assert len(body["faces"]) == 67 and len(body["label_names"]) == 25
    face = body["faces"][0]
    assert len(face["vertices"]) % 3 == 0 and len(face["indices"]) % 3 == 0
    assert max(face["indices"]) < len(face["vertices"]) // 3
    assert body["gcode"].startswith("%\nO1000")
    covered = sorted(i for f in body["features"] for i in f["faces"])
    assert len(covered) == len(set(covered))


@pytest.mark.parametrize("part", ["../README.md", "/etc/passwd", "upstream/../../pyproject.toml", None])
def test_rejects_parts_that_are_not_bundled(client, part):
    data = {"part": part} if part else {}
    assert client.post("/api/analyze", data=data).status_code == 404


def test_upload_must_be_step(client):
    r = client.post("/api/analyze", files={"file": ("part.stl", b"solid x", "application/octet-stream")})
    assert r.status_code == 415


def test_upload_size_is_capped(client):
    r = client.post("/api/analyze", files={"file": ("big.step", b"x" * (api.MAX_UPLOAD + 1))})
    assert r.status_code == 413


def test_invalid_step_upload_is_rejected_and_server_survives(client):
    r = client.post("/api/analyze", files={"file": ("junk.step", b"not a step file")})
    assert r.status_code == 422 and "STEP" in r.json()["detail"]
    assert client.get("/api/parts").status_code == 200


def plate_step_bytes(tmp_path):
    writer = STEPControl_Writer()
    writer.Transfer(plate(THROUGH, DEEP).solid, STEPControl_AsIs)
    path = tmp_path / "plate.step"
    writer.Write(str(path))
    return path.read_bytes()


def test_valid_upload_is_planned(client, tmp_path):
    body = client.post("/api/analyze", files={"file": ("plate.step", plate_step_bytes(tmp_path))}).json()
    assert body["name"] == "plate.step"
    assert body["gcode"].count("M06") == len({op["tool"]["number"] for op in body["operations"]})


def test_hostile_upload_name_adds_no_command(client, tmp_path):
    data = plate_step_bytes(tmp_path)
    plain = client.post("/api/analyze", files={"file": ("plate.step", data)}).json()["gcode"].splitlines()
    hostile = client.post("/api/analyze", files={"file": ("x) G00 Z-50 (.step", data)}).json()["gcode"].splitlines()
    assert hostile[2] == "(PART X_G00_Z-50_)"
    assert hostile[2].count("(") == 1 and hostile[2].count(")") == 1
    assert hostile[:2] == plain[:2] and hostile[3:] == plain[3:]


def test_demo_plate_keeps_its_name(client):
    body = client.post("/api/analyze", data={"part": "demo/mounting_plate.step"}).json()
    assert body["gcode"].splitlines()[2] == "(PART MOUNTING_PLATE)"
