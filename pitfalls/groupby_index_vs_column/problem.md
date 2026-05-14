# groupby(level=...) vs groupby(列名):接口不一致会炸

## 坑长什么样

同一个项目里,两个文件对"按股票分组"用了不同写法:

```python
# features/make_features.py —— 用列名
df.groupby('ticker')['close'].pct_change(5)

# labels/make_labels.py —— 用 index level
df[price_col].groupby(level="ticker")
```

`make_labels.py` 这行在运行时直接报错:

```
KeyError: 'level name ticker is not the name of the index'
```

## 为什么会炸

`groupby(level="ticker")` 要求 `ticker` 是 **DataFrame 的索引(index)的一层**。
而项目里实际传进来的 df,`date` 和 `ticker` 都是**普通列**,不是 index。

- qlib 等成熟库内部常用 `MultiIndex(datetime, instrument)`,所以能 `groupby(level=...)`
- 但本项目约定数据是"长格式 + 普通列",没有把 ticker 设成 index
- 从 qlib 抄代码时,把 `groupby(level=...)` 一起抄过来了,但数据结构不匹配

## 根本原因

**项目内没有统一"分组到底按 index 还是按列"的约定。** 一旦两个文件不一致:
- 把 A 文件的 df 传给 B 文件的函数,必然炸
- 即使没炸,行为也可能不同(index 排序 vs 列排序)

## 教训

1. 项目里先定死一个约定:**所有中间数据都是长格式,date/ticker 是普通列**。
2. 统一用 `groupby('列名')`,不用 `groupby(level=...)`,除非真的在用 MultiIndex。
3. 从经典仓库抄代码时,**先确认对方的数据结构和你的是否一致**,不一致就要改写,不能直接粘。
4. 顺手纠正一个常见误解:`groupby(level=0)` 是"按 index 的第 0 层",**不是**"按位置/按行号"。
