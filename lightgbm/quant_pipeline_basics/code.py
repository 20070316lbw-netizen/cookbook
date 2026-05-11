"""
量化里用 LightGBM 的最小可跑流程, 从 qlib (微软量化平台) 的 Alpha158 +
LGBModel 简化而来。 一共三步:
    1) make_label    — 用未来 N 日收益率打标签 (回归任务的 y)
    2) make_features — 写一组 Alpha158 风味的滚动技术因子 (X)
    3) train_lgb     — 训练 LightGBM, 用日均 IC 做评估

输入数据是 qlib 风格的 MultiIndex DataFrame:
    index = (datetime, instrument)
    columns 至少含 close, volume   (你也可以加 open/high/low)

为什么这样写、谁在用 (Alpha158 / LGBModel 长什么样), 看 notes.md / sources.md 。
"""

from typing import Any, Dict, Optional

import lightgbm as lgb
import numpy as np
import pandas as pd


# =====================================================================
# 1) 打标签:未来 N 日收益率
# =====================================================================
# qlib 里这一步是写成表达式 (qlib/contrib/data/handler.py 的 DEFAULT_LABEL):
#       Ref($close, -N-1) / Ref($close, -1) - 1
# 其中 Ref(x, t) 表示把 x 沿时间轴平移 -t 期 (t<0 取的是未来值) 。
# 翻译成 pandas: groupby("instrument") + shift(负数) 取未来值。
# 留 1 期 gap 是为了避开 t=0 「无法交易」的问题 (执行价用 t+1 的收盘价) 。

def make_label(
    df: pd.DataFrame,
    n_periods: int = 5,
    price_col: str = "close",
    gap: int = 1,
) -> pd.Series:
    """
    Args:
        df: MultiIndex (datetime, instrument) DataFrame, 至少含 price_col
        n_periods: 持仓天数 (预测未来多少天的累计收益)
        price_col: 用哪列价 (默认 close)
        gap: 当前 t 和进场之间隔几期 (默认 1, 即 t+1 开仓, t+1+N 平仓)
    Returns:
        Series, 同样的 MultiIndex, 值是未来 N 日收益率
    """
    by_inst = df[price_col].groupby(level="instrument")
    enter = by_inst.shift(-gap)
    exit_ = by_inst.shift(-gap - n_periods)
    return (exit_ / enter - 1).rename(f"label_{n_periods}d")


# =====================================================================
# 2) 写特征:Alpha158 的「轻量子集」
# =====================================================================
# Alpha158 (qlib/contrib/data/loader.py 里 Alpha158DL.get_feature_config)
# 有 158 个因子, 大多都是同一个套路: 几个原始字段 (OHLCV / VWAP) + 滚动
# 算子 (Mean/Std/Max/Min/Skew/Kurt/Corr/...) 在多个窗口上批量造出来 。
# 这里挑最经典的 4 类, 全在 close + volume 上算, 每个窗口都重复造一遍。

ROLL_WINDOWS = (5, 10, 20, 30, 60)


def _roll(s: pd.Series, window: int, func: str) -> pd.Series:
    """按 instrument 分组做滚动, 不让窗口跨股票, 同时保持原 MultiIndex 不变。"""
    return s.groupby(level="instrument").transform(
        lambda x: getattr(x.rolling(window), func)()
    )


