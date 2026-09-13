"""仅重绘论文实际使用的10张高质量科学图。"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import colors as mpl_colors
import numpy as np
BLUE = '#0072B2'
ORANGE = '#E69F00'
GREEN = '#009E73'
VERMILION = '#D55E00'
PURPLE = '#CC79A7'
SKY = '#56B4E9'
GRAY = '#6B7280'
BLACK = '#1F2937'
LIGHT_GRID = '#D9DEE7'

def configure_style() -> None:
    plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['PingFang SC', 'STHeiti', 'Songti SC', 'Microsoft YaHei', 'Noto Sans CJK SC', 'SimHei', 'Arial Unicode MS', 'Arial', 'DejaVu Sans'], 'font.size': 8.2, 'axes.titlesize': 9.5, 'axes.labelsize': 8.8, 'axes.linewidth': 0.8, 'axes.edgecolor': BLACK, 'axes.labelcolor': BLACK, 'axes.unicode_minus': False, 'xtick.labelsize': 7.7, 'ytick.labelsize': 7.7, 'xtick.color': BLACK, 'ytick.color': BLACK, 'xtick.major.width': 0.8, 'ytick.major.width': 0.8, 'xtick.major.size': 3.2, 'ytick.major.size': 3.2, 'legend.fontsize': 7.5, 'legend.frameon': False, 'lines.linewidth': 1.35, 'savefig.facecolor': 'white', 'figure.facecolor': 'white', 'svg.fonttype': 'path', 'pdf.fonttype': 42, 'ps.fonttype': 42})

def clean_axis(ax: plt.Axes, grid: bool=True) -> None:
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_axisbelow(True)
    if grid:
        ax.grid(axis='y', color=LIGHT_GRID, lw=0.55, alpha=0.75)

def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.12, 1.04, label, transform=ax.transAxes, fontsize=10.5, fontweight='bold', va='bottom', ha='left', color=BLACK)

def save_figure(fig: plt.Figure, output: Path, name: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    fig.savefig(output / f'{name}.png', dpi=600, bbox_inches='tight', pad_inches=0.035, metadata={'Software': 'Matplotlib; rebuilt from MM_AA repository data'})
    fig.savefig(output / f'{name}.svg', bbox_inches='tight', pad_inches=0.035, metadata={'Creator': 'Matplotlib; rebuilt from MM_AA repository data'})
    fig.savefig(output / f'{name}.pdf', bbox_inches='tight', pad_inches=0.035, metadata={'Creator': 'Matplotlib; rebuilt from MM_AA repository data'})
    plt.close(fig)

def label_colorbar_top(cb, label: str) -> None:
    """Use a compact horizontal title so a colorbar is not mistaken for an axis."""
    if cb.solids is not None:
        cb.solids.set_rasterized(False)
    cb.ax.set_title('')
    cb.ax.text(0.0, 1.025, label, transform=cb.ax.transAxes, fontsize=7.6, ha='left', va='bottom', clip_on=False)
    cb.ax.tick_params(labelsize=7.2, width=0.7, length=2.5)

def vector_field(ax, x, y, z, *, cmap, vmin: float, vmax: float):
    """Draw a fully vector field without visible seams in common PDF viewers.

    The 256 display bands are fine enough for publication-scale figures.  The
    source samples are neither smoothed nor altered; this is display
    quantisation only.  Painting contour edges with their face colour avoids
    hairline gaps caused by PDF antialiasing between adjacent vector polygons.
    """
    field = ax.contourf(x, y, np.ma.masked_invalid(z), levels=np.linspace(vmin, vmax, 257), cmap=cmap, antialiased=False)
    field.set_edgecolor('face')
    field.set_linewidth(0.5)
    return field

def temperature_cmap():
    """Return a smooth reversed plasma map ending exactly at #5202a3."""
    base = plt.get_cmap('plasma_r')
    rgba = base(np.linspace(0.0, 1.0, 256))
    target = np.array(mpl_colors.to_rgb('#5202a3'))
    start = 232
    anchor = rgba[start, :3].copy()
    for i in range(start, 256):
        alpha = (i - start) / (255 - start)
        rgba[i, :3] = (1.0 - alpha) * anchor + alpha * target
    rgba[-1, :3] = target
    return mpl_colors.ListedColormap(rgba, name='temperature_5202a3')

