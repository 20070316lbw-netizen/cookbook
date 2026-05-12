# DDG-DA: 概念漂移下的样本时间加权 (AAAI 2022, 精神简化版)

量化里很多模型的"残差不是白噪声"其实根本不是模型本身的问题, 而是
**训练集和测试集已经不是同一个分布了** (concept drift) 。 这种时候:

- 给残差再加 lag 特征 → 在新分布下没用, 还容易过拟合到老分布的伪信号。
- 上 DoubleEnsemble (`lightgbm/double_ensemble/`) → 它假设训练集内部有
  好/坏样本之分, 但漂移问题里"好样本"自己也漂走了, 解不对。
- **DDG-DA**: 根据数据分布演化趋势, **给老样本降权 / 给近样本升权**。

完整 DDG-DA 用一个 PyTorch 元学习器端到端学时间权重 schedule, 配套是
qlib + mlflow, 入门看不清主线。 `code.py` 留了三个核心环节:

1. **walk-forward rolling**: 跟 qlib 的 `RollingExperiment` 一样的回测协议。
2. **指数衰减权重 schedule**: `w(age) = 0.5 ^ (age / half_life)`,
   `half_life=inf` 退化为均匀权重。 直接灌进 `lgb.Dataset(weight=...)` 。
3. **"学"出 half_life 的网格搜版**: 在历史数据上切内部 walk-forward,
   选 RMSE 最小的 half_life 当下一段的 schedule。 这就是 DDG-DA 思想的
   极简版 —— 让数据自己告诉你衰减多快, 不要写死。

---

## 1. 跟完整 DDG-DA 的差距

| 维度 | 这里 (简化版) | DDG-DA 原版 |
|---|---|---|
| 权重形状 | 单参数指数 `2^(-age/HL)` | 任意形状, 每段历史时间一个权重 |
| 学习方式 | 网格搜单参数 | PyTorch 网络端到端学权重 |
| 优化目标 | 内部 walk-forward RMSE | IC loss (Spearman rank correlation) |
| 数据接口 | plain DataFrame | qlib MetaTaskDataset |
| 训练成本 | 几秒 (几个 LightGBM) | 几小时 (元学习 + 多次内部训练) |

简化版能 cover 80% 场景: **当漂移近似指数衰减时**, 单参数已经够用。
真要对付非平稳的、 突变的漂移 (比如政策窗口前后) , 才需要 DDG-DA 完整版
的可变形状权重。

---

## 2. 一个常见的反直觉点

**漂移并不总是"近的样本更好"**。 有时候市场会回到一个老的状态 (mean
reversion of regimes) , 这种时候"全部样本均匀" 反而比 "强衰减" 好。 这就是
为什么 DDG-DA 要学一个 schedule 而不是写死 half_life:

- 趋势性漂移 (β 缓慢游走): 短 half_life 赢
- regime-switching: 长 half_life / uniform 赢, 因为旧状态可能复现
- 完全随机突变 (财报暴雷): 谁都救不了, DDG-DA 论文也承认这一点

`learn_half_life` 在三种场景下分别会选出不同的 half_life, 这是它的价值。
我自测的 `_make_drift_data` 用的是随机游走的 β (典型趋势漂移) , 所以
half_life=60 赢了 uniform 。

---

## 3. walk-forward 协议的细节

```
fold 0:  train [t0, t0+W-1]  →  test [t0+W, t0+W+T-1]
fold 1:  train [t0+T, t0+W+T-1]  →  test [t0+W+T, t0+W+2T-1]
...
```

- `train_window_days=W` 固定: 每折训练样本数大致相等。
- `test_window_days=T`: 推进步长 = 测试段长度, 不重叠。
- 量化里常见 W=2 年 (~500 个交易日) , T=20 ~ 60 天 (一个月到一个季度) 。
- 想看到趋势漂移的影响, W 不能太短 (太短的话 uniform 也只看近期) 。

我用的是日历日 (`pd.Timedelta(days=W)`) 而不是交易日, 因为合成数据里
freq="B" 已经过滤了周末; 实盘要根据交易日历计数, qlib `RollingExperiment`
里也是按交易日。

---

## 4. 工程坑

1. **样本权重不要做 z-score / sum-to-1 标准化**。 LightGBM 的 weight 是按行
   线性放大梯度的, 缩放只影响学习率, 不影响排序。 强行 normalize 会让你
   误以为 "weights 都很小所以没生效"。
2. **age 用 (train_end - sample_date)**, 不是 (test_start - sample_date) 。
   后者会让最后一天的样本权重永远是 0.5^(1/HL) 而不是 1, 让 schedule
   整体偏一档。
3. **网格搜出来的 half_life 是用了"内部验证段"的信息**, 这部分数据不能再
   出现在最终 test 段里, 否则未来信息泄漏。 代码里 `inner_end < cursor` ,
   通过让 inner_start 也从 `dates[W]` 开始来保证。
4. **不要把 `half_life=0` 也放进候选**: 权重会变成
   `0.5^(age/0)` = 全 0, LightGBM 会拒绝训练。

---

## 5. 跟我之前问题的对接

我最初问"残差不是白噪声怎么办", 在量化里如果做完 `evaluation/alphalens_basics/`
诊断, 发现:

- IC 时序在最近一年一直 < 平均水平 → 概念漂移 → DDG-DA / 这一篇
- 整体 IC 不错但某些时段烂到爆 → 噪声样本聚集 → `lightgbm/double_ensemble/`
- IC 不错但残差有日内 / 周内自相关 → 大概率特征工程没做完, 不在这两篇范围

三者可以叠加: 先 DDG-DA 选权重 schedule (跨时段) , 再在每段 fold 里上
DoubleEnsemble (段内的样本质量) , 最后用 Alphalens 验证 IC 时序确实变稳。

---

## 6. 跟 cookbook 内其他条目的关系

- `lightgbm/quant_pipeline_basics/` —— 那一篇的 `train_lgb` 是单次训练,
  这一篇是把它包成 rolling-window 调用。
- `lightgbm/double_ensemble/` —— 治"段内的样本质量", 这一篇治"段间的分布
  漂移", 互补不冲突。
- `evaluation/alphalens_basics/` —— 判断要不要上这一篇的诊断信号
  ("IC 时序近端差远端好") 。
- `backtest/event_driven_loop/` —— 拿 walk-forward 的 prediction 接 backtest
  心跳的下一站。
