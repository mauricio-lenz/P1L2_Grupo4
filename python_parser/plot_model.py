import json
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


# Colores con buen contraste sobre fondo blanco.
KIND_COLOR = {"column": "#5b7dab", "beam": "#9aa84f", "wall": "#8a5fb8"}
KIND_WIDTH = {"column": 2.2, "beam": 1.0, "wall": 1.5}
SLAB_ALPHA = 0.30
# Subterraneos se dibujan como masa solida (base), niveles superiores como losas.
BASEMENT_LEVELS = {"S1", "S2"}
LEVEL_COLOR = {"S2": "#b08968", "S1": "#c19a6b", "P1": "#9fb8d9",
               "P2": "#a3c9a5", "P3": "#e0c287", "A": "#d4a6c3"}


def _build_figure(model):
    nodes = {n["tag"]: n for n in model["nodes"]}

    fig = plt.figure(figsize=(14, 9), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    for e in model["elements"]:
        if e["kind"] == "wall":
            continue  # sin "paredes": solo columnas + vigas + losas
        if e["i"] not in nodes or e["j"] not in nodes:
            continue
        a, b = nodes[e["i"]], nodes[e["j"]]
        col = KIND_COLOR.get(e["kind"], "#ffffff")
        lw = KIND_WIDTH.get(e["kind"], 1.0)
        ax.plot([a["x"], b["x"]], [a["y"], b["y"]], [a["z"], b["z"]],
                color=col, linewidth=lw, alpha=0.8)

    xs = [n["x"] for n in model["nodes"]]
    ys = [n["y"] for n in model["nodes"]]
    zs = [n["z"] for n in model["nodes"]]

    for s in model["slabs"]:
        z = next(l["elevation"] for l in model["levels"] if l["id"] == s["level"])
        col = LEVEL_COLOR.get(s["level"], "#ffffff")
        if s["level"] in BASEMENT_LEVELS:
            # masa solida: prisma desde la base del edificio hasta este nivel
            below = [l["elevation"] for l in model["levels"] if l["elevation"] < z]
            z0 = min(below) if below else min(l["elevation"] for l in model["levels"]) - 1.0
            poly = s["polygon"]
            walls = []
            for k in range(len(poly)):
                a = poly[k]
                b = poly[(k + 1) % len(poly)]
                walls.append([(a[0], a[1], z0), (b[0], b[1], z0),
                              (b[0], b[1], z), (a[0], a[1], z)])
            faces = [[(p[0], p[1], z0) for p in poly],
                     [(p[0], p[1], z) for p in poly]] + walls
            body = Poly3DCollection(faces, alpha=0.30, facecolor=col, edgecolor=col,
                                    linewidths=0.4)
            ax.add_collection3d(body)
        else:
            verts = [[(p[0], p[1], z) for p in s["polygon"]]]
            poly = Poly3DCollection(verts, alpha=SLAB_ALPHA, facecolor=col,
                                    edgecolor=col, linewidths=0.5)
            ax.add_collection3d(poly)

    ax.set_xlabel("X (m)", color="black", fontsize=9)
    ax.set_ylabel("Y (m)", color="black", fontsize=9)
    ax.set_zlabel("Z (m)", color="black", fontsize=9)
    ax.tick_params(colors="black", labelsize=7)
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor("#b0b0b0")
    ax.yaxis.pane.set_edgecolor("#b0b0b0")
    ax.zaxis.pane.set_edgecolor("#b0b0b0")

    for spine in ax.spines.values():
        spine.set_color("#b0b0b0")

    pad = 2
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    zmin = min([l["elevation"] for l in model["levels"]]) - 1.0
    ax.set_zlim(zmin, max(zs) + pad)
    ax.set_box_aspect([max(xs) - min(xs), max(ys) - min(ys), max(zs) - zmin])

    from matplotlib.lines import Line2D
    legend = [Line2D([0], [0], color=c, lw=2, label=k) for k, c in KIND_COLOR.items() if k != "wall"]
    legend += [Line2D([0], [0], color=LEVEL_COLOR[l], lw=8, alpha=0.6, label=f"Losa {l}")
               for l in ["S2", "S1", "P1", "P2", "P3", "A"]]
    ax.legend(handles=legend, loc="upper left", fontsize=8, facecolor="white",
              edgecolor="#c0c0c0", labelcolor="black")

    return fig, ax


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "data", "model_data.json")
    with open(path, encoding="utf-8") as f:
        model = json.load(f)

    out = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(out, exist_ok=True)

    # (archivo, elev, azim, descripción) — 4 ángulos: el general + 3 presets distintos
    VIEWS = [
        ("model_plot.png",                30, -60, "isometrica general"),
        ("model_plot_preset1_iso.png",    35,  45, "isometrica frontal-derecha"),
        ("model_plot_preset2_perfil.png", 10,  90, "perfil lateral (elev baja)"),
        ("model_plot_preset3_cenital.png", 65, 210, "cenital opuesta"),
    ]

    for fname, elev, azim, desc in VIEWS:
        fig, ax = _build_figure(model)
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(desc, color="white", fontsize=10)
        path_out = os.path.join(out, fname)
        plt.tight_layout()
        fig.savefig(path_out, facecolor=fig.get_facecolor())
        plt.close(fig)
        print(path_out)


if __name__ == "__main__":
    main()
