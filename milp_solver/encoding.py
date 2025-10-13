from inputs import Input
import gurobipy as gp
from gurobipy import GRB


def node_order(j):
    if isinstance(j, int):
        return j
    if isinstance(j, str) and j.startswith("L") and j[1:].isdigit():
        return 10000 + int(j[1:])
    return 999999  


'''
Write a class Encoding with the following instance attributes:
inp(Input)
tau, lam , ...... other encoding variables
ints_pos - specifying for which i tau_{icj} and lam_{ip} should be made integral
root - which node should be considered as the root
Instance functions:
tree_constraints()
samples_constraints()
reachability_constraints()
objective() - sets the objective, optimizes the model and returns the solution
'''

class Encoding:
    def __init__(self, int_pos , inp:Input , root):
        self.inp = inp
        self.int_pos = set(int_pos)
        self.root = root
        self.MAX_EXPLANATION = 1037
        self.I = range(self.inp.max_nodes)
        self.C= range(self.inp.c_max)
        self.P = range(len(self.inp.predicates))
        self.S = range(len(self.inp.samples.updated_samples))
        self.L = {f"L{i}":label for i,label in enumerate(self.inp.leaves)}
        
        self.model = gp.Model("pareto_points_exploration")
        lam_int = self.model.addVars(
            ((i,p) for i in self.I if i in self.int_pos for p in self.P) , vtype = GRB.INTEGER, lb = 0.0, ub =1.0, name = "lam"
        )
        lam_cont = self.model.addVars(
            ((i,p) for i in self.I if i not in self.int_pos for p in self.P) , vtype = GRB.CONTINUOUS, lb = 0.0, ub =1.0, name = "lam"
        )
        self.lam = gp.tupledict()
        self.lam.update(lam_int)
        self.lam.update(lam_cont)

        all_nodes = list(self.I) + list(self.L.keys())
        tau_int = self.model.addVars(
            ((i,c,j) for i in self.I if i in self.int_pos
             for c in self.C
             for j in all_nodes if node_order(j) > i),
             vtype= GRB.INTEGER, lb=0.0, ub = 1.0, name ="tau"
        )
        tau_cont = self.model.addVars(
            ((i,c,j) for i in self.I if i not in self.int_pos
             for c in self.C
             for j in all_nodes if node_order(j) > i),
             vtype= GRB.CONTINUOUS, lb=0.0, ub = 1.0, name ="tau"
        )
        self.tau = gp.tupledict()
        self.tau.update(tau_int)
        self.tau.update(tau_cont)

        self.m = self.model.addVars(((i,s) for i in all_nodes for s in self.S), vtype=GRB.CONTINUOUS , lb=0.0 , ub = 1.0 , name="m")
        self.b = self.model.addVars(((i, c, s) for i in self.I for c in self.C for s in self.S),vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="b")
        self.d = self.model.addVars(((i, c, j, s) for i in self.I for c in self.C for j in all_nodes if node_order(j) > i for s in self.S),vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="d")
        self.u = self.model.addVars(self.I, vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="u")
        self.z_u = self.model.addVars(((i, c, j) for i in self.I for c in self.C for j in all_nodes if node_order(j) > i),vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="z_u")
        self.o_u = self.model.addVars(((i, p) for i in self.I for p in self.P),vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="o_u")

    def B_P(self, p):
        return self.inp.predicates[p].num_buckets
    
    def tree_constraints(self):
        # every internal node is assigned exactly one predicate
        for i in self.I:
            self.model.addConstr(gp.quicksum(self.lam[i, p] for p in self.P) == 1)

        # unique transitions + parent-child predicate distinctness + consistency
        all_nodes = list(self.I) + list(self.L.keys())
        for i in self.I:
            for p in self.P:
                for c in self.C:
                    if c < self.B_P(p):
                        self.model.addConstr((self.lam[i, p] + gp.quicksum(self.tau[i, c, j] for j in all_nodes if node_order(j) > i)) <= 2)
                        self.model.addConstr(self.lam[i, p] <= gp.quicksum(self.tau[i, c, j] for j in all_nodes if node_order(j) > i))
                        for j in self.I:
                            if node_order(j) > i:
                                self.model.addConstr(self.lam[i, p] + self.tau[i, c, j] + self.lam[j, p] <= 2)

        # consistency constraints (no child if c >= num_buckets)
        for i in self.I:
            for p in self.P:
                if self.B_P(p) <= self.C[-1] :
                    for c in self.C:
                        if c >= self.B_P(p):
                            self.model.addConstr((self.lam[i, p] + gp.quicksum(self.tau[i, c, j] for j in all_nodes if node_order(j) > i)) <= 1,name="consistency")

    def sample_constraints(self):
        all_nodes = list(self.I) + list(self.L.keys())

        for s in self.S:
            for l_key,l_value in self.L.items():
                self.model.addConstr(self.m[l_key,s] == self.inp.func(s,l_value), name = "leaf")

            for i in self.I:
                for c in self.C:
                    # b[i,c,s] = sum_p func(s,p,c) * lam[i,p]
                    self.model.addConstr(
                        self.b[i, c, s] == gp.quicksum(self.inp.func(s, p, c) * self.lam[i, p] for p in self.P),
                        name="forming_b"
                    )

                    for j in all_nodes:
                        if node_order(j) > i:
                            # m lower bound
                            self.model.addConstr(self.b[i, c, s] + self.m[j, s] + self.tau[i, c, j] - 2 <= self.m[i, s],
                                                 name="m_lower_bound")
                            # d triangle bounds
                            self.model.addConstr(self.d[i, c, j, s] >= self.b[i, c, s] + self.m[j, s] + self.tau[i, c, j] - 2,
                                                 name="d_upper_bound")
                            self.model.addConstr(self.d[i, c, j, s] <= self.b[i, c, s])
                            self.model.addConstr(self.d[i, c, j, s] <= self.m[j, s])
                            self.model.addConstr(self.d[i, c, j, s] <= self.tau[i, c, j])

                    # flow consistency
                    self.model.addConstr(
                        gp.quicksum(self.d[i, c, j, s] for j in all_nodes if node_order(j) > i) <= self.b[i, c, s]
                    )

                # m upper bound
                self.model.addConstr(
                    self.m[i, s] <= gp.quicksum(self.d[i, c, j, s] for c in self.C for j in all_nodes if node_order(j) > i),
                    name="m_upper_bound"
                )

    def reachability_constraints(self):
        all_nodes = list(self.I) + list(self.L.keys())

        # root active
        self.model.addConstr(self.u[self.root] == 1, name="root_active")

        #all nodes with index less than root inactive
        for j in self.I:
            if j < self.root:
                self.model.addConstr(self.u[j] ==0 , name="nodes_less_than_root_inactive")

        # top-down reachability
        for j in all_nodes:
            for i in self.I:
                if i < node_order(j) :
                    for c in self.C:
                        if j in self.I:
                            self.model.addConstr(self.u[j] >= self.tau[i, c, j] + self.u[i] - 1)
                            self.model.addConstr(self.z_u[i, c, j] >= self.u[i] + self.tau[i, c, j] - 1)
                            self.model.addConstr(self.z_u[i, c, j] <= self.u[i])
                            self.model.addConstr(self.z_u[i, c, j] <= self.tau[i, c, j])

            if j in self.I and j != self.root:
                self.model.addConstr(
                    self.u[j] <= gp.quicksum(self.z_u[i, c, j] for i in self.I if i < node_order(j) for c in self.C)
                )

        # o_u linking: only one active predicate per active node
        for i in self.I:
            for p in self.P:
                self.model.addConstr(self.o_u[i, p] >= self.u[i] + self.lam[i, p] - 1)
                self.model.addConstr(self.o_u[i, p] <= self.u[i])
                self.model.addConstr(self.o_u[i, p] <= self.lam[i, p])
        for i in self.I:
            self.model.addConstr(gp.quicksum(self.o_u[i, p] for p in self.P) <= 1)

        # explanation budget
        self.model.addConstr(
            gp.quicksum(1 - self.u[i] for i in self.I) +
            gp.quicksum(self.inp.predicates[p].weight * self.o_u[i, p] for i in self.I for p in self.P)
            <= self.MAX_EXPLANATION
        )

    def objective(self):
        self.model.setObjective(
            gp.quicksum(1 - self.u[i] for i in self.I) +
            gp.quicksum(self.inp.predicates[p].weight * self.o_u[i, p] for i in self.I for p in self.P) +
            gp.quicksum(self.m[self.root, s] for s in self.S),
            GRB.MAXIMIZE
        )
        self.model.optimize()
        for v in self.model.getVars():
            if (v.VarName.startswith("o_u") or v.VarName.startswith("u") or v.VarName.startswith("m[0") or v.VarName.startswith("lam") or v.VarName.startswith("tau")) :
                print(f"{v.VarName} = {v.X}") 

        # return the objects so caller can inspect .X values
        return {
            "status": self.model.status,
            "obj": (self.model.objVal if self.model.status in (GRB.OPTIMAL, GRB.SUBOPTIMAL) else None),
            "lam": self.lam,
            "tau": self.tau,
            "u": self.u,
            "o_u": self.o_u,
            "m": self.m,
            "b": self.b,
            "d": self.d,
            "z_u": self.z_u,
            "I": list(self.I),
            "P": list(self.P),
            "C": list(self.C),
            "L": self.L,
            "S": list(self.S),
            "model": self.model
        }
    
    def calculate_explainability(self):
        return sum(1-self.u[i].X for i in self.I) + sum(self.inp.predicates[p].weight*self.o_u[i,p].X for i in self.I for p in self.P)
    
    def calculate_correctness(self):
        return sum(self.m[self.root, s].X for s in self.S)*1.0/len(self.S)


    
def main():
    inp = Input("examples/random_dataset", max_nodes=6)
    ints_pos = {0,1,2,3,4,5}             # make root’s lam and tau integral (add more indices if you like)
    enc = Encoding(ints_pos, inp, root=1)
    enc.tree_constraints()
    enc.sample_constraints()
    enc.reachability_constraints()
    sol = enc.objective()

    print("Status:", sol["status"])
    print("Obj:", sol["obj"])
            


if __name__ == "__main__":
    main()
    