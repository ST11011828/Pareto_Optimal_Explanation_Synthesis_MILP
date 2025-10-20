import sys
import time
import os
import matplotlib.pyplot as plt
from plot_pareto_curve_v2 import find_new_pareto_points

C = 6
I_vals = [4]  # try [2,3,4,...] if you like

log_dir = "examples/wine/recursively/combined_runs"
os.makedirs(log_dir, exist_ok=True)

# Where to save combined plots
plot_dir = "examples/wine/recursively/pareto_curves_combined"
os.makedirs(plot_dir, exist_ok=True)

# Simple color cycle for overlay curves
colors = ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"]

for I in I_vals:
    log_file = os.path.join(log_dir, f"I{I}_C{C}.log")
    with open(log_file, 'w') as f:
        # redirect all prints into per-run log
        sys.stdout = f

        start_time = time.time()

        # Make a single figure to overlay all Pareto curves for this I
        fig, ax = plt.subplots()

        # 1) Root-only curve: lam at i=0 integer AND tau from i=0 integer
        root_color = colors[0]
        root_label = f"root (i0)"
        count =0
        result_root = find_new_pareto_points(
            I, C,
            co= count,
            int_lam_nodes={0},
            int_tau_sources={0},
            ax=ax,
            color=root_color,
            label=root_label
        )
        f.write(f"Root result (I={I}, C={C}): {result_root}\n")
        count = 1

        # finalize combined figure
        ax.set_xlabel("Correctness")
        ax.set_ylabel("Explainability")
        ax.legend()
        fig.tight_layout()
        out_path = os.path.join(plot_dir, f"combined_pareto_curve_I{I}_C{C}.png")
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        end_time = time.time()
        f.write(f"\nTotal time taken: {end_time - start_time} seconds\n")

        # restore stdout
        sys.stdout = sys.__stdout__
