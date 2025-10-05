# Plotting angular distributions from my spreadsheet calculations. 

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Scrape FRESCO output file for data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# fort.16 file path
file_path = '/home/jce18b/Esparza_SPS/2023_01_9Be_6Li_d/9Be6Lid_fresco/765MeV/fort.16'

# Initialize lists to store columns of data
data_fresco = []

# Open the file
with open(file_path, 'r') as file:
    for line in file:
        # Try to split the line into float numbers
        try:
            # Convert line into list of floats if possible
            row = [float(i) for i in line.split()]
            data_fresco.append(row)
        except ValueError:
            # Skip lines that cannot be converted to floats (non-numeric lines)
            continue


# FRESCO output data
df_fresco = pd.DataFrame(data_fresco)

#~~~~~~~~~~~~~~~~~ Import the .ods file containing the experimental angular distribution data ~~~~~~~~~~~~~~~~#

pd.set_option('display.max_columns', None)

# Load exp data
ods_file = os.path.expanduser('/home/jce18b/Programs/SisyPhuS/totalangdistdata.ods')
df2 = pd.read_excel(ods_file, engine="odf", sheet_name="angdistdata_short")

# # Export to CSV to find correct cells
# csv_file = os.path.expanduser('/home/jce18b/Esparza_SPS/2023_01_9Be_6Li_d/datacheck.csv')
# df2.to_csv(csv_file, index=False)
# print(f"Data exported to {csv_file}")

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Extract Data ! ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Esparza data 
data_esp = np.array([
    df2.iloc[20:26, 1].values,  # theta values              0
    df2.iloc[20:26, 2].values,  # 6.86 MeV                  1
    df2.iloc[20:26, 3].values,  # 6.86 MeV uncertainties    2
    df2.iloc[20:26, 5].values,  # 7.55 MeV                  3
    df2.iloc[20:26, 6].values,  # 7.55 MeV uncertainties    4
    df2.iloc[20:26, 8].values,  # 7.65 MeV                  5
    df2.iloc[20:26, 9].values,  # 7.65 MeV uncertainties    6
    df2.iloc[20:26, 11].values, # 9.5 MeV                   7
    df2.iloc[20:26, 12].values, # 9.5 MeV uncertainties     8
    df2.iloc[20:26, 14].values, # 9.9 MeV                   9
    df2.iloc[20:26, 15].values, # 9.9 MeV uncertainties     10
    df2.iloc[20:26, 17].values, # 10.75 MeV                 11
    df2.iloc[20:26, 18].values, # 10.75 MeV uncertainties   12
])

# Aslanoglou data
# | 6.86ang | xsec6.86 | 7.55ang | xsec7.55 | 9.5ang | xsec9.5 | 9.9ang | xsec9.9 | 10.75ang | xsec10.75 |
data_aslan = np.array([
    df2.iloc[2:18, 1].values,
    df2.iloc[2:18, 2].values,
    df2.iloc[2:18, 4].values,
    df2.iloc[2:18, 5].values,
    df2.iloc[2:18, 10].values,
    df2.iloc[2:18, 11].values,
    df2.iloc[2:18, 13].values,
    df2.iloc[2:18, 14].values,
    df2.iloc[2:18, 16].values,
    df2.iloc[2:18, 17].values,

])

# Kemper ES data
# | ang0.0 | xsec0.0 | ang2.43 | xsec2.43 | 
data_kemp = np.array([
    df2.iloc[2:43, 23].values,
    df2.iloc[2:43, 24].values,
    df2.iloc[2:43, 26].values,
    df2.iloc[2:43, 27].values,
])

# Esparza, Aslanoglou, and Kemper experimental data
df_esp = pd.DataFrame(data_esp)
df_aslan = pd.DataFrame(data_aslan)
df_kemp = pd.DataFrame(data_kemp)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Elastic ! ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

# region

# Plot the first two columns and ignore the third column
## plt.plot(df[0], df[1], 'o-', label='DWBA')

