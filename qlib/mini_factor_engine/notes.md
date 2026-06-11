# 为什么要造一个“因子引擎”？手写一个简易版告诉你

在量化投研中，我们经常听到“因子引擎 (Factor Engine)”、“表达式引擎 (Expression Engine)” 这样的高大上词汇（比如 Qlib、WorldQuant 的 Alpha 101）。

如果我们只是个人玩家，用 Pandas 写脚本不香吗？为什么要费劲搞一个引擎呢？

## 1. 痛点：用原生 Pandas 写因子的烦恼

假设我们要写一个因子：**“过去 5 天的收盘价均值 / 昨天的收盘价 - 1”**。

如果用 Pandas 纯手工写，代码大概长这样：
```python
# 假设 df 是多重索引 (datetime, ticker)，包含列 'close'
grouped = df.groupby('ticker')
# 算均值 (注意防范 MultiIndex 对齐坑)
mean_5d = grouped['close'].transform(lambda x: x.rolling(5).mean())
# 算昨天
ref_1d = grouped['close'].shift(1)
# 最终因子
factor = mean_5d / ref_1d - 1
```

**问题在哪里？**
1. **代码太长，容易出错**：一旦因子复杂，或者你要写 100 个因子，光是 `groupby`、`shift`、`transform` 就能把你绕晕，尤其容易踩到 MultiIndex 赋值错位的坑。
2. **难以存储和复用**：因子逻辑写死在 Python 脚本里，很难用配置表（YAML/JSON）统一管理。
3. **性能瓶颈与缓存困难**：如果你改了公式最后一步的 `- 1`，Pandas 脚本会把 `mean_5d` 再算一遍。如果没有高度抽象的引擎，很难实现细粒度级别的计算结果缓存。

## 2. 解法：表达式引擎 (Expression Engine)

为了解决上面的痛点，系统架构师们引入了表达式引擎。

它的核心理念是：**将因子的业务逻辑（What）与底层计算的执行细节（How）完全解耦。**

研究员只需要输入：
`"Mean($close, 5) / Ref($close, 1) - 1"`

引擎在底层负责把这个字符串翻译成对应的计算机指令。

### 本简易版 (`mini_engine.py`) 的实现原理：

为了演示这个思想，我们在当前目录下编写了 `mini_engine.py`。它通过非常讨巧的机制实现了一个最小可用版的引擎：

1. **字符串替换 (Lexing / Parsing)**:
   利用正则表达式，把 Qlib 风格的算子翻译成 Python 函数调用。
   `Mean($close, 5)` -> `mean_func(close, 5)`
   `$close` -> `close`

2. **注入上下文计算 (Execution / Evaluation)**:
   把 DataFrame 里的所有列（如 `close`, `open`）提取出来作为变量。
   提前定义好 `mean_func` 和 `shift_func` 并在内部实现安全的 `groupby` 操作。
   用 Python 内置的 `eval(expr, {}, local_dict)` 把替换后的字符串直接跑起来
   （注意不是 `pandas.eval()`——后者只支持有限的算术表达式语法，塞不进
   我们自定义的 `mean_func` / `shift_func`；当然内置 eval 的代价就是下面
   3.1 里说的 RCE 安全隐患）。

这样一来，我们就实现了一个“伪 AST (抽象语法树)”的解析引擎！

## 3. Qlib 真正的引擎比我们强在哪？（从 Demo 到工业级生产的鸿沟）

虽然我们用几十行代码跑通了表达式计算，但这仅仅是个“玩具 Demo”。如果在真正的工程代码里这么写，会面临灾难性的后果。真实的量化引擎（如 Qlib）在以下几个维度进行了彻底的重构：

### 3.1 词法/语法分析 (Lexer & Parser) vs 正则表达式
我们在 `mini_engine.py` 中使用了正则 `r'Mean\(([^,]+),\s*(\d+)\)'` 来匹配函数。
**致命缺陷**：正则表达式无法正确处理**嵌套括号**。
如果遇到公式 `Mean(Ref($close, 1), 5)`，正则中的 `([^,]+)` 会在逗号处截断，直接导致解析崩溃。
**工业级解法**：必须使用标准的 Lexer/Parser（如 `asteval`, `PLY`）将表达式解析为严格的抽象语法树 (AST)。并且还需要维护一个 AST 白名单/自定义解释器，因为让系统直接运行裸的 `eval()` 等同于开了一个**远程代码执行 (RCE)** 的后门。

### 3.2 极端的性能瓶颈 (CPU 烤炉)
在我们的代码中，执行 `shift_func` 或 `mean_func` 时：
```python
def mean_func(series, d):
    return grouped[series.name].transform(...)
```
**致命缺陷**：每次函数调用，都在重新从 `grouped` 中根据列名提取数据，并在底层反复进行 groupby 的切片操作。如果只是少量数据没问题，但面对 `500只股票 × 10年 × 100个因子` 的运算量，Pandas 原生的 groupby 闭包操作会慢到让你怀疑人生。
**工业级解法**：通常会预编译执行图（Execution Graph），将计算任务**NumPy 化**，或者使用 `Numba`, `Cython`, 甚至直接采用 `Rust backend` / `Polars` 替代底层的计算循环。

### 3.3 缺乏中间依赖缓存 (Dependency Cache)
假设我们有多个因子都需要用到“昨天的收盘价” `Ref($close, 1)`。
**致命缺陷**：我们的简易引擎毫无记忆力，遇到一次就算一次。因子表达式越长、嵌套越深，重复计算造成的浪费就呈指数级上升。
**工业级解法**：将 AST 树转化为有向无环图 (DAG, Directed Acyclic Graph) 执行。对于每个中间节点，计算它的 `expression hash` 并写入本地高速缓存。如果哈希命中，直接从硬盘/内存拉取，避免重复计算。

**总结**：
造一个简易版的因子引擎有助于我们理解“声明式逻辑与底层执行解耦”的思想。但要跨越从 Demo 到工业级系统（如 Qlib）的鸿沟，必须补齐 AST 解析、DAG 缓存调度以及底层高性能计算（C/Rust）这三块核心拼图。