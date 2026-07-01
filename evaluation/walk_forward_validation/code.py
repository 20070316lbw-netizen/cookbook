"""
Walk-forward validation (你可能听过的别名: forward validation / forward
chaining / rolling-origin evaluation) —— 时序模型最基本的回测协议:

    把整条时间轴切成一串不重叠的 (train, test) 块, 从头走到尾:
        train[0] -> test[0] -> train[1] -> test[1] -> ... -> test[-1]
    每块都只用"当时能看到的历史"训练, 预测紧接着的下一段, 不像 k-fold
    那样随机切 (随机切会让训练集看到未来, 时序数据上是彻头彻尾的泄漏)。

这份实现刻意跟具体模型解耦: `train_fn` / `predict_fn` 只是两个你自己传的
函数, 可以是 lightgbm 也可以是一行 OLS。 组合上 `lightgbm/` 目录下的
训练函数看 `lightgbm/demo_walk_forward.py`。

除了标准的 walk-forward 之外, 这里还多做一件事 (对应我最初想解决的问题:
"模型是真学到了东西还是只是学到了噪音") ——

    signal_vs_noise_test: 把 label 整列打乱 (打断 X-y 关系, 只留数值分布),
    在同样的 walk-forward 协议上重复跑 N 次拿到一个"纯噪声"下的指标零分布,
    再看真实 label 跑出来的指标是不是明显超出这个零分布。
    超出得越多、越靠尾部, 说明模型学到的越像是真信号而不是过拟合噪声。

跑通看自测: `python code.py` —— 一组真信号数据 + 一组纯噪声数据对比,
应该能看到前者的 real metric 远超零分布, 后者落在零分布中间。
why 和坑看 notes.md, 出处看 sources.md 。
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


# =====================================================================
# 1) 把交易日切成一串 (train_dates, test_dates) 窗口
# =====================================================================

def make_walk_forward_windows(
    dates: pd.Index,
    n_train: int,
    n_test: int,
    step: Optional[int] = None,
    expanding: bool = False,
) -> List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
    """
    Args:
        dates:     全量交易日 (会自动去重排序)
        n_train:   训练窗口长度 (交易日数)
        n_test:    测试窗口长度 (交易日数) , 同时也是默认的推进步长
        step:      每轮往前推进多少天, 默认等于 n_test (测试块首尾相接不重叠)
        expanding: True = 训练窗口从头开始一直扩张 (expanding window)
                   False = 训练窗口固定长度平移 (rolling window)
    Returns:
        [(train_dates_0, test_dates_0), (train_dates_1, test_dates_1), ...]
    """
    dates = pd.DatetimeIndex(sorted(pd.unique(dates)))
    step = step or n_test
    windows = []
    cursor = n_train
    while cursor + n_test <= len(dates):
        train_dates = dates[0:cursor] if expanding else dates[cursor - n_train:cursor]
        test_dates = dates[cursor:cursor + n_test]
        windows.append((train_dates, test_dates))
        cursor += step
    return windows


# =====================================================================
# 2) 走一遍 walk-forward, 每块 train + predict + 打分
# =====================================================================

@dataclass
class WalkForwardFold:
    fold_idx: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    metric: float
    n_train: int
    n_test: int


def fold_mean_ic(pred: pd.Series, label: pd.Series) -> float:
    """
    一块 fold 内的日均 IC (Pearson) —— 跟 `lightgbm/quant_pipeline_basics/`
    的 `daily_ic` 是同一件事, 只是这里直接聚合成一个 float 方便跨 fold 汇总。
    """
    aligned = pd.concat([pred.rename("pred"), label.rename("label")], axis=1).dropna()
    ic = aligned.groupby(level="datetime").apply(lambda g: g["pred"].corr(g["label"]))
    return float(ic.mean())


def walk_forward_validate(
    df: pd.DataFrame,
    feat_cols: Sequence[str],
    label_col: str,
    train_fn: Callable[[pd.DataFrame, pd.Series], object],
    predict_fn: Callable[[object, pd.DataFrame], np.ndarray],
    metric_fn: Callable[[pd.Series, pd.Series], float] = fold_mean_ic,
    n_train: int = 200,
    n_test: int = 40,
    step: Optional[int] = None,
    expanding: bool = False,
) -> Tuple[List[WalkForwardFold], pd.Series]:
    """
    Args:
        df:         MultiIndex (datetime, instrument) DataFrame, 含
                    feat_cols + label_col
        train_fn:   (X_train, y_train) -> model, 模型可以是任何东西
                    (lgb.Booster / DoubleEnsemble ensemble / OLS 系数...)
        predict_fn: (model, X_test) -> np.ndarray
        metric_fn:  (pred, label) -> float, 默认用日均 IC
    Returns:
        folds:    每块的结果 (含起止日期、指标、样本量)
        all_pred: 跟 df 同 index 的预测 Series, 没被任何 test 块覆盖的地方是 NaN
                  (比如最开头 n_train 天, 从来不会被预测)
    """
    dt = df.index.get_level_values("datetime")
    windows = make_walk_forward_windows(dt, n_train, n_test, step, expanding)

    folds: List[WalkForwardFold] = []
    all_pred = pd.Series(np.nan, index=df.index, dtype=float)
    for i, (train_dates, test_dates) in enumerate(windows):
        train = df.loc[dt.isin(train_dates)]
        test = df.loc[dt.isin(test_dates)]
        if train.empty or test.empty:
            continue

        model = train_fn(train[feat_cols], train[label_col])
        pred = pd.Series(predict_fn(model, test[feat_cols]), index=test.index)
        all_pred.loc[test.index] = pred

        metric = metric_fn(pred, test[label_col])
        folds.append(WalkForwardFold(
            fold_idx=i,
            train_start=train_dates[0], train_end=train_dates[-1],
            test_start=test_dates[0], test_end=test_dates[-1],
            metric=metric, n_train=len(train), n_test=len(test),
        ))
    return folds, all_pred


# =====================================================================
# 3) 信号 vs 噪音: 把 label 打乱, 建零分布
# =====================================================================
# 思路: 如果模型真学到的是 X -> y 的结构, 那把 y 打乱之后 (X 不变) 重跑一遍
# 一模一样的 walk-forward 协议, 得到的指标应该明显更差。 反过来说, 如果真实
# label 跑出来的指标掉进了"乱序 label" 也能跑出来的范围里, 那大概率是过拟合
# 到了噪声/样本量太小/窗口切法凑巧, 而不是学到了真信号。

def signal_vs_noise_test(
    df: pd.DataFrame,
    feat_cols: Sequence[str],
    label_col: str,
    train_fn: Callable[[pd.DataFrame, pd.Series], object],
    predict_fn: Callable[[object, pd.DataFrame], np.ndarray],
    metric_fn: Callable[[pd.Series, pd.Series], float] = fold_mean_ic,
    n_train: int = 200,
    n_test: int = 40,
    step: Optional[int] = None,
    expanding: bool = False,
    n_shuffles: int = 30,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[float, np.ndarray, float]:
    """
    Returns:
        real_metric:  真实 label 跑完整条 walk-forward, 各 fold metric 的均值
        null_metrics: (n_shuffles,) , label 打乱后重跑同一协议, 每次的均值指标
        p_value:      null_metrics >= real_metric 的比例 (越小越显著,
                       没有真信号时大约应该在 0.5 附近)
    """
    if rng is None:
        rng = np.random.default_rng()

    real_folds, _ = walk_forward_validate(
        df, feat_cols, label_col, train_fn, predict_fn, metric_fn,
        n_train, n_test, step, expanding,
    )
    real_metric = float(np.mean([f.metric for f in real_folds]))

    shuffled = df.copy()
    null_metrics = np.zeros(n_shuffles)
    for i in range(n_shuffles):
        # 只打乱 label 的值, X 和 index 都不动: 保留了 label 的边际分布,
        # 但彻底打断了任何 X -> y 的关系 (也打断了时间结构, 是个"最狠"的零假设)。
        shuffled[label_col] = rng.permutation(df[label_col].to_numpy())
        null_folds, _ = walk_forward_validate(
            shuffled, feat_cols, label_col, train_fn, predict_fn, metric_fn,
            n_train, n_test, step, expanding,
        )
        null_metrics[i] = np.mean([f.metric for f in null_folds]) if null_folds else np.nan

    p_value = float(np.nanmean(null_metrics >= real_metric))
    return real_metric, null_metrics, p_value


# =====================================================================
# 自测: 造一份"真信号"面板数据和一份"纯噪声"面板数据, 对比两者的
# signal_vs_noise_test 结果 —— 这就是本篇要回答的问题:
# 「怎么知道模型是真学到了东西还是学到了噪音」。
# =====================================================================

def _make_panel(
    n_dates: int, n_assets: int, n_features: int, has_signal: bool, seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2019-01-01", periods=n_dates, freq="B")
    assets = [f"S{i:02d}" for i in range(n_assets)]
    mi = pd.MultiIndex.from_product([dates, assets], names=["datetime", "instrument"])

    X = rng.normal(size=(n_dates * n_assets, n_features))
    feat_cols = [f"f{i}" for i in range(n_features)]
    df = pd.DataFrame(X, index=mi, columns=feat_cols)

    if has_signal:
        beta = rng.normal(size=n_features)
        df["y"] = X @ beta + rng.normal(scale=1.0, size=len(df))
    else:
        # label 跟 X 完全无关的纯噪声, 模型再怎么训也训不出稳定的样本外指标
        df["y"] = rng.normal(size=len(df))
    return df


def _fit_ols(X: pd.DataFrame, y: pd.Series) -> np.ndarray:
    """自测用的最小模型: 带截距的最小二乘, 不引入额外依赖 (不用 sklearn)。"""
    Xm = np.column_stack([np.ones(len(X)), X.to_numpy()])
    coef, *_ = np.linalg.lstsq(Xm, y.to_numpy(), rcond=None)
    return coef


def _predict_ols(coef: np.ndarray, X: pd.DataFrame) -> np.ndarray:
    Xm = np.column_stack([np.ones(len(X)), X.to_numpy()])
    return Xm @ coef


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    feat_cols = [f"f{i}" for i in range(5)]
    N_TRAIN, N_TEST = 200, 40

    for label, has_signal in [("真信号 (y = Xβ + 噪声)", True), ("纯噪声 (y 与 X 无关)", False)]:
        df = _make_panel(n_dates=600, n_assets=20, n_features=5, has_signal=has_signal, seed=1)
        real_metric, null_metrics, p_value = signal_vs_noise_test(
            df, feat_cols, "y", _fit_ols, _predict_ols,
            n_train=N_TRAIN, n_test=N_TEST, n_shuffles=30, rng=rng,
        )
        print(f"\n== {label} ==")
        print(f"real IC = {real_metric:.4f}  |  null IC 均值/标准差 = "
              f"{np.nanmean(null_metrics):.4f} / {np.nanstd(null_metrics):.4f}  |  p_value = {p_value:.3f}")