# # GS ES 
# plt.plot(df[0][0:174], df[1][0:174], 'o-', label='FRESCO DWBA')
# plt.plot(df_kemp.iloc[0, 1:], df_kemp.iloc[1, 1:], 'o-', label='Cook + Kemper')
# plt.yscale('log')
# plt.xlabel('$\Theta_{\mathrm{C.M.}}$ (degrees)')
# plt.ylabel('$d\sigma/d\Omega$ (mb/sr)')
# plt.title('$^{9}Be(^{6}Li,d)^{13}C$ G.S. E.S.')
# plt.grid(True)
# plt.legend()

# Show the plot
# plt.show()

# # ES plots
# fig, axs = plt.subplots(1, 2, figsize=(15, 10))
# axs[0].scatter(df_kemp.iloc[0], df_kemp.iloc[1], color='green', label='Kemper')
# axs[0].set_yscale('log')
# axs[0].set_xlabel('CM Angles (degrees)')
# axs[0].set_ylabel('Cross sections (mb/sr)')
# axs[0].set_title('0 MeV ES (3/2-)')
# axs[0].grid(True)
# axs[0].legend()

# axs[1].scatter(df_kemp.iloc[2], df_kemp.iloc[3], color='green', label='Kemper')
# axs[1].set_yscale('log')
# axs[1].set_xlabel('CM Angles (degrees)')
# axs[1].set_ylabel('Cross sections (mb/sr)')
# axs[1].set_title('2.43 MeV ES (5/2-)')
# axs[1].grid(True)
# axs[1].legend()

# plt.figure
# plt.tight_layout()
# plt.show()

# endregion

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Ang. Dist. ! ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

# region
# # ES Plots
# # 0.0 MeV ES 
# plt.figure("GS ES", figsize=(10, 6))
# plt.scatter(df_kemp.iloc[0,1:], df_kemp.iloc[1, 1:], color='blue', label='Cook')
# plt.yscale('log')
# plt.xlabel('CM Angles (degrees)')
# plt.ylabel('Cross sections (mb/sr)')
# plt.title('0 MeV ES (3/2-)')
# plt.grid(True)
# plt.legend()

# # 2.43 MeV ES
# plt.figure("2.43MeV ES", figsize=(10, 6))
# plt.scatter(df_kemp.iloc[2], df_kemp.iloc[3], color='blue', label='Cook')
# plt.yscale('log')
# plt.xlabel('CM Angles (degrees)')
# plt.ylabel('Cross sections (mb/sr)')
# plt.title('2.43 MeV ES (5/2-)')
# plt.grid(True)
# plt.legend()


# # individual plots for each angular distribution
# # 6.86 MeV
# plt.figure(figsize=(10, 6))
# plt.scatter(df_aslan.iloc[0, 1:], df_aslan.iloc[1, 1:], color='blue', label='Aslanoglou')
# plt.scatter(df_esp.iloc[0], df_esp.iloc[1], color='red', label='Esparza')
# axs[0, 0].errorbar(df_esp.iloc[0], df_esp.iloc[1], yerr=df_esp.iloc[2], fmt='o', color='red', capsize=4)
# #plt.scatter(df_esp.iloc[0], df_esp.iloc[7], color='green', label='Esparza x1 7.65MeV')
# plt.yscale('log')
# plt.xlabel('CM Angles (degrees)')
# plt.ylabel('Cross sections (mb/sr)')
# plt.title('6.86 MeV (5/2+)')
# plt.grid(True)
# plt.legend()

# # 7.55 MeV
# plt.figure(figsize=(10, 6))
# plt.scatter(df_aslan.iloc[2], df_aslan.iloc[3], color='blue', label='Aslanoglou')
# plt.scatter(df_esp.iloc[0], df_esp.iloc[2], color='red', label='Esparza xavg 10.75MeV')
# plt.scatter(df_esp.iloc[0], df_esp.iloc[8], color='green', label='Esparza x1 7.65MeV')
# plt.yscale('log')
# plt.xlabel('CM Angles (degrees)')
# plt.ylabel('Cross sections (mb/sr)')
# plt.title('7.55 MeV (5/2-)')
# plt.grid(True)
# plt.legend()

