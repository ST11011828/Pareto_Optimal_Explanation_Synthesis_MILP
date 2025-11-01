# # # algorithms.py
# from inputs import Input
# from pareto_points import Pareto_Points
# from gurobipy import GRB

# EPS = 1e-6

# # algorithms.py
# from inputs import Input
# from pareto_points import Pareto_Points

# EPS = 1e-6

# def Non_Trivial_tau(root, inp: Input):
#     # root is ignored; we always use 0 as requested
#     ROOT = 0

#     def _solve(fixed_int_pos):
#         pp = Pareto_Points(inp, fixed_int_pos, ROOT)
#         pp.find_pareto_points()
#         sol = pp.pareto_points

#         if len(sol) != 1:
#             return len(sol), fixed_int_pos

#         enc = pp.enc
#         all_nodes = list(enc.I) + list(enc.L.keys())
#         next_nodes = []

#         for c in enc.C:
#             for j in all_nodes:
#                 key = (ROOT, c, j)
#                 if key in enc.tau:
#                     v = enc.tau[key].X
#                     if v >= 1 - EPS:
#                         if isinstance(j, str):
#                             continue
#                         next_nodes.append(j)

#         for j in next_nodes:
#             new_fixed = set(fixed_int_pos)
#             new_fixed.add(j)
#             k, used = _solve(new_fixed)
#             if k > 1:
#                 return k, used

#         return 1, fixed_int_pos

#     k = _solve({ROOT})
#     return k


# def main():
#     inp = Input("examples/wine", max_nodes=3)
#     k = Non_Trivial_tau(0, inp)
#     print("Minimum non-trivial size:", k)


# if __name__ == "__main__":
#     main()


# # def change_int_pos():
# #     #takes in a solution, finds the 
# #     pass

# # def non_trivial_tau():
# #     pass

# # def Non_Trivial_tau(root, inp: Input):
# #     def _solve(curr_root, fixed_int_pos):
# #         pp = Pareto_Points(inp, fixed_int_pos, curr_root)
# #         pp.find_pareto_points()
# #         sol = pp.pareto_points

# #         if len(sol) != 1:
# #             return len(sol), fixed_int_pos

# #         enc = pp.enc
# #         all_nodes = list(enc.I) + list(enc.L.keys())
# #         next_nodes = []

# #         for c in enc.C:
# #             for j in all_nodes:
# #                 key = (curr_root, c, j)
# #                 if key in enc.tau:
# #                     v = enc.tau[key].X
# #                     if v >= 1 - EPS:
# #                         if isinstance(j, str):  # leaf like "L0"
# #                             continue
# #                         next_nodes.append(j)

# #         for j in next_nodes:
# #             new_fixed = set(fixed_int_pos)
# #             new_fixed.add(j)
# #             k, used = _solve(j, new_fixed)
# #             if k > 1:
# #                 return k, used

# #         return 1, fixed_int_pos

# #     k, _ = _solve(root, {root})
# #     return k


# # def main():
# #     inp = Input("examples/wine", max_nodes=3)
# #     root = 0
# #     k = Non_Trivial_tau(root, inp)
# #     print("Minimum non-trivial size:", k)


# # if __name__ == "__main__":
# #     main()


# algorithms.py
from inputs import Input
from pareto_points import Pareto_Points

EPS = 1e-6

def Non_Trivial_tau(inp: Input, fixed_int_pos=None):
    ROOT = 0

    # Initialize int_pos if this is the first call
    if fixed_int_pos is None:
        fixed_int_pos = {ROOT}

    # Solve once with current set of integer nodes
    pp = Pareto_Points(inp, fixed_int_pos, ROOT)
    pp.find_pareto_points()
    sol = pp.pareto_points

    # If we already have more than one Pareto point, return this non-degenerate case
    if len(sol) != 1:
        return len(sol), fixed_int_pos

    # Otherwise, identify children connected to root
    enc = pp.enc
    all_nodes = list(enc.I) + list(enc.L.keys())
    next_nodes = []

    for c in enc.C:
        for j in all_nodes:
            key = (ROOT, c, j)
            if key in enc.tau:
                try:
                    print("enc.model.SolCount =", enc.model.SolCount)
                    v = enc.tau[key].X
                except Exception:
                    # ✅ fallback: use cached value from last feasible solution
                    v = getattr(pp, "last_feasible_tau", {}).get(key, 0.0)
                if v >= 1 - EPS:
                    if isinstance(j, str):   # Skip leaves
                        continue
                    next_nodes.append(j)


    # Recurse by adding one new child to the integer set at a time
    for j in next_nodes:
        new_fixed = set(fixed_int_pos)
        new_fixed.add(j)
        k, used = Non_Trivial_tau(inp, new_fixed)
        if k > 1:
            return k, used

    # If no child expansion gives more than one point, still degenerate
    return 1, fixed_int_pos


def main():
    inp = Input("examples/wine", max_nodes=4)
    k, used = Non_Trivial_tau(inp)
    print("Minimum non-trivial size:", k)
    print("Integer nodes used:", used)


if __name__ == "__main__":
    main()
