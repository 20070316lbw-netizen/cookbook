# 类方法的返回值类型要统一

## 1. 今天踩的坑

`run_all()` 里把所有检查方法放进一个列表，统一用循环处理：

```python
checks = [
    self.check_ohlcv(),        # 返回 dict {"ok": bool, "message": str}
    self.check_missing_data(), # 返回 dict
    self.count_trading_days()  # 返回 int  ← 类型不一样！
]
for result in checks:
    status = "✅" if result["ok"] else "❌"  # int 没有 "ok" 这个 key，报 KeyError
```

**报错：** `KeyError: 'ok'` / `KeyError: 0`

---

## 2. 根本原因

列表里混了两种不同类型的返回值：
- 其他方法返回 `dict`，可以用 `result["ok"]` 取值
- `count_trading_days()` 返回 `int`，用字符串索引会报 `KeyError`

循环不区分类型，遇到 int 就崩了。

---

## 3. 解决方案

**方法性质不同，不要强行塞进同一个循环。**

`count_trading_days()` 是"统计"，其他五个是"检查"，性质不同，分开处理：

```python
def run_all(self) -> None:
    # 检查类：统一返回 dict，走循环
    checks = [
        self.check_ohlcv(),
        self.check_missing_data(),
        self.check_date_column(),
        self.check_duplicates(),
        self.check_date_continuity(),
    ]
    for result in checks:
        status = "✅" if result["ok"] else "❌"
        print(f"{status} {result['message']}")

    # 统计类：单独打印，保持返回 int 不动
    print(f"📅 共 {self.count_trading_days()} 个交易日")
```

---

## 4. 顺手记：三元表达式

```python
# 写法
status = "✅" if result["ok"] else "❌"

# 等价于
if result["ok"]:
    status = "✅"
else:
    status = "❌"
```

`return` 和赋值 `=` 不能混用，`return status = "✅"` 是语法错误。

---

## 5. 结论

> 同一个列表里的元素，循环会用完全相同的方式处理每一个。
> 所以放进列表的方法，**返回值类型必须一致**。
> 类型不同的方法，单独处理，不要强行塞进同一个循环。
