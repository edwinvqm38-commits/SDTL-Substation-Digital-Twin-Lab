import ezdxf
from backend.cad_viewer.server import render, inspect

def test_synthetic_dxf(tmp_path):
    path = tmp_path / "synthetic.dxf"
    doc = ezdxf.new("R2013")
    doc.layers.new("TEST")
    doc.modelspace().add_line((0,0), (100,100), dxfattribs={"layer":"TEST"})
    doc.saveas(path)
    assert inspect(path)["statistics"]["total_entities"] == 1
    assert "<svg" in render(path)
    assert "<svg" in render(path, ["TEST"])
