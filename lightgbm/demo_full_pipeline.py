"""
lightgbm/ 目录下三个子文件夹的组合示例 —— 不是新技术, 只是把它们的方法
"调出去"接成一条完整的训练 + 评估流水线, 方便一眼看到三者的关系和差距:

    1) quant_pipeline_basics —— 打标签 / 造特征 (整条流水线的数据来源)
    2) train_function_template —— 最朴素的训练模板 (no early stopping)
    3) double_ensemble        —— SR (样本重加权) + FS (特征选择) 的进阶版

在同一份"15% 样本标签被污染"的合成数据上, 对比三种训练方式跑出来的日均 IC,
直观看到 double_ensemble 处理噪声样本的效果。

跨文件夹 import 的坑: 这三个子文件夹都没有 __init__.py, 也没有装成包,
这里用"把 lightgbm/ 这个目录加进 sys.path, 直接按子文件夹名 import"的写法
(跟 pitfalls/script_import_modulenotfound/ 里的解法一致)。
千万不要写 `import lightgbm.quant_pipeline_basics...` —— "lightgbm" 这个
顶层包名已经被 pip 装的真正 LightGBM 库占用, 那样写会让 Python 优先解析到
真正的 LightGBM 库 (regular package 优先于本地这个同名目录形成的 namespace
package) , 找不到 quant_pipeline_basics 子模块, 报 ModuleNotFoundError。
细节看 notes.md 里的"包名撞车"一节。

跑: 在仓库根目录 `python lightgbm/demo_full_pipeline.py`,
或者 cd 进 lightgbm/ 后 `python demo_full_pipeline.py` 。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import quant_pipeline_basics.code as qpb
import double_ensemble.code as de
import train_function_template.code as tft


def _make_contaminated_panel(seed: int = 0) -> tuple[pd.DataFrame, list[str]]:
    """OHLCV 面板 + 15% 样本标签换成纯噪声 (跟 double_ensemble 自测同款设定)。"""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")
    insts = [f"S{i:02d}" for i in range(10)]

    frames = []
    for inst in insts:
        rets = rng.normal(0, 0.01, len(dates))
        frames.append(pd.DataFrame(
            {
                "close": 10 * np.exp(np.cumsum(rets)),
                "volume": rng.lognormal(10, 0.5, len(dates)),
            },
            index=pd.MultiIndex.from_product([dates, [inst]], names=["datetime", "instrument"]),
        ))
    df = pd.concat(frames).sort_index()

    y = qpb.make_label(df, n_periods=5)
    X = qpb.make_features(df)
    data = pd.concat([X, y.rename("y")], axis=1).dropna()

    noisy_idx = rng.choice(len(data), size=int(0.15 * len(data)), replace=False)
    y_noisy = data["y"].to_numpy().copy()
    y_noisy[noisy_idx] = rng.normal(scale=data["y"].std() * 3, size=noisy_idx.size)
    data["y"] = y_noisy
    return data, X.columns.tolist()


if __name__ == "__main__":
    data, feat_cols = _make_contaminated_panel()
    dt = data.index.get_level_values("datetime")
    split_date = dt.unique().sort_values()[int(dt.nunique() * 0.7)]
    train, valid = data[dt <= split_date], data[dt > split_date]

    print("== 1) train_function_template.train_lightgbm (最朴素版) ==")
    model_tft = tft.train_lightgbm(train[feat_cols], train["y"], valid[feat_cols], valid["y"])
    pred_tft = tft.predict(model_tft, valid[feat_cols])
    ic_tft = qpb.daily_ic(pred_tft, valid["y"])

    print("\n== 2) quant_pipeline_basics.train_lgb (规范单模型, early stopping 走 callbacks) ==")
    model_qpb = qpb.train_lgb(train[feat_cols], train["y"], valid[feat_cols], valid["y"])
    pred_qpb = pd.Series(model_qpb.predict(valid[feat_cols]), index=valid.index)
    ic_qpb = qpb.daily_ic(pred_qpb, valid["y"])

    print("\n== 3) double_ensemble.train_double_ensemble (SR + FS, 治样本/特征噪声) ==")
    ens, feats, ws = de.train_double_ensemble(
        train[feat_cols], train["y"], valid[feat_cols], valid["y"], num_models=6,
        rng=np.random.default_rng(0),  # 固定住 FS 的 shuffle, 让示例结果可复现
    )
    pred_de = pd.Series(de.predict_double_ensemble(ens, feats, ws, valid[feat_cols]), index=valid.index)
    ic_de = qpb.daily_ic(pred_de, valid["y"])

    print("\n" + "=" * 64)
    print(f"{'方法':42s}{'日均IC':>10s}{'IR':>10s}")
    for name, ic in [
        ("1) train_function_template (baseline)", ic_tft),
        ("2) quant_pipeline_basics (规范单模型)", ic_qpb),
        ("3) double_ensemble (SR+FS)", ic_de),
    ]:
        print(f"{name:42s}{ic.mean():>10.4f}{ic.mean() / ic.std():>10.4f}")
