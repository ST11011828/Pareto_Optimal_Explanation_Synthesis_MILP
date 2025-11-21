import os
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import gurobipy as gp
from gurobipy import GRB
import time

from inputs import Input, Predicate
from encoding import Encoding


class Pareto_Points:
    def __init__(self,dir_name, max_nodes, lam_int_nodes , tau_int_nodes , u_int_nodes, m_int_nodes, root:int):
        self.root = root
        self.inp = Input(dir_name, max_nodes)
        self.pareto_points= []
        self.enc = Encoding(lam_int_nodes, tau_int_nodes , u_int_nodes , m_int_nodes, self.inp, root)

    def find_pareto_points(self, e_l, e_u , c_l , c_u):
        if (e_l is not None and e_u is not None and e_l > e_u) or (c_l is not None and c_u is not None and c_l > c_u):
            return
        print("-----------------------------------------------------------------")
        print(f"e_l={e_l}, e_u={e_u}, c_l={c_l}, c_u={c_u}")
        print("Inside the find_pareto_points function")
        # possible_pareto_point = self.enc.solve(e_l, e_u , c_l , c_u)
        res = self.enc.solve(e_l, e_u , c_l , c_u)
        print("Solving done")
        if self.enc.model.Status == GRB.INFEASIBLE:
            print("Returning because the model was infeasible")
            return
        c = self.enc.calculate_correctness()
        e = self.enc.calculate_explainability()
        print("--------------------")
        print(f"c={c}, e={e}")
        diagram_path = None if res is None else res.get("diagram_path")  
        print("Appending to pareto_points list")
        # c_final = round(c/self.enc.C_QUANT)*self.enc.C_QUANT
        c_final = max(0.0, min(1.0, round(c / self.enc.C_QUANT) * self.enc.C_QUANT))
        assert abs(c_final-c)<= 0.5 * self.enc.C_QUANT + 1e-12, f"Moving away because of the rounding too much!, by {abs(c_final-c)}"
        e_final = round(e,self.enc.E_ROUNDING_LIMIT)
        self.pareto_points.append([c_final, e_final, diagram_path]) 
        if e_u is not None and e_l is not None and e_u == e_l:
            return
        if c_u is not None and c_l is not None and c_u == c_l:
            return
        # print("Appending to pareto_points list")
        # self.pareto_points.append([c,e])
        if e_u is not None and e+1 <= e_u:
            print("Searching solutions with greater explainability")
            self.find_pareto_points(e+1,e_u,c_l,c - 1.0/len(self.enc.S) )
        else:
            if e_u is None:
                print("Searching solutions with greater explainability with e_u None")
                self.find_pareto_points(e+1,e_u,c_l,c- 1.0/len(self.enc.S) )
        if e_l is not None and e-1 >= e_l:
            print("Searching for solutions with greater correctness")
            self.find_pareto_points(e_l,e-1,c+ 1.0/len(self.enc.S),c_u)
        else:
            if e_l is None:
                print("Searching for solutions with greater correctness with e_l None")
                self.find_pareto_points(e_l,e-1,c+ 1.0/len(self.enc.S),c_u)
            else:
                return
            
    def clean_pareto_points(self):
        #arrange the pareto points in increasing order of correctness
        self.pareto_points.sort(key=lambda t: t[0])
        n = len(self.pareto_points)
        #removing points appropriately when their correctness is same
        pareto_so_far =0
        for i in range(n):
            c,e,path = self.pareto_points[i]
            max_expl_so_far = e
            best_path_so_far = path
            while pareto_so_far > 0 and self.pareto_points[pareto_so_far-1][0] == c:
                if self.pareto_points[pareto_so_far-1][1] > max_expl_so_far:
                    max_expl_so_far = self.pareto_points[pareto_so_far-1][1]
                    best_path_so_far = self.pareto_points[pareto_so_far-1][2]
                pareto_so_far = pareto_so_far -1
            self.pareto_points[pareto_so_far] = [c,max_expl_so_far,best_path_so_far]
            pareto_so_far = pareto_so_far +1

        del self.pareto_points[pareto_so_far:]
        
        # whenever you find a point that has greater explainability than the previous point, keep popping the previous point until you reach a stage where the previous point has greater explainability than the current point.
        
        n = len(self.pareto_points)
        pareto_so_far = 0
        for i in range(n):
            c,e,path = self.pareto_points[i]
            while pareto_so_far > 0 and self.pareto_points[pareto_so_far-1][1]<=e:
                pareto_so_far = pareto_so_far -1
            self.pareto_points[pareto_so_far] = [c,e,path]
            pareto_so_far = pareto_so_far + 1

        del self.pareto_points[pareto_so_far:]

        # delete all the decision diagrams that are not in the final pareto_points list
        keep_paths = {path for _, _, path in self.pareto_points if path}  # paths we want to keep
        diag_dir = os.path.join(self.inp.filename, "results", f"I_{self.enc.inp.max_nodes}_int_nodes_{self.enc._int_tag}", "decision_diagrams")
        if os.path.isdir(diag_dir):
            for fname in os.listdir(diag_dir):
                fpath = os.path.join(diag_dir, fname)
                if fpath not in keep_paths:
                    os.remove(fpath)

        
    def write_pareto_points(self):
        out_dir = os.path.join(self.inp.filename, "results", f"I_{self.enc.inp.max_nodes}_int_nodes_{self.enc._int_tag}", "pareto_points")
        os.makedirs(out_dir, exist_ok=True)
        fn = f"pareto_points_I{self.inp.max_nodes}_C{self.inp.c_max}.csv"
        with open(os.path.join(out_dir, fn), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["c", "e"])
            for c, e, _ in self.pareto_points:
                w.writerow([c, e])

    def plot_pareto_points(self):
        out_dir = os.path.join(self.inp.filename, "results", f"I_{self.enc.inp.max_nodes}_int_nodes_{self.enc._int_tag}", "pareto_curves")
        os.makedirs(out_dir, exist_ok=True)
        xs = [c for c, _,_ in self.pareto_points]
        ys = [e for _, e,_ in self.pareto_points]
        plt.figure()
        plt.plot(xs, ys, marker="o")
        plt.xlabel("Correctness")
        plt.ylabel("Explainability")
        plt.tight_layout()
        fn = f"pareto_curve_I{self.inp.max_nodes}_C{self.inp.c_max}.png"
        plt.savefig(os.path.join(out_dir, fn), dpi=300, bbox_inches="tight")
        plt.close()

    def cumulate_pareto_points(self):
        self.find_pareto_points(None, None, None, None)
        self.clean_pareto_points()
        self.write_pareto_points()
        self.plot_pareto_points()

# def main():
#     start = time.perf_counter()
#     pp_ = Input("examples/wine",3)
#     pp = Pareto_Points("examples/wine",5,{0,1,2,3,4},0)
#     pp.cumulate_pareto_points()
#     end = time.perf_counter()
#     print(f"Elapsed: {end - start:.2f} s")

def main():
    start = time.perf_counter()
    _ = Input("examples/wine", 3)
    pp = Pareto_Points(
        "examples/wine", 5,
        lam_int_nodes={0,1,2,3,4},
        tau_int_nodes={0,1,2,3,4},
        u_int_nodes=set(),
        m_int_nodes=set(),
        root=0
    )
    pp.cumulate_pareto_points()
    end = time.perf_counter()
    print(f"Elapsed: {end - start:.2f} s")


if __name__ == "__main__":
    main()