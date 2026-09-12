"""Finite-volume solver for the 2026 CUMCM problem A drying model.

The radial PDEs are discretized on a vertex-centred cylindrical finite-volume
grid.  Time integration uses backward Euler for the first step and BDF2 for
subsequent equal-size steps.  Nonlinear material properties are handled by a
Picard iteration at every implicit step.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np


_SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    result = 0
    for char in letters:
        result = result * 26 + ord(char.upper()) - ord("A") + 1
    return result - 1


def read_first_sheet_numeric(path: str | Path) -> tuple[list[str], np.ndarray]:
    """Read a simple numeric first worksheet using only the standard library."""

    with ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [
                "".join(node.text or "" for node in item.iter(_SHEET_NS + "t"))
                for item in root.findall(_SHEET_NS + "si")
            ]

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in rels}
        first_sheet = workbook.find(_SHEET_NS + "sheets")[0]
        target = targets[first_sheet.attrib[_REL_NS + "id"]]
        sheet_path = target if target.startswith("xl/") else "xl/" + target.lstrip("/")
        sheet = ET.fromstring(archive.read(sheet_path))

        rows: list[list[str | float | None]] = []
        for row_node in sheet.iter(_SHEET_NS + "row"):
            row: list[str | float | None] = []
            for cell in row_node.findall(_SHEET_NS + "c"):
                col = _column_index(cell.attrib["r"])
                while len(row) <= col:
                    row.append(None)
                value_node = cell.find(_SHEET_NS + "v")
                if value_node is None:
                    value: str | float | None = None
                elif cell.attrib.get("t") == "s":
                    value = shared[int(value_node.text)]
                else:
                    value = float(value_node.text)
                row[col] = value
            rows.append(row)

    headers = [str(item) for item in rows[0]]
    values = np.asarray(rows[1:], dtype=float)
    return headers, values


@dataclass(frozen=True)
class Environment:
    time_s: np.ndarray
    temperature_k: np.ndarray
    moisture: np.ndarray
    plateau_temperature_k: float
    plateau_moisture: float
    stable_start_s: float

    @classmethod
    def from_attachment(cls, path: str | Path) -> "Environment":
        _, values = read_first_sheet_numeric(path)
        time_s, temperature_c, moisture = values.T
        plateau_mask = time_s >= 9000.0
        plateau_temperature_k = float(np.mean(temperature_c[plateau_mask]) + 273.15)
        plateau_moisture = float(np.mean(moisture[plateau_mask]))

        stable = (
            (np.abs(temperature_c - (plateau_temperature_k - 273.15)) < 0.5)
            & (np.abs(moisture - plateau_moisture) < 1.0e-3)
        )
        stable_start_s = float(time_s[-1])
        required_points = 31  # 30 minutes at the supplied 60 s sampling interval.
        for index in range(len(time_s) - required_points + 1):
            if np.all(stable[index : index + required_points]):
                stable_start_s = float(time_s[index])
                break

        return cls(
            time_s=time_s,
            temperature_k=temperature_c + 273.15,
            moisture=moisture,
            plateau_temperature_k=plateau_temperature_k,
            plateau_moisture=plateau_moisture,
            stable_start_s=stable_start_s,
        )

    def values(self, time_s: float) -> tuple[float, float]:
        """Measured interpolation through 4 h, then the measured plateau mean."""

        if time_s <= self.time_s[-1]:
            return (
                float(np.interp(time_s, self.time_s, self.temperature_k)),
                float(np.interp(time_s, self.time_s, self.moisture)),
            )
        return self.plateau_temperature_k, self.plateau_moisture


@dataclass(frozen=True)
class RadiusModel:
    time_s: np.ndarray
    radius_m: np.ndarray

    @classmethod
    def from_attachment(cls, path: str | Path) -> "RadiusModel":
        _, values = read_first_sheet_numeric(path)
        return cls(time_s=values[:, 0], radius_m=values[:, 1] / 100.0)

    def value(self, time_s: float) -> float:
        return float(np.interp(time_s, self.time_s, self.radius_m))

    def rate(self, time_s: float) -> float:
        if time_s <= self.time_s[0] or time_s >= self.time_s[-1]:
            return 0.0
        index = int(np.searchsorted(self.time_s, time_s, side="right") - 1)
        return float(
            (self.radius_m[index + 1] - self.radius_m[index])
            / (self.time_s[index + 1] - self.time_s[index])
        )


PropertySet = Literal["appendix2", "appendix3", "appendix4"]


def material_properties(
    property_set: PropertySet, temperature_k: np.ndarray, moisture: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    safe_moisture = np.maximum(moisture, 1.0e-8)
    if property_set == "appendix2":
        rho = np.full_like(moisture, 820.0)
        cp = np.full_like(moisture, 2600.0)
        conductivity = np.full_like(moisture, 0.36)
        diffusivity = 7.0e-9 * np.exp(-0.89 / safe_moisture)
    elif property_set == "appendix3":
        rho = 650.0 + 128.0 * moisture
        cp = 1450.0 + 2736.0 * moisture / (moisture + 1.0)
        conductivity = 0.21 + 0.38 * moisture / (moisture + 1.0)
        diffusivity = (
            2.4e-3
            * np.exp(-0.45 / safe_moisture)
            * np.exp(-3850.0 / temperature_k)
        )
    elif property_set == "appendix4":
        rho = 760.0 + 90.0 * moisture
        cp = 1850.0 + 2150.0 * moisture / (moisture + 1.0)
        conductivity = 0.12 + 0.20 * moisture / (moisture + 1.0)
        diffusivity = (
            4.2e-4
            * np.exp(-0.30 / safe_moisture)
            * np.exp(-3850.0 / temperature_k)
        )
    else:
        raise ValueError(f"Unknown property set: {property_set}")
    return rho, cp, conductivity, diffusivity


def harmonic_mean(values: np.ndarray) -> np.ndarray:
    left, right = values[:-1], values[1:]
    denominator = left + right
    return np.divide(2.0 * left * right, denominator, out=np.zeros_like(left), where=denominator > 0)


def solve_tridiagonal(
    lower: np.ndarray, diagonal: np.ndarray, upper: np.ndarray, rhs: np.ndarray
) -> np.ndarray:
    """Thomas algorithm with copies so the assembled matrix is not mutated."""

    count = len(diagonal)
    c_prime = np.empty(count - 1, dtype=float)
    d_prime = np.empty(count, dtype=float)
    pivot = diagonal[0]
    if abs(pivot) < 1.0e-18:
        raise FloatingPointError("Near-zero pivot in tridiagonal solve")
    c_prime[0] = upper[0] / pivot
    d_prime[0] = rhs[0] / pivot
    for index in range(1, count):
        pivot = diagonal[index] - lower[index - 1] * c_prime[index - 1]
        if abs(pivot) < 1.0e-18:
            raise FloatingPointError("Near-zero pivot in tridiagonal solve")
        if index < count - 1:
            c_prime[index] = upper[index] / pivot
        d_prime[index] = (rhs[index] - lower[index - 1] * d_prime[index - 1]) / pivot

    result = np.empty(count, dtype=float)
    result[-1] = d_prime[-1]
    for index in range(count - 2, -1, -1):
        result[index] = d_prime[index] - c_prime[index] * result[index + 1]
    return result


@dataclass(frozen=True)
class Grid:
    xi: np.ndarray
    faces: np.ndarray
    radial_volume: np.ndarray
    dxi: float

    @classmethod
    def uniform(cls, node_count: int) -> "Grid":
        if node_count < 3:
            raise ValueError("At least three radial nodes are required")
        xi = np.linspace(0.0, 1.0, node_count)
        dxi = float(xi[1] - xi[0])
        faces = np.empty(node_count + 1)
        faces[0], faces[-1] = 0.0, 1.0
        faces[1:-1] = 0.5 * (xi[:-1] + xi[1:])
        radial_volume = 0.5 * (faces[1:] ** 2 - faces[:-1] ** 2)
        return cls(xi=xi, faces=faces, radial_volume=radial_volume, dxi=dxi)


@dataclass(frozen=True)
class SimulationConfig:
    property_set: PropertySet
    node_count: int = 161
    heat_transfer_coefficient: float = 25.0
    mass_transfer_coefficient: float = 8.0e-7
    fixed_radius_m: float = 0.02
    radius_model: RadiusModel | None = None
    include_coordinate_term: bool = False
    picard_tolerance: float = 2.0e-10
    picard_max_iterations: int = 30

    def radius(self, time_s: float) -> float:
        return self.fixed_radius_m if self.radius_model is None else self.radius_model.value(time_s)

    def radius_rate(self, time_s: float) -> float:
        return 0.0 if self.radius_model is None else self.radius_model.rate(time_s)


@dataclass
class SimulationResult:
    time_s: np.ndarray
    temperature_k: np.ndarray
    moisture: np.ndarray
    radius_m: np.ndarray
    dry_time_s: float | None = None
    dry_temperature_k: np.ndarray | None = None
    dry_moisture: np.ndarray | None = None
    max_picard_iterations: int = 0


def _diffusion_operator(
    grid: Grid,
    coefficient: np.ndarray,
    capacity: np.ndarray,
    radius_m: float,
    transfer_coefficient: float,
    ambient_value: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return lower/diagonal/upper and constant source for L(phi)+source."""

    count = len(grid.xi)
    face_coefficient = harmonic_mean(coefficient)
    face_conductance = (
        grid.faces[1:-1] * face_coefficient / grid.dxi / radius_m**2
    )
    scale = capacity * grid.radial_volume

    lower = face_conductance / scale[1:]
    upper = face_conductance / scale[:-1]
    diagonal = np.zeros(count, dtype=float)
    diagonal[:-1] -= upper
    diagonal[1:] -= lower

    boundary_exchange = transfer_coefficient / radius_m / scale[-1]
    diagonal[-1] -= boundary_exchange
    source = np.zeros(count, dtype=float)
    source[-1] = boundary_exchange * ambient_value
    return lower, diagonal, upper, source


