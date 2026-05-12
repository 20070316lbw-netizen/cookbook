"""
DDG-DA (AAAI 2022) 的"精神简化版" —— 用时间衰减权重做 rolling-window 训练,
对比 uniform vs. 指数衰减 vs. 用元模型学到的衰减形状, 看在概念漂移下哪个赢。

完整 DDG-DA 流程依赖 qlib + pytorch + meta-learning 元数据流, 入门看不清主线
(见 sources.md 里 qlib 那 600 行) 。 这里只保留两个核心环节:

    1) rolling-window 训练: 每次只用过去 W 天训, 预测下一段 T 天, 走完一轮
       推进 T 天, 标准 walk-forward 。
    2) sample weight schedule: 给历史样本一个时间衰减权重 (越近越重) 。
       - "uniform"   : 全部 1
       - "exp(half)" : 指数衰减, 半衰期参数化
       - "learned"   : 简单元学习 —— 在一组历史 rolling 折上, 网格搜出最好的
                       半衰期, 当作下一段的权重 schedule (DDG-DA 用神经网络
                       端到端学这个 schedule, 这里用网格搜化简) 。

跑通看自测: `python code.py` —— 在故意做了 concept drift 的合成数据上
对比三种 schedule 的 RMSE 。 why 和坑看 notes.md , 完整 DDG-DA 出处看 sources.md 。
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd


# =====================================================================
# 1) 时间衰减权重 schedule
# =====================================================================
# DDG-DA 学的是"对每段历史时间分配多少权重", 然后把权重灌进 LightGBM 的
# sample_weight 。 这里我们把"形状"参数化为 half_life (单位: 天) :
#       w(age) = 0.5 ^ (age / half_life)
# half_life = +inf 退化为均匀权重。

def exp_decay_weights(ages_in_days: np.ndarray, half_life: float) -> np.ndarray:
    if not np.isfinite(half_life):
        return np.ones_like(ages_in_days, dtype=float)
    return 0.5 ** (ages_in_days / half_life)


# =====================================================================
# 2) 单步训练 + 预测 (一次 rolling fold)
# =====================================================================

DEFAULT_LGB_PARAMS: Dict = {
    "objective": "regression",
    "metric": "rmse",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "feature_fraction": 0.9,
    "min_data_in_leaf": 20,
    "verbose": -1,
}


def train_predict_fold(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_test: pd.DataFrame,
    weights: Optional[np.ndarray] = None,
    params: Optional[Dict] = None,
    num_boost_round: int = 200,
) -> np.ndarray:
    """单段 train + 单段 predict, weights 灌进 lgb.Dataset 。"""
    params = {**DEFAULT_LGB_PARAMS, **(params or {})}
    dtrain = lgb.Dataset(X_train, label=y_train, weight=weights)
    model = lgb.train(
        params, dtrain,
        num_boost_round=num_boost_round,
        callbacks=[lgb.log_evaluation(period=0)],
    )
    return model.predict(X_test.values)


# =====================================================================
# 3) walk-forward rolling backtest
# =====================================================================
# 输入是 panel data (date × asset) , 每次拿 train_window 天训, 预测后面
# test_window 天, 然后整体推进 test_window 天。 跟 qlib 的 RollingExperiment
# 一致 (qlib/contrib/rolling/base.py) 。

@dataclass
class FoldResult:
    fold_idx: int
    train_start: pd.Timestamp
    train_end:   pd.Timestamp
    test_start:  pd.Timestamp
    test_end:    pd.Timestamp
    rmse: float
    n_train: int
    n_test: int


def rolling_walk_forward(
    df: pd.DataFrame,
    feat_cols: List[str],
    label_col: str,
    train_window_days: int,
    test_window_days: int,
    weight_schedule: Callable[[np.ndarray], np.ndarray],
    start: Optional[pd.Timestamp] = None,
) -> Tuple[List[FoldResult], pd.Series]:
    """
    Args:
        df: MultiIndex (datetime, instrument) DataFrame, 含 feat_cols + label_col
        weight_schedule: 接收 ages_in_days (numpy 数组) , 返回同长度的权重数组
    Returns:
        folds: 每段 fold 的结果
        all_pred: MultiIndex 一致的预测 Series
    """
    dates = df.index.get_level_values("datetime").unique().sort_values()
    if start is None:
        start = dates[train_window_days]

    folds: List[FoldResult] = []
    all_pred = pd.Series(np.nan, index=df.index, dtype=float)
    cursor = start
    i = 0
    while True:
        train_end = cursor - pd.Timedelta(days=1)
        train_start = train_end - pd.Timedelta(days=train_window_days - 1)
        test_start = cursor
        test_end = cursor + pd.Timedelta(days=test_window_days - 1)
        if test_end > dates[-1]:
            break

        dt = df.index.get_level_values("datetime")
        m_train = (dt >= train_start) & (dt <= train_end)
        m_test  = (dt >= test_start) & (dt <= test_end)
        train, test = df.loc[m_train], df.loc[m_test]
        if train.empty or test.empty:
            cursor = test_end + pd.Timedelta(days=1)
            i += 1
            continue

        ages = (train_end - train.index.get_level_values("datetime")).days.values.astype(float)
        weights = weight_schedule(ages)

        pred = train_predict_fold(
            train[feat_cols], train[label_col].values,
            test[feat_cols], weights=weights,
        )
        all_pred.loc[test.index] = pred
        rmse = float(np.sqrt(np.mean((test[label_col].values - pred) ** 2)))
        folds.append(FoldResult(i, train_start, train_end, test_start, test_end,
                                rmse, len(train), len(test)))

        cursor = test_end + pd.Timedelta(days=1)
        i += 1

    return folds, all_pred


# =====================================================================
# 4) "学" 一个 half_life —— 简化版 DDG-DA
# =====================================================================
# DDG-DA 用一个 PyTorch 网络端到端学权重 schedule。 这里用网格搜:
#   - 把"训练区间"再切出一个内部验证段
#   - 对一组候选 half_life 跑一遍内部 walk-forward
#   - 选内部平均 RMSE 最小的那个 half_life , 作为最终用的 schedule
# 跟 DDG-DA 的差距在: DDG-DA 学的是不规则的"每段时间一个权重"形状, 我们
# 这里只学单参数指数。 想法是一样的: 让数据本身告诉你怎么衰减。

def learn_half_life(
    df: pd.DataFrame,
    feat_cols: List[str],
    label_col: str,
    train_window_days: int,
    test_window_days: int,
    candidates: Tuple[float, ...] = (30, 60, 120, 240, 480, np.inf),
    n_inner_folds: int = 3,
) -> Tuple[float, pd.DataFrame]:
    """在历史数据上网格搜最优 half_life , 返回 (best_hl, 各候选 RMSE 表) 。"""
    dates = df.index.get_level_values("datetime").unique().sort_values()
    # 内部 walk-forward 的起点比正式回测早 n_inner_folds * test_window
    inner_start = dates[train_window_days]
    inner_end = dates[train_window_days + n_inner_folds * test_window_days]

    dt = df.index.get_level_values("datetime")
    inner_df = df.loc[(dt >= dates[0]) & (dt <= inner_end)]

    rows = []
    for hl in candidates:
        schedule = lambda ages, hl=hl: exp_decay_weights(ages, hl)
        folds, _ = rolling_walk_forward(
            inner_df, feat_cols, label_col,
            train_window_days, test_window_days,
            weight_schedule=schedule,
            start=inner_start,
        )
        rmses = [f.rmse for f in folds]
        rows.append({"half_life": hl, "mean_rmse": np.mean(rmses), "n_folds": len(folds)})

    table = pd.DataFrame(rows).sort_values("mean_rmse")
    best_hl = float(table.iloc[0]["half_life"])
    return best_hl, table


# =====================================================================
# 自测: 合成 concept drift 数据
# =====================================================================
# 设定: y = β(t)·X + 噪声 , β(t) 随时间漂移。
# 训练集里看到的 β 跟测试集的 β 已经不同 ; 老样本对最近预测越没用。
# 预期: half_life 有限的 schedule 优于 uniform 。

def _make_drift_data(
    n_dates: int = 600,
    n_assets: int = 30,
    n_features: int = 8,
    drift_speed: float = 0.02,
    seed: int = 0,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-01", periods=n_dates, freq="B")
    assets = [f"S{i:02d}" for i in range(n_assets)]
    mi = pd.MultiIndex.from_product([dates, assets], names=["datetime", "instrument"])

    X = rng.normal(size=(n_dates * n_assets, n_features))
    feat_cols = [f"f{i}" for i in range(n_features)]
    df = pd.DataFrame(X, index=mi, columns=feat_cols)

    # 每日 β 做一次随机游走, 形成缓慢漂移
    beta0 = rng.normal(size=n_features)
    walks = rng.normal(size=(n_dates, n_features)) * drift_speed
    beta_t = beta0 + np.cumsum(walks, axis=0)
    # 把 beta 按 datetime 广播到样本
    beta_per_row = pd.DataFrame(beta_t, index=dates, columns=feat_cols).reindex(
        df.index.get_level_values("datetime")
    ).values
    signal = (df.values * beta_per_row).sum(axis=1)
    noise = rng.normal(size=signal.shape) * 0.3
    df["y"] = signal + noise
    return df


if __name__ == "__main__":
    df = _make_drift_data(drift_speed=0.02)
    feat_cols = [c for c in df.columns if c != "y"]
    TRAIN_W, TEST_W = 200, 40  # 训练用 200 天, 滚动测 40 天

    # (a) uniform —— 不衰减
    folds_u, _ = rolling_walk_forward(
        df, feat_cols, "y", TRAIN_W, TEST_W,
        weight_schedule=lambda ages: exp_decay_weights(ages, np.inf),
    )
    rmse_u = np.mean([f.rmse for f in folds_u])

    # (b) 手动选 half_life=60 天
    folds_e, _ = rolling_walk_forward(
        df, feat_cols, "y", TRAIN_W, TEST_W,
        weight_schedule=lambda ages: exp_decay_weights(ages, 60.0),
    )
    rmse_e = np.mean([f.rmse for f in folds_e])

    # (c) "学" 一个 half_life (简化版 DDG-DA)
    best_hl, table = learn_half_life(df, feat_cols, "y", TRAIN_W, TEST_W)
    print("\n== half_life 候选 RMSE 表 (越小越好) ==")
    print(table.round(4).to_string(index=False))
    folds_l, _ = rolling_walk_forward(
        df, feat_cols, "y", TRAIN_W, TEST_W,
        weight_schedule=lambda ages, hl=best_hl: exp_decay_weights(ages, hl),
    )
    rmse_l = np.mean([f.rmse for f in folds_l])

    print(f"\n== uniform                        avg RMSE = {rmse_u:.4f}  ({len(folds_u)} folds)")
    print(f"== exp half_life=60              avg RMSE = {rmse_e:.4f}  ({len(folds_e)} folds)")
    print(f"== learned half_life={best_hl:>5.1f}     avg RMSE = {rmse_l:.4f}  ({len(folds_l)} folds)")
