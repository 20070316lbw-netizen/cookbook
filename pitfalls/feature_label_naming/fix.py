"""
特征 vs 标签:命名要区分"过去"和"未来",防数据泄漏

mom_5d   —— 过去 5 日动量,t-5 → t,已知信息,是特征
label_5d —— 未来 5 日收益,t+1 → t+6,待预测,是标签

两者计算上都用 pct_change / shift,但时间方向相反,名字必须分开。
"""
import pandas as pd


df = pd.DataFrame({
    "date":   ["2024-01-%02d" % i for i in range(1, 11)] * 2,
    "ticker": ["AAPL"] * 10 + ["MSFT"] * 10,
    "close":  [100, 101, 103, 102, 105, 107, 106, 108, 110, 109,
               200, 198, 202, 201, 205, 210, 208, 212, 215, 213],
}).astype({"close": float})
df = df.sort_values(["ticker", "date"]).reset_index(drop=True)


# ----------------------------------------------------------------------
# 特征:过去 N 日动量。只用 t 时刻及以前的信息。
#   pct_change(n) = close_t / close_{t-n} - 1
# ----------------------------------------------------------------------
def mom(df: pd.DataFrame, n: int) -> pd.Series:
    """过去 n 日动量 (t-n → t)。是特征。"""
    return df.groupby("ticker")["close"].pct_change(n)


# ----------------------------------------------------------------------
# 标签:未来 N 日收益。用到 t 之后的信息。
#   gap=1: t+1 开仓, t+1+n 平仓
#   shift(-k) 把未来第 k 期的值挪到当前行
# ----------------------------------------------------------------------
def make_label(df: pd.DataFrame, n: int = 5, gap: int = 1) -> pd.Series:
    """未来 n 日收益 (t+gap → t+gap+n)。是标签。"""
    by = df.groupby("ticker")["close"]
    enter = by.shift(-gap)
    exit_ = by.shift(-(gap + n))
    return (exit_ / enter - 1).rename(f"label_{n}d")


# ----------------------------------------------------------------------
# 一道简单的防泄漏检查:特征列名不允许出现前看词
# ----------------------------------------------------------------------
FORBIDDEN_IN_FEATURE = ("label", "future", "fwd", "target", "_y")

def assert_no_leak(feature_cols: list[str]) -> None:
    for col in feature_cols:
        low = col.lower()
        for bad in FORBIDDEN_IN_FEATURE:
            if bad in low:
                raise ValueError(f"特征列 '{col}' 含前看词 '{bad}',疑似数据泄漏")


if __name__ == "__main__":
    d = df.copy()
    d["mom_3d"] = mom(d, 3)
    d["label_3d"] = make_label(d, n=3, gap=1)

    print(d[["date", "ticker", "close", "mom_3d", "label_3d"]])

    # mom_3d 和 label_3d 数值上像,但错开了:label 是未来,mom 是过去
    print("\n注意 mom_3d(过去)和 label_3d(未来)是错开的,不是同一个东西")

    # 防泄漏检查
    feature_cols = ["mom_3d"]          # 正常
    assert_no_leak(feature_cols)
    print("特征列检查通过 ✅")

    try:
        assert_no_leak(["mom_3d", "label_3d"])  # 故意把 label 混进特征
    except ValueError as e:
        print(f"检查抓到泄漏: {e}")
