# 方法漏括号陷阱：`if path.exists:` 永远为真

## 坑长什么样

判断文件/目录是否存在时，方法名后面忘了写括号：

```python
if SP500_CACHE_PATH.exists:        # ❌ 漏了 ()
    logger.info("文件存在，准备写入")
else:
    SP500_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
```

## 为什么会炸

`Path.exists` 是一个**方法**。不加括号，`path.exists` 拿到的是
**方法对象本身**（一个 bound method），而不是调用它得到的 `True`/`False`。

在 Python 里，任何普通对象放进 `if` 都是真值（truthy）——一个方法对象当然也是。
所以 `if path.exists:` **恒为真**，无论文件到底在不在，永远走进 `if` 分支、永远跳过 `else`。

最阴险的是它**不报错**，还会让日志跟着撒谎：

```
2026-06-08 23:00:33 | INFO | 文件存在,准备开始写入   ← 文件夹根本不存在
```

紧接着真正用到文件的那步才炸，而且炸在离病根很远的地方：

```
OSError: Cannot save file into a non-existent directory:
'C:\Users\liu\Desktop\learn_quant\database'
```

——`else` 里的 `mkdir` 被跳过了，文件夹没建，`to_csv` 往不存在的目录写，才报错。
报错信息指向 `to_csv`，但真正的病根在上面那个漏括号的 `if`。

## 怎么解

调用它。两处（包括嵌套的）都补上 `()`：

```python
if SP500_CACHE_PATH.exists():      # ✅
    ...
```

`Path.exists()` 不收参数，直接 `()`，返回 `True` / `False`。

## 教训

看到 `if 某对象.某方法:` 后面没括号，立刻警觉：
**你要判断的是「这个方法」，还是「这个方法的返回值」？** 几乎总是后者。

同类高发对象（都是方法，都得加括号）：
- `path.exists()` / `path.is_file()` / `path.is_dir()`
- `str.isdigit()` / `str.isalpha()`
- `df.empty` —— ⚠️ 反例！这个**是属性不是方法**，正确写法就是 `if df.empty:` 不加括号。
  所以不能无脑加括号，得分清属性 vs 方法。

判断依据：方法（要 `()`）vs 属性（不要 `()`）。拿不准就去看类型提示或文档，
或者临时 `print(type(path.exists))` —— 是 `<class 'method'>` 就说明你漏了括号。
