# `python -m` 模块方式运行 vs 文件路径方式运行

## 1. 两种方式,不能混用

```powershell
# 方式一:文件路径 —— 反斜杠、.py 后缀
python .\pipeline\source\edgar.py

# 方式二:模块名 —— -m、点分隔、无 .py、无路径斜杠
python -m pipeline.source.edgar
```

杂交写法 `python -m .\pipeline\source\edgar.py` 会报
`Relative module names not supported`——`-m` 后面以 `.` 开头会被理解成
相对模块名(类似 `from . import x`)。

## 2. 为什么项目代码要用 `-m`

区别在 **`sys.path` 的起点**:

- 文件路径方式:起点是**脚本所在目录**(如 `pipeline/source/`),
  从那里找不到 `pipeline` 包,`from pipeline.base import ...` 直接
  `ModuleNotFoundError`
- `-m` 方式:起点是**当前工作目录**。在项目根目录跑,所有
  `from pipeline.xxx import ...` 都解析得到

```powershell
# 在 learn_quant 根目录:
uv run python -m pipeline.source.edgar   # ✅
```

## 3. 和 sys.path.insert 黑科技的关系

`python/path_and_syspath/` 里记的 `sys.path.insert(0, 项目根)` 是文件路径
方式下的补丁。**用对 `-m` 之后那套补丁永远不需要**,`import sys` 也可以
一起删掉。

优先级:`-m` > sys.path 补丁。补丁只在没法控制运行方式时用
(比如某些 IDE 的运行按钮)。

## 4. 记忆口诀

> 路径用斜杠带 .py,模块用点不带 .py;
> 项目内部互相 import,就到根目录用 `-m`。
