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


def PluckBCI_with_time(scaler_dir, data_dir, run_groups, output_csv="BCI_rates.csv"):
    """
    Extract beam integrator counts and run lengths, then calculate counts per minute.
    """
    run_lengths = get_run_lengths(data_dir)
    all_runs = []
    SR = 100  # sampling rate in Hz
    int_scale = 30  # integrator scale factor [nA]
    Q = int_scale / SR  # charge per count in nano-Coulombs

    print("\n📋 Processing scaler files and run lengths...\n")

    for angle_label, ranges in run_groups.items():  # keep angle info
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
                                        I_total = (Q*beamint_value) / run_len /60
                                        all_runs.append((run_number, beamint_value, run_len, I_total, angle_label))
                                    break

    # Sort by run number
    all_runs_sorted = sorted(all_runs, key=lambda x: x[0])
    # Extract data for plotting
    runs = [r[0] for r in all_runs_sorted]
    I_total = [r[3] for r in all_runs_sorted]
    angles = [r[4] for r in all_runs_sorted]


    # === Plotting ===
    plt.figure(figsize=(12,6))
    plt.plot(runs, I_total, marker='o', linestyle='-', linewidth=1.5, color='blue')
    # plt.scatter(runs, I_per_min, marker='o', color='blue')

    # Color palette (as many as needed)
    angle_palette = [
        "#ec8c8c", "#97e7f1", "#A2E78D", "#c091ec",
        "#f5c681", "#e4a1d5", "#a72f2f", "#8195ec",
        "#C708B7"
    ]

    angle_to_color = {}

    for i, (angle, ranges) in enumerate(run_groups.items()):
        color = angle_palette[i % len(angle_palette)]  # cycle if more angles than colors
        angle_to_color[angle] = color
        for run_min, run_max in ranges:
            
            # shaded block
            plt.axvspan(run_min, run_max, facecolor=color, alpha=0.6, label=angle)
            
            # vertical boundary lines
            plt.axvline(run_min, color=color, linestyle="--", linewidth=1)
            plt.axvline(run_max, color=color, linestyle="--", linewidth=1)

            # optional: label at the center
            mid = (run_min + run_max) / 2
            plt.text(mid, max(I_total)*1.02, f"{angle}", 
                    ha="center", va="bottom", fontsize=10, color="black", fontweight="bold",)


    # Avoid duplicate labels in legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))

    plt.xlabel("Run #")
    plt.ylabel("Beam Current (nA)")
    plt.title("Beam Integrator Current per Seccond vs Run #")
    plt.grid(True, linestyle="-", alpha=0.8)
    plt.legend(by_label.values(), by_label.keys(), title="Scattering Angle", loc="lower right", fontsize=9)
    plt.tight_layout()
    plt.show()

    # Write CSV
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Run", "Counts", "RunLength_minutes", "nA", "Angle"])
        for run_number, counts, run_len, I_total, angle in all_runs_sorted:
            writer.writerow([run_number, counts, run_len, I_total, angle])

    print(f"\n✅ Done! {len(all_runs_sorted)} runs written to {output_csv}")


# === Example usage ===
scaler_dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/scalers"
data_dir   = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/2025_06_13C_DATA/DAQ"

run_groups = {
    "7": [(317, 319),(394, 399), (427, 440), (465, 465)],
    "10": [(314, 315),(378, 393), (426, 426),(441, 447)],
    "12": [(341, 352), (458, 464)],
    "15": [(320, 340), (450, 457)],
    "17": [(369, 377)],
    "20": [(290, 297),(355, 368)],
    "25": [(420, 425)],
    "35": [(415, 419)],
    "40": [(404,414)]
    }

PluckBCI_with_time(scaler_dir, data_dir, run_groups)


