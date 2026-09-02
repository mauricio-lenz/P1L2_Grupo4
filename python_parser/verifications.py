"""Verificaciones físicas del modelo (invariantes del lab P1L2).

Checks implementados:
1. carga_total_por_piso   -> q * area por losa, total por nivel y caso.
2. suma_areas_tributarias -> por nivel y caso, suma de áreas == área de losa.
3. conservacion_carga     -> sum(F transferidas) == q * sum(area) == carga total.
4. equilibrio_global      -> sum(F) + sum(reacciones) ~= 0.
5. compatibilidad_diafragma -> nodos del diafragma en su nivel/plano.

Uso CLI:
    python verifications.py [ruta_modelo_json]
"""

import json
import os
import sys

TOL_REL = 1e-6


def polygon_area(poly):
    a = 0.0
    for k in range(len(poly)):
        x1, y1 = poly[k]
        x2, y2 = poly[(k + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def _result(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": detail}


def check_total_load(model):
    cases = model["load_cases"]
    per = []
    slabs_by_level = {}
    for s in model["slabs"]:
        slabs_by_level.setdefault(s["level"], []).append(s)
    for case, spec in cases.items():
        field = spec["slab_field"]
        for level, slabs in sorted(slabs_by_level.items()):
            total = sum(s[field] * polygon_area(s["polygon"]) for s in slabs)
            per.append({"case": case, "level": level, "total_load_kN": total,
                        "total_area_m2": sum(polygon_area(s["polygon"]) for s in slabs)})
    ok = all(p["total_load_kN"] >= 0 for p in per)
    return _result("carga_total_por_piso", ok, per)


def check_tributary_area_sum(model):
    per = []
    slabs_area = {s["level"]: 0.0 for s in model["slabs"]}
    for s in model["slabs"]:
        slabs_area[s["level"]] += polygon_area(s["polygon"])
    groups = {}
    for t in model["tributary_areas"]:
        groups.setdefault((t["level"], t["case"]), 0.0)
        groups[(t["level"], t["case"])] += t["area"]
    ok_all = True
    for (level, case), area in sorted(groups.items()):
        expected = slabs_area[level]
        ok = abs(area - expected) <= TOL_REL * max(expected, 1e-12)
        ok_all = ok_all and ok
        per.append({"level": level, "case": case, "suma_tributaria_m2": area,
                    "area_losa_m2": expected, "ok": ok})
    return _result("suma_areas_tributarias", ok_all, per)


def check_load_conservation(model):
    cases = model["load_cases"]
    slab_by_id = {s["id"]: s for s in model["slabs"]}
    per = []
    ok_all = True
    for case in sorted(cases):
        field = cases[case]["slab_field"]
        levels = {t["level"] for t in model["tributary_areas"]}
        for level in sorted(levels):
            area_total = 0.0
            f_total = 0.0
            for t in model["tributary_areas"]:
                if t["level"] == level:
                    area_total += t["area"]
                    f_total += t["area"] * slab_by_id[t["slab"]][field]
            slab_load = sum(
                s[field] * polygon_area(s["polygon"]) for s in model["slabs"]
                if s["level"] == level)
            ok = abs(f_total - slab_load) <= TOL_REL * max(slab_load, 1e-12)
            ok_all = ok_all and ok
            per.append({"level": level, "case": case, "carga_transferida_kN": f_total,
                        "carga_losa_kN": slab_load, "ok": ok})
    return _result("conservacion_carga", ok_all, per)


def check_global_equilibrium(model):
    cases = model["load_cases"]
    slab_by_id = {s["id"]: s for s in model["slabs"]}
    per = []
    ok_all = True
    for case in sorted(cases):
        field = cases[case]["slab_field"]
        applied = 0.0
        for t in model["tributary_areas"]:
            applied -= t["area"] * slab_by_id[t["slab"]][field]
        reactions = [r["rz"] for r in model.get("analysis", {}).get("reactions", [])
                     if r.get("case") == case]
        if not reactions:
            ok_all = False
            per.append({"case": case, "ok": False,
                        "detail": "sin reacciones en analysis.reactions"})
            continue
        rsum = sum(reactions)
        ok = abs(applied + rsum) <= TOL_REL * max(abs(applied), abs(rsum), 1e-12)
        ok_all = ok_all and ok
        per.append({"case": case, "aplicada_kN": applied, "reacciones_kN": rsum, "ok": ok})
    return _result("equilibrio_global", ok_all, per)


def check_diaphragm_compatibility(model):
    nodes_by_tag = {n["tag"]: n for n in model["nodes"]}
    level_z = {l["id"]: l["elevation"] for l in model["levels"]}
    level_nodes = {}
    for n in model["nodes"]:
        level_nodes.setdefault(n["level"], set()).add(n["tag"])
    per = []
    ok_all = True
    for d in model["diaphragms"]:
        bad = []
        if len(set(d["nodes"])) != len(d["nodes"]):
            bad.append("nodos duplicados")
        for tag in d["nodes"]:
            n = nodes_by_tag[tag]
            if n["level"] != d["level"]:
                bad.append(f"nodo {tag} en nivel {n['level']} != {d['level']}")
            elif abs(n["z"] - level_z[d["level"]]) > 1e-9:
                bad.append(f"nodo {tag} no coplanar (z={n['z']})")
        if d["master"] not in d["nodes"]:
            bad.append(f"master {d['master']} no está en nodes")
        missing = level_nodes.get(d["level"], set()) - set(d["nodes"])
        if missing:
            bad.append(f"nodos del nivel no incluidos: {sorted(missing)}")
        ok = not bad
        ok_all = ok_all and ok
        per.append({"diaphragm": d["id"], "level": d["level"],
                    "n_nodos": len(d["nodes"]), "ok": ok, "problemas": bad})
    return _result("compatibilidad_diafragma", ok_all, per)


def run_all(model):
    return [
        check_total_load(model),
        check_tributary_area_sum(model),
        check_load_conservation(model),
        check_global_equilibrium(model),
        check_diaphragm_compatibility(model),
    ]


def make_summary(model):
    kinds = {}
    for e in model["elements"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    slabs_area = {}
    for s in model["slabs"]:
        slabs_area[s["level"]] = slabs_area.get(s["level"], 0.0) + polygon_area(s["polygon"])
    cases = model["load_cases"]
    lines = ["=== RESUMEN DEL MODELO ==="]
    lines.append("Nodos: %d | Elementos: %d | Columnas: %d | Vigas+muros: %d | Losas: %d | Areas tributarias: %d | Apoyos: %d"
                 % (len(model["nodes"]), len(model["elements"]),
                    kinds.get("column", 0), kinds.get("beam", 0) + kinds.get("wall", 0),
                    len(model["slabs"]), len(model["tributary_areas"]),
                    len({r.get("node") for r in model["analysis"]["reactions"]})))
    lines.append("Niveles: %s" % ", ".join("%s=%.2f m" % (l["id"], l["elevation"]) for l in model["levels"]))
    lines.append("")
    lines.append("=== CARGAS POR PISO (q x area de losa) ===")
    header = "%-4s %10s %10s %10s %10s %10s" % ("Piso", "Area m2", "q_G kPa", "G kN", "q_Q kPa", "Q kN")
    lines.append(header)
    lines.append("-" * len(header))
    for s in model["slabs"]:
        area = polygon_area(s["polygon"])
        qg = s[cases["G"]["slab_field"]]
        qq = s[cases["Q"]["slab_field"]]
        lines.append("%-4s %10.1f %10.3f %10.1f %10.3f %10.1f" % (s["level"], area, qg, qg * area, qq, qq * area))
    for case in sorted(cases):
        applied = 0.0
        for t in model["tributary_areas"]:
            slab = next(x for x in model["slabs"] if x["id"] == t["slab"])
            applied -= t["area"] * slab[cases[case]["slab_field"]]
        reac = sum(r["rz"] for r in model["analysis"]["reactions"] if r.get("case") == case)
        lines.append("")
        lines.append("=== EQUILIBRIO %s ===" % case)
        lines.append("aplicada = %.1f kN | reacciones = %.1f kN" % (applied, reac))
    checks = run_all(model)
    ok = all(c["ok"] for c in checks)
    lines.append("")
    lines.append("".join("%s: %s  " % ("PASS" if c["ok"] else "FAIL", c["name"]) for c in checks))
    lines.append("RESULTADO GLOBAL: %s" % ("OK" if ok else "FALLAN CHECKS"))
    return "\n".join(lines)


def make_report(model):
    checks = run_all(model)
    ok_all = all(c["ok"] for c in checks)
    report = [f"{'PASS' if c['ok'] else 'FAIL'}  {c['name']}: {c['detail']}" for c in checks]
    report.append(f"RESULTADO GLOBAL: {'OK' if ok_all else 'FALLAN CHECKS'}")
    return "\n".join(report)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    path = args[0] if args else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "model_data.json")
    with open(path, encoding="utf-8") as fh:
        model = json.load(fh)
    if "--summary" in sys.argv[1:]:
        print(make_summary(model))
        sys.exit(0 if run_all(model) else 1)
    print(make_report(model))
    sys.exit(0 if all(c["ok"] for c in run_all(model)) else 1)