# 业绩 / 风险指标 (empyrical 简化版)

empyrical-reloaded (zipline 配套的指标库) 把每个函数都写成「能吃 Series 也能
吃 DataFrame、 支持 daily/weekly/monthly 年化、 NaN 早退、 滚动窗口」 的
通用版, 翻起来全是 dispatch 。 这里把最常报的 6 个指标固定到「日频 + 252
交易日年化」, 公式跟 empyrical 一行行对得上, 留作回测后跑一遍出报告。

输入约定: `returns` 是 daily simple returns 的 `pd.Series` , index 为日期。
跟 `backtest/event_driven_loop/run_backtest` 的输出直接对接。

---

## 0. 年化常数

empyrical 的 `periods.py` 里:

```python
APPROX_BDAYS_PER_YEAR = 252
ANNUALIZATION_FACTORS = {DAILY: 252, WEEKLY: 52, MONTHLY: 12, ...}
```

A 股、 美股都按 252 (一年大概 252 个交易日) 。 改成周频 / 月频时只要换掉
这个常数, 公式本身不变。

## 1. 年化收益 (CAGR)

```python
ending = (1 + returns).prod()          # 累计 net wealth
n_years = len(returns) / 252
cagr = ending ** (1 / n_years) - 1
```

也就是「假设这段历史每年都按同一速度复利」反推出的年化。 注意**不是**
`returns.mean() * 252` —— 那个是算术年化, 会高估真实复利收益。

## 2. 年化波动率 (Lévy scaling)

```python
returns.std(ddof=1) * sqrt(252)
```

前提假设是「日收益独立同分布」, 此时方差线性叠加 ⇒ 标准差按 √T 缩放。
真实金融时间序列有自相关 / 厚尾, 这个公式是近似, 但全行业都这么报。

`ddof=1` 是样本方差 (除以 n-1), empyrical 用的就是这个 (`nanstd(ddof=1)`),
pandas `.std()` 也默认 `ddof=1` , 跟 numpy 默认 `ddof=0` 不一样。

## 3. 夏普比率

```python
adj = returns - risk_free            # 注意 risk_free 是 "每个周期" 的!
sharpe = adj.mean() / adj.std(ddof=1) * sqrt(252)
```

**最容易踩的坑**: `risk_free` 要传**每天**的无风险收益 (例如 4% 年化大致
对应 `0.04/252 ≈ 1.6e-4`) , 不能直接传 `0.04` , 否则分子被多扣 4% 一天,
夏普直接负到地心。 empyrical 的 docstring 也明确写了 `risk_free` per
period 。 入门一般直接 `risk_free=0` 报 "粗夏普" 就行。

## 4. 最大回撤

```python
cum = (1 + returns).cumprod()         # 净值曲线
peak = cum.cummax()                   # 历史最高点 (单调不减)
drawdown = (cum - peak) / peak        # ≤ 0
max_dd = drawdown.min()               # 通常是个负数
```

`cummax` 这个 trick 是关键: 它给出「截至每一天为止的历史最高净值」, 当前
净值减它再除它就是相对历史峰值跌了多少。 empyrical 在 `drawdown_series`
里用的是 `np.fmax.accumulate(out, axis=0)`, 行为一样, 是 numpy 版而已。

返回值固定是 ≤ 0 的负数。 报数时一般取绝对值 (例如 "max drawdown = 23%") 。

## 5. Calmar 比率

```python
calmar = annual_return / abs(max_drawdown)
```

夏普看的是「平均收益 vs 波动」, Calmar 看的是「年化收益 vs 最坏一次回撤」,
对回撤敏感的策略更有意义 (CTA、 趋势策略尤其) 。 max_dd ≥ 0 时返回 NaN
(没经历过回撤的话比率没意义) 。

## 6. Sortino 比率

```python
adj = returns - required_return
downside = sqrt(mean(min(adj, 0) ** 2)) * sqrt(252)
sortino  = adj.mean() * 252 / downside
```

跟 sharpe 唯一的差别: **分母只算下行波动**。 把 `adj` 里大于 0 的部分截
成 0, 再做 RMS 。 哲学是: 大涨不应该被当成"风险" 。

注意 empyrical 实现里 mean 是对**所有**样本 (包括上涨的那些日子) 做的,
不是只对下跌日做。 也就是说: 上涨日贡献 `0**2 = 0` 但仍然占分母的样本数。
这是 Sortino 经典定义, 不是 bug 。

## 7. 一键报告

```python
perf_summary(daily_returns).to_string(float_format=lambda x: f"{x: .4f}")
```

出来的 6 行就是量化 PPT 第一页常见的「年化收益 / 波动 / 夏普 / 最大回撤 /
Calmar / Sortino」, 跟 pyfolio (empyrical 的可视化层) `show_perf_stats`
的子集对应。 想画净值曲线、 回撤曲线再上 matplotlib , 这里不抢饭碗。

## 跟 empyrical 完整版差什么

| 这里没写              | empyrical 怎么处理                                  |
| --------------------- | --------------------------------------------------- |
| `period` 参数         | dispatch 到 `ANNUALIZATION_FACTORS[period]`         |
| DataFrame 输入        | 用 `axis=0` 一列一列广播                            |
| 滚动版 (rolling_*)    | 多了一份 `roll_sharpe_ratio` 等用 `bottleneck` 算   |
| NaN 早退              | `_create_unary_vectorized_roll_function` 里统一处理 |
| Omega / Information / Beta | 还有十几个不那么常用的指标                     |

读懂这 6 个之后, 再看 empyrical 源码就是「翻索引」 , 不是从零学。
