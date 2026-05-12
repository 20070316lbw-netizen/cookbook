# 出处和参考

## Alphalens (Quantopian)

主要简化对象。 仓库本身已经在 Quantopian 倒闭后转为社区维护, 原仓库仍可用:

- 仓库: https://github.com/quantopian/alphalens
- 关键文件:
  - `alphalens/utils.py`
    https://github.com/quantopian/alphalens/blob/master/alphalens/utils.py
    - `compute_forward_returns(factor, prices, periods=...)` (大约第 216 行)
      —— `code.py` 同名函数的原型, 去掉了 cumulative_returns / filter_zscore /
      自动 trading calendar 等开关。
    - `quantize_factor(factor_data, quantiles=5, ...)` (大约第 85 行)
      —— `code.py` 同名函数的原型, 去掉了 zero_aware / by_group / bins 模式。
    - `get_clean_factor_and_forward_returns(...)` (大约第 666 行)
      —— 原库的一站式入口, 我代码里没单独抄, 拆成了 compute_forward_returns +
      quantize_factor 两步, 更好理解。
  - `alphalens/performance.py`
    https://github.com/quantopian/alphalens/blob/master/alphalens/performance.py
    - `factor_information_coefficient(factor_data)` (第 28 行起)
      —— 用 `scipy.stats.spearmanr` 算逐日 Spearman 相关。
      `code.py` 的 `factor_ic` 用 `rank().corr()` 等价实现, 省一个 scipy 依赖。
    - `mean_return_by_quantile(factor_data, ...)` (第 453 行起)
      —— `code.py` 同名函数的原型, 我去掉了 demeaned / group_adjust /
      by_date 选项。
    - `factor_rank_autocorrelation(factor_data, period=1)` (第 601 行起)
      —— 用 `pivot + corrwith` 算横截面排名自相关。 `code.py` 用 `unstack`
      等价。
  - `alphalens/tears.py` —— 一站式 tear sheet, 出 ~20 张图; 我没抄进来,
    只抄了核心的五个表的 `factor_tear_sheet` 。

## 同类工具 (备查)

- **qlib 的 SignalRecord**: `qlib/workflow/record_temp.py` 里的
  `SignalRecord` / `SigAnaRecord` 也算 IC / IR / Rank IC, 但接口是 qlib
  特有的 (跟 mlflow 绑定) 。 出处:
  https://github.com/microsoft/qlib/blob/main/qlib/workflow/record_temp.py
- **empyrical-reloaded**: 收益/风险指标, 跟 alphalens 互补, 看
  `evaluation/risk_metrics/` 。

## pandas API (我代码里关键的几个调用)

- `pd.DataFrame.pct_change(period)` + `shift(-period)`:
  https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pct_change.html
- `pd.qcut(x, q, labels=False, duplicates="drop")`:
  https://pandas.pydata.org/docs/reference/api/pandas.qcut.html
  `duplicates="drop"` 是处理"当日因子大部分相同 (停牌等)"时 qcut 报错的
  标准方案。
- `DataFrame.corrwith(other, axis=1)`:
  https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.corrwith.html
- `Series.unstack()` / `stack(future_stack=True)`:
  pandas 3.0 后 `stack()` 默认行为变了, 加 `future_stack=True` 用新行为,
  否则会报 FutureWarning 。

## IC 指标的标准参考 (背景知识)

- Grinold & Kahn《Active Portfolio Management》Ch. 6 "Information Ratio"
  —— IR 概念出处, 量化里 IC mean / IC std 的解释直接套用了 IR 的公式。
- López de Prado《Advances in Financial Machine Learning》Ch. 8
  "Feature Importance" —— 提醒不要单独看 IC mean, 要看 IC 的时序稳定性,
  对应 `ic_summary` 里的 IR 和 t-stat 列。

## 同 cookbook 内的相关条目

- `lightgbm/quant_pipeline_basics/` —— `daily_ic` 是 `factor_ic` 的极简版,
  那一篇也讲过 Alphalens 的 `get_clean_factor_and_forward_returns` 跟这里
  的关系。
- `lightgbm/double_ensemble/` —— 看完 IC 时序发现"有些时段噪声重", 是上
  DoubleEnsemble 的信号。
- `evaluation/concept_drift_ddgda/` —— 看 IC "近端好远端差" 是上 DDG-DA 的
  信号。
- `evaluation/risk_metrics/` —— 因子诊断完之后看实盘风险指标的下一站。
- `duckdb/wide_to_long/` —— prices 宽表 → MultiIndex 长表的转换 (这里
  `compute_forward_returns` 里 stack 那一步) , 详细写在那一篇。
