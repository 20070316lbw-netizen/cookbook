# 出处和参考

## empyrical-reloaded —— 主要简化对象

- 仓库主页: https://github.com/stefan-jansen/empyrical-reloaded
  (zipline-reloaded 作者维护的 empyrical 续作, 公式与原版 Quantopian
  empyrical 一致, 修了 numpy / pandas 新版兼容性)

- **所有 6 个指标的原始实现** 都在同一个文件:
  - `src/empyrical/stats.py`
    https://github.com/stefan-jansen/empyrical-reloaded/blob/main/src/empyrical/stats.py
    - `annual_return`             —— CAGR
    - `annual_volatility`         —— Lévy scaling
    - `sharpe_ratio`              —— `_adjust_returns` 处理 risk_free
    - `max_drawdown` / `drawdown_series` —— `np.fmax.accumulate` 的 cummax
    - `calmar_ratio`              —— `annual_return / abs(max_drawdown)`
    - `sortino_ratio` / `downside_risk` —— 只平方负值的 RMS

- **年化常数**:
  - `src/empyrical/periods.py` — `APPROX_BDAYS_PER_YEAR = 252` ,
    `ANNUALIZATION_FACTORS = {DAILY: 252, WEEKLY: 52, MONTHLY: 12, ...}`
    https://github.com/stefan-jansen/empyrical-reloaded/blob/main/src/empyrical/periods.py

## zipline-reloaded —— 业绩报告的调用方

- `src/zipline/finance/metrics/` 整个目录都在调 empyrical 算这些指标,
  逐 bar / 逐 session 累加到 `Tracker` 上, 最后写进回测输出 DataFrame
  的 `sharpe` / `max_drawdown` 列:
  https://github.com/stefan-jansen/zipline-reloaded/tree/main/src/zipline/finance/metrics

## pyfolio (Quantopian) —— 可视化层

- empyrical 是「算指标」 , pyfolio 是「把指标画成图 + 拼成报告」 :
  https://github.com/quantopian/pyfolio
  - `pyfolio.timeseries.perf_stats` 输出的就是这里 `perf_summary` 的超集

## 同 cookbook 内的相关条目

- `backtest/event_driven_loop/` — 那篇的 `run_backtest` 输出的 daily
  returns 直接喂进这里 `perf_summary` 就能出业绩。 两篇组合起来就是
  「事件驱动回测 + 业绩评估」的最小闭环 。
- `lightgbm/quant_pipeline_basics/` — 那里的 `daily_ic` 评估的是「模型
  预测力」 ( IC / IR ) , 这里评估的是「策略实盘表现」 (收益 / 风险) ,
  量化里这俩通常一起看 : IC 好但 Sharpe 烂, 一般是组合构建那一步出问题。
