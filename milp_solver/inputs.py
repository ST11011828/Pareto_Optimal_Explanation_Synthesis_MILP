import os
import pandas as pd
import numpy as np

class Samples:
    '''
    Instance attributes:
        dir_path(str) - stores the path of the folder which holds the sampels.csv file
        samples(DataFrame) - stores all the samples
        updated_samples(DataFrame) - stores the updated samples after processing the features 
        features(DataFrame) - stores all the features
        output(DataFrame) - stores all the outputs(last column of samples.csv)

    Instance methods:
        Add the appropriate description
    '''
    def __init__(self, samples_csv_path:str):
        # self.dir_path = samples_csv_path.replace("samples.csv","")
        self.dir_path = os.path.dirname(samples_csv_path)
        df = pd.read_csv(samples_csv_path, skipinitialspace=True)
        self.samples = df
        self.updated_samples = self.samples.copy()
        self.put_label_at_end()
        self.features = self.updated_samples.iloc[:,:-1].copy()
        self.output = self.updated_samples.iloc[:,-1].copy()

    def update_samples(self, new_feature, expression , engine):
        self.updated_samples[new_feature] = self.updated_samples.eval(expression, engine= engine)
        self.put_label_at_end()
        self.features = self.updated_samples.iloc[:,:-1].copy()

    def put_label_at_end(self):
        df = self.updated_samples
        if "label" in df.columns:
            label_series = df.pop("label")     
            df["label"] = label_series         
        self.updated_samples = df 

    def save_updated_samples(self):
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
        self.pred_name = name
        self.pred_id = pred_id
        self.num_buckets = num_buckets
        self.weight = weight
        self.conditions = []


class Input:
    '''
    instance attributes:
      filename (str)
      max_nodes (int)
      samples (Samples)
      predicates (list[Predicate])
      c_max (int)
      leaves (list[str])
    '''
    def __init__(self, filename, max_nodes):
        self.filename = filename
        self.max_nodes = max_nodes
        self.samples = Samples(os.path.join(self.filename, "samples.csv"))
        self.predicates = []
        self.c_max = 0
        self.leaves = []
        self.max_weight = 0
        self.min_weight = 20000000000
        self.read_features()
        self.samples.put_label_at_end()
        self.calculate_c_max()
        self.calculate_leaves()
        self.samples.save_updated_samples()
        # self.samples.updated_samples.to_csv(
        #     os.path.join(self.filename, "updated_samples.csv"),
        #     index=False
        # )

    def calculate_c_max(self):
        if len(self.predicates) == 0:
            self.c_max = 0
        else:
            self.c_max = max(p.num_buckets for p in self.predicates)

    def calculate_leaves(self):
        df = self.samples.output
        # last_col = df.columns[-1]
        self.leaves = pd.unique(df).tolist()

    # def put_label_at_the_end(self):
    #     df = self.samples.updated_samples
    #     if "label" in df.columns:
    #         label_series = df.pop("label")     
    #         df["label"] = label_series         
    #     self.samples.updated_samples = df

    def read_features(self):
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
                if int(weight) > self.max_weight:
                    self.max_weight = int(weight)
                if int(weight) < self.min_weight:
                    self.min_weight = int(weight)
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
                # bucket condition line (we ignore storing it here as per the minimal design)
                if current_pred is None:
                    continue
                current_pred.conditions.append(line)

        # self.samples.updated_samples = df

    def func(self, sample_id , pred_id, bucket_id = -1):
        df = self.samples.updated_samples
        curr_s = df.iloc[sample_id]
        if bucket_id >= 0:
            if bucket_id < self.predicates[pred_id].num_buckets and bucket_id < len(self.predicates[pred_id].conditions):
                condition = (self.predicates[pred_id].conditions)[bucket_id]
                result = eval(condition,{}, curr_s.to_dict())
                if result == True:
                    return 1
                else:
                    return 0
            else:
                return 0
        else:
            if curr_s["label"] == pred_id:
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
# def input_class_tester_main():
    k = Input("examples/random_dataset",8)
    # print(k.filename)
    # print(k.samples.features)
    # print(k.predicates)
    # print(k.c_max)
    # print(k.leaves)
    # print(k.predicates[0].conditions)
    # print(k.func(2,2,1))
    print(k.func(1,"shreya"))

if __name__ == "__main__":
    main()
