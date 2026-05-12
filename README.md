# Cookbook

我的个人代码素材库,收集从各处学到的代码片段,改写成通用形式后归档。

## 结构

每个主题一个文件夹,每个具体技术一个子文件夹,包含:
- `code.py` — 通用化后的代码
- `notes.md` — 输入输出、关键细节、坑
- `sources.md` — 出处和参考链接

## 索引

- **duckdb/**
  - [`wide_to_long/`](duckdb/wide_to_long/) — 宽表 ↔ 长表 (UNPIVOT / melt) 与 qlib 风格 MultiIndex
- **pandas/**
  - [`rolling_windows/`](pandas/rolling_windows/) — 滚动窗口
- **lightgbm/**
  - [`train_function_template/`](lightgbm/train_function_template/) — 训练/预测函数模板,参数字典抽离
  - [`quant_pipeline_basics/`](lightgbm/quant_pipeline_basics/) — 量化最小可跑流水线 (qlib 简化版):打标签 / 写特征 / 训练 + IC 评估
  - [`double_ensemble/`](lightgbm/double_ensemble/) — DoubleEnsemble (ICDM 2020):样本重加权 (SR) + 特征选择 (FS) 治样本噪声
- **backtest/**
  - [`event_driven_loop/`](backtest/event_driven_loop/) — 事件驱动回测心跳 (zipline-reloaded 简化版):mark-to-market + rebalance
- **evaluation/**
  - [`risk_metrics/`](evaluation/risk_metrics/) — 业绩 / 风险指标 (empyrical-reloaded 简化版):年化收益 / 波动 / 夏普 / 最大回撤 / Calmar / Sortino
  - [`alphalens_basics/`](evaluation/alphalens_basics/) — 因子诊断核心 (Alphalens 简化版):IC / IR / 分位单调性 / 换手
  - [`concept_drift_ddgda/`](evaluation/concept_drift_ddgda/) — 概念漂移下的样本时间加权 (DDG-DA 简化版):walk-forward + 指数衰减权重
- **logging/**
  - [`loguru_basics/`](logging/loguru_basics/) — loguru 入门
- **git/**
  - [`connect_my_git/`](git/connect_my_git/) — 账号 / 命令配置
  - [`manage_code/`](git/manage_code/) — `.gitignore` 等