def load_source(repo: Path):
    support = repo / '支撑材料'
    if not support.is_dir():
        support = repo
    sys.path.insert(0, str(support))
    from src import drying_solver as ds
    env = ds.read_environment(support / 'data' / '附件1.xlsx')
    radius = ds.read_radius(support / 'data' / '附件2.xlsx')
    summary = json.loads((support / 'result' / 'summary.json').read_text(encoding='utf-8'))
    return (ds, env, radius, summary)

def solve_models(ds, env, radius):
    print('[1/5] 问题1', flush=True)
    q1 = ds.solve_fixed('问题1', 1800.0, 161, 'appendix2', env)
    print('[2/5] 问题2', flush=True)
    q2 = ds.solve_fixed('问题2', 10800.0, 201, 'appendix3', env)
    print('[3/5] 问题3', flush=True)
    q3 = ds.solve_fixed('问题3', ds.RADIUS_MAX_TIME_S, 801, 'appendix3', env, True)
    print('[4/5] 问题4', flush=True)
    q4 = ds.solve_moving('问题4', ds.RADIUS_MAX_TIME_S, 601, env, radius, True, True)
    print('[5/5] 附录4物性固定半径对照', flush=True)
    app4_fixed = ds.solve_fixed('附录4物性固定半径', ds.FIXED_COMPARISON_MAX_TIME_S, 801, 'appendix4', env, True)
    return (q1, q2, q3, q4, app4_fixed)

def time_colors(n: int) -> list:
    return [plt.get_cmap('viridis')(x) for x in np.linspace(0.12, 0.86, n)]

def plot_profile_pair(ds, sim, times_s, labels, name: str, output: Path) -> None:
    colors_ = time_colors(len(times_s))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.05), gridspec_kw={'wspace': 0.28})
    for t, label, color in zip(times_s, labels, colors_):
        temperature, moisture = ds.sample_fixed(sim, np.asarray([t], dtype=float), sim.grid)
        axes[0].plot(sim.grid * 100, temperature[0], color=color, label=label)
        axes[1].plot(sim.grid * 100, moisture[0], color=color, label=label)
    for idx, (ax, title, ylabel) in enumerate(zip(axes, ['温度剖面', '水分浓度剖面'], ['温度 (°C)', '水分浓度 (kg/kg)'])):
        ax.set(xlabel='距中心径向距离 (cm)', ylabel=ylabel, title=title)
        ax.set_xlim(0, 2)
        clean_axis(ax)
        panel_label(ax, chr(65 + idx))
    axes[1].legend(title='时刻', loc='best')
    save_figure(fig, output, name)

