# A题药材烘干数值求解

本目录包含最终论文、代码说明书、四问数值代码、验证程序和题目要求的结果文件。

主要入口：

- `run_all.py`：运行四问并生成 `outputs/summary.json` 和中间 CSV。
- `src/drying_solver.py`：柱坐标有限体积、BDF1/BDF2、Picard 非线性迭代。
- `validate_results.py`：守恒、平衡态、网格和时间收敛验证。
- `tools/build_workbooks.mjs`：生成四个题目要求的 Excel 结果文件。
- `tools/generate_report_assets.py`、`tools/make_figures.py`：生成论文表格、宏和图片。
- `report/paper.tex`：正式建模论文 LaTeX 源文件。
- `report/code_manual.tex`：代码说明与结果可行性分析 LaTeX 源文件。

Python 环境：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_all.py
python validate_results.py
python tools/generate_report_assets.py
python tools/make_figures.py
```

Excel 导出脚本依赖 `@oai/artifact-tool`，竞赛提交时通常直接使用已生成的
`result1.xlsx`--`result4.xlsx`，无需重新导出。

正式网格：问题1--3 使用 641 个径向节点；问题4 使用 321 个无量纲径向节点。计算网格显著细于题目规定的 0.1 cm 输出网格。

最终时长：问题3为 57.5303 h；问题4完整移动边界模型为 52.6776 h。
