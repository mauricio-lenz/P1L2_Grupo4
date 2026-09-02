"""Inventario de todas las láminas DXF: cobertura, sectores y niveles.

Uso:
    python inventory_dxf.py [dir_dxf] > inventory.txt
"""

import os
import sys
from collections import Counter

import ezdxf

ROOT = sys.argv[1] if len(sys.argv) > 1 else "cad_files/dxf"


def geom_info(msp):
    xs, ys = [], []
    for e in msp:
        try:
            xs.append(e.dxf.start.x)
            ys.append(e.dxf.start.y)
            xs.append(e.dxf.end.x)
            ys.append(e.dxf.end.y)
        except Exception:
            pass
    if not xs:
        return None, None
    width = (max(xs) - min(xs)) / 1000.0
    height = (max(ys) - min(ys)) / 1000.0
    x0, x1 = min(xs) / 1000.0, max(xs) / 1000.0
    y0, y1 = min(ys) / 1000.0, max(ys) / 1000.0
    return (width, height, x0, x1, y0, y1)


def layer_counts(msp):
    counts = Counter()
    for e in msp:
        counts[e.dxf.layer] += 1
    return counts


def texts(msp, layers):
    out = Counter()
    for e in msp:
        if e.dxf.layer in layers and e.dxftype() in ("TEXT", "MTEXT"):
            v = (e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text).strip()
            for kw in ("PLANTA", "N.O.G.", "N.R.", "LOSA e", "NPT", "NIVEL"):
                if kw in v:
                    out[v] += 1
    return out


def main():
    seq = 0
    header = ("archivo | W[m] | H[m] | X[m] | Y[m] | ejes | vigas | pilares "
              "| muros | losa | nivel")
    print(header)
    print("-" * len(header))
    for rootdir, _dirs, files in sorted(os.walk(ROOT)):
        for f in sorted(files):
            if not f.lower().endswith((".dxf", ".dwg")):
                continue
            path = os.path.join(rootdir, f)
            try:
                doc = ezdxf.readfile(path)
                msp = doc.modelspace()
            except Exception as ex:
                print(f"{f:28s} ERROR {ex}")
                continue
            g = geom_info(msp)
            if not g[0]:
                continue
            c = layer_counts(msp)
            ejes = c.get("RLE-EJE", 0) + c.get("RLE-EJES", 0)
            nv = " ".join(f"{t}" for t, _ in texts(msp, {"RLE-NIVELES"}).most_common(3))
            seq += 1
            print(f"{f:28s} | {g[0]:4.2f} | {g[1]:4.2f} | "
                  f"{g[2]:5.2f}-{g[3]:5.2f} | {g[4]:5.2f}-{g[5]:5.2f} | "
                  f"{ejes:4d} | {c.get('RLE-VIGA', 0):4d} | {c.get('RLE-PILAR', 0):4d} "
                  f"| {c.get('RLE-MURO', 0):3d} | {c.get('RLE-LOSA', 0) + c.get('RLA-LOSAS', 0):4d} | {nv}")


if __name__ == "__main__":
    main()