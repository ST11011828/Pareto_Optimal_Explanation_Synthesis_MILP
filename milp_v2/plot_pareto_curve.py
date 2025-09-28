# import gurobipy as gp
# from gurobipy import GRB
# from solver import model_solver
# from helper_functions import calculate_correctness, calculate_explainability
# import csv

# def find_new_pareto_points(solution, counter):
#     print(f'Current value of counter is {counter}')
#     print("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
#     model = solution["model"]
#     m = solution["m"]
#     S = solution["S"]
#     u = solution["u"]
#     o_u = solution["o_u"]
#     I = solution["I"]
#     P = solution["P"]
#     k1 = float(calculate_correctness(solution))
#     print ("THIS IS THE INITIAL K1 ", str(k1))
#     k2 = float(calculate_explainability(solution))
#     print ("THIS IS THE INITIAL K2 ", str(k2))
#     if k1 >= 0.00001 :
#         # for i in I:
#             # model.addConstr(u[i] >=0)
#         model.addConstr( gp.quicksum(m[0,s] for s in S) <= k1*len(S) -1)
#         print(str(k2), " is the new explainability")
#         print("hehe1||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")

#         model.addConstr(gp.quicksum( 1- u[i] for i in I) + gp.quicksum(o_u[i,p] for i in I for p in P) >= k2 + 1, name ="NEWLY_ADDED")

#         model.update()
#         model.optimize()
#         print("hehe2||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
#         if model.status == GRB.OPTIMAL or model.status == GRB.SUBOPTIMAL:
        
#             print("THIS IS THE FINAL K1 ", str(float(calculate_correctness(solution))))
#             print("THIS IS THE FINAL K2 ", float(calculate_explainability(solution)))
#             print("hehe3------------------------------------------------------------------------")
#             for v in model.getVars():
#                 if v.VarName.startswith("u") or v.VarName.startswith("o"):
#                     print(f"{v.VarName} = {v.X}")
#             return [float(calculate_correctness(solution)), float(calculate_explainability(solution))]
#         else:
#             return []
#         # print("hehe4------------------------------------------------------------------------")
#         # model.write("debug.lp")
#         # print("hehe5_-----------------------------------------------------------------------")

#     else:
#         return []
    
# def cumulate_pareto_points():
#     counter = 0
#     solution = model_solver()
#     c = float(calculate_correctness(solution))
#     e = float(calculate_explainability(solution))
#     filename = "pareto_points.csv"
#     with open(filename, mode="w", newline="") as f:
#         writer = csv.writer(f)
#         writer.writerow(["c", "e"])
#         writer.writerow([c, e])
#     print(f"Initial Pareto point saved: c={c}, e={e}")
#     # l =0
#     while c > 0.000001:
#     # while l <=0:
#         new_point = find_new_pareto_points(solution, counter)
#         counter += 1
#         # l = l+1
#         # print("YOYOYOYOYOYOYOYOYOYOYOYOYO")
#         if new_point is []:
#             print("No further improvement")
#             break

#         c_new, e_new = new_point
#         if c_new < c and e_new > e:
#             with open(filename, mode="a", newline="") as f:
#                 writer = csv.writer(f)
#                 writer.writerow([c_new, e_new])
#             print(f"New Pareto point saved: c={c_new}, e={e_new}")
#             c, e = c_new, e_new
#         else:
#             print("No strict decrease in correctness found")
#             break
    

# def main():
#     cumulate_pareto_points()

# if __name__=="__main__":
#     main()

import gurobipy as gp
from gurobipy import GRB
from solver import model_solver
from helper_functions import calculate_correctness, calculate_explainability, return_weight
import csv

# Choose tolerances:
# If correctness is a COUNT (integer), use dc = 1.0; if it's a fraction/continuous, use a small epsilon.
DC_INTEGER_STEP = True
EPS = 1e-6

