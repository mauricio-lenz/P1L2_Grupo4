"""Inspección detallada de un plano DXF para decidir la estrategia del parser.

Uso:
    python inspect_plan.py path_plano.dxf [--layers RLE-VIGA,RLE-...]
"""

import sys
from collections import Counter

import ezdxf

INTEREST = ["RLE-EJE", "RLE-EJES", "RLE-PILAR", "RLE-VIGA", "RLE-MURO",
            "RLE-LOSA", "RLE-LOSAS", "RLA-LOSAS", "RLE-NIVELES", "RLE-FUNDACION",
            "RLE-SEGMENTOS1", "RLE-CORTES-ABATIDOS", "RLE-PROYECCION", "RLE-SOLID",
            "RLE-TEXTO-1", "RLE-TEXTOS-SM", "RLE-FE", "fe", "TEXTOS-SM"]


def fmt(v):
    if isinstance(v, (int, float)):
        return f"{v:.2f}"
    return str(v)


def dump_lines(es, layer, n=8):
    out = []
    for e in [x for x in es if x.dxftype() == "LINE"][:n]:
        s, t = e.dxf.start, e.dxf.end
        out.append(f"LINE ({fmt(s.x)},{fmt(s.y)},{fmt(s.z)}) -> "
                   f"({fmt(t.x)},{fmt(t.y)},{fmt(t.z)}) len={fmt((t - s).magnitude)}")
    return out


def dump_lwpolyline(es, layer, n=8):
    out = []
    for e in [x for x in es if x.dxftype() == "LWPOLYLINE"][:n]:
        pts = [(round(p[0], 2), round(p[1], 2)) for p in e.get_points("xy")]
        out.append(f"LWPOLYLINE n={len(pts)} pts={pts}")
    return out


def unique_texts(es, layer, n=40):
    texts = Counter()
    for e in es:
        if e.dxf.layer != layer:
            continue
        if e.dxftype() in ("TEXT", "MTEXT"):
            val = (e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text).strip()
            if val:
                texts[val] += 1
    return [f"'{t}' x{c}" for t, c in texts.most_common(n)]


def main(path, layers):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    header = doc.header
    insunits = header.get("$INSUNITS", None)
    print("archivo:", path)
    print("INSUNITS:", insunits, "(0=sin especificar, 6=m, 4=mm, 5=cm)")
    ext = header.get("$EXTMIN"), header.get("$EXTMAX")
    if ext[0]:
        print("EXTMIN:", ext[0], "EXTMAX:", ext[1])
    print("-" * 70)
    for layer in layers:
        ents = [e for e in msp if e.dxf.layer == layer]
        if not ents:
            print(f"[{layer}] vacío")
            continue
        kinds = Counter(e.dxftype() for e in ents)
        print(f"[{layer}] ({len(ents)}) tipos={dict(kinds)}")
        if layer in ("RLE-EJE", "RLE-EJES", "RLE-VIGA", "RLE-MURO", "RLE-LOSA",
                     "RLE-LOSAS", "RLE-FUNDACION", "RLE-SEGMENTOS1",
                     "RLE-CORTES-ABATIDOS", "RLE-PROYECCION", "RLE-SOLID",
                     "RLA-LOSAS"):
            for ln in dump_lines(ents, layer):
                print("   ", ln)
            for p in dump_lwpolyline(ents, layer):
                print("   ", p)
        if layer in ("RLE-NIVELES", "RLE-TEXTO-1", "RLE-TEXTOS-SM", "RLE-FE",
                     "fe", "TEXTOS-SM", "RLA-TEXTOS1", "RLE-REVISION 0"):
            for t in unique_texts(ents, layer):
                print("   TXT", t)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    layers = sys.argv[2].split(",") if len(sys.argv) > 2 else INTEREST
    main(path, layers)