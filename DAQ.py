import os
import re
import pandas as pd
import matplotlib.pyplot as plt

def parse_run_info_file(path):
    data = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or '=' not in line:
                continue
            k, v = line.split('=', 1)
            data[k.strip()] = v.strip()
    return data

def safe_float_prefix(x):
    """Return leading numeric portion of a string, or None."""
    if x is None:
        return None
    m = re.match(r'^([+-]?\d+(\.\d+)?([eE][+-]?\d+)?).*', x.strip())
    return float(m.group(1)) if m else None

def collect_channel_telemetry(
    data_dir, 
    channels=(3,5), 
    board_prefix="board.0-11-89", 
    run_range=None
):
    """
    Parse run.info in run_xxx folders and extract telemetry for the given channels.

    Parameters
    ----------
    data_dir : str
        Path to the DATA folder with run_xxx subfolders.
    channels : tuple
        Which channel numbers to extract (default: (3,5)).
    board_prefix : str
        Board identifier prefix in run.info (default: "board.0-11-89").
    run_range : tuple or None
        (min_run, max_run). If None, process all runs.
    """
    rows = []
    folders = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir,d)) and d.startswith("run_")]
    folders = sorted(folders, key=lambda s: int(re.search(r'(\d+)', s).group(1)))

    for folder in folders:
        run_num = int(re.search(r'(\d+)', folder).group(1))
        if run_range is not None:
            low, high = run_range
            if run_num < low or run_num > high:
                continue

        info_path = os.path.join(data_dir, folder, "run.info")
        if not os.path.isfile(info_path):
            continue
        info = parse_run_info_file(info_path)

        row = {"run": run_num}

        # board-level items
        for key in ["readout.rate", "throughput"]:
            full_key = f"{board_prefix}.{key}"
            if full_key in info:
                row[key] = safe_float_prefix(info[full_key])
            elif key in info:
                row[key] = safe_float_prefix(info[key])
            else:
                row[key] = None

        # channel-specific items
        for ch in channels:
            ch_prefix = f"{board_prefix}.{ch}"
            icr_val, ocr_val, throughput_val = None, None, None
            rej_sum, found_rej = 0.0, False

            for k, v in info.items():
                if not k.startswith(ch_prefix):
                    continue
                tail = k[len(ch_prefix):].lstrip('.')
                if tail.endswith("icr"):
                    icr_val = safe_float_prefix(v)
                elif tail.endswith("ocr"):
                    ocr_val = safe_float_prefix(v)
                elif tail.endswith("throughput"):
                    throughput_val = safe_float_prefix(v)
                elif '.rejections.' in tail or tail.startswith('rejections'):
                    found_rej = True
                    rej_sum += safe_float_prefix(v) or 0.0

            row[f"icr_ch{ch}"] = icr_val
            row[f"ocr_ch{ch}"] = ocr_val
            row[f"throughput_ch{ch}"] = throughput_val
            row[f"rejections_ch{ch}"] = rej_sum if found_rej else None
            row[f"live_frac_ch{ch}"] = (float(ocr_val) / float(icr_val)) if (icr_val and ocr_val is not None and icr_val != 0) else None

        rows.append(row)

    df = pd.DataFrame(rows).sort_values("run").reset_index(drop=True)
    return df

def plot_channel_telemetry_full(df, channels=(3,5)):
    """
    Make a 2x3 grid of subplots for key telemetry quantities per run.
    Includes: ICR, OCR, Throughput, Live Fraction, Rejections, ICR/OCR ratio
    """
    runs = df['run']
    
    fig, axs = plt.subplots(2, 3, figsize=(18,8))
    axs = axs.flatten()

    # 1. ICR per channel
    for ch in channels:
        axs[0].plot(runs, df[f'icr_ch{ch}'], marker='o', linestyle='-', label=f'CH {ch}')
    axs[0].set_ylabel("ICR (counts/s)")
    axs[0].set_title("Input Count Rate (ICR)")
    axs[0].grid(True)
    axs[0].legend()

    # 2. OCR per channel
    for ch in channels:
        axs[1].plot(runs, df[f'ocr_ch{ch}'], marker='o', linestyle='-', label=f'CH {ch}')
    axs[1].set_ylabel("OCR (counts/s)")
    axs[1].set_title("Output Count Rate (OCR)")
    axs[1].grid(True)
    axs[1].legend()

    # 3. Throughput per channel
    for ch in channels:
        axs[2].plot(runs, df[f'throughput_ch{ch}'], marker='o', linestyle='-', label=f'CH {ch}')
    axs[2].set_ylabel("Throughput")
    axs[2].set_title("Throughput")
    axs[2].grid(True)
    axs[2].legend()

    # 4. Live fraction per channel
    for ch in channels:
        axs[3].plot(runs, df[f'live_frac_ch{ch}'], marker='o', linestyle='-', label=f'CH {ch}')
    axs[3].set_ylabel("Live Fraction")
    axs[3].set_title("Live Fraction")
    axs[3].grid(True)
    axs[3].legend()

    # 5. Rejections per channel
    for ch in channels:
        axs[4].plot(runs, df[f'rejections_ch{ch}'], marker='o', linestyle='-', label=f'CH {ch}')
    axs[4].set_ylabel("Rejections")
    axs[4].set_title("Rejections")
    axs[4].grid(True)
    axs[4].legend()

    axs[5].set_visible(False)  # Empty subplot

    plt.tight_layout()
    plt.show()





# data directory
data_dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/2025_06_13C_DATA/DAQ"

# Only runs x – y, channels 3 and 5
df = collect_channel_telemetry(data_dir, channels=(3,5), run_range=(290,464))
plot_channel_telemetry_full(df, channels=(3,5))

# Save to CSV
df.to_csv("telemetry_runs290to464.csv", index=False)





