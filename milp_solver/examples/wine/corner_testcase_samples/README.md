# Testcases that are used for corner testing

Here is the description of corner cases files that **necessarily have to pass** for us to prove that we have created the right encoding.

## samples_c_1

This should yield only 1 pareto point with accuracy 1, as all the datapoints have the same output.  

Whatever be the the root, the transition corresponding to all the buckets should take us to the leaf containing label 1.

## samples_c_0.5

This should yield only 0.5 pareto point with accuracy 1, as all the datapoints have the same output.  
There will be only one active node and the edge corresponding to any bucket will either go to leaf containing label 1 or leaf containing label 2.  

## samples_c_more_than_0.5

This should yield an accuracy of more than 0.5 and the tree correponding to c= 0 should go to label 2 for sure.

## samples_c_less_than_0.5

This should give a correctness of 0.33333...