import os
import re
import csv

def PluckBCI(scaler_dir, run_groups, output_dir=None, output_csv="BCI_counts.csv", totals_txt="BCI_totals.txt"):
    """
    Extract beam integrator (BCI) counts from scaler files, grouped by angles.

    Parameters
    ----------
    scaler_dir : str
        Path to directory containing scaler files (e.g. run_XXX_scalers.txt).
    run_groups : dict
        Dictionary mapping angle labels to lists of (min_run, max_run) tuples.
    output_dir : str or None
        Directory to save the outputs. If None, defaults to scaler_dir.
    output_csv : str
        Filename for the detailed CSV output.
    totals_txt : str
        Filename for the summary totals text file.
    """
    all_results = {}   # {angle_label: [(run, counts), ...]}
    angle_totals = {}
    grand_total = 0

    # Print summary
    print("\n📋 Run Range Summary by Angle:")
    for angle_label, ranges in run_groups.items():
        print(f"{angle_label:<15}", end='')
        print('   '.join([f"{r[0]}–{r[1]}" for r in ranges]))

    print("\n📤 Processing files...\n")

    # Loop over angle groups
    for angle_label, ranges in run_groups.items():
        angle_total = 0
        run_beamints = []

        for filename in os.listdir(scaler_dir):
            match = re.match(r'run_(\d+)_scalers\.txt', filename)
            if not match:
                continue

            run_number = int(match.group(1))
            in_range = any(run_min <= run_number <= run_max for run_min, run_max in ranges)
            if not in_range:
                continue

            file_path = os.path.join(scaler_dir, filename)
            with open(file_path, 'r') as f:
                for line in f:
                    if "beamint" in line:
                        parts = line.strip().split()
                        if len(parts) == 2 and parts[0] == "beamint":
                            beamint_value = int(parts[1])
                            run_beamints.append((run_number, beamint_value))
                            angle_total += beamint_value
                            grand_total += beamint_value
                        break

        if run_beamints:
            run_beamints.sort(key=lambda x: x[0])
            all_results[angle_label] = run_beamints
            angle_totals[angle_label] = angle_total

    # Pick output directory
    if output_dir is None:
        output_dir = scaler_dir
    os.makedirs(output_dir, exist_ok=True)

    # --- Write detailed CSV ---
    out_csv = os.path.join(output_dir, output_csv)
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Angle", "Run", "Counts"])
        for angle, runs in all_results.items():
            for run_number, beamint in runs:
                writer.writerow([angle, run_number, beamint])
            writer.writerow([angle, " total = ", angle_totals[angle]])

    # --- Write summary TXT ---
    out_txt = os.path.join(output_dir, totals_txt)
    with open(out_txt, "w") as f:
        f.write("angle\t|\ttotal\t|\tscale\n")
        for angle, total in angle_totals.items():
            scale = 10
            f.write(f"{angle}\t|\t{total}\t|\t{scale:d}\n")

    # --- Print summary ---
    # print(f"\n✅ Done! Results written to:\n  {out_csv}\n  {out_txt}")
    # print(f"\n📊 Total BeamInt by angle:")
    # for angle_label, total in angle_totals.items():
    #     print(f"  {angle_label}: {total:,}")
    # print(f"\n📈 Grand Total BeamInt across all angles: {grand_total:,}")


if __name__ == "__main__":
    
    
    # 9Be(6Li,d)13C scalers
    # scaler_dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/scalers/9Be_6Lid_scalers"
    # output_dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/6Lid/BCI_outputs"

    # # 6Lid higher Ex runs
    run_groups = {
    #     # "7": [(317, 319),(394, 398), (427, 440), (465, 465)],
        "10": [(314, 315),(378, 382),(385,389), (426,426),(441, 447)],
        "12": [(341, 346),(351, 352), (458, 464)],
        "15": [(320, 329), (340, 340), (450, 457)],
        "17": [(369, 375)],
        "20": [(355,364)],
        "25": [(420, 425)],
        "35": [(415, 418)],
        "40": [(404, 413)]
    }

    # # 6Lid lower Ex runs
    # run_groups = {
    #     # "7": [(399, 399)],
    #     "10": [(383, 384), (390,393)],
    #     "12": [(347, 350)],
    #     "15": [(330, 339)],
    #     "17": [(376, 377)],
    #     "20": [(290, 297),(365, 368)],
    #     "35":[(419, 419)],
    #     "40": [(414, 414)]
    # }

    # PluckBCI(scaler_dir, run_groups, output_dir=output_dir, output_csv="BCI_counts_6Lid_HL.csv")
    # PluckBCI(scaler_dir, run_groups, output_dir=output_dir, output_csv="BCI_counts_6Lid_LL.csv")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

    # 12C(d,p)13C scalers
    # scaler_dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/scalers/12Cdp_scalers"
    # output_dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/dp/BCI_outputs"

    # # dp low field setting
    # run_groups = {
    #     "10": [(217, 218), (237, 241)],
    #     "15": [(211, 213), (233, 236)],
    #     "20": [(222, 228)],
    #     "32": [(155, 160)],
    #     "35": [(173, 178)],
    #     "40": [(140, 149)],
    #     "45": [(123, 124), (162, 168), (196, 199)],
    #     "50": [(107, 113), (191, 195)],
    # }

    # # dp high field setting
    # run_groups = {
    #     "10": [(215, 215)],
    #     "15": [(207, 208), (229, 230)],
    #     "20": [(125, 126), (187, 187)],
    #     "32": [(150, 152)],
    #     "35": [(171, 171)],
    #     "40": [(133, 137)],
    #     "45": [(103, 103), (118, 118), (170, 170), (201, 201)],
    #     "50": [(116, 117), (188, 189)],
    # }

    # PluckBCI(scaler_dir, run_groups, output_dir=output_dir, output_csv="BCI_counts_6Lid_HL.csv")
    # PluckBCI(scaler_dir, run_groups, output_dir=output_dir, output_csv="BCI_counts_6Lid_LL.csv")

    PluckBCI(scaler_dir, run_groups, output_dir=output_dir, output_csv="BCI_totals.txt")
    
    
