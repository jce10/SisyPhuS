#!/usr/bin/env python3
"""
align_spectra_interactive.py

Interactive spectral aligner (chaos mode): you get shift & scale sliders for BOTH spectra,
live update, Reset and Save controls.

Dependencies: pandas, numpy, matplotlib
Run: python3 align_spectra_interactive.py
"""

import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.widgets import Slider, Button, CheckButtons

# ----------------------------- User settings / defaults -----------------------------
# Replace these paths with your actual parquet files if desired
DEFAULT_PARQUET_1 = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/15deg_13.85kG_300s_cut.parquet"
DEFAULT_PARQUET_2 = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/12C_dp_newtarget/run_233_cut.parquet"

DEFAULT_LABEL_1 = "9Be(6Li,d)13C"
DEFAULT_LABEL_2 = "12C(d,p)13C"

DEFAULT_BINS = 600
DEFAULT_RANGE = (-300, 300)   # Excitation energy window (units MeV in your earlier code)
OUTPUT_SAVE = "aligner_settings.json"
# ------------------------------------------------------------------------------------

def load_xavg(parquet_path):
    """Load Xavg column from parquet (or raise helpful error)."""
    p = Path(parquet_path)
    if not p.exists():
        raise FileNotFoundError(f"Parquet not found: {parquet_path}")
    df = pd.read_parquet(parquet_path, columns=["Xavg"])
    return df["Xavg"].to_numpy(dtype=float)

def build_hist(xarr, bins, energy_range):
    """Return (counts, bin_edges, bin_centers)"""
    counts, edges = np.histogram(xarr, bins=bins, range=energy_range)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return counts.astype(float), edges, centers

def safe_transform(xarr, scale, shift):
    """Apply horizontal transform: x_new = x * scale + shift"""
    return xarr * (scale) + shift

def make_fig_and_widgets():
    # top plot and lower area for sliders/buttons
    fig = plt.figure(figsize=(10, 7))
    ax_main = fig.add_axes([0.07, 0.28, 0.88, 0.66])  # left, bottom, width, height
    # slider axes (four sliders)
    ax_shift1 = fig.add_axes([0.12, 0.18, 0.35, 0.03])
    ax_scale1 = fig.add_axes([0.12, 0.13, 0.35, 0.03])
    ax_shift2 = fig.add_axes([0.60, 0.18, 0.35, 0.03])
    ax_scale2 = fig.add_axes([0.60, 0.13, 0.35, 0.03])

    # buttons
    ax_reset = fig.add_axes([0.12, 0.03, 0.15, 0.06])
    ax_save = fig.add_axes([0.30, 0.03, 0.15, 0.06])
    ax_toggle = fig.add_axes([0.60, 0.03, 0.25, 0.06])

    sliders = {
        "shift1": Slider(ax_shift1, "Shift 1 (MeV)", -50.0, 50.0, valinit=0.0, valstep=0.01),
        "scale1": Slider(ax_scale1, "Scale 1 (×)", 0.1, 1.5, valinit=1.0, valstep=0.0005),
        "shift2": Slider(ax_shift2, "Shift 2 (MeV)", -50.0, 50.0, valinit=0.0, valstep=0.01),
        "scale2": Slider(ax_scale2, "Scale 2 (×)", 0.1, 1.5, valinit=1.0, valstep=0.0005),
    }

    btn_reset = Button(ax_reset, "Reset", hovercolor="0.975")
    btn_save = Button(ax_save, "Save", hovercolor="0.975")
    chk = CheckButtons(ax_toggle, ["Show histogram 1", "Show histogram 2"], [True, True])

    return fig, ax_main, sliders, btn_reset, btn_save, chk

