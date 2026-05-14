"""
groupby(level=...) vs groupby(列名)

约定:本项目所有中间数据都是长格式,date / ticker 是普通列(不是 index)。
所以统一用 groupby('ticker'),不用 groupby(level='ticker')。
"""
import pandas as pd


# ----------------------------------------------------------------------
# 造一个最小示例:长格式,date / ticker 是普通列
# ----------------------------------------------------------------------
df = pd.DataFrame({
    "date":   ["2024-01-01", "2024-01-02", "2024-01-03"] * 2,
    "ticker": ["AAPL"] * 3 + ["MSFT"] * 3,
    "close":  [100.0, 101.0, 103.0, 200.0, 198.0, 202.0],
})


# ----------------------------------------------------------------------
# ❌ 错:数据是普通列,却用 groupby(level=...)
# ----------------------------------------------------------------------
def wrong():
    # KeyError: 'level name ticker is not the name of the index'
    return df["close"].groupby(level="ticker").pct_change(1)


# ----------------------------------------------------------------------
# ✅ 对:用列名分组
# ----------------------------------------------------------------------
def right():
    # 先排序,保证 pct_change / shift 的方向正确
    d = df.sort_values(["ticker", "date"])
    return d.groupby("ticker")["close"].pct_change(1)


# ----------------------------------------------------------------------
# 如果数据真的是 MultiIndex,才用 level=,且用名字不用数字
# ----------------------------------------------------------------------
def right_if_multiindex():
    d = df.set_index(["date", "ticker"]).sort_index()
    # level="ticker" 安全;level=1 在 index 顺序变化时会出错
    return d["close"].groupby(level="ticker").pct_change(1)


if __name__ == "__main__":
    print("right():")
    print(right())
    print("\nright_if_multiindex():")
    print(right_if_multiindex())
    try:
        wrong()
    except KeyError as e:
        print(f"\nwrong() 如预期报错: {e}")
