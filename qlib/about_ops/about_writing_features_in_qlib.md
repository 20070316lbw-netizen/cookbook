我们先从最基础、但也是所有算子都要打交道的大底座 —— Expression 基类和原始特征类 Feature 讲起。只有看懂了它们，后面复杂的滚动算子才能迎刃而解。
---
​在 ops.py 的最后（1677），你看到了这一行代码：
```
Operators.register(OpsList + [P, PRef])
```
原始特征的起点 —— Feature 与 PFeature

其中的 Feature 和 PFeature 并不是我们传统意义上的“加减乘除算子”，但它们是整棵计算树的叶子节点（即数据的源头）。

- ​1. 它们在表达式里长什么样？

​当你在 Qlib 配置文件中写：
​
"$close"：代表获取原始的收盘价。​"$open"：代表获取原始的开盘价。

​这里的 $ 符号就是 Qlib 表达式解析器（Expression Parser）的特殊暗号。解析器一看到 $，就会在后台自动把它实例化为一个 Feature 对象：Feature("close")。

- ​2. 源码级别的运行逻辑
​
虽然 Feature 的具体定义在基类文件（base.py）里，但在 ops.py 中，它们作为叶子节点，其数据加载的底层逻辑是这样的：
​
当触发 Feature.load(instrument, start_index, end_index) 时：

​它不再向下调用其他算子（因为它是最底层了）。
​
它直接向 Qlib 的 DataManager（数据管理器）索要这个 instrument（比如股票 SH600000）在指定时间段内的二进制冷启动数据。

​它直接返回一个 pd.Series，其 index 是时间（Datetime），value 就是每天的收盘价。

​- 3. Feature 与 PFeature 的区别是什么？

​Feature（普通特征）：获取的是标准时序数据，比如量价数据（Open, High, Low, Close, Volume）。它是随交易日天天更新的。

​PFeature（PIT特征）：PIT 全称是 Point-In-Time（时点数据），通常用于处理财务报表数据（如季度利润表、资产负债表）。

​为什么不能用普通 Feature 存财务数据？ 因为财报（比如年报）虽然在 12-31 截止，但真正发布（财报披露）可能是在来年的 3 月或 4 月。如果直接按时序对齐，就会产生“未来函数”（在 1 月份就用到了 3 月才公布的利润）。

​PFeature 在 load 时，底层会严格根据**披露时间（Release Time）**而非自然时间把数据喂给模型，防止AI“偷看答案”。
