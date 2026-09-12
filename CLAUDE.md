# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains the numerical simulation framework, LaTeX manuscripts, and output workbooks for **2026 CUMCM Problem A: Numerical Simulation and Analysis of Chinese Herbal Medicine Hot-Air Drying Process** (中药材热风烘干过程的数值模拟与分析).

The codebase models 1D radial coupled heat and moisture transfer in cylindrical coordinates under time-varying drying chamber conditions and moving boundaries (radial shrinkage).

- `A题/`: Problem statement (`A题.pdf`) and competition attachments (`附件1.xlsx` chamber data, `附件2.xlsx` shrinkage history, `附件3/` empty template workbooks).
- `A1_1/`: Deliverables (`.pdf` papers, `result1.xlsx`--`result4.xlsx`) and code trees (`support_files/` and `A题_支撑材料/`, which are identical copies).

## Common Commands

All simulation and tool scripts should be run from within `A1_1/support_files/` (or `A1_1/A题_支撑材料/`):

```bash
cd A1_1/support_files
```

### Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Dependencies: `numpy>=2.0`, `pandas>=2.0`, `matplotlib>=3.8`, `openpyxl>=3.1`.

### Data Path Note
`run_all.py`, `validate_results.py`, and `tools/make_figures.py` reference `ATTACHMENT_DIR = ROOT / "A题" / "附件"`. Local copies of `附件1.xlsx` and `附件2.xlsx` exist in `data/`. When running from `support_files/`, either ensure access to `../../A题/附件` (or link/copy `A题/附件`), or point `ATTACHMENT_DIR` to `ROOT / "data"` or `ROOT.parents[1] / "A题" / "附件"`.

### Simulation Execution
- **Full simulation (production grid, ~1--2 min)**:
  ```bash
  python run_all.py
  ```
  Executes Questions 1--4, mechanism comparisons, and spatial/temporal convergence runs. Generates intermediate CSVs in `tmp/numerical/` and summary data in `outputs/summary.json`. Default parameters: 641 nodes for Q1--Q3, 321 nodes for Q4; $dt = 1\text{ s}$ for initial periods, $dt = 30\text{ s}$ for long-term drying.

- **Fast simulation (coarse grid, skips convergence, for development/testing)**:
  ```bash
  python run_all.py --fixed-nodes 161 --moving-nodes 81 --long-dt 60.0 --skip-convergence
  ```
  Note: `--fixed-nodes` must satisfy `(nodes - 1) % 20 == 0` so that 0.1 cm output sampling points align with grid vertices.

### Verification & Validation
- **Run independent numerical checks**:
  ```bash
  python validate_results.py
  ```
  Performs 4 checks: grid convergence for Q1/Q2 (321 vs 641 nodes), equilibrium state preservation with active boundaries, closed-system moisture conservation ($h = h_m = 0$), and relative change across grid/time refinements. Outputs to `outputs/validation.json`.

### Asset & Report Generation
- **Generate LaTeX tables, macros, and CSV curves**:
  ```bash
  python tools/generate_report_assets.py
  ```
  Reads `outputs/summary.json` and `outputs/validation.json`; generates `report/generated_results.tex`, `report/generated_tables.tex`, and center moisture curve CSVs.

- **Generate publication figures**:
  ```bash
  python tools/make_figures.py
  ```
  Generates `boundary_data.png`, `early_profiles.png`, `drying_curves.png`, and `grid_convergence.png` into `report/figures/`.

- **Compile LaTeX documents**:
  ```bash
  cd report
  xelatex paper.tex
  xelatex code_manual.tex
  ```

### Workbook Generation
- Excel deliverables (`result1.xlsx`--`result4.xlsx`) are pre-generated in `results/` and `A1_1/`. The generation script `tools/build_workbooks.mjs` depends on `@oai/artifact-tool`.

## Architecture & Numerical Methods