def heatmap_pair(ds, sim, end_s: float, name: str, output: Path, time_scale: float, time_label: str, shared_limits: tuple[tuple[float, float], tuple[float, float]] | None=None) -> None:
    plot_times = np.linspace(0, end_s, 181)
    plot_r = np.linspace(0, ds.INITIAL_RADIUS_M, 121)
    temp, moisture = ds.sample_fixed(sim, plot_times, plot_r)
    tlim = shared_limits[0] if shared_limits else (float(np.nanmin(temp)), float(np.nanmax(temp)))
    clim = shared_limits[1] if shared_limits else (float(np.nanmin(moisture)), float(np.nanmax(moisture)))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.25), sharey=True, gridspec_kw={'wspace': 0.22})
    images = [vector_field(axes[0], plot_r * 100, plot_times / time_scale, temp, cmap=temperature_cmap(), vmin=tlim[0], vmax=tlim[1]), vector_field(axes[1], plot_r * 100, plot_times / time_scale, moisture, cmap='viridis_r', vmin=clim[0], vmax=clim[1])]
    titles = ['温度场', '水分浓度场']
    labels = ['温度 (°C)', '水分浓度 (kg/kg)']
    for idx, (ax, im, title, cblabel) in enumerate(zip(axes, images, titles, labels)):
        ax.set(xlabel='距中心径向距离 (cm)', title=title)
        if idx == 0:
            ax.set_ylabel(time_label)
        panel_label(ax, chr(65 + idx))
        cb = fig.colorbar(im, ax=ax, pad=0.025, fraction=0.048)
        label_colorbar_top(cb, '°C' if idx == 0 else 'kg/kg')
    save_figure(fig, output, name)

def plot_q3_heatmaps(ds, q3, safe3: float, output: Path) -> None:
    times = np.linspace(0, safe3 + ds.POST_DRY_S, 181)
    radial = np.linspace(0, ds.INITIAL_RADIUS_M, 121)
    temperature, moisture = ds.sample_fixed(q3, times, radial)
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True, gridspec_kw={'wspace': 0.24})
    image_t = vector_field(axes[0], radial * 100, times / 3600, temperature, cmap=temperature_cmap(), vmin=28, vmax=50)
    image_c = vector_field(axes[1], radial * 100, times / 3600, moisture, cmap='viridis_r', vmin=0.05, vmax=2.55)
    for idx, (ax, title) in enumerate(zip(axes, ['温度场', '水分浓度场'])):
        ax.set_title(title)
        panel_label(ax, chr(65 + idx))
    axes[0].set(xlabel='径向距离 (cm)', ylabel='时间 (h)', xlim=(0, 2))
    axes[1].set(xlabel='径向距离 (cm)', xlim=(0, 2))
    cb = fig.colorbar(image_t, ax=axes[0], pad=0.025, fraction=0.05)
    label_colorbar_top(cb, '°C')
    cb = fig.colorbar(image_c, ax=axes[1], pad=0.025, fraction=0.05)
    label_colorbar_top(cb, 'kg/kg')
    save_figure(fig, output, 'question3_heatmaps')

def plot_q4_heatmaps(ds, q4, radius, safe4: float, output: Path) -> None:
    times = np.linspace(0, safe4 + ds.POST_DRY_S, 181)
    physical_r = np.linspace(0, ds.INITIAL_RADIUS_M, 121)
    temperature, moisture = q4.fields(times)
    tmap = np.full((times.size, physical_r.size), np.nan)
    mmap = np.full_like(tmap, np.nan)
    radius_curve = np.empty(times.size)
    for j, t in enumerate(times):
        radius_j, _ = radius.value_and_rate(float(t))
        radius_curve[j] = radius_j
        valid = physical_r <= radius_j + 1e-12
        xi = physical_r[valid] / radius_j
        tmap[j, valid] = np.interp(xi, q4.grid, temperature[:, j]) - 273.15
        mmap[j, valid] = np.interp(xi, q4.grid, moisture[:, j])
    temp_cmap = temperature_cmap()
    moist_cmap = plt.get_cmap('viridis_r').copy()
    temp_cmap.set_bad('white')
    moist_cmap.set_bad('white')
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True, gridspec_kw={'wspace': 0.24})
    image_t = vector_field(axes[0], physical_r * 100, times / 3600, tmap, cmap=temp_cmap, vmin=28, vmax=50)
    image_c = vector_field(axes[1], physical_r * 100, times / 3600, mmap, cmap=moist_cmap, vmin=0.05, vmax=2.55)
    for idx, (ax, title) in enumerate(zip(axes, ['温度场', '水分浓度场'])):
        ax.plot(radius_curve * 100, times / 3600, color=BLACK, lw=1.0, ls=(0, (4, 2)), label='药材表面')
        ax.set_title(title)
        if idx == 0:
            ax.set_ylabel('时间 (h)')
            ax.legend(loc='upper right')
        panel_label(ax, chr(65 + idx))
    axes[0].set(xlabel='径向距离 (cm)', xlim=(0, 2))
    axes[1].set(xlabel='径向距离 (cm)', xlim=(0, 2))
    cb = fig.colorbar(image_t, ax=axes[0], pad=0.025, fraction=0.05)
    label_colorbar_top(cb, '°C')
    cb = fig.colorbar(image_c, ax=axes[1], pad=0.025, fraction=0.05)
    label_colorbar_top(cb, 'kg/kg')
    save_figure(fig, output, 'question4_heatmaps')

