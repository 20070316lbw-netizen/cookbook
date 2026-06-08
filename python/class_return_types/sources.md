# 出处和参考

## Python 官方文档
- 条件表达式（三元 `a if cond else b`）：
  https://docs.python.org/3/reference/expressions.html#conditional-expressions
- 内置类型 `dict` / `int`：https://docs.python.org/3/library/stdtypes.html

## 背景
- 自己写数据质量检查类时，把返回 `dict` 的「检查方法」和返回 `int` 的「统计方法」
  混进同一个循环，`result["ok"]` 报 `KeyError` 后整理出来的教训。属于自己踩出来的
  设计经验，没有特定外部出处。
