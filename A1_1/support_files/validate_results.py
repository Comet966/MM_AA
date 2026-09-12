"""Independent numerical checks for the finite-volume drying solver."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from run_all import ATTACHMENT_DIR, OUTPUT_DIR, interpolate_time, sample_at_positions
from src.drying_solver import Environment, Grid, SimulationConfig, simulate


def main() -> None:
    summary = json.loads((OUTPUT_DIR / "summary.json").read_text(encoding="utf-8"))
    environment = Environment.from_attachment(ATTACHMENT_DIR / "附件1.xlsx")
    positions = np.asarray([0.0, 0.5, 1.0, 1.5, 2.0])

    q1_coarse = simulate(
        SimulationConfig(property_set="appendix2", node_count=321),
        environment,
        0.0,
        1800.0,
        1.0,
        save_every_s=1.0,
    )
    q2_coarse = simulate(
        SimulationConfig(property_set="appendix3", node_count=321),
        environment,
        0.0,
        10800.0,
        1.0,
        save_every_s=1.0,
    )

    comparison: dict[str, float] = {}
    cases = [
        (
            "q1_temperature_c",
            q1_coarse,
            "temperature_k",
            [100.0, 300.0, 600.0, 900.0, 1200.0, 1500.0, 1800.0],
            273.15,
        ),
        (
            "q1_moisture",
            q1_coarse,
            "moisture",
            [100.0, 300.0, 600.0, 900.0, 1200.0, 1500.0, 1800.0],
            0.0,
        ),
        (
            "q2_temperature_c",
            q2_coarse,
            "temperature_k",
            [1800.0, 3600.0, 5400.0, 7200.0, 9000.0, 10800.0],
            273.15,
        ),
        (
            "q2_moisture",
            q2_coarse,
            "moisture",
            [1800.0, 3600.0, 5400.0, 7200.0, 9000.0, 10800.0],
            0.0,
        ),
    ]
    for key, coarse, field, times, offset in cases:
        fine_rows = summary["tables"][key]
        errors = []
        for fine_row, time_s in zip(fine_rows, times):
            coarse_profile = interpolate_time(coarse, time_s, field)
            coarse_values = np.asarray(
                sample_at_positions(coarse_profile, 321, 0.02, positions), dtype=float
            ) - offset
            fine_values = np.asarray(fine_row["values"], dtype=float)
            errors.extend(np.abs(coarse_values - fine_values))
        comparison[key + "_max_abs_321_vs_641"] = float(np.max(errors))

    constant_environment = Environment(
        time_s=np.asarray([0.0, 3600.0]),
        temperature_k=np.asarray([301.15, 301.15]),
        moisture=np.asarray([2.55, 2.55]),
        plateau_temperature_k=301.15,
        plateau_moisture=2.55,
        stable_start_s=0.0,
    )
    equilibrium = simulate(
        SimulationConfig(property_set="appendix2", node_count=81),
        constant_environment,
        0.0,
        600.0,
        10.0,
        save_every_s=600.0,
    )
    equilibrium_error = max(
        float(np.max(np.abs(equilibrium.temperature_k[-1] - 301.15))),
        float(np.max(np.abs(equilibrium.moisture[-1] - 2.55))),
    )

    grid = Grid.uniform(161)
    initial_moisture = 1.0 + 0.2 * (1.0 - grid.xi**2)
    closed = simulate(
        SimulationConfig(
            property_set="appendix2",
            node_count=161,
            heat_transfer_coefficient=0.0,
            mass_transfer_coefficient=0.0,
        ),
        constant_environment,
        0.0,
        3600.0,
        10.0,
        initial_moisture=initial_moisture,
        save_every_s=3600.0,
    )
    initial_inventory = float(np.dot(initial_moisture, grid.radial_volume))
    final_inventory = float(np.dot(closed.moisture[-1], grid.radial_volume))
    conservation_relative_error = abs(final_inventory - initial_inventory) / initial_inventory

    validation = {
        "profile_convergence": comparison,
        "uniform_equilibrium_max_abs_error": equilibrium_error,
        "closed_system_moisture_conservation_relative_error": conservation_relative_error,
        "q3_space_last_refinement_relative_change": abs(
            summary["convergence"]["q3_space"][-1]["dry_time_h"]
            - summary["convergence"]["q3_space"][-2]["dry_time_h"]
        )
        / summary["convergence"]["q3_space"][-1]["dry_time_h"],
        "q4_space_last_refinement_relative_change": abs(
            summary["convergence"]["q4_space"][-1]["dry_time_h"]
            - summary["convergence"]["q4_space"][-2]["dry_time_h"]
        )
        / summary["convergence"]["q4_space"][-1]["dry_time_h"],
        "q4_time_30_vs_15_relative_change": abs(
            summary["convergence"]["q4_time"][-1]["dry_time_h"]
            - summary["convergence"]["q4_time"][-2]["dry_time_h"]
        )
        / summary["convergence"]["q4_time"][-1]["dry_time_h"],
    }
    (OUTPUT_DIR / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

