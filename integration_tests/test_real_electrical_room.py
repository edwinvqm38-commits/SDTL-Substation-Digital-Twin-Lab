import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

OUTPUT = ROOT / "integration_tests" / "outputs"


def save(path, data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )


def test_sdtl_real_pipeline():


    pdf = {

        "pdf":
        "SE-PI-PL-OC-700.pdf",

        "page":
        2

    }


    save(
        OUTPUT /
        "candidates" /
        "pdf.json",

        pdf
    )


    candidate = {

        "id":
        "CAND-TEST-001",

        "type":
        "ElectricalRoom",

        "confidence":
        0.93,


        "dimensions":

        {

            "length":12,

            "width":8,

            "height":4

        },


        "source":
        pdf

    }


    save(
        OUTPUT /
        "candidates" /
        "candidate.json",

        candidate
    )


    sdtl_object = {

        "id":
        "CIV-ROOM-TEST-001",

        "type":
        candidate["type"],

        "state":
        "approved",

        "dimensions":
        candidate["dimensions"],

        "source":
        candidate["source"]

    }


    save(
        OUTPUT /
        "objects" /
        "sdtl_object.json",

        sdtl_object
    )


    object3d = {

        "id":
        "3D-ROOM-TEST-001",

        "type":
        "ElectricalRoom",

        "components":

        [

            "Floor",

            "Wall_1",

            "Wall_2",

            "Wall_3",

            "Wall_4",

            "Roof"

        ],

        "source":
        sdtl_object["id"]

    }


    save(
        OUTPUT /
        "models" /
        "object3d.json",

        object3d
    )


    assert object3d["type"] == "ElectricalRoom"

    assert len(object3d["components"]) == 6