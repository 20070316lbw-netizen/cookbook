在 Qlib 的源码世界里，Expression（表达式）是整个特征工程（Feature Engineering）的灵魂基类。

​简单来说：在 Qlib 中，所有的因子、指标、算子、甚至原始的股票价格，在底层全部都是一个 Expression 对象。

​为了让你彻底理解它，我们可以从它的类型本质、核心设计以及它是怎么把一串字符串变成数据的这三个维度来剖析。

---
1. Expression 到底是什么类型？

​从 Python 的面向对象角度来看，Expression 是一个抽象基类（Abstract Base Class）。

​它自己本身不负责具体的计算，而是定义了一套**“哪怕你是天王老子，只要你想当因子，就必须遵守的死规则”**（即规范了统一的接口）。你之前在 ops.py 看到的 Abs, Add, Mean, Ref 等所有算子，全都是 Expression 的子类

---
2. 怎么理解 Expression 的核心设计？

​要理解它，你可以把它想象成一棵**“计算树（Expression Tree）”的节点**。

​比如，你在策略里写了一个极其常见的量化因子表达式（一串字符串）：

"Mean($close, 5) / Ref($close, 1)"（大意是：5日均价除以昨收盘价）

​Qlib 的解析引擎在后台拿到这个字符串后，绝对不会把它当成普通的字符串用 eval() 暴力执行，而是会用 Expression 把它组装成一棵树：
```text
               [ Div (这是一个 Expression) ]
                       /           \
                      /             \
[ Mean (这是一个 Expression) ]    [ Ref (这是一个 Expression) ]
          /        \                        /         \
   [ $close ]      [ 5 ]             [ $close ]       [ 1 ]
  (原始特征)      (常数)             (原始特征)       (常数)
```
在这个树状结构里：

​根节点 Div 是一个 Expression。

​左子节点 Mean 是一个 Expression。

​右子节点 Ref 也是一个 Expression。

​甚至连最底层的原始数据集 $close（对应源码里的 Feature 或 PFeature），同样继承自 Expression。

---
​3. Expression 靠什么把这棵树盘活？

​既然大家都是 Expression，那当框架高喊一声：“请给我计算出 2026 年 5 月 21 日这一天的因子数据！”的时候，这棵树是怎么协同工作的呢？
​靠的就是你在源码里看到的两个核心本领：


- ​本领 A：级联加载数据 (load 与 _load_internal)

​当框架调用根节点 Div.load() 时：​Div 会主动去调用左儿子 Mean.load() 和右儿子 Ref.load()。​Mean 又会去调用它底层的 $close.load()。

​最底层的 $close 真正去硬盘/内存里把原始的收盘价 Pandas Series 读出来，返回给 Mean。

​Mean 拿到一堆收盘价，用 Pandas 算好 5 日均线，返回给 Div。

​Ref 也把昨收盘算好返回给 Div。

​最终 Div 把两个 Series 一除，大功告成！

​这就是为什么算子互相嵌套多少层都不会乱，因为它们拥有相同的基类类型，可以用一模一样的方式（多态）互相调用。


- ​本领 B：时序窗口追溯 (get_longest_back_rolling)

​量化回测最怕“未来函数”（即看到了不该看的数据），或者因为数据不够而导致前面几天算不出数（比如算 5 日均线，前 4 天肯定没数据）。

​Expression 规定了每个子类必须能汇报自己“需要往前追溯多少天的数据”。
​
Mean($close, 5) 会汇报：“我需要 5 天的数据。”

​Ref($close, 1) 会汇报：“我需要 1 天的数据。”

​根节点 Div 通过 max(left_br, right_br) 综合一评估：整条流水线在初始化数据时，必须帮我往前多准备 max(5, 1) = 5 天的历史冷启动数据！