def _pct_change(s: pd.Series, window: int) -> pd.Series:
    """按 instrument 分组算 N 期收益率。"""
    # groupby.pct_change 是内置优化版, 比 transform(lambda x: x.pct_change()) 快很多
    return s.groupby(level="instrument").pct_change(window)


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入 MultiIndex (datetime, instrument) DataFrame, 至少含 close, volume 。
    输出: 同 index, 一组数值特征 (每只股票独立计算, 不跨样本泄漏) 。
    """
    close = df["close"]
    volume = df["volume"]
    ret1 = _pct_change(close, 1)        # 日收益, 用来算波动率
    feats: Dict[str, pd.Series] = {}

    for w in ROLL_WINDOWS:
        # 动量: N 日累计收益率 (Alpha158 的 ROC)
        feats[f"ROC{w}"] = _pct_change(close, w)
        # 价格相对 N 日均线的偏离 (Alpha158 KMID/MA 风味)
        feats[f"MA{w}"] = _roll(close, w, "mean") / close - 1
        # N 日已实现波动率
        feats[f"STD{w}"] = _roll(ret1, w, "std")
        # 当前成交量相对 N 日均量的偏离 (Alpha158 VMA)
        feats[f"VMA{w}"] = _roll(volume, w, "mean") / volume - 1

    return pd.concat(feats, axis=1)


# =====================================================================
# 3) 训练 LightGBM + 日均 IC 评估
# =====================================================================
# 默认参数照搬 qlib LGBModel (qlib/contrib/model/gbdt.py) 的常见配置:

DEFAULT_PARAMS: Dict[str, Any] = {
    "objective": "regression",
    "metric": "rmse",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "min_data_in_leaf": 50,
    "verbose": -1,
}


def train_lgb(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_valid: Optional[pd.DataFrame] = None,
    y_valid: Optional[pd.Series] = None,
    params: Optional[Dict[str, Any]] = None,
    num_boost_round: int = 200,
    early_stopping_rounds: int = 20,
) -> lgb.Booster:
    """
    训练: 传进来的 (X, y) 必须已经按时间切好, 不要在这里做随机切分,
    否则会发生未来信息泄漏 (量化里这是最常见的 bug) 。
    """
    # 合并而不是替换: 用户只想覆盖个别参数 (比如 learning_rate) 时,
    # 其余默认值要保留, 否则会把 objective / num_leaves 都丢掉。
    params = {**DEFAULT_PARAMS, **(params or {})}
    train_set = lgb.Dataset(X_train, label=y_train)
    valid_sets = [train_set]
    callbacks = [lgb.log_evaluation(period=50)]
    if X_valid is not None and y_valid is not None:
        valid_sets.append(lgb.Dataset(X_valid, label=y_valid, reference=train_set))
        callbacks.append(lgb.early_stopping(early_stopping_rounds))
    return lgb.train(
        params,
        train_set,
        num_boost_round=num_boost_round,
        valid_sets=valid_sets,
        callbacks=callbacks,
    )


def daily_ic(pred: pd.Series, label: pd.Series) -> pd.Series:
    """
    每日横截面 IC (Pearson 相关) , 量化里看模型好坏最常用的指标:
        IC.mean()        — 平均预测力
        IC.mean()/IC.std() — IR, 信息比率, 看稳定性
    """
    df = pd.concat([pred.rename("pred"), label.rename("label")], axis=1).dropna()
    return df.groupby(level="datetime").apply(
        lambda g: g["pred"].corr(g["label"])
    )


if __name__ == "__main__":
    # 自测: 造 5 只股票 * 400 个交易日的假数据, 跑通整条流水线
    rng = np.random.default_rng(0)
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    insts = ["A", "B", "C", "D", "E"]

    frames = []
    for inst in insts:
        rets = rng.normal(0, 0.01, len(dates))
        frames.append(pd.DataFrame(
            {
                "close": 10 * np.exp(np.cumsum(rets)),
                "volume": rng.lognormal(10, 0.5, len(dates)),
            },
            index=pd.MultiIndex.from_product(
                [dates, [inst]], names=["datetime", "instrument"]
            ),
        ))
    df = pd.concat(frames).sort_index()

    # X / y
    y = make_label(df, n_periods=5)
    X = make_features(df)
    data = pd.concat([X, y.rename("y")], axis=1).dropna()

    # 时间切分: 前 70% 训, 后 30% 测 (不要随机切!)
    split_date = dates[int(len(dates) * 0.7)]
    dt = data.index.get_level_values("datetime")
    train, valid = data[dt <= split_date], data[dt > split_date]
    feat_cols = X.columns.tolist()

    model = train_lgb(
        train[feat_cols], train["y"],
        valid[feat_cols], valid["y"],
    )

    pred = pd.Series(model.predict(valid[feat_cols]), index=valid.index)
    ic = daily_ic(pred, valid["y"])
    print(
        f"\n== valid 段日均 IC = {ic.mean():.4f} , "
        f"IR = {ic.mean() / ic.std():.4f} =="
    )
