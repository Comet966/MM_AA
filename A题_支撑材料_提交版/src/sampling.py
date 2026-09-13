"""数值解的阈值判定、空间采样与网格误差计算。"""

import numpy as np
from scipy.optimize import brentq

from .models import RadiusHistory, Simulation

def event_time(simulation: Simulation) -> float:
    event_arrays = simulation.solution.t_events
    if not event_arrays or len(event_arrays[0]) == 0:
        sample_t = np.linspace(0.0, simulation.solution.t[-1], 2001)
        _, sample_c = simulation.fields(sample_t)
        residual = np.max(sample_c, axis=0) - 0.15
        crossed = np.where((residual[:-1] >= 0.0) & (residual[1:] < 0.0))[0]
        if crossed.size == 0:
            end_h = simulation.solution.t[-1] / 3600.0
            raise RuntimeError(f"{simulation.name} 在 {end_h:g} h 内未达到全域 C<0.15")
        idx = int(crossed[0])

        def scalar_residual(t: float) -> float:
            return float(np.max(simulation.fields(t)[1]) - 0.15)

        return float(brentq(scalar_residual, sample_t[idx], sample_t[idx + 1]))
    return float(event_arrays[0][0])


def sample_fixed(
    simulation: Simulation, times_s: np.ndarray, output_r_m: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    temperature, moisture = simulation.fields(times_s)
    sampled_t = np.vstack(
        [np.interp(output_r_m, simulation.grid, temperature[:, j]) for j in range(times_s.size)]
    )
    sampled_c = np.vstack(
        [np.interp(output_r_m, simulation.grid, moisture[:, j]) for j in range(times_s.size)]
    )
    return sampled_t - 273.15, sampled_c


def sample_moving_moisture(
    simulation: Simulation,
    radius_history: RadiusHistory,
    times_s: np.ndarray,
    output_r_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    _, moisture = simulation.fields(times_s)
    sampled = np.full((times_s.size, output_r_m.size), np.nan, dtype=float)
    radii = np.empty(times_s.size, dtype=float)
    for j, time_s in enumerate(times_s):
        radius, _ = radius_history.value_and_rate(float(time_s))
        radii[j] = radius
        valid = output_r_m <= radius + 1e-12
        sampled[j, valid] = np.interp(
            output_r_m[valid] / radius, simulation.grid, moisture[:, j]
        )
    return sampled, radii

def representative_table(
    simulation: Simulation, times_h: list[float], distances_cm: list[float]
) -> dict[str, list]:
    times_s = np.asarray(times_h, dtype=float) * 3600.0
    radii_m = np.asarray(distances_cm, dtype=float) / 100.0
    temperature_c, moisture = sample_fixed(simulation, times_s, radii_m)
    return {
        "times_h": times_h,
        "distances_cm": distances_cm,
        "temperature_c": np.round(temperature_c, 4).tolist(),
        "moisture": np.round(moisture, 4).tolist(),
    }


def max_moisture(simulation: Simulation, time_s: float) -> float:
    return float(np.max(simulation.fields(time_s)[1]))


def first_output_time_below(
    simulation: Simulation, step_s: float = 60.0, require_displayed_below: bool = False
) -> tuple[float, float]:
    """返回输出网格上首次严格达标的时刻及未经舍入的最大含水率。"""
    times = np.arange(step_s, simulation.solution.t[-1] + 0.1, step_s)
    maxima = np.max(simulation.fields(times)[1], axis=0)
    eligible = np.round(maxima, 4) < 0.15 if require_displayed_below else maxima < 0.15
    indices = np.flatnonzero(eligible)
    if indices.size == 0:
        qualifier = "四位小数显示" if require_displayed_below else "原始数值"
        raise RuntimeError(f"{simulation.name} 没有在输出网格上以{qualifier}达到 C<0.15")
    index = int(indices[0])
    return float(times[index]), float(maxima[index])


def first_node_output_time_below(
    simulation: Simulation, node_index: int, step_s: float = 60.0
) -> tuple[float, float]:
    """返回指定计算节点在输出网格上首次严格低于0.15的时刻。"""
    times = np.arange(step_s, simulation.solution.t[-1] + 0.1, step_s)
    values = simulation.fields(times)[1][node_index]
    indices = np.flatnonzero(values < 0.15)
    if indices.size == 0:
        raise RuntimeError(f"{simulation.name} 的节点{node_index}在输出网格上未达标")
    index = int(indices[0])
    return float(times[index]), float(values[index])


def grid_difference(
    coarse: Simulation, fine: Simulation, time_s: float, field: str = "moisture"
) -> float:
    coarse_t, coarse_c = coarse.fields(time_s)
    fine_t, fine_c = fine.fields(time_s)
    coarse_values = coarse_c if field == "moisture" else coarse_t
    fine_values = fine_c if field == "moisture" else fine_t
    interpolated = np.interp(coarse.grid, fine.grid, fine_values)
    return float(np.max(np.abs(coarse_values - interpolated)))

