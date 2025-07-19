import argparse
import pandas as pd
from scipy import stats

def analyze_experiment_results(data_path: str):
    """
    Loads experiment data and performs a T-test to determine the winner.
    
    Args:
        data_path (str): Path to the Parquet file containing experiment results.
                         Expected columns: `user_id`, `variant_name`, `converted` (0 or 1).
    """
    df = pd.read_parquet(data_path)
    
    control_group = df[df['variant_name'] == 'champion']
    treatment_group = df[df['variant_name'] == 'challenger']
    
    # --- Calculate metrics ---
    control_conversion_rate = control_group['converted'].mean()
    treatment_conversion_rate = treatment_group['converted'].mean()
    lift = (treatment_conversion_rate - control_conversion_rate) / control_conversion_rate
    
    # --- Perform Welch's T-test ---
    # More robust than standard T-test as it doesn't assume equal variance
    t_stat, p_value = stats.ttest_ind(
        treatment_group['converted'], 
        control_group['converted'], 
        equal_var=False
    )
    
    # --- Print Results ---
    print("--- A/B Test Analysis Report ---")
    print(f"Control (Champion) Conversion Rate: {control_conversion_rate:.4f}")
    print(f"Treatment (Challenger) Conversion Rate: {treatment_conversion_rate:.4f}")
    print(f"Relative Lift: {lift:+.2%}")
    print(f"\nP-value: {p_value:.5f}")
    
    if p_value < 0.05: # Using alpha = 0.05
        print("\nResult: Statistically Significant. The challenger model is the winner.")
    else:
        print("\nResult: Not Statistically Significant. We cannot conclude the challenger is better.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-path", required=True)
    args = parser.parse_args()
    analyze_experiment_results(args.data_path)