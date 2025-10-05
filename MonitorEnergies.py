import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import imageio.v2 as imageio  # for writing GIFs
import tempfile

def monitor_energies(dir, run_start, run_end, bins=512, energy_range=(0, 4096),
                     output_csv=None, output_gif=None):
    """
    Plot MonitorEnergy spectra for a range of run numbers,
    optionally save max-bin values to a CSV,
    and create an animated GIF showing spectra added step by step.
    """
    plt.figure(figsize=(8,6))  
    max_bin_list = []
    images = []  # for storing frame file paths

    print(f"{'Run':<6} | {'x-bin (max)':>10} | {'y-max':>8}")
    print("-"*32)

    colors = plt.cm.tab20.colors
    color_idx = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        for run in range(run_start, run_end + 1):
            file = f"run_{run}.parquet"
            path = os.path.join(dir, file)

            if not os.path.exists(path):
                print(f"⚠️ File not found: {file}, skipping.")
                continue

            df = pd.read_parquet(path)
            if "MonitorEnergy" not in df.columns:
                print(f"⚠️ No 'MonitorEnergy' column in {file}, skipping.")
                continue

            # Histogram
            counts, edges = np.histogram(df["MonitorEnergy"], bins=bins, range=energy_range)
            max_bin_index = np.argmax(counts)
            max_bin_center = (edges[max_bin_index] + edges[max_bin_index+1]) / 2
            max_count = counts[max_bin_index]

            print(f"{run:<6} | {max_bin_center:>10.2f} | {max_count:>8}")
            max_bin_list.append({'Run': run, 'MaxBinCenter': max_bin_center, 'MaxCount': max_count})

            # Plot histogram + vertical line
            color = colors[color_idx % len(colors)]
            plt.hist(df["MonitorEnergy"], bins=bins, range=energy_range,
                     histtype="step", linewidth=1.5, color=color, label=f"Run {run}")
            # plt.axvline(max_bin_center, color=color, linestyle='--', linewidth=1.2)

            color_idx += 1

            # Save intermediate frame
            frame_path = os.path.join(tmpdir, f"frame_{run}.png")
            plt.legend()
            plt.xlabel("MonitorEnergy")
            plt.ylabel("Counts")
            plt.title(f"MonitorEnergy spectra (up to run {run})")
            plt.grid(True, alpha=0.3)
            plt.savefig(frame_path)
            images.append(imageio.imread(frame_path))

        plt.show()

        # # Save GIF if requested
        # if output_gif and images:
        #     imageio.mimsave(output_gif, images, duration=0.8)  # 0.8s per frame
        #     print(f"✅ Saved GIF animation to {output_gif}")

    # # Save CSV if requested
    # if output_csv and max_bin_list:
    #     df_max = pd.DataFrame(max_bin_list)
    #     df_max.to_csv(output_csv, index=False)
    #     print(f"✅ Saved max-bin values to {output_csv}")


# Example usage
if __name__ == "__main__":
    monitor_energies(
        dir="/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built",
        run_start=290,
        run_end=465,
        # output_csv="MonitorEnergy_MaxBins.csv",
        # output_gif="MonitorEnergy_Buildup.gif"
    )





