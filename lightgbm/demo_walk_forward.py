"""
把 evaluation/walk_forward_validation/ 的通用 walk-forward 协议 + "信号 vs
噪音"检验, 接到这个目录下两种训练方法上做对比:

    - 单棵 LightGBM (quant_pipeline_basics.train_lgb)
    - DoubleEnsemble  (double_ensemble.train_double_ensemble)

在同一份合成量化面板数据上跑 walk-forward, 分别看两者的样本外 IC 是否明显
甩开"label 打乱后"的零分布 —— 这就是回答"模型是真学到了东西还是学到了
噪音"这个问题的具体操作。

跨文件夹 import 的写法/坑跟 demo_full_pipeline.py 一致 (见那边注释) ,
这里多一步: 因为要用到 lightgbm/ 目录之外的 evaluation/walk_forward_validation/,
额外把仓库根目录也加进 sys.path。 这一步不会跟"lightgbm"这个包名撞车 ——
撞车只发生在"用 lightgbm.xxx 这种带 lightgbm 前缀的路径 import 本仓库文件"
的时候, 这里我们是通过 evaluation.xxx 这条路径进去的, 不涉及 lightgbm 这个
名字。

跑: 在仓库根目录 `python lightgbm/demo_walk_forward.py` (不要用
`python -m lightgbm.demo_walk_forward`, 原因见 notes.md 的"包名撞车"一节)。
"""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
sys.path.insert(0, str(_THIS_DIR))
sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import pandas as pd

import quant_pipeline_basics.code as qpb
import double_ensemble.code as de
from evaluation.walk_forward_validation.code import fold_mean_ic, signal_vs_noise_test


def _train_predict_lgb(X: pd.DataFrame, y: pd.Series):
    # walk-forward 每块都重训一次, 关掉 early stopping (没有独立 valid 段)
    # 并且把树数/参数调小, 不然一次 walk-forward + N 次 shuffle 会很慢。
    # num_boost_round 特意避开 qpb.train_lgb 里硬编码的 log_evaluation(period=50) ,
    # 不然 walk-forward 反复重训会刷一堆无意义的日志。
    return qpb.train_lgb(
        X, y, num_boost_round=40,
        params={"num_leaves": 15, "min_data_in_leaf": 20},
    )


def _predict_lgb(model, X: pd.DataFrame) -> np.ndarray:
    return model.predict(X)


def _train_predict_de(X: pd.DataFrame, y: pd.Series):
    return de.train_double_ensemble(
        X, y, num_models=3, num_boost_round=30,
        params={"num_leaves": 15, "min_data_in_leaf": 20},
        rng=np.random.default_rng(0),  # 固定住 FS 的 shuffle, 让示例结果可复现
    )


def _predict_de(model, X: pd.DataFrame) -> np.ndarray:
    ens, feats, ws = model
    return de.predict_double_ensemble(ens, feats, ws, X)


def _make_panel(n_dates: int, n_assets: int, n_features: int, seed: int) -> pd.DataFrame:
    """跟 quant_pipeline_basics 自测同款 OHLCV 面板, 但故意给日收益率加一点
    AR(1) 动量自相关 (`rets[t] += phi * rets[t-1]`) —— 纯随机游走的价格里
    ROC/MA 这些动量因子对未来收益是真的没有任何预测力, 那样 walk-forward
    永远测不出显著信号, 没法演示"检测到信号"这一半的效果。 加一点动量后
    ROC 类因子才有真实 (虽然很弱) 的样本外可预测性, 更接近真实股价的情形。
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-01", periods=n_dates, freq="B")
    insts = [f"S{i:02d}" for i in range(n_assets)]
    phi = 0.6

    frames = []
    for inst in insts:
        rets = rng.normal(0, 0.01, len(dates))
        for t in range(1, len(dates)):
            rets[t] += phi * rets[t - 1]
        frames.append(pd.DataFrame(
            {
                "close": 10 * np.exp(np.cumsum(rets)),
                "volume": rng.lognormal(10, 0.5, len(dates)),
            },
            index=pd.MultiIndex.from_product([dates, [inst]], names=["datetime", "instrument"]),
        ))
    df = pd.concat(frames).sort_index()

    y = qpb.make_label(df, n_periods=5)
    X = qpb.make_features(df)
    data = pd.concat([X, y.rename("y")], axis=1).dropna()
    return data, X.columns.tolist()


if __name__ == "__main__":
    data, feat_cols = _make_panel(n_dates=400, n_assets=8, n_features=5, seed=0)
    rng = np.random.default_rng(0)

    N_TRAIN, N_TEST, N_SHUFFLES = 150, 40, 16

    for name, train_fn, predict_fn in [
        ("单棵 LightGBM (quant_pipeline_basics.train_lgb)", _train_predict_lgb, _predict_lgb),
        ("DoubleEnsemble (double_ensemble.train_double_ensemble)", _train_predict_de, _predict_de),
    ]:
        real_metric, null_metrics, p_value = signal_vs_noise_test(
            data, feat_cols, "y", train_fn, predict_fn, fold_mean_ic,
            n_train=N_TRAIN, n_test=N_TEST, n_shuffles=N_SHUFFLES, rng=rng,
        )
        print(f"\n== {name} ==")
        print(
            f"real IC = {real_metric:.4f}  |  null IC 均值/标准差 = "
            f"{np.nanmean(null_metrics):.4f} / {np.nanstd(null_metrics):.4f}  |  "
            f"p_value = {p_value:.3f}"
        )
