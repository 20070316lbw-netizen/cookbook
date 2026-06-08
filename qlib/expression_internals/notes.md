# Qlib 表达式内核：Expression 基类 / Feature 叶子 / ops 算子

读 `qlib/data/ops.py` 和 `qlib/data/base.py` 的笔记。把一串字符串
`"Mean($close, 5) / Ref($close, 1)"` 变成数据，靠的就是这套 Expression 体系。
自底向上：**基类 Expression → 叶子 Feature/PFeature → 算子 ops**。

---

## 1. Expression 是什么类型？

从面向对象角度看，`Expression` 是一个**抽象基类（Abstract Base Class）**。

它自己不负责具体计算，而是规定了一套统一接口——「只要你想当因子，就必须遵守的规则」。
`ops.py` 里看到的 `Abs`、`Add`、`Mean`、`Ref` 等所有算子，全都是 `Expression` 的子类。

---

## 2. 核心设计：计算树（Expression Tree）

把 Expression 想象成一棵**计算树的节点**。比如一个常见因子字符串：

`"Mean($close, 5) / Ref($close, 1)"`（5 日均价除以昨收盘价）

Qlib 的解析引擎拿到这个字符串后，**绝不会**当成普通字符串用 `eval()` 暴力执行，
而是用 Expression 把它组装成一棵树：

```text
               [ Div (一个 Expression) ]
                       /           \
                      /             \
[ Mean (一个 Expression) ]    [ Ref (一个 Expression) ]
          /        \                        /         \
   [ $close ]      [ 5 ]             [ $close ]       [ 1 ]
  (原始特征)      (常数)             (原始特征)       (常数)
```

根节点 `Div`、左子节点 `Mean`、右子节点 `Ref` 都是 Expression；甚至最底层的
原始数据 `$close`（对应源码里的 `Feature` / `PFeature`）也继承自 Expression。

---

## 3. Expression 靠什么把这棵树盘活？

当框架高喊「请计算出 2026-05-21 这一天的因子！」时，靠两个核心本领：

### 本领 A：级联加载数据（`load` 与 `_load_internal`）

调用根节点 `Div.load()` 时——

1. `Div` 主动调用左儿子 `Mean.load()` 和右儿子 `Ref.load()`
2. `Mean` 又调用底层 `$close.load()`
3. 最底层 `$close` 真正去硬盘/内存把原始收盘价的 `pd.Series` 读出来，返回给 `Mean`
4. `Mean` 用 Pandas 算好 5 日均线返回给 `Div`；`Ref` 把昨收盘算好返回给 `Div`
5. `Div` 把两个 Series 一除，大功告成

算子互相嵌套多少层都不会乱，因为它们拥有**相同的基类类型**，可以用一模一样的
方式（多态）互相调用。

### 本领 B：时序窗口追溯（`get_longest_back_rolling`）

量化回测最怕「未来函数」，也怕因数据不够导致前几天算不出数（算 5 日均线，前 4
天肯定没数据）。Expression 规定每个子类必须能汇报自己「需要往前追溯多少天」：

- `Mean($close, 5)` 汇报：「我需要 5 天。」
- `Ref($close, 1)` 汇报：「我需要 1 天。」
- 根节点 `Div` 通过 `max(left_br, right_br)` 综合评估：初始化数据时必须帮我
  往前多准备 `max(5, 1) = 5` 天的历史冷启动数据。

---

## 4. 叶子节点：Feature 与 PFeature

`ops.py` 最后（约 1677 行）有这一句注册算子：

```python
Operators.register(OpsList + [P, PRef])
```

`Feature` 和 `PFeature` 不是「加减乘除算子」，而是整棵计算树的**叶子节点**（数据源头）。

### 它们在表达式里长什么样？

配置里写 `"$close"` 取收盘价、`"$open"` 取开盘价。`$` 是 Qlib 表达式解析器的特殊
暗号，解析器一看到 `$` 就在后台把它实例化为 `Feature` 对象：`Feature("close")`。

### 运行逻辑（叶子的数据加载）

`Feature` 的定义在基类文件 `base.py` 里。触发 `Feature.load(instrument, start_index, end_index)` 时：

- 它不再向下调用其他算子（已是最底层）
- 直接向 Qlib 的 `DataManager` 索要这个 `instrument`（如 SH600000）在指定时间段的二进制数据
- 直接返回一个 `pd.Series`，index 是时间，value 是每天的收盘价

### Feature vs PFeature

- **Feature（普通特征）**：标准时序数据，如量价（Open/High/Low/Close/Volume），随交易日天天更新。
- **PFeature（PIT 特征）**：PIT = Point-In-Time（时点数据），用于财务报表（季度利润表、资产负债表）。

为什么财务数据不能用普通 Feature？因为年报虽在 12-31 截止，但真正披露可能在来年
3、4 月。直接按时序对齐会产生「未来函数」（1 月就用到了 3 月才公布的利润）。
`PFeature` 在 load 时底层严格按**披露时间（Release Time）**而非自然时间喂数据，防止
AI「偷看答案」。

