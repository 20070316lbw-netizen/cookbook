# DoubleEnsemble: 样本重加权 + 特征选择 (ICDM 2020)

金融数据信噪比低, 单个 LightGBM 在残差里经常残留两类问题:

1. **样本噪声**: 有些样本 (突发事件 / 标签噪声) 怎么训都拟合不进去, 反而干扰
   树的分裂方向。
2. **冗余特征**: 几十上百个因子里相当多其实只是噪声 ,
   `feature_fraction` 这种全局采样治标不治本。

DoubleEnsemble 的做法是 **训 K 个 sub-model , 每训完一个就根据"学习轨迹"
更新样本权重 (SR) 和特征子集 (FS) , 然后训下一个**, 最后 ensemble 起来。
完整代码在 `code.py` , 出处在 `sources.md` 。

---

## 1. SR (Sample Reweighting) —— 把难/噪声样本降权

核心是给每个样本算一个 h-value, 越大说明这个样本越"该降权":

```
h_value = α1 * h1 + α2 * h2
    h1 = rank(当前 ensemble loss)         # 当前 loss 大 → h1 大 → 降权
    h2 = rank(l_end / l_start)            # 训练过程中 loss 没怎么降 (>=1 甚至升) → h2 大 → 降权
```

- `h1` 大: 当前模型在这个样本上 loss 大, 是个难样本。
- `h2` 大: 上一棵 sub-model 训练过程里这个样本的 loss 一直降不下来,
  说明它在学习轨迹上"不稳" —— 大概率是噪声而不是难特征样本。
- 两者加权后分箱 (`bins_sr=10`) , 同一箱共享一个权重, 权重和 `h_avg` 成反比:

```
weights[bin] = 1 / (decay^k * h_avg + 0.1)
```

`decay < 1`, k 越往后整体权重越平 , 防止后期把权重压得过于极端。

### qlib 实现的一处反号

qlib `qlib/contrib/model/double_ensemble.py` 里 h1 写的是
`loss_values_norm = (-loss_values).rank(pct=True)` , 加了负号。 加了负号之后,
**高 loss 样本拿到 LOW h1**, 由于最终权重是 `1 / (decay^k * h_avg + 0.1)`,
等于给难/噪声样本反而加大了权重 (AdaBoost 风格的"focus on hard")。 但论文
Section 4 明说是要 **降低噪声样本权重** , 跟 qlib 的实际效果方向相反。

这一篇 code.py 按论文意图实现 (无负号) , 跟 qlib 当前版本不一致。 想看 qlib
原貌的话: 把 `loss_values.rank(pct=True)` 换回 `(-loss_values).rank(pct=True)`
就行。 我没在原仓库 issue 里找到这个分歧的讨论, 可能确实是 qlib 一处长存
的 sign error, 也可能我对论文 Algorithm 2 的解读有偏差。 用的时候建议两版
都跑一下回测对比。

### 一个常被踩的坑

`loss_curve` 是 (N, num_trees) 矩阵: **每棵树之后**每个样本的 loss 。 不是
LightGBM 自带的 `evals_result` (那是 epoch 级聚合) 。 拿这玩意得手动循环
`model.predict(X, start_iteration=t, num_iteration=1)` 一棵一棵累加预测
(代码里的 `retrieve_loss_curve`) 。

---

## 2. FS (Feature Selection) —— 把噪声特征降权 / 丢掉

逐列 shuffle, 看 ensemble 的样本 loss 上升多少, 用信噪比形式衡量重要性:

```
g_value = mean(loss_shuffled - loss_orig) / (std(loss_shuffled - loss_orig) + 1e-7)
```

`mean(diff)` 大且 `std(diff)` 小, 说明这个特征对样本 loss 有稳定的正向贡献 ,
留下来; 反之是噪声特征。 然后按 `g_value` 分 `bins_fs=5` 箱, 从最重要的箱
开始按 `sample_ratios=(0.8, 0.7, 0.6, 0.5, 0.4)` 抽 , 拼成下一轮的特征集。

这等价于"按重要性分层的 colsample_bytree", 比 LightGBM 自带的全局随机采样
更有目的性。

### 工程注意点

- FS 是 `O(F * N)` 的 predict 调用, 特征多时贵。 代码里 `enable_fs=False`
  可以单独关掉, 只用 SR 也能拿到一部分增益。
- shuffle 是 in-place 改列再还原, 不要 deep-copy 整个 X (在 100w * 200 维
  上会爆内存) 。

---

## 3. 主循环

```
for k in 1..K:
    sub_k = train_lgb(X[:, features], y, weight=weights)
    if k == K: break
    loss_curve  = retrieve_loss_curve(sub_k, X, y)
    pred_ens    = weighted_avg(sub_1..sub_k)
    loss_values = (y - pred_ens)^2
    weights  = sample_reweight(loss_curve, loss_values, k)   # SR
    features = feature_selection(X, y, loss_values, ensemble) # FS
predict: 加权平均所有 sub-model
```

K (`num_models`) 一般 6, 论文消融 4~8 都行, 再多边际收益就掉了。

---

## 4. 跟我之前问题的对接

我最初问的是"残差不是白噪声怎么办":

- ChatGPT 说"对残差再建个模 (stacked) " → 治标。 因为如果残差里的结构来自
  少数噪声样本, stacking 会把这些噪声当信号继续学。
- DeepSeek 说"把 lag 残差当特征" → 治标, 还容易引入未来信息泄漏 (lag-1 残差
  在 t 时刻其实需要看到 t 的真实 y, 但量化里 t 时刻 y 未知) 。
- DoubleEnsemble 是**治本**: 直接在原任务上识别哪些样本/特征不可靠, 把它们
  在训练时降权。 它不假设残差本身有结构, 而是假设训练集里混了不同质量的样本。

在我自测的合成数据上 (15% 样本标签纯噪声) , DoubleEnsemble 的 RMSE 比单棵
LightGBM 略好。 在真实的 Alpha158 + 中国股票上, 论文报的 Sharpe 提升是
~20%, 大头来自 SR 把那些 "市场状态突变期" 的样本权重压下去了。

---

## 5. 跟 cookbook 内其他条目的关系

- `lightgbm/quant_pipeline_basics/` —— 那一篇里 `train_lgb` 是单棵 LGBM 的
  最小流水线。 这一篇相当于把那个 `train_lgb` 替换成 `train_double_ensemble`,
  其他 (`make_label`/`make_features`/`daily_ic`) 都不动。
- `evaluation/alphalens_basics/` —— 用 Alphalens 看完 IC 时序、 IR 之后,
  如果发现 IC 在某些时段特别差 (噪声样本聚集) , 先上 DoubleEnsemble 而不是
  急着改特征。
- `evaluation/concept_drift_ddgda/` —— 如果发现"近端 IC 一直好, 远端 IC
  一直差", 那是分布漂移, DDG-DA 更对症; DoubleEnsemble 处理的是
  "同分布内的样本质量不均"。 两者可以叠加。