# # 7.65 MeV
# plt.figure(figsize=(10, 6))
# plt.scatter(df_esp.iloc[0], df_esp.iloc[3], color='red', label='Esparza xavg 10.75MeV')
# plt.scatter(df_esp.iloc[0], df_esp.iloc[9], color='green', label='Esparza x1 7.65MeV')
# plt.yscale('log')
# plt.xlabel('CM Angles (degrees)')
# plt.ylabel('Cross sections (mb/sr)')
# plt.title('7.65 MeV (3/2+)')
# plt.grid(True)
# plt.legend()

# # 9.5 MeV
# plt.figure(figsize=(10, 6))
# plt.scatter(df_aslan.iloc[4], df_aslan.iloc[5], color='blue', label='Aslanoglou')
# plt.scatter(df_esp.iloc[0], df_esp.iloc[4], color='red', label='Esparza')
# plt.yscale('log')
# plt.xlabel('CM Angles (degrees)')
# plt.ylabel('Cross sections (mb/sr)')
# plt.title('9.5 MeV (9/2+)')
# plt.grid(True)
# plt.legend()

# # 9.9 MeV
# plt.figure(figsize=(10, 6))
# plt.scatter(df_aslan.iloc[6], df_aslan.iloc[7], color='blue', label='Aslanoglou')
# plt.scatter(df_esp.iloc[0], df_esp.iloc[5], color='red', label='Esparza')
# plt.scatter(df[0][362:542], df[1][362:542], color='green', label='FRESCO DWBA')
# plt.yscale('log')
# plt.xlabel('CM Angles (degrees)')
# plt.ylabel('Cross sections (mb/sr)')
# plt.title('9.9 MeV (3/2-)')
# plt.grid(True)
# plt.legend()

# # 10.75 MeV
# plt.figure(figsize=(10, 6))
# plt.scatter(df_aslan.iloc[8], df_aslan.iloc[9], color='blue', label='Aslanoglou')
# plt.scatter(df_esp.iloc[0], df_esp.iloc[6], color='red', label='Esparza xavg 10.75MeV')
# plt.scatter(df_esp.iloc[0], df_esp.iloc[12], color='green', label='Esparza x1 7.65MeV')
# plt.yscale('log')
# plt.xlabel('CM Angles (degrees)')
# plt.ylabel('Cross sections (mb/sr)')
# plt.title('10.75 MeV (7/2-)')
# plt.grid(True)
# plt.legend()


# # Adjust layout and show plot
# plt.tight_layout()
# plt.show()

# endregion

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Ang Dists Grid View! ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

# region

# Create a 2x3 grid of subplots for all angular distributions
fig, axs = plt.subplots(2, 3, figsize=(15, 10))

# 6.86 MeV
axs[0, 0].scatter(df_aslan.iloc[0, 1:], df_aslan.iloc[1, 1:], color='blue', label='Aslanoglou')
#axs[0, 0].scatter(df_esp.iloc[0], df_esp.iloc[13], color='green', label='Esparza x1 7.65MeV')
axs[0, 0].scatter(df_esp.iloc[0], df_esp.iloc[1], color='red', label='Esparza')
axs[0, 0].errorbar(df_esp.iloc[0], df_esp.iloc[1], yerr=df_esp.iloc[2], fmt='o', color='red', capsize=4)
axs[0, 0].set_yscale('log')
# axs[0, 0].set_ylim(8e-3, 4e-1)
axs[0, 0].set_xlabel('CM Angles (degrees)')
axs[0, 0].set_ylabel(r'$d\sigma / d\Omega$ (mb/sr)',fontsize=12)
axs[0, 0].set_title(r'6.86 MeV $(5/2^{+})$')
axs[0, 0].grid(True)
axs[0, 0].legend()

# 7.55 MeV
axs[0, 1].scatter(df_aslan.iloc[2], df_aslan.iloc[3], color='blue', label='Aslanoglou')
#axs[0, 1].scatter(df_esp.iloc[0], df_esp.iloc[14], color='green', label='Esparza x1 7.65MeV')
axs[0, 1].scatter(df_esp.iloc[0], df_esp.iloc[3], color='red', label='Esparza')
axs[0, 1].errorbar(df_esp.iloc[0], df_esp.iloc[3], yerr=df_esp.iloc[4], fmt='o', color='red', capsize=4)
axs[0, 1].set_yscale('log')
# axs[0, 1].set_ylim(8e-3, 4e-1)
axs[0, 1].set_xlabel('CM Angles (degrees)')
axs[0, 1].set_ylabel(r'$d\sigma / d\Omega$ (mb/sr)',fontsize=12)
axs[0, 1].set_title(r'7.55 MeV $(5/2^{-})$')
axs[0, 1].grid(True)
axs[0, 1].legend()

