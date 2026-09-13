# A 题“药材的烘干问题”支撑材料

本目录用于复现四个问题的数值结果与论文图表。根据全国大学生数学建模竞赛（CUMCM）评奖规范要求，四个规定结果工作簿（`result1.xlsx` $\sim$ `result4.xlsx`）直接位于本支撑材料根目录下。

## 目录结构

```text
支撑材料/
├─ result1.xlsx               问题一规定结果工作簿（温度与水分浓度）
├─ result2.xlsx               问题二规定结果工作簿（温度与水分浓度）
├─ result3.xlsx               问题三规定结果工作簿（水分浓度）
├─ result4.xlsx               问题四规定结果工作簿（含药材表面水分浓度）
├─ data/                       原始输入数据
│  ├─ 附件1.xlsx              烘房温度与水分浓度
│  └─ 附件2.xlsx              药材半径随时间的变化
├─ src/                        求解源码
│  ├─ config.py               路径、初始条件与数值常量
│  ├─ models.py               环境、半径历程与求解结果数据结构
│  ├─ data_io.py              附件数据读取和输入校验
│  ├─ physics.py              物性参数与传热传质系数
│  ├─ solver.py               有限体积半离散与 BDF 积分
│  ├─ sampling.py             阈值判定、插值采样与网格误差
│  ├─ excel_output.py         四个规定结果工作簿的写入
│  ├─ plotting.py             论文图表生成
│  ├─ workflow.py             四问求解和结果汇总流程
│  ├─ sensitivity_analysis.py 参数敏感性分析
│  └─ drying_solver.py        兼容旧调用的统一接口
├─ result/                     汇总指标与校验记录
│  ├─ summary.json            论文表格、达标时间与网格检验汇总
│  ├─ parameter_sensitivity.json  参数敏感性结果
│  └─ validation.json         自动校验记录
├─ figures/                    论文高清图表（PNG、SVG、PDF 与说明文本）
├─ rebuild_figures.py          最新版论文图独立重绘脚本
├─ run_all.py                  一键复现主入口
├─ validate_results.py         结果完整性校验程序
├─ requirements.txt            Python 依赖版本
├─ AI工具使用详情.pdf          AI 工具使用场景、Prompt 与核验详情
├─ 支撑材料文件清单.pdf        提交文件目录结构与规范说明
└─ README.md                   支撑材料使用与复现指南
```

## 运行环境

- Python 3.12+
- Windows / macOS / Linux 跨平台兼容；程序路径处理与当前工作目录无关
- 依赖版本见 `requirements.txt`：
  - `numpy==2.5.3`
  - `scipy==1.18.1`
  - `openpyxl==3.1.5`
  - `matplotlib==3.11.1`

建议在本目录创建虚拟环境安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 一键复现

在本目录执行：

```bash
python run_all.py
```

程序依次完成四问数值求解、根目录下四个 Excel 结果导出、图表生成、参数敏感性分析和结果校验。正常结束时终端显示“复现完成”，并在 `result/validation.json` 中记录 `status: pass`。

如只需快速复现四问结果与图表，可跳过敏感性分析：

```bash
python run_all.py --skip-sensitivity
```

单独复核已有结果文件与时间边界：

```bash
python validate_results.py
```

## 数据与结果说明

- `data/附件1.xlsx` 和 `data/附件2.xlsx` 是程序运行所需的全部外部数据。
- `result1.xlsx`、`result2.xlsx` 位于根目录下，各含“温度”和“水分浓度”两个工作表；A 列为时间（s），首行为到药材中心的距离（cm）。
- `result3.xlsx`、`result4.xlsx` 位于根目录下，保存水分浓度；A 列为时间（s），首行为距离（cm）。问题四另含“药材表面”列，超出当时半径的固定空间位置留空。
- Excel 数值按题意保留四位小数；严格达标判据使用未舍入内部值。问题三在 207300 s 首次满足 60 s 输出网格上的最大水分浓度严格小于 0.15 kg/kg，内部值为 0.14998444；问题四对应 189780 s，内部值为 0.14999407。表中显示为 0.1500 是四舍五入造成的。
- 问题三、四的结果均在首个严格达标点后继续输出 1800 s，满足题目“不在 0.15 处立即停止”的要求。

## 图表说明

`figures/` 中包含论文实际引用的 10 组高清科学图，均与论文当前采用的绘图代码保持一致。温度热力图采用低温浅、高温深的连续色标，最高温端固定为 `#5202a3`；水分浓度热力图同样采用低值浅、高值深的连续色标。`drying_threshold` 呈现问题三全过程水分演化及达标点局部放大，`radius_and_comparison` 采用论文最终的三模型比较方案。每张图同时提供 600 dpi PNG、矢量 SVG 和矢量 PDF，并附带数据说明文本 TXT 与 `data_manifest.json`。

如需独立重绘论文图片而不重新运行全过程仿真，可在本目录执行：

```bash
python rebuild_figures.py --repo . --output figures
```

## 可复现性与校验范围

`validate_results.py` 自动检查：

1. 根目录下四个结果工作簿的工作表、表头、行列数和首末时间；
2. 问题三、四报告时点是否为 60 s 网格上的首个严格达标点；
3. 论文实际使用的 10 组图表及参数敏感性结果是否齐全。

`result/summary.json` 保存粗细网格对照、连续阈值时刻、论文代表点和求解器统计量，便于独立复核论文中的各项数值。
