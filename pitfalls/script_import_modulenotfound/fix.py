"""
ModuleNotFoundError: No module named 'utils' —— 解法 2 的写法

核心思路:
1. 核心函数(make_features)保持纯粹,只用 pandas,不 import utils。
2. 依赖 utils 的代码(get_db 之类)只出现在 __main__ 块。
3. sys.path hack 也放在 __main__ 块里,只在直接运行时生效,
   被别的模块 import 时不走这里,不污染 sys.path。

下面是一个 features/make_features.py 的结构示意。
"""
import pandas as pd

# 注意:这里【不要】写 from utils.config import get_db
# 核心函数不依赖项目配置,这样被别的模块 import 时不会因为 utils 找不到而炸。


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """纯函数:输入 OHLCV df,输出加了特征列的 df。只依赖 pandas。"""
    df = df.sort_values(["ticker", "date"]).copy()
    df["mom_1d"] = df.groupby("ticker")["close"].pct_change(1)
    df["mom_5d"] = df.groupby("ticker")["close"].pct_change(5)
    return df


if __name__ == "__main__":
    # ---- sys.path hack:只在直接运行本文件时生效 ----
    # __file__ = .../quant/features/make_features.py
    # .parent = features/ , .parent.parent = quant/ (项目根)
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    # 依赖 utils 的 import 放在 hack 之后
    from utils.config import get_db

    # 自测:从数据库读数据 -> 跑特征 -> 看结果
    with get_db() as con:
        df = con.execute("SELECT * FROM prices ORDER BY ticker, date").fetchdf()

    out = make_features(df)
    print(out.head())
    print(f"\n共 {len(out)} 行,NaN:\n{out.isnull().sum()}")


# ----------------------------------------------------------------------
# 对比:scripts/generate_config.py 把 hack 放在文件顶部,是因为它的
# 核心函数本身就要用 PROJECT_ROOT(来自 utils),没法挪。
# 而 make_features 核心逻辑纯 pandas,可以挪进 __main__ —— 这样更干净:
#   - 被 import 时:不碰 utils,不碰 sys.path
#   - 直接运行时:hack 生效,自测能跑
#
# 另一种选择:干脆别 hack,统一用  uv run python -m features.make_features
# ----------------------------------------------------------------------
