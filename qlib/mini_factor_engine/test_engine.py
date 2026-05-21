import pandas as pd
import numpy as np
import pytest

# 从当前目录的 mini_engine.py 中导入我们写的简易引擎
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from mini_engine import MiniFactorEngine

@pytest.fixture
def mock_data():
    """
    创建一个包含 2 只股票，5 天交易数据的 Mock DataFrame，带有 MultiIndex。
    """
    dates = pd.date_range("2023-01-01", periods=5)
    instruments = ["AAPL", "MSFT"]
    index = pd.MultiIndex.from_product([dates, instruments], names=["datetime", "instrument"])

    df = pd.DataFrame(index=index)

    # 构造固定的 close 价格方便断言
    # AAPL: 10, 20, 30, 40, 50
    # MSFT: 100, 200, 300, 400, 500
    df["close"] = [
        10, 100,
        20, 200,
        30, 300,
        40, 400,
        50, 500
    ]

    # 构造固定的 open 价格
    df["open"] = [
        5, 50,
        15, 150,
        25, 250,
        35, 350,
        45, 450
    ]

    return df

def test_engine_basic_arithmetic(mock_data):
    """
    测试基础的四则运算: ($close - $open) / $open
    """
    engine = MiniFactorEngine(mock_data)
    expr = "($close - $open) / $open"
    res = engine.calc(expr)

    # 检查返回格式
    assert isinstance(res, pd.Series)
    assert res.name == expr
    assert isinstance(res.index, pd.MultiIndex)

    # 断言具体数值
    # AAPL day 1: (10 - 5) / 5 = 1.0
    assert res.loc[("2023-01-01", "AAPL")] == 1.0
    # AAPL day 3: (30 - 25) / 25 = 0.2
    assert np.isclose(res.loc[("2023-01-03", "AAPL")], 0.2)
    # MSFT day 5: (500 - 450) / 450 = 0.1111...
    assert np.isclose(res.loc[("2023-01-05", "MSFT")], 50 / 450)

def test_engine_ref_operator(mock_data):
    """
    测试时序操作符: Ref($close, 1) 获取昨天收盘价
    """
    engine = MiniFactorEngine(mock_data)
    expr = "Ref($close, 1)"
    res = engine.calc(expr)

    # 第一天没有昨天的数据，应当为 NaN
    assert pd.isna(res.loc[("2023-01-01", "AAPL")])
    assert pd.isna(res.loc[("2023-01-01", "MSFT")])

    # AAPL day 2 昨天的收盘价应该是 AAPL day 1 的收盘价: 10
    assert res.loc[("2023-01-02", "AAPL")] == 10.0
    # MSFT day 3 昨天的收盘价应该是 MSFT day 2 的收盘价: 200
    assert res.loc[("2023-01-03", "MSFT")] == 200.0

def test_engine_mean_operator(mock_data):
    """
    测试滑动操作符: Mean($close, 3) 过去 3 天的平均值
    """
    engine = MiniFactorEngine(mock_data)
    expr = "Mean($close, 3)"
    res = engine.calc(expr)

    # 只有前 2 天，算不出 3 天均值，应当为 NaN
    assert pd.isna(res.loc[("2023-01-01", "AAPL")])
    assert pd.isna(res.loc[("2023-01-02", "MSFT")])

    # AAPL day 3 的均值 = (10 + 20 + 30) / 3 = 20.0
    assert res.loc[("2023-01-03", "AAPL")] == 20.0
    # MSFT day 4 的均值 = (200 + 300 + 400) / 3 = 300.0
    assert res.loc[("2023-01-04", "MSFT")] == 300.0

def test_engine_composite_expression(mock_data):
    """
    测试复杂的组合因子: Mean($close, 3) / Ref($close, 1) - 1
    注意：这里我们刻意避免了嵌套括号 (例如 Mean(Ref(...)))，因为我们的简易正则不支持。
    """
    engine = MiniFactorEngine(mock_data)
    expr = "Mean($close, 3) / Ref($close, 1) - 1"
    res = engine.calc(expr)

    # 计算 AAPL day 3 的复合公式：
    # Mean($close, 3) = 20.0
    # Ref($close, 1) = 20.0
    # 20.0 / 20.0 - 1 = 0.0
    assert res.loc[("2023-01-03", "AAPL")] == 0.0

    # 计算 MSFT day 4 的复合公式：
    # Mean($close, 3) = 300.0
    # Ref($close, 1) = 300.0
    # 300.0 / 300.0 - 1 = 0.0
    assert res.loc[("2023-01-04", "MSFT")] == 0.0

    # 计算 AAPL day 4 的复合公式：
    # Mean($close, 3) = (20 + 30 + 40) / 3 = 30.0
    # Ref($close, 1) = 30.0
    # 30.0 / 30.0 - 1 = 0.0
    assert res.loc[("2023-01-04", "AAPL")] == 0.0
