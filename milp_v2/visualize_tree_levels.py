# visualize_tree_levels.py (only spacing changed)
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from collections import defaultdict, deque

def _node_level_layout(edges, all_nodes, root="i0"):
    level = {}
    if root in all_nodes:
        level[root] = 0
        q = deque([root])
        children = defaultdict(list)
        for u, v in edges:
            children[u].append(v)
        while q:
            u = q.popleft()
            for v in children.get(u, []):
                if v not in level:
                    level[v] = level[u] + 1
                    q.append(v)

    maxlvl = max(level.values(), default=0)
    for n in all_nodes:
        if n not in level:
            level[n] = maxlvl + 1

    per_level = defaultdict(list)
    for n, lv in level.items():
        per_level[lv].append(n)

    def keyfunc(n):
        if isinstance(n, str) and n.startswith("i") and n[1:].isdigit():
            return (0, int(n[1:]))
        if isinstance(n, str) and n.startswith("L") and n[1:].isdigit():
            return (1, int(n[1:]))
        return (2, n)

    order = {}
    for lv in per_level:
        per_level[lv].sort(key=keyfunc)
        for idx, n in enumerate(per_level[lv]):
            order[n] = idx

    return level, order, per_level

def visualize_tree_levels(
    lam, tau, I, P, L, filename="milp_tree_levels.png", tol=1e-6, root_index=0,
    hspace=2.0, vspace=1.6  # <<< spacing knobs (was effectively 1.0, 1.0)
):
    G = nx.MultiDiGraph()

    all_nodes = set()
    for i in I:
        active = [f"p{p}:{lam[i, p].X:.2f}" for p in P if lam[i, p].X > tol]
        label = f"i{i}" if not active else f"i{i}\n" + ", ".join(active)
        node_id = f"i{i}"
        G.add_node(node_id, label=label, color="skyblue")
        all_nodes.add(node_id)

    for lid, lbl in L.items():
        G.add_node(lid, label=f"{lid}\n{lbl}", color="lightgreen")
        all_nodes.add(lid)

    edges = []
    for (i, c, j), var in tau.items():
        val = float(getattr(var, "X", 0.0))
        if val > tol:
            src = f"i{i}"
            dst = f"i{j}" if isinstance(j, int) else j
            if dst not in G:
                G.add_node(dst, label=dst, color="lightgray")
            edges.append((src, dst, c, val))
            all_nodes.add(src); all_nodes.add(dst)
            G.add_edge(src, dst, c=c, val=val)

    root = f"i{root_index}"
    simple_edges = [(u, v) for (u, v, _c, _val) in edges]
    level, order, per_level = _node_level_layout(simple_edges, all_nodes, root=root)

    # --- spaced coordinates ---
    pos = {}
    for lv, nodes in per_level.items():
        n = len(nodes)
        if n == 1:
            xs = [0.0]
        else:
            xs = [ (i - (n-1)/2) * hspace for i in range(n) ]  # wider horizontally
        for idx, name in enumerate(nodes):
            pos[name] = (xs[idx], -lv * vspace)  # taller vertically

    # colors/legend the same as before
    n_edges = len(edges)
    cmap = plt.cm.get_cmap("tab20", n_edges) if n_edges <= 20 else plt.cm.get_cmap("hsv", n_edges)

    pair2idxs = {}
    for k, (u, v, c, val) in enumerate(edges):
        pair2idxs.setdefault((u, v), []).append(k)

    def radii_for(k):
        if k == 1: return [0.0]
        span = 0.35
        step = span / max(k - 1, 1)
        start = -span / 2
        return [start + i * step for i in range(k)]

    legend_handles = []
    for (u, v), idxs in pair2idxs.items():
        rads = radii_for(len(idxs))
        for j, idx in enumerate(idxs):
            src, dst, c, val = edges[idx]
            color = cmap(idx)
            nx.draw_networkx_edges(
                G, pos, edgelist=[(src, dst)], edge_color=[color],
                width=1.2 + 3.0 * val, arrows=True, arrowsize=14,
                connectionstyle=f"arc3,rad={rads[j]}",
                min_source_margin=12, min_target_margin=12
            )
            legend_handles.append(Line2D([0], [0], color=color, lw=3,
                                         label=f"{src} — c{c} → {dst} (τ={val:.2f})"))

    node_colors = [G.nodes[n].get("color", "lightgray") for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=1500, node_color=node_colors)
    nx.draw_networkx_labels(G, pos, labels=nx.get_node_attributes(G, "label"), font_size=8)

    if legend_handles:
        plt.legend(handles=legend_handles, loc="center left",
                   bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0, fontsize=8)

    plt.axis("off")
    plt.tight_layout()
    plt.savefig(filename, dpi=800, bbox_inches="tight")
    plt.close()
    print(f"Saved hierarchical tree visualization to {filename}")
