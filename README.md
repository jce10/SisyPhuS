# SisyPhuS
Analysis scripts for SE-SPS data 

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