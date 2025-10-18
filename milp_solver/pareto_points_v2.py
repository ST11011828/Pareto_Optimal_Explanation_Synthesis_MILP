import os
import csv
import matplotlib.pyplot as plt
import gurobipy as gp
from gurobipy import GRB

from inputs import Input
from encoding import Encoding

EPS = 1e-6  # tolerance used everywhere


def near_int(x, tol=EPS):
    return abs(x - round(x)) <= tol


class Pareto_Points:
    """
    - pareto_points: list[[c,e], ...]
    - inp: Input
    - int_pos: set[int]  (nodes whose lam/tau are integer)
    - root: int
    - encs: [Encoding, Encoding]  (independent models for the two walks)
    """

    def __init__(self, inp: Input, int_pos, root: int):
        self.inp = inp
        self.int_pos = set(int_pos)
        self.root = root

        # two independent encodings (each walk edits/solves its own model)
        self.encs = [
            Encoding(self.int_pos, self.inp, self.root),
            Encoding(self.int_pos, self.inp, self.root),
        ]
        self.pareto_points = []

    # ----- helpers -----
    def _solve_once_each(self):
        self.encs[0].solve()
        self.encs[1].solve()

    def _ensure_solution(self, enc: Encoding):
        m = enc.model
        if m.status == GRB.INFEASIBLE:
            return False
        if getattr(m, "SolCount", 0) == 0:
            enc.solve()
            if getattr(m, "SolCount", 0) == 0:
                return False
        return True

    def _current_hits(self, enc: Encoding) -> int:
        """sum_s m[root,s] from incumbent, rounded to int."""
        root, S = enc.root, enc.S
        val = sum(enc.m[root, s].X for s in S)
        return int(round(val))

    def _current_e_int(self, enc: Encoding) -> int:
        """explainability count from incumbent, rounded to int (robust to 7.999999)."""
        I, P = enc.I, enc.P
        val = 0.0
        # sum(1 - u[i]) + sum(weight[p] * o_u[i,p])
        val += sum(1.0 - enc.u[i].X for i in I)
        val += sum(enc.inp.predicates[p].weight * enc.o_u[i, p].X for i in I for p in P)
        return int(round(val))

    def _current_c_float(self, enc: Encoding) -> float:
        return float(enc.calculate_correctness())

    def _current_e_float(self, enc: Encoding) -> float:
        e = float(enc.calculate_explainability())
        return float(round(e)) if near_int(e) else e

    # ----- walks -----
    def find_pareto_solutions_more_e(self):
        """
        Increase explainability, decrease correctness.
        Commit successful ladder cuts so the next step builds on them.
        """
        print("Entering find pareto solutions more e")
        enc = self.encs[0]
        model = enc.model
        I, P, S = enc.I, enc.P, enc.S
        root = enc.root

        if not self._ensure_solution(enc):
            return

        steps = 0
        max_steps = len(S) + 100  # simple safety cap

        while steps < max_steps:
            if not self._ensure_solution(enc):
                break

            curr_hits = self._current_hits(enc)
            curr_e_int = self._current_e_int(enc)
            curr_c = self._current_c_float(enc)
            curr_e = self._current_e_float(enc)

            print(f"[more-e] baseline: hits={curr_hits}/{len(S)}  c={curr_c:.12f}  e={curr_e}")

            # trial ladder cuts (one rung): hits - 1, e + 1
            corr_cut = model.addConstr(
                gp.quicksum(enc.m[root, s] for s in S) <= (curr_hits - 1) + EPS
            )
            e_expr = (
                gp.quicksum(1 - enc.u[i] for i in I)
                + gp.quicksum(enc.inp.predicates[p].weight * enc.o_u[i, p] for i in I for p in P)
            )
            expl_cut = model.addConstr(e_expr >= (curr_e_int + 1) - EPS)

            model.update()
            model.optimize()

            feasible = model.status in (GRB.OPTIMAL, GRB.SUBOPTIMAL)
            if not feasible:
                # no progress possible; remove the trial pair and stop
                model.remove(corr_cut)
                model.remove(expl_cut)
                model.update()
                break

            # read new discrete rungs from the incumbent
            new_hits = self._current_hits(enc)
            new_e_int = self._current_e_int(enc)
            new_c = new_hits / float(len(S))
            new_e = self._current_e_float(enc)

            print(f"[more-e] trial:    hits={new_hits}/{len(S)}  c={new_c:.12f}  e={new_e}")

            improved = (new_hits == curr_hits - 1) and (new_e_int >= curr_e_int + 1)
            if improved:
                # COMMIT: keep these cuts to advance the baseline
                print(f"[more-e] ADD pareto point ({new_c}, {new_e})")
                self.pareto_points.append([new_c, new_e])
                steps += 1
                if new_hits <= 0:
                    break
                # do NOT remove cuts; continue to next rung
            else:
                # no strict +1/-1 improvement; back out this trial and stop
                model.remove(corr_cut)
                model.remove(expl_cut)
                model.update()
                break

    def find_pareto_solutions_more_c(self):
        """
        Increase correctness, decrease explainability.
        Commit successful ladder cuts so the next step builds on them.
        """
        print("Entering find pareto solutions more c")
        enc = self.encs[1]
        model = enc.model
        I, P, S = enc.I, enc.P, enc.S
        root = enc.root

        if not self._ensure_solution(enc):
            return

        steps = 0
        max_steps = len(S) + 100

        while steps < max_steps:
            if not self._ensure_solution(enc):
                break

            curr_hits = self._current_hits(enc)
            curr_e_int = self._current_e_int(enc)
            curr_c = self._current_c_float(enc)
            curr_e = self._current_e_float(enc)

            print(f"[more-c] baseline: hits={curr_hits}/{len(S)}  c={curr_c:.12f}  e={curr_e}")

            # trial ladder cuts (one rung): hits + 1, e - 1
            corr_cut = model.addConstr(
                gp.quicksum(enc.m[root, s] for s in S) >= (curr_hits + 1) - EPS
            )
            e_expr = (
                gp.quicksum(1 - enc.u[i] for i in I)
                + gp.quicksum(enc.inp.predicates[p].weight * enc.o_u[i, p] for i in I for p in P)
            )
            expl_cut = model.addConstr(e_expr <= (curr_e_int - 1) + EPS)

            model.update()
            model.optimize()

            feasible = model.status in (GRB.OPTIMAL, GRB.SUBOPTIMAL)
            if not feasible:
                model.remove(corr_cut)
                model.remove(expl_cut)
                model.update()
                break

            new_hits = self._current_hits(enc)
            new_e_int = self._current_e_int(enc)
            new_c = new_hits / float(len(S))
            new_e = self._current_e_float(enc)

            print(f"[more-c] trial:    hits={new_hits}/{len(S)}  c={new_c:.12f}  e={new_e}")

            improved = (new_hits == curr_hits + 1) and (new_e_int <= curr_e_int - 1)
            if improved:
                print(f"[more-c] ADD pareto point ({new_c}, {new_e})")
                self.pareto_points.append([new_c, new_e])
                steps += 1
                if new_hits >= len(S):
                    break
                # keep cuts; continue forward
            else:
                model.remove(corr_cut)
                model.remove(expl_cut)
                model.update()
                break

    # ----- main entry -----
    def find_new_pareto_points(self, clear: bool = False, save_csv: bool = False, plot_png: bool = False):
        if clear:
            self.pareto_points.clear()

        # initial solves
        self._solve_once_each()

        # base point (mirrors your old two-solver trick)
        curr_c = self._current_c_float(self.encs[0])
        curr_e = self._current_e_float(self.encs[1])
        print("-------------------------------------------------------")
        print(f"Start from base point: c = {curr_c}, e = {curr_e}")
        print("-------------------------------------------------------")

        # walks
        self.find_pareto_solutions_more_e()
        print("_____________ switching to more-c walk")
        self.find_pareto_solutions_more_c()

        # include base point if not dominated / not duplicate
        placed = False
        for (c, e) in self.pareto_points:
            if near_int(c - curr_c) and abs(e - curr_e) <= EPS:
                placed = True
                break
        if not placed:
            self.pareto_points.append([curr_c, curr_e])

        # sort & dedup
        self.pareto_points.sort(key=lambda xy: xy[0])
        dedup = []
        for c, e in self.pareto_points:
            if not dedup or abs(dedup[-1][0] - c) > EPS or abs(dedup[-1][1] - e) > EPS:
                dedup.append([c, e])
        self.pareto_points = dedup

        # save / plot
        if save_csv:
            out_dir = os.path.join(self.inp.filename, "results", "pareto_points")
            os.makedirs(out_dir, exist_ok=True)
            fn = f"pareto_points_I{self.inp.max_nodes}_C{self.inp.c_max}.csv"
            with open(os.path.join(out_dir, fn), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["c", "e"])
                for c, e in self.pareto_points:
                    w.writerow([c, e])

        if plot_png:
            out_dir = os.path.join(self.inp.filename, "results", "pareto_curves")
            os.makedirs(out_dir, exist_ok=True)
            xs = [c for c, _ in self.pareto_points]
            ys = [e for _, e in self.pareto_points]
            plt.figure()
            plt.plot(xs, ys, marker="o")
            plt.xlabel("Correctness")
            plt.ylabel("Explainability")
            plt.tight_layout()
            fn = f"pareto_curve_I{self.inp.max_nodes}_C{self.inp.c_max}.png"
            plt.savefig(os.path.join(out_dir, fn), dpi=300, bbox_inches="tight")
            plt.close()

        return self.pareto_points


# quick demo usage (optional)
if __name__ == "__main__":
    inp = Input("examples/wine", max_nodes=3)
    ints_pos = {0, 1, 2}
    pp = Pareto_Points(inp, ints_pos, root=0)
    pts = pp.find_new_pareto_points(clear=True, save_csv=True, plot_png=True)
    print("Pareto points:", pts)
