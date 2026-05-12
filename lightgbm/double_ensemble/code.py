"""
DoubleEnsemble (ICDM 2020) 的最小可跑实现, 从 qlib 的
qlib/contrib/model/double_ensemble.py 抽出来, 去掉 DatasetH / Reweighter / 日志
等 qlib 框架代码, 只留两块核心算法:

    1) SR (Sample Reweighting): 根据上一个 sub-model 的 "学习轨迹"
       (每个样本在每棵树之后的 loss) , 给难样本/噪声样本调权重重训。
    2) FS (Feature Selection): 把每一列特征 shuffle 一遍, 看 ensemble 的
       loss 变化多大 (类似 permutation importance), 然后分箱抽样组成下一轮
       sub-model 的特征子集。

输入接口故意做得简单 (X / y 都是 numpy / DataFrame, 不依赖 qlib),
所以你拿现成的 (X_train, y_train, X_valid, y_valid) 就能直接训。

跑通看自测: `python code.py` —— 会在合成数据上对比单棵 LGBM 和
DoubleEnsemble 的 RMSE 。 why 和坑看 notes.md 。
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd


DEFAULT_LGB_PARAMS: Dict[str, Any] = {
    "objective": "regression",
    "metric": "rmse",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "min_data_in_leaf": 20,
    "verbose": -1,
}


# =====================================================================
# 1) SR —— 样本重加权
# =====================================================================
# 论文 Algorithm 2。 直觉:
#   h1 = 当前 ensemble 对样本 i 的 loss 排名 (越大说明越难学)
#   h2 = 上一个 sub-model 训练过程里 , 这个样本 loss 的 "改进幅度"
#        (l_end / l_start , 越小说明这棵树越来越能拟合它 => 是好样本)
# 然后把 h = α1*h1 + α2*h2 分箱, 同一箱内的样本拿同一个权重,
# 权重和 h_avg 成反比 (难样本 / 不稳定样本 → 小权重, 让模型少看它们) 。

def sample_reweight(
    loss_curve: pd.DataFrame,
    loss_values: pd.Series,
    k_th: int,
    alpha1: float = 1.0,
    alpha2: float = 1.0,
    bins: int = 10,
    decay: float = 0.9,
) -> pd.Series:
    """
    Args:
        loss_curve:  (N, T) DataFrame, 上个 sub-model 在每棵树之后的样本 loss
        loss_values: (N,) Series, 当前 ensemble 对每个样本的 loss
        k_th:        当前 sub-model 的序号 (1-based) , 用来做 decay
        alpha1:      h1 (静态难度) 的权重
        alpha2:      h2 (轨迹改进) 的权重
        bins:        分箱数
        decay:       k_th 越大, 整体权重越平, 减少后期重加权的剧烈程度
    Returns:
        (N,) Series, 给 lgb.Dataset 的 weight=
    """
    # 按横向排名归一化, 让两个 h 在 [0,1] 上同尺度。
    # 注意: 这里用 loss_values.rank(pct=True) 而不是 qlib 当前版本里的
    # (-loss_values).rank(pct=True) 。 后者会让"高 loss 样本拿到 LOW h1 →
    # 拿到 LARGE weight", 即对难/噪声样本反而加权, 跟论文 Section 4 描述的
    # "downweight noisy samples" 是相反的。 详见 notes.md "qlib 实现的一处反号" 。
    loss_curve_norm = loss_curve.rank(axis=0, pct=True)
    loss_values_norm = loss_values.rank(pct=True)

    # h2 用 "前 10% 棵树的平均 loss" 当 l_start, "后 10% 棵树的平均 loss" 当 l_end
    N, T = loss_curve.shape
    part = max(int(T * 0.1), 1)
    l_start = loss_curve_norm.iloc[:, :part].mean(axis=1)
    l_end = loss_curve_norm.iloc[:, -part:].mean(axis=1)

    h1 = loss_values_norm
    h2 = (l_end / l_start).rank(pct=True)
    h = pd.DataFrame({"h_value": alpha1 * h1 + alpha2 * h2})

    # 分箱, 同箱共享同一个 1/(decay^k * h_avg + 0.1) 权重
    h["bins"] = pd.cut(h["h_value"], bins)
    h_avg = h.groupby("bins", group_keys=False, observed=False)["h_value"].mean()
    weights = pd.Series(np.zeros(N, dtype=float))
    for b in h_avg.index:
        weights[h["bins"] == b] = 1.0 / (decay**k_th * h_avg[b] + 0.1)
    return weights


# =====================================================================
# 2) FS —— 特征选择 (permutation 风味)
# =====================================================================
# 论文 Algorithm 3。 流程:
#   对每个特征 f , 把它 shuffle 一下 , 跑一遍 ensemble.predict ,
#   看新 loss 比原 loss 高多少 , 得到 g_value (信噪比形式) 。
#   g 越大说明这个特征越重要, 不能丢; g 越小说明它没用 (甚至有噪声) 。
# 然后按 g_value 分 bins_fs 个箱, 从大到小每个箱按 sample_ratios 抽样,
# 这样既保留了重要特征 , 又给低重要度的特征留了一点出场机会
# (经典 GBDT 调 colsample_bytree 的强化版) 。

def feature_selection(
    X: pd.DataFrame,
    y: np.ndarray,
    loss_values: pd.Series,
    ensemble: Sequence[lgb.Booster],
    sub_features: Sequence[pd.Index],
    bins: int = 5,
    sample_ratios: Sequence[float] = (0.8, 0.7, 0.6, 0.5, 0.4),
    rng: Optional[np.random.Generator] = None,
) -> pd.Index:
    """
    返回选中的特征列名 (pd.Index) , 用来训下一个 sub-model 。
    """
    if rng is None:
        rng = np.random.default_rng()
    if len(sample_ratios) != bins:
        raise ValueError("sample_ratios 长度必须等于 bins")
    features = X.columns
    N, F = X.shape
    M = len(ensemble)

    g_values = np.zeros(F)
    X_tmp = X.copy()
    for i_f, feat in enumerate(features):
        # shuffle 单列, 算 permuted 之后 ensemble 的样本 loss
        original = X_tmp[feat].values.copy()
        X_tmp[feat] = rng.permutation(original)

        pred = np.zeros(N)
        for sub, feats_sub in zip(ensemble, sub_features):
            pred += sub.predict(X_tmp[feats_sub].values) / M
        loss_feat = (y - pred) ** 2

        diff = loss_feat - loss_values.values
        # signal-to-noise: 平均提升 / 提升的波动, 比单看 mean 稳
        g_values[i_f] = diff.mean() / (diff.std() + 1e-7)

        X_tmp[feat] = original  # 还原

    g = pd.DataFrame({"g_value": np.nan_to_num(g_values, nan=0.0)})
    g["bins"] = pd.cut(g["g_value"], bins)

    # 从重要箱到次要箱依次按比例采, 拼起来去重
    sorted_bins = sorted(g["bins"].dropna().unique(), reverse=True)
    chosen: List[str] = []
    for i_b, b in enumerate(sorted_bins):
        feats_in_bin = features[g["bins"] == b]
        if len(feats_in_bin) == 0:
            continue
        n_take = int(np.ceil(sample_ratios[i_b] * len(feats_in_bin)))
        chosen += rng.choice(feats_in_bin, size=n_take, replace=False).tolist()
    return pd.Index(sorted(set(chosen)))


# =====================================================================
# 3) 取学习轨迹 loss_curve
# =====================================================================
# 在 LightGBM 里 , 训练完一个 Booster 之后 , 我们可以用 start_iteration /
# num_iteration 一棵树一棵树地拿当前累计预测值, 再算每棵之后的样本级 loss,
# 拼成 (N, num_trees) 的轨迹矩阵。 这是 SR 模块的输入。

def retrieve_loss_curve(model: lgb.Booster, X: pd.DataFrame, y: np.ndarray) -> pd.DataFrame:
    num_trees = model.num_trees()
    N = X.shape[0]
    curve = np.zeros((N, num_trees))
    pred_cum = np.zeros(N)
    X_values = X.values  # 提到循环外, num_trees 通常上百, 避免每棵都过一次 .values
    for t in range(num_trees):
        pred_cum += model.predict(X_values, start_iteration=t, num_iteration=1)
        curve[:, t] = (y - pred_cum) ** 2
    return pd.DataFrame(curve)


# =====================================================================
# 4) 主训练循环
# =====================================================================

def train_double_ensemble(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_valid: Optional[pd.DataFrame] = None,
    y_valid: Optional[np.ndarray] = None,
    *,
    num_models: int = 6,
    enable_sr: bool = True,
    enable_fs: bool = True,
    alpha1: float = 1.0,
    alpha2: float = 1.0,
    bins_sr: int = 10,
    bins_fs: int = 5,
    decay: float = 0.9,
    sample_ratios: Sequence[float] = (0.8, 0.7, 0.6, 0.5, 0.4),
    sub_weights: Optional[Sequence[float]] = None,
    params: Optional[Dict[str, Any]] = None,
    num_boost_round: int = 100,
    early_stopping_rounds: Optional[int] = None,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[List[lgb.Booster], List[pd.Index], List[float]]:
    """
    返回 (ensemble, sub_features, sub_weights) , 配合 predict_double_ensemble 用。

    Args (重点):
        num_models:       要训几个 sub-model (论文实验里 6 比较常见)
        enable_sr/_fs:    是否启用 SR / FS , 都关掉就退化成 num_models 个等权 LGBM
        sub_weights:      ensemble 投票权重 , 默认每个都 1
    """
    params = {**DEFAULT_LGB_PARAMS, **(params or {})}
    if rng is None:
        rng = np.random.default_rng()
    if sub_weights is None:
        sub_weights = [1.0] * num_models
    if len(sub_weights) != num_models:
        raise ValueError("sub_weights 长度必须等于 num_models")

    N = X_train.shape[0]
    weights = pd.Series(np.ones(N))
    features = X_train.columns
    pred_sub = np.zeros((N, num_models))

    ensemble: List[lgb.Booster] = []
    sub_features: List[pd.Index] = []

    for k in range(num_models):
        sub_features.append(features)

        # ---- 训 sub-model k (LightGBM, 带 sample weight) ----
        dtrain = lgb.Dataset(X_train[features], label=y_train, weight=weights.values)
        valid_sets, callbacks = [dtrain], [lgb.log_evaluation(period=0)]
        if X_valid is not None and y_valid is not None:
            valid_sets.append(lgb.Dataset(X_valid[features], label=y_valid, reference=dtrain))
            if early_stopping_rounds:
                callbacks.append(lgb.early_stopping(early_stopping_rounds, verbose=False))
        model_k = lgb.train(
            params, dtrain,
            num_boost_round=num_boost_round,
            valid_sets=valid_sets,
            callbacks=callbacks,
        )
        ensemble.append(model_k)

        # 最后一个 sub-model 不再需要更新 weights/features
        if k + 1 == num_models:
            break

        # ---- 算 loss_curve + 当前 ensemble 的 loss_values ----
        loss_curve = retrieve_loss_curve(model_k, X_train[features], y_train)
        pred_sub[:, k] = model_k.predict(X_train[features].values)
        # 加权平均: 截至 k 的 ensemble 预测
        w = np.array(sub_weights[: k + 1], dtype=float)
        pred_ensemble = pred_sub[:, : k + 1] @ w / w.sum()
        loss_values = pd.Series((y_train - pred_ensemble) ** 2)

        # ---- SR / FS 更新 ----
        if enable_sr:
            weights = sample_reweight(
                loss_curve, loss_values, k_th=k + 1,
                alpha1=alpha1, alpha2=alpha2, bins=bins_sr, decay=decay,
            )
        if enable_fs:
            features = feature_selection(
                X_train, y_train, loss_values, ensemble, sub_features,
                bins=bins_fs, sample_ratios=sample_ratios, rng=rng,
            )

    return ensemble, sub_features, list(sub_weights)


def predict_double_ensemble(
    ensemble: Sequence[lgb.Booster],
    sub_features: Sequence[pd.Index],
    sub_weights: Sequence[float],
    X: pd.DataFrame,
) -> np.ndarray:
    """加权平均所有 sub-model 的预测; 各 sub-model 看自己当时被选中的特征列。"""
    w = np.array(sub_weights, dtype=float)
    pred = np.zeros(X.shape[0])
    for sub, feats, wi in zip(ensemble, sub_features, w):
        pred += sub.predict(X[feats].values) * wi
    return pred / w.sum()


if __name__ == "__main__":
    # 合成数据: y = 真信号 + 噪声特征 + 一部分"难样本"完全是噪声驱动 ,
    # SR 应该能学会把这些难样本降权, FS 应该能学会把噪声特征丢掉。
    rng = np.random.default_rng(0)
    N, F_signal, F_noise = 4000, 5, 15
    X_signal = rng.normal(size=(N, F_signal))
    X_noise = rng.normal(size=(N, F_noise))
    X_all = np.hstack([X_signal, X_noise])
    cols = [f"s{i}" for i in range(F_signal)] + [f"n{i}" for i in range(F_noise)]
    X = pd.DataFrame(X_all, columns=cols)

    beta = rng.normal(size=F_signal)
    y_clean = X_signal @ beta + 0.3 * rng.normal(size=N)

    # 故意污染 15% 的样本: 标签换成纯噪声 , 模型再怎么学也学不会
    noisy_idx = rng.choice(N, size=int(0.15 * N), replace=False)
    y = y_clean.copy()
    y[noisy_idx] = rng.normal(scale=2.0, size=noisy_idx.size)

    # 时间切分 (随机切只为示例 , 量化里要按 date 切)
    split = int(N * 0.7)
    X_tr, X_va = X.iloc[:split], X.iloc[split:]
    y_tr, y_va = y[:split], y[split:]

    # 基线: 单棵 LightGBM
    base = lgb.train(
        DEFAULT_LGB_PARAMS,
        lgb.Dataset(X_tr, y_tr),
        num_boost_round=100,
        valid_sets=[lgb.Dataset(X_va, y_va)],
        callbacks=[lgb.log_evaluation(period=0)],
    )
    rmse_base = float(np.sqrt(np.mean((y_va - base.predict(X_va.values)) ** 2)))

    # DoubleEnsemble
    ens, feats, ws = train_double_ensemble(
        X_tr, y_tr, X_va, y_va, num_models=6, rng=rng,
    )
    pred_va = predict_double_ensemble(ens, feats, ws, X_va)
    rmse_de = float(np.sqrt(np.mean((y_va - pred_va) ** 2)))

    print(f"\n== single LGBM       RMSE = {rmse_base:.4f}")
    print(f"== DoubleEnsemble    RMSE = {rmse_de:.4f}")
    print(f"== sub-model 每轮选中的特征数: {[len(f) for f in feats]}")
