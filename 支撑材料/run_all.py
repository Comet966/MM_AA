"""一键复现 A 题四问结果、图表与敏感性分析。"""

from __future__ import annotations

import argparse

from src import drying_solver, sensitivity_analysis
import validate_results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-sensitivity",
        action="store_true",
        help="跳过参数敏感性分析，仅复现四问结果与图表",
    )
    args = parser.parse_args()

    print("=== A 题支撑材料复现开始 ===", flush=True)
    drying_solver.run_all(write_excel=True)
    if not args.skip_sensitivity:
        print("=== 参数敏感性分析 ===", flush=True)
        sensitivity_analysis.run_sensitivity(print_output=False)
    else:
        print("=== 已按参数跳过敏感性分析 ===", flush=True)
    print("=== 结果完整性校验 ===", flush=True)
    validate_results.main(require_sensitivity=not args.skip_sensitivity)
    print("=== 复现完成 ===", flush=True)


if __name__ == "__main__":
    main()
