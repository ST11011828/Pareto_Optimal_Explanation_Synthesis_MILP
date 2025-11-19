import os
import pandas as pd
import sys
# import numpy as np

class Samples:
    '''
    Instance attributes:
        dir_path(str) - stores the path of the folder which holds the sampels.csv file
        samples(csv) - stores all the samples
        updated_samples(csv) - stores the updated samples after processing the features 
        features(DataFrame) - stores all the feature values for samples
        output(csv) - stores all the outputs(last column of samples.csv)

    NOTE:
    This code assumes that there is a column named label which has the output values, it does not necessarily need to be at the very end.
    All changes are made in updated_samples
    '''
    def __init__(self, samples_csv_path:str):
        # self.dir_path = samples_csv_path.replace("samples.csv","")
        self.dir_path = os.path.dirname(samples_csv_path) # initializing the directory path
        df = pd.read_csv(samples_csv_path, skipinitialspace=True) #reading samples.csv
        self.samples = df
        self.updated_samples = self.samples.copy() #making a copy of samples.csv in updated_samples
        self.put_label_at_end() #finds out the column with the name "label" and puts it at the end
        self.features = self.updated_samples.iloc[:,:-1].copy() #initializing feature values
        self.output = self.updated_samples.iloc[:,-1].copy() #initializzing output values

    def update_samples(self, new_feature, expression , engine):
        '''
        This function adds a column based on the expression we give and puts the "label" column at the end of the samples.csv
        '''
        self.updated_samples[new_feature] = self.updated_samples.eval(expression, engine= engine) #creating a new column with new feature
        self.put_label_at_end()
        self.features = self.updated_samples.iloc[:,:-1].copy() #updating self.features

    def put_label_at_end(self):
        '''
        This function takes the updated_ samples and puts the label column at the end
        '''
        df = self.updated_samples 
        if "label" in df.columns:
            label_series = df.pop("label")     
            df["label"] = label_series         
        self.updated_samples = df 

    def save_updated_samples(self):
        '''
        This function creates a new file updated_samples.csv
        '''
        self.updated_samples.to_csv(
            os.path.join(self.dir_path, "updated_samples.csv"),
            index=False
        )


class Predicate:
    '''
    Instance attributes:
        pred_name: stores the name of the predicate
        pred_id: Stores the number assigned to that predicate
        num_buckets: stores the number of buckets allowed by that feature
        weight: Stores the weight assosciated with that predicate
        conditions(list): stores the conditions assosciated with each predicate

    '''
    def __init__(self , name ,pred_id , num_buckets , weight):
        self.pred_name = name #initializing predicate name
        self.pred_id = pred_id #initializing predicate id
        self.num_buckets = num_buckets #initializing number of buckets
        self.weight = weight #initializing weight
        self.conditions = [] #initializing conditions list as empty initially


