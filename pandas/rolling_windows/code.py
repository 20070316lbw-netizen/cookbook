"""
pandas 滚动窗口 (rolling) 速查: 单序列的基本用法 + 量化 panel data
(MultiIndex (datetime, instrument)) 上不跨股票滚动的正确姿势。

输入约定: 单序列是 index=日期 的 Series; panel 是 MultiIndex
(datetime, instrument) 的 Series/DataFrame (同 lightgbm/quant_pipeline_basics)。
细节和坑放 notes.md , 出处放 sources.md 。
"""

import numpy as np
import pandas as pd


# ---------- 1) 单序列: rolling 基本款 ----------

def rolling_basics(close: pd.Series, window: int = 5) -> pd.DataFrame:
    """
    最常用的几个滚动统计, 一次算齐方便对照。

    前 window-1 个值是 NaN (窗口没填满) ; 想让窗口没满也出数,
    加 min_periods (见 notes.md 的取舍) 。
    """
    r = close.rolling(window)
    return pd.DataFrame({
        "mean": r.mean(),                       # 均线
        "std": r.std(),                         # 滚动波动
        "max": r.max(),
        "min": r.min(),
        "mean_minp1": close.rolling(window, min_periods=1).mean(),
    })


# ---------- 2) panel: 按 instrument 分组滚动, 不让窗口跨股票 ----------

def panel_rolling_mean(s: pd.Series, window: int) -> pd.Series:
    """
    MultiIndex (datetime, instrument) 的 Series 上做滚动均值。

    用 groupby + transform: 输出保持原 MultiIndex 不变, 能直接赋值回原 df 。
    直接 s.rolling(window) 是致命 bug —— 窗口会从 A 股票的尾部滚进 B 股票
    的头部 (见 notes.md) 。
    """
    return s.groupby(level="instrument").transform(
        lambda x: x.rolling(window).mean()
    )


if __name__ == "__main__":
    # 自测 1: 单序列
    rng = np.random.default_rng(0)
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, len(dates))), index=dates)
    print("== 单序列 rolling(5) ==")
    print(rolling_basics(close, window=5).round(2))

    # 自测 2: panel, 验证窗口没有跨股票
    insts = ["A", "B"]
    mi = pd.MultiIndex.from_product([dates, insts], names=["datetime", "instrument"])
    panel = pd.Series(rng.normal(0, 1, len(mi)), index=mi).sort_index()

    good = panel_rolling_mean(panel, window=3)
    bad = panel.rolling(3).mean()  # 反面教材: 不分组直接滚

    # 每只股票的前 2 个值都该是 NaN (窗口没满) ; 不分组时只有整体前 2 个是 NaN
    n_nan_good = good.isna().groupby(level="instrument").sum()
    print("\n== 分组滚动: 每只股票各自有 2 个 NaN (正确) ==")
    print(n_nan_good)
    print(f"\n== 不分组直接滚: 总共只有 {bad.isna().sum()} 个 NaN, "
          f"窗口跨了股票 (错误) ==")
    assert (n_nan_good == 2).all()
    print("\nself-check passed.")
