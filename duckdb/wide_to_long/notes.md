# 把 DB 里的数据变成「长列表」

## 1. 宽表 vs 长表是啥

**宽表 (wide / pivoted)** —— 每个 instrument 占一列, 行是日期:

| date       | AAPL  | MSFT  | GOOG  |
|------------|-------|-------|-------|
| 2024-01-01 | 100.0 | 200.0 | 300.0 |
| 2024-01-02 | 101.0 | 201.0 | 299.0 |

**长表 (long / tidy)** —— 每行一个 (date, instrument, value):

| date       | instrument | close |
|------------|------------|-------|
| 2024-01-01 | AAPL       | 100.0 |
| 2024-01-01 | MSFT       | 200.0 |
| 2024-01-01 | GOOG       | 300.0 |
| 2024-01-02 | AAPL       | 101.0 |
| ...        | ...        | ...   |

工业代码库里(qlib、Alphalens、Backtrader 等)的标准形态其实是
**「长表 + MultiIndex」**, 也就是把 (datetime, instrument) 设成两层索引,
features (close / volume / $high / $low ...) 当列:

```
                       close   volume
datetime    instrument
2024-01-01  AAPL       100.0    1.2e6
            MSFT       200.0    3.4e6
            GOOG       300.0    1.1e6
2024-01-02  AAPL       101.0    1.5e6
            ...
```

## 2. 为什么要这么做

1. **加品种不用改 schema**
   - 宽表加一只票要 `ALTER TABLE` , 还要在所有下游代码里加列
   - 长表只是多几行
2. **多 feature 自然扩展**
   - close / open / volume / vwap 都能塞同一张长表(再多一列叫 feature)
   - 宽表的话每个 feature 都得维护一张宽表
3. **特征工程 groupby 友好**
   - 算 5 日均价: `df.groupby("instrument")["close"].rolling(5).mean()`
   - 横截面 rank: `df.groupby("datetime")["alpha"].rank(pct=True)`
   - 两个方向都是一句 groupby , 宽表做不到
4. **稀疏 / 不齐数据无浪费**
   - 退市、停牌、IPO 时间不一: 长表自然不出现; 宽表会留一片 NaN
5. **列存压缩友好**
   - DuckDB / Parquet 是列存, instrument 那一列高度重复, 字典编码后压缩比极高
6. **这是 tidy data 的定义**
   - Hadley Wickham 的 Tidy Data 论文 (sources.md): 每行一个观测、每列一个变量 ——
     长表是默认形态, 宽表是「为了人看」临时 pivot 出来的

## 3. qlib 是怎么做的 (工业参照)

qlib 给模型的输入就是上面那种 MultiIndex DataFrame:

- 底层存储: 每个 instrument × 每个 feature 一个 `.bin` 文件
  (本质就是「长存」, 每个 cell 一行)
- 读取层: `qlib/data/data.py` 的 `DatasetProvider` 把这些 bin 拼起来,
  返回 MultiIndex `(datetime, instrument)` 的 DataFrame
- 模型层: `qlib/contrib/data/handler.py` 里的 `Alpha158` / `Alpha360`
  直接接这个 MultiIndex 算因子, 内部全是 `groupby("instrument")` + rolling

所以一个工业 pipeline 经常长这样:

```
原始行情 (csv/宽表)
     │  UNPIVOT / melt
     ▼
长表 (date, instrument, feature, value)  ←── 存进 DuckDB / Parquet
     │  set_index([datetime, instrument])
     ▼
MultiIndex DataFrame  ←── 喂给 qlib / Alpha158 / LightGBM
```

## 4. 关键操作 (DuckDB 侧)

- 宽 → 长: `UNPIVOT table ON COLUMNS(* EXCLUDE (date)) INTO NAME instrument VALUE close`
- 长 → 宽: `PIVOT table ON instrument USING first(close) GROUP BY date`

pandas 等价物: `melt` ↔ `pivot` / `pivot_table` ;
多层用 `stack` / `unstack` 。 见 code.py 里两边都写了。

## 5. 坑

- `UNPIVOT` 必须排除掉 id 列, 否则 date 也会被融进去
  → `ON COLUMNS(* EXCLUDE (date))`
- 转 MultiIndex 后**一定**要 `sort_index()` , 不然 `.loc[(date, ins)]` 会触发
  `PerformanceWarning: indexing past lexsort depth may impact performance` ,
  而且切片速度差几个数量级
- 长表数据量是宽表的 N 倍 (N = instrument 数) , 内存里 instrument 列
  建议转 `Categorical` , 不然字符串会占爆内存
- 多 feature 时, 长表有两种放法:
  - **窄长表**: (date, instrument, feature, value) —— 四列, 最灵活, 适合 DB 存储
  - **半宽长表**: (date, instrument) 当 index, 每个 feature 一列 —— qlib 用的就是这种
  - 一般**存**用窄长表 (DB 友好) , **算**用半宽长表 (groupby 友好) ,
    中间 `pivot` 一下切换
