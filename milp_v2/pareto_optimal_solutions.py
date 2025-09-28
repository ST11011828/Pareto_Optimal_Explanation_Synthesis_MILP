import gurobipy as gp
from gurobipy import GRB
from solver import model_solver  
from visualize_tree_levels import visualize_tree_levels

def compute_explainability_score(solution):
    model = solution["model"]
    I = solution["I"]
    P = solution["P"]
    u = solution["u"]
    o_u = solution["o_u"]

    if model.status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
        raise RuntimeError("No solution available to compute explainability score.")

    term1 = sum(1.0 - u[i].X for i in I)
    term2 = sum(o_u[i, p].X for i in I for p in P)
    return term1 + term2


def final_tree(lam, tau, solution, filename="final_tree.png"):
    I = solution["I"]     # internal nodes
    P = solution["P"]     # predicates
    L = solution["L"]     # leaf dictionary

    print("\n=== Lambda values (lam[i,p]) ===")
    for i in I:
        for p in P:
            val = float(getattr(lam[i, p], "X", lam[i, p]))
            print(f"lam[{i},{p}] = {val:.4f}")

    print("\n=== Tau values (tau[i,c,j]) ===")
    for (i, c, j), var in tau.items():
        val = float(getattr(var, "X", var))
        print(f"tau[{i},{c},{j}] = {val:.4f}")

    # Just call your visualize function
    visualize_tree_levels(
        lam=lam,
        tau=tau,
        I=I,
        P=P,
        L=L,
        filename=filename
    )



def reconstruct_tree(lam, tau, depth, node_number, solution):
    """
    Greedily fix lam and tau choices at each internal node by:
      1. Picking the predicate with the largest lam[i,p].X
      2. Picking the best child j for each bucket c with the largest tau[i,c,j].X
    Then add constraints to fix these choices and re-optimize.
    Works recursively until all internal nodes are covered.
    """
    print("Starting procedure for node ", str(node_number))
    model = solution["model"]
    P = solution["P"]
    C = solution["C"]
    I = solution["I"]

    def safe_val(var):
        return var.X if hasattr(var, "X") else float(var)

    # --- Step 1: Pick the predicate with max lam value for this node ---
    max_p = max(P, key=lambda p: lam[node_number, p].X)

    # Fix best predicate = 1, all others = 0
    model.addConstr(lam[node_number, max_p] == 1, name=f"fix_lam_{node_number}_{max_p}")
    for p in P:
        if p != max_p:
            model.addConstr(lam[node_number, p] == 0, name=f"fix_lam_{node_number}_{p}")

    # --- Step 2: For each bucket, pick the best child transition ---
    for c in C:
        # find the best child j (must exist in tau)
        candidates = [(j, tau[node_number, c, j].X)
                      for j in range(node_number + 1, I[-1] + 1)
                      if (node_number, c, j) in tau]

        if candidates:
            max_j, _ = max(candidates, key=lambda x: x[1])
            # Fix chosen transition
            model.addConstr(tau[node_number, c, max_j] == 1,
                            name=f"fix_tau_{node_number}_{c}_{max_j}")
            # Fix all other transitions to 0
            for j, _ in candidates:
                if j != max_j:
                    model.addConstr(tau[node_number, c, j] == 0,
                                    name=f"fix_tau_{node_number}_{c}_{j}")

    # --- Step 3: Re-optimize the model with these fixes ---
    model.update()
    model.optimize()
    for v in model.getVars():
            if v.VarName.startswith("u"):
                print(f"{v.VarName} = {v.X}")
    # --- Step 4: Recursive call to the next internal node ---
    if node_number + 1 < len(I):
        reconstruct_tree(lam, tau, depth + 1, node_number + 1, solution)


def main():
    """
    Main entry point:
    1. Build and solve the MILP (model_solver).
    2. Reconstruct the tree greedily (reconstruct_tree).
    3. Visualize the final fixed tree (final_tree).
    """
    # Step 1: Solve the MILP
    solution = model_solver()

    # Step 2: Greedy reconstruction of lam and tau
    

    print("\n--- Starting greedy reconstruction of the tree ---")
    reconstruct_tree(solution["lam"], solution["tau"], depth=0, node_number=0, solution=solution)
    # solution["model"].update()
    # Step 3: Plot the final fixed tree
    print("\n--- Final tree visualization ---")
    final_tree(solution["lam"], solution["tau"], solution, filename="final_tree.png")
    print("Final tree saved as final_tree.png")
    

if __name__ == "__main__":
    main()



