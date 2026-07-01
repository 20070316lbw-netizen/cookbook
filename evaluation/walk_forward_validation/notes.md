# Walk-Forward Validation: 时序模型的"从头走到尾"回测协议

我记得的是"字母 F 开头, 叫 forward 什么什么", 查了一圈主流资料 (见
`sources.md`) , 对上号了: 这东西最常见的名字是 **walk-forward
validation/optimization**, 但确实有好几篇经典资料 (MachineLearningMastery、
一些时序 CV 的讨论) 把它就叫 **forward validation** 或 **forward
chaining**, 也有人叫 rolling-origin evaluation。 都是同一个概念, 完整代码
在 `code.py`。

---

## 1. 核心思路: 别随机切, 顺着时间走

```
train[0] -> test[0] -> train[1] -> test[1] -> ... -> test[-1]
```

跟 sklearn 的 k-fold 随机切完全不是一回事: 时序数据里"随机切"意味着训练集
里混进了比验证集更晚的样本, 模型能间接"看到未来" (哪怕只是通过同期的市场
状态), 这是时序/量化里最常见的泄漏源之一。 walk-forward 强制训练集永远
在测试集之前, 而且**反复做** (不是切一刀训一次, 是切好多刀走一遍) , 这样
每个时间段都被当过一次"样本外", 比单次 train/valid 切分更能反映模型在
不同市场环境下的真实表现。

`make_walk_forward_windows` 两种模式:

- `expanding=False` (rolling window, 默认): 训练窗口固定长度 `n_train`,
  跟着测试窗口一起平移。 假设越旧的数据参考价值越低 (跟
  `evaluation/concept_drift_ddgda/` 的动机一致) 。
- `expanding=True`: 训练窗口从头开始一直变长, 测试窗口平移。 假设数据
  no drift, 多多益善。

`step` 默认等于 `n_test`, 也就是测试块首尾相接、不重叠、不遗漏, 严格
"切成很多块从头走到尾"。 想要测试块之间有重叠 (比如每 5 天滚动一次但每次
测 20 天) , 把 `step` 设小于 `n_test` 就行。

## 2. 为什么加"信号 vs 噪音"检验

单跑一遍 walk-forward, 你会得到一个 "样本外 IC 均值"。 但这个数字本身
**不能告诉你它是不是运气**: 特征多、fold 少的时候, 纯噪声也能刷出一个
看着还行的正数 IC (尤其是量化数据信噪比低、单只股票样本量又不够大的时候)。

`signal_vs_noise_test` 的做法很直接: 既然想知道"这个 IC 是不是巧合",
就去看"如果 X 和 y 根本没关系, 这套流程 (同样的窗口切法、同样的模型、
同样的 fold 数) 能刷出多高的 IC"。 具体是把 `label_col` 整列打乱
(`rng.permutation`) , X 和索引都不动, 在同一套 walk-forward 协议上重跑
`n_shuffles` 次, 拿到一个"纯噪声" IC 的零分布, 然后看真实 IC 落在这个
分布的什么位置 (`p_value`) 。

自测结果 (`python code.py`) :

```
== 真信号 (y = Xβ + 噪声) ==
real IC = 0.9168  |  null IC 均值/标准差 = -0.0015 / 0.0120  |  p_value = 0.000

== 纯噪声 (y 与 X 无关) ==
real IC = -0.0037 |  null IC 均值/标准差 = -0.0003 / 0.0094  |  p_value = 0.667
```

真信号的 IC 远远甩开零分布 (`p_value≈0`) ; 纯噪声的 IC 本身就落在零分布
正中间 (`p_value≈0.67`, 比 0.5 高低都正常, 说明这个"IC"就是噪声波动)。
这就是这一篇要解决的问题: **一个孤零零的 IC 数字没有意义, 要跟它自己的
零分布比**。

## 3. 工程注意点

1. **打乱是"整列打乱", 不是分层打乱**。 这是故意的最狠零假设: 连时间结构
   一起打断。 更精细的做法 (比如只打乱同一天内的截面标签, 保留时间序列结构)
   能检验"是不是只学到了截面结构而非时序结构", 这里没做, 想要更细粒度的
   零假设设计参考 `sources.md` 里 López de Prado 的工作。
2. **retrain 成本**: `n_shuffles=30` 意味着要把整条 walk-forward 协议重跑
   30 遍, 如果 `train_fn` 是 LightGBM 而不是自测用的 OLS, 这个成本会明显
   上升。 工程上可以先用便宜模型 (线性/OLS) 做零假设检验的"预筛", 只有
   显著的信号再上重模型细调。
3. **fold 数不能太少**: 少于 5~6 个 fold 时, `real_metric` 本身的方差就很
   大, `p_value` 不稳定。 `n_train`/`n_test` 的选择要在"fold 数够多"和
   "训练集够长学得动"之间权衡, 跟 `evaluation/concept_drift_ddgda/` 里
   `train_window_days`/`test_window_days` 的取舍是同一个道理。
4. **`all_pred` 的开头一段永远是 NaN**: 前 `n_train` 天从来没有被任何
   test 窗口覆盖到 (它们只能当训练数据) , 这是正常现象不是 bug。

## 4. 跟 cookbook 内其他条目的关系

- `evaluation/concept_drift_ddgda/` 的 `rolling_walk_forward` 也是同一套
  "切块走到头"协议, 但那一篇把它跟"时间衰减样本权重"绑在一起, 目的是应对
  概念漂移。 这一篇把 walk-forward 单独抽出来做成通用协议 (`train_fn` /
  `predict_fn` 完全可插拔) , 再加上"信号 vs 噪音"的零分布检验, 两者可以
  合起来用 (drift 用 DDG-DA 的权重 schedule, 显著性用这一篇的检验)。
- `lightgbm/quant_pipeline_basics/` —— `fold_mean_ic` 跟那一篇的
  `daily_ic` 是同一件事, 只是这里聚合成单个 fold 的 float, 方便跨 fold
  汇总; `train_lgb` / `predict` 可以直接当 `train_fn`/`predict_fn` 传进来。
- `lightgbm/double_ensemble/` —— `train_double_ensemble` /
  `predict_double_ensemble` 签名不完全一样 (返回值是 tuple) , 需要包一层
  薄适配器再传给 `walk_forward_validate`。 组合示例见
  `lightgbm/demo_walk_forward.py`。
- `evaluation/alphalens_basics/` —— 那一篇诊断"IC 时序好不好", 这一篇回答
  更进一步的问题"这个 IC 是不是噪声", 两者可以串起来用。
