"""Genera un modelo estructural sintético pequeño (stub) y consistente.

Usado como ejemplo oficial en data/model_data.json y como fixture de tests.
La geometría es una retícula 2x2 de 6x6 m con tres niveles (N0 base, P1, P2).

Asignación de áreas tributarias (triangulación por paño):
cada paño de losa aporta area/4 a cada una de sus 4 vigas de borde.
Por nivel: suma(areas tributarias) == area total de losa.
Conservación: F_G = q_G * area_tributaria.
"""

import json
import os

GRID = [0.0, 6.0, 12.0]
LEVELS = [
    {"id": "N0", "elevation": 0.0, "story_height": 3.5},
    {"id": "P1", "elevation": 3.5, "story_height": 3.5},
    {"id": "P2", "elevation": 7.0, "story_height": 3.5},
]
Q_G = 5.0
Q_Q = 3.0
SLAB_T = 0.15
LEN = 6.0
SLAB_LEVELS = ("P1", "P2")


def lev_index(lev):
    return next(i for i, l in enumerate(LEVELS) if l["id"] == lev)


def node_tag(ix, iy, lev):
    return lev_index(lev) * 9 + 1 + ix + 3 * iy


def node_coord(ix, iy, lev):
    lz = next(l["elevation"] for l in LEVELS if l["id"] == lev)
    return [GRID[ix], GRID[iy], lz]


