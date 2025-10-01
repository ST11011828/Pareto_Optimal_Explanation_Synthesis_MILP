import gurobipy as gp
from gurobipy import GRB
from solver import model_solver
from helper_functions import calculate_correctness, calculate_explainability, return_weight , return_max_weight
import csv

pareto_points = [] # stores all the pareto_points

def find_pareto_solution_more_e(solution):
    """
    This function will take a solution and then find another pareto-optimal point which has greater explainability than the current solution and lesser correctness.
    """
    print("Inside find_pareto_solution_more_e")
    curr_correctness = float(calculate_correctness(solution)) #initial correctness
    curr_explainability = float(calculate_explainability(solution)) #initil explainability
    model = solution["model"]
    m = solution["m"]
    S = solution["S"]
    u = solution["u"]
    o_u = solution["o_u"]
    I = solution["I"]
    P = solution["P"]
    target = curr_correctness*len(S) -1
    constr_corr = model.addConstr(gp.quicksum(m[0, s] for s in S) <= target) # decreasing correctness
    constr_expl = model.addConstr(return_max_weight()*gp.quicksum(1 - u[i] for i in I) + gp.quicksum(return_weight(p)*o_u[i, p] for i in I for p in P) >= (curr_explainability + 1)) # increasing explainability
    model.update()
    model.optimize()
    if model.status == GRB.OPTIMAL or model.status == GRB.SUBOPTIMAL:
        print("Objective value:", model.objVal)
        for v in model.getVars():
            if (v.VarName.startswith("o_u") or v.VarName.startswith("u") or v.VarName.startswith("m[0") or v.VarName.startswith("lam") or v.VarName.startswith("tau")) :
                print(f"{v.VarName} = {v.X}") #printing the ulam,tau,u,o_u and m[0,x] as a testing measure
    if model.status == GRB.INFEASIBLE:
        print("[INFO] Model became infeasible under the new cuts.")
    model.remove(constr_corr) # removing the current constraint - this has to be done because we will be using the same solution in the find_pareto_optimal_solution_more_c and if we don't remove it then the the model will become infeasible
    model.remove(constr_expl)
    new_correctness = float(calculate_correctness(solution))
    new_explainability = float(calculate_explainability(solution))
    if new_correctness < curr_correctness and new_explainability > curr_explainability :
        print(f"New pareto points added, correctness = {new_correctness} , explainability = {new_explainability}")
        pareto_points.append([new_correctness,new_explainability])  
    if new_correctness <= 1e-6:
        return None
    else :
        find_pareto_solution_more_e(solution)
    pass

def find_pareto_solution_more_c(solution):
    """
    This function will take a solution and then find another pareto-optimal point which has lesser explainability than the current solution and greater correctness
    """
    print("Inside find_pareto_solution_more_c")
    curr_correctness = float(calculate_correctness(solution)) #initial correctness
    curr_explainability = float(calculate_explainability(solution)) #initial explainability
    model = solution["model"]
    m = solution["m"]
    S = solution["S"]
    u = solution["u"]
    o_u = solution["o_u"]
    I = solution["I"]
    P = solution["P"]
    target = curr_correctness*len(S) +1
    constr_corr = model.addConstr(gp.quicksum(m[0, s] for s in S) >= target) # increasing correctness
    constr_expl = model.addConstr(return_max_weight()*gp.quicksum(1 - u[i] for i in I) + gp.quicksum(return_weight(p)*o_u[i, p] for i in I for p in P) <= (curr_explainability - 1)) # decreasing explainability
    model.update()
    model.optimize()
    if model.status == GRB.OPTIMAL or model.status == GRB.SUBOPTIMAL:
        print("Objective value:", model.objVal)
        for v in model.getVars():
            if (v.VarName.startswith("o_u") or v.VarName.startswith("u") or v.VarName.startswith("m[0") or v.VarName.startswith("lam") or v.VarName.startswith("tau")) :
                print(f"{v.VarName} = {v.X}") #printing the lam,tau,u,o_u amd m[0,x] as a testing measure
    if model.status == GRB.INFEASIBLE:
        print("[INFO] Model became infeasible under the new cuts.")
    model.remove(constr_corr) # removing the current constraint - in this case since we have already called the find_pareto_solution_more_e and won't be calling it again - its okay had we chosen not to remove the constraints as well
    model.remove(constr_expl)
    new_correctness = float(calculate_correctness(solution))
    new_explainability = float(calculate_explainability(solution))
    if new_correctness > curr_correctness and new_explainability < curr_explainability :
        print(f"New pareto points added, correctness = {new_correctness} , explainability = {new_explainability}")
        pareto_points.append([new_correctness,new_explainability])
    if new_correctness >= 1-1e-6:
        return None
    else :
        find_pareto_solution_more_c(solution)
    pass


def find_new_pareto_points(I,C):
    """
    Takes a solution and finds pareto solution on both the spaces- more e less c and less c more e
    """
    solution = model_solver(I,C)
    global pareto_points
    curr_correctness = float(calculate_correctness(solution))        # correctness 
    curr_explainability = float(calculate_explainability(solution))     # explainability

    print("THIS IS THE INITIAL CORRECTNESS", curr_correctness)
    print("THIS IS THE INITIAL EXPLAINABILITY", curr_explainability)

    find_pareto_solution_more_e(solution)
    find_pareto_solution_more_c(solution)

    pareto_points.append([curr_correctness, curr_explainability])   
    def return_corr(point):
        return point[0]
    sorted_pareto_points = sorted(pareto_points, key=return_corr) 
    filename = f"examples/AutoTaxi/pareto_points/pareto_points_{I}_{C}.csv"
    with open(filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["c", "e"])
        for point in sorted_pareto_points:
            writer.writerow(point[0], point[1])


