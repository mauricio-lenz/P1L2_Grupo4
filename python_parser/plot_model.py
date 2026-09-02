import json
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


KIND_COLOR = {"column": "#3b82f6", "beam": "#94a3b8", "wall": "#22c55e"}
KIND_WIDTH = {"column": 2.5, "beam": 1.0, "wall": 1.8}
SLAB_ALPHA = 0.25
LEVEL_COLOR = {"N0": "#cbd5e1", "P1": "#60a5fa", "P2": "#22c55e", "P3": "#f59e0b"}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "data", "model_data.json")
    with open(path, encoding="utf-8") as f:
        model = json.load(f)

    out = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(out, exist_ok=True)

    nodes = {n["tag"]: n for n in model["nodes"]}

    fig = plt.figure(figsize=(14, 9), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")

    for e in model["elements"]:
        if e["i"] not in nodes or e["j"] not in nodes:
            continue
        a, b = nodes[e["i"]], nodes[e["j"]]
        col = KIND_COLOR.get(e["kind"], "#ffffff")
        lw = KIND_WIDTH.get(e["kind"], 1.0)
        ax.plot([a["x"], b["x"]], [a["y"], b["y"]], [a["z"], b["z"]],
                color=col, linewidth=lw, alpha=0.85)

    xs = [n["x"] for n in model["nodes"]]
    ys = [n["y"] for n in model["nodes"]]
    zs = [n["z"] for n in model["nodes"]]

    for s in model["slabs"]:
        z = next(l["elevation"] for l in model["levels"] if l["id"] == s["level"])
        verts = [[(p[0], p[1], z) for p in s["polygon"]]]
        col = LEVEL_COLOR.get(s["level"], "#ffffff")
        poly = Poly3DCollection(verts, alpha=SLAB_ALPHA, facecolor=col, edgecolor=col, linewidths=0.5)
        ax.add_collection3d(poly)

    ax.set_xlabel("X (m)", color="white", fontsize=9)
    ax.set_ylabel("Y (m)", color="white", fontsize=9)
    ax.set_zlabel("Z (m)", color="white", fontsize=9)
    ax.tick_params(colors="white", labelsize=7)
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor("#334155")
    ax.yaxis.pane.set_edgecolor("#334155")
    ax.zaxis.pane.set_edgecolor("#334155")

    for spine in ax.spines.values():
        spine.set_color("#334155")

    pad = 2
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_zlim(-0.5, max(zs) + pad)
    ax.set_box_aspect([max(xs) - min(xs), max(ys) - min(ys), max(zs) + 0.5])
    ax.view_init(elev=30, azim=-60)

    from matplotlib.lines import Line2D
    legend = [Line2D([0], [0], color=c, lw=2, label=k) for k, c in KIND_COLOR.items()]
    legend += [Line2D([0], [0], color=LEVEL_COLOR[l], lw=8, alpha=0.5, label=f"Losas {l}")
               for l in ["P1", "P2", "P3"]]
    ax.legend(handles=legend, loc="upper left", fontsize=8, facecolor="#1e293b", edgecolor="#475569", labelcolor="white")

    path_out = os.path.join(out, "model_plot.png")
    plt.tight_layout()
    fig.savefig(path_out, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(path_out)


if __name__ == "__main__":
    main()
