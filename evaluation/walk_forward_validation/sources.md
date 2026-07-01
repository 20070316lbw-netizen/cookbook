# 出处和参考

## 命名和概念确认

我一开始只记得"字母 F 开头, 叫 forward 什么什么", 查证下来这套协议在不同
资料里叫法不完全统一, 但都是同一件事:

- **Walk-Forward Validation / Optimization** —— 量化交易圈最常用的名字。
  - QuantInsti: "Walk-Forward Optimization: How It Works, Its Limitations,
    and Backtesting Implementation"
    https://blog.quantinsti.com/walk-forward-optimization-introduction/
  - Alpha Scientist: "Stock Prediction with ML: Walk-forward Modeling"
    https://alphascientist.com/walk_forward_model_building.html
- **Forward Validation** —— walk-forward 的常见别名, 机器学习时序预测
  资料里常这么叫 (对上了我最初的印象) 。
  - "Optimal model averaging based on forward-validation"
    https://www.sciencedirect.com/science/article/abs/pii/S030440762200094X
  - Tutorialspoint: "Time Series - Walk Forward Validation"
    https://www.tutorialspoint.com/time_series/time_series_walk_forward_validation.htm
- **Forward Chaining** —— 时序交叉验证语境下的另一个常见叫法, 强调"每次
  只用过去数据预测下一段, 链条式往前走"。
  - Analytics Vidhya: "Time Series Cross-Validation: Techniques &
    Implementation" https://www.analyticsvidhya.com/blog/2026/03/time-series-cross-validation/
  - MachineLearningMastery: "How To Backtest Machine Learning Models for
    Time Series Forecasting"
    https://machinelearningmastery.com/backtest-machine-learning-models-time-series-forecasting/
- **Rolling-Origin Evaluation / Rolling Window Analysis** —— 统计预测
  文献 (Hyndman 等) 里更学术的叫法, 概念一致。

## 官方实现参照 (qlib)

- `qlib/contrib/rolling/base.py` `class Rolling` —— walk-forward 的基类,
  跟 `evaluation/concept_drift_ddgda/` 里的 `rolling_walk_forward` 是同一个
  简化对象, 这一篇的 `make_walk_forward_windows` / `walk_forward_validate`
  是把同一套协议再抽成"跟模型解耦"的通用版本。
  https://github.com/microsoft/qlib/blob/main/qlib/contrib/rolling/base.py

## "信号 vs 噪音"检验的相关背景

- Marcos López de Prado, *Advances in Financial Machine Learning* —— 第 11
  章 "The Dangers of Backtesting" 和第 12 章 "Backtesting through
  Cross-Validation" 系统讲了"单个回测指标不可信, 要看它在零假设/多重检验
  下的分布"这一整套思路。 这一篇的 `signal_vs_noise_test` 是这个思想最简化
  的版本 (整列打乱 label 做 permutation test) , 完整版是他提出的
  Probability of Backtest Overfitting (PBO) / Combinatorial Purged
  Cross-Validation (CSCV) , 用组合切分而不是单纯打乱, 检验更严格。
  - `mlfinlab` 的 CSCV 实现 (第三方复现) :
    https://github.com/hudson-and-thames/mlfinlab
- White's Reality Check / Hansen's Superior Predictive Ability —— 更早的
  统计学工作, 讲"测了很多策略/参数组合后, 最好的那个到底是真的好还是选择性
  偏差", 跟这里"real IC vs null 分布"的思路同源。

## LightGBM / pandas API

- `numpy.linalg.lstsq` —— 自测用的最小二乘, 用来在不引入 sklearn 依赖的
  前提下给 `train_fn`/`predict_fn` 一个可跑的最小实现。
  https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html
- `numpy.random.Generator.permutation` —— 打乱 label 做零假设检验。
  https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.permutation.html

## 同 cookbook 内的相关条目

- `evaluation/concept_drift_ddgda/` —— 同一套 walk-forward 协议, 那一篇
  绑定了时间衰减权重 (解决概念漂移) , 这一篇是通用/可插拔版本 + 显著性检验。
- `lightgbm/quant_pipeline_basics/` —— `train_lgb`/`daily_ic` 可以直接
  当 `train_fn`/`metric_fn` 的具体实现传进来。
- `lightgbm/double_ensemble/` —— `train_double_ensemble` 需要包一层适配器
  才能塞进 `train_fn` 的签名, 见 `lightgbm/demo_walk_forward.py`。
- `evaluation/alphalens_basics/` —— IC/IR 的定义和这一篇 `fold_mean_ic`
  是同一套指标体系。
