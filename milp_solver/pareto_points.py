import os
import csv
import matplotlib.pyplot as plt
import gurobipy as gp
from gurobipy import GRB

from inputs import Input, Predicate
from encoding import Encoding


# class Pareto_Points:
#     """
#     - pareto_points: list[[c,e], ...]
#     - inp: Input
#     - int_pos: set[int]  (nodes whose lam/tau are integer)
#     - root: int
#     - encs: [Encoding, Encoding]  (independent models for the two walks)
#     - solution: dict (the initial base solution from encs[0])
#     """

#     def __init__(self, inp: Input, int_pos, root: int):
#         self.inp = inp
#         self.int_pos = set(int_pos)
#         self.root = root

#         # two independent encodings (so each walk can add/remove its own cuts with no rebuild penalty)
#         self.encs = [
#             Encoding(self.int_pos, self.inp, self.root),
#             Encoding(self.int_pos, self.inp, self.root),
#         ]

#         self.pareto_points = []
#         # self.solution = None  # base solution from encs[0]

#     # ------------- helpers -------------
#     def _solve_once_each(self):
#         """Solve both encodings once to initialize."""
#         sol0 = self.encs[0].solve()
#         sol1 = self.encs[1].solve()
#         # self.solution = sol0  # keep one around if caller wants it
#         # return sol0, sol1

#     # ------------- walks -------------
#     def find_pareto_solutions_more_e(self):
#         """
#         Increase explainability, decrease correctness.
#         Operates on encs[0] in-place, adding temporary cuts which are removed after each solve.
#         """
#         print("Entering find pareto solutions more e")
#         enc = self.encs[0]
#         model = enc.model
#         I, P, S = enc.I, enc.P, enc.S
#         root = enc.root

#         # ensure base objective/constraints are present
#         enc.solve()

#         def _step():
#             if model.status == GRB.INFEASIBLE:
#                 return False
#             curr_c = float(enc.calculate_correctness())
#             curr_e = float(enc.calculate_explainability())

#             print(f"This is the current correctness = {curr_c} and this is the current explainability = {curr_e}")
#             # correctness: sum m[root, s] <= target (drop by 1 unit)
#             target = curr_c - 1 
#             constr_corr = model.addConstr(gp.quicksum(enc.m[root, s] for s in S) <= target)

#             # explainability: >= current + 1
#             constr_expl = model.addConstr(
#                 gp.quicksum(1 - enc.u[i] for i in I) +
#                 gp.quicksum(enc.inp.predicates[p].weight * enc.o_u[i, p] for i in I for p in P)
#                 >= (curr_e + 1 )
#             )

#             model.update()
#             model.optimize()

#             # capture new values then remove cuts so the next step starts clean
#             feasible = model.status in (GRB.OPTIMAL, GRB.SUBOPTIMAL)
#             new_c = float(enc.calculate_correctness()) if feasible else curr_c
#             new_e = float(enc.calculate_explainability()) if feasible else curr_e
#             print(f"new_curr = {new_c}, new_e = {new_e}")
#             model.remove(constr_corr)
#             model.remove(constr_expl)
#             model.update()

#             if feasible and (new_c < curr_c) and (new_e > curr_e):
#                 print(f"Feasibility of the model is {feasible}")
#                 print(f"ADDING pareto point {new_c}, {new_e}")
#                 self.pareto_points.append([new_c, new_e])
#                 # stop if correctness is ~0
#                 if new_c <= 1e-6:
#                     print("RETURNING FALSE _______________________________________________________________________________________")
#                     return False
#                 print("RETURNING TRUE ______________________________________________________________________________________")
#                 return True
#             print("RETURNING FALSE ___________________________________________________________________________________________")
#             return False

#         # keep stepping while we improve
#         while _step():
#             pass

#     def find_pareto_solutions_more_c(self):
#         """
#         Increase correctness, decrease explainability.
#         Operates on encs[1] in-place, adding temporary cuts which are removed after each solve.
#         """
#         print("Entering more c------------------------")
#         enc = self.encs[1]
#         model = enc.model
#         I, P, S = enc.I, enc.P, enc.S
#         root = enc.root

#         enc.solve()

#         def _step():
#             if model.status == GRB.INFEASIBLE:
#                 return False

#             curr_c = float(enc.calculate_correctness())
#             curr_e = float(enc.calculate_explainability())

#             # target = curr_c * len(S) + 1
#             target = curr_c + 1 - 10e-6

#             constr_corr = model.addConstr(gp.quicksum(enc.m[root, s] for s in S) >= target)

