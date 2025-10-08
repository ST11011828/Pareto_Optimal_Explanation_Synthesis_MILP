import sys
import time
from plot_pareto_curve import find_new_pareto_points
import os

C = 6
I = [1,2,3,4,5,6]
log_dir = "examples/wine/lam_and_tau_integer_for_not_divisible_by_5_integer/combined_runs_logs"
os.makedirs(log_dir, exist_ok=True)
for i in I:
     
    log_file = f'examples/wine/lam_and_tau_integer_for_not_divisible_by_5_integer/combined_runs_logs/I{i}_C{C}.log'
    with open(log_file, 'w') as f:
        sys.stdout = f
        start_time = time.time()
        result = find_new_pareto_points(i,C)
        end_time = time.time()
        if result != None:
            f.write(result)
        f.write(f'\n Total time taken: {end_time - start_time} seconds')
        sys.stdout = sys.__stdout__