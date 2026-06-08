# 深入理解 Qlib 的底层因子引擎 (Factor Engine)

在量化投资中，因子（Alpha）是解释和预测资产未来收益的关键。Qlib 的底层因子引擎 (Factor / Expression Engine) 是其能够高效处理海量金融时间序列数据的核心所在。

它通过高度优化的公式表达式（Formulaic Alpha）解析与计算机制，辅以多级缓存系统，实现了兼顾灵活性与高性能的因子提取。

---

## 1. 表达式引擎 (Expression Engine)

Qlib 允许用户直接使用类字符串的数学公式表达式来定义因子。在 Qlib 中，这样的公式被称为 **Formulaic Alpha**。

### 1.1 基础概念与语法

*   **基础字段 (Fields)**: 以 `$` 开头的变量代表原始行情数据或基础数据列，例如 `$open` (开盘价)、`$close` (收盘价)、`$high` (最高价)、`$low` (最低价)、`$volume` (成交量)。
*   **算术运算**: 支持标准的加减乘除运算，例如 `($close - $open) / $open`。
*   **操作符 (Operators / Ops)**: Qlib 内置了丰富的时间序列和横截面操作符，常见的包括：
    *   `Ref(X, d)`: 获取 X 在 d 天前的值。例如 `Ref($close, 1)` 表示昨天的收盘价，`Ref($close, -1)` 表示明天的收盘价。
    *   `Mean(X, d)`: 计算 X 过去 d 天的滑动平均值。
    *   `EMA(X, d)`: 计算 X 过去 d 天的指数移动平均线。
    *   `Max(X, d)` / `Min(X, d)`: 计算过去 d 天的最大/最小值。
    *   `Rank(X)`: 横截面排序操作，计算资产在截面上的排名。

### 1.2 为什么使用表达式引擎？

1. **零代码/低代码因子开发**: 研究员可以像写 Excel 公式一样写因子，而无需编写冗长、容易出错的 Pandas/NumPy 循环代码。
2. **抽象底层存储**: 用户无需关心数据是存在 CSV、Bin 文件还是数据库中，引擎会自动解析表达式并从 `Data Provider` 拉取所需数据。
3. **计算优化**: Qlib 的引擎（底层操作符）通常由 C/C++ 或高度优化的 Cython/NumPy 实现，执行效率远超原生的 Pandas 的 `apply`。

### 1.3 典型示例：使用表达式构建 MACD 因子

MACD 是经典的量化因子，在 Qlib 中可以通过纯字符串表达式构建，并通过 `QlibDataLoader` 直接加载计算结果：

```python
from qlib.data.dataset.loader import QlibDataLoader

# 1. 定义 MACD 表达式 (Formulaic Alpha)
# DIF = (EMA($close, 12) - EMA($close, 26)) / $close
# DEA = EMA(DIF, 9)
# MACD = 2 * (DIF - DEA)
MACD_EXP = '2 * ((EMA($close, 12) - EMA($close, 26))/$close - EMA((EMA($close, 12) - EMA($close, 26))/$close, 9))'

fields = [MACD_EXP]
names = ['MACD']

# 2. 定义收益率标签 Label (例如 T+2 收益率)
labels = ['Ref($close, -2)/Ref($close, -1) - 1']
label_names = ['LABEL']

# 3. 组装 Loader 配置
data_loader_config = {
    "feature": (fields, names),
    "label": (labels, label_names)
}

# 4. 加载数据，引擎将在底层自动计算 MACD 序列
data_loader = QlibDataLoader(config=data_loader_config)
df = data_loader.load(instruments='csi300', start_time='2010-01-01', end_time='2017-12-31')

print(df)
# 引擎将返回带有多级索引 (datetime, instrument) 包含 MACD 和 LABEL 的 DataFrame。
```

---

## 2. 动态过滤机制 (Dynamic Filter)

表达式引擎不仅用于生成特征因子，还可以用于**动态构建股票池 (Instrument Pool)**。Qlib 提供了 `ExpressionDFilter`：

```python
from qlib.data.filter import NameDFilter, ExpressionDFilter
from qlib.data import D

# 过滤出当日收盘价大于昨日收盘价的股票池
expressionDFilter = ExpressionDFilter(rule_expression='$close>Ref($close,1)')
instruments = D.instruments(market='csi300', filter_pipe=[expressionDFilter])
```

在配置文件中，它长这样：
```yaml
instruments:
  market: csi300
  filter_pipe:
    - filter_type: ExpressionDFilter
      rule_expression: "Ref($close, -2) / Ref($close, -1) > 1"
```
这种机制避免了在每次回测前都需要单独跑脚本生成股票列表。

---

## 3. 多级缓存机制 (Cache Mechanism)

随着因子公式越来越复杂（如 `Alpha360` 有 360 个复杂特征），如果每次实验都从头算一遍 `EMA` 或 `Ref`，耗时将不可接受。为此，Qlib 因子引擎设计了强大的缓存机制：

1. **MemCache (内存全局缓存)**:
   在 `qlib.data.cache` 模块中维护了一个全局字典，用于缓存最常用的基础数据：**Calendar (日历)**、**Instruments (股票列表)** 和 **Features (基础行情列)**。

2. **ExpressionCache (表达式缓存)**:
   当引擎计算出一个表达式（如 `Mean($close, 5)`）的结果后，它可以被缓存下来。Qlib 实现了 `DiskExpressionCache`，计算结果将按照 `hash(instrument, field_expression, freq)` 生成哈希值，保存在磁盘文件（如 `.bin` 格式）中。下次如果遇到同样的子表达式（即便是作为更长表达式的一部分），将直接命中磁盘缓存。

3. **DatasetCache (数据集缓存)**:
   在数据切片和预处理（如丢弃缺失值、归一化）完成后，引擎还可以将整个 `Dataset` 结果缓存到磁盘 (`DiskDatasetCache`)。该缓存通过 `hash(stockpool_config, field_expression_list, freq)` 映射。这意味着，对于给定的股票池和特征集，只要数据预处理逻辑不发生改变，第二次提取将瞬间完成。

### 缓存存储目录结构示例:
```text
- data/
    [raw data] # 原始数据
    - calendars/
    - instruments/
    - features/ # 基础高开低收等

    [cached data] # 引擎计算后的缓存
    - calculated features/
        - sh600000/
            - [hash(instrtument, field_expression, freq)] # 表达式计算结果
                - ...bin
    - cache/
        - [hash(stockpool_config, field_expression_list, freq)] # 完整 Dataset 缓存
            - ...bin
```

## 4. 总结

Qlib 底层因子引擎的精密之处体现在：
1. **抽象**: 提供了一套完备且语义明确的领域特定语言 (DSL / Expression) 来描述金融因子逻辑。
2. **组合**: 基础的 Operator（Ref, Mean, Max, EMA）可以像乐高积木一样嵌套组合出无限种类的复杂因子（Formulaic Alphas）。
3. **极速**: 借助多进程计算和底层的 `ExpressionCache` / `DatasetCache`，以牺牲一定磁盘空间为代价，换取了指数级的研发效率提升。