# 7.65 MeV
axs[0, 2].scatter(df_esp.iloc[0], df_esp.iloc[5], color='red', label='Esparza')
axs[0, 2].errorbar(df_esp.iloc[0], df_esp.iloc[5], yerr=df_esp.iloc[6], fmt='o', color='red', capsize=4)
#axs[0, 2].scatter(df_esp.iloc[0], df_esp.iloc[15], color='green', label='Esparza x1 7.65MeV')
# axs[0, 2].set_xlim(0, 60)
axs[0, 2].set_yscale('log')
# axs[0, 2].set_ylim(8e-3, 4e-1)
axs[0, 2].set_xlabel('CM Angles (degrees)')
axs[0, 2].set_ylabel(r'$d\sigma / d\Omega$ (mb/sr)',fontsize=12)
axs[0, 2].set_title(r'7.65 MeV $(3/2^{+})$')
axs[0, 2].grid(True)
axs[0, 2].legend()

# 9.5 MeV
axs[1, 0].scatter(df_aslan.iloc[4], df_aslan.iloc[5], color='blue', label='Aslanoglou')
axs[1, 0].scatter(df_esp.iloc[0], df_esp.iloc[7], color='red', label='Esparza')
axs[1, 0].errorbar(df_esp.iloc[0], df_esp.iloc[7], yerr=df_esp.iloc[8], fmt='o', color='red', capsize=4)
axs[1, 0].set_yscale('log')
# axs[1, 0].set_ylim(1e-2, 1e0)
axs[1, 0].set_xlabel('CM Angles (degrees)')
axs[1, 0].set_ylabel(r'$d\sigma / d\Omega$ (mb/sr)',fontsize=12)
axs[1, 0].set_title(r'9.5 MeV $(9/2^{+})$')
axs[1, 0].grid(True)
axs[1, 0].legend()

# 9.9 MeV
axs[1, 1].scatter(df_aslan.iloc[6], df_aslan.iloc[7], color='blue', label='Aslanoglou')
axs[1, 1].scatter(df_esp.iloc[0], df_esp.iloc[9], color='red', label='Esparza')
axs[1, 1].errorbar(df_esp.iloc[0], df_esp.iloc[9], yerr=df_esp.iloc[10], fmt='o', color='red', capsize=4)
axs[1, 1].set_yscale('log')
# axs[1, 1].set_ylim(1e-2, 1e0)
axs[1, 1].set_xlabel('CM Angles (degrees)')
axs[1, 1].set_ylabel(r'$d\sigma / d\Omega$ (mb/sr)',fontsize=12)
axs[1, 1].set_title(r'9.9 MeV $(3/2^{-})$')
axs[1, 1].grid(True)
axs[1, 1].legend()

# 10.75 MeV
axs[1, 2].scatter(df_aslan.iloc[8], df_aslan.iloc[9], color='blue', label='Aslanoglou')
#axs[1, 2].scatter(df_esp.iloc[0], df_esp.iloc[18], color='green', label='Esparza x1 7.65MeV')
axs[1, 2].scatter(df_esp.iloc[0], df_esp.iloc[11], color='red', label='Esparza')
axs[1, 2].errorbar(df_esp.iloc[0], df_esp.iloc[11], yerr=df_esp.iloc[12], fmt='o', color='red', capsize=4)
axs[1, 2].set_yscale('log')
axs[1, 2].set_xlabel('CM Angles (degrees)')
axs[1, 2].set_ylabel(r'$d\sigma / d\Omega$ (mb/sr)',fontsize=12)
axs[1, 2].set_title(r'10.75 MeV $(7/2^{-})$')
axs[1, 2].grid(True)
axs[1, 2].legend()

# Adjust layout and show plot
plt.tight_layout()
plt.show()

# endregion

# ~~~ JCE ~~~ #

