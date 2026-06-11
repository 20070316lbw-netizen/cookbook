# pandas 滚动窗口 (rolling)

## 输入 / 输出

- 单序列: `pd.Series`, index=日期 → `rolling(w).agg()` 返回同 index 的序列
- panel: MultiIndex `(datetime, instrument)` 的 Series →
  `groupby(level="instrument").transform(lambda x: x.rolling(w)...)`
  返回**原 MultiIndex 不变**的序列, 可直接赋回原 df

## 关键细节

1. **`rolling(w)` 的窗口是「含当前行的过去 w 行」**, 不偷看未来。
   想要"截至昨天"的均线, 算完再 `shift(1)` (先 rolling 后 shift) 。
2. **前 w-1 个值是 NaN**。 `min_periods=1` 能让窗口没满也出数, 但代价是
   早期统计量样本不足、噪声大 —— 做特征时一般宁可 NaN 再 dropna,
   别用 min_periods 凑数 (见 `lightgbm/quant_pipeline_basics/` 的处理)。
3. **panel 上必须先 `groupby(level="instrument")` 再 rolling**, 否则窗口
   从 A 股票的尾部滚进 B 股票的头部, 特征被跨标的污染, 而且不报错。
   code.py 自测里用「每只股票该有几个 NaN」验证了这一点。
4. **为什么用 `transform` 而不是 `.groupby().rolling()`**:
   后者会在结果外面再包一层 instrument 索引, 变成三层 MultiIndex,
   赋值回原 df 时静默错位 —— 这是 `pitfalls/rolling_index_misalign/`
   踩过的坑。 `transform` 保持原 index 不动, 没这个问题。
5. `rolling` 家族的近亲: `expanding()` (从头累计到当前) 、 `ewm()`
   (指数加权, qlib 的 `Mean(x, N)` 在 0<N<1 时就转成 ewm,
   见 `qlib/expression_internals/`) 。

## 坑

- `rolling(w).apply(自定义函数)` 是逐窗口跑 Python, 比内置 `mean/std/...`
  慢一到两个数量级; 内置统计量够用时别上 apply 。
- `std()` 默认 `ddof=1` (样本标准差) , 跟 numpy 默认不一样,
  和 `evaluation/risk_metrics/` 里 empyrical 的口径一致。
- 时间窗口写法 `rolling("5D")` 按日历日算 (要求 index 单调) ,
  跟 `rolling(5)` 按行数算不是一回事, 停牌多的票差别很大。
