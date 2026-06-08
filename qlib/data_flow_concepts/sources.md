# 出处和参考

读 microsoft/qlib 官方文档整理的整体架构与数据流。

## qlib 文档
- 仓库主页：https://github.com/microsoft/qlib
- 框架总览（Workflow：Data → Model → Strategy → Backtest）：
  https://qlib.readthedocs.io/en/latest/introduction/introduction.html
- Workflow / `qrun` 与 YAML 配置：
  https://qlib.readthedocs.io/en/latest/component/workflow.html
- 各组件文档：Data Handler / Dataset / Model / Strategy / Backtest / Record：
  https://qlib.readthedocs.io/en/latest/component/

## qlib 源码（示例代码对应处）
- `qlib/contrib/data/handler.py` —— `Alpha158` / `Alpha360`
- `qlib/contrib/model/gbdt.py` —— `LGBModel`
- `qlib/contrib/strategy/` —— `TopkDropoutStrategy`
- `qlib/workflow/record_temp.py` —— `SignalRecord` / `PortAnaRecord`

## 同 cookbook 内的相关条目
- `qlib/factor_engine/` / `qlib/expression_internals/` —— 数据流里「因子计算」那一段的细节
- `lightgbm/quant_pipeline_basics/` —— 这条流水线的纯 pandas 简化版
