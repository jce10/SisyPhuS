# SisyPhuS
**S**isy**P**hu**S** is a set of scripts for analyzing data for the Super Enge **S**plit-**P**ole **S**pectrograph at FSU. This is not comprehensive so it should be treated more as a scaffolding to full analysis. As I develop more to my personal repo, I'll add the scripts I deem the most useful. 

## Installation
### Clone Repository 
	git clone https://github.com/jce10/SisyPhuS.git
	cd SisyPhuS
### Create and Load Python Virtual Environment and Install Required Python Packages
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt
Note: `pip` is highly recommended as the package installer. 
Note x2: You can name your virtual enviornment something other than ".venv" -- edit this to whatever you'd like. To deactivate the environment, use the command `deactivate` in the active terminal. 

# SisyPhuS Workflow

## Angular Distribution Calculator
    • Reads:
        ◦ Experimental peak volumes
        ◦ The BCI_totals.txt file containing beam charge normalization
    • Computes:
        ◦ Differential cross sections and their uncertainties
    • Outputs:
        ◦ A combined CSV

## Load FRESCO
    Scans all subdirectories automatically (each representing an excitation energy).
    • Finds the second # Theta block, which isolates the excited-state angular distribution.
    • Applies a theta_max cutoff so it’s directly comparable to experiment.
    • Returns a clean dictionary {subdir_name: (angles, xsecs)} for plotting or analysis later.
→ This keeps your loader reusable and fast, since you only call it once.

## Mega Plotter
    Merges all datasets using just energy identifiers in labels (no hard-coded matches).
    • Accepts fresco_data as an argument so you can skip reloading files if you’ve already parsed them.
    • Uses a dynamic subplot grid so the figure scales automatically with your number of states.
    • Includes proper error bars, log-scaling, and clean legends.
