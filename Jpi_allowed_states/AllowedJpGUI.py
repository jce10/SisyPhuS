from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from fractions import Fraction


PARTICLE_PRESETS = {
    "neutron": {"spin": "1/2", "parity": "+"},
    "proton": {"spin": "1/2", "parity": "+"},
    "alpha": {"spin": "0", "parity": "+"},
    "deuteron": {"spin": "1", "parity": "+"},
    "triton": {"spin": "1/2", "parity": "+"},
    "3He": {"spin": "1/2", "parity": "+"},
}

SPECTRO_SYMBOLS = {
    0: "s",
    1: "p",
    2: "d",
    3: "f",
    4: "g",
    5: "h",
    6: "i",
    7: "j",
    8: "k",
    9: "l",
    10: "m",
}


# ------------------------------------------------------------
# Core parsing / physics logic
# ------------------------------------------------------------

def parse_jpi(jpi_str: str) -> tuple[Fraction, int]:
    s = jpi_str.strip().replace(" ", "")
    if not s:
        raise ValueError("Empty Jπ field.")

    if s[-1] not in ["+", "-"]:
        raise ValueError(
            f"Could not parse parity from '{jpi_str}'. Use forms like 1/2+, 3/2-, 2+, 0-."
        )

    parity = +1 if s[-1] == "+" else -1
    j_str = s[:-1]
    if not j_str:
        raise ValueError(f"Could not parse spin from '{jpi_str}'.")

    try:
        J = Fraction(j_str)
    except Exception as exc:
        raise ValueError(
            f"Could not parse spin from '{jpi_str}'. Use integers or fractions like 2, 1/2, 3/2."
        ) from exc

    if J < 0:
        raise ValueError("Spin must be non-negative.")

    return J, parity


def parse_spin(spin_str: str) -> Fraction:
    s = spin_str.strip().replace(" ", "")
    if not s:
        raise ValueError("Transferred spin field is empty.")

    try:
        value = Fraction(s)
    except Exception as exc:
        raise ValueError(
            f"Could not parse transferred spin '{spin_str}'. Use values like 0, 1/2, 1, 3/2."
        ) from exc

    if value < 0:
        raise ValueError("Transferred spin must be non-negative.")

    return value


def format_fraction(frac: Fraction) -> str:
    if frac.denominator == 1:
        return str(frac.numerator)
    return f"{frac.numerator}/{frac.denominator}"


def parity_symbol(parity: int) -> str:
    return "+" if parity == 1 else "-"


def orbital_parity(l_value: int) -> int:
    return +1 if l_value % 2 == 0 else -1


def spectroscopic_label(l_value: int) -> str:
    return SPECTRO_SYMBOLS.get(l_value, f"l={l_value}")


def shell_label(l_value: int) -> str:
    """
    Lightweight label for spectroscopic notation.

    This reports the minimum major shell number N = 2n + l consistent with the
    transfer, using the lowest radial choice n = 0. That means N = l here.
    For a fully nucleus-specific shell assignment, additional structure input is needed.
    """
    shell_N = l_value
    return f"N = {shell_N}, {spectroscopic_label(l_value)}-wave"


def allowed_j_values(l_value: int, spin: Fraction) -> list[Fraction]:
    l_frac = Fraction(l_value, 1)
    j_min = abs(l_frac - spin)
    j_max = l_frac + spin

    values: list[Fraction] = []
    j = j_min
    while j <= j_max:
        values.append(j)
        j += 1
    return values


def can_couple(J_initial: Fraction, j_value: Fraction, J_final: Fraction) -> bool:
    return abs(J_initial - j_value) <= J_final <= (J_initial + j_value)


