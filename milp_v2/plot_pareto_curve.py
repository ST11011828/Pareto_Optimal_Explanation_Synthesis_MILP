from itertools import count
import gurobipy as gp
from gurobipy import GRB
from solver import model_solver
from helper_functions import calculate_correctness, calculate_explainability, return_weight , return_max_weight
import csv
import os
import matplotlib.pyplot as plt
pareto_points = [] # stores all the pareto_points

def find_pareto_solution_more_e(solution):
    """
    This function will take a solution and then find another pareto-optimal point which has greater explainability than the current solution and lesser correctness.
    """
    print("Inside find_pareto_solution_more_e")
    print('----------------------------------')
    global pareto_points
    model = solution["model"]
    m = solution["m"]
    S = solution["S"]
    u = solution["u"]
    o_u = solution["o_u"]
    I = solution["I"]
    P = solution["P"]
    if model.status != GRB.INFEASIBLE:
        curr_correctness = float(calculate_correctness(solution)) #initial correctness
        curr_explainability = float(calculate_explainability(solution)) #initil explainability
        target = curr_correctness*len(S) -1
        constr_corr = model.addConstr(gp.quicksum(m[0, s] for s in S) <= target) # decreasing correctness
        print(f'THE CURRENT CORRECTNESS IS: {curr_correctness}, AND THE CURRENT EXPLAINABILITY IS: {curr_explainability}')
        constr_expl = model.addConstr(gp.quicksum(1 - u[i] for i in I) + gp.quicksum(return_weight(p)*o_u[i, p] for i in I for p in P) >= (curr_explainability + 1)) # increasing explainability
        model.update()
        model.optimize()
        if model.status == GRB.OPTIMAL or model.status == GRB.SUBOPTIMAL:
            print("Objective value:", model.objVal)
            for v in model.getVars():
                if (v.VarName.startswith("o_u") or v.VarName.startswith("u") or v.VarName.startswith("m[0") or v.VarName.startswith("lam") or v.VarName.startswith("tau")) :
                    val = v.X
                    # Round to nearest integer if close enough
                    if abs(val - round(val)) < 1e-4:
                        val = round(val)
                    print(f"{v.VarName} = {val}")
            print("-----------------------------------------------------------------")
            for v in model.getVars():
                if v.X <1  and  v.X>0:
                    print(f"{v.VarName} = {v.X}")
            print("-----------------------------------------------------------------")
            
                    # print(f"{v.VarName} = {v.X}") #printing the ulam,tau,u,o_u and m[0,x] as a testing measure
            model.remove(constr_corr) # removing the current constraint - this has to be done because we will be using the same solution in the find_pareto_optimal_solution_more_c and if we don't remove it then the the model will become infeasible
            model.remove(constr_expl)
            new_correctness = float(calculate_correctness(solution))
            new_explainability = float(calculate_explainability(solution))
            print(f'THE NEW CORRECTNESS IS: {new_correctness}, AND THE NEW EXPLAINABILITY IS: {new_explainability}')

            if new_correctness < curr_correctness and new_explainability > curr_explainability :
                print("************************************************************")
                print(f"New pareto points added, correctness = {new_correctness} , explainability = {new_explainability}")
                print("App ending 1......")
                pareto_points.append([new_correctness,new_explainability])  
            if new_correctness <= 1e-6:
                print("End of find_pareto_solution_more_e 1 @@@@@@@@@@@@@")
                return None
            else:
                print("End of find_pareto_solution_more_e 4 @@@@@@@@@@@@@")
                find_pareto_solution_more_e(solution)
        else:
            print("[INFO] Model became infeasible under the new cuts.")
            print("End of find_pareto_solution_more_e 2 @@@@@@@@@@@")
            return None
    else:
        print("End of find_pareto_solution_more_e 3 @@@@@@@@@@@")
        return None
    pass

