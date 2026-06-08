# `to_csv` 的 `index=False`（以及 `encoding="utf-8"`）

## 一句话

写 CSV 时几乎总要带 `index=False`，否则 pandas 会把 DataFrame 的
**行索引（0,1,2,...）当成额外一列**塞进文件。

```python
df.to_csv(SP500_CACHE_PATH, index=False, encoding="utf-8")
```

## 这两个参数各干什么

| 参数 | 不写的默认值 | 作用 | 该不该带 |
|------|------------|------|---------|
| `index` | `True` | 是否把行索引写进 CSV 第一列 | **几乎总是 `False`** |
| `encoding` | `"utf-8"`（多数环境） | 文件编码 | Windows 上有中文/特殊字符时**显式写 `"utf-8"`** 保平安 |

## 为什么 index 默认是 True 却几乎总要关掉

因为 pandas 的设计假设你的 index **有意义**（比如时间序列里 index 是日期，
那确实该写进去）。但大多数普通表格的 index 只是自动行号 0,1,2...，
写进 CSV 纯属垃圾：

- 文件里凭空多一列空表头的数字
- 下次 `read_csv` 读回来，那列变成 `Unnamed: 0`，得手动再删
- 反复存读几次，`Unnamed: 0`、`Unnamed: 0.1` 越积越多

**判断标准**：你的 index 是「有信息的」（日期、ticker…）还是「自动行号」？
- 自动行号 → `index=False`
- 有信息的 index → 要么 `index=True` 留着，要么先 `reset_index()` 把它变成正经一列

## 反向情形：什么时候不能无脑 index=False

读回来时如果你需要那个 index，写的时候就得留。或者更稳妥的做法是
**写之前 `df.reset_index()`** 把 index 降成普通列，这样它有了列名，
`index=False` 也不会丢信息。量化里存价格表常这么干（把 Date 索引 reset 成列）。

## 一句口诀

> 存普通表 → `index=False`；index 有意义 → 先 `reset_index()` 再存。
> Windows 写中文 → 顺手 `encoding="utf-8"`。
