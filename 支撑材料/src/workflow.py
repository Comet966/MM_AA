"""四问求解、结果汇总、Excel 输出与绘图总流程。"""

import json
import math

import numpy as np

from .config import (
    ATTACHMENT_DIR,
    FIXED_COMPARISON_MAX_TIME_S,
    INITIAL_RADIUS_M,
    PLATEAU_START_S,
    POST_DRY_S,
    RADIUS_MAX_TIME_S,
    RESULT_DIR,
    TEMPLATE_DIR,
)
from .data_io import read_environment, read_radius
from .excel_output import write_single_sheet_result, write_two_sheet_result
from .plotting import create_figures
from .sampling import (
    event_time,
    first_node_output_time_below,
    first_output_time_below,
    grid_difference,
    max_moisture,
    representative_table,
    sample_fixed,
    sample_moving_moisture,
)
from .solver import solve_fixed, solve_moving

def run_all(write_excel: bool = True) -> dict:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    environment = read_environment(ATTACHMENT_DIR / "附件1.xlsx")
    radius_history = read_radius(ATTACHMENT_DIR / "附件2.xlsx")

    print("[1/8] 求解问题一（161 节点）", flush=True)
    q1 = solve_fixed("问题一", 1800.0, 161, "appendix2", environment)
    print("[2/8] 求解问题二（201 节点）", flush=True)
    q2 = solve_fixed("问题二", 10800.0, 201, "appendix3", environment)
    print("[3/8] 求解问题三（801 节点，积分至 72 h）", flush=True)
    q3 = solve_fixed("问题三", RADIUS_MAX_TIME_S, 801, "appendix3", environment, True)
    dry3_s = event_time(q3)
    safe3_s, safe3_c = first_output_time_below(q3)
    visible3_s, visible3_c = first_output_time_below(q3, require_displayed_below=True)
    print(
        f"      问题三连续临界：{dry3_s / 3600:.6f} h；"
        f"60 s网格首个严格达标：{safe3_s:.0f} s",
        flush=True,
    )
    print("[4/8] 求解问题四（601 节点，含几何项）", flush=True)
    q4 = solve_moving("问题四", RADIUS_MAX_TIME_S, 601, environment, radius_history, True, True)
    dry4_s = event_time(q4)
    safe4_s, safe4_c = first_output_time_below(q4)
    visible4_s, visible4_c = first_output_time_below(q4, require_displayed_below=True)
    print(
        f"      问题四连续临界：{dry4_s / 3600:.6f} h；"
        f"60 s网格首个严格达标：{safe4_s:.0f} s",
        flush=True,
    )

    print("[5/8] 求解网格与模型敏感性对照", flush=True)
    q1_coarse = solve_fixed("问题一粗网格", 1800.0, 81, "appendix2", environment)
    q1_fine = solve_fixed("问题一细网格", 1800.0, 321, "appendix2", environment)
    q2_coarse = solve_fixed("问题二粗网格", 10800.0, 101, "appendix3", environment)
    q2_fine = solve_fixed("问题二细网格", 10800.0, 401, "appendix3", environment)
    q3_coarse = solve_fixed("问题三粗网格", RADIUS_MAX_TIME_S, 401, "appendix3", environment, True)
    q3_fine = solve_fixed("问题三细网格", RADIUS_MAX_TIME_S, 1201, "appendix3", environment, True)
    q4_coarse = solve_moving("问题四粗网格", RADIUS_MAX_TIME_S, 321, environment, radius_history, True, True)
    q4_fine = solve_moving("问题四细网格", RADIUS_MAX_TIME_S, 801, environment, radius_history, True, True)
    q4_no_geometry = solve_moving("问题四无几何项", RADIUS_MAX_TIME_S, 601, environment, radius_history, False, True)
    appendix4_fixed = solve_fixed("附录4固定半径", FIXED_COMPARISON_MAX_TIME_S, 801, "appendix4", environment, True)
    dry3_coarse_s = event_time(q3_coarse)
    dry3_fine_s = event_time(q3_fine)
    dry4_coarse_s = event_time(q4_coarse)
    dry4_fine_s = event_time(q4_fine)
    dry4_no_geometry_s = event_time(q4_no_geometry)
    dry_appendix4_fixed_s = event_time(appendix4_fixed)
    safe_appendix4_fixed_s, safe_appendix4_fixed_c = first_output_time_below(appendix4_fixed)
    q3_surface_safe_s, q3_surface_safe_c = first_node_output_time_below(q3, -1)
    q4_radius_at_safe_m, _ = radius_history.value_and_rate(safe4_s)

    output_r_cm = np.round(np.arange(0.0, 2.0 + 0.05, 0.1), 1)
    output_r_m = output_r_cm / 100.0
    if write_excel:
        print("[6/8] 填写四个 Excel 结果模板", flush=True)
        q1_times = np.arange(1.0, 1800.0 + 1.0, 1.0)
        q1_t, q1_c = sample_fixed(q1, q1_times, output_r_m)
        write_two_sheet_result(TEMPLATE_DIR / "result1.xlsx", q1_times, output_r_cm, q1_t, q1_c)

        q2_times = np.arange(1.0, 10800.0 + 1.0, 1.0)
        q2_t, q2_c = sample_fixed(q2, q2_times, output_r_m)
        write_two_sheet_result(TEMPLATE_DIR / "result2.xlsx", q2_times, output_r_cm, q2_t, q2_c)

        q3_end_s = min(RADIUS_MAX_TIME_S, safe3_s + POST_DRY_S)
        q3_times = np.arange(60.0, q3_end_s + 0.1, 60.0)
        _, q3_c = sample_fixed(q3, q3_times, output_r_m)
        write_single_sheet_result(
            TEMPLATE_DIR / "result3.xlsx", q3_times, output_r_cm.tolist(), q3_c
        )

        q4_end_s = min(RADIUS_MAX_TIME_S, safe4_s + POST_DRY_S)
        q4_times = np.arange(60.0, q4_end_s + 0.1, 60.0)
        q4_c, _ = sample_moving_moisture(q4, radius_history, q4_times, output_r_m)
        q4_surface = q4.fields(q4_times)[1][-1, :]
        q4_values = np.column_stack((q4_c, q4_surface))
        q4_headers: list[float | str] = output_r_cm.tolist() + ["药材表面"]
        write_single_sheet_result(
            TEMPLATE_DIR / "result4.xlsx", q4_times, q4_headers, q4_values
        )

    print("[7/8] 汇总代表点、误差与可行性检查", flush=True)
    q1_paper_times = np.asarray([100, 300, 600, 900, 1200, 1500, 1800], dtype=float)
    paper_r_cm = np.asarray([0, 0.5, 1.0, 1.5, 2.0], dtype=float)
    q1_pt, q1_pc = sample_fixed(q1, q1_paper_times, paper_r_cm / 100.0)
    q2_paper = representative_table(q2, [0.5, 1, 1.5, 2, 2.5, 3], paper_r_cm.tolist())

    q3_paper_hours = np.append(
        np.arange(6.0, math.floor(safe3_s / 3600.0 / 6.0) * 6.0 + 0.1, 6.0),
        safe3_s / 3600.0,
    )
    _, q3_paper_c = sample_fixed(q3, q3_paper_hours * 3600.0, paper_r_cm / 100.0)
    q4_fixed_r_cm = np.asarray([0.0, 0.5, 1.0, 1.5], dtype=float)
    q4_paper_hours = np.append(
        np.arange(6.0, math.floor(safe4_s / 3600.0 / 6.0) * 6.0 + 0.1, 6.0),
        safe4_s / 3600.0,
    )
    q4_paper_c, q4_paper_radii = sample_moving_moisture(
        q4, radius_history, q4_paper_hours * 3600.0, q4_fixed_r_cm / 100.0
    )
    q4_paper_surface = q4.fields(q4_paper_hours * 3600.0)[1][-1, :]

    def nullable_rows(array: np.ndarray) -> list[list[float | None]]:
        return [
            [None if not np.isfinite(value) else round(float(value), 4) for value in row]
            for row in array
        ]

    validation_delta_s = 60.0
    dry3_before = max_moisture(q3, max(0.0, dry3_s - validation_delta_s))
    dry3_after = max_moisture(q3, min(RADIUS_MAX_TIME_S, dry3_s + POST_DRY_S))
    dry4_before = max_moisture(q4, max(0.0, dry4_s - validation_delta_s))
    dry4_after = max_moisture(q4, min(RADIUS_MAX_TIME_S, dry4_s + POST_DRY_S))
    safe3_previous = max_moisture(q3, safe3_s - 60.0)
    safe4_previous = max_moisture(q4, safe4_s - 60.0)

    comparison_times_h = {
        "附录3固定半径": dry3_s / 3600.0,
        "附录4固定半径": dry_appendix4_fixed_s / 3600.0,
        "附录4动态半径": dry4_s / 3600.0,
        "动态半径无几何项": dry4_no_geometry_s / 3600.0,
    }
    summary = {
        "environment": {
            "plateau_start_s": PLATEAU_START_S,
            "plateau_temperature_c": environment.plateau_temperature_k - 273.15,
            "plateau_moisture": environment.plateau_moisture,
        },
        "radius": {
            "initial_cm": radius_history.radius_m[0] * 100.0,
            "at_72h_cm": radius_history.radius_m[-1] * 100.0,
        },
        "drying_time": {
            "question3_continuous_threshold_s": dry3_s,
            "question3_continuous_threshold_h": dry3_s / 3600.0,
            "question3_safe_60s_output_s": safe3_s,
            "question3_safe_60s_output_h": safe3_s / 3600.0,
            "question3_first_displayed_below_s": visible3_s,
            "question3_first_displayed_below_h": visible3_s / 3600.0,
            "question4_continuous_threshold_s": dry4_s,
            "question4_continuous_threshold_h": dry4_s / 3600.0,
            "question4_safe_60s_output_s": safe4_s,
            "question4_safe_60s_output_h": safe4_s / 3600.0,
            "question4_first_displayed_below_s": visible4_s,
            "question4_first_displayed_below_h": visible4_s / 3600.0,
            "appendix4_fixed_h": dry_appendix4_fixed_s / 3600.0,
            "question4_without_geometry_term_h": dry4_no_geometry_s / 3600.0,
        },
        "threshold_check": {
            "question3_safe_60s_output_raw_max": safe3_c,
            "question3_safe_60s_output_rounded_4dp": round(safe3_c, 4),
            "question3_previous_60s_output_raw_max": safe3_previous,
            "question3_first_displayed_below_raw_max": visible3_c,
            "question3_60s_before": dry3_before,
            "question3_30min_after": dry3_after,
            "question4_safe_60s_output_raw_max": safe4_c,
            "question4_safe_60s_output_rounded_4dp": round(safe4_c, 4),
            "question4_previous_60s_output_raw_max": safe4_previous,
            "question4_first_displayed_below_raw_max": visible4_c,
            "question4_60s_before": dry4_before,
            "question4_30min_after": dry4_after,
        },
        "abstract_metrics": {
            "question1_at_1800s": {
                "center_temperature_c": float(q1_pt[-1, 0]),
                "surface_temperature_c": float(q1_pt[-1, -1]),
                "center_moisture": float(q1_pc[-1, 0]),
                "surface_moisture": float(q1_pc[-1, -1]),
            },
            "question2_at_3h": {
                "center_temperature_c": float(q2_paper["temperature_c"][-1][0]),
                "surface_temperature_c": float(q2_paper["temperature_c"][-1][-1]),
                "center_moisture": float(q2_paper["moisture"][-1][0]),
                "surface_moisture": float(q2_paper["moisture"][-1][-1]),
            },
            "question3_surface_safe_60s_s": q3_surface_safe_s,
            "question3_surface_safe_60s_h": q3_surface_safe_s / 3600.0,
            "question3_surface_safe_raw_moisture": q3_surface_safe_c,
            "question3_center_to_surface_drying_time_ratio": safe3_s / q3_surface_safe_s,
            "question3_center_minus_surface_drying_time_h": (safe3_s - q3_surface_safe_s) / 3600.0,
            "question3_center_to_surface_moisture_ratio_at_finish": safe3_c / float(q3.fields(safe3_s)[1][-1]),
            "question4_radius_at_finish_cm": q4_radius_at_safe_m * 100.0,
            "appendix4_fixed_safe_60s_s": safe_appendix4_fixed_s,
            "appendix4_fixed_safe_60s_h": safe_appendix4_fixed_s / 3600.0,
            "appendix4_fixed_safe_raw_moisture": safe_appendix4_fixed_c,
            "question4_time_reduction_vs_fixed_h": (safe_appendix4_fixed_s - safe4_s) / 3600.0,
            "question4_time_reduction_vs_fixed_percent": (safe_appendix4_fixed_s - safe4_s) / safe_appendix4_fixed_s * 100.0,
            "question4_drying_speed_ratio_vs_fixed": safe_appendix4_fixed_s / safe4_s,
        },
        "grid_convergence": {
            "question1_max_temperature_difference_81_vs_321_at_1800s_K": grid_difference(q1_coarse, q1_fine, 1800.0, "temperature"),
            "question1_max_moisture_difference_81_vs_321_at_1800s": grid_difference(q1_coarse, q1_fine, 1800.0, "moisture"),
            "question1_max_temperature_difference_161_vs_321_at_1800s_K": grid_difference(q1, q1_fine, 1800.0, "temperature"),
            "question1_max_moisture_difference_161_vs_321_at_1800s": grid_difference(q1, q1_fine, 1800.0, "moisture"),
            "question2_max_temperature_difference_101_vs_401_at_3h_K": grid_difference(q2_coarse, q2_fine, 10800.0, "temperature"),
            "question2_max_moisture_difference_101_vs_401_at_3h": grid_difference(q2_coarse, q2_fine, 10800.0, "moisture"),
            "question2_max_temperature_difference_201_vs_401_at_3h_K": grid_difference(q2, q2_fine, 10800.0, "temperature"),
            "question2_max_moisture_difference_201_vs_401_at_3h": grid_difference(q2, q2_fine, 10800.0, "moisture"),
            "question3_dry_time_h_401_nodes": dry3_coarse_s / 3600.0,
            "question3_dry_time_h_801_nodes": dry3_s / 3600.0,
            "question3_dry_time_h_1201_nodes": dry3_fine_s / 3600.0,
            "question4_dry_time_h_321_nodes": dry4_coarse_s / 3600.0,
            "question4_dry_time_h_601_nodes": dry4_s / 3600.0,
            "question4_dry_time_h_801_nodes": dry4_fine_s / 3600.0,
        },
        "paper_tables": {
            "question1": {
                "times_s": q1_paper_times.astype(int).tolist(),
                "distances_cm": paper_r_cm.tolist(),
                "temperature_c": np.round(q1_pt, 4).tolist(),
                "moisture": np.round(q1_pc, 4).tolist(),
            },
            "question2": q2_paper,
            "question3": {
                "times_h": np.round(q3_paper_hours, 6).tolist(),
                "distances_cm": paper_r_cm.tolist(),
                "moisture": np.round(q3_paper_c, 4).tolist(),
            },
            "question4": {
                "times_h": np.round(q4_paper_hours, 6).tolist(),
                "fixed_distances_cm": q4_fixed_r_cm.tolist(),
                "radius_cm": np.round(q4_paper_radii * 100.0, 4).tolist(),
                "moisture_at_fixed_distances": nullable_rows(q4_paper_c),
                "surface_moisture": np.round(q4_paper_surface, 4).tolist(),
            },
        },
        "solver_stats": {
            sim.name: {"nfev": int(sim.solution.nfev), "njev": int(sim.solution.njev)}
            for sim in [q1, q2, q3, q4]
        },
    }
    (RESULT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("[8/8] 生成说明书图表", flush=True)
    create_figures(
        environment,
        radius_history,
        q1,
        q2,
        q3,
        q4,
        appendix4_fixed,
        dry3_s,
        dry4_s,
        safe3_s,
        safe4_s,
        comparison_times_h,
    )
    print("全部数值任务完成。", flush=True)
    return summary
