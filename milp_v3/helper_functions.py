import pandas as pd

predicates = {}
pred_id =0
line_num = 0
df = pd.read_csv("samples.csv", skipinitialspace=True)

def num_buckets(pred_id):
    return int(predicates[pred_id]["num_buckets"])

def func(sample_id, pred_id , bucket_id = -1):    
    global df
    sample = df.iloc[sample_id]
    if bucket_id >=0:
        #TODO: Why bucket_id < len(predicates[pred_id]["conditions"])
        if bucket_id<num_buckets(pred_id) and  bucket_id < len(predicates[pred_id]["conditions"]):
            condition = predicates[pred_id]["conditions"][bucket_id]
            result = eval(condition,{},sample.to_dict())
            if result == True:
                return 1
            else:
                return 0
        else:
            return 0
    else:
        #TODO: Create a special case for leaves when bucket id is -1, if the label on the sample is equal to the label corresponding to that leaf return 1 else return 0
        if sample["label"] == pred_id:
            return 1
        else:
            return 0

def read_samples():
    global df
    features = list(df.columns[:-1])
    X = df[features]
    Y = df[df.columns[-1]]

def read_features():
    global pred_id
    global line_num
    global df
    with open("features.txt", "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines:
        
        if line.startswith("predicate"):
            _ , pred_name , num_buckets , weight = line.split(":")
            predicates[pred_id]={
                "name": pred_name,
                "num_buckets": int(num_buckets),
                "weight": float(weight),
                "conditions": []
            }
            pred_id = pred_id + 1
        elif " = " in line:
            new_feature,expression = line.split("=")
            new_feature = new_feature.strip()
            expression = expression.strip()
            df[new_feature] = df.eval(expression, engine="python")
        else:
            if pred_id == 0:
                pass
            else:
                predicates[pred_id-1]["conditions"].append(line)
        line_num = line_num + 1
    if "label" in df.columns:
        label_col = df["label"]
        df.drop(columns=["label"], inplace=True)
        df["label"] = label_col
        df.to_csv("updated_samples.csv")

def main():
    read_features()

if __name__ == "__main__":
    main()