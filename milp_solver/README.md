
# MILP Pareto Optimal explanation solver

## Purpose:

Finds out the entire set of pareto-optimal solutions for a set of given samples and features.

## Files:

- **inputs.py** : process everything about inputs ( samples , features , maximum number of nodes)
- **encoding.py** : processes the encoding + declaration of encoding variables
- **pareto_points.py** : calculates the pareto-points using divide and conquer technique
- **algorithms.py** : implements all the algorithms we have worked on so far and compares it with the original solution
- **driver.py** : supplies all the required inputs 

## Input format:

- Make a file with the instance name in the folder *examples* , for examples, if you want to name your instance wine, create the folder examples/wine in the same directory as other code.
- Inside the folder, put the files *samples.csv* and *features.txt*. 
    - samples.csv should have the output/class/label as the last column
    - features.txt should follow the following example format:
            alcohol
            malic_acid
            flavanoids
            color_intensity
            hue
            proline
            alc_flav_sum = alcohol + flavanoids
            color_minus_hue = color_intensity - hue
            proline_minus_malic = proline - malic_acid

            predicate: alcohol : 4 : 2
            alcohol < 12.9
            12.9 <= alcohol < 13.36
            13.36 <= alcohol < 13.83
            alcohol >= 13.83

            predicate: malic_acid : 3 : 1
            malic_acid < 1.7
            1.7 <= malic_acid < 1.94
            malic_acid >= 1.94

            predicate: flavanoids : 6 : 3
            flavanoids < 1.5
            1.5 <= flavanoids < 1.68
            1.68 <= flavanoids < 2.14
            2.14 <= flavanoids < 2.5
            2.5 <= flavanoids < 2.88
            flavanoids >= 2.88

            predicate: color_intensity : 5 : 2
            color_intensity < 3.2
            3.2 <= color_intensity < 4.0
            4.0 <= color_intensity < 4.69
            4.69 <= color_intensity < 6.2
            color_intensity >= 6.2

            predicate: hue : 2 : 1
            hue < 1.04
            hue >= 1.04

            predicate: proline : 4 : 3
            proline < 500
            500 <= proline < 675
            675 <= proline < 985
            proline >= 985

            predicate: alc_flav_sum : 3 : 1
            alc_flav_sum < 15.0
            15.0 <= alc_flav_sum < 16.5
            alc_flav_sum >= 16.5

            predicate: color_minus_hue : 2 : 1
            color_minus_hue < 3.0
            color_minus_hue >= 3.0

            predicate: proline_minus_malic : 3 : 2
            proline_minus_malic < 500
            500 <= proline_minus_malic < 900
            proline_minus_malic >= 900
- Add the name of the instance file and the maximum number of internal nodes at the indicated places (check the description of the file) in *driver.py*

## Output format:

The output will be saved in the results folder (e.g., if the name of the instance is wine, the output will be found in the file examples/wine/results). The file will be named according to the algorithm whoch has been run. It can also be found in the description of the appropriate function in the file *algorithms.py*.

## How to run the repository

python driver.py