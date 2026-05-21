import pandas as pd
import numpy as np
import re

class MiniFactorEngine:
    """
    一个极其简化的 Qlib 风格因子表达式引擎。
    它接收一个形如 "Mean($close, 5) / Ref($close, 1)" 的字符串，
    并在底层将其翻译成 Pandas 操作来计算结果。
    """
    def __init__(self, data: pd.DataFrame):
        """
        data: 必须是一个带有 MultiIndex (datetime, instrument) 的 DataFrame
        """
        if not isinstance(data.index, pd.MultiIndex):
            raise ValueError("Data must have a MultiIndex (datetime, instrument)")
        self.data = data.sort_index()

    def _parse_expression(self, expr: str) -> str:
        """
        将 Qlib 风格的表达式替换为能够放入 pandas.eval 的 Python 表达式。
        这里使用正则做最简单的字符串替换演示。
        """
        # 1. 替换基础字段 $close -> close
        expr = re.sub(r'\$(\w+)', r'\1', expr)

        # 2. 替换 Ref(X, d) -> shift_func(X, d)
        # 注意：Qlib 中 Ref(X, 1) 表示昨天，Pandas 中 shift(1) 也是昨天
        expr = re.sub(r'Ref\(([^,]+),\s*(-?\d+)\)', r'shift_func(\1, \2)', expr)

        # 3. 替换 Mean(X, d) -> mean_func(X, d)
        expr = re.sub(r'Mean\(([^,]+),\s*(\d+)\)', r'mean_func(\1, \2)', expr)

        return expr

    def calc(self, expr: str) -> pd.Series:
        """
        计算因子表达式并返回。
        """
        parsed_expr = self._parse_expression(expr)

        # 我们需要按股票 (instrument) 分组来计算时序因子
        # instrument 在 MultiIndex 的 level 1
        grouped = self.data.groupby(level=1)

        # 定义供 eval 使用的自定义函数
        def shift_func(series, d):
            return grouped[series.name].shift(int(d))

        def mean_func(series, d):
            # 注意避坑: 使用 transform 防止 index 错位 (参考 pitfalls/rolling_index_misalign)
            return grouped[series.name].transform(lambda x: x.rolling(int(d)).mean())

        # 将 DataFrame 的列名提取到局部变量中，供 eval 使用
        local_dict = {col: self.data[col] for col in self.data.columns}
        local_dict['shift_func'] = shift_func
        local_dict['mean_func'] = mean_func

        try:
            # 使用原生的 Python eval 计算替换后的表达式
            # pd.eval 不支持调用自定义函数 (如 mean_func)
            res = eval(parsed_expr, {}, local_dict)
            res.name = expr
            return res
        except Exception as e:
            raise RuntimeError(f"计算表达式 '{expr}' (解析为: '{parsed_expr}') 时失败: {e}")

if __name__ == "__main__":
    # 构造模拟数据
    dates = pd.date_range("2023-01-01", periods=10)
    instruments = ["AAPL", "MSFT"]
    index = pd.MultiIndex.from_product([dates, instruments], names=["datetime", "instrument"])

    df = pd.DataFrame(index=index)
    df["close"] = np.random.uniform(100, 200, size=len(index))
    df["open"] = df["close"] * np.random.uniform(0.98, 1.02, size=len(index))

    print("=== 原始数据 (前 5 行) ===")
    print(df.head())
    print("\n")

    engine = MiniFactorEngine(df)

    # 1. 计算简单的四则运算: 当日涨跌幅
    expr1 = "($close - $open) / $open"
    print(f"=== 计算: {expr1} ===")
    print(engine.calc(expr1).head())
    print("\n")

    # 2. 计算时序函数: 昨天收盘价
    expr2 = "Ref($close, 1)"
    print(f"=== 计算: {expr2} ===")
    print(engine.calc(expr2).head(4)) # 查看前4行，应该包含NaN因为是第一天
    print("\n")

    # 3. 计算复杂嵌套函数: 过去3天收盘均价相对昨日的偏离度
    expr3 = "Mean($close, 3) / Ref($close, 1) - 1"
    print(f"=== 计算: {expr3} ===")
    print(engine.calc(expr3).dropna().head())