### Pipeline Flow
```
Data Inputs (附件1.xlsx, 附件2.xlsx)
    │
    ▼
src/drying_solver.py (FVM, BDF2, Picard iteration, moving coordinate transformation)
    │
    ▼
run_all.py ──► Intermediate CSVs (`tmp/numerical/`) & `outputs/summary.json`
    │
    ├─► validate_results.py ──► `outputs/validation.json`
    │
    ├─► tools/generate_report_assets.py ──► LaTeX macros/tables (`report/`)
    ├─► tools/make_figures.py ──► Figures (`report/figures/`)
    └─► tools/build_workbooks.mjs ──► Excel deliverables (`result1.xlsx`--`result4.xlsx`)
```

### Core Solver Architecture (`src/drying_solver.py`)
1. **Governing Equations**:
   - **Fixed Radius (Questions 1--3)**:
     $$\rho c_p \frac{\partial T}{\partial t} = \frac{1}{r} \frac{\partial}{\partial r}\left(r k \frac{\partial T}{\partial r}\right), \quad \frac{\partial C}{\partial t} = \frac{1}{r} \frac{\partial}{\partial r}\left(r D \frac{\partial C}{\partial r}\right)$$
   - **Moving Boundary / Shrinkage (Question 4)**:
     Mapping physical radius $r$ to normalized coordinate $\xi = r / R(t) \in [0, 1]$ introduces a geometric transport advection term:
     $$\frac{\partial T}{\partial t} = \xi \frac{\dot{R}}{R} \frac{\partial T}{\partial \xi} + \frac{1}{\rho c_p R^2 \xi} \frac{\partial}{\partial \xi}\left(\xi k \frac{\partial T}{\partial \xi}\right)$$
     $$\frac{\partial C}{\partial t} = \xi \frac{\dot{R}}{R} \frac{\partial C}{\partial \xi} + \frac{1}{R^2 \xi} \frac{\partial}{\partial \xi}\left(\xi D \frac{\partial C}{\partial \xi}\right)$$
     In `src/drying_solver.py`, `_coordinate_source()` computes $\xi \frac{\dot{R}}{R} \frac{\partial \phi}{\partial \xi}$ with central differences for interior nodes and backward differences at the surface (`include_coordinate_term=True`).

2. **Spatial Discretization**:
   - Vertex-centred 1D cylindrical Finite Volume Method (FVM).
   - Radial cell volume weights: $\omega_i = \frac{1}{2}(\xi_{i+1/2}^2 - \xi_{i-1/2}^2)$.
   - Harmonic mean for interface transport coefficients ($k, D$).
   - Center boundary ($\xi = 0$): natural zero-flux symmetry ($r=0$, avoiding $1/r$ singularity).
   - Surface boundary ($\xi = 1$): Robin convective heat ($h$) and mass ($h_m$) transfer.

3. **Time Integration & Nonlinearity**:
   - First time step uses Backward Euler (BDF1); subsequent equal steps use BDF2.
   - Temperature- and moisture-dependent thermophysical properties (`material_properties()`) are resolved using Picard iteration at each time step (tolerance $2 \times 10^{-10}$, maximum 30 iterations, typically converges in $\le 8$).
   - Tridiagonal linear systems solved directly via the Thomas algorithm (`solve_tridiagonal()`).

4. **Event Handling & Post-Processing**:
   - `simulate()` monitors the drying termination condition ($\max_i C_i \le 0.15\text{ kg/kg}$) and performs zero-crossing linear interpolation to determine the exact drying completion time and profile.
   - `sample_profiles()` projects numerical grid results to fixed physical positions ($0, 0.1, \dots, 2.0\text{ cm}$). When $r > R(t)$ due to shrinkage in Q4, values outside the herb domain are marked as `NaN` (blank in Excel).

### Reference Results
- **Question 3 drying time** (Appendix 3 properties, fixed $R = 2\text{ cm}$): **57.5303 h**
- **Question 4 drying time** (Appendix 4 properties, shrinking $R(t)$, with geometric transport): **52.6776 h** (final radius: $1.2000\text{ cm}$)
- **Shrinkage reduction**: Shrinkage reduces drying time by 59.47% relative to the fixed-radius Appendix 4 baseline (129.9873 h).
- **Geometric transport term effect**: Omitting $\xi \frac{\dot{R}}{R}$ yields 51.1141 h (-2.97% error).
