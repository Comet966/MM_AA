"""Generate LaTeX fragments and CSV curves from the verified JSON outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "report"


def fmt(value: float | None) -> str:
    return "--" if value is None else f"{value:.4f}"


def small_table(title: str, label: str, time_label: str, rows: list[dict]) -> str:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        rf"\caption{{{title}}}\label{{{label}}}",
        r"\small",
        r"\begin{tabular}{rrrrrr}",
        r"\toprule",
        rf"{time_label} & 0 cm & 0.5 cm & 1.0 cm & 1.5 cm & 2.0 cm \\",
        r"\midrule",
    ]
    for row in rows:
        time_value = row["time_s"] / 3600.0 if time_label == "时间/h" else row["time_s"]
        time_text = f"{time_value:.1f}" if time_label == "时间/h" else f"{time_value:.0f}"
        lines.append(time_text + " & " + " & ".join(fmt(v) for v in row["values"]) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def long_q3_table(rows: list[dict]) -> str:
    lines = [
        r"\begin{longtable}{rrrrrr}",
        r"\caption{问题3每6 h及达标时刻的水分浓度}\label{tab:q3}\\",
        r"\toprule",
        r"时间/h & 0 cm & 0.5 cm & 1.0 cm & 1.5 cm & 2.0 cm \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"时间/h & 0 cm & 0.5 cm & 1.0 cm & 1.5 cm & 2.0 cm \\",
        r"\midrule",
        r"\endhead",
    ]
    for index, row in enumerate(rows):
        time_h = row["time_s"] / 3600.0
        time_text = f"{time_h:.4f}" if index == len(rows) - 1 else f"{time_h:.0f}"
        lines.append(time_text + " & " + " & ".join(fmt(v) for v in row["values"]) + r" \\")
    lines.extend([r"\bottomrule", r"\end{longtable}"])
    return "\n".join(lines)


def long_q4_table(rows: list[dict]) -> str:
    lines = [
        r"\begin{longtable}{rrrrrr}",
        r"\caption{问题4每6 h及达标时刻的水分浓度}\label{tab:q4}\\",
        r"\toprule",
        r"时间/h & 半径/cm & 0 cm & 0.5 cm & 1.0 cm & 药材表面 \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"时间/h & 半径/cm & 0 cm & 0.5 cm & 1.0 cm & 药材表面 \\",
        r"\midrule",
        r"\endhead",
    ]
    for index, row in enumerate(rows):
        time_h = row["time_s"] / 3600.0
        time_text = f"{time_h:.4f}" if index == len(rows) - 1 else f"{time_h:.0f}"
        values = row["values"]
        lines.append(
            f"{time_text} & {row['radius_cm']:.4f} & {fmt(values[0])} & "
            f"{fmt(values[1])} & {fmt(values[2])} & {fmt(row['surface'])} " + r"\\"
        )
    lines.extend([r"\bottomrule", r"\end{longtable}"])
    return "\n".join(lines)


def write_curve(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time_h", "center_moisture"])
        writer.writerow([0.0, 2.55])
        for row in rows:
            writer.writerow([row["time_s"] / 3600.0, row["values"][0]])


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary = json.loads((ROOT / "outputs" / "summary.json").read_text(encoding="utf-8"))
    validation = json.loads((ROOT / "outputs" / "validation.json").read_text(encoding="utf-8"))
    dry = summary["dry_times_h"]
    mechanism = summary["mechanism"]
    radius = summary["radius"]
    environment = summary["environment"]

    net_reduction = 100.0 * (
        dry["question3_appendix3_fixed_radius"] - dry["question4_appendix4_shrinking"]
    ) / dry["question3_appendix3_fixed_radius"]
    macros = rf"""
\newcommand{{\QThreeDryHours}}{{{dry['question3_appendix3_fixed_radius']:.4f}}}
\newcommand{{\QFourDryHours}}{{{dry['question4_appendix4_shrinking']:.4f}}}
\newcommand{{\AppendixFourFixedHours}}{{{dry['appendix4_fixed_radius']:.4f}}}
\newcommand{{\NoCoordinateCaseHours}}{{{dry['question4_without_coordinate_term_sensitivity']:.4f}}}
\newcommand{{\ShrinkReduction}}{{{mechanism['shrinkage_time_reduction_percent_vs_appendix4_fixed']:.2f}\%}}
\newcommand{{\AppendixIncrease}}{{{mechanism['appendix_change_percent_vs_question3']:.2f}\%}}
\newcommand{{\OmitCoordinateDifference}}{{{mechanism['omit_coordinate_term_difference_percent']:.2f}\%}}
\newcommand{{\NetReduction}}{{{net_reduction:.2f}\%}}
\newcommand{{\StableStartHours}}{{{environment['stable_start_s']/3600.0:.3f}}}
\newcommand{{\PlateauTemperature}}{{{environment['plateau_temperature_c']:.4f}}}
\newcommand{{\PlateauMoisture}}{{{environment['plateau_moisture']:.6f}}}
\newcommand{{\QFourDryRadius}}{{{radius['q4_dry_cm']:.4f}}}
\newcommand{{\ConservationError}}{{{validation['closed_system_moisture_conservation_relative_error']:.2e}}}
\newcommand{{\EquilibriumError}}{{{validation['uniform_equilibrium_max_abs_error']:.2e}}}
\newcommand{{\QThreeGridChange}}{{{100*validation['q3_space_last_refinement_relative_change']:.3f}\%}}
\newcommand{{\QFourGridChange}}{{{100*validation['q4_space_last_refinement_relative_change']:.3f}\%}}
\newcommand{{\QFourTimeChange}}{{{100*validation['q4_time_30_vs_15_relative_change']:.5f}\%}}
\newcommand{{\QOneMoistureProfileError}}{{{validation['profile_convergence']['q1_moisture_max_abs_321_vs_641']:.2e}}}
\newcommand{{\QTwoMoistureProfileError}}{{{validation['profile_convergence']['q2_moisture_max_abs_321_vs_641']:.2e}}}
""".strip()
    (REPORT_DIR / "generated_results.tex").write_text(macros + "\n", encoding="utf-8")

    tables = summary["tables"]
    fragments = [
        small_table(r"问题1：30 min 内药材温度（$^\circ$C）", "tab:q1t", "时间/s", tables["q1_temperature_c"]),
        small_table("问题1：30 min 内水分浓度（kg/kg）", "tab:q1c", "时间/s", tables["q1_moisture"]),
        small_table(r"问题2：3 h 内药材温度（$^\circ$C）", "tab:q2t", "时间/h", tables["q2_temperature_c"]),
        small_table("问题2：3 h 内水分浓度（kg/kg）", "tab:q2c", "时间/h", tables["q2_moisture"]),
        long_q3_table(tables["q3_moisture"]),
        long_q4_table(tables["q4_moisture"]),
    ]
    (REPORT_DIR / "generated_tables.tex").write_text("\n\n".join(fragments) + "\n", encoding="utf-8")

    write_curve(REPORT_DIR / "q3_center.csv", tables["q3_moisture"])
    write_curve(REPORT_DIR / "q4_center.csv", tables["q4_moisture"])

    for key, file_name in [("q3_space", "q3_grid.csv"), ("q4_space", "q4_grid.csv")]:
        with (REPORT_DIR / file_name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["nodes", "dry_time_h"])
            for row in summary["convergence"][key]:
                writer.writerow([row["node_count"], row["dry_time_h"]])


if __name__ == "__main__":
    main()
