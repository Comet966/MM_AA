"""生成论文所需的数值结果图。"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from .config import FIGURE_DIR, INITIAL_RADIUS_M, POST_DRY_S, RADIUS_MAX_TIME_S
from .models import Environment, RadiusHistory, Simulation
from .sampling import event_time, max_moisture, sample_fixed

TEMPERATURE_CMAP = LinearSegmentedColormap.from_list(
    "temperature_blue_yellow_red",
    ["#2166ac", "#67a9cf", "#ffffbf", "#fdae61", "#f46d43", "#b2182b"],
)
MOISTURE_CMAP = plt.get_cmap("viridis_r")

def create_figures(
    environment: Environment,
    radius_history: RadiusHistory,
    q1: Simulation,
    q2: Simulation,
    q3: Simulation,
    q4: Simulation,
    appendix4_fixed: Simulation,
    dry3_s: float,
    dry4_s: float,
    safe3_s: float,
    safe4_s: float,
    comparison_times_h: dict[str, float],
) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei"], "axes.unicode_minus": False})

    full_time = np.linspace(0.0, RADIUS_MAX_TIME_S, 721)
    full_env = np.asarray([environment(float(t)) for t in full_time])
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True)
    axes[0].plot(environment.time_s / 3600.0, environment.temperature_k - 273.15, ".", ms=2, label="附件1")
    axes[0].plot(full_time / 3600.0, full_env[:, 0] - 273.15, lw=1.3, label="插值/平台延拓")
    axes[0].set_ylabel("环境温度/°C")
    axes[0].legend()
    axes[1].plot(environment.time_s / 3600.0, environment.moisture, ".", ms=2)
    axes[1].plot(full_time / 3600.0, full_env[:, 1], lw=1.3)
    axes[1].set_xlabel("时间/h")
    axes[1].set_ylabel("环境水分浓度/(kg/kg)")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "environment_extension.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    for t_s in [100, 600, 1200, 1800]:
        tc, cc = sample_fixed(q1, np.asarray([t_s]), q1.grid)
        axes[0].plot(q1.grid * 100, tc[0], label=f"{t_s}s")
        axes[1].plot(q1.grid * 100, cc[0], label=f"{t_s}s")
    axes[0].set(xlabel="到中心距离/cm", ylabel="温度/°C")
    axes[1].set(xlabel="到中心距离/cm", ylabel="水分浓度/(kg/kg)")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "question1_profiles.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    for t_h in [0.5, 1.0, 2.0, 3.0]:
        tc, cc = sample_fixed(q2, np.asarray([t_h * 3600]), q2.grid)
        axes[0].plot(q2.grid * 100, tc[0], label=f"{t_h:g}h")
        axes[1].plot(q2.grid * 100, cc[0], label=f"{t_h:g}h")
    axes[0].set(xlabel="到中心距离/cm", ylabel="温度/°C")
    axes[1].set(xlabel="到中心距离/cm", ylabel="水分浓度/(kg/kg)")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "question2_profiles.png", dpi=180)
    plt.close(fig)

    def fixed_heatmaps(simulation: Simulation, end_s: float, filename: str, title: str) -> None:
        plot_times = np.linspace(0.0, end_s, 401)
        plot_r_m = np.linspace(0.0, INITIAL_RADIUS_M, 241)
        temperature_c, moisture = sample_fixed(simulation, plot_times, plot_r_m)
        time_scale = 3600.0 if end_s > 7200.0 else 60.0
        time_label = "时间/h" if time_scale == 3600.0 else "时间/min"
        fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.0), sharey=True)
        image_t = axes[0].pcolormesh(
            plot_r_m * 100.0, plot_times / time_scale, temperature_c,
            shading="auto", cmap=TEMPERATURE_CMAP
        )
        image_c = axes[1].pcolormesh(
            plot_r_m * 100.0, plot_times / time_scale, moisture,
            shading="auto", cmap=MOISTURE_CMAP
        )
        axes[0].set(xlabel="到中心距离/cm", ylabel=time_label, title="温度/°C")
        axes[1].set(xlabel="到中心距离/cm", title="水分浓度/(kg/kg)")
        fig.colorbar(image_t, ax=axes[0], pad=0.02)
        fig.colorbar(image_c, ax=axes[1], pad=0.02)
        fig.suptitle(title)
        fig.tight_layout()
        fig.savefig(FIGURE_DIR / filename, dpi=180)
        plt.close(fig)

    fixed_heatmaps(q1, 1800.0, "question1_heatmaps.png", "问题一完整时空演化")
    fixed_heatmaps(q2, 10800.0, "question2_heatmaps.png", "问题二完整时空演化")
    fixed_heatmaps(q3, safe3_s + POST_DRY_S, "question3_heatmaps.png", "问题三至达标后0.5 h的时空演化")

    q4_plot_times = np.linspace(0.0, safe4_s + POST_DRY_S, 401)
    q4_plot_r_m = np.linspace(0.0, INITIAL_RADIUS_M, 241)
    q4_temperature, q4_moisture = q4.fields(q4_plot_times)
    q4_t_map = np.full((q4_plot_times.size, q4_plot_r_m.size), np.nan)
    q4_c_map = np.full_like(q4_t_map, np.nan)
    for j, time_s in enumerate(q4_plot_times):
        radius, _ = radius_history.value_and_rate(float(time_s))
        valid = q4_plot_r_m <= radius + 1e-12
        xi_query = q4_plot_r_m[valid] / radius
        q4_t_map[j, valid] = np.interp(xi_query, q4.grid, q4_temperature[:, j]) - 273.15
        q4_c_map[j, valid] = np.interp(xi_query, q4.grid, q4_moisture[:, j])
    cmap_t = TEMPERATURE_CMAP.copy()
    cmap_c = MOISTURE_CMAP.copy()
    cmap_t.set_bad("white")
    cmap_c.set_bad("white")
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2), sharey=True, constrained_layout=True)
    image_t = axes[0].pcolormesh(
        q4_plot_r_m * 100.0, q4_plot_times / 3600.0, q4_t_map,
        shading="auto", cmap=cmap_t
    )
    image_c = axes[1].pcolormesh(
        q4_plot_r_m * 100.0, q4_plot_times / 3600.0, q4_c_map,
        shading="auto", cmap=cmap_c
    )
    radius_curve = np.asarray([radius_history.value_and_rate(float(t))[0] for t in q4_plot_times])
    for axis in axes:
        axis.plot(radius_curve * 100.0, q4_plot_times / 3600.0, color="white", lw=1.2, ls="--")
        axis.set_xlabel("到中心距离/cm")
    axes[0].set(ylabel="时间/h", title="温度/°C")
    axes[1].set_title("水分浓度/(kg/kg)")
    fig.colorbar(image_t, ax=axes[0], pad=0.02)
    fig.colorbar(image_c, ax=axes[1], pad=0.02)
    fig.suptitle("问题四移动物理域时空演化（白色区域为药材外部）")
    fig.savefig(FIGURE_DIR / "question4_heatmaps.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    check_time3 = np.linspace(0.0, min(q3.solution.t[-1], dry3_s + POST_DRY_S), 800)
    check_time4 = np.linspace(0.0, min(q4.solution.t[-1], dry4_s + POST_DRY_S), 500)
    max3 = np.max(q3.fields(check_time3)[1], axis=0)
    max4 = np.max(q4.fields(check_time4)[1], axis=0)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(check_time3 / 3600.0, max3, label="问题3：固定半径/附录3")
    ax.plot(check_time4 / 3600.0, max4, label="问题4：动态半径/附录4")
    ax.axhline(0.15, color="black", ls="--", lw=1, label="阈值0.15")
    safe_values = [max_moisture(q3, safe3_s), max_moisture(q4, safe4_s)]
    ax.scatter([safe3_s / 3600, safe4_s / 3600], safe_values, s=24, label="60 s网格首个严格达标点")
    ax.set(xlabel="时间/h", ylabel="全域最大水分浓度/(kg/kg)")
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "drying_threshold.png", dpi=180)
    plt.close(fig)

    fixed_end_s = event_time(appendix4_fixed)
    fixed_times = np.linspace(0.0, min(appendix4_fixed.solution.t[-1], fixed_end_s + POST_DRY_S), 900)
    moving_times = np.linspace(0.0, min(q4.solution.t[-1], safe4_s + POST_DRY_S), 500)
    fixed_max = np.max(appendix4_fixed.fields(fixed_times)[1], axis=0)
    moving_max = np.max(q4.fields(moving_times)[1], axis=0)
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    ax.plot(fixed_times / 3600.0, fixed_max, lw=1.5, label="附录4物性：固定半径2 cm")
    ax.plot(moving_times / 3600.0, moving_max, lw=1.5, label="附录4物性：附件2动态半径")
    ax.axhline(0.15, color="black", ls="--", lw=1, label="阈值0.15")
    ax.scatter(
        [fixed_end_s / 3600.0, dry4_s / 3600.0], [0.15, 0.15],
        color=["#4C78A8", "#F58518"], zorder=3
    )
    ax.annotate(f"{fixed_end_s / 3600.0:.2f} h", (fixed_end_s / 3600.0, 0.15), xytext=(-38, 12), textcoords="offset points")
    ax.annotate(f"{dry4_s / 3600.0:.2f} h", (dry4_s / 3600.0, 0.15), xytext=(6, 12), textcoords="offset points")
    ax.set(xlabel="时间/h", ylabel="全域最大水分浓度/(kg/kg)", ylim=(0, None))
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "shrinkage_effect.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    axes[0].plot(radius_history.time_s / 3600.0, radius_history.radius_m * 100.0)
    axes[0].set(xlabel="时间/h", ylabel="半径/cm")
    names = list(comparison_times_h)
    vals = [comparison_times_h[name] for name in names]
    axes[1].bar(range(len(vals)), vals, color=["#4C78A8", "#F58518", "#54A24B", "#B279A2"][: len(vals)])
    axes[1].set_xticks(range(len(vals)), names, rotation=18, ha="right", fontsize=8)
    axes[1].set_ylabel("烘干达标时间/h")
    for idx, value in enumerate(vals):
        axes[1].text(idx, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "radius_and_comparison.png", dpi=180)
    plt.close(fig)

