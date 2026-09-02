"""Parser de geometría estructural desde un plano DXF (una planta).

Unidades del dibujo: CM. SCALE_CM_TO_M = 0.01.

De cada planta se extraen:
  - retícula de ejes (RLE-EJES + burbujas RLE-EJE)
  - pilares (RLE-PILAR: rectángulos de 4 LINES -> centro + dim)
  - vigas (RLE-VIGA: pares de caras paralelas -> eje central)
  - muros (RLE-MURO: pares de caras -> eje + espesor)
  - espesores de losa (RLA-LOSAS: texto '15' = 15 cm)
  - niveles (RLE-NIVELES: N.O.G./N.R.)

El resultado de cada nivel es un FloorRaw listo para ensamblar el modelo JSON.
"""

import re
from collections import Counter, defaultdict

import ezdxf

SCALE_CM_TO_M = 0.01

GRID_TOL = 75.0      # tolerancia de agrupación de ejes (u = 0.75 m): funde jitter <1m, preserva retícula >=2.5 m
SEG_TOL = 20.0        # tolerancia de agrupación de segmentos (rects de pilares)
PAIR_TOL = 25.0       # matching de caras paralelas (muros/vigas)


def point(e, side):
    p = e.dxf.start if side == 0 else e.dxf.end
    return (p.x, p.y)


def read_layers(msp):
    layers = defaultdict(list)
    for e in msp:
        layers[e.dxf.layer].append(e)
    return layers


def cluster_axis(coord_list, tol=GRID_TOL):
    """Agrupa coordenadas próximas en una lista de valores representativos."""
    out = []
    for c in sorted(coord_list):
        found = False
        for i, v in enumerate(out):
            if abs(c - v) <= tol:
                out[i] = 0.5 * (v + c)
                found = True
                break
        if not found:
            out.append(c)
    return sorted(out)


def extract_grid(layers, cols, beams, walls):
    """Retícula desde líneas de evidencia (vigas/muros) + columnas.

    Líneas horizontales aportan su coordenada Y fija; verticales su X fija.
    Los extremos NO se usan para la retícula. RLE-EJES amplía el bbox.
    Devuelve (xs, ys) ordenadas en unidades (cm).
    """
    xs, ys = [], []
    for (x, y, b, h) in cols:
        xs.append(x)
        ys.append(y)
    for (x1, y1, x2, y2) in beams + walls:
        if y1 == y2:
            ys.append(y1)
        elif x1 == x2:
            xs.append(x1)
        else:
            xs.append(0.5 * (x1 + x2))
            ys.append(0.5 * (y1 + y2))
    xg = cluster_axis(xs)
    yg = cluster_axis(ys)
    ejex, ejey = [], []
    for e in layers.get("RLE-EJES", []):
        if e.dxftype() != "LINE":
            continue
        x1, y1 = e.dxf.start.x, e.dxf.start.y
        x2, y2 = e.dxf.end.x, e.dxf.end.y
        if abs(x1 - x2) < 0.5 and abs(y2 - y1) > 500:
            ejex.append(0.5 * (x1 + x2))
        elif abs(y1 - y2) < 0.5 and abs(x2 - x1) > 500:
            ejey.append(0.5 * (y1 + y2))
    xg = cluster_axis(xg + ejex)
    yg = cluster_axis(yg + ejey)
    return xg, yg


