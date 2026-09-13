"""求解过程中使用的数据结构。"""

from dataclasses import dataclass

import numpy as np

from .config import PLATEAU_START_S

@dataclass(frozen=True)
class Environment:
    time_s: np.ndarray
    temperature_k: np.ndarray
    moisture: np.ndarray
    plateau_temperature_k: float
    plateau_moisture: float

    def __call__(self, t: float) -> tuple[float, float]:
        if t < PLATEAU_START_S:
            ta = float(np.interp(t, self.time_s, self.temperature_k))
            ca = float(np.interp(t, self.time_s, self.moisture))
            return ta, ca
        return self.plateau_temperature_k, self.plateau_moisture


@dataclass(frozen=True)
class RadiusHistory:
    time_s: np.ndarray
    radius_m: np.ndarray

    def value_and_rate(self, t: float) -> tuple[float, float]:
        if t < self.time_s[0] - 1e-9 or t > self.time_s[-1] + 1e-9:
            raise ValueError(f"半径查询时间 {t} s 超出附件 2 的 0--72 h 范围")
        tc = float(np.clip(t, self.time_s[0], self.time_s[-1]))
        idx = int(np.searchsorted(self.time_s, tc, side="right") - 1)
        idx = min(max(idx, 0), len(self.time_s) - 2)
        t0, t1 = self.time_s[idx], self.time_s[idx + 1]
        r0, r1 = self.radius_m[idx], self.radius_m[idx + 1]
        rate = float((r1 - r0) / (t1 - t0))
        radius = float(r0 + rate * (tc - t0))
        return radius, rate


@dataclass
class Simulation:
    name: str
    grid: np.ndarray
    solution: object
    moving_radius: bool = False

    @property
    def n(self) -> int:
        return self.grid.size

    def fields(self, time_s: np.ndarray | float) -> tuple[np.ndarray, np.ndarray]:
        values = np.asarray(self.solution.sol(time_s), dtype=float)
        return values[: self.n], values[self.n :]
