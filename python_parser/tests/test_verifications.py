"""Tests del esquema y las verificaciones sobre el modelo stub.

Ejecutar desde la raíz del repo:
    python -m pytest python_parser/tests -q
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_stub_model import build_stub_model
from schema import validate_model
from verifications import run_all


def test_schema_ok_stub():
    model = build_stub_model()
    assert validate_model(model) == []


def test_all_checks_pass_stub():
    model = build_stub_model()
    checks = run_all(model)
    assert all(c["ok"] for c in checks), checks
    assert [c["name"] for c in checks] == [
        "carga_total_por_piso",
        "suma_areas_tributarias",
        "conservacion_carga",
        "equilibrio_global",
        "compatibilidad_diafragma",
    ]


def test_total_area_stub():
    model = build_stub_model()
    per = {c["level"]: c["total_area_m2"] for c in run_all(model)[0]["detail"]}
    assert per == {"P1": 144.0, "P2": 144.0}


def test_load_conservation_detects_tamper():
    model = build_stub_model()
    model["tributary_areas"][0]["area"] += 3.0
    checks = {c["name"]: c for c in run_all(model)}
    assert not checks["suma_areas_tributarias"]["ok"]
    assert not checks["conservacion_carga"]["ok"]


def test_equilibrium_detects_reaction_error():
    model = build_stub_model()
    model["analysis"]["reactions"][0]["rz"] *= 1.5
    checks = {c["name"]: c for c in run_all(model)}
    assert not checks["equilibrio_global"]["ok"]


def test_diaphragm_detects_missing_node():
    model = build_stub_model()
    model["diaphragms"][0]["nodes"].remove(model["diaphragms"][0]["nodes"][-1])
    checks = {c["name"]: c for c in run_all(model)}
    assert not checks["compatibilidad_diafragma"]["ok"]


def test_schema_detects_wrong_level():
    model = build_stub_model()
    model["nodes"][0]["level"] = "P2"
    errors = validate_model(model)
    assert any("coincide" in e for e in errors)


def test_data_model_data_json_is_valid():
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "data", "model_data.json")
    with open(path, encoding="utf-8") as fh:
        model = json.load(fh)
    assert validate_model(model) == []
    assert all(c["ok"] for c in run_all(model))


def test_example_json_matches_stub():
    model = build_stub_model()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "stub_model.json")
    with open(path, encoding="utf-8") as fh:
        on_disk = json.load(fh)
    assert on_disk == model