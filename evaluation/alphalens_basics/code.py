"""
Alphalens 的最小可跑核心, 从 quantopian/alphalens 抽出来:
    alphalens/utils.py       (compute_forward_returns, quantize_factor)
    alphalens/performance.py (factor_information_coefficient,
                              mean_return_by_quantile,
                              factor_rank_autocorrelation)

工业版的 Alphalens 把每个函数都写成支持 by_group / cumulative / pyfolio /
trading_calendar 等十几种开关, 入门看不清主线。 这里只保留量化里日常用的
四件事:

    1) compute_forward_returns —— 把"宽表价格"打成 MultiIndex 的未来 N 日收益
    2) quantize_factor         —— 按 date 把因子分 N 分位 (横截面)
    3) factor_ic               —— Spearman IC 的逐日时序
    4) mean_return_by_quantile —— 分组平均未来收益 (看单调性)
    5) factor_rank_autocorr    —— 因子排名换手 (看稳定性)

输入数据格式:
    factor:  MultiIndex (date, asset) 的 Series, 模型的预测值就可以直接当 factor
    prices:  宽表 DataFrame, index=date, columns=asset

为什么要这一篇见 notes.md , 出处见 sources.md 。
"""

from typing import Dict, Sequence, Tuple

import numpy as np
import pandas as pd


# =====================================================================
# 1) 未来 N 日收益: 把宽表价格转成 MultiIndex 的 forward returns
# =====================================================================
# Alphalens 的 compute_forward_returns 支持 cumulative / 非 cumulative、 自动
# 推断 trading calendar、 z-score 过滤等。 这里只留主线: pct_change(period) +
# shift(-period) , 跟 alphalens.utils.compute_forward_returns 的核心三行一致。

def compute_forward_returns(
    factor: pd.Series,
    prices: pd.DataFrame,
    periods: Sequence[int] = (1, 5, 10),
) -> pd.DataFrame:
    """
    Args:
        factor:  MultiIndex (date, asset) Series, 决定要取哪些 (date, asset) 对
        prices:  宽表 DataFrame, index=date, columns=asset
        periods: 算几个 horizon 的 forward return
    Returns:
        MultiIndex (date, asset) DataFrame, columns = ["1D","5D","10D"...]
    """
    factor_dates = factor.index.get_level_values("date").unique()
    factor_dates = factor_dates.intersection(prices.index)
    prices = prices.filter(items=factor.index.get_level_values("asset").unique())

    out: Dict[str, pd.Series] = {}
    for p in sorted(periods):
        # cumulative pct_change(p) shift(-p) 等价于 close_{t+p}/close_t - 1
        fwd = prices.pct_change(p).shift(-p).reindex(factor_dates)
        # 宽表 → 长表 (date, asset)
        s = fwd.stack(future_stack=True).rename(f"{p}D")
        s.index.set_names(["date", "asset"], inplace=True)
        out[f"{p}D"] = s

    df = pd.concat(out, axis=1).reindex(factor.index)
    return df


# =====================================================================
# 2) 因子分位: 每天按截面分 N 分位 (1..N, 数字越大因子越大)
# =====================================================================
# alphalens.utils.quantize_factor 还支持 by_group / bins / zero_aware, 这里只留
# "每天按 qcut 切 N 分位"这一种最常用的。 量化里看分组单调性都是这么算的。

def quantize_factor(factor: pd.Series, quantiles: int = 5) -> pd.Series:
    """每天截面 qcut(quantiles) , 返回同样的 MultiIndex Series, 值是 1..quantiles 。"""
    def _q(x: pd.Series) -> pd.Series:
        # duplicates="drop" 防止当日因子大部分相同 (停牌等) 时 qcut 报错
        return pd.qcut(x, quantiles, labels=False, duplicates="drop") + 1
    q = factor.groupby(level="date", group_keys=False).apply(_q)
    q.name = "factor_quantile"
    return q.dropna().astype(int)


# =====================================================================
# 3) IC: 每天截面 Spearman 相关
# =====================================================================
# alphalens.performance.factor_information_coefficient 默认用 Spearman,
# 比 Pearson 对极端值稳健。 这里用 rank + Pearson 等价实现, 不必拉 scipy 。

def factor_ic(factor: pd.Series, forward_returns: pd.DataFrame) -> pd.DataFrame:
    """
    每日 Spearman IC 的时间序列。

    Returns:
        DataFrame, index=date, columns=各个 horizon ("1D"/"5D"/...) 的 IC
    """
    aligned = pd.concat({"factor": factor, **{c: forward_returns[c] for c in forward_returns.columns}}, axis=1)
    aligned = aligned.dropna()

    def _ic(group: pd.DataFrame) -> pd.Series:
        f_rank = group["factor"].rank()
        return pd.Series({
            col: f_rank.corr(group[col].rank())
            for col in forward_returns.columns
        })

    return aligned.groupby(level="date", group_keys=False).apply(_ic)