def find_new_pareto_points(solution, counter):
    """
    Tighten correctness by a strict step and force explainability to strictly improve.
    Returns a tuple (c_new, e_new) on success, or None if no further improvement.
    """
    print(f"Current value of counter is {counter}")
    print("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")

    model = solution["model"]
    m = solution["m"]
    S = solution["S"]
    u = solution["u"]
    o_u = solution["o_u"]
    I = solution["I"]
    P = solution["P"]

    # Current metrics
    k1 = float(calculate_correctness(solution))        # correctness (e.g., accuracy or #correct)
    k2 = float(calculate_explainability(solution))     # explainability

    print("THIS IS THE INITIAL K1", k1)
    print("THIS IS THE INITIAL K2", k2)

    # If correctness is already ~0, nothing to improve
    if k1 < 1e-8:
        return None

    # We add constraints to the SAME model to look for a new point
    # 1) Strictly reduce correctness
    #    Decide whether correctness is a COUNT or a FRACTION:
    if DC_INTEGER_STEP:
        # assume Σ m[0,s] is integer (# correctly classified samples)
        curr_correct_count = k1 * len(S)  # if k1 was a fraction; if k1 is already a count, just use k1
        # If k1 already a count, set: target = curr_correct_count - 1
        target = curr_correct_count - 1.0 + (EPS)  # small slop to avoid numerical ties
        # Safer: floor before subtracting 1
        # import math; target = math.floor(curr_correct_count + EPS) - 1 + (1 - EPS)
        constr = model.addConstr(gp.quicksum(m[0, s] for s in S) <= target, name=f"dec_correct_{counter}")
    else:
        # if correctness is continuous (e.g., average of continuous m[0,s])
        target = k1 * len(S) - EPS * len(S)
        constr = model.addConstr(gp.quicksum(m[0, s] for s in S) <= target, name=f"dec_correct_{counter}")

    print(k2, " is the current explainability; will require a strict improvement")

    # 2) Strictly improve explainability
    # If your explainability is an integer measure, set step to 1.0; otherwise a small epsilon.
    if DC_INTEGER_STEP:
        step_e = 1.0 - EPS
    else:
        step_e = 1e-3  # small bump; tune as needed

    expl_expr = gp.quicksum(1 - u[i] for i in I) + gp.quicksum(return_weight(p)*o_u[i, p] for i in I for p in P)
    model.addConstr(expl_expr >= k2 + step_e, name=f"inc_expl_{counter}")

    model.update()
    model.optimize()

    if model.status in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
        # Read the new values directly
        # Recompute via helpers (they read the same model/vars)
        c_new = float(calculate_correctness(solution))
        e_new = float(calculate_explainability(solution))
        print("THIS IS THE FINAL K1", c_new)
        print("THIS IS THE FINAL K2", e_new)
        print("---- u and o_u snapshot ----")
        for v in model.getVars():
            if v.VarName.startswith("u") or v.VarName.startswith("o_u"):
                print(f"{v.VarName} = {v.X}")
        return (c_new, e_new)

    # Infeasible or no better solution
    if model.status == GRB.INFEASIBLE:
        print("[INFO] Model became infeasible under the new cuts.")
    else:
        print(f"[INFO] Solver returned status {model.status} (no usable solution).")
    return None


def cumulate_pareto_points():
    counter = 0
    solution = model_solver()

    # Initial point
    c = float(calculate_correctness(solution))
    e = float(calculate_explainability(solution))

    filename = "pareto_points.csv"
    with open(filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["c", "e"])
        writer.writerow([c, e])
    print(f"Initial Pareto point saved: c={c}, e={e}")

    # Iterate until correctness is ~0 or no improvement
    while c > 1e-8:
        new_point = find_new_pareto_points(solution, counter)
        counter += 1

        # Properly handle "no new point"
        if not new_point:   # catches None or empty sequence
            print("No further improvement")
            break

        c_new, e_new = new_point

        # Require strict Pareto improvement: lower c AND higher e
        if (c_new < c - 1e-12) and (e_new > e + 1e-12):
            with open(filename, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([c_new, e_new])
            print(f"New Pareto point saved: c={c_new}, e={e_new}")
            c, e = c_new, e_new
        else:
            print("No strict Pareto improvement (either c didn't drop or e didn't rise).")
            break


def main():
    cumulate_pareto_points()

if __name__ == "__main__":
    main()
