import matplotlib.pyplot as plt
from matplotlib import cm, colors as mcolors
from collections import deque
from inputs import Input
import gurobipy as gp
from gurobipy import GRB
import os

MAX_NODES = 10000

def node_order(j):
    if isinstance(j, int):
        return j
    if isinstance(j, str) and j.startswith("L") and j[1:].isdigit():
        return MAX_NODES + int(j[1:]) #NOTE:use macro here ------> Done!
    return MAX_NODES  


'''
Instance attributes:
inp(Input)
tau, lam , ...... other encoding variables
ints_pos - specifying for which i tau_{icj} and lam_{ip} should be made integral
root - which node should be considered as the root
Instance functions:
tree_constraints() - adds the constraints that builds up the tree
samples_constraints() - adds the contraints that parse the samples on the tree for calculating correctness
reachability_constraints() - adds the constraints that parse the tree for reachability
objective() - sets the objective, optimizes the model and returns the solution
'''
class Encoding:
    def __init__(self, lam_int_nodes, tau_int_nodes , u_int_nodes , m_int_nodes, inp:Input , root , MAX_EXPLANATION = 1037): #NOTE:give better name to int_pos
        self.inp = inp
        self.lam_int_nodes = set(lam_int_nodes) #converting to set because it is faster to check containment in set
        self.tau_int_nodes = set(tau_int_nodes)
        self.u_int_nodes = set(u_int_nodes)
        self.m_int_nodes = set(m_int_nodes)
        self.root = root
        self.MAX_EXPLANATION = MAX_EXPLANATION 
        self.I = range(self.inp.max_nodes)
        self.C= range(self.inp.c_max)
        self.P = range(len(self.inp.predicates))
        self.S = range(len(self.inp.samples.updated_samples))
        self.L = {f"L{i}":label for i,label in enumerate(self.inp.leaves)}
        self._built = False
        def _fmt(nodes):
            return "none" if not nodes else "_".join(str(i) for i in sorted(nodes))
        self._int_tag = (
            f"l_{_fmt(self.lam_int_nodes)}"
            f"_tau_{_fmt(self.tau_int_nodes)}"
            f"_u_{_fmt(self.u_int_nodes)}"
            f"_m_{_fmt(self.m_int_nodes)}"
        )
        # self._int_tag = "none" if not self.int_nodes else "_".join(str(i) for i in sorted(self.int_nodes))
        self.C_QUANT = 1.0/len(self.S)
        self.E_ROUNDING_LIMIT = 6

        self.model = gp.Model("pareto_points_exploration")
        lam_int = self.model.addVars(
            ((i,p) for i in self.I if i in self.lam_int_nodes for p in self.P) , vtype = GRB.INTEGER, lb = 0.0, ub =1.0, name = "lam"
        )
        lam_cont = self.model.addVars(
            ((i,p) for i in self.I if i not in self.lam_int_nodes for p in self.P) , vtype = GRB.CONTINUOUS, lb = 0.0, ub =1.0, name = "lam"
        )
        self.lam = gp.tupledict()
        self.lam.update(lam_int)
        self.lam.update(lam_cont)
        # self.lam = self.model.addVars(((i,p) for i in self.I for p in self.P), vtype=GRB.INTEGER , lb=0.0 , ub = 1.0 , name="lam")
        all_nodes = list(self.I) + list(self.L.keys())
        tau_int = self.model.addVars(
            ((i,c,j) for i in self.I if i in self.tau_int_nodes
             for c in self.C
             for j in all_nodes if node_order(j) > i),
             vtype= GRB.INTEGER, lb=0.0, ub = 1.0, name ="tau"
        )
        tau_cont = self.model.addVars(
            ((i,c,j) for i in self.I if i not in self.tau_int_nodes for c in self.C for j in all_nodes if node_order(j) > i ), vtype= GRB.CONTINUOUS, lb=0.0, ub = 1.0, name ="tau"
        )
        self.tau = gp.tupledict()
        self.tau.update(tau_int)
        # self.tau.update(tau_int_default)
        self.tau.update(tau_cont)

        # self.m = self.model.addVars(((i,s) for i in all_nodes for s in self.S), vtype=GRB.CONTINUOUS , lb=0.0 , ub = 1.0 , name="m")
        m_int = self.model.addVars(
            ((i,s) for i in all_nodes if i in self.m_int_nodes for s in self.S) , vtype = GRB.INTEGER, lb = 0.0, ub =1.0, name = "m"
        )
        m_cont = self.model.addVars(
            ((i,s) for i in all_nodes if i not in self.m_int_nodes for s in self.S) , vtype = GRB.CONTINUOUS, lb = 0.0, ub =1.0, name = "m"
        )
        self.m = gp.tupledict()
        self.m.update(m_int)
        self.m.update(m_cont)
        self.b = self.model.addVars(((i, c, s) for i in self.I for c in self.C for s in self.S),vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="b")
        self.d = self.model.addVars(((i, c, j, s) for i in self.I for c in self.C for j in all_nodes if node_order(j) > i for s in self.S),vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="d")
        # self.u = self.model.addVars(self.I, vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="u")
        u_int = self.model.addVars(
            (i for i in self.I if i in self.u_int_nodes) , vtype = GRB.INTEGER, lb = 0.0, ub =1.0, name = "u"
        )
        u_cont = self.model.addVars(
            (i for i in self.I if i not in self.u_int_nodes ) , vtype = GRB.CONTINUOUS, lb = 0.0, ub =1.0, name = "u"
        )
        self.u = gp.tupledict()
        self.u.update(u_int)
        self.u.update(u_cont)
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
        #NOTE: State assumptions beforehand
        for i in self.I:
            for c in self.C:
                self.model.addConstr(gp.quicksum(self.tau[i,c,j] for j in all_nodes if node_order(j)>i) == gp.quicksum(self.inp.valid_branch(c,p)*self.lam[i,p] for p in self.P))

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
            #labelling the leaf
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
                # self.model.addConstr(
                #     # self.m[i, s] <= gp.quicksum(self.d[i, c, j, s] for c in self.C for j in all_nodes if node_order(j) > i),
                #     name="m_upper_bound"
                # )
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
            (self.inp.max_weight+1)*gp.quicksum(1 - self.u[i] for i in self.I) +
            gp.quicksum(self.inp.predicates[p].weight * self.o_u[i, p] for i in self.I for p in self.P)
            <= self.MAX_EXPLANATION
        )

    def _build_constraints(self):
        if self._built:
            return
        self.tree_constraints()
        self.sample_constraints()
        self.reachability_constraints()
        self._built = True

    def solve(self, e_l , e_u , c_l , c_u ):
        #TODO: remove all the old constraints
        old_cons = [c for c in self.model.getConstrs() if c.ConstrName and c.ConstrName.startswith("temp_")]
        if old_cons:
            self.model.remove(old_cons)
            self.model.update()
        #adding all the fixed constraints
        self._build_constraints()
        # self.model.addConstr(self.m[0,1] == 1)
        #adding the new constraints
        if e_l is not None:
            self.model.addConstr((self.inp.max_weight+1)*gp.quicksum(1 - self.u[i] for i in self.I) +
            gp.quicksum(self.inp.predicates[p].weight * self.o_u[i, p] for i in self.I for p in self.P) >= e_l , name = "temp_e_lower")
        if e_u is not None:
            self.model.addConstr((self.inp.max_weight+1)*gp.quicksum(1 - self.u[i] for i in self.I) +
            gp.quicksum(self.inp.predicates[p].weight * self.o_u[i, p] for i in self.I for p in self.P) <= e_u , name = "temp_e_upper")
        if c_l is not None:
            self.model.addConstr(gp.quicksum(self.m[self.root, s] for s in self.S) >= c_l*len(self.S) , name = "temp_c_lower")
        if c_u is not None:
            self.model.addConstr(gp.quicksum(self.m[self.root, s] for s in self.S) <= c_u*len(self.S) , name = "temp_c_upper")
        self.model.setObjective(
            (self.inp.max_weight+1)*gp.quicksum(1 - self.u[i] for i in self.I) +
            gp.quicksum(self.inp.predicates[p].weight * self.o_u[i, p] for i in self.I for p in self.P) +
            gp.quicksum(self.m[self.root, s] for s in self.S),
            GRB.MAXIMIZE
        )
        diagram_path = None
        self.model.update()
        # self.model.write(f"I_{self.inp.max_nodes}_int_nodes_{self._int_tag}.lp") 
        self.model.optimize()
        if self.model.Status == GRB.OPTIMAL:
            for v in self.model.getVars():
                if (v.VarName.startswith("o_u") or v.VarName.startswith("u") or v.VarName.startswith("m") or v.VarName.startswith("lam") or v.VarName.startswith("tau")) :
                    print(f"{v.VarName} = {v.X}") 
            out_dir = os.path.join(self.inp.filename, "results",f"I_{self.inp.max_nodes}_int_nodes_{self._int_tag}", "decision_diagrams")
            os.makedirs(out_dir, exist_ok=True)
            diagram_path = os.path.join(out_dir, f"e_l_{e_l}_e_u_{e_u}_c_l_{c_l}_c_u_{c_u}.png")  
            self.plot_decision_diagram(edge_threshold=0.5, savepath=diagram_path)  
            # diagram_path = os.path.abspath(diagram_path)


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
            "model": self.model,
            "diagram_path": diagram_path
        }
    #NOTE
    
    def plot_decision_diagram(self, edge_threshold=0.5, savepath=None):
        """
        Draw the decision diagram from lam/tau.
        - Draw ALL edges (i,c)->j whose τ[i,c,j] >= edge_threshold.
        - Each parent i gets a unique base color; each bucket c is a lighter shade.
        - Leaves are placed at the bottom; root at the top.
        - Edge labels are black for readability.
        """

        # ---------- gather edges we will draw (ALL τ above threshold) ----------
        all_nodes = list(self.I) + list(self.L.keys())
        edges = []  # (i, j, c, τ_value)
        for i in self.I:
            for c in self.C:
                for j in all_nodes:
                    if node_order(j) > i:
                        val = float(self.tau[i, c, j].X)
                        if val >= edge_threshold:
                            edges.append((i, j, c, val))

        # ---------- build node labels (show ALL predicate names with lam values) ----------
        node_label = {}
        for i in self.I:
            lines = [str(i)]
            for p in self.P:
                pname = self.inp.predicates[p].pred_name
                lines.append(f"{pname}({float(self.lam[i, p].X):.2f})")
            node_label[i] = "\n".join(lines)
        for leaf_key, leaf_val in self.L.items():
            node_label[leaf_key] = f"{leaf_key}\n{leaf_val}"

        # ---------- compute vertical "levels": BFS for internal nodes, leaves at bottom ----------
        level = {self.root: 0}
        q = deque([self.root])

        # adjacency among internal nodes only (so the layout is top-down)
        adj = {}
        for i, j, c, v in edges:
            if isinstance(j, int):  # only internal children
                adj.setdefault(i, []).append(j)

        while q:
            u = q.popleft()
            for v in adj.get(u, []):
                if v not in level:
                    level[v] = level[u] + 1
                    q.append(v)

        max_internal_level = max(level.values()) if level else 0
        used_leaves = {j for _, j, _, _ in edges if isinstance(j, str)}
        bottom_level = max_internal_level + 1
        for lk in used_leaves:
            level[lk] = bottom_level

        # ---------- assign (x, y) positions: spread nodes on each level ----------
        levels_to_nodes = {}
        for n, L in level.items():
            levels_to_nodes.setdefault(L, []).append(n)
        for L in levels_to_nodes:
            levels_to_nodes[L].sort(key=lambda x: node_order(x))

        pos = {}
        for L, nodes_on_L in levels_to_nodes.items():
            count = len(nodes_on_L)
            for k, n in enumerate(nodes_on_L):
                x = k - (count - 1) / 2.0    # center them horizontally
                y = -L                        # higher L = lower y (top-down)
                pos[n] = (x, y)

        # ---------- color design: unique base per parent, clear shades per c ----------
        parents = sorted({i for i, _, _, _ in edges})
        base_map = cm.get_cmap('tab20', max(20, len(parents)))
        parent_base = {i: base_map(idx / max(1, len(parents)-1)) for idx, i in enumerate(parents)}

        # construct lightened shades for each bucket c of each parent i
        parent_c_color = {}
        for i in parents:
            base_rgb = mcolors.to_rgb(parent_base[i])
            cs_for_i = sorted({c for (pi, _, c, _) in edges if pi == i})
            steps = max(1, len(cs_for_i)-1)
            for rank, c in enumerate(cs_for_i):
                # alpha goes 0.20 -> 0.85 across c values (visibly distinct)
                alpha = 0.20 + 0.65 * (rank / steps if steps else 0.0)
                shade_rgb = (
                    (1 - alpha) * base_rgb[0] + alpha * 1.0,
                    (1 - alpha) * base_rgb[1] + alpha * 1.0,
                    (1 - alpha) * base_rgb[2] + alpha * 1.0,
                )
                parent_c_color[(i, c)] = mcolors.to_hex(shade_rgb)

        # ---------- draw ----------
        plt.figure(figsize=(12, 9))

        # nodes
        for n, (x, y) in pos.items():
            face = "lightgreen" if isinstance(n, str) else ("gold" if n == self.root else "skyblue")
            plt.scatter([x], [y], s=700, color=face, edgecolor="black", zorder=3)
            plt.text(x, y, node_label[n], ha="center", va="center", fontsize=8, zorder=4)

        # edges (ALL transitions above threshold)
        for i, j, c, val in edges:
            if i in pos and j in pos:
                xi, yi = pos[i]
                xj, yj = pos[j]
                col = parent_c_color.get((i, c), "#000000")
                width = 1.5 + 2.0 * float(val)           # a bit thicker for larger τ
                plt.plot([xi, xj], [yi, yj], color=col, linewidth=width, alpha=0.98, zorder=2)

                # label (always black). Slightly biased toward the child so it doesn't sit on node centers
                lx = 0.55 * xj + 0.45 * xi
                ly = 0.55 * yj + 0.45 * yi
                plt.text(lx, ly, f"c={c}, τ={val:.2f}", fontsize=8, color="black", zorder=5)

        plt.axis("off")
        plt.tight_layout()
        if savepath:
            plt.savefig(savepath, dpi=240, bbox_inches="tight")
            plt.close()
        else:
            print("There is no path to save the image in")
            plt.show() #removed because there is no display in cn07
    
    def calculate_explainability(self):
        return (self.inp.max_weight+1)*sum(1-self.u[i].X for i in self.I) + sum(self.inp.predicates[p].weight*self.o_u[i,p].X for i in self.I for p in self.P)
    
    def calculate_correctness(self):
        return sum(self.m[self.root, s].X for s in self.S)*1.0/len(self.S)
        # return sum(self.m[self.root, s].X for s in self.S)*1.0