class Input:
    '''
    instance attributes:
      filename (str) - stores the filename which has samples.csv and features.txt (for examples, "examples/wine")
      max_nodes (int) - stores the maximum number of internal nodes possible as inputted by the user
      samples (Samples) - stores all info related to samples.csv
      predicates (list[Predicate]) - contains a list of predicates (along with their details)
      c_max (int) - stores the maximum number of branches possible ( calculated from features.txt)
      leaves (list[str]) - stores the leaves of the decision diagram

      NOTE:
      Currently there is a restriction that maximum weight is less that 20000000000(aribitrarily chosen large number for now)
    '''
    def __init__(self, filename, max_nodes, MAX_WEIGHT = 20000000000):
        self.filename = filename #initializing filename
        self.max_nodes = max_nodes #initializing max_nodes
        self.samples = Samples(os.path.join(self.filename, "samples.csv")) #making an object of the class Samples
        self.predicates = [] #initializing the list of predicates(starting with empty)
        self.c_max = 0
        self.leaves = []
        self.max_weight = 0
        self.min_weight = MAX_WEIGHT
        self.read_features() # predicates[] updated
        self.samples.put_label_at_end() 
        self.calculate_c_max() 
        self.calculate_leaves()
        self.samples.save_updated_samples()
        # self.samples.updated_samples.to_csv(
        #     os.path.join(self.filename, "updated_samples.csv"),
        #     index=False
        # )

    def calculate_c_max(self):
        '''
        This function calculates c_max from the list predicates.
        '''
        if len(self.predicates) == 0:
            self.c_max = 0
        else:
            self.c_max = max(p.num_buckets for p in self.predicates)

    def calculate_leaves(self):
        '''
        This function calculates the leaves by looking at unique outputs(from the column label) and stores the leaves as a set.'''
        df = self.samples.output
        # last_col = df.columns[-1]
        self.leaves = pd.unique(df).tolist()

    def read_features(self):
        '''
        This function reads features.txt and updates the list predicates and also adds. new columns in updated_samples (if required)
        '''
        # df = self.samples.updated_samples
        pred_id = 0
        current_pred = None
        # max_weight = 0
        # min_weight = 200000000000

        with open(os.path.join(self.filename, "features.txt"), "r") as f:
            lines = [line.strip() for line in f if line.strip()]

        for line in lines:
            if line.startswith("predicate"):
                # format: predicate: <name> : <num_buckets> : <weight>
                _, pred_name, num_buckets, weight = [x.strip() for x in line.split(":")]
                #updating max_weight( if needed )
                if int(weight) > self.max_weight:
                    self.max_weight = int(weight)
                #updating min_weight ( if needed )
                if int(weight) < self.min_weight:
                    self.min_weight = int(weight)
                #updating current_pred and appending it to predicates
                current_pred = Predicate(
                        name=pred_name,
                        pred_id=pred_id,
                        num_buckets=int(num_buckets),
                        weight=float(weight)
                    )
                self.predicates.append(current_pred)
                pred_id += 1

            elif " = " in line:
                # derived feature: <new_feature> = <expression>
                new_feature, expression = line.split("=")
                new_feature = new_feature.strip()
                expression = expression.strip()
                # evaluate using existing columns (including previously derived ones)
                # df[new_feature] = df.eval(expression, engine="python")
                self.samples.update_samples(new_feature, expression, engine="python")

            else:
                # bucket condition line 
                if current_pred is None:
                    continue
                # appending the conditions to the current predicate
                current_pred.conditions.append(line)

            # if len(current_pred.conditions) != current_pred.num_buckets:
            #     sys.stderr(f"Conditions for predicate {current_pred.pred_name} are not consistent with number of buckets entered")
            #     sys.exit(1)

        # self.samples.updated_samples = df

    def valid_branch(self,bucket_id, pred_id):
        '''
        This function takes a branch number and a predicate id and returns whether that branch is valid for that predicate or not.
        A valid branch would be a branch that corresponds to some condition for that predicate.
        '''
        if bucket_id < self.predicates[pred_id].num_buckets:
            return 1
        else:
            return 0

    def func(self, sample_id , pred_id, bucket_id = -1):
        '''
        returns 1 if a particular sample sample_id would take a bucket bucket_id when evaluated through the predicate pred_id
        if bucket_id = -1, that means we are evaluating a sample at one of the leaves, in that case the function returns true when the label of the sample is same as the label of the leaf'''
        df = self.samples.updated_samples
        curr_s = df.iloc[sample_id]
        if bucket_id >= 0:
            # if bucket_id < self.predicates[pred_id].num_buckets and bucket_id < len(self.predicates[pred_id].conditions): 
            if bucket_id < self.predicates[pred_id].num_buckets: 
                condition = (self.predicates[pred_id].conditions)[bucket_id]
                result = eval(condition,{}, curr_s.to_dict())
                if result == True:
                    return 1
                else:
                    return 0
            else:
                return 0
        else:
            if curr_s["label"] == pred_id: # here pred_id refers to leaf id as this is the leaf case
                return 1
            else:
                return 0
            

# def sample_class_tester_main():
# # def main():
#     #A tester code for the class Samples
#     k = Samples("examples/random_dataset/samples.csv")
#     print(k.features)
#     print("------------------------------------------")
#     print(k.output)
#     print("------------------------------------------")
#     k.update_samples("yo" , "yo1+yo2" , "python")
#     print(k.updated_samples)
#     print(k.features)
#     print("------------------------------------------")
#     k.put_label_at_end()
#     print(k.updated_samples)
#     print("---------------------------------------")
    
def main():
    print("Testing class Samples")
    print("-------------------------------------------------")
    k = Samples("examples/random_dataset/samples.csv")
    print("PRINTING FEATURES --------------")
    print(k.features)
    print("PRINTING OUTPUT--------------------------")
    print(k.output)
    print("PRINTING UPDATED SAMPLES-------------")
    print(k.updated_samples)
    print("TESTING OF THE CLASS SAMPLES DONE!!!!!!!")
    print("-------------------------------------")
    print("-------------------------------------")
    print("Testing class Input")
# def input_class_tester_main():
    k1 = Input("examples/random_dataset",8)
    print("PRINTING FILENAME")
    print(k1.filename)
    print("--------------------------------------")
    print("Printing features of the samples in the input")
    print(k1.samples.features)
    print("--------------------------------------")
    print("Printing the predicates of input")
    print(k1.predicates)
    print("--------------------------------------")
    print("Printing c_max")
    print(k1.c_max)
    print("----------------------------------")
    print("Printing leaves")
    print(k1.leaves)
    print("--------------------------------")
    print("Printing conditions for a particular predicate")
    print(k1.predicates[0].conditions)
    print("-------------------------------------")
    print("Printing the number of buckets for a particular predicate")
    print(k1.predicates[1].num_buckets)
    print("------------------------------")
    print("Testing the valid_branch() function")
    print(k1.valid_branch(2,1))
    print("---------------------------")
    print("Testing the function func()")
    print(k1.func(1,"shy"))
    print(k1.func(2,2,1))

if __name__ == "__main__":
    main()
