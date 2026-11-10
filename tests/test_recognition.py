from pathlib import Path

import numpy as np
import pytest
from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.gp import gp_Pnt
from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCC.Core.StepRepr import StepRepr_RepresentationItem
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Extend.TopologyUtils import TopologyExplorer

from peck_pilot.model import PUBLISHED_CHECKPOINT
from peck_pilot.recognition import InvalidPart, load_model, read_part, recognize

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_PART = ROOT / "parts" / "upstream" / "1_true.stp"
PUBLISHED_WEIGHTS = ROOT / "models" / "published" / PUBLISHED_CHECKPOINT


def stored_labels(path):
    """MFCAD++ label ids stored as each Face's STEP entity name, in Face order."""
    reader = STEPControl_Reader()
    reader.ReadFile(str(path))
    reader.TransferRoots()
    transfer = reader.WS().TransferReader()
    solid = next(iter(TopologyExplorer(reader.OneShape()).solids()))
    return np.array([
        int(StepRepr_RepresentationItem.DownCast(transfer.EntityFromShapeResult(f, 1)).Name().ToCString())
        for f in TopologyExplorer(solid).faces()
    ])


@pytest.mark.parametrize("content", [b"", b"hello, not a STEP file", b"ISO-10303-21;\nHEADER;\n"])
def test_rejects_files_that_are_not_step(tmp_path, content):
    path = tmp_path / "bad.step"
    path.write_bytes(content)
    with pytest.raises(InvalidPart):
        read_part(path)


def test_rejects_more_than_one_solid(tmp_path):
    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    builder.Add(compound, BRepPrimAPI_MakeBox(10, 10, 10).Shape())
    builder.Add(compound, BRepPrimAPI_MakeBox(gp_Pnt(20, 0, 0), 10, 10, 10).Shape())
    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    path = tmp_path / "two.step"
    writer.Write(str(path))
    with pytest.raises(InvalidPart, match="exactly one solid"):
        read_part(path)


@pytest.mark.skipif(not PUBLISHED_WEIGHTS.with_suffix(".ckpt.index").exists(), reason="published weights not present")
def test_published_checkpoint_labels_upstream_part():
    result = recognize(UPSTREAM_PART, load_model(PUBLISHED_WEIGHTS))
    truth = stored_labels(UPSTREAM_PART)
    assert len(result.labels) == len(truth) == len(result.faces)
    assert np.all((result.confidences > 0) & (result.confidences <= 1))
    assert np.mean(result.labels == truth) >= 0.95  # spike measured 0.970
