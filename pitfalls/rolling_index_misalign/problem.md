# groupby().rolling() 之后 index 变 MultiIndex,赋值回 df 会乱

## 坑长什么样

想给长格式 df 加一列"按股票分组的 5 日滚动标准差":

```python
df['std_5d'] = df.groupby('ticker')['mom_1d'].rolling(5).std()
```

结果要么报错 `cannot reindex ...`,要么赋值进去全是 NaN / 顺序错乱。

## 为什么会炸

`groupby('ticker').rolling(5).std()` 返回的 Series,**index 不再是原 df 的 index**,
而是变成了 `MultiIndex(ticker, 原index)`:

```
ticker  原index
AAPL    0          NaN
        1          NaN
        ...
MSFT    500        NaN
        ...
```

而 `df['std_5d'] = ...` 要求右边的 Series **index 和 df 的 index 对齐**。
两边 index 结构不一样,pandas 没法正确对齐,于是出错或错位。

## 两种正确写法

### 写法 A:transform(推荐,最简洁)

`transform` 保证输出的 index 和输入完全一致:

```python
df['std_5d'] = df.groupby('ticker')['mom_1d'].transform(
    lambda x: x.rolling(5).std()
)
```

### 写法 B:reset_index 把多出来的层丢掉

```python
df['std_5d'] = (
    df.groupby('ticker')['mom_1d']
    .rolling(5)
    .std()
    .reset_index(level=0, drop=True)   # 丢掉 ticker 那一层,留下原 index
)
```

## 教训

1. `groupby().rolling()` / `groupby().expanding()` 都会多出一层 group key 的 index。
2. 只要结果要 **赋值回原 df**,就必须让 index 对齐:用 `transform`,或 `reset_index(level=0, drop=True)`。
3. `groupby().pct_change()`、`groupby().shift()` **不会**有这个问题(它们保持原 index),
   所以容易让人误以为 rolling 也一样 —— 不一样。
4. 一个项目里挑一种写法统一用。本项目统一用 `transform`。