#             constr_expl = model.addConstr(
#                 gp.quicksum(1 - enc.u[i] for i in I) +
#                 gp.quicksum(enc.inp.predicates[p].weight * enc.o_u[i, p] for i in I for p in P)
#                 <= (curr_e - 1 + 10e-6)
#             )

#             model.update()
#             model.optimize()

#             feasible = model.status in (GRB.OPTIMAL, GRB.SUBOPTIMAL)
#             new_c = float(enc.calculate_correctness()) if feasible else curr_c
#             new_e = float(enc.calculate_explainability()) if feasible else curr_e

#             model.remove(constr_corr)
#             model.remove(constr_expl)
#             model.update()

#             if feasible and (new_c > curr_c) and (new_e < curr_e):
#                 self.pareto_points.append([new_c, new_e])
#                 if new_c >= 1 - 1e-6:
#                     return False
#                 return True
#             return False

#         while _step():
#             pass

#     # ------------- main entry -------------
#     def find_new_pareto_points(self, clear: bool = False, save_csv: bool = False, plot_png: bool = False):
#         """
#         Runs both walks from two independent encodings.
#         If `clear` is True, we clear any existing points (useful when reusing the same object).
#         """

#         # initial solves
#         self._solve_once_each()

#         # base “current” (like your old two-solver trick)
#         curr_c = float(self.encs[0].calculate_correctness())
#         curr_e = float(self.encs[1].calculate_explainability())
#         print("-------------------------------------------------------")
#         print(f"Yo I am starting, this curr_c = {curr_c}, curr e = {curr_e}")
#         print("-------------------------------------------------------")

#         # do both walks
#         self.find_pareto_solutions_more_e()
#         print("___________________________________ starting more c")
#         self.find_pareto_solutions_more_c()

#         # ensure the base point is represented / undominated
#         replaced = False
#         for pt in self.pareto_points:
#             if pt[0] == curr_c and pt[1] < curr_e:
#                 pt[1] = curr_e
#                 replaced = True
#             elif pt[1] == curr_e and pt[0] < curr_c:
#                 pt[0] = curr_c
#                 replaced = True
#         if not replaced:
#             self.pareto_points.append([curr_c, curr_e])

#         # sort by correctness
#         self.pareto_points.sort(key=lambda xy: xy[0])

#         # optional save / plot
#         if save_csv:
#             out_dir = os.path.join(self.inp.filename, "results", "pareto_points")
#             os.makedirs(out_dir, exist_ok=True)
#             fn = f"pareto_points_I{self.inp.max_nodes}_C{self.inp.c_max}.csv"
#             with open(os.path.join(out_dir, fn), "w", newline="") as f:
#                 w = csv.writer(f)
#                 w.writerow(["c", "e"])
#                 for c, e in self.pareto_points:
#                     w.writerow([c, e])

#         if plot_png:
#             out_dir = os.path.join(self.inp.filename, "results", "pareto_curves")
#             os.makedirs(out_dir, exist_ok=True)
#             xs = [c for c, _ in self.pareto_points]
#             ys = [e for _, e in self.pareto_points]
#             plt.figure()
#             plt.plot(xs, ys, marker="o")
#             plt.xlabel("Correctness")
#             plt.ylabel("Explainability")
#             plt.tight_layout()
#             fn = f"pareto_curve_I{self.inp.max_nodes}_C{self.inp.c_max}.png"
#             plt.savefig(os.path.join(out_dir, fn), dpi=300, bbox_inches="tight")
#             plt.close()

#         return self.pareto_points


# # quick demo usage (optional)
# if __name__ == "__main__":
#     inp = Input("examples/wine", max_nodes=3)
#     ints_pos = {0,1,2}   # make lam/tau integral for node 0
#     pp = Pareto_Points(inp, ints_pos, root=0)
#     pts = pp.find_new_pareto_points(clear=True, save_csv=True, plot_png=True)
#     print("Pareto points:", pts)

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
            self.enc.model.update()
            self.enc.solve()
            print("SOLVED FOR THE NEW POINT, NOW CHECKING IF IT IS PARETO_POINT OR NOT")
            if self.enc.model.status == GRB.INFEASIBLE:
                print( f"Model infeasible for explainabbility = {expl} , trying for next value")
            else :
                curr_expl = self.enc.calculate_explainability()
                curr_correctness = self.enc.calculate_correctness()
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

            self.enc.model.remove(expl_constr)
            self.enc.model.update()
        print(self.pareto_points)
        self.write_pareto_points()
        self.plot_pareto_points()

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
    pp = Pareto_Points("examples/wine",3,{0,1,2},0)
    pp.find_pareto_points()

if __name__ == "__main__":
    main()