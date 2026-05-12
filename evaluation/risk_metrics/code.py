"""
empyrical-reloaded (zipline 配套的业绩 / 风险指标库) 把每个指标都写成可处理
NaN、 可滚动、 可自定义年化周期的版本, 工业级。 这里挑量化里最常报的 6 个
指标, 用「日频 + 默认 252 个交易日年化」固化下来, 公式跟 empyrical 完全一致,
只是去掉了 series/dataframe 双路径、 NaN 早退、 周期参数这些分支。

输入统一是一个 daily returns Series (index 是日期, 值是单期简单收益率) ,
比如 `backtest/event_driven_loop/run_backtest` 的输出。

为什么用这几个公式、 跟 empyrical 对得上吗, 看 notes.md 。
"""

import numpy as np
import pandas as pd

# 一年的交易日数, empyrical periods.py 里 `APPROX_BDAYS_PER_YEAR = 252`
ANN_FACTOR = 252


# =====================================================================
# 1) 年化收益 (CAGR)
# =====================================================================
# empyrical: ending = nanprod(returns + 1); (ending ** (1 / num_years)) - 1
# 用「累计 net wealth」开 1/年数次方再减 1, 也就是 CAGR。
# 隐含假设: ending > 0 (策略没爆仓到负净值) 。 ending <= 0 时 numpy 会
# 返回 nan + RuntimeWarning, 跟 empyrical 行为一致, 此时业绩本身也已经
# 失去意义, 不在这份简化版的处理范围内。
def annual_return(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan
    num_years = len(returns) / ANN_FACTOR
    ending = (1 + returns).prod()
    return ending ** (1 / num_years) - 1


# =====================================================================
# 2) 年化波动率
# =====================================================================
# empyrical: nanstd(returns, ddof=1) * ann_factor ** (1 / alpha), alpha=2
# 也就是经典的 Lévy 缩放 σ_year = σ_day * sqrt(252)。
def annual_volatility(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) < 2:
        return np.nan
    return returns.std(ddof=1) * np.sqrt(ANN_FACTOR)


# =====================================================================
# 3) 夏普比率
# =====================================================================
# empyrical: adj = returns - risk_free  (按 period 减, 不是按年减!)
#            mean(adj) / std(adj, ddof=1) * sqrt(ann_factor)
# 注意 risk_free 是「每天的无风险收益」, 传 0.04 这种年化值会算错。
def sharpe_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    returns = returns.dropna()
    if len(returns) < 2:
        return np.nan
    adj = returns - risk_free
    sd = adj.std(ddof=1)
    if sd == 0:
        return np.nan
    return adj.mean() / sd * np.sqrt(ANN_FACTOR)


# =====================================================================
# 4) 最大回撤
# =====================================================================
# empyrical 的 drawdown_series 思路:
#     cum     = (1 + returns).cumprod()
#     peak    = np.fmax.accumulate(cum)        # 历史最高点
#     drawdown = (cum - peak) / peak           # 永远 ≤ 0
#     max_drawdown = drawdown.min()
# 返回值是负数 (例如 -0.23 表示亏了 23%) 。
def max_drawdown(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan
    cum = (1 + returns).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    return drawdown.min()


# =====================================================================
# 5) Calmar 比率
# =====================================================================
# empyrical: annual_return / abs(max_drawdown), max_dd >= 0 时返回 NaN
def calmar_ratio(returns: pd.Series) -> float:
    mdd = max_drawdown(returns)
    if mdd is None or np.isnan(mdd) or mdd >= 0:
        return np.nan
    return annual_return(returns) / abs(mdd)


# =====================================================================
# 6) Sortino 比率
# =====================================================================
# empyrical: 用 downside_risk 替换分母, 只把「跌下 required_return 的部分」
# 平方后求均值再开根:
#     downside = sqrt(mean(min(adj, 0) ** 2)) * sqrt(ann_factor)
#     sortino  = mean(adj) * ann_factor / downside
# 跟 sharpe 的区别: 不惩罚向上波动 (大涨), 只惩罚向下波动。
def sortino_ratio(returns: pd.Series, required_return: float = 0.0) -> float:
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan
    adj = returns - required_return
    downside_sq = np.minimum(adj, 0) ** 2
    downside_risk = np.sqrt(downside_sq.mean()) * np.sqrt(ANN_FACTOR)
    if downside_risk == 0:
        return np.nan
    return adj.mean() * ANN_FACTOR / downside_risk


# =====================================================================
# 一键业绩报告
# =====================================================================
def perf_summary(returns: pd.Series, risk_free: float = 0.0) -> pd.Series:
    """量化 PPT 上最常见的那六行, 串成一个 Series 方便打印 / 入表。"""
    return pd.Series(
        {
            "年化收益率": annual_return(returns),
            "年化波动率": annual_volatility(returns),
            "夏普比率":   sharpe_ratio(returns, risk_free),
            "最大回撤":   max_drawdown(returns),
            "Calmar":     calmar_ratio(returns),
            "Sortino":    sortino_ratio(returns, risk_free),
        }
    )


if __name__ == "__main__":
    # 自测: 1000 个交易日, 日均 0.05% , 日波动 1% 的合成收益
    rng = np.random.default_rng(42)
    dates = pd.date_range("2020-01-01", periods=1000, freq="B")
    returns = pd.Series(rng.normal(0.0005, 0.01, len(dates)), index=dates)

    print(perf_summary(returns).to_string(float_format=lambda x: f"{x: .4f}"))

    # 验算最大回撤: 手算一遍跟函数对得上
    cum = (1 + returns).cumprod()
    manual_mdd = ((cum - cum.cummax()) / cum.cummax()).min()
    assert np.isclose(manual_mdd, max_drawdown(returns)), "max_drawdown 不对"
    print("\nself-check passed.")