def find_allowed_l(
    jpi_initial: str,
    jpi_final: str,
    transferred_spin: str,
    transferred_parity: int = +1,
    l_max: int = 8,
) -> dict:
    J_initial, pi_initial = parse_jpi(jpi_initial)
    J_final, pi_final = parse_jpi(jpi_final)
    spin = parse_spin(transferred_spin)

    if l_max < 0:
        raise ValueError("l_max must be non-negative.")

    # Need pi_f = pi_i * pi_particle * (-1)^l
    required_orbital_parity = pi_final * pi_initial * transferred_parity

    parity_requirement_text = (
        f"Parity condition: πf = πi × πparticle × (-1)^l\n"
        f"                 {parity_symbol(pi_final)} = {parity_symbol(pi_initial)} × {parity_symbol(transferred_parity)} × (-1)^l\n"
        f"Therefore, (-1)^l must be {parity_symbol(required_orbital_parity)}."
    )

    parity_family = "even l only" if required_orbital_parity == +1 else "odd l only"

    allowed_results: list[dict] = []

    for l_value in range(l_max + 1):
        if orbital_parity(l_value) != required_orbital_parity:
            continue

        j_candidates = allowed_j_values(l_value, spin)
        working_j = [j for j in j_candidates if can_couple(J_initial, j, J_final)]

        if working_j:
            allowed_results.append(
                {
                    "l": l_value,
                    "all_j": j_candidates,
                    "allowed_j": working_j,
                    "spectro": shell_label(l_value),
                }
            )

    lowest_allowed_l = allowed_results[0]["l"] if allowed_results else None

    return {
        "J_initial": J_initial,
        "pi_initial": pi_initial,
        "J_final": J_final,
        "pi_final": pi_final,
        "transferred_spin": spin,
        "transferred_parity": transferred_parity,
        "l_max": l_max,
        "required_orbital_parity": required_orbital_parity,
        "parity_family": parity_family,
        "parity_requirement_text": parity_requirement_text,
        "allowed": allowed_results,
        "lowest_allowed_l": lowest_allowed_l,
    }


# ------------------------------------------------------------
# GUI helpers
# ------------------------------------------------------------

def insert_text(widget: tk.Text, text: str) -> None:
    widget.configure(state="normal")
    widget.delete("1.0", tk.END)
    widget.insert(tk.END, text)
    widget.configure(state="disabled")


def build_report(result: dict) -> str:
    lines: list[str] = []

    lines.append("Allowed Angular Momentum Transfer Report")
    lines.append("=" * 44)
    lines.append("")
    lines.append(
        f"Initial state:      Jπ = {format_fraction(result['J_initial'])}{parity_symbol(result['pi_initial'])}"
    )
    lines.append(
        f"Final state:        Jπ = {format_fraction(result['J_final'])}{parity_symbol(result['pi_final'])}"
    )
    lines.append(
        f"Transferred particle: {result.get('particle_name', 'custom')}"
    )
    lines.append(
        f"Transferred spin:   s  = {format_fraction(result['transferred_spin'])}"
    )
    lines.append(
        f"Transferred parity: π  = {parity_symbol(result['transferred_parity'])}"
    )
    lines.append(f"Maximum l checked:  {result['l_max']}")
    lines.append("")
    lines.append(result["parity_requirement_text"])
    lines.append(f"Parity filter result: {result['parity_family']}")
    lines.append("")
    lines.append("Coupling rule used:")
    lines.append("  1) j = l ⊕ s  ->  j = |l-s| ... l+s")
    lines.append("  2) Jf must satisfy |Ji-j| ≤ Jf ≤ Ji+j")
    lines.append("")

    if not result["allowed"]:
        lines.append("No allowed l values were found up to the chosen l_max.")
        return "\n".join(lines)

    lines.append("Allowed l values:")
    for item in result["allowed"]:
        l_value = item["l"]
        all_j_str = ", ".join(format_fraction(j) for j in item["all_j"])
        allowed_j_str = ", ".join(format_fraction(j) for j in item["allowed_j"])
        marker = "   <-- lowest allowed l" if l_value == result["lowest_allowed_l"] else ""
        lines.append(f"  l = {l_value}   ({item['spectro']})")
        lines.append(f"      all j from l⊕s:     {all_j_str}")
        lines.append(f"      j values giving Jf: {allowed_j_str}{marker}")

    lines.append("")
    if result["lowest_allowed_l"] is not None:
        lowest_spec = shell_label(result["lowest_allowed_l"])
        lines.append(f"Lowest allowed l: {result['lowest_allowed_l']}   ({lowest_spec})")
    lines.append("Physics note: this script returns quantum-mechanically allowed l values only.")
    lines.append("The shell label shown here uses the lowest radial choice n = 0, so N = l.")
    lines.append("A fully nucleus-specific spectroscopic assignment needs extra shell-structure input.")

    return "\n".join(lines)


