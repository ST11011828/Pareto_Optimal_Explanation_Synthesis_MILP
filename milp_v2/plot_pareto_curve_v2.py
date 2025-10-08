import gurobipy as gp
from gurobipy import GRB
from solver import model_solver
from helper_functions import calculate_correctness, calculate_explainability, return_weight , return_max_weight
import csv
import os

pareto_points = []  # stores all the pareto_points

def is_dominated(candidate, points):
    """
    Returns True if candidate point is dominated by any point in 'points'
    candidate: [c, e]
    points: list of [c, e]
    """
    for p in points:
        if (p[0] >= candidate[0] and p[1] >= candidate[1]) and (p[0] > candidate[0] or p[1] > candidate[1]):
            return True
    return False

def find_pareto_solution_more_e(solution):
    global pareto_points
    """
    This function will take a solution and then find another pareto-optimal point which has greater explainability than the current solution and lesser correctness.
    """
    print("Inside find_pareto_solution_more_e")
    print('----------------------------------')
    model = solution["model"]
    m = solution["m"]
    S = solution["S"]
    u = solution["u"]
    o_u = solution["o_u"]
    I = solution["I"]
    P = solution["P"]
    if model.status != GRB.INFEASIBLE:
        curr_correctness = float(calculate_correctness(solution))  # initial correctness
        curr_explainability = float(calculate_explainability(solution))  # initial explainability
        target = curr_correctness * len(S) - 1
        constr_corr = model.addConstr(gp.quicksum(m[0, s] for s in S) <= target)  # decreasing correctness
        print(f'THE CURRENT CORRECTNESS IS: {curr_correctness}, AND THE CURRENT EXPLAINABILITY IS: {curr_explainability}')
        constr_expl = model.addConstr(return_max_weight() * gp.quicksum(1 - u[i] for i in I) + gp.quicksum(return_weight(p) * o_u[i, p] for i in I for p in P) >= (curr_explainability + 1))  # increasing explainability
        model.update()
        model.optimize()
        if model.status == GRB.OPTIMAL or model.status == GRB.SUBOPTIMAL:
            print("Objective value:", model.objVal)
            for v in model.getVars():
                if (v.VarName.startswith("o_u") or v.VarName.startswith("u") or v.VarName.startswith("m[0") or v.VarName.startswith("lam") or v.VarName.startswith("tau")):
                    print(f"{v.VarName} = {v.X}")
            model.remove(constr_corr)
            model.remove(constr_expl)
            new_correctness = float(calculate_correctness(solution))
            new_explainability = float(calculate_explainability(solution))
            print(f'THE NEW CORRECTNESS IS: {new_correctness}, AND THE NEW EXPLAINABILITY IS: {new_explainability}')

            if new_correctness < curr_correctness and new_explainability > curr_explainability:
                new_point = [new_correctness, new_explainability]
                if not is_dominated(new_point, pareto_points):
                    # remove points dominated by new_point
                    pareto_points = [p for p in pareto_points if not ((new_point[0] >= p[0] and new_point[1] >= p[1]) and (new_point[0] > p[0] or new_point[1] > p[1]))]
                    print(f"New pareto points added, correctness = {new_correctness} , explainability = {new_explainability}")
                    pareto_points.append(new_point)
            if new_correctness <= 1e-6:
                return None
            else:
                find_pareto_solution_more_e(solution)
        if model.status == GRB.INFEASIBLE:
            print("[INFO] Model became infeasible under the new cuts.")
            return None
    else:
        return None
    pass

def find_pareto_solution_more_c(solution):
    global pareto_points
    """
    This function will take a solution and then find another pareto-optimal point which has lesser explainability than the current solution and greater correctness
    """
    print("Inside find_pareto_solution_more_c")
    model = solution["model"]
    m = solution["m"]
    S = solution["S"]
    u = solution["u"]
    o_u = solution["o_u"]
    I = solution["I"]
    P = solution["P"]
    if model.status != GRB.INFEASIBLE:
        curr_correctness = float(calculate_correctness(solution))  # initial correctness
        curr_explainability = float(calculate_explainability(solution))  # initial explainability
        target = curr_correctness * len(S) + 1
        constr_corr = model.addConstr(gp.quicksum(m[0, s] for s in S) >= target)  # increasing correctness
        constr_expl = model.addConstr(return_max_weight() * gp.quicksum(1 - u[i] for i in I) + gp.quicksum(return_weight(p) * o_u[i, p] for i in I for p in P) <= (curr_explainability - 1))  # decreasing explainability
        model.update()
        model.optimize()
        if model.status == GRB.OPTIMAL or model.status == GRB.SUBOPTIMAL:
            print("Objective value:", model.objVal)
            for v in model.getVars():
                if (v.VarName.startswith("o_u") or v.VarName.startswith("u") or v.VarName.startswith("m[0") or v.VarName.startswith("lam") or v.VarName.startswith("tau")):
                    print(f"{v.VarName} = {v.X}")
        if model.status == GRB.INFEASIBLE:
            print("[INFO] Model became infeasible under the new cuts.")
        model.remove(constr_corr)
        model.remove(constr_expl)
        new_correctness = float(calculate_correctness(solution))
        new_explainability = float(calculate_explainability(solution))
        if new_correctness > curr_correctness and new_explainability < curr_explainability:
            new_point = [new_correctness, new_explainability]
            if not is_dominated(new_point, pareto_points):
                pareto_points = [p for p in pareto_points if not ((new_point[0] >= p[0] and new_point[1] >= p[1]) and (new_point[0] > p[0] or new_point[1] > p[1]))]
                print(f"New pareto points added, correctness = {new_correctness} , explainability = {new_explainability}")
                pareto_points.append(new_point)
        if new_correctness >= 1 - 1e-6:
            return None
        else:
            find_pareto_solution_more_c(solution)
    else:
        return None
    pass

def find_new_pareto_points(I, C):
    """
    Takes a solution and finds pareto solution on both the spaces- more e less c and less c more e
    """
    solution = model_solver(I, C)
    solution_copy = solution
    global pareto_points
    curr_correctness = float(calculate_correctness(solution))  # correctness 
    curr_explainability = float(calculate_explainability(solution_copy))  # explainability

    print("THIS IS THE INITIAL CORRECTNESS", curr_correctness)
    print("THIS IS THE INITIAL EXPLAINABILITY", curr_explainability)

    find_pareto_solution_more_e(solution)
    find_pareto_solution_more_c(solution)

    initial_point = [curr_correctness, curr_explainability]
    if not is_dominated(initial_point, pareto_points):
        pareto_points = [p for p in pareto_points if not ((initial_point[0] >= p[0] and initial_point[1] >= p[1]) and (initial_point[0] > p[0] or initial_point[1] > p[1]))]
        pareto_points.append(initial_point)

    def return_corr(point):
        return point[0]

    sorted_pareto_points = sorted(pareto_points, key=return_corr)
    pareto_dir = "examples/AutoTaxi/pareto_points_v2"
    os.makedirs(pareto_dir, exist_ok=True)
    filename = f"examples/AutoTaxi/pareto_points_v2/pareto_points_{I}_{C}.csv"
    with open(filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["c", "e"])
        for point in sorted_pareto_points:
            writer.writerow([point[0], point[1]])
