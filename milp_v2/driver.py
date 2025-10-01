import sys
import time
from plot_pareto_curve import find_new_pareto_points

C = 6
I = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,19,20]

for i in I:
    log_file = f'examples/AutoTaxi/combined_runs_logs_ilp/I{i}_C{C}.log'
    with open(log_file, 'w') as f:
        sys.stdout = f
        start_time = time.time()
        result = find_new_pareto_points(i,C)
        end_time = time.time()
        if result != None:
            f.write(result)
        f.write(f'\n Total time taken: {end_time - start_time} seconds')
        sys.stdout = sys.__stdout__