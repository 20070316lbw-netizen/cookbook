# 裸 `raise` 陷阱：`RuntimeError: No active exception to reraise`

## 坑长什么样

想在某个条件不满足时「抛个错」，于是写了个光秃秃的 `raise`：

```python
SP500_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
if SP500_CACHE_PATH.exists():
    logger.info("文件存在，准备写入")
else:
    raise          # ❌ 后面什么都没跟
```

## 为什么会炸

不带参数的 `raise` 不是「抛一个新错误」，而是
**「把当前正在处理的异常重新抛出去」**——它只在 `except` 块里有意义：

```python
try:
    risky()
except SomeError:
    log_it()
    raise          # ✅ 这里合法：重新抛出刚捕获的 SomeError
```

如果当前**根本没有正在处理的异常**（比如你在 `else` 分支里裸写 `raise`），
Python 找不到「要重新抛的东西」，于是自己炸了：

```
RuntimeError: No active exception to reraise
```

讽刺的是：你本想报「文件不存在」的错，结果报了个驴唇不对马嘴的
`RuntimeError`，把真正的意图完全盖住了。

## 怎么解

抛错要**指定异常类型和信息**：

```python
else:
    raise FileNotFoundError(f"缓存目录创建后仍不存在：{SP500_CACHE_PATH.parent}")
```

## 教训

- 光秃秃的 `raise` **只能待在 `except` 块里**，作用是「原样再抛一次刚抓到的异常」。
- 在任何别的地方想主动报错，必须 `raise 异常类型("说明")`，
  常用的有 `ValueError` / `FileNotFoundError` / `KeyError` / `RuntimeError`。
- 顺带：这个坑当时其实是上一个坑（`exists` 漏括号）连环引发的——
  `mkdir` 已经把目录建好了，那段「建完再检查、不存在就 raise」的嵌套防御
  本身就是多余的。`mkdir(parents=True, exist_ok=True)` 要么成功、
  要么自己抛异常，不需要你手动复查。**多余的防御代码反而制造了新 bug。**
