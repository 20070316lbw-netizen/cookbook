# COUNT(DISTINCT ...) vs GROUP BY —— 数量 vs 列表

## 场景

想知道数据库里有多少个交易日，以及都是哪些交易日。

---

## 两种写法

### 只要数量 → `COUNT(DISTINCT date)`

```sql
SELECT COUNT(DISTINCT date) FROM prices
```

- 数据库内部直接算好，只返回一个整数
- 不管数据有多大，永远只传回一个数字
- **用途：** 只需要知道"共有多少个"

Python 里：
```python
result = con.execute("SELECT COUNT(DISTINCT date) FROM prices").fetchone()
return result[0]  # 直接拿整数
```

---

### 要列表 → `GROUP BY date`

```sql
SELECT date
FROM prices
GROUP BY date
ORDER BY date
```

- 把所有不重复的日期都拉回 Python，是一个 DataFrame
- **用途：** 需要知道"具体是哪些日期"，方便后续复用

Python 里：
```python
result = con.execute("""
    SELECT date FROM prices
    GROUP BY date
    ORDER BY date
""").df()
return result["date"].tolist()
```

---

## 健壮性对比

| | `COUNT(DISTINCT)` | `GROUP BY` |
|---|---|---|
| 返回值 | 整数 | 列表/DataFrame |
| 内存占用 | 极小（一个数字） | 随数据量增长 |
| 速度 | 快（数据库内算完） | 需要传输所有日期 |
| 适用场景 | 只要数量 | 需要具体内容 |

> 只要数量用 `COUNT(DISTINCT)`，需要内容用 `GROUP BY`。
