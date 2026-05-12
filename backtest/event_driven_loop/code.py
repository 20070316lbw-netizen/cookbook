"""
zipline-reloaded 的 Ledger 是个上千行的类, 负责把「持仓 + 现金 + 价格」沿时间
推进, 每根 K 线吐出一行收益。 这里把它压缩成一个小类 + 一个主循环, 演示
事件驱动回测的核心心跳, 只保留两个动作:
    1) mark_to_market — 拿最新价给持仓估值, 算这一根 bar 的 daily return
    2) rebalance      — 按目标权重生成成交, 更新现金 + 持仓

输入数据:
    prices:  DataFrame, index=date, columns=asset, 当根 bar 的收盘价
    weights: DataFrame, 同形, 目标权重 (每行 sum 一般 ≤ 1, 剩下的留作现金)

输出: Series of daily returns , 口径和 zipline 一致:
    r_t = (V_t - V_{t-1}) / V_{t-1}

省掉了什么、对应 zipline 哪几行, 看 notes.md / sources.md 。
"""

from typing import Dict

import numpy as np
import pandas as pd


class SimpleLedger:
    """zipline `Ledger` + `PositionTracker` 的最小实现, 只跟踪现金和股数。"""

    def __init__(self, starting_cash: float = 1_000_000.0):
        self.cash: float = starting_cash
        self.positions: Dict[str, float] = {}  # asset -> shares
        self.portfolio_value: float = starting_cash
        # 最新价缓存: 停牌 / 数据缺失时沿用上一次见过的价。
        # 对应 zipline 里 Position.last_sale_price (只在有新价时更新) 。
        self._last_prices: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # 1) mark-to-market: 拿新价估值, 算这一 bar 的 return
    #    对应 zipline Ledger.update_portfolio 里:
    #        end_value = cash + positions_value
    #        returns   = (end_value - start_value) / start_value
    # ------------------------------------------------------------------
    def mark_to_market(self, prices: pd.Series) -> float:
        start_value = self.portfolio_value
        # 先把今天能看到的价灌进缓存; 没看到的资产 (停牌) 沿用历史价,
        # 否则 positions_value 会瞬间塌成 0, 当天 return 假跌一大段。
        for asset, p in prices.dropna().items():
            self._last_prices[asset] = p
        positions_value = sum(
            shares * self._last_prices.get(asset, 0.0)
            for asset, shares in self.positions.items()
        )
        self.portfolio_value = self.cash + positions_value
        if start_value == 0:
            return 0.0
        return (self.portfolio_value - start_value) / start_value

    # ------------------------------------------------------------------
    # 2) rebalance: 按目标权重产生成交
    #    对应 zipline Blotter.order_target_percent + Transaction 流程,
    #    这里直接按 close 价成交, 不模拟滑点 / 手续费 (后续再加)。
    # ------------------------------------------------------------------
    def rebalance(self, target_weights: pd.Series, prices: pd.Series) -> None:
        # 哪些 asset 这根 bar 有价? 没价的全部跳过 (停牌)。
        live = prices.dropna()
        for asset, w in target_weights.items():
            if asset not in live.index:
                continue
            target_value = w * self.portfolio_value
            target_shares = target_value / live[asset]
            current_shares = self.positions.get(asset, 0.0)
            delta = target_shares - current_shares
            if delta == 0:
                continue
            # 成交: 现金扣 (delta * price), 持仓加 delta 股
            self.cash -= delta * live[asset]
            new_shares = current_shares + delta
            if abs(new_shares) < 1e-9:
                self.positions.pop(asset, None)
            else:
                self.positions[asset] = new_shares
        # 重新估值: rebalance 本身不改总价值 (零滑点零手续费的恒等式),
        # 但写一次更稳, 也方便后面加摩擦项。 用 _last_prices 而不是 live,
        # 这样停牌资产的持仓也按上次价计入, 跟 mark_to_market 保持一致。
        positions_value = sum(
            s * self._last_prices.get(a, 0.0) for a, s in self.positions.items()
        )
        self.portfolio_value = self.cash + positions_value


def run_backtest(
    prices: pd.DataFrame,
    weights: pd.DataFrame,
    starting_cash: float = 1_000_000.0,
) -> pd.Series:
    """
    事件驱动主循环, 对应 zipline 里 `TradingSimulation.transform` 的 for-bar:
        for each bar:
            1. ledger 用新价 mark-to-market, 记录 today's return
            2. 用「今天能看到的」信号下单 (信号已 shift 过)
    weights 必须事先做过 shift(1): t 日下的单只能用 t-1 收盘前知道的信号 ,
    不然就是用未来信息回测 (量化最常见 bug, 和 lightgbm/quant_pipeline_basics
    里 make_label 的 gap=1 是同一个坑) 。
    """
    weights = weights.reindex(prices.index).fillna(0.0)
    ledger = SimpleLedger(starting_cash)
    daily_returns = []
    for date, px in prices.iterrows():
        # 1) 估值 + 收益: 持仓还是昨天的, 但价格换成了今天的
        r = ledger.mark_to_market(px)
        daily_returns.append(r)
        # 2) 用今天的目标权重调仓 (按今日收盘价成交)
        ledger.rebalance(weights.loc[date], px)
    return pd.Series(daily_returns, index=prices.index, name="returns")


if __name__ == "__main__":
    # 自测: 3 只股票 * 500 天, 用「过去 20 日动量」当信号回测
    rng = np.random.default_rng(0)
    dates = pd.date_range("2021-01-01", periods=500, freq="B")
    assets = ["A", "B", "C"]
    rets = rng.normal(0.0003, 0.012, (len(dates), len(assets)))
    prices = pd.DataFrame(
        100 * np.exp(np.cumsum(rets, axis=0)), index=dates, columns=assets
    )

    # 信号: 过去 20 日累计收益, 横截面归一到目标权重 (和为 1)
    momentum = prices.pct_change(20)
    raw = momentum.clip(lower=0)              # 只做多动量为正的
    weights = raw.div(raw.sum(axis=1), axis=0).fillna(0.0)
    # 关键: 信号要 shift(1) , 否则 t 日用了 t 日收盘后才知道的动量
    weights = weights.shift(1).fillna(0.0)

    daily_ret = run_backtest(prices, weights, starting_cash=1_000_000.0)
    cum = (1 + daily_ret).cumprod()

    print(f"bars            : {len(daily_ret)}")
    print(f"total return    : {cum.iloc[-1] - 1: .4%}")
    print(f"daily mean / std: {daily_ret.mean(): .5f} / {daily_ret.std(): .5f}")
    print(f"年化夏普 (rf=0) : {daily_ret.mean() / daily_ret.std() * np.sqrt(252): .3f}")
