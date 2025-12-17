import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def plot_13C_overlay(parquet_1, parquet_2,
                     label_1="6Li,d", label_2="d,p",
                     bins=600, energy_range=(-300,300),
                     shift_1=0.0, scale_1=1.0,
                     shift_2=0.0, scale_2=1.0):
    """
    Overlay 13C spectra with horizontal shift & stretch (no amplitude scaling).
    - shift_2: moves spectrum 2 left/right.
    - scale_2: stretches/compresses spectrum 2 energy axis.
    """

    # --- Load only the Xavg column ---
    df1 = pd.read_parquet(parquet_1, columns=['Xavg'])
    df2 = pd.read_parquet(parquet_2, columns=['Xavg'])

    # --- Apply horizontal scaling and shift to spectra ---
    df1['Xavg'] = df1['Xavg'] * scale_1 + shift_1
    df2['Xavg'] = df2['Xavg'] * scale_2 + shift_2

    # --- Histograms (raw counts) ---
    counts1, edges = np.histogram(df1['Xavg'], bins=bins, range=energy_range)
    counts2, _     = np.histogram(df2['Xavg'], bins=bins, range=energy_range)

    # --- Plot ---
    plt.figure(figsize=(8,5))
    bin_centers = 0.5 * (edges[:-1] + edges[1:])
    plt.step(bin_centers, counts1, where='mid', linewidth=1.4, label=label_1)
    plt.step(bin_centers, counts2, where='mid', linewidth=1.4, label=label_2)

    # plt.rcParams['text.usetex'] = True
    plt.xlabel("Scaled Focal Plane Position (mm)", fontsize=20)
    plt.ylabel("Counts (arb. units)", fontsize=20)
    plt.title(r"$^{13}C$ Spectra $\theta =15\degree$", fontsize=25)
    plt.legend(fontsize=18)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

def plot_13C_individual(parquet, label=None,
                     bins=600, energy_range=(-300,300),
                     shift=0.0, scale=1.0,
                     rxn=None):
    """
    Plot individual 13C spectrum with horizontal shift & stretch (no amplitude scaling).
    - shift: moves spectrum left/right.
    - scale: stretches/compresses spectrum energy axis.
    """

    # --- Load only the Xavg column ---
    df = pd.read_parquet(parquet, columns=['Xavg'])

    # --- Apply horizontal scaling and shift to spectra ---
    df['Xavg'] = df['Xavg'] * scale + shift

    # --- Histograms (raw counts) ---
    counts, edges = np.histogram(df['Xavg'], bins=bins, range=energy_range)

    # --- Plot ---
    plt.figure(figsize=(8,5))
    bin_centers = 0.5 * (edges[:-1] + edges[1:])
    plt.step(bin_centers, counts, where='mid', linewidth=1.4, label=label)


    plt.xlabel("Focal Plane Position (mm)", fontsize=20)
    plt.ylabel("Counts (arb. units)", fontsize=20)
    plt.title(rxn + " Spectrum", fontsize=30)
    plt.legend(fontsize=18)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


# ----------------------------
if __name__ == "__main__":
    # plot_13C_overlay(
    #     parquet_1= "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/15deg_13.85kG_total_cut.parquet",
    #     parquet_2= "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/12C_dp_newtarget/run_233_cut.parquet",
    #     label_1= r"$^{9}Be(^{6}Li,d)^{13}C$" + "\nB= 13.85 kG\n E= 32 MeV",
    #     label_2= r"$^{12}C(d,p)^{13}C$" + "\nB= 5.6 kG\nE= 16 MeV",
    #     shift_1= -2.269999999999996,
    #     scale_1= 1.403,
    #     shift_2= 45.5,
    #     scale_2= 0.5225
    # )

    plot_13C_individual(
        parquet= "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/15deg_13.85kG_300s_cut.parquet",
        label= "B = 13.85 kG\n E = 32 MeV\n" + r"$\theta = 15\degree$",
        shift= 0.0,
        scale= 1.0,
        rxn= r"$^{9}Be(^{6}Li,d)^{13}C$"
    )

    plot_13C_individual(
        parquet= "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/12C_dp_newtarget/run_233_cut.parquet",
        label= "B = 5.6 kG\n E = 16 MeV\n" + r"$\theta = 15\degree$",
        shift= 0.0,
        scale= 1.0,
        rxn= r"$^{12}C(d,p)^{13}C$"
    )