def _coordinate_source(
    values: np.ndarray, grid: Grid, radius_m: float, radius_rate_m_s: float
) -> np.ndarray:
    """Eulerian-to-fixed-coordinate term retained in the main moving-boundary case."""

    gradient = np.empty_like(values)
    gradient[0] = 0.0
    gradient[1:-1] = (values[2:] - values[:-2]) / (2.0 * grid.dxi)
    gradient[-1] = (values[-1] - values[-2]) / grid.dxi
    return grid.xi * radius_rate_m_s / radius_m * gradient


def _implicit_step(
    config: SimulationConfig,
    grid: Grid,
    environment: Environment,
    time_new_s: float,
    dt_s: float,
    temperature_n: np.ndarray,
    moisture_n: np.ndarray,
    temperature_nm1: np.ndarray | None,
    moisture_nm1: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, int]:
    bdf2 = temperature_nm1 is not None and moisture_nm1 is not None
    alpha = 1.5 if bdf2 else 1.0
    temperature_history = (
        2.0 * temperature_n - 0.5 * temperature_nm1 if bdf2 else temperature_n
    )
    moisture_history = 2.0 * moisture_n - 0.5 * moisture_nm1 if bdf2 else moisture_n

    if bdf2:
        temperature_guess = 2.0 * temperature_n - temperature_nm1
        moisture_guess = 2.0 * moisture_n - moisture_nm1
    else:
        temperature_guess = temperature_n.copy()
        moisture_guess = moisture_n.copy()

    ambient_temperature, ambient_moisture = environment.values(time_new_s)
    radius_m = config.radius(time_new_s)
    radius_rate_m_s = config.radius_rate(time_new_s)

    for iteration in range(1, config.picard_max_iterations + 1):
        rho, cp, conductivity, _ = material_properties(
            config.property_set, temperature_guess, moisture_guess
        )
        heat_lower, heat_diag, heat_upper, heat_source = _diffusion_operator(
            grid,
            conductivity,
            rho * cp,
            radius_m,
            config.heat_transfer_coefficient,
            ambient_temperature,
        )
        if config.include_coordinate_term:
            heat_source += _coordinate_source(
                temperature_guess, grid, radius_m, radius_rate_m_s
            )
        temperature_new = solve_tridiagonal(
            -dt_s * heat_lower,
            alpha - dt_s * heat_diag,
            -dt_s * heat_upper,
            temperature_history + dt_s * heat_source,
        )

        _, _, _, diffusivity = material_properties(
            config.property_set, temperature_new, moisture_guess
        )
        mass_lower, mass_diag, mass_upper, mass_source = _diffusion_operator(
            grid,
            diffusivity,
            np.ones_like(moisture_guess),
            radius_m,
            config.mass_transfer_coefficient,
            ambient_moisture,
        )
        if config.include_coordinate_term:
            mass_source += _coordinate_source(
                moisture_guess, grid, radius_m, radius_rate_m_s
            )
        moisture_new = solve_tridiagonal(
            -dt_s * mass_lower,
            alpha - dt_s * mass_diag,
            -dt_s * mass_upper,
            moisture_history + dt_s * mass_source,
        )

        temperature_error = float(
            np.max(np.abs(temperature_new - temperature_guess))
            / max(1.0, float(np.max(np.abs(temperature_new))))
        )
        moisture_error = float(
            np.max(np.abs(moisture_new - moisture_guess))
            / max(1.0, float(np.max(np.abs(moisture_new))))
        )
        temperature_guess = temperature_new
        moisture_guess = moisture_new
        if max(temperature_error, moisture_error) < config.picard_tolerance:
            return temperature_new, moisture_new, iteration

    raise RuntimeError(
        f"Picard iteration did not converge at t={time_new_s:.3f} s; "
        f"last errors were {temperature_error:.3e}, {moisture_error:.3e}"
    )


