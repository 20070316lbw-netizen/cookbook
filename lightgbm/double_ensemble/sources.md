# 出处和参考

## 论文

- **DoubleEnsemble: A New Ensemble Method Based on Sample Reweighting and
  Feature Selection for Financial Data Analysis** (ICDM 2020)
  Chuheng Zhang, Yuanqi Li, Xi Chen, Yifei Jin, Pingzhong Tang, Jian Li
- arXiv: https://arxiv.org/abs/2010.01265
  - Algorithm 1 = 整体训练循环 (本仓库 `train_double_ensemble`)
  - Algorithm 2 = SR (本仓库 `sample_reweight`)
  - Algorithm 3 = FS (本仓库 `feature_selection`)
- 论文里的核心实验是在 Alpha158 + 中国股票 + LightGBM 上做的, 跟 qlib
  例子完全对得上。

## 官方实现 (qlib)

主要简化对象 —— 模型代码:

- `qlib/contrib/model/double_ensemble.py`
  https://github.com/microsoft/qlib/blob/main/qlib/contrib/model/double_ensemble.py
  - `class DEnsembleModel(Model, FeatureInt)` —— `code.py` 的全部函数都是
    从这里拆出来的, 对应关系:
    - `DEnsembleModel.fit`              ↔ `train_double_ensemble`
    - `DEnsembleModel.sample_reweight`  ↔ `sample_reweight`
    - `DEnsembleModel.feature_selection`↔ `feature_selection`
    - `DEnsembleModel.retrieve_loss_curve` ↔ `retrieve_loss_curve`
    - `DEnsembleModel.predict`          ↔ `predict_double_ensemble`
  - 原版依赖 `qlib.data.dataset.DatasetH` / `DataHandlerLP` 取数, 我直接换成
    `(X_train, y_train, X_valid, y_valid)` 的 plain pandas 接口。

跑通用的 example + 配置:

- `examples/benchmarks/DoubleEnsemble/`
  https://github.com/microsoft/qlib/tree/main/examples/benchmarks/DoubleEnsemble
  - `workflow_config_doubleensemble_Alpha158.yaml` —— 默认超参的实战配置:
    `num_models=6`, `enable_sr=True`, `enable_fs=True`, `decay=0.5`,
    `sample_ratios=[0.8,0.7,0.6,0.5,0.4]` 等, 是我代码里默认值的来源。
  - `README.md` —— qlib 例子 leaderboard 上 DoubleEnsemble 和单棵
    LightGBM 的指标对比 (Annualized Return / IR / MDD) , 看效果上限。

## LightGBM 文档 (我代码用到的 API)

- `lgb.train` / `Dataset(weight=...)`:
  https://lightgbm.readthedocs.io/en/latest/Python-API.html#lightgbm.train
  样本权重就是从这里塞进去的, SR 输出 `weights` 直接当
  `lgb.Dataset(..., weight=weights.values)` 用。
- `Booster.predict(start_iteration=, num_iteration=)`:
  https://lightgbm.readthedocs.io/en/latest/Python-API.html#lightgbm.Booster.predict
  `retrieve_loss_curve` 用这个一棵树一棵树地拿增量预测, 是 SR 模块的
  数据来源。
- `lgb.early_stopping` callback:
  https://lightgbm.readthedocs.io/en/latest/Python-Intro.html#early-stopping
  4.x 以后 `early_stopping_rounds=` 已经从 `lgb.train` 移到 callbacks 里。

## 跟我之前 ChatGPT/DeepSeek 给的方案比较

- "对残差再建模 (stacked) ": Wolpert (1992)
  https://www.sciencedirect.com/science/article/abs/pii/S0893608005800231
  —— 在金融数据上容易把噪声当结构, 见 López de Prado《Advances in Financial
  Machine Learning》第 7 章 "Cross-Validation in Finance" 警示。
- "把 lag 残差当特征": 经典 ARIMAX, 但量化里要小心 lag-1 残差需要 t 时刻的
  真实 y, 实操中容易写出未来信息泄漏。

## 同 cookbook 内的相关条目

- `lightgbm/quant_pipeline_basics/` —— 单棵 LGBM 的基线; 替换 `train_lgb`
  即可接 DoubleEnsemble。
- `lightgbm/train_function_template/` —— `code.py` 里 LightGBM 训练那一段
  (params 字典抽出来, callbacks 走 list) 的写法来自这一篇。
- `evaluation/alphalens_basics/` —— 用来诊断要不要上 DoubleEnsemble。
- `evaluation/concept_drift_ddgda/` —— 治本方案另一支 (针对分布漂移而不是
  样本噪声) 。
