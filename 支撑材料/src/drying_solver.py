r"""A题“药材的烘干问题”数值求解兼容入口。

核心实现已按用途拆分到 config、models、data_io、physics、solver、
sampling、excel_output、plotting 和 workflow 模块。建议从支撑材料
根目录运行 python run_all.py。
"""

from __future__ import annotations

import argparse

from .config import (
    ATTACHMENT_DIR,
    DATA_DIR,
    FIGURE_DIR,
    FIXED_COMPARISON_MAX_TIME_S,
    INITIAL_C,
    INITIAL_RADIUS_M,
    INITIAL_T_K,
    PLATEAU_START_S,
    POST_DRY_S,
    PROJECT_ROOT,
    RADIUS_MAX_TIME_S,
    RESULT_DIR,
    TEMPLATE_DIR,
)
from .data_io import read_environment, read_radius
from .models import Environment, RadiusHistory, Simulation
from .physics import material_properties
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
from .solver import (
    coupled_jacobian_sparsity,
    dry_event,
    make_fixed_rhs,
    make_moving_rhs,
    solve_fixed,
    solve_moving,
)
from .workflow import run_all


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="只计算和绘图，不改写附件3结果文件",
    )
    args = parser.parse_args()
    run_all(write_excel=not args.no_excel)


if __name__ == "__main__":
    main()
