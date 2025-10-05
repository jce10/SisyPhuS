import os
import re
import csv
import matplotlib.pyplot as plt

def get_run_lengths(data_dir):
    """
    Loops through run directories and extracts run lengths in minutes
    from 'time.real' in run.info
    Returns dict: {run_number: run_length_minutes}
    """
    run_lengths = {}

    for folder in os.listdir(data_dir):
        if folder.startswith("run_"):
            run_info_path = os.path.join(data_dir, folder, "run.info")
            if os.path.isfile(run_info_path):
                with open(run_info_path, "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 4:
                        time_real_line = lines[3].strip()  # 4th line
                        if "=" in time_real_line:
                            time_str = time_real_line.split("=")[1]  # e.g., "00:04:57"
                            h, m, s = map(int, time_str.split(":"))
                            run_length_minutes = h*60 + m + s/60
                            run_number = int(folder.split("_")[1])
                            run_lengths[run_number] = run_length_minutes
    return run_lengths


def PluckBCI_with_time(scaler_dir, data_dir, run_groups, output_csv="BCI_rates_solo.csv"):
    """
    Extract beam integrator counts and run lengths, then calculate counts per minute.
    Adds angle info and plots shaded regions per angle with fixed colors.
    """
    run_lengths = get_run_lengths(data_dir)
    all_runs = []

    print("\n📋 Processing scaler files and run lengths...\n")

    for angle_label, ranges in run_groups.items():  # Keep angle info
        for run_min, run_max in ranges:
            for filename in os.listdir(scaler_dir):
                match = re.match(r'run_(\d+)_scalers\.txt', filename)
                if match:
                    run_number = int(match.group(1))
                    if run_min <= run_number <= run_max:
                        file_path = os.path.join(scaler_dir, filename)
                        with open(file_path, 'r') as f:
                            for line in f:
                                if "beamint" in line:
                                    parts = line.strip().split()
                                    if len(parts) == 2 and parts[0] == "beamint":
                                        beamint_value = int(parts[1])
                                        run_len = run_lengths.get(run_number, None)
                                        if run_len is None:
                                            print(f"⚠️  Warning: Run {run_number} has no time.real info!")
                                            continue
                                        counts_per_min = beamint_value / run_len
                                        all_runs.append((run_number, beamint_value, run_len, counts_per_min, angle_label))
                                    break

    # Sort by run number
    all_runs_sorted = sorted(all_runs, key=lambda x: x[0])
    runs = [r[0] for r in all_runs_sorted]
    counts_per_min = [r[3] for r in all_runs_sorted]
    angles = [r[4] for r in all_runs_sorted]

    # Write CSV
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Run", "Counts", "RunLength_minutes", "CountsPerMinute", "Angle"])
        for run_number, counts, run_len, counts_per_min, angle in all_runs_sorted:
            writer.writerow([run_number, counts, run_len, counts_per_min, angle])

    print(f"\n✅ Done! {len(all_runs_sorted)} runs written to {output_csv}")


# === Example usage ===
scaler_dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/scalers"
data_dir   = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/2025_06_13C_DATA/DAQ"

run_groups = {
    "7": [(317, 319),(394, 398), (427, 440), (465, 465)],
    "10": [(314, 315),(378, 382),(385,389), (426,426),(441, 442),(444, 447)],
    "12": [(341, 346),(351, 352), (458, 464)],
    "15": [(320, 329), (340, 340), (450, 454), (457, 457)],
    "17": [(369, 375)],
    "20": [(355,365)],
    "25": [(420, 425)],
    "35": [(415, 418)],
    "40": [(404, 405),(408, 413)],
}

PluckBCI_with_time(scaler_dir, data_dir, run_groups)