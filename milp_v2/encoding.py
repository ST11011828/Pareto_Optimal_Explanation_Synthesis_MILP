import gurobipy as gp
from gurobipy import GRB
from helper_functions import func, return_weight , return_max_weight
MAX_EXPLANATION = 1037
# helper to order internal nodes (ints) before leaves ("L0", "L1", ...)
def node_order(j):
    if isinstance(j, int):
        return j
    if isinstance(j, str) and j.startswith("L") and j[1:].isdigit():
        return 10000 + int(j[1:])
    raise ValueError(f"Unexpected node id: {j}")

def tree_constraints(model, lam, tau, I, P, C , L , B_P):
    #every internal node is assigned exactly one predicate
    for i in I:
        model.addConstr(gp.quicksum(lam[i,p] for p in P) == 1)
    #unique transitions
    for i in I:
            for p in P:
                    for c in C:
                            if c< B_P(p):
                                model.addConstr( (lam[i,p] + gp.quicksum(tau[(i,c,j)] for j in list(I) + list(L.keys()) if node_order(j)>i)) <= 2)
                                model.addConstr( lam[i,p] <=  gp.quicksum(tau[(i,c,j)] for j in list(I) + list(L.keys()) if node_order(j)>i) )
                                for j in list(I) : 
                                            if node_order(j)>i:
                                                    #parent and child won't have the same predicate
                                                    # TODO: add the constraint that shows across any path the same predicate cannot be used twice
                                                    model.addConstr( lam[i,p] + tau[(i,c,j)] + lam[j,p] <=2)
    #consistency constraints
    for i in I:
            for p in P:
                    if B_P(p)<=C[-1]:
                        for c in C :
                                if c>=B_P(p):
                                    model.addConstr( (lam[i,p] + gp.quicksum(tau[(i,c,j)] for j in list(I) + list(L.keys()) if node_order(j)>i)) <= 1 , name ="consistency")

def sample_constraints(model,m , S, lam , tau , u, I ,  P , C , L , b , d):
    for s in S:
        #labelling the leaves 
        for l,label in L.items():
            model.addConstr(m[(l,s)] == func(s,label), name="leaf")
        for i in I:
            # recursively labelling the internal nodes
            for c in C:
                model.addConstr( b[(i,c,s)] == gp.quicksum(func(s,p,c)*lam[i,p] for p in P) , name="forming_b")
                for j in list(I) + list(L.keys()):
                    if node_order(j)>i:
                        model.addConstr(b[(i,c,s)] + m[(j,s)] + tau[(i,c,j)] -2<= m[(i,s)], name ="m_lower_bound")
                        model.addConstr(d[(i,c,j,s)] >= b[(i,c,s)] + m[(j,s)] + tau[(i,c,j)] -2 , name = "d_upper_bound")
                        model.addConstr(d[(i,c,j,s)] <= b[(i,c,s)])
                        model.addConstr(d[(i,c,j,s)] <= m[(j,s)])
                        model.addConstr(d[(i,c,j,s)] <= tau[(i,c,j)])
            
                model.addConstr((gp.quicksum(d[(i,c,j,s)] for j in list(I)+list(L.keys()) if node_order(j)>i)) <= b[(i,c,s)])
                # model.addConstr((gp.quicksum(d[(i,c,j,s)] for c in C for j in list(I)+list(L.keys()) if node_order(j)>i)) <= (gp.quicksum(tau[(i,c,j)] for c in C for j in list(I)+list(L.keys()) if node_order(j)>i)))
            model.addConstr(m[(i,s)] <= gp.quicksum(d[(i,c,j,s)] for c in C for j in list(I)+list(L.keys()) if node_order(j)>i) , name ="m upper bound")


def reachability_constraints(model, lam, tau, u , z_u , I , C , P , o_u , L):
    #root active
    model.addConstr(u[0] == 1, name = "root_active")
    #recursively labelling the tree top down
    for j in list(I)+list(L.keys()):
        for i in I:
            if i<node_order(j):
                for c in C:
                    if j in I:
                        model.addConstr(u[j]>=tau[(i,c,j)]+u[i]-1)
                        model.addConstr(z_u[(i,c,j)]>= u[i]+tau[(i,c,j)]-1)
                        model.addConstr(z_u[(i,c,j)] <= u[i])
                        model.addConstr(z_u[(i,c,j)]<=tau[(i,c,j)])
        if j in I:
            if j>0:
                model.addConstr(u[j]<=gp.quicksum(z_u[(i,c,j)] for i in I if i<node_order(j) for c in C))
    for i in I:
        for p in P:
            # model.addConstr(2*o_u[i,p]<=u[i]+lam[i,p])
            model.addConstr(o_u[i,p] >= u[i] + lam[i,p] -1)
            model.addConstr(o_u[i,p] <= u[i])
            model.addConstr(o_u[i,p] <= lam[i,p])
    for i in I:
         model.addConstr(gp.quicksum(o_u[i,p] for p in P) <=1)
    model.addConstr(gp.quicksum( 1- u[i] for i in I) + gp.quicksum(return_weight(p)*o_u[i,p] for i in I for p in P)<=MAX_EXPLANATION)

def objective(model, u , o_u , m , I , P , S):
    model.setObjective((gp.quicksum( 1- u[i] for i in I) + gp.quicksum(return_weight(p)*o_u[i,p] for i in I for p in P) + gp.quicksum(m[0,s] for s in S)), GRB.MAXIMIZE)