def polygon_area(poly):
    a = 0.0
    for k in range(len(poly)):
        x1, y1 = poly[k]
        x2, y2 = poly[(k + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def build_stub_model():
    model = {
        "schema_version": "0.1.0",
        "metadata": {
            "title": "Stub edificio 2x2 para desarrollo y pruebas",
            "units": {"length": "m", "force": "kN", "pressure": "kPa"},
            "elevation_axis": "Z",
            "source_plans": [],
        },
        "materials": [
            {"id": "C25", "name": "Hormigon C25", "type": "concrete",
             "gamma": 25.0, "E": 25000000.0, "fc": 25000.0},
            {"id": "A630", "name": "Acero A630-420H", "type": "steel",
             "gamma": 78.5, "E": 200000000.0, "fy": 630000.0},
        ],
        "sections": [
            {"id": "C40x40", "shape": "rect", "b": 0.40, "h": 0.40,
             "material": "C25", "kinds": ["column"]},
            {"id": "V30x50", "shape": "rect", "b": 0.30, "h": 0.50,
             "material": "C25", "kinds": ["beam"]},
            {"id": "W20x200", "shape": "rect", "b": 0.20, "h": 2.00,
             "material": "C25", "kinds": ["wall"]},
        ],
        "levels": LEVELS,
        "nodes": [],
        "supports": [],
        "diaphragms": [],
        "elements": [],
        "slabs": [],
        "tributary_areas": [],
        "load_cases": {
            "G": {"description": "Gravedad: losa + terminaciones", "slab_field": "qG"},
            "Q": {"description": "Carga viva", "slab_field": "qQ"},
        },
        "analysis": {"reactions": []},
    }

    for lev in LEVELS:
        for iy in range(3):
            for ix in range(3):
                x, y, z = node_coord(ix, iy, lev["id"])
                model["nodes"].append({"tag": node_tag(ix, iy, lev["id"]),
                                       "x": x, "y": y, "z": z, "level": lev["id"]})

    for ix in range(3):
        for iy in range(3):
            model["supports"].append({
                "node": node_tag(ix, iy, "N0"),
                "ux": True, "uy": True, "uz": True, "rx": False, "ry": False, "rz": False,
            })

    for lvl in SLAB_LEVELS:
        master = node_tag(1, 1, lvl)
        model["diaphragms"].append({
            "id": f"diaf_{lvl}", "level": lvl, "master": master, "rigid": True,
            "nodes": [node_tag(ix, iy, lvl) for iy in range(3) for ix in range(3)],
        })

    tag = 1000
    for lvl in SLAB_LEVELS:
        for iy in range(3):
            for ix in range(3):
                i = node_tag(ix, iy, "N0" if lvl == "P1" else "P1")
                j = node_tag(ix, iy, lvl)
                model["elements"].append({
                    "tag": tag, "kind": "column", "i": i, "j": j,
                    "section": "C40x40", "level": lvl, "local_x": [1.0, 0.0, 0.0],
                })
                tag += 1

    for lvl in SLAB_LEVELS:
        for iy in range(3):
            for ix in range(2):
                model["elements"].append({
                    "tag": tag, "kind": "beam", "i": node_tag(ix, iy, lvl),
                    "j": node_tag(ix + 1, iy, lvl), "section": "V30x50",
                    "level": lvl, "local_x": [1.0, 0.0, 0.0],
                })
                tag += 1
        for ix in range(3):
            for iy in range(2):
                model["elements"].append({
                    "tag": tag, "kind": "beam", "i": node_tag(ix, iy, lvl),
                    "j": node_tag(ix, iy + 1, lvl), "section": "V30x50",
                    "level": lvl, "local_x": [0.0, 1.0, 0.0],
                })
                tag += 1

    for (ix, iy) in ((0, 0), (0, 2), (2, 0), (2, 2)):
        model["elements"].append({
            "tag": tag, "kind": "wall", "i": node_tag(ix, iy, "N0"),
            "j": node_tag(ix, iy, "P1"), "section": "W20x200", "level": "P1",
            "local_x": [0.0, 1.0, 0.0],
        })
        tag += 1

    for lvl in SLAB_LEVELS:
        for iy in range(2):
            for ix in range(2):
                x0, x1 = GRID[ix], GRID[ix + 1]
                y0, y1 = GRID[iy], GRID[iy + 1]
                model["slabs"].append({
                    "id": f"losa_{lvl}_{iy * 2 + ix + 1}", "level": lvl,
                    "polygon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                    "thickness": SLAB_T, "material": "C25",
                    "qG": Q_G, "qQ": Q_Q,
                })

    beam_lookup = {}
    for e in model["elements"]:
        beam_lookup[(e["level"], e["kind"], e["i"], e["j"])] = e["tag"]

    by_level_slab = {lvl: [s for s in model["slabs"] if s["level"] == lvl]
                     for lvl in SLAB_LEVELS}

    count = 0
    for lvl in SLAB_LEVELS:
        for iy in range(3):
            for ix in range(2):
                x0, x1 = GRID[ix], GRID[ix + 1]
                ya = GRID[iy]
                xm, hside = 0.5 * (x0 + x1), 0.5 * LEN
                e = beam_lookup[(lvl, "beam", node_tag(ix, iy, lvl),
                                 node_tag(ix + 1, iy, lvl))]
                if iy < 2:
                    count += 1
                    slab = f"losa_{lvl}_{iy * 2 + ix + 1}"
                    model["tributary_areas"].append({
                        "id": f"TA_{count}", "element": e, "slab": slab, "level": lvl,
                        "case": "G", "area": 0.5 * LEN * hside,
                        "polygon": [[x0, ya], [x1, ya], [xm, ya + hside]]})
                if iy > 0:
                    count += 1
                    slab = f"losa_{lvl}_{(iy - 1) * 2 + ix + 1}"
                    model["tributary_areas"].append({
                        "id": f"TA_{count}", "element": e, "slab": slab, "level": lvl,
                        "case": "G", "area": 0.5 * LEN * hside,
                        "polygon": [[x0, ya], [x1, ya], [xm, ya - hside]]})
        for ix in range(3):
            for iy in range(2):
                xa = GRID[ix]
                y0, y1 = GRID[iy], GRID[iy + 1]
                ym, hside = 0.5 * (y0 + y1), 0.5 * LEN
                e = beam_lookup[(lvl, "beam", node_tag(ix, iy, lvl),
                                 node_tag(ix, iy + 1, lvl))]
                if ix < 2:
                    count += 1
                    slab = f"losa_{lvl}_{iy * 2 + ix + 1}"
                    model["tributary_areas"].append({
                        "id": f"TA_{count}", "element": e, "slab": slab, "level": lvl,
                        "case": "G", "area": 0.5 * LEN * hside,
                        "polygon": [[xa, y0], [xa, y1], [xa + hside, ym]]})
                if ix > 0:
                    count += 1
                    slab = f"losa_{lvl}_{iy * 2 + (ix - 1) + 1}"
                    model["tributary_areas"].append({
                        "id": f"TA_{count}", "element": e, "slab": slab, "level": lvl,
                        "case": "G", "area": 0.5 * LEN * hside,
                        "polygon": [[xa, y0], [xa, y1], [xa - hside, ym]]})

    per_level_G = sum(Q_G * polygon_area(s["polygon"]) for lvl in SLAB_LEVELS
                      for s in by_level_slab[lvl]) / len(SLAB_LEVELS)
    per_level_Q = sum(Q_Q * polygon_area(s["polygon"]) for lvl in SLAB_LEVELS
                      for s in by_level_slab[lvl]) / len(SLAB_LEVELS)
    for (case, per_level) in (("G", per_level_G), ("Q", per_level_Q)):
        total = per_level * len(SLAB_LEVELS)
        per_support = round(total / 9.0, 12)
        for ix in range(3):
            for iy in range(3):
                model["analysis"]["reactions"].append({
                    "node": node_tag(ix, iy, "N0"), "case": case, "rz": per_support,
                })
    return model


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    m = build_stub_model()
    targets = [
        os.path.join(root, "data", "model_data.json"),
        os.path.join(here, "tests", "fixtures", "stub_model.json"),
    ]
    for p in targets:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(m, fh, indent=2)
        print("escrito:", p)
    print("nodos:", len(m["nodes"]), "elementos:", len(m["elements"]),
          "losas:", len(m["slabs"]), "areas tributarias:", len(m["tributary_areas"]))