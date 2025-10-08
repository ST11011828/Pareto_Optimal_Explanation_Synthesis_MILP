import pandas as pd
predicates = {}
pred_id =0
line_num = 0
# parent_dir = input('Input parent directory: ')
parent_dir = 'examples/wine'
df = pd.read_csv(f"{parent_dir}/samples.csv", skipinitialspace=True)

def _reset_state():
    """Clear all module-level state so repeated runs don't accumulate."""
    global predicates, pred_id, line_num
    predicates.clear()
    pred_id = 0
    line_num = 0

def num_buckets(pred_id):
    return int(predicates[pred_id]["num_buckets"])

def return_weight(pred_id):
    return int(predicates[pred_id]["weight"])

def return_max_weight():
    max_weight =0
    for p in predicates:
        if return_weight(p) > max_weight:
            max_weight = return_weight(p)
    return 2*max_weight

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
    _reset_state()
    global pred_id
    global line_num
    global df
    with open(f"{parent_dir}/features.txt", "r") as f:
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


def calculate_explainability(solution):
    # returns the explainability score of a model
    I = solution["I"]
    P = solution["P"]
    u = solution["u"]
    o_u = solution["o_u"]

    # return return_max_weight()*sum(1 - u[i].X for i in I)+ sum(return_weight(p)*o_u[i,p].X for i in I for p in P)
    return sum(1 - u[i].X for i in I)+ sum(return_weight(p)*o_u[i,p].X for i in I for p in P)

def calculate_correctness(solution):
    m = solution["m"]
    S = range(len(df))
    return sum(m[0,s].X for s in S)*1.0/len(df)



def main():
    read_features()

if __name__ == "__main__":
    main()