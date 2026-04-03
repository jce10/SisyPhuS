from __future__ import annotations

import sys
from fractions import Fraction

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


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
    parity_family = "even l only" if required_orbital_parity == +1 else "odd l only"

    parity_requirement_text = (
        f"Parity condition: πf = πi × πparticle × (-1)^l\n"
        f"                 {parity_symbol(pi_final)} = {parity_symbol(pi_initial)} × {parity_symbol(transferred_parity)} × (-1)^l\n"
        f"Therefore, (-1)^l must be {parity_symbol(required_orbital_parity)}."
    )

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


def build_report(result: dict, particle_name: str) -> str:
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
    lines.append(f"Transferred particle: {particle_name}")
    lines.append(f"Transferred spin:   s  = {format_fraction(result['transferred_spin'])}")
    lines.append(f"Transferred parity: π  = {parity_symbol(result['transferred_parity'])}")
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
        lines.append(
            f"Lowest allowed l: {result['lowest_allowed_l']}   ({shell_label(result['lowest_allowed_l'])})"
        )
    lines.append("Physics note: this tool returns quantum-mechanically allowed l values only.")
    lines.append("The shell label shown here uses the lowest radial choice n = 0, so N = l.")
    lines.append("A fully nucleus-specific orbital assignment still needs shell-structure input.")
    return "\n".join(lines)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Angular Momentum Transfer Finder — Qt6")
        self.resize(1120, 820)
        self._build_ui()
        self._wire_signals()
        self.apply_example("29Si(d,p)30Si*(2+)")
        self.update_particle_fields()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Allowed Angular Momentum Transfer Finder")
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(
            "Enter initial and final Jπ values, choose a transferred particle, and set the maximum l to check."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        input_box = QGroupBox("Inputs")
        input_layout = QGridLayout(input_box)
        input_layout.setHorizontalSpacing(16)
        input_layout.setVerticalSpacing(10)

        self.initial_edit = QLineEdit()
        self.final_edit = QLineEdit()
        self.spin_edit = QLineEdit()
        self.lmax_edit = QLineEdit("8")

        self.particle_combo = QComboBox()
        self.particle_combo.addItems([
            "neutron",
            "proton",
            "alpha",
            "deuteron",
            "triton",
            "3He",
            "custom",
        ])

        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["+", "-"])

        self.example_combo = QComboBox()
        self.example_combo.addItems([
            "29Si(d,p)30Si*(2+)",
            "9Be(6Li,d)13C*(1/2-) alpha transfer",
            "Blank",
        ])

        input_layout.addWidget(QLabel("Initial Jπ:"), 0, 0)
        input_layout.addWidget(self.initial_edit, 0, 1)
        input_layout.addWidget(QLabel("Final Jπ:"), 0, 2)
        input_layout.addWidget(self.final_edit, 0, 3)

        input_layout.addWidget(QLabel("Transferred particle:"), 1, 0)
        input_layout.addWidget(self.particle_combo, 1, 1)
        input_layout.addWidget(QLabel("Transferred spin s:"), 1, 2)
        input_layout.addWidget(self.spin_edit, 1, 3)

        input_layout.addWidget(QLabel("Transferred parity:"), 2, 0)
        input_layout.addWidget(self.parity_combo, 2, 1)
        input_layout.addWidget(QLabel("Maximum l to check:"), 2, 2)
        input_layout.addWidget(self.lmax_edit, 2, 3)

        input_layout.addWidget(QLabel("Quick example:"), 3, 0)
        input_layout.addWidget(self.example_combo, 3, 1)

        help_label = QLabel(
            "Accepted formats: Jπ like 1/2+, 3/2-, 2+, 0-. Choose a common transferred particle from the dropdown, or select custom to enter spin/parity manually."
        )
        help_label.setWordWrap(True)
        input_layout.addWidget(help_label, 4, 0, 1, 4)

        layout.addWidget(input_box)

        self.summary_label = QLabel("Ready")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.summary_label.setStyleSheet(
            "QLabel { padding: 8px 10px; border-radius: 8px; background-color: #20242b; }"
        )
        layout.addWidget(self.summary_label)

        result_box = QGroupBox("Results")
        result_layout = QVBoxLayout(result_box)
        self.report_edit = QPlainTextEdit()
        self.report_edit.setReadOnly(True)
        report_font = QFont("Monospace")
        report_font.setStyleHint(QFont.StyleHint.TypeWriter)
        report_font.setPointSize(10)
        self.report_edit.setFont(report_font)
        self.report_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.report_edit.setPlainText(
            "Click 'Calculate' to compute allowed l values.\n\n"
            "This tool applies parity conservation and angular momentum coupling rules only."
        )
        result_layout.addWidget(self.report_edit)
        layout.addWidget(result_box, stretch=1)

        button_row = QHBoxLayout()
        self.calc_button = QPushButton("Calculate")
        self.copy_button = QPushButton("Copy Report")
        self.clear_button = QPushButton("Clear")
        button_row.addWidget(self.calc_button)
        button_row.addWidget(self.copy_button)
        button_row.addWidget(self.clear_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

    def _wire_signals(self) -> None:
        self.particle_combo.currentTextChanged.connect(self.update_particle_fields)
        self.example_combo.currentTextChanged.connect(self.apply_example)
        self.calc_button.clicked.connect(self.calculate)
        self.copy_button.clicked.connect(self.copy_report)
        self.clear_button.clicked.connect(self.clear_inputs)

    def update_particle_fields(self) -> None:
        particle = self.particle_combo.currentText()
        if particle in PARTICLE_PRESETS:
            self.spin_edit.setText(PARTICLE_PRESETS[particle]["spin"])
            self.parity_combo.setCurrentText(PARTICLE_PRESETS[particle]["parity"])
            self.spin_edit.setEnabled(False)
            self.parity_combo.setEnabled(False)
        else:
            self.spin_edit.setEnabled(True)
            self.parity_combo.setEnabled(True)

    def apply_example(self, example_name: str) -> None:
        if example_name == "29Si(d,p)30Si*(2+)":
            self.initial_edit.setText("1/2+")
            self.final_edit.setText("2+")
            self.particle_combo.setCurrentText("neutron")
            self.spin_edit.setText("1/2")
            self.parity_combo.setCurrentText("+")
            self.lmax_edit.setText("8")
        elif example_name == "9Be(6Li,d)13C*(1/2-) alpha transfer":
            self.initial_edit.setText("3/2-")
            self.final_edit.setText("1/2-")
            self.particle_combo.setCurrentText("alpha")
            self.spin_edit.setText("0")
            self.parity_combo.setCurrentText("+")
            self.lmax_edit.setText("8")
        elif example_name == "Blank":
            self.initial_edit.clear()
            self.final_edit.clear()
            self.particle_combo.setCurrentText("neutron")
            self.spin_edit.setText("1/2")
            self.parity_combo.setCurrentText("+")
            self.lmax_edit.setText("8")
        self.update_particle_fields()

    def calculate(self) -> None:
        try:
            transferred_parity = +1 if self.parity_combo.currentText() == "+" else -1
            l_max = int(self.lmax_edit.text().strip())

            result = find_allowed_l(
                jpi_initial=self.initial_edit.text(),
                jpi_final=self.final_edit.text(),
                transferred_spin=self.spin_edit.text(),
                transferred_parity=transferred_parity,
                l_max=l_max,
            )

            particle_name = self.particle_combo.currentText()
            self.report_edit.setPlainText(build_report(result, particle_name))

            if result["lowest_allowed_l"] is None:
                self.summary_label.setText("No allowed l values found up to the chosen l_max.")
            else:
                l_value = result["lowest_allowed_l"]
                self.summary_label.setText(
                    f"Lowest allowed transfer: l = {l_value} ({spectroscopic_label(l_value)}-wave); parity filter gives {result['parity_family']}."
                )
        except Exception as exc:
            QMessageBox.critical(self, "Input error", str(exc))

    def copy_report(self) -> None:
        text = self.report_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Nothing to copy", "There is no report to copy yet.")
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Report copied to clipboard.")

    def clear_inputs(self) -> None:
        self.example_combo.setCurrentText("Blank")
        self.report_edit.clear()
        self.summary_label.setText("Ready")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
