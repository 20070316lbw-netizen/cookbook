# 出处和参考

## zipline-reloaded —— 主要简化对象

- 仓库主页: https://github.com/stefan-jansen/zipline-reloaded

- **mark-to-market / daily return 公式** 的原型:
  - `src/zipline/finance/ledger.py` — `Ledger.update_portfolio` (≈ 666-697 行)
    , `end_value = cash + position_value; returns = pnl / start_value` 就在这里
    https://github.com/stefan-jansen/zipline-reloaded/blob/main/src/zipline/finance/ledger.py
  - 每根 bar 切分 daily return 的逻辑 (`start_of_session` 缓存
    `_previous_total_returns`, `todays_returns` 用 `(1+R)/(1+R_prev)-1` 还原
    单期收益) 也在同一文件 ~388 行

- **持仓 / 成本基更新** (我没抄进来的那一块, 留给后续扩展):
  - `src/zipline/finance/position.py` — `Position.update(txn)` , 体积加权
    平均成本的更新
    https://github.com/stefan-jansen/zipline-reloaded/blob/main/src/zipline/finance/position.py
  - `src/zipline/_protocol.pyx` 里的 `InnerPosition` 是 `Position` 的底层
    dataclass

- **Portfolio 数据结构** (`cash` / `portfolio_value` / `positions` 几个字段
  从哪来):
  - `src/zipline/protocol.py` — `class Portfolio` (≈ 115-181 行)
    https://github.com/stefan-jansen/zipline-reloaded/blob/main/src/zipline/protocol.py

- **持仓估值的聚合** (Σ shares × price × multiplier):
  - `src/zipline/finance/_finance_ext.pyx` —
    `calculate_position_tracker_stats` (≈ 114-244 行) ,
    填 `PositionStats.net_value` / `net_exposure`
    https://github.com/stefan-jansen/zipline-reloaded/blob/main/src/zipline/finance/_finance_ext.pyx

- **主循环** (我代码里 `run_backtest` 的 for-bar 对应) :
  - `src/zipline/gens/tradesimulation.py` — `AlgorithmSimulator.transform` ,
    按 `simulation_dt` 迭代, 在 `BEFORE_TRADING_START_BAR / BAR / SESSION_END`
    几种事件上各做一段动作
    https://github.com/stefan-jansen/zipline-reloaded/blob/main/src/zipline/gens/tradesimulation.py

- **下单接口** (`order_target_percent` 对应 `rebalance` 里的那行除法):
  - `src/zipline/algorithm.py` — `TradingAlgorithm.order_target_percent`
    https://github.com/stefan-jansen/zipline-reloaded/blob/main/src/zipline/algorithm.py

## 同 cookbook 内的相关条目

- `lightgbm/quant_pipeline_basics/` — 这里 `weights` 一般就是那一篇训出来的
  模型预测做横截面归一得到的, 信号 `shift(1)` 的理由也跟那里 `make_label`
  的 `gap=1` 是同一个 (不要用未来信息) 。
- `evaluation/risk_metrics/` — `run_backtest` 出来的 daily returns 直接喂
  给那一篇里的 `sharpe_ratio` / `max_drawdown` 就能出业绩报告。