def plot_drying_threshold(ds, q3, q4, summary, output: Path) -> None:
    safe3 = summary['drying_time']['question3_safe_60s_output_s']
    t3 = np.linspace(0, safe3 + ds.POST_DRY_S, 850)
    max3 = np.max(q3.fields(t3)[1], axis=0)
    y3 = summary['threshold_check']['question3_safe_60s_output_raw_max']
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    ax.plot(t3 / 3600, max3, color=BLUE, label='问题3：固定半径/附录3物性')
    ax.axhline(0.15, color=BLACK, lw=0.9, ls=(0, (3, 2)), label='严格判据：全域最大值 < 0.15')
    ax.scatter([safe3 / 3600], [y3], s=26, color=BLUE, edgecolor='white', lw=0.7, zorder=4)
    ax.set(xlabel='时间 (h)', ylabel='全域最大水分浓度 (kg/kg)', xlim=(0, 60), ylim=(0, 2.65))
    clean_axis(ax)
    ax.legend(loc='upper right')
    inset_specs = [(q3, safe3, y3, BLUE, f'问题3：达标点 {safe3 / 3600:.2f} h', [0.51, 0.27, 0.25, 0.27], (0.61, 0.59))]
    for sim, safe, threshold_y, color, title, bounds, arrow_start in inset_specs:
        zoom = ax.inset_axes(bounds)
        local_t = np.linspace(safe - 120, safe + 120, 161)
        local_y = np.max(sim.fields(local_t)[1], axis=0)
        rel_min = (local_t - safe) / 60
        zoom.plot(rel_min, local_y, color=color, lw=1.0)
        values = [float(np.max(sim.fields(safe - 60)[1])), float(np.max(sim.fields(safe)[1]))]
        zoom.scatter([-1, 0], values, s=13, color=color, edgecolor='white', lw=0.5, zorder=3)
        zoom.axhline(0.15, color=BLACK, lw=0.7, ls=(0, (2, 2)))
        zoom.axvline(0, color=GRAY, lw=0.55, ls=(0, (2, 2)))
        pad = max((max(max(local_y), 0.15) - min(min(local_y), 0.15)) * 0.18, 2e-06)
        zoom.set(xlim=(-2, 2), ylim=(min(min(local_y), 0.15) - pad, max(max(local_y), 0.15) + pad))
        zoom.set_title(title, fontsize=6.8, pad=2)
        zoom.set_xlabel('相对达标点 (min)', fontsize=6.1, labelpad=1)
        zoom.tick_params(labelsize=5.8, width=0.55, length=1.8)
        zoom.ticklabel_format(axis='y', style='plain', useOffset=False)
        zoom.spines['top'].set_visible(False)
        zoom.spines['right'].set_visible(False)
        inset_center_x = bounds[0] + bounds[2] / 2
        ax.annotate('', xy=(inset_center_x, bounds[1] - 0.14), xycoords='axes fraction', xytext=(safe / 3600, threshold_y), textcoords='data', arrowprops=dict(arrowstyle='-|>', color=color, lw=0.9, mutation_scale=9, shrinkA=1, shrinkB=1, connectionstyle='arc3,rad=0'), zorder=8)
    save_figure(fig, output, 'drying_threshold')

