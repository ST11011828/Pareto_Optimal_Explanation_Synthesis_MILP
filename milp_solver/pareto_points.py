import os
import csv
import matplotlib.pyplot as plt
import gurobipy as gp
from gurobipy import GRB

from inputs import Input, Predicate
from encoding import Encoding


class Pareto_Points:
    def __init__(self,inp, int_pos, root:int):
        self.root = root
        self.inp = inp
        self.pareto_points= []
        self.enc = Encoding(int_pos, self.inp, root)

    def find_pareto_points(self):
        possible_explainabilities = range(self.inp.min_weight+self.inp.max_nodes-1, self.inp.max_nodes*self.inp.max_weight+1)
        for expl in possible_explainabilities:
            expl_constr = self.enc.model.addConstr(
                gp.quicksum(1 - self.enc.u[i] for i in self.enc.I) +
                gp.quicksum(self.enc.inp.predicates[p].weight * self.enc.o_u[i, p] for i in self.enc.I for p in self.enc.P)
                == expl
            )
            print("Stopping at line 26----------------------")
            self.enc.model.update()
            self.enc.solve()
            print("Stopping at line 29---------------------------------------")
            print("SOLVED FOR THE NEW POINT, NOW CHECKING IF IT IS PARETO_POINT OR NOT")
            if self.enc.model.status == GRB.INFEASIBLE:
                print( f"Model infeasible for explainabbility = {expl} , trying for next value")
                print("Stopping at line 33---------------------------------------")
                break
            elif self.enc.model.status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
                print(f"Model failed (status={self.enc.model.status}) for explainability = {expl}, skipping")
                print("Stopping at line 36---------------------------------------")
                continue
            else :
                curr_expl = self.enc.calculate_explainability()
                curr_correctness = self.enc.calculate_correctness()
                print("Stopping at line 41---------------------------------------")
                print(f"Checking if e= {curr_expl} and c = {curr_correctness} is a pareto point or not")
                if len(self.pareto_points) != 0:
                    if self.pareto_points[-1][0] > curr_correctness and self.pareto_points[-1][1] > curr_expl:
                        print("CURRENT POINT IS NOT PARETO OPTIMAL, THE PREVIOUS POINT HAS BOTH GREATER CORRECTNESS AND GREATER EXPL")
                    elif self.pareto_points[-1][0] < curr_correctness and self.pareto_points[-1][1] < curr_expl:
                        print("The CURRENT POINT PARETO_DOMINATES THE PREVIOUS POINT, HENCE IT IS BEING REPLACED, BOTH EXPL AND CORR ARE MORE")
                        self.pareto_points[-1][0] = curr_correctness
                        self.pareto_points[-1][1] = curr_expl
                    elif self.pareto_points[-1][0] == curr_correctness and self.pareto_points[-1][1] < curr_expl:
                        print("PREV POINT HAS SAME CORR AND HIGHER EXPL, OVERWRITING THE NEW POINT")
                        self.pareto_points[-1][1] = curr_expl
                    elif self.pareto_points[-1][0] < curr_correctness and self.pareto_points[-1][1] == curr_expl:
                        print("PREV POINT HAS GREATER CORR SAME EXPL, OVERWRITING.........")
                        self.pareto_points[-1][0] = curr_correctness
                    else:
                        print("Adding NEW PARETO POINT")
                        self.pareto_points.append([curr_correctness, curr_expl])
                else:
                    self.pareto_points.append([curr_correctness, curr_expl])
                print("Stopping at line 61---------------------------------------")
                self.last_feasible_tau = {k: self.enc.tau[k].X for k in self.enc.tau.keys()}
                self.last_feasible_u = {i: self.enc.u[i].X for i in self.enc.I}
                self.last_feasible_lam = {k: self.enc.lam[k].X for k in self.enc.lam.keys()}
                self.last_feasible_o_u = {k: self.enc.o_u[k].X for k in self.enc.o_u.keys()}

            
            self.enc.model.remove(expl_constr)
            self.enc.model.update()
        print("-------------------------------------------------|||||||||||||||||||||||||||||||||||||||||||||------------------------------------------------------------")
        print(self.pareto_points)
        #TODO: CHECK THIS
        # self._prune_nondominated()
        self.write_pareto_points()
        self.plot_pareto_points()

    # def find_pareto_points(self):
    #     # Optional: set once
    #     try:
    #         self.enc.model.Params.MIPFocus = 1      # favor quick feasible solutions
    #         self.enc.model.Params.Heuristics = 0.2  # modest heuristic effort
    #         # Presolve stays auto (default)
    #     except gp.GurobiError:
    #         pass

    #     possible_explainabilities = range(
    #         self.inp.min_weight + self.inp.max_nodes - 1,
    #         self.inp.max_nodes * self.inp.max_weight + 1
    #     )

    #     for expl in possible_explainabilities:
    #         # Add equality to fix explainability
    #         expl_constr = self.enc.model.addConstr(
    #             gp.quicksum(1 - self.enc.u[i] for i in self.enc.I) +
    #             gp.quicksum(self.enc.inp.predicates[p].weight * self.enc.o_u[i, p]
    #                         for i in self.enc.I for p in self.enc.P)
    #             == expl,
    #             name=f"fix_expl_{expl}"
    #         )
    #         self.enc.model.update()

    #         # ---------- Warm start via Var.Start (robust across Gurobi versions) ----------
    #         # Clear old starts only where we will set new ones (optional)
    #         if hasattr(self, "last_feasible_lam"):
    #             try:
    #                 for k, v in self.last_feasible_lam.items():
    #                     self.enc.lam[k].Start = v
    #                 for k, v in self.last_feasible_tau.items():
    #                     self.enc.tau[k].Start = v
    #                 for i, v in self.last_feasible_u.items():
    #                     self.enc.u[i].Start = v
    #                 for k, v in self.last_feasible_o_u.items():
    #                     self.enc.o_u[k].Start = v
    #                 # 'm' start is optional (can be large):
    #                 # if hasattr(self, "last_feasible_m"):
    #                 #     for k, v in self.last_feasible_m.items():
    #                 #         self.enc.m[k].Start = v
    #             except gp.GurobiError as e:
    #                 print(f"[warm-start] setting Start attributes skipped at expl={expl}: {e}")
    #         # ------------------------------------------------------------------------------

    #         self.enc.solve()
    #         print("SOLVED FOR THE NEW POINT, NOW CHECKING IF IT IS PARETO_POINT OR NOT")

    #         if self.enc.model.status == GRB.INFEASIBLE:
    #             print(f"Model infeasible for explainabbility = {expl} , trying for next value")

    #         elif self.enc.model.status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
    #             print(f"Model failed (status={self.enc.model.status}) for explainability = {expl}, skipping")
    #             # Remove the constraint and continue
    #             self.enc.model.remove(expl_constr)
    #             self.enc.model.update()
    #             continue

    #         else:
    #             curr_expl = self.enc.calculate_explainability()
    #             curr_correctness = self.enc.calculate_correctness()
    #             print(f"Checking if e= {curr_expl} and c = {curr_correctness} is a pareto point or not")

    #             if len(self.pareto_points) != 0:
    #                 if self.pareto_points[-1][0] > curr_correctness and self.pareto_points[-1][1] > curr_expl:
    #                     print("CURRENT POINT IS NOT PARETO OPTIMAL, THE PREVIOUS POINT HAS BOTH GREATER CORRECTNESS AND GREATER EXPL")
    #                 elif self.pareto_points[-1][0] < curr_correctness and self.pareto_points[-1][1] < curr_expl:
    #                     print("The CURRENT POINT PARETO_DOMINATES THE PREVIOUS POINT, HENCE IT IS BEING REPLACED, BOTH EXPL AND CORR ARE MORE")
    #                     self.pareto_points[-1][0] = curr_correctness
    #                     self.pareto_points[-1][1] = curr_expl
    #                 elif self.pareto_points[-1][0] == curr_correctness and self.pareto_points[-1][1] < curr_expl:
    #                     print("PREV POINT HAS SAME CORR AND HIGHER EXPL, OVERWRITING THE NEW POINT")
    #                     self.pareto_points[-1][1] = curr_expl
    #                 elif self.pareto_points[-1][0] < curr_correctness and self.pareto_points[-1][1] == curr_expl:
    #                     print("PREV POINT HAS GREATER CORR SAME EXPL, OVERWRITING.........")
    #                     self.pareto_points[-1][0] = curr_correctness
    #                 else:
    #                     print("Adding NEW PARETO POINT")
    #                     self.pareto_points.append([curr_correctness, curr_expl])
    #             else:
    #                 self.pareto_points.append([curr_correctness, curr_expl])

    #             # Save solution for next warm start
    #             self.last_feasible_tau = {k: self.enc.tau[k].X for k in self.enc.tau.keys()}
    #             self.last_feasible_u   = {i: self.enc.u[i].X for i in self.enc.I}
    #             self.last_feasible_lam = {k: self.enc.lam[k].X for k in self.enc.lam.keys()}
    #             self.last_feasible_o_u = {k: self.enc.o_u[k].X for k in self.enc.o_u.keys()}
    #             # Optionally:
    #             # self.last_feasible_m = {k: self.enc.m[k].X for k in self.enc.m.keys()}

    #         # Remove the equality for this sweep step
    #         self.enc.model.remove(expl_constr)
    #         self.enc.model.update()

    #     print(self.pareto_points)
    #     # Optional global prune here if you like:
    #     # self._prune_nondominated()
    #     self.write_pareto_points()
    #     self.plot_pareto_points()


    def _prune_nondominated(self):
        # points are [[c, e], ...]
        pts = self.pareto_points

        # 1) collapse duplicates at same e keeping max c
        by_e = {}
        for c, e in pts:
            if e not in by_e or c > by_e[e]:
                by_e[e] = c

        # 2) sort by e asc
        sorted_pts = sorted(((c, e) for e, c in by_e.items()), key=lambda t: t[1])

        # 3) scan to keep strictly improving c
        pruned = []
        best_c = float("-inf")
        for c, e in sorted_pts:
            if c > best_c:
                pruned.append([c, e])
                best_c = c

        self.pareto_points = pruned


    def write_pareto_points(self):
        out_dir = os.path.join(self.inp.filename, "results", "pareto_points")
        os.makedirs(out_dir, exist_ok=True)
        fn = f"pareto_points_I{self.inp.max_nodes}_C{self.inp.c_max}.csv"
        with open(os.path.join(out_dir, fn), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["c", "e"])
            for c, e in self.pareto_points:
                w.writerow([c, e])

    def plot_pareto_points(self):
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

def main():
    pp_ = Input("examples/wine",2)
    pp = Pareto_Points(pp_,{0},0)
    pp.find_pareto_points()

if __name__ == "__main__":
    main()