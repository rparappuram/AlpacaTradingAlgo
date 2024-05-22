import pandas as pd

# read finetune_results.csv
# remove rows where final_value is nan
# save to finetune_results1.csv
#


def remove_nan_rows(csv_file_path):
    df = pd.read_csv(csv_file_path)
    df = df.dropna(subset=["final_value"])
    df.to_csv(csv_file_path, index=False)


remove_nan_rows("finetune_results.csv")
