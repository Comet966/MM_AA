# 论文实际使用图表

本目录仅收录论文正文实际引用的 10 张图。全部图形由支撑材料中的原始数据、数值结果和 `rebuild_figures.py` 生成，没有从旧图片反向取点。

## 图表清单

- `question1_profiles`
- `question1_heatmaps`
- `question2_profiles`
- `question2_heatmaps`
- `drying_threshold`
- `question3_heatmaps`
- `question4_heatmaps`
- `grid_convergence`
- `shrinkage_effect`
- `radius_and_comparison`

每张图提供以下文件：

- `.png`：600 dpi，供论文直接引用；
- `.svg`：可编辑矢量版本；
- `.pdf`：投稿用矢量版本；
- `.txt`：图形内容和读图说明。

温度场和水分浓度场均采用低值浅、高值深的连续色标，温度场最高值端固定为深紫色 `#5202a3`。`drying_threshold` 仅保留问题3曲线及其达标点局部图；`radius_and_comparison` 仅比较论文采用的三个模型。

在支撑材料根目录执行以下命令即可重新生成这 10 张图：

```powershell
python rebuild_figures.py --repo . --output report/figures
```
