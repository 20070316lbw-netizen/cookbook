# 裸 raise 写在 except 之外,运行时炸

## 坑长什么样

学了"失败时直接 raise"的契约后,在 if/else 的失败分支里写了光秃秃的 `raise`:

```python
if df is not None:
    return df
else:
    logger.error("没拿到数据")
    raise   # RuntimeError: No active exception to re-raise
```

更离谱的变体:把 raise 挤进 except 那一行——
`except raise ConnectionError f` ——直接语法错误。

## 为什么会炸

裸 `raise` 在 Python 里有专门语义:**重新抛出当前正在处理的异常**。
它只在 except 块里有意义——那里有一个"正在被处理的异常"可以重抛。
在 else/if 等普通代码路径上,没有任何活跃异常,Python 报
`RuntimeError: No active exception to re-raise`。

不是语法错,是语义错,所以编辑器事先不标红,跑到那一行才炸。

## 怎么解

记住 raise 的两种用法,位置决定写法:

- **普通路径上主动抛**:必须带类型,`raise ValueError("没拿到数据")`
- **except 块里重抛**:才能用裸 `raise`,标准组合是 log 一行 + raise 一行

## 教训

"直接 raise"这四个字在两种位置有两种拼法。背口诀:
**有 except 才有裸 raise;不在 except 里,raise 后面必须跟异常类型。**
