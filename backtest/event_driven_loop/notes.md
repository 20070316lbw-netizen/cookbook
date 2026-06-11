# 事件驱动回测的最小心跳 (zipline 简化版)

zipline-reloaded 完整跑一遍要拉 `TradingAlgorithm` + `TradingSimulation` +
`Ledger` + `PositionTracker` + `Blotter` 一堆类, 配上 bcolz / minute bundle 数据,
入门看着头大。 这里把"事件驱动"的内核压成一个小循环, 用纯 pandas 写,
方便对照官方源码学。 完整能跑代码在 `code.py` , 出处看 `sources.md` 。

数据假设: `prices` 是宽表 DataFrame, `index=date`, `columns=asset` , 元素是
当根 bar 的收盘价; `weights` 同形, 元素是目标权重 (long-only 时 ∈ [0, 1]) 。

---

## 1. 事件驱动到底是什么

「事件驱动」这个词在 zipline 里其实就是**一个 for 循环**: 每根 K 线 (一个
event) 触发一组动作。 zipline 的主循环在 `AlgorithmSimulator.transform`
(`gens/tradesimulation.py`) 里, 简化到只剩骨架就是:

```python
for dt, bar in data_portal:
    ledger.update_portfolio()      # 用最新价 mark-to-market
    algo.before_trading_start()    # 用户钩子: 生成信号
    algo.handle_data(data)         # 用户钩子: 下单 (写进 blotter)
    blotter.execute_orders()       # 撮合: 生成 transactions
    ledger.process_transactions()  # 把 transactions 落到 positions / cash
```

每个 bar 都做一遍 mark-to-market → 下单 → 成交 → 落账 , 这就是「事件驱动」。
跟向量化回测 (一次性 `(weights * returns).sum(axis=1)`) 比, 它的好处是:
能正确处理停牌 / 现金 / 滑点 / 手续费等所有「会改变持仓和价值」的事件。

`code.py` 里我把 5 步收成 2 步: `mark_to_market` + `rebalance` 。 没了 blotter、
没了用户钩子, 信号直接以「目标权重」形式从外面传进来。

## 2. mark-to-market: 怎么算 daily return

zipline 的核心公式在 `Ledger.update_portfolio` ( `finance/ledger.py` , 约 373-402 行) :

```python
start_value = portfolio.portfolio_value
portfolio.portfolio_value = end_value = portfolio.cash + position_value
pnl     = end_value - start_value
returns = pnl / start_value if start_value != 0 else 0.0
```

人话:

```
V_t = cash_t + Σ shares_i * price_i,t          # 今天的组合总价值
r_t = (V_t - V_{t-1}) / V_{t-1}                # 今天的收益率
```

注意持仓 `shares_i` 用的还是**昨天收盘后的持仓** (今天的调仓还没发生),
但价格用**今天**的, 差额就是 holding return 。 这一步必须先于 rebalance,
否则会把"今天调仓产生的"现金流计入今天的收益。

## 3. rebalance: 从目标权重到成交

zipline 的 `order_target_percent(asset, target)` 干的事是:

```
target_shares = target_weight * portfolio_value / price
delta_shares  = target_shares - current_shares
```

然后 `delta_shares` 走 `Blotter` 生成订单, 经过滑点 / 手续费模型变成
`Transaction`, 最后 `Ledger.process_transactions` 把它落到 `cash` 和
`positions` 上 (`Position.update` 还会更新成本基, 那块我没抄, 因为只算
returns 用不到) 。

简化版直接按当根 bar 收盘价成交:

```python
delta = target_shares - current_shares
self.cash -= delta * price
self.positions[asset] += delta
```

这一行就是「零滑点零手续费假设」下整个 finance 模块的总和。 真要做摩擦项,
再把 `delta * price` 改成 `delta * price + slippage(delta, price) + commission(...)`
即可, 接口完全一样。

## 4. 信号必须 shift(1) (回测里的"明天才能交易")

这是回测里最容易踩的坑, 和 `lightgbm/quant_pipeline_basics/` 里 `make_label`
的 `gap=1` 是同一回事。

- `weights.loc[t]` 是「在 t 日要持有的权重」
- 这个权重只能用 t 之前能看到的信息算出来
- 例: 用「过去 20 日动量」, 那 t 日的动量值你最早只能在 **t 日收盘后** 拿到 ,
  在 t 日盘中没法用它下单 ⇒ 必须 `weights.shift(1)` , 把它推迟到 t+1 才生效

向量化研究里大家经常忘记这一步, 然后看到夏普 5+ 沾沾自喜。 事件驱动版里
我把 shift 放在外面 (`run_backtest` 之前) , 因为这是**回测引擎的输入约定**:
传进来的 weights 必须是「今天就能照着下单的」, shift 的责任在调用者。

## 5. 不写的东西 (留给读者扩展)

| 没写             | 怎么加 (一句话)                                                       |
| ---------------- | ------------------------------------------------------------------- |
| 成本基 / unreal pnl | `Position.update` 那段, 我代码里 `positions` 只存股数, 没存 cost     |
| 滑点 / 手续费    | `rebalance` 里 `self.cash -= delta * price` 后面再扣一笔             |
| 多账户 / 多 ccy  | 把 `cash` 改成 dict 按账户存                                          |
| 分钟级           | 把 `prices.iterrows()` 换成分钟 bar 即可, ledger 不动                  |
| benchmark / 风险归因 | 在 `run_backtest` 外面拿 daily_returns 跟 `evaluation/risk_metrics/` 比 |

工业级 zipline 多出来的几千行, 基本都是在这五件事上的扩展, 不是另起炉灶。
看懂这五十行的心跳, 再去看 `ledger.py` 就是「找对应组件」而不是「啃整个框架」。