def update_particle_fields(
    particle_var: tk.StringVar,
    spin_var: tk.StringVar,
    parity_var: tk.StringVar,
    spin_entry: ttk.Entry,
    parity_box: ttk.Combobox,
) -> None:
    particle = particle_var.get()
    if particle in PARTICLE_PRESETS:
        spin_var.set(PARTICLE_PRESETS[particle]["spin"])
        parity_var.set(PARTICLE_PRESETS[particle]["parity"])
        spin_entry.configure(state="disabled")
        parity_box.configure(state="disabled")
    else:
        spin_entry.configure(state="normal")
        parity_box.configure(state="readonly")


def example_fill(
    initial_var: tk.StringVar,
    final_var: tk.StringVar,
    spin_var: tk.StringVar,
    parity_var: tk.StringVar,
    lmax_var: tk.StringVar,
    particle_var: tk.StringVar,
    example_name: str,
) -> None:
    if example_name == "29Si(d,p)30Si*(2+)":
        initial_var.set("1/2+")
        final_var.set("2+")
        particle_var.set("neutron")
        spin_var.set("1/2")
        parity_var.set("+")
        lmax_var.set("8")
    elif example_name == "9Be(6Li,d)13C*(1/2-) alpha transfer":
        initial_var.set("3/2-")
        final_var.set("1/2-")
        particle_var.set("alpha")
        spin_var.set("0")
        parity_var.set("+")
        lmax_var.set("8")
    elif example_name == "Blank":
        initial_var.set("")
        final_var.set("")
        particle_var.set("neutron")
        spin_var.set("1/2")
        parity_var.set("+")
        lmax_var.set("8")


# ------------------------------------------------------------
# Main GUI
# ------------------------------------------------------------

