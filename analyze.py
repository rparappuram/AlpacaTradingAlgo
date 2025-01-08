import pandas as pd

# Load the CSV file
file_path = "finetune_results_2024-01-01.csv"
df = pd.read_csv(file_path)

# Define the number of top unique final values to analyze
top_n = 3

# Sort the dataframe by final_value in descending order
sorted_df = df.sort_values(by="final_value", ascending=False)

# Get the top N unique final values
top_n_final_values = sorted_df["final_value"].unique()[:top_n]

# Filter the dataframe to include only rows with the top N final values
top_n_df = sorted_df[sorted_df["final_value"].isin(top_n_final_values)]

# Count the occurrences of each parameter value for the top N final values
parameter_columns = [
    "bollinger_period",
    "bollinger_std",
    "bollinger_width_threshold",
    "rsi_upper",
    "rsi_lower",
    "atr_multiplier",
    "final_value",
]

parameter_counts = {}
for param in parameter_columns:
    parameter_counts[param] = top_n_df[param].value_counts()

# Display the counts for each parameter
for param, counts in parameter_counts.items():
    print(f"\nCounts for {param} in the top {top_n} unique final values:")
    print(counts)