def interactive_aligner(parquet1=DEFAULT_PARQUET_1,
                        parquet2=DEFAULT_PARQUET_2,
                        label1=DEFAULT_LABEL_1,
                        label2=DEFAULT_LABEL_2,
                        bins=DEFAULT_BINS,
                        energy_range=DEFAULT_RANGE):
    # Load data
    x1 = load_xavg(parquet1)
    x2 = load_xavg(parquet2)

    # compute baseline histograms
    counts1_base, edges, centers = build_hist(x1, bins, energy_range)
    counts2_base, _, _ = build_hist(x2, bins, energy_range)

    # initial transforms (identity)
    s1 = 1.0
    t1 = 0.0
    s2 = 1.0
    t2 = 0.0

    # Build figure & widgets
    fig, ax, sliders, btn_reset, btn_save, check = make_fig_and_widgets()

    # Plot initial stepped histograms
    line1, = ax.step(centers, counts1_base, where="mid", color="tab:blue", lw=1.6, label=label1)
    line2, = ax.step(centers, counts2_base, where="mid", color="tab:orange", lw=1.6, label=label2)

    # Also draw filled versions with alpha for ease of viewing (but toggled by CheckButtons)
    fill1 = ax.fill_between(centers, counts1_base, step="mid", alpha=0.12, color="tab:blue")
    fill2 = ax.fill_between(centers, counts2_base, step="mid", alpha=0.12, color="tab:orange")

    ax.set_xlabel("Excitation Energy (MeV)")
    ax.set_ylabel("Counts (arb. units)")
    ax.set_title("Interactive Spectra Aligner — CHAOS MODE")
    ax.grid(alpha=0.35)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_xlim(energy_range)
    # autoscale y to show both histograms initially
    y_max = max(counts1_base.max(), counts2_base.max()) * 1.15
    ax.set_ylim(0, max(10, y_max))

    # text box to show current transform values
    txt = ax.text(0.02, 0.95, "", transform=ax.transAxes, fontsize=10, va="top")

    def update_text():
        txt.set_text(
            f"{label1}: scale={sliders['scale1'].val:.6f}, shift={sliders['shift1'].val:.3f} MeV\n"
            f"{label2}: scale={sliders['scale2'].val:.6f}, shift={sliders['shift2'].val:.3f} MeV"
        )

    # update function used by sliders
    def update(val=None):
        nonlocal line1, line2, fill1, fill2
        s1 = sliders["scale1"].val
        t1 = sliders["shift1"].val
        s2 = sliders["scale2"].val
        t2 = sliders["shift2"].val

        # transform raw arrays, then build their histograms on common edges
        tx1 = safe_transform(x1, s1, t1)
        tx2 = safe_transform(x2, s2, t2)

        c1, _ = np.histogram(tx1, bins=edges)
        c2, _ = np.histogram(tx2, bins=edges)

        # Update step plots: matplotlib.step returns a tuple; we used ax.step earlier -> got Line2D objects
        # But step created multiple segments; simple approach: set line data to centers & counts
        line1.remove()
        line2.remove()
        fill1.remove()
        fill2.remove()

        line1, = ax.step(centers, c1, where="mid", color="tab:blue", lw=1.6, label=label1)
        line2, = ax.step(centers, c2, where="mid", color="tab:orange", lw=1.6, label=label2)
        fill1 = ax.fill_between(centers, c1, step="mid", alpha=0.12, color="tab:blue")
        fill2 = ax.fill_between(centers, c2, step="mid", alpha=0.12, color="tab:orange")

        # update y-limits gently (don't jump when switching)
        ymax = max(c1.max(), c2.max(), 1) * 1.15
        ax.set_ylim(0, ymax)

        update_text()
        fig.canvas.draw_idle()

    # attach sliders to update
    for s in sliders.values():
        s.on_changed(update)

    # Reset button handler
    def reset(event):
        sliders["shift1"].reset()
        sliders["scale1"].reset()
        sliders["shift2"].reset()
        sliders["scale2"].reset()
        update()

    btn_reset.on_clicked(reset)

    # Save handler: write JSON with values
    def save(event):
        settings = {
            "parquet1": str(parquet1),
            "parquet2": str(parquet2),
            "label1": label1,
            "label2": label2,
            "bins": int(bins),
            "energy_range": list(energy_range),
            "scale1": float(sliders["scale1"].val),
            "shift1": float(sliders["shift1"].val),
            "scale2": float(sliders["scale2"].val),
            "shift2": float(sliders["shift2"].val),
        }
        with open(OUTPUT_SAVE, "w") as wf:
            json.dump(settings, wf, indent=2)
        print(f"✅ Aligner settings saved to {OUTPUT_SAVE}")

    btn_save.on_clicked(save)

    # Checkbuttons handler (toggle visibility)
    def toggle_visibility(label):
        # label is string of clicked item
        visible1 = check.get_status()[0]
        visible2 = check.get_status()[1]
        # remove & re-add works but simpler: set visible on artists
        line_artists = [a for a in ax.get_lines()]
        # assume first is hist1, second hist2
        try:
            if len(line_artists) >= 2:
                line_artists[0].set_visible(visible1)
                line_artists[1].set_visible(visible2)
            fill1.set_visible(visible1)
            fill2.set_visible(visible2)
        except Exception:
            pass
        fig.canvas.draw_idle()

    check.on_clicked(toggle_visibility)

    # initial text
    update_text()

    plt.show()


# ---------------------------- run as script ----------------------------
if __name__ == "__main__":
    try:
        interactive_aligner()
    except Exception as e:
        print("Error running aligner:", e)
        raise