def main():
    inp = Input("examples/wine", max_nodes=6)
    lam = {0,1,2,3,4,5}
    tau = {0,1,2,3,4,5}
    u   = set()          # keep u continuous in this test
    m   = set()          # keep m continuous in this test
    enc = Encoding(lam, tau, u, m, inp, root=0)
    enc.tree_constraints()
    enc.sample_constraints()
    enc.reachability_constraints()
    sol = enc.solve(None, None, 0.5, None)
    print(f"Explainability is {enc.calculate_explainability()}")
    print(f"Correctness is {enc.calculate_correctness()}")
    print("Status:", sol["status"])
    print("Obj:", sol["obj"])
    
# def main():
#     inp = Input("examples/wine", max_nodes=6)
#     ints_pos = {0,1,2,3,4,5}             # make root’s tau integral (add more indices if you like)
#     enc = Encoding(ints_pos, inp, root=0)
#     enc.tree_constraints()
#     enc.sample_constraints()
#     enc.reachability_constraints()
#     sol = enc.solve(None,None,0.5,None)
#     print(f"Explainability is {enc.calculate_explainability()}")
#     print(f"Correctness is {enc.calculate_correctness()}")

#     print("Status:", sol["status"])
#     print("Obj:", sol["obj"])
            


if __name__ == "__main__":
    main()
    