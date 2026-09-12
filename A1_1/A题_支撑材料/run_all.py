"""Run all four drying simulations and write intermediate CSV/JSON results."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from src.drying_solver import (
    Environment,
    Grid,
    RadiusModel,
    SimulationConfig,
    SimulationResult,
    sample_profiles,
    simulate,
)


ROOT = Path(__file__).resolve().parent
ATTACHMENT_DIR = ROOT / "A题" / "附件"
OUTPUT_DIR = ROOT / "outputs"
INTERMEDIATE_DIR = ROOT / "tmp" / "numerical"
MAX_SIMULATION_TIME_S = 15.0 * 86400.0


def write_csv(path: Path, headers: list[str], rows: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows.tolist())


def interpolate_time(result: SimulationResult, target_s: float, field: str) -> np.ndarray:
    values = getattr(result, field)
    if target_s <= result.time_s[0]:
        return values[0].copy()
    if target_s >= result.time_s[-1]:
        if result.dry_time_s is not None and np.isclose(target_s, result.dry_time_s):
            dry_field = result.dry_temperature_k if field == "temperature_k" else result.dry_moisture
            return dry_field.copy()
        return values[-1].copy()
    upper = int(np.searchsorted(result.time_s, target_s))
    lower = upper - 1
    fraction = (target_s - result.time_s[lower]) / (result.time_s[upper] - result.time_s[lower])
    return values[lower] + fraction * (values[upper] - values[lower])


def sample_at_positions(
    profile: np.ndarray, node_count: int, radius_m: float, positions_cm: np.ndarray
) -> list[float | None]:
    xi = Grid.uniform(node_count).xi
    positions_m = positions_cm / 100.0
    sampled: list[float | None] = []
    for position in positions_m:
        sampled.append(
            None if position > radius_m + 1.0e-12 else float(np.interp(position / radius_m, xi, profile))
        )
    return sampled


def save_required_csvs(
    q1: SimulationResult,
    q23_first: SimulationResult,
    q23_long: SimulationResult,
    q4: SimulationResult,
    fixed_node_count: int,
    moving_node_count: int,
) -> None:
    xi = Grid.uniform(moving_node_count).xi
    fixed_cm = np.round(np.arange(0.0, 2.0 + 0.05, 0.1), 1)

    q1_time_mask = q1.time_s >= 1.0
    q1_temp = np.column_stack(
        [q1.time_s[q1_time_mask], q1.temperature_k[q1_time_mask, :: fixed_node_count // 20] - 273.15]
    )
    q1_moisture = np.column_stack(
        [q1.time_s[q1_time_mask], q1.moisture[q1_time_mask, :: fixed_node_count // 20]]
    )
    write_csv(INTERMEDIATE_DIR / "result1_temperature.csv", ["时间\\到药材中心的距离", *map(str, fixed_cm)], q1_temp)
    write_csv(INTERMEDIATE_DIR / "result1_moisture.csv", ["时间\\到药材中心的距离", *map(str, fixed_cm)], q1_moisture)

    q2_time_mask = q23_first.time_s >= 1.0
    q2_temp = np.column_stack(
        [q23_first.time_s[q2_time_mask], q23_first.temperature_k[q2_time_mask, :: fixed_node_count // 20] - 273.15]
    )
    q2_moisture = np.column_stack(
        [q23_first.time_s[q2_time_mask], q23_first.moisture[q2_time_mask, :: fixed_node_count // 20]]
    )
    write_csv(INTERMEDIATE_DIR / "result2_temperature.csv", ["时间\\到药材中心的距离", *map(str, fixed_cm)], q2_temp)
    write_csv(INTERMEDIATE_DIR / "result2_moisture.csv", ["时间\\到药材中心的距离", *map(str, fixed_cm)], q2_moisture)

    q3_times = np.concatenate([q23_first.time_s, q23_long.time_s[1:]])
    q3_moisture_full = np.vstack([q23_first.moisture, q23_long.moisture[1:]])
    q3_mask = (q3_times >= 60.0) & np.isclose(np.mod(q3_times, 60.0), 0.0, atol=1.0e-8)
    q3_rows = np.column_stack([q3_times[q3_mask], q3_moisture_full[q3_mask, :: fixed_node_count // 20]])
    write_csv(INTERMEDIATE_DIR / "result3_moisture.csv", ["时间\\到药材中心的距离", *map(str, fixed_cm)], q3_rows)

    q4_mask = (q4.time_s >= 60.0) & np.isclose(np.mod(q4.time_s, 60.0), 0.0, atol=1.0e-8)
    q4_sampled, q4_headers = sample_profiles(
        SimulationResult(
            time_s=q4.time_s[q4_mask],
            temperature_k=q4.temperature_k[q4_mask],
            moisture=q4.moisture[q4_mask],
            radius_m=q4.radius_m[q4_mask],
        ),
        xi,
        fixed_cm,
        include_surface=True,
    )
    q4_rows = np.column_stack([q4.time_s[q4_mask], q4_sampled])
    write_csv(INTERMEDIATE_DIR / "result4_moisture.csv", ["时间\\到药材中心的距离", *q4_headers], q4_rows)


def table_data(
    result: SimulationResult,
    node_count: int,
    times_s: list[float],
    positions_cm: np.ndarray,
    field: str,
    moving: bool = False,
    surface: bool = False,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for time_s in times_s:
        profile = interpolate_time(result, time_s, field)
        radius_m = float(np.interp(time_s, result.time_s, result.radius_m))
        values = sample_at_positions(profile, node_count, radius_m, positions_cm)
        if field == "temperature_k":
            values = [None if value is None else value - 273.15 for value in values]
        row: dict[str, object] = {"time_s": time_s, "values": values}
        if moving:
            row["radius_cm"] = radius_m * 100.0
        if surface:
            row["surface"] = float(profile[-1])
        rows.append(row)
    return rows


def run_case(
    config: SimulationConfig,
    environment: Environment,
    end_time_s: float,
    dt_s: float,
    stop: bool,
) -> SimulationResult:
    return simulate(
        config,
        environment,
        0.0,
        end_time_s,
        dt_s,
        save_every_s=60.0 if dt_s <= 60.0 else dt_s,
        stop_moisture=0.15 if stop else None,
    )


def dry_time_convergence(
    environment: Environment,
    radius_model: RadiusModel,
    node_counts: list[int],
    dt_s: float,
    property_set: str,
    moving: bool,
    include_coordinate_term: bool = False,
) -> list[dict[str, float]]:
    results = []
    for node_count in node_counts:
        config = SimulationConfig(
            property_set=property_set,
            node_count=node_count,
            radius_model=radius_model if moving else None,
            include_coordinate_term=include_coordinate_term,
        )
        result = run_case(config, environment, MAX_SIMULATION_TIME_S, dt_s, stop=True)
        if result.dry_time_s is None:
            raise RuntimeError("Dryness event was not reached during convergence run")
        results.append(
            {
                "node_count": node_count,
                "spacing_initial_cm": 2.0 / (node_count - 1),
                "dt_s": dt_s,
                "dry_time_h": result.dry_time_s / 3600.0,
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-nodes", type=int, default=641)
    parser.add_argument("--moving-nodes", type=int, default=321)
    parser.add_argument("--long-dt", type=float, default=30.0)
    parser.add_argument("--skip-convergence", action="store_true")
    args = parser.parse_args()
    if (args.fixed_nodes - 1) % 20:
        raise ValueError("--fixed-nodes must equal 20*k+1 so 0.1 cm outputs align exactly")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    environment = Environment.from_attachment(ATTACHMENT_DIR / "附件1.xlsx")
    radius_model = RadiusModel.from_attachment(ATTACHMENT_DIR / "附件2.xlsx")

    q1_config = SimulationConfig(property_set="appendix2", node_count=args.fixed_nodes)
    q1 = simulate(q1_config, environment, 0.0, 1800.0, 1.0, save_every_s=1.0)

    q23_config = SimulationConfig(property_set="appendix3", node_count=args.fixed_nodes)
    q23_first = simulate(q23_config, environment, 0.0, 10800.0, 1.0, save_every_s=1.0)
    q23_long = simulate(
        q23_config,
        environment,
        10800.0,
        MAX_SIMULATION_TIME_S,
        args.long_dt,
        initial_temperature_k=q23_first.temperature_k[-1],
        initial_moisture=q23_first.moisture[-1],
        save_every_s=60.0,
        stop_moisture=0.15,
    )
    if q23_long.dry_time_s is None:
        raise RuntimeError("Question 3 did not reach the drying criterion")

    # The complete moving-boundary model is obtained by transforming the
    # Eulerian equations with xi=r/R(t).  The resulting geometric transport
    # term xi*Rdot/R*d(phi)/dxi is retained in the reported question-4 result.
    q4_config = SimulationConfig(
        property_set="appendix4",
        node_count=args.moving_nodes,
        radius_model=radius_model,
        include_coordinate_term=True,
    )
    q4 = simulate(
        q4_config,
        environment,
        0.0,
        MAX_SIMULATION_TIME_S,
        args.long_dt,
        save_every_s=60.0,
        stop_moisture=0.15,
    )
    if q4.dry_time_s is None:
        raise RuntimeError("Question 4 did not reach the drying criterion")

    fixed_appendix4_config = SimulationConfig(property_set="appendix4", node_count=args.moving_nodes)
    fixed_appendix4 = run_case(
        fixed_appendix4_config, environment, MAX_SIMULATION_TIME_S, args.long_dt, stop=True
    )
    if fixed_appendix4.dry_time_s is None:
        raise RuntimeError("Fixed-radius appendix 4 comparison did not reach criterion")

    no_coordinate_config = SimulationConfig(
        property_set="appendix4",
        node_count=args.moving_nodes,
        radius_model=radius_model,
        include_coordinate_term=False,
    )
    no_coordinate_case = run_case(
        no_coordinate_config, environment, MAX_SIMULATION_TIME_S, args.long_dt, stop=True
    )
    if no_coordinate_case.dry_time_s is None:
        raise RuntimeError("No-coordinate-term comparison did not reach criterion")

    save_required_csvs(
        q1, q23_first, q23_long, q4, args.fixed_nodes, args.moving_nodes
    )

    positions = np.asarray([0.0, 0.5, 1.0, 1.5, 2.0])
    q1_times = [100.0, 300.0, 600.0, 900.0, 1200.0, 1500.0, 1800.0]
    q2_times = [1800.0, 3600.0, 5400.0, 7200.0, 9000.0, 10800.0]
    q3_full = SimulationResult(
        time_s=np.concatenate([q23_first.time_s, q23_long.time_s[1:]]),
        temperature_k=np.vstack([q23_first.temperature_k, q23_long.temperature_k[1:]]),
        moisture=np.vstack([q23_first.moisture, q23_long.moisture[1:]]),
        radius_m=np.concatenate([q23_first.radius_m, q23_long.radius_m[1:]]),
        dry_time_s=q23_long.dry_time_s,
        dry_temperature_k=q23_long.dry_temperature_k,
        dry_moisture=q23_long.dry_moisture,
    )
    q3_table_times = list(np.arange(6.0 * 3600.0, q23_long.dry_time_s, 6.0 * 3600.0))
    q3_table_times.append(q23_long.dry_time_s)
    q4_table_times = list(np.arange(6.0 * 3600.0, q4.dry_time_s, 6.0 * 3600.0))
    q4_table_times.append(q4.dry_time_s)

    convergence: dict[str, object] = {}
    if not args.skip_convergence:
        convergence["q3_space"] = dry_time_convergence(
            environment, radius_model, [161, 321, 641, 1281], 60.0, "appendix3", False
        )
        convergence["q4_space"] = dry_time_convergence(
            environment,
            radius_model,
            [81, 161, 321, 641],
            60.0,
            "appendix4",
            True,
            include_coordinate_term=True,
        )
        convergence["q4_time"] = [
            dry_time_convergence(
                environment,
                radius_model,
                [args.moving_nodes],
                dt,
                "appendix4",
                True,
                include_coordinate_term=True,
            )[0]
            for dt in [60.0, 30.0, 15.0]
        ]

    summary = {
        "method": {
            "fixed_radius_node_count": args.fixed_nodes,
            "fixed_radius_spacing_cm": 2.0 / (args.fixed_nodes - 1),
            "moving_radius_node_count": args.moving_nodes,
            "moving_initial_spacing_cm": 2.0 / (args.moving_nodes - 1),
            "q1_q2_dt_s": 1.0,
            "q3_q4_dt_s": args.long_dt,
            "time_scheme": "backward Euler first step + BDF2",
            "nonlinearity": "Picard iteration",
            "q4_main_frame": "fixed xi coordinate with geometric transport term",
        },
        "environment": {
            "stable_start_s": environment.stable_start_s,
            "plateau_temperature_c": environment.plateau_temperature_k - 273.15,
            "plateau_moisture": environment.plateau_moisture,
            "data_end_s": float(environment.time_s[-1]),
        },
        "dry_times_h": {
            "question3_appendix3_fixed_radius": q23_long.dry_time_s / 3600.0,
            "appendix4_fixed_radius": fixed_appendix4.dry_time_s / 3600.0,
            "question4_appendix4_shrinking": q4.dry_time_s / 3600.0,
            "question4_without_coordinate_term_sensitivity": no_coordinate_case.dry_time_s / 3600.0,
        },
        "mechanism": {
            "shrinkage_time_reduction_percent_vs_appendix4_fixed": 100.0
            * (fixed_appendix4.dry_time_s - q4.dry_time_s)
            / fixed_appendix4.dry_time_s,
            "appendix_change_percent_vs_question3": 100.0
            * (fixed_appendix4.dry_time_s - q23_long.dry_time_s)
            / q23_long.dry_time_s,
            "omit_coordinate_term_difference_percent": 100.0
            * (no_coordinate_case.dry_time_s - q4.dry_time_s)
            / q4.dry_time_s,
        },
        "radius": {
            "initial_cm": float(radius_model.radius_m[0] * 100.0),
            "last_data_cm": float(radius_model.radius_m[-1] * 100.0),
            "last_data_time_h": float(radius_model.time_s[-1] / 3600.0),
            "q4_dry_cm": radius_model.value(q4.dry_time_s) * 100.0,
        },
        "tables": {
            "q1_temperature_c": table_data(q1, args.fixed_nodes, q1_times, positions, "temperature_k"),
            "q1_moisture": table_data(q1, args.fixed_nodes, q1_times, positions, "moisture"),
            "q2_temperature_c": table_data(q23_first, args.fixed_nodes, q2_times, positions, "temperature_k"),
            "q2_moisture": table_data(q23_first, args.fixed_nodes, q2_times, positions, "moisture"),
            "q3_moisture": table_data(q3_full, args.fixed_nodes, q3_table_times, positions, "moisture"),
            "q4_moisture": table_data(
                q4,
                args.moving_nodes,
                q4_table_times,
                positions,
                "moisture",
                moving=True,
                surface=True,
            ),
        },
        "checks": {
            "q1_temperature_bounds_c": [
                float(np.min(q1.temperature_k - 273.15)),
                float(np.max(q1.temperature_k - 273.15)),
            ],
            "q1_moisture_bounds": [float(np.min(q1.moisture)), float(np.max(q1.moisture))],
            "q3_minimum_moisture": float(np.min(q3_full.moisture)),
            "q4_minimum_moisture": float(np.min(q4.moisture)),
            "q3_max_location_at_dry_xi": float(
                Grid.uniform(args.fixed_nodes).xi[int(np.argmax(q23_long.dry_moisture))]
            ),
            "q4_max_location_at_dry_xi": float(
                Grid.uniform(args.moving_nodes).xi[int(np.argmax(q4.dry_moisture))]
            ),
            "maximum_picard_iterations": max(
                q1.max_picard_iterations,
                q23_first.max_picard_iterations,
                q23_long.max_picard_iterations,
                q4.max_picard_iterations,
            ),
        },
        "convergence": convergence,
    }
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary["dry_times_h"], ensure_ascii=False, indent=2))
    print(json.dumps(summary["mechanism"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
