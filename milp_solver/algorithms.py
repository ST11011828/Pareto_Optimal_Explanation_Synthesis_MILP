# # algorithms.py
from inputs import Input
from pareto_points import Pareto_Points
from gurobipy import GRB

EPS = 1e-6

def Non_Trivial_tau(root, inp: Input):
    def _solve(curr_root, fixed_int_pos):
        pp = Pareto_Points(inp, fixed_int_pos, curr_root)
        pp.find_pareto_points()
        sol = pp.pareto_points

        if len(sol) != 1:
            return len(sol), fixed_int_pos

        enc = pp.enc
        all_nodes = list(enc.I) + list(enc.L.keys())
        next_nodes = []

        for c in enc.C:
            for j in all_nodes:
                key = (curr_root, c, j)
                if key in enc.tau:
                    v = enc.tau[key].X
                    if v >= 1 - EPS:
                        if isinstance(j, str):  # leaf like "L0"
                            continue
                        next_nodes.append(j)

        for j in next_nodes:
            new_fixed = set(fixed_int_pos)
            new_fixed.add(j)
            k, used = _solve(j, new_fixed)
            if k > 1:
                return k, used

        return 1, fixed_int_pos

    k, _ = _solve(root, {root})
    return k


def main():
    inp = Input("examples/wine", max_nodes=3)
    root = 0
    k = Non_Trivial_tau(root, inp)
    print("Minimum non-trivial size:", k)


if __name__ == "__main__":
    main()
