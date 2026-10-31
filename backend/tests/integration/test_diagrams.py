import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_diagram_manifest_retrieval(client: AsyncClient) -> None:
    headers = {"X-Demo-User-Id": "1"}

    # List all diagrams
    res = await client.get("/api/v1/diagrams", headers=headers)
    assert res.status_code == 200
    diagrams = res.json()
    assert len(diagrams) == 7
    ids = [d["id"] for d in diagrams]
    expected_ids = ["animal", "plant", "neuron", "bacteria", "whiteBlood", "epithelial", "muscle"]
    for expected in expected_ids:
        assert expected in ids

    # Get single diagram manifest for plant cell
    plant_res = await client.get("/api/v1/diagrams/plant", headers=headers)
    assert plant_res.status_code == 200
    plant = plant_res.json()
    assert plant["display_name"] == "Plant Cell: Photosynthetic Architecture"
    assert len(plant["structures"]) >= 4
    assert len(plant["pathways"]) >= 1
    assert "licence" in plant

    # Get single diagram manifest for animal cell
    animal_res = await client.get("/api/v1/diagrams/animal", headers=headers)
    assert animal_res.status_code == 200
    animal = animal_res.json()
    assert animal["display_name"] == "Animal Cell: Metabolic & Cellular Architecture"
    assert len(animal["structures"]) >= 3
    assert len(animal["pathways"]) >= 1
    assert "licence" in animal


