Qlib/data/ops.py
内部有很多代码包导入，这里对核心代码进行摘取
---
文件里的所有类，几乎都继承自同一个祖先：ExpressionOps（表达式算子）

Qlib 最厉害的一点在于，你输入一个字符串："Mean($close, 5) / Ref($close, 1)"，它能自动解析并计算。
它是怎么做到的？看这个文件里反复出现的两个核心方法：
1. ​__str__(self)：负责把算子还原成字符串。 比如 Mean 类返回 "Mean({},{})"，这构成了 Qlib 的表达式解析语法。
'''Python
def __str__(self):
        return "{}({})".format(type(self).__name__, self.feature)

2. ​_load_internal(self, instrument, start_index, end_index, *args)：这是真正的执行核心。当数据引擎需要算数据时，会传入股票代码（instrument）和时间范围，这个方法就会调用底层的高性能计算（Numpy/Pandas/Cython），最后返回一个带有时间索引的 pd.Series。
'''Python
def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        return getattr(np, self.func)(series)
'''

---
​整个 ops.py 里的几十个类，其实可以整齐地划分为以下四大核心家族。读代码时，每个家族抽一个代表来看就行：
​1. 单元素算子家族 (ElemOperator)
​特点：对一列数据进行独立转换（输入一个特征，输出一个特征）。
​代表：Abs（绝对值）、Log（对数）。
​源码精髓：通常直接调用 Numpy。比如 NpElemOperator 里的 getattr(np, self.func)(series)。
'''python
class NpElemOperator(ElemOperator):
    """Numpy Element-wise Operator

    Parameters
    ----------
    feature : Expression
        feature instance
    func : str
        numpy feature operation method

    Returns
    ----------
    Expression
        feature operation output
    """

    def __init__(self, feature, func):
        self.func = func
        super(NpElemOperator, self).__init__(feature)

    def _load_internal(self, instrument, start_index, end_index, *args):
        series = self.feature.load(instrument, start_index, end_index, *args)
        return getattr(np, self.func)(series)
   '''     


​2. 双特征算子家族 (PairOperator)
​特点：两个特征（或特征与常数）之间进行四则运算或逻辑比较。
​代表：Add（加）、Sub（减）、Mul（乘）、Div（除）、Gt（大于）。
​源码精髓：处理两个特征长度不对齐时的异常（代码中那段长长的 warning_info 就是在干这件事）。

​3. 时序滚动算子家族 (Rolling) 🌟最核心
​特点：量化中最常用的滑动窗口计算。比如“5日均线”、“20日最高价”。
​代表：Mean（均值）、Max（最大值）、Std（标准差）、Ref（时光倒流/前移）。
​源码精髓：
​如果 N == 0，代表 expanding（从历史第一天累加到今天）。
​如果 0 < N < 1，自动转为指数加权流动窗口（ewm）。
​终极加速：注意看文件最上方的 _libs.rolling（导入了 rolling_slope 等）。普通的 Pandas 滚动回归（Slope, Rsquare）极其慢，Qlib 在这里调用了 Cython（C++）编写的底层库来进行百倍加速！
​
4. 时序重采样算子 (TResample)
​特点：专门做频段转换，比如把日线数据（Day）合成周线（Week）或月线（Month）。






     
