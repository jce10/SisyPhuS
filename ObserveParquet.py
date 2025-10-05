#!/usr/bin/env python3
import os
import pandas as pd

def observe_parquet(dir, run_start, run_end, output_csv=None, nrows_preview=5):
    """
    Load a range of .parquet files into a Pandas DataFrame and optionally write to CSV.

    Parameters
    ----------
    dir : str
        Directory containing parquet files
    run_start : int
        First run number (inclusive)
    run_end : int
        Last run number (inclusive)
    output_csv : str or None
        If specified, writes combined DataFrame to CSV
    nrows_preview : int
        Number of rows to display as a quick preview
    """
    all_dfs = []

    for run in range(run_start, run_end + 1):
        file_name = f"run_{run}.parquet"
        path = os.path.join(dir, file_name)

        if not os.path.exists(path):
            print(f"⚠️ File not found: {file_name}, skipping.")
            continue

        df = pd.read_parquet(path)
        df['Run'] = run  # optional: add a column to track run number
        all_dfs.append(df)

    if not all_dfs:
        print("No files loaded. Exiting.")
        return

    combined_df = pd.concat(all_dfs, ignore_index=True)
    print(f"✅ Loaded {len(all_dfs)} files into a DataFrame with {len(combined_df)} rows.")
    # print("\nColumns:")
    # print(combined_df.columns.tolist())
    # print(f"\nFirst {nrows_preview} rows:")
    # print(combined_df.head(nrows_preview))

    if output_csv:
        combined_df.to_csv(output_csv, index=False)
        print(f"✅ Combined DataFrame saved to {output_csv}")


# Example usage
if __name__ == "__main__":
    dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built"
    observe_parquet(
        dir=dir,
        run_start=464,
        run_end=464,
        output_csv="ObservedRuns.csv"
    )
