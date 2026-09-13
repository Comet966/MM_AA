"""有限体积半离散与 BDF 时间积分。"""

from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix

from . import physics
from .config import INITIAL_C, INITIAL_RADIUS_M, INITIAL_T_K
from .models import Environment, RadiusHistory, Simulation

def coupled_jacobian_sparsity(node_count: int):
    """温度/水分两场、三点空间模板对应的稀疏雅可比结构。"""
    pattern = lil_matrix((2 * node_count, 2 * node_count), dtype=int)
    for equation_field in range(2):
        for variable_field in range(2):
            row_offset = equation_field * node_count
            col_offset = variable_field * node_count
            for i in range(node_count):
                for j in range(max(0, i - 1), min(node_count, i + 2)):
                    pattern[row_offset + i, col_offset + j] = 1
    return pattern.tocsr()


def make_fixed_rhs(
    radius_m: float,
    node_count: int,
    model: str,
    environment: Environment,
) -> tuple[np.ndarray, Callable[[float, np.ndarray], np.ndarray]]:
    r = np.linspace(0.0, radius_m, node_count)
    dr = float(r[1] - r[0])
    r_half = 0.5 * (r[:-1] + r[1:])

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        temperature = y[:node_count]
        moisture = y[node_count:]
        rho, cp, k, diffusivity = physics.material_properties(model, temperature, moisture)
        k_face = physics.harmonic_mean(k)
        d_face = physics.harmonic_mean(diffusivity)
        ta, ca = environment(t)

        dt = np.empty(node_count, dtype=float)
        dc = np.empty(node_count, dtype=float)
        dt[0] = 4.0 * k_face[0] * (temperature[1] - temperature[0]) / (
            rho[0] * cp[0] * dr**2
        )
        dc[0] = 4.0 * d_face[0] * (moisture[1] - moisture[0]) / dr**2

        heat_out = r_half[1:] * k_face[1:] * np.diff(temperature)[1:] / dr
        heat_in = r_half[:-1] * k_face[:-1] * np.diff(temperature)[:-1] / dr
        mass_out = r_half[1:] * d_face[1:] * np.diff(moisture)[1:] / dr
        mass_in = r_half[:-1] * d_face[:-1] * np.diff(moisture)[:-1] / dr
        dt[1:-1] = (heat_out - heat_in) / (rho[1:-1] * cp[1:-1] * r[1:-1] * dr)
        dc[1:-1] = (mass_out - mass_in) / (r[1:-1] * dr)

        r_minus = radius_m - 0.5 * dr
        shell_measure = radius_m**2 - r_minus**2
        dt[-1] = 2.0 * (
            -radius_m * physics.HEAT_TRANSFER * (temperature[-1] - ta)
            - r_minus * k_face[-1] * (temperature[-1] - temperature[-2]) / dr
        ) / (rho[-1] * cp[-1] * shell_measure)
        dc[-1] = 2.0 * (
            -radius_m * physics.MASS_TRANSFER * (moisture[-1] - ca)
            - r_minus * d_face[-1] * (moisture[-1] - moisture[-2]) / dr
        ) / shell_measure
        return np.concatenate((dt, dc))

    return r, rhs


