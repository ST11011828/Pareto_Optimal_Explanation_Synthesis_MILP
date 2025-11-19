# lp_relaxations.py
import random
from pareto_points import Pareto_Points


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
        self.pp_root_int = []
        self.pp_root_and_outgoing_int = []
        self.pp_leaf_transitions_int = []
        self.pp_fix_root_and_then_relax = []
        self.pp_root_plus_one_int = []
        self.pp_all_int = []

    def _run(self, int_nodes, bucket_attr_name):
        '''
        Internal helper:
        - builds Pareto_Points with the given set of nodes that are integral
        - calls cumulate_pareto_points()
        - copies the resulting list into the right attribute
        - returns that list
        '''
        pp = Pareto_Points(self.dir_name, self.max_nodes, int_nodes, self.root)
        pp.cumulate_pareto_points()
        setattr(self, bucket_attr_name, list(pp.pareto_points))
        return getattr(self, bucket_attr_name)

    def root_only(self):
        '''
        Relaxation 1: only the root's lam and tau are integral.
        In current Encoding, "int_nodes" contains nodes whose lam[i,*] and tau[i,*,*] are integral.
        '''
        int_nodes = {self.root}
        return self._run(int_nodes, "pp_root_int")

    def root_and_outgoing_nodes(self):
        '''
        Relaxation 2: only the root and transitions from the root and the lam and tau of roots children are integral.

        '''
        int_nodes = {self.root}
        return self._run(int_nodes, "pp_root_and_outgoing_int")

    # def leaf_transitions_only(self):
    #     '''
    #     Relaxation 3: only transitions that go to a leaf are integral.

    #     '''
    #     int_nodes = set(range(self.max_nodes))  # best achievable under current Encoding
    #     return self._run(int_nodes, "pp_leaf_transitions_int")

    def root_plus_random(self, seed=None):
        '''
        Relaxation 4: the root and one randomly selected internal node are integral.
        "seed" can be given to make the random choice reproducible.
        '''
        rng = random.Random(seed)
        candidates = [i for i in range(self.max_nodes) if i != self.root]
        if len(candidates) == 0:
            # fallback: if there is only the root, just use the root
            chosen = self.root
        else:
            chosen = rng.choice(candidates)
        int_nodes = {self.root, chosen}
        return self._run(int_nodes, "pp_root_plus_one_int")

    def all_integers(self):
        '''
        Relaxation 5: all nodes have lam and tau integral.
        '''
        int_nodes = set(range(self.max_nodes))
        return self._run(int_nodes, "pp_all_int")


def main():
    lr = LP_Relaxation("examples/random_dataset", max_nodes=3, root=0)

    print("Running: root_only")
    lr.root_only()
    print(f"Pareto points found: {len(lr.pp_root_int)}")

    # print("Running: root_and_outgoing")
    # lr.root_and_outgoing()
    # print(f"Pareto points found: {len(lr.pp_root_and_outgoing_int)}")

    # print("Running: leaf_transitions_only 
    # lr.leaf_transitions_only()
    # print(f"Pareto points found: {len(lr.pp_leaf_transitions_int)}")

    print("Running: root_plus_random")
    lr.root_plus_random(seed=42)
    print(f"Pareto points found: {len(lr.pp_root_plus_one_int)}")

    print("Running: all_integers")
    lr.all_integers()
    print(f"Pareto points found: {len(lr.pp_all_int)}")


if __name__ == "__main__":
    main()
