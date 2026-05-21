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
   利用 `pandas.eval()` 强大的执行能力，把替换后的字符串塞进去直接跑。

这样一来，我们就实现了一个“伪 AST (抽象语法树)”的解析引擎！

## 3. Qlib 真正的引擎比我们强在哪？

虽然我们只用了不到 50 行代码就跑通了表达式，但微软 Qlib 的真实引擎要强大和精密得多：

1. **真正的 AST 解析**：Qlib 不用正则替换这种容易出 Bug 的糙办法，而是写了专门的解析器，把字符串转化为一棵抽象语法树。
2. **C++ / Cython 性能压榨**：Qlib 的底层算子（如 `rolling_mean`, `rank`）很多是用 C 甚至 NumPy 底层指令重写的，速度飞快，还加入了多进程计算。
3. **极智的缓存设计**：当我们计算 `"Mean($close, 5) / Ref($close, 1) - 1"` 时，Qlib 引擎会将其拆分成三个节点。它会检查磁盘缓存里有没有算过 `Mean($close, 5)`，如果有就直接读文件，绝不重复计算。
4. **动态图优化**：真实引擎在计算复杂的因子公式树时，会进行拓扑排序并优化计算路径，从而降低内存消耗。

**总结**：
造一个简易版的因子引擎非常有助于我们理解量化平台底层的设计模式。从“面条式”的 Pandas 脚本，进化到配置驱动的“表达式引擎”，是个人手工作坊向量化系统工程迈出的最关键一步。