def find_pareto_solution_more_c(solution):
    """
    This function will take a solution and then find another pareto-optimal point which has lesser explainability than the current solution and greater correctness
    """
    print("Inside find_pareto_solution_more_c")
    global pareto_points
    model = solution["model"]
    m = solution["m"]
    S = solution["S"]
    u = solution["u"]
    o_u = solution["o_u"]
    I = solution["I"]
    P = solution["P"]
    if model.status != GRB.INFEASIBLE:
        curr_correctness = float(calculate_correctness(solution)) #initial correctness
        curr_explainability = float(calculate_explainability(solution)) #initial explainability
        target = curr_correctness*len(S) +1
        constr_corr = model.addConstr(gp.quicksum(m[0, s] for s in S) >= target) # increasing correctness
        constr_expl = model.addConstr(gp.quicksum(1 - u[i] for i in I) + gp.quicksum(return_weight(p)*o_u[i, p] for i in I for p in P) <= (curr_explainability - 1)) # decreasing explainability
        model.update()
        model.optimize()
        model.remove(constr_corr) # removing the current constraint - in this case since we have already called the find_pareto_solution_more_e and won't be calling it again - its okay had we chosen not to remove the constraints as well
        model.remove(constr_expl)
        if model.status == GRB.OPTIMAL or model.status == GRB.SUBOPTIMAL:
            print("Objective value:", model.objVal)
            for v in model.getVars():
                if (v.VarName.startswith("o_u") or v.VarName.startswith("u") or v.VarName.startswith("m[0") or v.VarName.startswith("lam") or v.VarName.startswith("tau")) :
                    val = v.X
                    # Round to nearest integer if close enough
                    if abs(val - round(val)) < 1e-4:
                        val = round(val)
                    print(f"{v.VarName} = {val}")
            print("-----------------------------------------------------")
            for v in model.getVars():
                if v.X <1  and  v.X>0:
                    print(f"{v.VarName} = {v.X}")
            print("-----------------------------------------------------------------")

                    # print(f"{v.VarName} = {v.X}") #printing the lam,tau,u,o_u amd m[0,x] as a testing measure
        if model.status == GRB.INFEASIBLE:
            print("[INFO] Model became infeasible under the new cuts.")
            print("End of find_pareto_solution_more_c 1 |||||||||||||||||")
            return None
        new_correctness = float(calculate_correctness(solution))
        new_explainability = float(calculate_explainability(solution))
        if new_correctness > curr_correctness and new_explainability < curr_explainability :
            print(f"New pareto points added, correctness = {new_correctness} , explainability = {new_explainability}")
            print("App ending 2.................")
            pareto_points.append([new_correctness,new_explainability])
        if new_correctness >= 1-1e-6:
            print("End of find_pareto_solution_more_c 2 |||||||||||||||||")
            return None
        else :
            print("End of find_pareto_solution_more_c 4 |||||||||||||||||")
            find_pareto_solution_more_c(solution)
    else:
        print("End of find_pareto_solution_more_c 3 |||||||||||||||||")
        return None
    pass


def find_new_pareto_points(I,C):
    """
    Takes a solution and finds pareto solution on both the spaces- more e less c and less c more e
    """
    global pareto_points
    pareto_points.clear()
    print("I AM STARTING --------------------")
    print(pareto_points)
    print("NOW I AM GOING TO SOLVE THE MODEL FOR FIRST SOLUTION")
    solution = model_solver(I,C)
    print(pareto_points)
    solution_copy = model_solver(I,C)
    curr_correctness = float(calculate_correctness(solution))                   # correctness 
    curr_explainability = float(calculate_explainability(solution_copy))        # explainability

    print("THIS IS THE INITIAL CORRECTNESS", curr_correctness)
    print("THIS IS THE INITIAL EXPLAINABILITY", curr_explainability)

    find_pareto_solution_more_e(solution)
    find_pareto_solution_more_c(solution_copy)
    count = 0
    for point in pareto_points:
        print(point)
        print("Printing original list")
        for points in pareto_points:
            print(points)
        if point[0] == curr_correctness:
            if point[1] < curr_explainability:
                count = 1
                print(f"Updating explainability %%%%%% from {point[1]} to {curr_explainability}")
                point[1] = curr_explainability
        elif point[1] == curr_explainability:
            if point[0] < curr_correctness:
                count = 1
                print(f"updating correctness ^^^^^^^^^^^^ from {point[0]} to {curr_correctness}")
                point[0] = curr_correctness
        print("Printing list after change")
        for points in pareto_points:
            print(points)
    if count == 0:
        print(f"App ending 3....................... c = {curr_correctness} , e = {curr_explainability}")
        pareto_points.append([curr_correctness, curr_explainability])
        
        

    def return_corr(point):
        return point[0]
    sorted_pareto_points = sorted(pareto_points, key=return_corr) 
    pareto_dir = "examples/wine/lam_and_tau_integers/pareto_points"
    os.makedirs(pareto_dir, exist_ok=True)
    filename = f"examples/wine/lam_and_tau_integers/pareto_points/pareto_points{I}_{C}.csv"
    with open(filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["c", "e"])
        for point in sorted_pareto_points:
            writer.writerow([point[0], point[1]])
    plot_pareto_curve(sorted_pareto_points,I,C)

def plot_pareto_curve(sorted_pareto_points,I,C):
    """
    This function plots pareto_points
    """
    # global pareto_points
    x = [pt[0] for pt in sorted_pareto_points] # correctness
    y = [pt[1] for pt in sorted_pareto_points] # explainability

    plt.figure()
    plt.plot(x , y , marker = 'o')
    plt.xlabel('Correctness')
    plt.ylabel('Explainability')
    # plt.show()
    out_dir = "examples/wine/lam_and_tau_integers/pareto_curves"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"pareto_curve_{I}_{C}.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.show()