@pytest.mark.asyncio
async def test_voice_command_interpretation(client: AsyncClient) -> None:
    headers = {"X-Demo-User-Id": "1"}

    # 1. Structure Highlight Command on Animal Cell
    cmd_res = await client.post(
        "/api/v1/diagrams/animal/commands",
        json={"diagram_id": "animal", "spoken_text": "Show the mitochondrion"},
        headers=headers,
    )
    assert cmd_res.status_code == 200
    res_data = cmd_res.json()
    assert res_data["action"] == "HIGHLIGHT_STRUCTURE"
    assert res_data["target_structure_id"] == "mitochondrion"

    # 2. Reset View Command
    reset_res = await client.post(
        "/api/v1/diagrams/plant/commands",
        json={"diagram_id": "plant", "spoken_text": "Reset the diagram"},
        headers=headers,
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["action"] == "RESET_VIEW"

    # 3. Rotate View Command
    rot_res = await client.post(
        "/api/v1/diagrams/neuron/commands",
        json={"diagram_id": "neuron", "spoken_text": "Rotate the cell to the left"},
        headers=headers,
    )
    assert rot_res.status_code == 200
    assert rot_res.json()["action"] == "ROTATE_VIEW"
    assert rot_res.json()["view_direction"] == "left"

    # 4. Ambiguity Resolution Command
    amb_res = await client.post(
        "/api/v1/diagrams/plant/commands",
        json={"diagram_id": "plant", "spoken_text": "Show the organelle"},
        headers=headers,
    )
    assert amb_res.status_code == 200
    assert amb_res.json()["action"] == "CLARIFY"
    assert len(amb_res.json()["clarification_options"]) >= 2

    # 5. Assessment Safety: Block Answer Reveal During Assessment Mode
    safe_res = await client.post(
        "/api/v1/diagrams/animal/commands",
        json={"diagram_id": "animal", "spoken_text": "Highlight the mitochondrion", "is_assessment_mode": True},
        headers=headers,
    )
    assert safe_res.status_code == 200
    assert safe_res.json()["action"] == "ASSESSMENT_SAFETY_BLOCKED"


@pytest.mark.asyncio
async def test_diagram_assessment_submission_and_idempotency(client: AsyncClient) -> None:
    headers = {"X-Demo-User-Id": "1"}
    attempt_id = str(uuid.uuid4())

    submit_payload = {
        "client_attempt_id": attempt_id,
        "diagram_id": "animal",
        "question_id": "q-diag-animal-01",
        "assessment_type": "identification",
        "selected_structure_id": "mitochondrion",
    }

    # First submission
    res1 = await client.post(
        "/api/v1/diagrams/animal/assessments",
        json=submit_payload,
        headers=headers,
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["is_correct"] is True
    assert data1["score"] == 1.0
    assert data1["is_idempotent_replay"] is False
    assert "mastery" in data1
    assert data1["mastery"]["concept_id"] == "lp-respiration"

    # Second submission (Idempotency replay)
    res2 = await client.post(
        "/api/v1/diagrams/animal/assessments",
        json=submit_payload,
        headers=headers,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_idempotent_replay"] is True
    assert data2["score"] == data1["score"]
    assert data2["mastery"]["after"] == data1["mastery"]["after"]


def test_glb_geometry_integrity_and_bounds() -> None:
    """Automated regression test verifying that all 5 GLB models exist,

    are valid glTF binaries, have valid meshes, and all organelle positions
    remain strictly within the model's physical bounding box (no floating markers).
    """
    import json
    import os
    import struct

    glbs = {
        "plant": {
            "file": "../frontend/public/models/plant-cell-first001.glb",
            "positions": {
                "nucleus": [0.088, 0.166, -0.172],
                "vacuole": [0.117, 0.027, 0.023],
                "chloroplast": [0.133, -0.066, 0.025],
                "cellWall": [-0.28, 0.05, 0.0],
            },
        },
        "whiteBlood": {
            "file": "../frontend/public/models/white-blood-cell-user.glb",
            "positions": {
                "nucleus": [0.0, 0.08, 0.05],
                "lysosome": [-0.15, -0.12, 0.12],
                "granules": [0.16, -0.10, 0.10],
            },
        },
        "animal": {
            "file": "../frontend/public/models/animal-cell-nih.glb",
            "positions": {
                "nucleus": [29.5, 9.8, 25.8],
                "mitochondrion": [10.0, 20.0, 22.0],
                "golgi": [42.0, -10.0, 24.0],
            },
        },
        "neuron": {
            "file": "../frontend/public/models/neuron-nih.glb",
            "positions": {
                "soma": [0.005, 0.061, 0.015],
                "axon": [0.18, -0.15, 0.01],
                "dendrites": [-0.12, 0.22, 0.01],
            },
        },
        "bacteria": {
            "file": "../frontend/public/models/bacteria-wall-nih.glb",
            "positions": {
                "nucleoid": [89.7, 199.6, 184.5],
                "cellWall": [-600.0, 200.0, 180.0],
                "flagellum": [650.0, 500.0, 180.0],
            },
        },
    }

    for model_id, model_data in glbs.items():
        glb_path = os.path.abspath(model_data["file"])
        assert os.path.exists(glb_path), f"GLB asset missing: {glb_path}"
        assert os.path.getsize(glb_path) > 1000, f"GLB asset suspiciously small: {glb_path}"

        with open(glb_path, "rb") as f:
            magic = f.read(4)
            assert magic == b"glTF", f"Not valid glTF: {glb_path}"
            _ver, length = struct.unpack("<II", f.read(8))
            assert length == os.path.getsize(glb_path)

            chunk_len, chunk_type = struct.unpack("<II", f.read(8))
            assert chunk_type == 0x4E4F534A  # JSON chunk
            json_data = json.loads(f.read(chunk_len).decode("utf-8"))

            assert len(json_data.get("meshes", [])) >= 1, f"No meshes in {model_id}"
            prim = json_data["meshes"][0]["primitives"][0]
            pos_acc = json_data["accessors"][prim["attributes"]["POSITION"]]
            min_pt = pos_acc["min"]
            max_pt = pos_acc["max"]

            # Verify every organelle position is physically within the model bounds (margin: 10% tolerance)
            for org_id, pos in model_data["positions"].items():
                for axis in range(3):
                    margin = (max_pt[axis] - min_pt[axis]) * 0.1
                    assert min_pt[axis] - margin <= pos[axis] <= max_pt[axis] + margin, (
                        f"Organelle '{org_id}' in '{model_id}' position {pos} "
                        f"exceeds mesh bounds min={min_pt}, max={max_pt} on axis {axis}"
                    )