def union_find_clusters(segs, tol=SEG_TOL):
    """Agrupa segmentos cuyos extremos se tocan (rect que forman pilares)."""
    parent = list(range(len(segs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            for (ax, ay) in segs[i]:
                for (bx, by) in segs[j]:
                    if abs(ax - bx) <= tol and abs(ay - by) <= tol:
                        union(i, j)
                        break
                else:
                    continue
                break
    groups = defaultdict(list)
    for i, s in enumerate(segs):
        groups[find(i)].append(s)
    return list(groups.values())


def cluster_bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def extract_columns(layers):
    """Pilares del layer RLE-PILAR. Devuelve (x, y, b, h) en unidades (centro + lado)."""
    segs = [((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y))
            for e in layers.get("RLE-PILAR", []) if e.dxftype() == "LINE"]
    cols = []
    for grp in union_find_clusters(segs):
        pts = [p for s in grp for p in s]
        x0, y0, x1, y1 = cluster_bbox(pts)
        cols.append((0.5 * (x0 + x1), 0.5 * (y0 + y1), x1 - x0, y1 - y0))
    return cols


def raw_axisaligned(layer_segs, min_len=50.0):
    """Solo segmentos estrictamente horizontales o verticales (evidencia)."""
    out = []
    for (x1, y1, x2, y2) in layer_segs:
        if abs(y1 - y2) < 0.5 and abs(x2 - x1) >= min_len:
            out.append((x1, y1, x2, y2))  # horizontal (y fijo)
        elif abs(x1 - x2) < 0.5 and abs(y2 - y1) >= min_len:
            out.append((x1, y1, x2, y2))  # vertical (x fijo)
    return out


def extract_beams(layers):
    segs = [(e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y)
            for e in layers.get("RLE-VIGA", []) if e.dxftype() == "LINE"]
    return raw_axisaligned(segs)


def extract_walls(layers):
    segs = [(e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y)
            for e in layers.get("RLE-MURO", []) if e.dxftype() == "LINE"]
    return raw_axisaligned(segs, min_len=150.0)


def extract_slab_thickness(layers):
    """RLA-LOSAS: textos tipo '15' = espesor en cm (el más frecuente)."""
    counts = Counter()
    for e in layers.get("RLA-LOSAS", []):
        if e.dxftype() in ("TEXT", "MTEXT"):
            v = e.plain_text().strip() if e.dxftype() == "MTEXT" else e.dxf.text.strip()
            if v.isdigit() and 8 <= int(v) <= 60:
                counts[int(v)] += 1
    tl = counts.most_common(1)
    return (tl[0][0], tl[0][1]) if tl else (None, 0)


def extract_levels(layers):
    """RLE-NIVELES: textos de nivel -> lista (cota, etiqueta)."""
    out = []
    for e in layers.get("RLE-NIVELES", []):
        if e.dxftype() != "MTEXT":
            continue
        v = e.plain_text().strip()
        m = re.search(r"[Nn]\.?[OOG]?\.?[G]?\s*=\s*(-?\d+\.?\d*)", v)
        if m:
            out.append((float(m.group(1)), v))
    return out


def extract_floor(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    layers = read_layers(msp)
    cols = extract_columns(layers)
    beams = extract_beams(layers)
    walls = extract_walls(layers)
    xs, ys = extract_grid(layers, cols, beams, walls)
    thick, _ = extract_slab_thickness(layers)
    levels = extract_levels(layers)
    return {
        "xs": xs, "ys": ys,
        "columns": cols,
        "beams": beams,
        "walls": walls,
        "slab_thickness_cm": thick,
        "levels": levels,
        "scale_cm_to_m": SCALE_CM_TO_M,
        "_doc": doc,
    }


if __name__ == "__main__":
    import sys

    for p in sys.argv[1:]:
        f = extract_floor(p)
        print("==", p)
        print(f"  retícula: {len(f['xs'])} X x {len(f['ys'])} Y")
        print(f"  X: {[round(x*SCALE_CM_TO_M,2) for x in f['xs']]}")
        print(f"  Y: {[round(y*SCALE_CM_TO_M,2) for y in f['ys']]}")
        print(f"  pilares: {len(f['columns'])}")
        print(f"  vigas (lineas eje): {len(f['beams'])}")
        print(f"  muros (lineas eje): {len(f['walls'])}")
        print(f"  espesor losa (cm): {f['slab_thickness_cm']}")
        print(f"  niveles: {f['levels']}")