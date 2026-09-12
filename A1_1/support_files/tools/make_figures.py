"""Create publication figures from the verified numerical outputs."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ATT = ROOT / "A题" / "附件"
NUM = ROOT / "tmp" / "numerical"
OUT = ROOT / "report" / "figures"


def finish(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })

    env = pd.read_excel(ATT / "附件1.xlsx")
    radius = pd.read_excel(ATT / "附件2.xlsx")
    fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.25))
    t_h = env.iloc[:, 0].to_numpy() / 3600
    ax[0].plot(t_h, env.iloc[:, 1], lw=1.6, label="Air temperature")
    ax0b = ax[0].twinx()
    ax0b.plot(t_h, env.iloc[:, 2], color="#c44e52", lw=1.4, label="Air moisture")
    ax[0].set(xlabel="Time (h)", ylabel="Temperature (deg C)")
    ax0b.set_ylabel("Moisture (kg/kg)", color="#c44e52")
    ax[0].set_title("Measured drying-room boundary")
    ax[1].plot(radius.iloc[:, 0] / 3600, radius.iloc[:, 1], color="#2f5597", lw=1.7)
    ax[1].set(xlabel="Time (h)", ylabel="Radius (cm)", title="Measured radius history")
    finish(OUT / "boundary_data.png")

    q1t = pd.read_csv(NUM / "result1_temperature.csv")
    q1c = pd.read_csv(NUM / "result1_moisture.csv")
    q2t = pd.read_csv(NUM / "result2_temperature.csv")
    q2c = pd.read_csv(NUM / "result2_moisture.csv")
    r = np.asarray([float(x) for x in q1t.columns[1:]])
    fig, ax = plt.subplots(2, 2, figsize=(9.2, 6.2), sharex=True)
    for sec in [300, 900, 1800]:
        row = q1t.loc[q1t.iloc[:, 0] == sec].iloc[0, 1:].to_numpy(float)
        ax[0, 0].plot(r, row, label=f"{sec} s")
        row = q1c.loc[q1c.iloc[:, 0] == sec].iloc[0, 1:].to_numpy(float)
        ax[1, 0].plot(r, row, label=f"{sec} s")
    for sec in [3600, 7200, 10800]:
        row = q2t.loc[q2t.iloc[:, 0] == sec].iloc[0, 1:].to_numpy(float)
        ax[0, 1].plot(r, row, label=f"{sec/3600:.0f} h")
        row = q2c.loc[q2c.iloc[:, 0] == sec].iloc[0, 1:].to_numpy(float)
        ax[1, 1].plot(r, row, label=f"{sec/3600:.0f} h")
    ax[0, 0].set(title="Question 1: temperature", ylabel="Temperature (deg C)")
    ax[1, 0].set(title="Question 1: moisture", xlabel="Radius (cm)", ylabel="Moisture (kg/kg)")
    ax[0, 1].set(title="Question 2: temperature", ylabel="Temperature (deg C)")
    ax[1, 1].set(title="Question 2: moisture", xlabel="Radius (cm)", ylabel="Moisture (kg/kg)")
    for a in ax.ravel():
        a.legend(frameon=False, fontsize=8)
    finish(OUT / "early_profiles.png")

    q3 = pd.read_csv(NUM / "result3_moisture.csv")
    q4 = pd.read_csv(NUM / "result4_moisture.csv")
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.plot(q3.iloc[:, 0] / 3600, q3.iloc[:, 1], lw=1.8, label="Q3 center")
    ax.plot(q3.iloc[:, 0] / 3600, q3.iloc[:, -1], lw=1.4, label="Q3 surface")
    ax.plot(q4.iloc[:, 0] / 3600, q4.iloc[:, 1], lw=1.8, label="Q4 center")
    ax.plot(q4.iloc[:, 0] / 3600, q4.iloc[:, -1], lw=1.4, label="Q4 moving surface")
    ax.axhline(0.15, color="#c44e52", ls="--", lw=1.2, label="Criterion 0.15")
    ax.set(xlabel="Time (h)", ylabel="Moisture (kg/kg)", xlim=(0, 60), ylim=(0, 2.65))
    ax.legend(frameon=False, ncol=2)
    finish(OUT / "drying_curves.png")

    summary = json.loads((ROOT / "outputs" / "summary.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.3))
    for a, key, title in zip(ax, ["q3_space", "q4_space"], ["Question 3", "Question 4"]):
        rows = summary["convergence"][key]
        spacing = [row["spacing_initial_cm"] for row in rows]
        hours = [row["dry_time_h"] for row in rows]
        a.plot(spacing, hours, "o-", color="#2f5597")
        a.invert_xaxis()
        a.set(xlabel="Initial radial spacing (cm)", ylabel="Drying time (h)", title=title)
    finish(OUT / "grid_convergence.png")


if __name__ == "__main__":
    main()