---

## 5. ops.py 算子：ExpressionOps

`ops.py` 里几乎所有类都继承自同一个祖先 `ExpressionOps`。两个反复出现的核心方法：

1. **`__str__(self)`**：把算子还原成字符串。比如 `Mean` 返回 `"Mean({},{})"`，
   这构成了 Qlib 的表达式解析语法。
2. **`_load_internal(self, instrument, start_index, end_index, *args)`**：真正的
   执行核心。数据引擎需要算数据时传入股票代码和时间范围，这个方法调用底层高性能
   计算（Numpy/Pandas/Cython），返回一个带时间索引的 `pd.Series`。

### 关于 `*args` 的参数校验（`isinstance` 用法）

`*args` 在函数内部是元组，常用 `isinstance()` 校验：

```python
def load_data(instrument, start_index, end_index, *args):
    # 规定：除前三个参数，最多再传 1 个额外的整数参数
    if len(args) > 1:
        raise ValueError(f"参数传多了！最多 1 个额外参数，实际传了 {len(args)} 个。")
    if len(args) == 1:
        extra_param = args[0]
        if not isinstance(extra_param, int):
            raise TypeError(f"额外参数必须是整数，而不是 {type(extra_param)}")
    print("参数校验通过，开始加载数据...")
```

`isinstance(object, classinfo)` 检查对象是否属于某类型（或其子类），返回布尔值。
`classinfo` 可以是单个类，也可以是一个**类型元组**（多选一）。

```python
print(isinstance("Qlib", str))            # True
print(isinstance([1, 2], (list, tuple)))  # True —— 多选一
```

**最强大的特性是承认继承关系**：子类的实例和父类做 `isinstance` 检查也返回 `True`。

```python
class Animal: pass
class Dog(Animal): pass
my_dog = Dog()
print(isinstance(my_dog, Animal))  # True（狗也是动物）
```

#### `isinstance()` vs `type()` —— 致命区别

`type()` 不考虑继承关系，只认精准匹配：

```python
print(type(my_dog) == Dog)     # True
print(type(my_dog) == Animal)  # False！（type 不认父类）
```

> 💡 黄金法则：实际开发永远优先用 `isinstance()`。面向对象讲究「多态」，你写一个
> 处理 `Animal` 的函数、用户传入 `Dog`，`isinstance` 完美兼容，`type` 会无情报错。

#### 回看 ops.py 源码里的实战用法

```python
def get_longest_back_rolling(self):
    if isinstance(self.feature_left, (Expression,)):
        left_br = self.feature_left.get_longest_back_rolling()
    else:
        left_br = 0
```

双目算子（如 `Add(feature_left, feature_right)`）的左参数可能是复杂表达式
（`Ref($close, 1)`），也可能只是数字常数（`1.0`）。用 `isinstance(..., (Expression,))`
判断：是 Expression（特征）就调它的 `.get_longest_back_rolling()`；不是（纯数字）
就让 `left_br = 0`。这就是 `isinstance` 在工业级框架里最典型的用法——**动态识别
对象身份，采取不同处理策略**。

---

## 6. ops.py 的四大算子家族

`ops.py` 里几十个类可整齐划分为四大家族，读代码时每个家族抽一个代表看即可：

### 1. 单元素算子家族（`ElemOperator`）
- **特点**：对一列数据独立转换（输入一个特征，输出一个特征）。
- **代表**：`Abs`（绝对值）、`Log`（对数）。
- **源码精髓**：通常直接调 Numpy，如 `NpElemOperator` 里的 `getattr(np, self.func)(series)`。

### 2. 双特征算子家族（`PairOperator`）
- **特点**：两个特征（或特征与常数）之间做四则运算或逻辑比较。
- **代表**：`Add`、`Sub`、`Mul`、`Div`、`Gt`。
- **源码精髓**：处理两个特征长度不对齐时的异常（那段长长的 `warning_info`）。

### 3. 时序滚动算子家族（`Rolling`）🌟 最核心
- **特点**：量化中最常用的滑动窗口计算，如「5 日均线」「20 日最高价」。
- **代表**：`Mean`、`Max`、`Std`、`Ref`（时光倒流/前移）。
- **源码精髓**：
  - `N == 0` 代表 `expanding`（从历史第一天累加到今天）
  - `0 < N < 1` 自动转为指数加权窗口（`ewm`）
  - 终极加速：文件最上方的 `_libs.rolling`（导入 `rolling_slope` 等）。普通
    Pandas 滚动回归（`Slope`、`Rsquare`）极慢，Qlib 调用 Cython（C++）底层库百倍加速。

### 4. 时序重采样算子（`TResample`）
- **特点**：专门做频段转换，把日线（Day）合成周线（Week）或月线（Month）。
