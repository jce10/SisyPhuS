from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
import re
from typing import Iterable


# -----------------------------
# Data containers
# -----------------------------

@dataclass(frozen=True)
class Level:
    energy_mev: float
    jpi: str   # e.g. "3/2+"

@dataclass(frozen=True)
class ParsedJPi:
    J: float       # decimal, e.g. 1.5
    parity: int    # +1 or -1
    raw: str       # original string


# -----------------------------
# Parsing helpers
# -----------------------------

def parse_jpi(jpi_str: str) -> ParsedJPi:
    """
    Parse a Jpi string like:
        '3/2+'
        '5/2-'
        '3+'
        '2-'

    Returns J as decimal and parity as +/-1.
    """
    s = jpi_str.strip().replace(" ", "")

    match = re.fullmatch(r"(\d+(?:/\d+)?)([+-])", s)
    if not match:
        raise ValueError(f"Could not parse Jpi string: {jpi_str!r}")

    j_part, parity_part = match.groups()

    if "/" in j_part:
        J = float(Fraction(j_part))
    else:
        J = float(j_part)

    parity = +1 if parity_part == "+" else -1
    return ParsedJPi(J=J, parity=parity, raw=jpi_str)


def float_is_close_to_int_or_half(x: float, tol: float = 1e-9) -> bool:
    """
    True if x is very close to an integer or half-integer.
    """
    return abs(2 * x - round(2 * x)) < tol


def format_decimal_j(x: float) -> str:
    """
    Format J or j_transfer for FRESCO-friendly decimal output.
    Examples:
        1.5 -> '1.5'
        3.0 -> '3.0'
        2.5 -> '2.5'
    """
    if not float_is_close_to_int_or_half(x):
        return f"{x:.6g}"
    return f"{x:.1f}"


def parity_symbol(parity: int) -> str:
    return "+" if parity == +1 else "-"


# -----------------------------
# Orbital angular momentum helpers
# -----------------------------

L_LETTERS = {
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


def l_to_letter(l_value: int) -> str:
    return L_LETTERS.get(l_value, f"l={l_value}")


def allowed_j_values(l_value: int, s_transfer: float) -> list[float]:
    """
    Return all allowed j values from coupling l with s_transfer:
        j = |l - s|, |l - s| + 1, ..., l + s
    Works for integer or half-integer s_transfer.
    """
    j_min = abs(l_value - s_transfer)
    j_max = l_value + s_transfer

    values = []
    n_steps = int(round(j_max - j_min)) + 1
    for k in range(n_steps):
        j = j_min + k
        values.append(round(j * 2) / 2.0)  # snap to integer/half-integer
    return values


def triangle_allows(Ji: float, j_transfer: float, Jf: float, tol: float = 1e-9) -> bool:
    """
    Angular momentum triangle rule:
        |Ji - j| <= Jf <= Ji + j
    """
    return (abs(Ji - j_transfer) - tol) <= Jf <= (Ji + j_transfer + tol)


# -----------------------------
# Core physics engine
# -----------------------------

def allowed_transfer_states(
    Ji: float,
    pi_i: int,
    Jf: float,
    pi_f: int,
    s_transfer: float,
    pi_transfer: int,
    l_max: int = 8,
    n_value: int = 2,
) -> list[dict]:
    """
    Enumerate allowed transfer states based on:
      - parity conservation
      - angular momentum coupling

    Parameters
    ----------
    Ji, pi_i
        Initial-state spin/parity
    Jf, pi_f
        Final-state spin/parity
    s_transfer, pi_transfer
        Spin and intrinsic parity of transferred cluster/particle
        Example:
            alpha: s=0.0, pi=+1
            neutron/proton: s=0.5, pi=+1
    l_max
        Maximum l to test
    n_value
        Placeholder n value to write into output rows

    Returns
    -------
    list of dict
        Each dict has:
            n, l_int, l_letter, j_transfer
    """
    allowed = []

    for l_value in range(l_max + 1):
        # parity condition:
        # pi_f = pi_i * pi_transfer * (-1)^l
        parity_calc = pi_i * pi_transfer * ((-1) ** l_value)
        if parity_calc != pi_f:
            continue

        for jtr in allowed_j_values(l_value, s_transfer):
            if triangle_allows(Ji, jtr, Jf):
                allowed.append(
                    {
                        "n": n_value,
                        "l_int": l_value,
                        "l_letter": l_to_letter(l_value),
                        "j_transfer": jtr,
                    }
                )

    return allowed


# -----------------------------
# Output writer
# -----------------------------

def build_rows_for_level(
    level: Level,
    Ji: float,
    pi_i: int,
    s_transfer: float,
    pi_transfer: int,
    l_max: int = 8,
    n_value: int = 2,
) -> list[str]:
    """
    Build tab-delimited output rows for one level.
    Output format:
        E    Jpi    n    l    j_transfer

    Notes
    -----
    - E is written as decimal MeV
    - Jpi is written in the original spectroscopic style, e.g. 3/2+
    - j_transfer is written as decimal for FRESCO compatibility
    """
    parsed = parse_jpi(level.jpi)

    allowed = allowed_transfer_states(
        Ji=Ji,
        pi_i=pi_i,
        Jf=parsed.J,
        pi_f=parsed.parity,
        s_transfer=s_transfer,
        pi_transfer=pi_transfer,
        l_max=l_max,
        n_value=n_value,
    )

    rows = []
    for state in allowed:
        row = "\t".join(
            [
                f"{level.energy_mev:.3f}",
                level.jpi,
                str(state["n"]),
                state["l_letter"],
                format_decimal_j(state["j_transfer"]),
            ]
        )
        rows.append(row)

    return rows


def write_state_file(
    levels: Iterable[Level],
    output_file: str,
    Ji: float,
    pi_i: int,
    s_transfer: float,
    pi_transfer: int,
    l_max: int = 8,
    n_value: int = 2,
) -> None:
    """
    Write the tab-delimited transfer-state file.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# E\tJpi\tn\tl\tj_transfer\n")
        for level in levels:
            rows = build_rows_for_level(
                level=level,
                Ji=Ji,
                pi_i=pi_i,
                s_transfer=s_transfer,
                pi_transfer=pi_transfer,
                l_max=l_max,
                n_value=n_value,
            )
            for row in rows:
                f.write(row + "\n")


# -----------------------------
# Example usage
# -----------------------------

if __name__ == "__main__":
    # Example: 9Be(6Li,d)13C alpha transfer
    # 9Be ground state: 3/2-
    Ji_str = "3/2-"
    parsed_i = parse_jpi(Ji_str)

    # alpha transfer:
    # s_alpha = 0, parity = +
    s_transfer = 0.0
    pi_transfer = +1

    levels = [
        Level(energy_mev=4.172, jpi="3/2+"),
        Level(energy_mev=3.854, jpi="5/2-"),
        Level(energy_mev=7.547, jpi="5/2+"),
    ]

    write_state_file(
        levels=levels,
        output_file="allowed_states.txt",
        Ji=parsed_i.J,
        pi_i=parsed_i.parity,
        s_transfer=s_transfer,
        pi_transfer=pi_transfer,
        l_max=8,
        n_value=2,
    )

    print("Wrote allowed_states.txt")