import os
import csv
import matplotlib.pyplot as plt
import gurobipy as gp
from gurobipy import GRB

from inputs import Input, Predicate
from encoding import Encoding
from pareto_points import Pareto_Points

class non_trivial_tau_set:
    def __init__(self, dir , max_nodes ):
        self.inp = Input(dir, max_nodes)
        self.pareto_points = []
        self.max_nodes = max_nodes

    def non_trivial_tau_set(self):
        self.pareto_points.append()