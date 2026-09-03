"""Ensambla el modelo estructural 3D completo desde plantas DXF (2017_67).

Por nivel (P1/P2/P3):
  - nodos = retícula x (columna o extremo de viga/muro), snap a ejes
  - columnas = cada columna conecta nivel → nivel inferior (base N0)
  - vigas/muros = tramo entre nodos consecutivos con evidencia (líneas)
  - losa = footprint del nivel; qG/qQ reales desde 2017_67-700 (PLANTA CIELO)
  - áreas tributarias = por paño de retícula, triángulo al borde (fallback viga más cercana)
  - reacciones = total por caso repartido en apoyos base

Uso:
    python assemble_model.py [--out data/model_data.json]
"""

import argparse
import json
import os
import re

from parse_dxf import extract_floor, SCALE_CM_TO_M

SNAP_TOL_M = 0.75
EVID_TOL_M = 0.80
OVERLAP_MIN = 0.50

MAT_H = {"id": "C25", "name": "Hormigon C25", "type": "concrete",
         "gamma": 25.0, "E": 25000000.0, "fc": 25000.0}
# Cargas del 2017_67-700 (PLANTA CIELO, rótulos HATCH CARGAS); kg/m2 -> kPa (*9.80665/1000)
#   PP. LOSA = e(m)x2500 Kg/m2 (e=0.15 -> 375 kg/m2 -> 3.678 kPa)
#   PM. ADIC. tipico 260 kg/m2 -> 2.550 kPa  |  SC tipico 300 kg/m2 -> 2.942 kPa
G_LOADS_KG = {"E": 0.15, "PM_ADIC": 260.0, "SC": 300.0}
_KG2KPA = 9.80665 / 1000.0
LOADS = {}
for _lvl in ("S2", "S1", "P1", "P2", "P3", "A"):
    qg = (G_LOADS_KG["E"] * 2500.0 + G_LOADS_KG["PM_ADIC"]) * _KG2KPA
    LOADS[_lvl] = {"qG": round(qg, 3), "qQ": round(G_LOADS_KG["SC"] * _KG2KPA, 3)}

LEVELS = [
    {"id": "S2", "elevation": -8.42, "story_height": 0.0},
    {"id": "S1", "elevation": -4.01, "story_height": 4.41},
    {"id": "P1", "elevation": -0.05, "story_height": 3.96},
    {"id": "P2", "elevation": 3.91, "story_height": 3.96},
    {"id": "P3", "elevation": 7.87, "story_height": 3.96},
    {"id": "A", "elevation": 11.83, "story_height": 3.96},
]
# PLANS: (ruta_dxf, [indices de LEVELS a los que sirve], indice base)
PLANS = [
    ("cad_files/dxf/2017_67/2017_67-100.dxf", [0], 0),        # S2 <- fundaciones/subterraneo
    ("cad_files/dxf/2017_67/2017_67-101.dxf", [1, 2], 0),     # S1 y P1 comparten huella
    ("cad_files/dxf/2017_67/2017_67-102.dxf", [3, 4], 1),     # P2 y P3
    ("cad_files/dxf/2017_67/2017_67-103.dxf", [5], 2),        # Azotea (techo sobre P3)
]

# VOLADIZOS: NO existen. La losa no sobresale de la retícula de columnas en los
# planos; el intento previo de extender la losa con CANTILEVER generó voladizos
# inexistentes y diagonales falsas en el frame implícito. Se retira por completo.

P_COL = re.compile(r"(\d+)\s*[xX]\s*(\d+)")
P_BEAM = re.compile(r"(\d+)\s*/\s*(\d+)")
P_WALL = re.compile(r"e\s*=\s*(\d+)")


def ntag(lev, xi, yj):
    return lev * 1_000_000 + xi * 1000 + yj


