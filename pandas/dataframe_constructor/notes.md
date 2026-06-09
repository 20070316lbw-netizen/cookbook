# `pd.DataFrame()` 括号里能塞什么

## 一句话

`pd.DataFrame(data)` 的 `data` 能吃很多种形态，核心就一个判断：
**「这堆东西里,谁当行、谁当列、谁当列名」搞清楚,就知道会变成什么表。**

最常用的是 **list of dict**(EDGAR、API 返回的 JSON 几乎都是这个),
记住它就够日常 80% 的场景。

---

## 按「喂进去的形态」分类

### 1. list of dict —— 最常用,API/JSON 的天然形态 ★

```python
records = [
    {"end": "2006-09-30", "val": 9984000000, "filed": "2009-10-27"},
    {"end": "2007-09-29", "val": 14531000000, "filed": "2010-10-27"},
]
pd.DataFrame(records)
```

规则:**每个 dict 变一行,dict 的 key 变列名,value 填格子。**
- key 不全也没事,缺的自动填 `NaN`(所以 EDGAR 里有的记录没 `frame` 字段也不报错)。
- 这是为什么 `pd.DataFrame(data["units"]["USD"])` 能一步成表 —— 数据已经钻到 list of dict 了。

### 2. dict of list —— 手动造表最直观

```python
pd.DataFrame({
    "ticker": ["AAPL", "MSFT", "NVDA"],
    "cik":    [320193, 789019, 1045810],
})
```

规则:**每个 key 变一列(列名就是 key),value 那个 list 是整列的数据。**
- 跟 list of dict 正好「转置」着想:这里 key=列,上面 key=行内字段。
- 要求各 list 等长,否则报错。

### 3. list of list(嵌套列表)—— 没列名,得自己给

```python
pd.DataFrame(
    [[320193, "AAPL"], [789019, "MSFT"]],
    columns=["cik", "ticker"],   # 不给的话列名就是 0,1,2...
)
```

规则:**每个子 list 一行,但没有列名**,得手动用 `columns=` 补。
不补的话列名是默认整数,基本没法用。

### 4. 单个 dict(value 是标量)—— 注意要加 index

```python
pd.DataFrame({"a": 1, "b": 2}, index=[0])   # 不加 index 会报错
```

value 是标量(不是 list)时,pandas 不知道有几行,必须给 `index=`。
**坑点**:很多人想造「一行的表」会在这翻车,加 `index=[0]` 即可。

### 5. numpy 数组 / 另一个 DataFrame / Series

```python
pd.DataFrame(np.array([[1, 2], [3, 4]]), columns=["x", "y"])
```
纯数值矩阵常见,同样建议带 `columns=` 否则列名是 0,1。

---

## 常用关键字参数

| 参数 | 作用 | 什么时候要 |
|------|------|-----------|
| `columns=` | 指定/筛选列名与顺序 | list of list、数组时**必加**;也可用来只挑某几列 |
| `index=` | 指定行索引 | 单 dict 标量值时**必加**;想用某列当索引时用 |
| `dtype=` | 强制列类型 | 想统一类型时偶尔用 |

---

## 一张「形态 → 谁是行/列」对照表

| 喂进去的东西 | 行是谁 | 列是谁 | 列名哪来 |
|------------|-------|-------|---------|
| list of dict | 每个 dict | dict 的字段 | dict 的 key(自动) |
| dict of list | list 的元素 | 每个 key | key(自动) |
| list of list | 每个子 list | 子 list 的位置 | 默认 0,1,2(需手动 columns) |
| 单 dict 标量 | 1 行(需 index) | 每个 key | key |

---

## 口诀

> JSON/API 返回 → 大概率 list of dict → 直接塞,key 自动变列名。
> 手动造表 → dict of list,一列一个 key。
> 只有裸数据没列名(list of list / 数组)→ 记得补 `columns=`。
> 想造单行表 → 别忘 `index=[0]`。
