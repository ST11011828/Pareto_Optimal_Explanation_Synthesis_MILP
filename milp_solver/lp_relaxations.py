import random
from pareto_points import Pareto_Points
import time

class LP_Relaxation:
    '''
    This class groups six LP/ILP relaxation runs.
    Each relaxation stores its resulting Pareto points list on a separate attribute:
      - pp_root_int
      - pp_root_and_outgoing_int # to be implemented
      - pp_leaf_transitions_int   # to be implemented
      - pp_fix_root_and_then_relax # to be implemented
      - pp_root_plus_one_int
      - pp_all_int
    '''

    def __init__(self, dir_name, max_nodes, root):
        # remembering the dataset folder (has samples.csv, features.txt)
        self.dir_name = dir_name
        # remembering the maximum number of internal nodes to allow
        self.max_nodes = max_nodes
        # remembering which node index is the root (usually 0)
        self.root = root

        # result buckets for each relaxation; they will store [c, e, path] triples
        self.pp_all_lam_all_tau_int = []
        self.pp_root_plus_one_lam_and_tau_int = []
        self.pp_root_lam_root_tau_int = []
        self.pp_all_lam_all_u_int = []
        self.pp_all_lam_all_u_root_tau_int = []
        self.pp_all_lam_before_leaves_m_int = []
        self.pp_root_lam_root_tau_before_leaves_m_int = []
        self.pp_root_plus_one_lam_and_tau_and_before_leaves_m_int = []
        self.pp_all_lam_all_u_before_leaves_m_int = []
        self.pp_fix_root_and_then_relax = []
        self.pp_all_continuous = []

    def _run(self, lam_nodes, tau_nodes=None, u_nodes=None, m_nodes=None, bucket_attr_name=None):
        '''
        Build Pareto_Points with the requested integrality sets, run, and store results.
        Defaults:
        - tau_nodes defaults to lam_nodes (keep old behavior)
        - u_nodes and m_nodes default to continuous (empty sets)
        '''
        if tau_nodes is None: tau_nodes = set(lam_nodes)
        if u_nodes   is None: u_nodes   = set()
        if m_nodes   is None: m_nodes   = set()

        pp = Pareto_Points(self.dir_name, self.max_nodes,
                        lam_nodes, tau_nodes, u_nodes, m_nodes, self.root)
        pp.cumulate_pareto_points()
        if bucket_attr_name is not None:
            setattr(self, bucket_attr_name, list(pp.pareto_points))
            return getattr(self, bucket_attr_name)
        return list(pp.pareto_points)

    def root_only(self):
        lam = {self.root}
        tau = {self.root}
        u   = set()
        m   = set()
        return self._run(lam, tau, u, m, "pp_root_int")

    def root_and_outgoing_nodes(self):
        # current simplified definition = same ints as root_only (structure will decide children)
        lam = {self.root}
        tau = {self.root}
        u   = set()
        m   = set()
        return self._run(lam, tau, u, m, "pp_root_and_outgoing_int")

    def root_plus_random(self, seed=None):
        rng = random.Random(seed)
        candidates = [i for i in range(self.max_nodes) if i != self.root]
        chosen = self.root if not candidates else rng.choice(candidates)
        print(f"The chosen random node is {chosen}")
        lam = {self.root, chosen}
        tau = {self.root, chosen}
        u   = set()
        m   = set()
        return self._run(lam, tau, u, m, "pp_root_plus_one_int")

    def all_integers(self):
        full = set(range(self.max_nodes))
        lam = full
        tau = full
        u   = full
        m   = full
        return self._run(lam, tau, u, m, "pp_all_int")

    def all_continuous(self):
        lam = set()
        tau = set()
        u   = set()
        m   = set()
        return self._run(lam, tau, u, m, "pp_all_continuous")




def main():
    start = time.perf_counter()
    lr = LP_Relaxation("examples/wine", max_nodes=3, root=0)

    # print("Running: root_only")
    # lr.root_only()
    # print(f"Pareto points found: {len(lr.pp_root_int)}")

    # print("Running: root_and_outgoing")
    # lr.root_and_outgoing()
    # print(f"Pareto points found: {len(lr.pp_root_and_outgoing_int)}")

    # print("Running: leaf_transitions_only) 
    # lr.leaf_transitions_only() 
    # print(f"Pareto points found: {len(lr.pp_leaf_transitions_int)}")

    # print("Running: root_plus_random")
    # lr.root_plus_random(seed=42)
    # print(f"Pareto points found: {len(lr.pp_root_plus_one_int)}")

    # print("Running: all_integers")
    # lr.all_integers()
    # print(f"Pareto points found: {len(lr.pp_all_int)}")

    print("Running all continuous")
    lr.all_continuous()
    print(f"Pareto points found: {len(lr.pp_all_continuous)}")


    end = time.perf_counter()
    print(f"Elapsed: {end - start:.2f} s")


if __name__ == "__main__":
    main()