def make_moving_rhs(
    node_count: int,
    environment: Environment,
    radius_history: RadiusHistory,
    include_geometry_term: bool,
) -> tuple[np.ndarray, Callable[[float, np.ndarray], np.ndarray]]:
    xi = np.linspace(0.0, 1.0, node_count)
    dxi = float(xi[1] - xi[0])
    xi_half = 0.5 * (xi[:-1] + xi[1:])

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        temperature = y[:node_count]
        moisture = y[node_count:]
        radius, radius_rate = radius_history.value_and_rate(t)
        rho, cp, k, diffusivity = physics.material_properties(
            "appendix4", temperature, moisture
        )
        k_face = physics.harmonic_mean(k)
        d_face = physics.harmonic_mean(diffusivity)
        ta, ca = environment(t)

        dt = np.empty(node_count, dtype=float)
        dc = np.empty(node_count, dtype=float)
        dt[0] = 4.0 * k_face[0] * (temperature[1] - temperature[0]) / (
            rho[0] * cp[0] * radius**2 * dxi**2
        )
        dc[0] = 4.0 * d_face[0] * (moisture[1] - moisture[0]) / (
            radius**2 * dxi**2
        )

        heat_out = xi_half[1:] * k_face[1:] * np.diff(temperature)[1:] / dxi
        heat_in = xi_half[:-1] * k_face[:-1] * np.diff(temperature)[:-1] / dxi
        mass_out = xi_half[1:] * d_face[1:] * np.diff(moisture)[1:] / dxi
        mass_in = xi_half[:-1] * d_face[:-1] * np.diff(moisture)[:-1] / dxi
        dt[1:-1] = (heat_out - heat_in) / (
            rho[1:-1] * cp[1:-1] * radius**2 * xi[1:-1] * dxi
        )
        dc[1:-1] = (mass_out - mass_in) / (
            radius**2 * xi[1:-1] * dxi
        )

        xi_minus = 1.0 - 0.5 * dxi
        shell_measure = 1.0 - xi_minus**2
        dt[-1] = 2.0 * (
            -radius * physics.HEAT_TRANSFER * (temperature[-1] - ta)
            - xi_minus * k_face[-1] * (temperature[-1] - temperature[-2]) / dxi
        ) / (rho[-1] * cp[-1] * radius**2 * shell_measure)
        dc[-1] = 2.0 * (
            -radius * physics.MASS_TRANSFER * (moisture[-1] - ca)
            - xi_minus * d_face[-1] * (moisture[-1] - moisture[-2]) / dxi
        ) / (radius**2 * shell_measure)

        if include_geometry_term:
            factor = radius_rate / radius
            t_xi = np.empty(node_count, dtype=float)
            c_xi = np.empty(node_count, dtype=float)
            t_xi[0] = 0.0
            c_xi[0] = 0.0
            t_xi[1:-1] = (temperature[2:] - temperature[:-2]) / (2.0 * dxi)
            c_xi[1:-1] = (moisture[2:] - moisture[:-2]) / (2.0 * dxi)
            t_xi[-1] = -radius * physics.HEAT_TRANSFER * (temperature[-1] - ta) / k[-1]
            c_xi[-1] = -radius * physics.MASS_TRANSFER * (moisture[-1] - ca) / diffusivity[-1]
            dt += xi * factor * t_xi
            dc += xi * factor * c_xi
        return np.concatenate((dt, dc))

    return xi, rhs


def dry_event(node_count: int) -> Callable[[float, np.ndarray], float]:
    def event(_t: float, y: np.ndarray) -> float:
        return float(np.max(y[node_count:]) - 0.15)

    event.direction = -1
    event.terminal = False
    return event


def solve_fixed(
    name: str,
    end_s: float,
    node_count: int,
    model: str,
    environment: Environment,
    track_dry_event: bool = False,
) -> Simulation:
    grid, rhs = make_fixed_rhs(INITIAL_RADIUS_M, node_count, model, environment)
    y0 = np.concatenate(
        (np.full(node_count, INITIAL_T_K), np.full(node_count, INITIAL_C))
    )
    events = dry_event(node_count) if track_dry_event else None
    solution = solve_ivp(
        rhs,
        (0.0, end_s),
        y0,
        method="BDF",
        rtol=1.0e-6,
        atol=1.0e-8,
        max_step=300.0,
        dense_output=True,
        events=events,
        jac_sparsity=coupled_jacobian_sparsity(node_count),
    )
    if not solution.success:
        raise RuntimeError(f"{name} 求解失败：{solution.message}")
    return Simulation(name=name, grid=grid, solution=solution)


def solve_moving(
    name: str,
    end_s: float,
    node_count: int,
    environment: Environment,
    radius_history: RadiusHistory,
    include_geometry_term: bool,
    track_dry_event: bool = True,
) -> Simulation:
    grid, rhs = make_moving_rhs(
        node_count, environment, radius_history, include_geometry_term
    )
    y0 = np.concatenate(
        (np.full(node_count, INITIAL_T_K), np.full(node_count, INITIAL_C))
    )
    events = dry_event(node_count) if track_dry_event else None
    solution = solve_ivp(
        rhs,
        (0.0, end_s),
        y0,
        method="BDF",
        rtol=1.0e-6,
        atol=1.0e-8,
        max_step=300.0,
        dense_output=True,
        events=events,
        jac_sparsity=coupled_jacobian_sparsity(node_count),
    )
    if not solution.success:
        raise RuntimeError(f"{name} 求解失败：{solution.message}")
    return Simulation(name=name, grid=grid, solution=solution, moving_radius=True)

