import gurobipy as gp
from gurobipy import GRB
from encoding import node_order,tree_constraints, sample_constraints, reachability_constraints, objective
from helper_functions import read_features,num_buckets, df
from visualize_tree_levels import visualize_tree_levels


def model_solver(I, C):
    I = range(I)
    C = range(C)
    model = gp.Model("pareto_optimal_explanations")
    # model.setParam("Threads", 40)  
    # I = range(int(input("Enter the number of nodes:")))
    read_features()
    from helper_functions import pred_id
    P = range(pred_id)
    # C = range(int(input("Enter the maximum number of buckets you want:")))
    S = range(len(df))
    labels = df["label"].unique()
    L = {f"L{i}" : label for i,label in enumerate(labels)}
    lam = model.addVars(I,P, vtype=GRB.INTEGER ,lb = 0.0, ub = 1.0, name = "lam")
    # tau = model.addVars(((i,c,j) for i in I for c in C for j in list(I)+list(L.keys()) if node_order(j)>i), vtype=GRB.CONTINUOUS, lb=0.0 , ub = 1.0 , name ="tau")
    # INTEGER tau for i = 0
    tau0 = model.addVars(((i,c,j) for i in I if i%5 != 0 for c in C for j in list(I)+list(L.keys()) if node_order(j) > i),
                        vtype=GRB.INTEGER, lb=0.0, ub=1.0, name="tau")

    # INTEGER tau for i > 0
    tau_rest = model.addVars(((i,c,j) for i in I if i %5 == 0 for c in C for j in list(I)+list(L.keys()) if node_order(j) > i),
                            vtype=GRB.CONTINUOUS, name="tau")
    tau = gp.tupledict()
    tau.update(tau0)
    tau.update(tau_rest)
    tree_constraints(model,lam,tau,I,P,C,L,num_buckets)
    # lam0 = model.addVars([0], P, vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="lam")

    # # CONTINUOUS for nodes > 0
    # lam_rest = model.addVars(range(1, len(I)), P, vtype=GRB.CONTINUOUS, name="lam")

    # # Merge into one dictionary
    # lam = gp.tupledict()
    # lam.update(lam0)
    # lam.update(lam_rest)
    m = model.addVars(((i,s) for i in list(I)+list(L.keys()) for s in S), vtype=GRB.CONTINUOUS , lb=0.0 , ub = 1.0 , name="m")
    b = model.addVars(I,C,S, vtype=GRB.CONTINUOUS, lb = 0.0 , ub = 1.0 , name = "b")
    d = model.addVars(((i,c,j,s)  for i in I for c in C for j in list(I)+list(L.keys()) if node_order(j)>i for s in S) ,vtype=GRB.CONTINUOUS , lb=0.0 , ub=1.0, name = "d")
    u = model.addVars(I, vtype=GRB.CONTINUOUS , lb = 0.0 , ub = 1.0 , name = "u")
    sample_constraints(model,m,S,lam,tau,u,I,P,C,L,b,d)
    z_u = model.addVars(((i,c,j) for i in I for c in C for j in list(I)+list(L.keys()) if node_order(j)>i), vtype=GRB.CONTINUOUS, lb=0.0 , ub = 1.0 , name ="z_u")
    o_u = model.addVars(I,P, vtype = GRB.CONTINUOUS , lb = 0.0 , ub = 1.0 , name = "o_u")
    reachability_constraints(model, lam, tau, u , z_u , I , C , P , o_u , L)
    objective(model, u , o_u , m , I , P , S)
    model.update()
    model.optimize()
    if model.status == GRB.INFEASIBLE:
        print("Model is infeasible. Computing IIS...")
    if model.status == GRB.OPTIMAL or model.status == GRB.SUBOPTIMAL:
        print("Objective value:", model.objVal)
        for v in model.getVars():
            if (v.VarName.startswith("o_u") or v.VarName.startswith("u") or v.VarName.startswith("m[0") or v.VarName.startswith("lam") or v.VarName.startswith("tau")) :
                print(f"{v.VarName} = {v.X}")       
        print("------------------------------------------------------------------------")
        # for v in model.getVars():
        #     # if v.VarName.startswith("u") or v.VarName.startswith("o"):
        #     print(f"{v.VarName} = {v.X}")
        print("------------------------------------------------------------------------")
        visualize_tree_levels(lam, tau, I, P, L)
    return {
        "model": model,
        "I": list(I),
        "P": list(P),
        "C":list(C),
        "L": {f"L{i}" : label for i,label in enumerate(labels)},
        "u": u,
        "o_u": o_u,
        "lam": lam,  
        "tau": tau, 
        "m": m,
        "S": S      
    }

def main():
    model_solver()

if __name__ == "__main__":
    main()
