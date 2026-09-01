"""Validación estructural del contrato JSON data/model_data.json.

Devuelve una lista de errores de estructura (claves, referencias, unicidad,
positividad). No realiza verificación física (eso es verifications.py).
"""

REQUIRED_TOP = [
    "schema_version", "metadata", "materials", "sections", "levels",
    "nodes", "supports", "diaphragms", "elements", "slabs",
    "tributary_areas", "load_cases",
]


def polygon_area(poly):
    a = 0.0
    for k in range(len(poly)):
        x1, y1 = poly[k]
        x2, y2 = poly[(k + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def validate_model(model):
    errors = []

    for key in REQUIRED_TOP:
        if key not in model:
            errors.append(f"falta clave top-level: {key}")
    if errors:
        return errors

    ids = {}
    for kind in ("materials", "sections", "levels"):
        seen = set()
        for item in model.get(kind, []):
            if item.get("id") in seen:
                errors.append(f"{kind}: id duplicado {item.get('id')}")
            seen.add(item.get("id"))
        ids[kind] = seen

    seen_nodes = set()
    for n in model["nodes"]:
        tag = n.get("tag")
        if tag in seen_nodes:
            errors.append(f"nodo tag duplicado {tag}")
        seen_nodes.add(tag)
        for axis in ("x", "y", "z"):
            if not isinstance(n.get(axis), (int, float)):
                errors.append(f"nodo {tag}: {axis} no numérica")
        if n.get("level") not in ids["levels"]:
            errors.append(f"nodo {tag}: level desconocido {n.get('level')}")

    level_z = {l["id"]: l["elevation"] for l in model["levels"]}
    for n in model["nodes"]:
        z = n.get("z")
        if abs(z - level_z[n["level"]]) > 1e-9:
            errors.append(
                f"nodo {n.get('tag')}: z={z} no coincide con nivel "
                f"{n['level']} (elevación {level_z[n['level']]})")

    for s in model["sections"]:
        if s.get("material") not in ids["materials"]:
            errors.append(f"sección {s.get('id')}: material desconocido {s.get('material')}")

    for sup in model["supports"]:
        if sup.get("node") not in seen_nodes:
            errors.append(f"apoyo: nodo desconocido {sup.get('node')}")

    for d in model["diaphragms"]:
        if d.get("level") not in ids["levels"]:
            errors.append(f"diafragma {d.get('id')}: level desconocido {d.get('level')}")
        if d.get("master") not in seen_nodes:
            errors.append(f"diafragma {d.get('id')}: master desconocido {d.get('master')}")
        for t in d.get("nodes", []):
            if t not in seen_nodes:
                errors.append(f"diafragma {d.get('id')}: nodo desconocido {t}")

    seen_el = set()
    for e in model["elements"]:
        tag = e.get("tag")
        if tag in seen_el:
            errors.append(f"elemento tag duplicado {tag}")
        seen_el.add(tag)
        if e.get("kind") not in ("beam", "column", "wall"):
            errors.append(f"elemento {tag}: kind inválido {e.get('kind')}")
        if e.get("i") not in seen_nodes or e.get("j") not in seen_nodes:
            errors.append(f"elemento {tag}: nodos i/j desconocidos")
        if e.get("section") not in ids["sections"]:
            errors.append(f"elemento {tag}: sección desconocida {e.get('section')}")
        if e.get("level") not in ids["levels"]:
            errors.append(f"elemento {tag}: level desconocido {e.get('level')}")

    for s in model["slabs"]:
        if s.get("level") not in ids["levels"]:
            errors.append(f"losa {s.get('id')}: level desconocido {s.get('level')}")
        poly = s.get("polygon", [])
        if len(poly) < 3 or polygon_area(poly) <= 1e-9:
            errors.append(f"losa {s.get('id')}: polígono inválido o área cero")
        for field in ("qG", "qQ"):
            if not (isinstance(s.get(field), (int, float)) and s.get(field) >= 0):
                errors.append(f"losa {s.get('id')}: {field} inválido")

    seen_ta = set()
    for t in model["tributary_areas"]:
        if t.get("id") in seen_ta:
            errors.append(f"área tributaria id duplicado {t.get('id')}")
        seen_ta.add(t.get("id"))
        if t.get("element") not in seen_el:
            errors.append(f"área tributaria {t.get('id')}: elemento desconocido {t.get('element')}")
        if t.get("level") not in ids["levels"]:
            errors.append(f"área tributaria {t.get('id')}: level desconocido {t.get('level')}")
        if not (isinstance(t.get("area"), (int, float)) and t.get("area") > 0):
            errors.append(f"área tributaria {t.get('id')}: área inválida")
        slab_ids = {s["id"] for s in model["slabs"]}
        if t.get("slab") not in slab_ids:
            errors.append(f"área tributaria {t.get('id')}: losa desconocida {t.get('slab')}")
        if t.get("case") not in model["load_cases"]:
            errors.append(f"área tributaria {t.get('id')}: caso desconocido {t.get('case')}")

    return errors