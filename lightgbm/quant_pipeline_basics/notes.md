# 量化 LightGBM 流水线基础 (qlib 简化版)

工业仓库 (qlib / Alphalens) 把这一整套拆成了几十个类、表达式引擎和算子,
对入门来说太重了。 这里把最核心的三段抽出来, 用纯 pandas + LightGBM 写,
方便对照官方文档学。 完整能跑代码在 `code.py` , 出处看 `sources.md` 。

数据假设全程一致: MultiIndex `(datetime, instrument)` 的 DataFrame ,
columns 至少含 `close, volume` 。 这个格式 qlib / Alphalens 都在用,
就是 `duckdb/wide_to_long/` 里讲过的「长表 → MultiIndex」。

---

## 1. 打标签 (`make_label`)

量化里说「标签」就是想让模型预测的东西, 通常是**未来某段时间的收益率**。

qlib 在 `qlib/contrib/data/handler.py` 里把默认 label 写成一个表达式字符串:

```python
DEFAULT_LABEL = ["Ref($close, -2) / Ref($close, -1) - 1"]
```

`Ref(x, t)` 是 qlib 表达式引擎里的算子,意思是把 `x` 按时间轴平移 `-t` 期
(`t<0` 取的是「未来」) 。 翻译过来就是:

```
label_t = close_{t+2} / close_{t+1} - 1
```

也就是「**t+1 开盘买入, t+2 收盘卖出**」 (在日频里近似为收盘价之间) 的收益。
之所以不直接用 `close_{t+1}/close_t - 1` , 是因为 t 时刻你看到的是 t 收盘价,
**还来不及在 t 的收盘价上交易**, 至少要等下一根 K 线进场, 否则就是用未来信息打标签。

写成 pandas 就是 `shift(-N)`:

```python
by_inst = df["close"].groupby(level="instrument")
enter   = by_inst.shift(-1)        # t+1 的价
exit_   = by_inst.shift(-1 - N)    # t+1+N 的价
label   = exit_ / enter - 1
```

**关键点**

1. 一定要 `groupby("instrument")` , 否则 shift 会把 A 股的收盘价 shift 到 B 股
   头上, 造成跨标的的信息污染。
2. `gap=1` 不能省。 这个 1 期的 gap (在原始 qlib 里是用 `Ref($close, -1)` 当
   分母实现的) 就是「执行延迟」 , 反映真实交易里 t 时刻没法在 t 收盘价上成交。
3. 出来的 label 在序列末尾会有 NaN (没有未来数据), 后面合并训练集时 dropna 掉。

## 2. 写特征 (`make_features`)

qlib 的 `Alpha158DL.get_feature_config` (`qlib/contrib/data/loader.py`)
长这样 (节选) :

```python
def get_feature_config(config={...}):
    fields = []
    names  = []

    if "kbar" in config:
        fields += [
            "($close-$open)/$open",                          # KMID
            "($high-$low)/$open",                            # KLEN
            "($close-$open)/($high-$low+1e-12)",             # KMID2
            ...
        ]
        names += ["KMID", "KLEN", "KMID2", ...]

    windows = config.get("rolling", {}).get("windows", [5,10,20,30,60])
    if "roc" in config["rolling"]:
        fields += [f"Ref($close, {w})/$close" for w in windows]
        names  += [f"ROC{w}"                  for w in windows]
    ...
    return fields, names
```

也就是说 158 个因子里, 大部分是「**几个窗口 × 几个滚动算子**」的笛卡尔积。
最经典的几类挑出来:

| 因子族 | 含义                                  | 表达式 (close 上)              |
| ------ | ------------------------------------- | ------------------------------ |
| ROC{w} | 过去 w 日累计收益率 (动量)            | `close / Ref(close, w) - 1`    |
| MA{w}  | 当前价相对 w 日均线的偏离             | `Mean(close, w) / close - 1`   |
| STD{w} | 过去 w 日已实现波动率                 | `Std(close/Ref(close,1)-1, w)` |
| VMA{w} | 当前成交量相对 w 日均量的偏离 (量能)  | `Mean(volume, w) / volume - 1` |

