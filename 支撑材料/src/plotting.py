"""生成论文采用的最新版高质量图表。

具体绘图实现集中在支撑材料根目录的 ``rebuild_figures.py``。本模块保留
``workflow.run_all`` 所需的 ``create_figures`` 接口，使一键复现流程与独立
绘图流程生成同一套图形。
"""

from __future__ import annotations

import importlib.util
import json
from types import SimpleNamespace

from .config import (
    FIGURE_DIR,
    INITIAL_RADIUS_M,
    PLATEAU_START_S,
    POST_DRY_S,
    PROJECT_ROOT,
    RADIUS_MAX_TIME_S,
)
from .sampling import sample_fixed


def _load_figure_builder():
    script_path = PROJECT_ROOT / "rebuild_figures.py"
    spec = importlib.util.spec_from_file_location("mm_aa_latest_figure_builder", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法载入最新版绘图脚本：{script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_figures(
    environment,
    radius_history,
    q1,
    q2,
    q3,
    q4,
    appendix4_fixed,
    dry3_s: float,
    dry4_s: float,
    safe3_s: float,
    safe4_s: float,
    comparison_times_h: dict[str, float],
) -> None:
    """使用工作流已求得的数值解生成论文最新版图形。"""

    del dry3_s, dry4_s, comparison_times_h
    builder = _load_figure_builder()
    builder.configure_style()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    summary_path = PROJECT_ROOT / "result" / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    plotting_api = SimpleNamespace(
        INITIAL_RADIUS_M=INITIAL_RADIUS_M,
        PLATEAU_START_S=PLATEAU_START_S,
        POST_DRY_S=POST_DRY_S,
        RADIUS_MAX_TIME_S=RADIUS_MAX_TIME_S,
        sample_fixed=sample_fixed,
    )

    builder.plot_drying_threshold(plotting_api, q3, q4, summary, FIGURE_DIR)
    builder.plot_grid_convergence(summary, FIGURE_DIR)
    builder.heatmap_pair(plotting_api, q1, 1800, "question1_heatmaps", FIGURE_DIR, 60, "时间 (min)")
    builder.plot_profile_pair(
        plotting_api,
        q1,
        [100, 600, 1200, 1800],
        ["100 s", "600 s", "1200 s", "1800 s"],
        "question1_profiles",
        FIGURE_DIR,
    )
    builder.heatmap_pair(plotting_api, q2, 10800, "question2_heatmaps", FIGURE_DIR, 3600, "时间 (h)")
    builder.plot_profile_pair(
        plotting_api,
        q2,
        [1800, 3600, 7200, 10800],
        ["0.5 h", "1 h", "2 h", "3 h"],
        "question2_profiles",
        FIGURE_DIR,
    )
    builder.plot_q3_heatmaps(plotting_api, q3, safe3_s, FIGURE_DIR)
    builder.plot_q4_heatmaps(plotting_api, q4, radius_history, safe4_s, FIGURE_DIR)
    builder.plot_radius_comparison(radius_history, summary, FIGURE_DIR)
    builder.plot_shrinkage_effect(plotting_api, q4, appendix4_fixed, summary, FIGURE_DIR)

    manifest = {
        "source_data": ["data/附件1.xlsx", "data/附件2.xlsx", "result/summary.json"],
        "solver": "src/drying_solver.py",
        "figure_builder": "rebuild_figures.py",
        "raster_dpi": 600,
        "figures": [
            "question1_profiles.png",
            "question1_heatmaps.png",
            "question2_profiles.png",
            "question2_heatmaps.png",
            "drying_threshold.png",
            "question3_heatmaps.png",
            "question4_heatmaps.png",
            "grid_convergence.png",
            "shrinkage_effect.png",
            "radius_and_comparison.png",
        ],
        "notes": (
            "论文图由支撑材料中的原始数据和数值解重新生成；温度场采用低温浅、"
            "高温深的连续色标，最高温端为 #5202a3；水分浓度场同样为低值浅、"
            "高值深。drying_threshold 仅保留问题3，radius_and_comparison 采用"
            "论文最终三模型方案。"
        ),
    }
    (FIGURE_DIR / "data_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
