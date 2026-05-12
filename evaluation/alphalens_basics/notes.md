# Alphalens: 因子诊断标准指标

量化里"残差不是白噪声"光看 ACF/Ljung-Box 是不够的, 这些是时间序列统计指标,
**没回答"模型在实盘还能不能赚钱"**。 Alphalens 给出了一套因子级别的诊断
标准, 抄过来就能直接用在 LightGBM 模型的 `pred` 上 (预测值就是因子) 。

`code.py` 把 Alphalens 的核心五件事抠出来, 不依赖 alphalens 库本身
(原库依赖 ipython / matplotlib / pyfolio, 入门看不清主线) 。

---

## 数据契约

```
factor          : MultiIndex (date, asset) Series — 模型预测值 / 因子值
prices          : 宽表 DataFrame, index=date, columns=asset — 收盘价
forward_returns : MultiIndex (date, asset) DataFrame, columns=["1D","5D","10D"]
quantile        : MultiIndex (date, asset) Series — 横截面 N 分位 (1..N)
```

跟 `lightgbm/quant_pipeline_basics/` 的输出对齐, 拿过去 `pred` 就能丢进
`factor_tear_sheet` 。

---

## 1. 五件事

### 1.1 `compute_forward_returns(factor, prices, periods)`

把宽表价格打成 forward returns 的 MultiIndex DataFrame , 等价于
`alphalens.utils.compute_forward_returns` 。 核心三行就是:

```python
returns = prices.pct_change(period)
fwd     = returns.shift(-period).reindex(factor_dates)
```

`pct_change(p)` 已经是累计 p 日收益, 再 `shift(-p)` 把它对齐到 t 日 (t 日观测,
未来 p 日的收益) 。 原库还支持 cumulative=False / trading_calendar 推断,
不用先不抄。

### 1.2 `quantize_factor(factor, quantiles=5)` —— 横截面分位

**关键点**: 必须 `groupby("date")` 再 `qcut` 。 跨日期 qcut 等于在用整个样本
期的全局分布给单日打标签, 会让"全市场涨"的日子全跑到高分位 —— 这是入门
最常见的 bug 。 `duplicates="drop"` 是为了避免停牌日因子大部分相同时 qcut
报错。

### 1.3 `factor_ic(factor, forward_returns)` —— Spearman IC 时序

每天截面做 rank 相关, 输出 DataFrame `index=date, columns=horizon` 。
Alphalens 默认 Spearman (秩相关) 而不是 Pearson, 对极端值更稳健。 这里用
`rank().corr()` 等价实现, 不必拉 scipy 。

`ic_summary` 给五个数:
- `IC mean`: 平均预测力。 量化里 > 0.03 算"有信号", > 0.05 算很好。
- `IC std`: IC 的波动。
- `IR = IC mean / IC std`: 信息比率。 > 0.3 算不错, > 0.5 是顶级。
- `t-stat`: `IC mean / (IC std / sqrt(n))` , 看 IC 是不是统计显著的。
- `IC > 0 ratio`: 胜率, 看正负 IC 的分布偏不偏。

### 1.4 `mean_return_by_quantile(quantile, forward_returns)`

每个分位的平均未来收益 — 如果 1..5 单调递增, 而且 top-bottom spread 显著为
正, 因子就有用。 自测里 5 分位收益 -15bp → +28bp 单调递增, spread = 43bp,
意味着多空 long-short 组合每天能赚 43bp。

### 1.5 `factor_rank_autocorr(factor, period=1)` —— 换手指标

横截面 rank 在 t 日和 t-1 日的相关。 越接近 1 越稳, 越接近 0 越换手。

- ~0.95: 因子非常稳, 换手低, 交易成本友好
- ~0.5:  中等换手, 一般日频信号
- ~0:    每天重排, 换手爆炸, 实盘容易被手续费吃掉
- 负数:  反向相关, 大概率有 bug

我的自测里因子是每天独立采样的高斯, autocorr ≈ 0 是预期; 但模型的预测值
通常会有 0.7~0.9 的 autocorr (前后两天看到的特征只差一天) 。

---

## 2. 跟 ACF/Ljung-Box 残差诊断的区别

我最初问的是"模型残差不是白噪声怎么办"。 在统计里残差白噪声是模型
"穷尽了可预测部分"的判据, 但量化里:

- ACF/Ljung-Box 看的是**单一时间序列**的残差自相关 → 默认输入是一个 ts,
  没法直接处理 panel data (date × asset) 。
- 即便残差有自相关, 也可能是因为**截面强弱信号被时间序列混在一起**,
  IC 时序看起来稳定就没事。 反之残差白噪声但 IC 时序很差也照样亏钱。

所以量化里诊断模型, **先看 IC / IR / 分位单调性 / 换手, 再看残差统计指标**。
顺序反了容易踩"残差挺好但回测亏钱"的坑。

---

## 3. 工程坑

1. **MultiIndex 命名要严格**: `("date", "asset")` 是 Alphalens 的标准命名,
   qlib 用的是 `("datetime", "instrument")` 。 两个生态混着用时, 入口处
   rename 一次, 不要中间到处 swaplevel 。
2. **prices 的 index 要包含 factor.index 的所有日期 + 未来 N 天**。
   compute_forward_returns 需要看到 t+N 的价才能算 forward return; 截到
   t 就会丢一段尾部样本。
3. **不要把 forward_returns 直接当模型 label**。 forward_returns 在 t 日是
   未来 N 日的真实收益, 用来评估; label (训练用) 是同样的东西但训练时
   要小心 t-1 时刻是不是真的能看到这个值 (执行延迟) 。 见
   `lightgbm/quant_pipeline_basics/notes.md` 里的 `gap=1` 那一段。

---

## 4. 跟 cookbook 内其他条目的关系

- `lightgbm/quant_pipeline_basics/` —— 那一篇里 `daily_ic` 只算了 IC mean
  和 IR, 这一篇把指标族补齐: 分位单调性 + spread + autocorr。
- `lightgbm/double_ensemble/` —— 用 Alphalens 看完 IC 时序后, 如果发现
  某些时段 IC 很差 (噪声样本聚集), 先上 DoubleEnsemble。
- `evaluation/concept_drift_ddgda/` —— 看 IC 是否"近端好远端差", 是 DDG-DA
  最适用的信号。
- `evaluation/risk_metrics/` —— 因子诊断完了, 看 long-short 组合的夏普 / 回撤
  就是去那一篇。