def plot_grid_convergence(summary, output: Path) -> None:
    grid = summary['grid_convergence']
    series = [([401, 801, 1201], [grid['question3_dry_time_h_401_nodes'], grid['question3_dry_time_h_801_nodes'], grid['question3_dry_time_h_1201_nodes']], '问题3', BLUE), ([321, 601, 801], [grid['question4_dry_time_h_321_nodes'], grid['question4_dry_time_h_601_nodes'], grid['question4_dry_time_h_801_nodes']], '问题4', ORANGE)]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.95), gridspec_kw={'wspace': 0.3})
    for idx, (nodes, values, title, color) in enumerate(series):
        ax = axes[idx]
        ax.plot(nodes, values, color=color, lw=0.75, ls=(0, (3, 2)), alpha=0.65, zorder=1, label='视觉引导线')
        ax.scatter(nodes, values, s=26, facecolor='white', edgecolor=color, linewidth=1.0, zorder=2, label='计算结果')
        ax.axhline(values[-1], color=GRAY, lw=0.65, ls=(0, (2, 2)), zorder=0, label='最细网格参考')
        for n, value in zip(nodes, values):
            ax.annotate(f'{value:.3f}', (n, value), xytext=(0, 7), textcoords='offset points', ha='center', color=color, fontsize=7.2)
        ax.set(xlabel='径向节点数', ylabel='连续达标时间 (h)', title=title)
        ax.set_xticks(nodes)
        clean_axis(ax)
        panel_label(ax, chr(65 + idx))
        relative = abs(values[0] - values[-1]) / values[-1] * 100
        ax.text(0.03, 0.04, f'纵轴局部放大；粗→细相对变化 {relative:.2f}%', transform=ax.transAxes, fontsize=6.5, color=GRAY, va='bottom')
    axes[0].legend(loc='center right', fontsize=6.5)
    save_figure(fig, output, 'grid_convergence')

def plot_shrinkage_effect(ds, q4, fixed, summary, output: Path) -> None:
    fixed_h = summary['drying_time']['appendix4_fixed_h']
    moving_h = summary['drying_time']['question4_continuous_threshold_h']
    tf = np.linspace(0, min(fixed.solution.t[-1], fixed_h * 3600 + ds.POST_DRY_S), 1000)
    tm = np.linspace(0, min(q4.solution.t[-1], moving_h * 3600 + ds.POST_DRY_S), 650)
    mf = np.max(fixed.fields(tf)[1], axis=0)
    mm = np.max(q4.fields(tm)[1], axis=0)
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    ax.plot(tf / 3600, mf, color=BLUE, label='附录4物性：固定半径 2 cm')
    ax.plot(tm / 3600, mm, color=ORANGE, label='附录4物性：动态半径')
    ax.axhline(0.15, color=BLACK, lw=0.9, ls=(0, (3, 2)), label='干燥判据 0.15')
    ax.scatter([fixed_h, moving_h], [0.15, 0.15], s=28, color=[BLUE, ORANGE], edgecolor='white', lw=0.7, zorder=4)
    ax.annotate(f'{fixed_h:.2f} h', (fixed_h, 0.15), xytext=(-38, 16), textcoords='offset points', color=BLUE)
    ax.annotate(f'{moving_h:.2f} h', (moving_h, 0.15), xytext=(5, 16), textcoords='offset points', color=ORANGE)
    ax.text(91, 0.42, '缩短 77.30 h（59.45%）', color=BLACK, ha='center', fontsize=8.0)
    ax.set(xlabel='时间 (h)', ylabel='全域最大水分浓度 (kg/kg)', xlim=(0, 137), ylim=(0, 2.65))
    clean_axis(ax)
    ax.legend(loc='upper right')
    save_figure(fig, output, 'shrinkage_effect')

