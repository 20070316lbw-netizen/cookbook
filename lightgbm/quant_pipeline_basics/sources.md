# 出处和参考

## qlib (微软量化平台) —— 这份代码的主要简化对象

- 仓库主页: https://github.com/microsoft/qlib

- **标签 `make_label`** 的原型 (默认 `Ref($close, -2)/Ref($close, -1) - 1`):
  - `qlib/contrib/data/handler.py` — `Alpha158` / `Alpha360` 里
    `DEFAULT_LABEL` 的定义
    https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/handler.py
  - 表达式算子 `Ref` 的实现:
    `qlib/data/ops.py` , `class Ref(ElemOperator)`
    https://github.com/microsoft/qlib/blob/main/qlib/data/ops.py

- **特征 `make_features`** 的原型 (Alpha158 的 158 个因子):
  - `qlib/contrib/data/loader.py` — `Alpha158DL.get_feature_config`
    (KMID / KLEN / ROC{w} / MA{w} / STD{w} / VMA{w} / ... 全在这)
    https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/loader.py
  - 360 字段的稠密版: `Alpha360DL.get_feature_config` 同文件下面一点
  - 截面标准化 (我没抄进来的那一步):
    `qlib/data/dataset/processor.py` , `class CSZScoreNorm`
    https://github.com/microsoft/qlib/blob/main/qlib/data/dataset/processor.py

- **训练 `train_lgb` / 默认参数**:
  - `qlib/contrib/model/gbdt.py` — `class LGBModel(ModelFT, LightGBMFInt)`
    , 里面 `_prepare_data` / `fit` / `predict` 三段是这份代码的直系祖先
    https://github.com/microsoft/qlib/blob/main/qlib/contrib/model/gbdt.py

- **训练/预测的调度**:
  - `qlib/data/dataset/__init__.py` — `DatasetH.prepare("train"|"valid"|"test")`
    决定了按时间切分而不是随机切分
    https://github.com/microsoft/qlib/blob/main/qlib/data/dataset/__init__.py

## Alphalens (Quantopian) —— IC 评估的标准做法

- 仓库: https://github.com/quantopian/alphalens
  - `alphalens.utils.get_clean_factor_and_forward_returns` 接收的就是
    MultiIndex `(date, asset)` 的因子 Series 和 forward returns DataFrame
  - `alphalens.performance.factor_information_coefficient` 就是按 date
    groupby 算 Pearson / Spearman 相关 —— 也就是 `daily_ic` 在做的事

## LightGBM 官方文档 (语法层面)

- Python API (`lgb.train` / `Dataset` / callbacks):
  https://lightgbm.readthedocs.io/en/latest/Python-API.html
- 参数解释 (`num_leaves`, `feature_fraction`, `min_data_in_leaf` ...):
  https://lightgbm.readthedocs.io/en/latest/Parameters.html
- v4.0 后 `early_stopping_rounds` → `callbacks=[lgb.early_stopping(...)]`
  的迁移说明 (我代码里这么写的原因):
  https://lightgbm.readthedocs.io/en/latest/Python-Intro.html#early-stopping

## 同 cookbook 内的相关条目

- `lightgbm/train_function_template/` — 这份代码里 `train_lgb` 的写法
  (参数字典抽出来 + train/predict 拆开 + `if __name__ == "__main__"` 自测)
  就是从那一篇延伸来的, 先读那一篇再读这里更顺。
- `duckdb/wide_to_long/` — 这里输入数据的 MultiIndex `(datetime, instrument)`
  格式怎么来的, 看那一篇。