def simulate(
    config: SimulationConfig,
    environment: Environment,
    start_time_s: float,
    end_time_s: float,
    dt_s: float,
    initial_temperature_k: np.ndarray | None = None,
    initial_moisture: np.ndarray | None = None,
    save_every_s: float | None = None,
    stop_moisture: float | None = None,
    progress: Callable[[float, float], None] | None = None,
) -> SimulationResult:
    """Integrate the model and optionally stop when every node is dry enough."""

    grid = Grid.uniform(config.node_count)
    temperature_n = (
        np.full(config.node_count, 301.15)
        if initial_temperature_k is None
        else np.asarray(initial_temperature_k, dtype=float).copy()
    )
    moisture_n = (
        np.full(config.node_count, 2.55)
        if initial_moisture is None
        else np.asarray(initial_moisture, dtype=float).copy()
    )
    if temperature_n.shape != (config.node_count,) or moisture_n.shape != (config.node_count,):
        raise ValueError("Initial profiles must match node_count")

    save_every_s = dt_s if save_every_s is None else save_every_s
    ratio = save_every_s / dt_s
    save_stride = int(round(ratio))
    if not np.isclose(ratio, save_stride, rtol=0.0, atol=1.0e-10):
        raise ValueError("save_every_s must be an integer multiple of dt_s")

    time_values = [float(start_time_s)]
    temperature_values = [temperature_n.copy()]
    moisture_values = [moisture_n.copy()]
    radius_values = [config.radius(start_time_s)]
    temperature_nm1: np.ndarray | None = None
    moisture_nm1: np.ndarray | None = None
    dry_time_s: float | None = None
    dry_temperature: np.ndarray | None = None
    dry_moisture_profile: np.ndarray | None = None
    maximum_iterations = 0

    total_steps = int(np.ceil((end_time_s - start_time_s) / dt_s))
    previous_time = float(start_time_s)
    previous_max = float(np.max(moisture_n))

    for step in range(1, total_steps + 1):
        time_new = min(start_time_s + step * dt_s, end_time_s)
        actual_dt = time_new - previous_time
        use_history = np.isclose(actual_dt, dt_s) and temperature_nm1 is not None
        temperature_new, moisture_new, iterations = _implicit_step(
            config,
            grid,
            environment,
            time_new,
            actual_dt,
            temperature_n,
            moisture_n,
            temperature_nm1 if use_history else None,
            moisture_nm1 if use_history else None,
        )
        maximum_iterations = max(maximum_iterations, iterations)
        current_max = float(np.max(moisture_new))

        if stop_moisture is not None and previous_max > stop_moisture >= current_max:
            fraction = (previous_max - stop_moisture) / max(previous_max - current_max, 1.0e-30)
            dry_time_s = previous_time + fraction * actual_dt
            dry_temperature = temperature_n + fraction * (temperature_new - temperature_n)
            dry_moisture_profile = moisture_n + fraction * (moisture_new - moisture_n)

            time_values.append(float(dry_time_s))
            temperature_values.append(dry_temperature.copy())
            moisture_values.append(dry_moisture_profile.copy())
            radius_values.append(config.radius(dry_time_s))
            maximum_iterations = max(maximum_iterations, iterations)
            if progress is not None:
                progress(dry_time_s, end_time_s)
            break

        if step % save_stride == 0 or np.isclose(time_new, end_time_s):
            time_values.append(float(time_new))
            temperature_values.append(temperature_new.copy())
            moisture_values.append(moisture_new.copy())
            radius_values.append(config.radius(time_new))

        temperature_nm1, temperature_n = temperature_n, temperature_new
        moisture_nm1, moisture_n = moisture_n, moisture_new
        previous_time, previous_max = time_new, current_max

        if progress is not None and (step == total_steps or step % max(1, total_steps // 20) == 0):
            progress(time_new, end_time_s)

    return SimulationResult(
        time_s=np.asarray(time_values),
        temperature_k=np.asarray(temperature_values),
        moisture=np.asarray(moisture_values),
        radius_m=np.asarray(radius_values),
        dry_time_s=dry_time_s,
        dry_temperature_k=dry_temperature,
        dry_moisture=dry_moisture_profile,
        max_picard_iterations=maximum_iterations,
    )


def sample_profiles(
    result: SimulationResult,
    xi: np.ndarray,
    physical_radius_cm: np.ndarray,
    include_surface: bool = False,
) -> tuple[np.ndarray, list[str]]:
    """Sample profiles at fixed physical radii; outside-domain values are NaN."""

    output = np.full((len(result.time_s), len(physical_radius_cm)), np.nan)
    for row, radius_m in enumerate(result.radius_m):
        physical_m = physical_radius_cm / 100.0
        valid = physical_m <= radius_m + 1.0e-12
        output[row, valid] = np.interp(physical_m[valid] / radius_m, xi, result.moisture[row])
    headers = [f"{value:.1f}" for value in physical_radius_cm]
    if include_surface:
        output = np.column_stack([output, result.moisture[:, -1]])
        headers.append("药材表面")
    return output, headers
