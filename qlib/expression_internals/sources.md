# 出处和参考

读 microsoft/qlib 源码做的笔记。

## qlib 源码（核心）
- 仓库主页：https://github.com/microsoft/qlib
- `qlib/data/ops.py` —— 所有算子（`Abs` / `Add` / `Mean` / `Ref` …）的定义，
  `ExpressionOps` 基类、`__str__` / `_load_internal`、`get_longest_back_rolling`、
  以及四大算子家族（`ElemOperator` / `PairOperator` / `Rolling` / `TResample`）
  https://github.com/microsoft/qlib/blob/main/qlib/data/ops.py
- `qlib/data/base.py` —— `Expression` 抽象基类、`Feature` / `PFeature` 叶子节点的定义
  https://github.com/microsoft/qlib/blob/main/qlib/data/base.py
- `_libs/rolling`（Cython）—— `Rolling` 家族里 `Slope` / `Rsquare` 等的底层加速实现

## Python 知识点
- `isinstance` / `type` 内置函数：https://docs.python.org/3/library/functions.html#isinstance

## 同 cookbook 内的相关条目
- `qlib/factor_engine/` —— 这套算子组成的表达式引擎在更高层怎么用
- `qlib/mini_factor_engine/` —— 手写一个最小版理解 Expression → 计算的过程