def main() -> None:
    root = tk.Tk()
    root.title("Angular Momentum Transfer Finder")
    root.geometry("1000x790")
    root.minsize(940, 700)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    mainframe = ttk.Frame(root, padding=14)
    mainframe.pack(fill="both", expand=True)

    title_label = ttk.Label(
        mainframe,
        text="Allowed Angular Momentum Transfer Finder",
        font=("TkDefaultFont", 15, "bold"),
    )
    title_label.pack(anchor="w", pady=(0, 10))

    subtitle = ttk.Label(
        mainframe,
        text=(
            "Enter initial and final Jπ values, choose a transferred particle, "
            "and set the maximum l to check."
        ),
        wraplength=920,
        justify="left",
    )
    subtitle.pack(anchor="w", pady=(0, 12))

    inputs = ttk.LabelFrame(mainframe, text="Inputs", padding=12)
    inputs.pack(fill="x", pady=(0, 12))

    initial_var = tk.StringVar(value="1/2+")
    final_var = tk.StringVar(value="2+")
    spin_var = tk.StringVar(value="1/2")
    parity_var = tk.StringVar(value="+")
    lmax_var = tk.StringVar(value="8")
    example_var = tk.StringVar(value="29Si(d,p)30Si*(2+)")
    particle_var = tk.StringVar(value="neutron")

    ttk.Label(inputs, text="Initial Jπ:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=6)
    ttk.Entry(inputs, textvariable=initial_var, width=18).grid(row=0, column=1, sticky="w", pady=6)

    ttk.Label(inputs, text="Final Jπ:").grid(row=0, column=2, sticky="w", padx=(20, 8), pady=6)
    ttk.Entry(inputs, textvariable=final_var, width=18).grid(row=0, column=3, sticky="w", pady=6)

    ttk.Label(inputs, text="Transferred particle:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=6)
    particle_box = ttk.Combobox(inputs, textvariable=particle_var, width=18, state="readonly")
    particle_box["values"] = (
        "neutron",
        "proton",
        "alpha",
        "deuteron",
        "triton",
        "3He",
        "custom",
    )
    particle_box.grid(row=1, column=1, sticky="w", pady=6)

    ttk.Label(inputs, text="Transferred spin s:").grid(row=1, column=2, sticky="w", padx=(20, 8), pady=6)
    spin_entry = ttk.Entry(inputs, textvariable=spin_var, width=18)
    spin_entry.grid(row=1, column=3, sticky="w", pady=6)

    ttk.Label(inputs, text="Transferred parity:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=6)
    parity_box = ttk.Combobox(inputs, textvariable=parity_var, width=15, state="readonly")
    parity_box["values"] = ("+", "-")
    parity_box.grid(row=2, column=1, sticky="w", pady=6)

    ttk.Label(inputs, text="Maximum l to check:").grid(row=2, column=2, sticky="w", padx=(20, 8), pady=6)
    ttk.Entry(inputs, textvariable=lmax_var, width=18).grid(row=2, column=3, sticky="w", pady=6)

    ttk.Label(inputs, text="Quick example:").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=6)
    example_box = ttk.Combobox(inputs, textvariable=example_var, width=34, state="readonly")
    example_box["values"] = (
        "29Si(d,p)30Si*(2+)",
        "9Be(6Li,d)13C*(1/2-) alpha transfer",
        "Blank",
    )
    example_box.grid(row=3, column=1, sticky="w", pady=6)

    help_text = ttk.Label(
        inputs,
        text=(
            "Accepted formats: Jπ like 1/2+, 3/2-, 2+, 0-.  "
            "Choose a common transferred particle from the dropdown, or select custom to enter spin/parity manually."
        ),
        wraplength=900,
        justify="left",
    )
    help_text.grid(row=4, column=0, columnspan=4, sticky="w", pady=(10, 0))

    outputs = ttk.LabelFrame(mainframe, text="Results", padding=12)
    outputs.pack(fill="both", expand=True)

    text = tk.Text(outputs, wrap="word", font=("Courier New", 11), height=27)
    scroll = ttk.Scrollbar(outputs, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    text.configure(state="disabled")

    button_row = ttk.Frame(mainframe)
    button_row.pack(fill="x", pady=(10, 0))

    def do_calculate() -> None:
        try:
            transferred_parity = +1 if parity_var.get() == "+" else -1
            l_max = int(lmax_var.get())
            result = find_allowed_l(
                jpi_initial=initial_var.get(),
                jpi_final=final_var.get(),
                transferred_spin=spin_var.get(),
                transferred_parity=transferred_parity,
                l_max=l_max,
            )
            result["particle_name"] = particle_var.get()
            report = build_report(result)
            insert_text(text, report)
        except Exception as exc:
            messagebox.showerror("Input error", str(exc))

    def do_clear() -> None:
        example_fill(initial_var, final_var, spin_var, parity_var, lmax_var, particle_var, "Blank")
        update_particle_fields(particle_var, spin_var, parity_var, spin_entry, parity_box)
        insert_text(text, "")

    def do_copy() -> None:
        content = text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Nothing to copy", "There is no report to copy yet.")
            return
        root.clipboard_clear()
        root.clipboard_append(content)
        root.update()
        messagebox.showinfo("Copied", "Report copied to clipboard.")

    def on_example_change(*_args) -> None:
        example_fill(initial_var, final_var, spin_var, parity_var, lmax_var, particle_var, example_var.get())
        update_particle_fields(particle_var, spin_var, parity_var, spin_entry, parity_box)

    def on_particle_change(*_args) -> None:
        update_particle_fields(particle_var, spin_var, parity_var, spin_entry, parity_box)

    example_var.trace_add("write", on_example_change)
    particle_var.trace_add("write", on_particle_change)
    update_particle_fields(particle_var, spin_var, parity_var, spin_entry, parity_box)

    ttk.Button(button_row, text="Calculate", command=do_calculate).pack(side="left")
    ttk.Button(button_row, text="Copy Report", command=do_copy).pack(side="left", padx=8)
    ttk.Button(button_row, text="Clear", command=do_clear).pack(side="left")

    insert_text(
        text,
        "Click 'Calculate' to compute allowed l values.\n\n"
        "This tool applies parity conservation and angular momentum coupling rules only."
    )

    root.mainloop()


if __name__ == "__main__":
    main()
