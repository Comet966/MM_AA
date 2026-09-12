"""关键传热传质参数的正负10%敏感性分析。"""

from __future__ import annotations

import json
from pathlib import Path

from . import drying_solver as solve


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "result" / "parameter_sensitivity.json"


def one_case(parameter: str, factor: float) -> dict[str, float]:
    original_h = solve.HEAT_TRANSFER
    original_hm = solve.MASS_TRANSFER
    original_d = solve.DIFFUSIVITY_SCALE
    try:
        if parameter == "heat_transfer_h":
            solve.HEAT_TRANSFER = original_h * factor
        elif parameter == "mass_transfer_hm":
            solve.MASS_TRANSFER = original_hm * factor
        elif parameter == "diffusivity_scale":
            solve.DIFFUSIVITY_SCALE = original_d * factor
        elif parameter != "baseline":
            raise ValueError(parameter)

        environment = solve.read_environment(solve.ATTACHMENT_DIR / "附件1.xlsx")
        radius = solve.read_radius(solve.ATTACHMENT_DIR / "附件2.xlsx")
        q3 = solve.solve_fixed(
            f"问题三-{parameter}-{factor}",
            solve.RADIUS_MAX_TIME_S,
            801,
            "appendix3",
            environment,
            True,
        )
        q4 = solve.solve_moving(
            f"问题四-{parameter}-{factor}",
            solve.RADIUS_MAX_TIME_S,
            601,
            environment,
            radius,
            True,
            True,
        )
        event3 = solve.event_time(q3)
        event4 = solve.event_time(q4)
        safe3, _ = solve.first_output_time_below(q3)
        safe4, _ = solve.first_output_time_below(q4)
        return {
            "question3_continuous_h": event3 / 3600.0,
            "question3_safe_60s_h": safe3 / 3600.0,
            "question4_continuous_h": event4 / 3600.0,
            "question4_safe_60s_h": safe4 / 3600.0,
        }
    finally:
        solve.HEAT_TRANSFER = original_h
        solve.MASS_TRANSFER = original_hm
        solve.DIFFUSIVITY_SCALE = original_d


def run_sensitivity(print_output: bool = True) -> dict:
    baseline = one_case("baseline", 1.0)
    cases: dict[str, dict[str, dict[str, float]]] = {}
    for parameter in ["heat_transfer_h", "mass_transfer_hm", "diffusivity_scale"]:
        cases[parameter] = {
            "minus_10_percent": one_case(parameter, 0.9),
            "plus_10_percent": one_case(parameter, 1.1),
        }

    for parameter, variants in cases.items():
        for variant, values in variants.items():
            for question in ["question3", "question4"]:
                base_h = baseline[f"{question}_continuous_h"]
                changed_h = values[f"{question}_continuous_h"]
                values[f"{question}_relative_change_percent"] = (
                    (changed_h - base_h) / base_h * 100.0
                )

    output = {
        "perturbation": "each parameter independently multiplied by 0.9 or 1.1",
        "baseline_parameters": {
            "heat_transfer_h_W_m2K": solve.HEAT_TRANSFER,
            "mass_transfer_hm_m_s": solve.MASS_TRANSFER,
            "diffusivity_scale": solve.DIFFUSIVITY_SCALE,
        },
        "baseline": baseline,
        "cases": cases,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    if print_output:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    return output


def main() -> None:
    run_sensitivity(print_output=True)


if __name__ == "__main__":
    main()
