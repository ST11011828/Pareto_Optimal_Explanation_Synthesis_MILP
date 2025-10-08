import sys
import time
from plot_pareto_curve_v2 import find_new_pareto_points
import os

C = 6
I = [1,2,3,4]
log_dir = "examples/balance_scale/combined_runs_logs_correct_ilp_v_new_driver"
os.makedirs(log_dir, exist_ok=True)
for i in I:
     
    log_file = f'examples/balance_scale/combined_runs_logs_correct_ilp_v_new_driver/I{i}_C{C}.log'
    with open(log_file, 'w') as f:
        sys.stdout = f
        start_time = time.time()
        result = find_new_pareto_points(i,C)
        end_time = time.time()
        if result != None:
            f.write(result)
        f.write(f'\n Total time taken: {end_time - start_time} seconds')
        sys.stdout = sys.__stdout__