def ic_summary(ic: pd.DataFrame) -> pd.DataFrame:
    """常用 IC 汇总: 均值 / std / IR / t-stat / 胜率。"""
    summary = pd.DataFrame({
        "IC mean": ic.mean(),
        "IC std": ic.std(),
        "IR (mean/std)": ic.mean() / ic.std(),
        "t-stat": ic.mean() / (ic.std() / np.sqrt(ic.count())),
        "IC > 0 ratio": (ic > 0).mean(),
    })
    return summary


# =====================================================================
# 4) 分组平均未来收益: 看 monotonicity 和 top-bottom spread
# =====================================================================
# alphalens.performance.mean_return_by_quantile 是因子能不能赚钱最直观的图:
# 如果分位 1..5 的平均收益是单调递增的, 而且 5-1 spread 显著为正, 因子就有用。

def mean_return_by_quantile(
    quantile: pd.Series,
    forward_returns: pd.DataFrame,
) -> pd.DataFrame:
    """各 quantile 在每个 horizon 上的平均未来收益。"""
    df = pd.concat([quantile.rename("q"), forward_returns], axis=1).dropna()
    return df.groupby("q")[list(forward_returns.columns)].mean()


def top_minus_bottom(mean_ret: pd.DataFrame) -> pd.Series:
    """top-bottom spread, 量化里看 long-short 收益的速算。"""
    top = mean_ret.index.max()
    bot = mean_ret.index.min()
    return mean_ret.loc[top] - mean_ret.loc[bot]


# =====================================================================
# 5) 因子排名自相关: 看换手 / 稳定性
# =====================================================================
# alphalens.performance.factor_rank_autocorrelation 。 直觉: 把因子每天 rank
# 一下, 看 t 日和 t-period 日的截面排名相关有多高。 越接近 1 越稳, 接近 0 就是
# 每天换一批股票 (换手爆炸) 。

def factor_rank_autocorr(factor: pd.Series, period: int = 1) -> pd.Series:
    """跨日期的截面排名相关序列。"""
    ranks = factor.groupby(level="date", group_keys=False).rank()
    wide = ranks.unstack("asset")
    shifted = wide.shift(period)
    return wide.corrwith(shifted, axis=1)


# =====================================================================
# 6) 一站式 tear sheet (简化版)
# =====================================================================
# alphalens 提供的 create_full_tear_sheet 会出 ~20 张图。 这里只 print 5 张表,
# 量化里看完这五张基本能判断"这因子值不值得回测"。

def factor_tear_sheet(
    factor: pd.Series,
    prices: pd.DataFrame,
    periods: Sequence[int] = (1, 5, 10),
    quantiles: int = 5,
) -> Dict[str, pd.DataFrame]:
    fwd = compute_forward_returns(factor, prices, periods=periods)
    q = quantize_factor(factor, quantiles=quantiles)
    ic = factor_ic(factor, fwd)
    summary = ic_summary(ic)
    mean_ret = mean_return_by_quantile(q, fwd)
    tmb = top_minus_bottom(mean_ret)
    autocorr_1d = factor_rank_autocorr(factor, period=1)

    print("\n== IC summary ==")
    print(summary.round(4))
    print("\n== mean return by quantile (basis points) ==")
    print((mean_ret * 1e4).round(2))
    print("\n== top - bottom spread (basis points) ==")
    print((tmb * 1e4).round(2))
    print(f"\n== 1-day rank autocorr: {autocorr_1d.mean():.3f}"
          f"  (越接近 1 越稳; <0.9 一般意味换手率高)")
    return {
        "ic": ic,
        "ic_summary": summary,
        "mean_return_by_quantile": mean_ret,
        "top_minus_bottom": tmb,
        "rank_autocorr_1d": autocorr_1d,
    }


# =====================================================================
# 自测
# =====================================================================

def _make_demo_data(
    n_dates: int = 200,
    n_assets: int = 50,
    ic_strength: float = 0.05,
    seed: int = 0,
) -> Tuple[pd.Series, pd.DataFrame]:
    """造一份"因子和未来收益弱相关"的合成数据。 ic_strength 越大因子越牛。"""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=n_dates, freq="B")
    assets = [f"S{i:03d}" for i in range(n_assets)]

    # 每日收益 = ic_strength * (滞后一日的因子) + 噪声
    factor = rng.normal(size=(n_dates, n_assets))
    noise = rng.normal(size=(n_dates, n_assets)) * 0.02
    # 因子在 t 日生成 → 在 t+1 日影响收益
    returns = np.zeros_like(factor)
    returns[1:] = ic_strength * factor[:-1] * 0.02 + noise[1:]

    prices = pd.DataFrame(
        100 * np.exp(np.cumsum(returns, axis=0)),
        index=dates, columns=assets,
    )
    prices.index.name = "date"
    prices.columns.name = "asset"

    factor_s = pd.DataFrame(factor, index=dates, columns=assets).stack(future_stack=True)
    factor_s.index.set_names(["date", "asset"], inplace=True)
    factor_s.name = "factor"
    return factor_s, prices


if __name__ == "__main__":
    factor, prices = _make_demo_data(ic_strength=0.10)
    factor_tear_sheet(factor, prices, periods=(1, 5, 10), quantiles=5)