def _poly_area(poly):
    s = 0.0
    for k in range(len(poly)):
        x1, y1 = poly[k]
        x2, y2 = poly[(k + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def snap_i(v, axis, tol=SNAP_TOL_M):
    best = min(range(len(axis)), key=lambda k: abs(axis[k] - v))
    return best if abs(axis[best] - v) <= tol else None


def overlap_cm(ev, a, b, fix):
    """ev (cm): ¿cubre [a,b] en eje fijo (ambos en cm) con >= OVERLAP_MIN?"""
    x1, y1, x2, y2 = ev
    if abs(y1 - y2) <= 1e-6 and abs(y1 - fix) <= EVID_TOL_M * 100:
        lo, hi = max(a, min(x1, x2)), min(b, max(x1, x2))
        return hi - lo >= OVERLAP_MIN * max(b - a, 1e-9)
    if abs(x1 - x2) <= 1e-6 and abs(x1 - fix) <= EVID_TOL_M * 100:
        lo, hi = max(a, min(y1, y2)), min(b, max(y1, y2))
        return hi - lo >= OVERLAP_MIN * max(b - a, 1e-9)
    return False


def load_labels(doc):
    out = []
    for e in doc.modelspace():
        if e.dxf.layer not in ("RLE-TEXTO-1", "RLA-TEXTOS1"):
            continue
        if e.dxftype() not in ("TEXT", "MTEXT"):
            continue
        val = e.plain_text().strip() if e.dxftype() == "MTEXT" else e.dxf.text.strip()
        if not val:
            continue
        ip = e.dxf.insert
        out.append((ip.x, ip.y, val))
    return out


def nearest_label(labels, pattern, xm, ym, max_d=3.0):
    best, bd = None, max_d
    for (tx, ty, val) in labels:
        m = pattern.search(val)
        if not m:
            continue
        d = ((tx - xm) ** 2 + (ty - ym) ** 2) ** 0.5 * SCALE_CM_TO_M
        if d < bd:
            best, bd = m, d
    return best


def build_floor(path, lev):
    floor = extract_floor(path)
    doc = floor.pop("_doc", None)
    labels = load_labels(doc) if doc else []
    doc = None
    xs = [v * SCALE_CM_TO_M for v in floor["xs"]]
    ys = [v * SCALE_CM_TO_M for v in floor["ys"]]
    cols = [(x * SCALE_CM_TO_M, y * SCALE_CM_TO_M, b * SCALE_CM_TO_M, h * SCALE_CM_TO_M)
            for (x, y, b, h) in floor["columns"]]
    beams = floor["beams"]   # cm
    walls = [w for w in floor["walls"] if abs(w[1] - w[3]) < 0.5 or abs(w[0] - w[2]) < 0.5]

    col_nodes = {}
    for (x, y, b, h) in cols:
        xi, yj = snap_i(x, xs), snap_i(y, ys)
        if xi is None or yj is None:
            continue
        prev = col_nodes.get((xi, yj))
        col_nodes[(xi, yj)] = (max(prev, (b, h)) if prev else (b, h))

    end_nodes = set()
    for (x1c, y1c, x2c, y2c) in beams:
        for (x, y) in ((x1c * SCALE_CM_TO_M, y1c * SCALE_CM_TO_M),
                       (x2c * SCALE_CM_TO_M, y2c * SCALE_CM_TO_M)):
            xi, yj = snap_i(x, xs), snap_i(y, ys)
            if xi is not None and yj is not None:
                end_nodes.add((xi, yj))

    def has_node(xi, yj):
        return (xi, yj) in col_nodes or (xi, yj) in end_nodes

    spans = []  # (kind, xi0, yj0, xi1, yj1)
    # filas (ejes horizontales: y = ys[yj])
    for yj in range(len(ys)):
        for xi in range(len(xs) - 1):
            if not (has_node(xi, yj) and has_node(xi + 1, yj)):
                continue
            a = xs[xi] * 100
            b = xs[xi + 1] * 100
            fix = ys[yj] * 100
            ev = any(overlap_cm(e, a, b, fix) for e in beams)
            evw = any(overlap_cm(e, a, b, fix) for e in walls)
            if ev:
                spans.append(("beam", xi, yj, xi + 1, yj))
            if evw:
                spans.append(("wall", xi, yj, xi + 1, yj))
    # columnas (ejes verticales: x = xs[xi])
    for xi in range(len(xs)):
        for yj in range(len(ys) - 1):
            if not (has_node(xi, yj) and has_node(xi, yj + 1)):
                continue
            a = ys[yj] * 100
            b = ys[yj + 1] * 100
            fix = xs[xi] * 100
            ev = any(overlap_cm(e, a, b, fix) for e in beams)
            evw = any(overlap_cm(e, a, b, fix) for e in walls)
            if ev:
                spans.append(("beam", xi, yj, xi, yj + 1))
            if evw:
                spans.append(("wall", xi, yj, xi, yj + 1))

    used = set(col_nodes)
    for (k, x0, y0, x1, y1) in spans:
        used.add((x0, y0))
        used.add((x1, y1))
    node_ids = sorted(used)
    node_xy = {key: (xs[key[0]], ys[key[1]]) for key in node_ids}

    # secciones por rótulo cercano
    def dims_for(kind, pos):
        xm, ym = pos
        if kind == "beam":
            m = nearest_label(labels, P_BEAM, xm, ym)
            return (float(m.group(1)) / 100.0, float(m.group(2)) / 100.0) if m else (0.30, 0.50)
        if kind == "wall":
            m = nearest_label(labels, P_WALL, xm, ym)
            t = float(m.group(1)) / 100.0 if m else 0.20
            return (t, 2.0)
        m = nearest_label(labels, P_COL, xm, ym)
        return (float(m.group(1)) / 100.0, float(m.group(2)) / 100.0) if m else (0.40, 0.40)

    return {"lev": lev, "xs": xs, "ys": ys, "node_ids": node_ids,
            "node_xy": node_xy, "col_nodes": col_nodes, "spans": spans,
            "slab_t": (floor["slab_thickness_cm"] or 15) / 100.0,
            "labels": labels, "dims_for": dims_for}


def main(out_path):
    # Cada plano estructural ("planta cielo") puede dibujar varias losas/niveles
    # (p.ej. -101 dibuja S1 y P1). Generamos la geometria una vez con el nivel de
    # plantilla (levels[0]) y la expandimos a los niveles restantes del mismo plano.
    floors = [(build_floor(path, levels[0]), levels) for path, levels, _base in PLANS]
    level_idx_e = {l["id"]: k for k, l in enumerate(LEVELS)}

    # secciones únicas
    sec_pool = {}
    def sec_id(kind, b, h):
        key = (kind, round(b, 4), round(h, 4))
        if key not in sec_pool:
            if kind == "wall":
                sid = f"W{int(b * 100)}x{int(h * 100)}"
            elif kind == "beam":
                sid = f"V{int(b * 100)}x{int(h * 100)}"
            else:
                sid = f"C{int(b * 100)}x{int(h * 100)}"
            sec_pool[key] = sid
        return sec_pool[key]

    # elementos con sección (una geometría por plano, expandida a sus niveles)
    elements = []
    tag = 1000
    for fidx, (fl, levs) in enumerate(floors):
        base = PLANS[fidx][2]
        for lev in levs:
            for (xi, yj) in sorted(fl["col_nodes"]):
                b, h = fl["dims_for"]("col", (fl["xs"][xi], fl["ys"][yj]))
                elements.append({"tag": tag, "kind": "column",
                                 "i": ntag(base, xi, yj), "j": ntag(lev, xi, yj),
                                 "section": sec_id("col", b, h), "level": LEVELS[lev]["id"],
                                 "local_x": [0.0, 0.0, 1.0]})
                tag += 1
            for (kind, x0, y0, x1, y1) in fl["spans"]:
                xm = 0.5 * (fl["node_xy"][(x0, y0)][0] + fl["node_xy"][(x1, y1)][0])
                ym = 0.5 * (fl["node_xy"][(x0, y0)][1] + fl["node_xy"][(x1, y1)][1])
                b, h = fl["dims_for"](kind, (xm, ym))
                elements.append({"tag": tag, "kind": kind,
                                 "i": ntag(lev, x0, y0), "j": ntag(lev, x1, y1),
                                 "section": sec_id(kind, b, h), "level": LEVELS[lev]["id"],
                                 "local_x": [1.0, 0.0, 0.0]})
                tag += 1
    elements.sort(key=lambda x: x["tag"])

    # nodos: por cada nivel de cada plano (misma XY, cota del nivel)
    node_map = {}
    for fl, levs in floors:
        for lev in levs:
            for (xi, yj) in fl["node_ids"]:
                x, y = fl["node_xy"][(xi, yj)]
                node_map[ntag(lev, xi, yj)] = {"tag": ntag(lev, xi, yj), "x": x, "y": y,
                                               "z": LEVELS[lev]["elevation"],
                                               "level": LEVELS[lev]["id"]}
    for e in elements:
        if e["kind"] == "column" and e["i"] not in node_map:
            src = node_map[e["j"]]
            bid = level_idx_e[e["level"]] - 1
            node_map[e["i"]] = {"tag": e["i"], "x": src["x"], "y": src["y"],
                                "z": LEVELS[bid]["elevation"], "level": LEVELS[bid]["id"]}
    model_nodes = [node_map[k] for k in sorted(node_map)]

    # vigas implícitas de marco: en cada nivel, conectar nodos del MISMO nivel que
    # comparten una línea recta exacta (misma coordenada Y -> horizontal; misma
    # coordenada X -> vertical) y que son CONSECUTIVOS (sin otro nodo intermedio entre
    # ellos), SOLO si no hay viga/muro por evidencia. La agrupación se hace por
    # coordenada real (no por índice de tag) y se verifica que el tramo sea recto y sin
    # nodos entre medias, de modo que NUNCA se generan diagonales ni tramos cruzados.
    # Completa la grilla de pórticos del stub sin inventar vigas inexistentes.
    occupied = set()
    for e in elements:
        if e["kind"] in ("beam", "wall"):
            occupied.add((e["i"], e["j"]))
            occupied.add((e["j"], e["i"]))
    tag = max(e["tag"] for e in elements) + 1
    for fl, levs in floors:
        for lev in levs:
            if lev == 0:
                continue
            lvl = LEVELS[lev]["id"]
            nodes_lvl = [(tag_id, n["x"], n["y"])
                         for tag_id, n in node_map.items() if n["level"] == lvl]
            rows = {}  # y exacta -> [(x, tag)]
            cols = {}  # x exacta -> [(y, tag)]
            for tid, x, y in nodes_lvl:
                rows.setdefault(round(y, 6), []).append((x, tid))
                cols.setdefault(round(x, 6), []).append((y, tid))
            for lst in rows.values():
                lst.sort()
                for (xa, ia), (xb, ib) in zip(lst, lst[1:]):
                    # tramo horizontal real y sin nodos intermedios
                    if abs(xa - xb) < 0.01:
                        continue
                    if any(xa < xm < xb for xm, _ in lst):
                        continue
                    if (ia, ib) in occupied:
                        continue
                    ni, nj = node_map[ia], node_map[ib]
                    xm = 0.5 * (ni["x"] + nj["x"])
                    ym = 0.5 * (ni["y"] + nj["y"])
                    b, h = fl["dims_for"]("beam", (xm, ym))
                    elements.append({"tag": tag, "kind": "beam",
                                     "i": ia, "j": ib,
                                     "section": sec_id("beam", b, h),
                                     "level": lvl,
                                     "local_x": [1.0, 0.0, 0.0]})
                    occupied.add((ia, ib))
                    occupied.add((ib, ia))
                    tag += 1
            for lst in cols.values():
                lst.sort()
                for (ya, ia), (yb, ib) in zip(lst, lst[1:]):
                    # tramo vertical real y sin nodos intermedios
                    if abs(ya - yb) < 0.01:
                        continue
                    if any(ya < ym < yb for ym, _ in lst):
                        continue
                    if (ia, ib) in occupied:
                        continue
                    ni, nj = node_map[ia], node_map[ib]
                    xm = 0.5 * (ni["x"] + nj["x"])
                    ym = 0.5 * (ni["y"] + nj["y"])
                    b, h = fl["dims_for"]("beam", (xm, ym))
                    elements.append({"tag": tag, "kind": "beam",
                                     "i": ia, "j": ib,
                                     "section": sec_id("beam", b, h),
                                     "level": lvl,
                                     "local_x": [1.0, 0.0, 0.0]})
                    occupied.add((ia, ib))
                    occupied.add((ib, ia))
                    tag += 1
    elements.sort(key=lambda x: x["tag"])

    # apoyos (base = nivel inferior S2): solo donde hay columna o muro que nace/termina,
    # para no dejar "bloques naranjos" en nodos huecos de la retícula.
    supports_lvl = LEVELS[0]["id"]
    sup_lvl_nodes = {n["tag"] for n in model_nodes if n["level"] == supports_lvl}
    col_bases = {e["j"] for e in elements if e["kind"] == "column"} | \
                {e["i"] for e in elements if e["kind"] == "column"}
    wall_ends = {e["i"] for e in elements if e["kind"] == "wall"} | \
                {e["j"] for e in elements if e["kind"] == "wall"}
    # nodos base de columnas que estan en S2 (i del column) o extremos de muro en S2
    supported = set()
    for e in elements:
        if e["kind"] == "column" and e["i"] in sup_lvl_nodes:
            supported.add(e["i"])
        elif e["kind"] == "wall" and e["i"] in sup_lvl_nodes:
            supported.add(e["i"])
            supported.add(e["j"])
    supports = [{"node": n, "ux": True, "uy": True, "uz": True,
                 "rx": False, "ry": False, "rz": False}
                for n in supported]
    diaphragms = []
    for lev in range(1, len(LEVELS)):
        lv = LEVELS[lev]["id"]
        nods = sorted(k for k, n in node_map.items() if n["level"] == lv)
        if not nods:
            continue
        diaphragms.append({"id": f"diaf_{lv}", "level": lv, "master": nods[0],
                           "rigid": True, "nodes": nods})
    slabs = []
    for fl, levs in floors:
        x0, x1 = min(fl["xs"]), max(fl["xs"])
        y0, y1 = min(fl["ys"]), max(fl["ys"])
        for lev in levs:
            lv = LEVELS[lev]["id"]
            slabs.append({"id": f"losa_{lv}", "level": lv,
                          "polygon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                          "thickness": fl["slab_t"], "material": "C25",
                          "qG": LOADS[lv]["qG"], "qQ": LOADS[lv]["qQ"]})

    # áreas tributarias: por paño de retícula, triángulo a cada viga de borde
    # (fallback: viga más cercana si el borde no tiene viga). Conserva por construcción.
    elem_by_span = {}
    elem_pos = {}
    for e in elements:
        elem_by_span[(e["kind"], e["i"], e["j"])] = e["tag"]
        elem_by_span[(e["kind"], e["j"], e["i"])] = e["tag"]
        if e["kind"] == "beam":
            node_j = node_map[e["j"]]
            node_i = node_map[e["i"]]
            elem_pos[e["tag"]] = (0.5 * (node_i["x"] + node_j["x"]),
                                  0.5 * (node_i["y"] + node_j["y"]))
    trib = []
    count = 0
    for fl, levs in floors:
        x0, x1 = min(fl["xs"]), max(fl["xs"])
        y0, y1 = min(fl["ys"]), max(fl["ys"])
        for lev in levs:
            lv = LEVELS[lev]["id"]
            beams_lvl = [e["tag"] for e in elements
                         if e["kind"] == "beam" and e["level"] == lv]
            if not beams_lvl:
                continue
            for iy in range(len(fl["ys"]) - 1):
                for ix in range(len(fl["xs"]) - 1):
                    xa, xb = fl["xs"][ix], fl["xs"][ix + 1]
                    ya, yb = fl["ys"][iy], fl["ys"][iy + 1]
                    xm, ym = 0.5 * (xa + xb), 0.5 * (ya + yb)
                    bl = (xa, ya)
                    br = (xb, ya)
                    tr = (xb, yb)
                    tl = (xa, yb)
                    edges = []
                    edges.append(((ix, iy), (ix + 1, iy), ntag(lev, ix, iy),
                                 ntag(lev, ix + 1, iy)))
                    edges.append(((ix, iy + 1), (ix + 1, iy + 1), ntag(lev, ix, iy + 1),
                                 ntag(lev, ix + 1, iy + 1)))
                    edges.append(((ix, iy), (ix, iy + 1), ntag(lev, ix, iy),
                                 ntag(lev, ix, iy + 1)))
                    edges.append(((ix + 1, iy), (ix + 1, iy + 1), ntag(lev, ix + 1, iy),
                                 ntag(lev, ix + 1, iy + 1)))
                    tris = [[bl, br, [xm, ym]], [tl, tr, [xm, ym]],
                            [bl, tl, [xm, ym]], [br, tr, [xm, ym]]]
                    for (pa, pb, i, j), tri in zip(edges, tris):
                        tag = elem_by_span.get(("beam", i, j))
                        if tag is None:
                            cx, cy = tri[2]
                            tag = min(beams_lvl, key=lambda t: (elem_pos[t][0] - cx) ** 2
                                      + (elem_pos[t][1] - cy) ** 2)
                        A = _poly_area(tri)
                        count += 1
                        trib.append({"id": f"TA_{count}", "element": tag,
                                     "slab": f"losa_{lv}", "level": lv, "case": "G",
                                     "area": A, "polygon": tri})

    sections = []
    for (kind, b, h), sid in sec_pool.items():
        sections.append({"id": sid, "shape": "rect", "b": b, "h": h,
                         "material": "C25",
                         "kinds": [{"col": "column"}.get(kind, kind)]})

    model = {
        "schema_version": "0.1.0",
        "metadata": {
            "title": "Edificio Ingenieria UAndes - estructura 3D desde planos DXF",
            "units": {"length": "m", "force": "kN", "pressure": "kPa"},
            "elevation_axis": "Z",
            "source_plans": [os.path.basename(p) for p, _, _ in PLANS],
            "drawing_units": "cm",
            "notes_todo": ["zonas especiales de -700 fuera de rango tipico: SC=800 (4? piso),",
                           "PM.ADIC.=2800 (zona pesada), cargas puntuales de equipo 6700-13000 kg",
                           "elevaciones N.O.G. a confirmar en la defensa"],
        },
        "materials": [MAT_H],
        "sections": sections,
        "levels": LEVELS,
        "nodes": model_nodes,
        "supports": supports,
        "diaphragms": diaphragms,
        "elements": elements,
        "slabs": slabs,
        "tributary_areas": trib,
        "load_cases": {
            "G": {"description": "Gravedad: losa + terminaciones", "slab_field": "qG"},
            "Q": {"description": "Carga viva", "slab_field": "qQ"},
        },
        "analysis": {"reactions": []},
    }

    total = {"G": sum(s["qG"] * _poly_area(s["polygon"]) for s in slabs),
             "Q": sum(s["qQ"] * _poly_area(s["polygon"]) for s in slabs)}
    sup = [s["node"] for s in supports]
    for n in sup:
        for case in ("G", "Q"):
            model["analysis"]["reactions"].append(
                {"node": n, "case": case, "rz": total[case] / len(sup)})

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(model, fh, indent=2)
    print("escrito:", out_path)
    print("nodos:", len(model["nodes"]), "elementos:", len(model["elements"]),
          "columnas:", sum(1 for e in elements if e["kind"] == "column"),
          "losas:", len(model["slabs"]), "areas:", len(model["tributary_areas"]),
          "apoyos:", len(model["supports"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data", "model_data.json"))
    args = ap.parse_args()
    main(args.out)