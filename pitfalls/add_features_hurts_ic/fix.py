"""
"加因子反而让 IC 下降" —— 这个条目的真正教训,比标题更深。

最初想用最小合成数据复现"共线特征稀释弱信号"。做了两版才看清真相:

  方式 A(等权平均):效应被完全抹掉 —— 简化方式本身杀死了要研究的现象
  方式 B(LightGBM 多种子):效应出现了,但方向不稳定 —— seed 一换,
         IC 差异能从 -0.0015 翻到 +0.0039

最终结论不是"加共线因子一定降 IC",而是:
**弱信号下,加因子对单次 IC 的影响被随机性主导,方向不稳定。
靠单次 IC 涨跌判断一个因子好坏,是不可靠的。**
这才是该记住的东西。

依赖:numpy / pandas / lightgbm(cookbook 环境已有)。不依赖 scipy。
"""
import numpy as np
import pandas as pd
import lightgbm as lgb


def make_data(n_days=200, n_stocks=300, seed=42):
    """合成:真实信号极弱;ROC 含信号;MA 是 ROC 的近似副本(相关性~0.999)。"""
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_days):
        sig = rng.normal(0, 1, n_stocks)
        fut = 0.02 * sig + rng.normal(0, 1, n_stocks)   # 信号占比极低
        roc = sig + rng.normal(0, 0.5, n_stocks)
        ma = roc + rng.normal(0, 0.05, n_stocks)        # 与 ROC 几乎共线
        for i in range(n_stocks):
            rows.append((d, roc[i], ma[i], fut[i]))
    return pd.DataFrame(rows, columns=["day", "ROC", "MA", "future"])


def _ic(frame, feats, score_col="_s"):
    """逐日截面 spearman 再平均(口径与项目 evaluate.py 一致)。
    pandas 自带 spearman,不依赖 scipy。"""
    g = frame.groupby("day")
    return g.apply(
        lambda x: x[score_col].corr(x["future"], method="spearman"),
        include_groups=False,
    ).mean()


def ic_equalweight(df, feats):
    """方式 A:特征等权平均当打分。
    缺陷:平均两个几乎相同的变量 ≈ 原变量,共线效应被抹掉。"""
    d = df.assign(_s=df[feats].mean(axis=1))
    return _ic(d, feats)


def ic_lgbm(df, feats, seed=0):
    """方式 B:用 LightGBM(真实会在特征间分配分裂的模型)。
    时间切分,不随机切:前 70% 天训练,后 30% 天测试。"""
    days = np.sort(df["day"].unique())
    cut = days[int(len(days) * 0.7)]
    tr = df[df["day"] <= cut]
    te = df[df["day"] > cut].copy()
    params = {"objective": "regression", "num_leaves": 15,
              "learning_rate": 0.05, "verbose": -1, "seed": seed,
              "feature_fraction": 0.9, "bagging_fraction": 0.8,
              "bagging_freq": 5}
    model = lgb.train(params, lgb.Dataset(tr[feats], label=tr["future"]),
                      num_boost_round=100)
    te["_s"] = model.predict(te[feats])
    return _ic(te, feats)


if __name__ == "__main__":
    df = make_data()
    print(f"ROC vs MA 相关性: {df['ROC'].corr(df['MA']):.4f}  "
          f"(越接近 1 越冗余)\n")

    print("--- 方式 A:等权平均(反面教材:简化抹掉了现象)---")
    a1 = ic_equalweight(df, ["ROC"])
    a2 = ic_equalweight(df, ["ROC", "MA"])
    print(f"只用 ROC       : {a1:.6f}")
    print(f"加共线 MA 之后 : {a2:.6f}")
    print(f"差异           : {a2 - a1:+.6f}   <- 几乎为 0,效应被抹掉\n")

    print("--- 方式 B:LightGBM 多种子(真实机制,暴露方向不稳定)---")
    for s in range(5):
        b1 = ic_lgbm(df, ["ROC"], seed=s)
        b2 = ic_lgbm(df, ["ROC", "MA"], seed=s)
        print(f"seed={s}: 只ROC={b1:.6f}  ROC+MA={b2:.6f}  "
              f"差异={b2 - b1:+.6f}")

    print("\n结论:方式 B 的差异 seed 间正负翻转 —— 弱信号下,加因子对")
    print("单次 IC 的影响被随机性主导。靠单次 IC 涨跌判断因子好坏不可靠,")
    print("必须多种子重复 + 因子相关性 / 重要性分析。")
