"""
groupby().rolling() 后 index 错位问题

核心:groupby().rolling() 的结果 index 会多一层 group key,
赋值回原 df 前必须把 index 对齐。
"""
import pandas as pd


df = pd.DataFrame({
    "date":   ["2024-01-0%d" % i for i in range(1, 8)] * 2,
    "ticker": ["AAPL"] * 7 + ["MSFT"] * 7,
    "close":  [100, 101, 103, 102, 105, 107, 106,
               200, 198, 202, 201, 205, 210, 208],
}).astype({"close": float})
df = df.sort_values(["ticker", "date"]).reset_index(drop=True)


# ----------------------------------------------------------------------
# ❌ 错:直接赋值,index 是 MultiIndex(ticker, 原index),对不上
# ----------------------------------------------------------------------
def wrong():
    raw = df.groupby("ticker")["close"].rolling(3).std()
    print("groupby().rolling() 的 index 长这样:")
    print(raw.index[:4].tolist())   # [('AAPL', 0), ('AAPL', 1), ...]
    # df["std_3d"] = raw  # 这一步会 reindex 出错或全 NaN
    return raw


# ----------------------------------------------------------------------
# ✅ 写法 A:transform —— index 和输入完全一致
# ----------------------------------------------------------------------
def right_transform():
    d = df.copy()
    d["std_3d"] = d.groupby("ticker")["close"].transform(
        lambda x: x.rolling(3).std()
    )
    return d


# ----------------------------------------------------------------------
# ✅ 写法 B:reset_index 丢掉多出来的 group key 层
# ----------------------------------------------------------------------
def right_reset_index():
    d = df.copy()
    d["std_3d"] = (
        d.groupby("ticker")["close"]
        .rolling(3)
        .std()
        .reset_index(level=0, drop=True)
    )
    return d


# ----------------------------------------------------------------------
# 对照:pct_change / shift 不会有这个问题(保持原 index)
# ----------------------------------------------------------------------
def pct_change_is_fine():
    d = df.copy()
    d["ret_1d"] = d.groupby("ticker")["close"].pct_change(1)  # 直接赋值 OK
    return d


if __name__ == "__main__":
    wrong()
    print("\nright_transform():")
    print(right_transform())
    print("\nright_reset_index():")
    print(right_reset_index())

    # 两种正确写法结果应一致
    a = right_transform()["std_3d"]
    b = right_reset_index()["std_3d"]
    assert a.equals(b), "两种写法结果应该一样"
    print("\n两种正确写法结果一致 ✅")
