# A 题“药材的烘干问题”支撑材料

本目录用于复现四个问题的数值结果与论文图表。目录中仅保留复现所需的数据、程序、结果和图表。

## 目录结构

```text
支撑材料/
├─ data/                       原始输入数据
│  ├─ 附件1.xlsx              烘房温度与水分浓度
│  └─ 附件2.xlsx              药材半径随时间的变化
├─ src/                        求解源码
│  ├─ drying_solver.py        四问统一求解、结果导出与绘图
│  └─ sensitivity_analysis.py 参数敏感性分析
├─ result/                     数值结果
│  ├─ result1.xlsx            问题一完整结果
│  ├─ result2.xlsx            问题二完整结果
│  ├─ result3.xlsx            问题三完整结果
│  ├─ result4.xlsx            问题四完整结果
│  ├─ summary.json            论文表格、达标时间与网格检验汇总
│  ├─ parameter_sensitivity.json  参数敏感性结果
│  └─ validation.json         自动校验记录
├─ report/figures/             论文可用图表
├─ run_all.py                  一键复现入口
├─ validate_results.py         结果完整性校验
└─ requirements.txt            Python 依赖版本
```

## 运行环境

- Python 3.12
- Windows 11；程序路径处理与当前工作目录无关
- 依赖版本见 `requirements.txt`

建议在本目录创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 一键复现

在本目录执行：

```powershell
.\.venv\Scripts\python.exe run_all.py
```

程序依次完成四问求解、Excel 导出、图表生成、参数敏感性分析和结果校验。正常结束时终端显示“复现完成”，并在 `result/validation.json` 中记录 `status: pass`。

如只需快速复现四问结果与图表，可跳过敏感性分析：

```powershell
.\.venv\Scripts\python.exe run_all.py --skip-sensitivity
```

单独复核已有结果：

```powershell
.\.venv\Scripts\python.exe validate_results.py
```

## 数据与结果说明

- `data/附件1.xlsx` 和 `data/附件2.xlsx` 是程序运行所需的全部外部数据。
- `result1.xlsx`、`result2.xlsx` 各含“温度”和“水分浓度”两个工作表；A 列为时间（s），首行为到药材中心的距离（cm）。
- `result3.xlsx`、`result4.xlsx` 保存水分浓度；A 列为时间（s），首行为距离（cm）。问题四另含“药材表面”列，超出当时半径的固定空间位置留空。
- Excel 数值按题意保留四位小数；严格达标判据使用未舍入内部值。问题三在 207300 s 首次满足 60 s 输出网格上的最大水分浓度严格小于 0.15 kg/kg，内部值为 0.14998444；问题四对应 189780 s，内部值为 0.14999407。表中显示为 0.1500 是四舍五入造成的。
- 问题三、四的结果均在首个严格达标点后继续输出 1800 s，满足题目“不在 0.15 处立即停止”的要求。

## 图表说明

`report/figures` 中共 10 张 PNG：环境参数延拓、四问时空分布、代表点变化、达标判据、半径变化，以及问题四“收缩模型—附录 4 物性但固定半径”的对照图。温度热力图采用低温蓝、高温黄—橙—红的色序；水分热力图采用含水率越高颜色越深的色序。

## 可复现性与校验范围

`validate_results.py` 自动检查：

1. 四个结果工作簿的工作表、行列数和首末时间；
2. 问题三、四报告时点是否为 60 s 网格上的首个严格达标点；
3. 10 张图表及参数敏感性结果是否齐全。

`summary.json` 另保存粗细网格对照、连续阈值时刻、论文代表点和求解器统计量，便于独立复核论文中的数值。