在 pandas 里, 同样必须按 instrument 分组:

```python
def _roll(s, w, fn):
    return s.groupby(level="instrument").transform(
        lambda x: getattr(x.rolling(w), fn)()
    )
```

用 `transform` 比 `groupby(...).rolling(...).reset_index(level=0, drop=True)`
干净: `transform` 自动保持原 MultiIndex 不变, 不会多塞一层 group key。

**关键点**

1. 必须 `groupby("instrument")` 再 rolling, 否则窗口会跨股票滚动 (致命 bug) 。
2. 所有因子在样本最早期都会有 NaN (滚动窗口没填满), 合并训练集时 dropna 即可。
3. 工业级会进一步做横截面标准化 (qlib 的 `CSZScoreNorm`) , 让因子在每个日期
   内 z-score 化。 这里没做, 入门先看清楚原始因子长啥样。

## 3. 训练 + 评估 (`train_lgb` , `daily_ic`)

参数字典直接照搬 qlib LGBModel (`qlib/contrib/model/gbdt.py`) 的默认值,
都是「树模型在低信噪比金融数据上」的常见配置:

```python
DEFAULT_PARAMS = {
    "objective": "regression",
    "metric": "rmse",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "min_data_in_leaf": 50,
    "verbose": -1,
}
```

复用 `lightgbm/train_function_template/` 里讲过的「参数抽出来当常量」、
「train / predict 拆开」, 这里只多了两点:

1. **early stopping 走 callbacks**:

   ```python
   callbacks = [
       lgb.log_evaluation(period=50),
       lgb.early_stopping(early_stopping_rounds),  # 只在有 valid 时加
   ]
   ```

   LightGBM 4.x 之后 `early_stopping_rounds` 参数从 `lgb.train(...)` 移到了
   `callbacks` 列表里, 老的写法会报 warning 。

2. **数据切分不要随机切**: 量化必须按时间切, 否则训练集里会出现「比 valid
   更晚的样本」, 模型会偷看未来。 在 `__main__` 里我用的是:

   ```python
   dt = data.index.get_level_values("datetime")
   train = data[dt <= split_date]
   valid = data[dt > split_date]
   ```

   工业级会用滚动窗口的 walk-forward (qlib 的 `DatasetH.prepare(slc)`) ,
   每次只用过去训练、预测下一段, 但思想是一样的。

### 评估指标:日均 IC

```python
df.groupby(level="datetime").apply(lambda g: g["pred"].corr(g["label"]))
```

每天对所有股票算 (pred, label) 的 Pearson 相关, 再看时间序列的:

- `IC.mean()`     —— 平均预测力, 量化里 > 0.03 就算「有信号」
- `IC.mean()/IC.std()` —— IR (信息比率) , 看稳定性, > 0.3 算不错

Alphalens (Quantopian) 的 `get_clean_factor_and_forward_returns` 就是
把数据搞成 MultiIndex 然后算这个的, 跟这里思路一致。

---

## 整条流水线串起来

```python
y    = make_label(df, n_periods=5)
X    = make_features(df)
data = pd.concat([X, y.rename("y")], axis=1).dropna()

dt   = data.index.get_level_values("datetime")
train, valid = data[dt <= split], data[dt > split]

model = train_lgb(train[feats], train["y"], valid[feats], valid["y"])
pred  = pd.Series(model.predict(valid[feats]), index=valid.index)
ic    = daily_ic(pred, valid["y"])
print(ic.mean(), ic.mean() / ic.std())
```

跟 qlib 的 `task` config (`task["model"] + task["dataset"]`) 干的事是一样的,
只是 qlib 把 `make_label` / `make_features` 抽成了 `DataHandlerLP` 类、
`train_lgb` 抽成了 `LGBModel.fit` , 配置走 yaml 。 流程懂了之后, 再去看
qlib 的源码就是「找对应组件」而不是「啃整个框架」。