def plot_radius_comparison(radius, summary, output: Path) -> None:
    names = ['附录3\n固定半径', '附录4\n固定半径', '附录4\n动态半径']
    values = [summary['drying_time']['question3_continuous_threshold_h'], summary['drying_time']['appendix4_fixed_h'], summary['drying_time']['question4_continuous_threshold_h']]
    fig = plt.figure(figsize=(7.0, 3.35))
    grid = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.18], wspace=0.42)
    ax = fig.add_subplot(grid[:, 0])
    ax.plot(radius.time_s / 3600, radius.radius_m * 100, color=GREEN, marker='o', markevery=5, ms=2.4, mfc='white', mew=0.6)
    ax.set(xlabel='时间 (h)', ylabel='药材半径 (cm)', title='附件2半径实测变化')
    ax.set_ylim(1.15, 2.04)
    clean_axis(ax)
    panel_label(ax, 'A')
    ax = fig.add_subplot(grid[0, 1])
    y = np.arange(len(names))
    bar_colors = [BLUE, PURPLE, ORANGE]
    bars = ax.barh(y, values, color=bar_colors, height=0.62)
    ax.set_yticks(y, names)
    ax.invert_yaxis()
    ax.set(xlabel='连续达标时间 (h)', title='全部模型', xlim=(0, 142))
    clean_axis(ax, grid=False)
    ax.grid(axis='x', color=LIGHT_GRID, lw=0.55, alpha=0.75)
    for bar, value in zip(bars, values):
        ax.text(value + 2.0, bar.get_y() + bar.get_height() / 2, f'{value:.2f}', va='center', fontsize=7.5)
    panel_label(ax, 'B')
    save_figure(fig, output, 'radius_and_comparison')

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="支撑材料根目录")
    parser.add_argument("--output", type=Path, required=True, help="论文图片输出目录")
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.output.resolve()
    configure_style()
    ds, env, radius, summary = load_source(repo)
    q1, q2, q3, q4, app4_fixed = solve_models(ds, env, radius)

    safe3 = summary["drying_time"]["question3_safe_60s_output_s"]
    safe4 = summary["drying_time"]["question4_safe_60s_output_s"]
    print("绘制论文实际使用的 10 张图……", flush=True)
    plot_profile_pair(ds, q1, [100, 600, 1200, 1800], ["100 s", "600 s", "1200 s", "1800 s"], "question1_profiles", output)
    heatmap_pair(ds, q1, 1800, "question1_heatmaps", output, 60, "时间 (min)")
    plot_profile_pair(ds, q2, [1800, 3600, 7200, 10800], ["0.5 h", "1 h", "2 h", "3 h"], "question2_profiles", output)
    heatmap_pair(ds, q2, 10800, "question2_heatmaps", output, 3600, "时间 (h)")
    plot_drying_threshold(ds, q3, q4, summary, output)
    plot_q3_heatmaps(ds, q3, safe3, output)
    plot_q4_heatmaps(ds, q4, radius, safe4, output)
    plot_grid_convergence(summary, output)
    plot_shrinkage_effect(ds, q4, app4_fixed, summary, output)
    plot_radius_comparison(radius, summary, output)

    manifest = {
        "source_data": ["data/附件1.xlsx", "data/附件2.xlsx", "result/summary.json"],
        "solver": "src/drying_solver.py",
        "figure_builder": "rebuild_figures.py",
        "raster_dpi": 600,
        "figures": [p.name for p in sorted(output.glob("*.png"))],
        "notes": (
            "仅生成论文实际引用的10张图。温度场采用低温浅、高温深的连续色标，"
            "最高温端为#5202a3；水分浓度场采用低值浅、高值深的连续色标。"
            "drying_threshold仅保留问题3，radius_and_comparison采用三模型方案。"
        ),
    }
    (output / "data_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"完成：{output}", flush=True)


if __name__ == "__main__":
    main()

