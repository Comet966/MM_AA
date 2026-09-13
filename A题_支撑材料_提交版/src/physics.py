"""附录2--4物性关系与界面系数计算。"""

import numpy as np

from .config import (
    DIFFUSIVITY_SCALE_DEFAULT,
    HEAT_TRANSFER_DEFAULT,
    MASS_TRANSFER_DEFAULT,
)

HEAT_TRANSFER = HEAT_TRANSFER_DEFAULT
MASS_TRANSFER = MASS_TRANSFER_DEFAULT
DIFFUSIVITY_SCALE = DIFFUSIVITY_SCALE_DEFAULT

def material_properties(
    model: str, temperature_k: np.ndarray, moisture: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    c = np.maximum(np.asarray(moisture, dtype=float), 1e-10)
    t = np.asarray(temperature_k, dtype=float)
    if model == "appendix2":
        rho = np.full_like(c, 820.0)
        cp = np.full_like(c, 2600.0)
        k = np.full_like(c, 0.36)
        diffusivity = 7.0e-9 * np.exp(-0.89 / c)
    elif model == "appendix3":
        rho = 650.0 + 128.0 * c
        cp = 1450.0 + 2736.0 * c / (c + 1.0)
        k = 0.21 + 0.38 * c / (c + 1.0)
        diffusivity = 2.4e-3 * np.exp(-0.45 / c) * np.exp(-3850.0 / t)
    elif model == "appendix4":
        rho = 760.0 + 90.0 * c
        cp = 1850.0 + 2150.0 * c / (c + 1.0)
        k = 0.12 + 0.20 * c / (c + 1.0)
        diffusivity = 4.2e-4 * np.exp(-0.30 / c) * np.exp(-3850.0 / t)
    else:
        raise ValueError(f"未知物性模型：{model}")
    return rho, cp, k, diffusivity * DIFFUSIVITY_SCALE


def harmonic_mean(values: np.ndarray) -> np.ndarray:
    left, right = values[:-1], values[1:]
    return 2.0 * left * right / np.maximum(left + right, 1e-300)

