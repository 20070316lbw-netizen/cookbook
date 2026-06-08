# 出处和参考

`mini_engine.py` 是为了理解「声明式表达式 → 底层执行」这一思想，手写的最小 Demo，
并非抄某段现成代码；对照对象是 qlib 的真实表达式引擎。

## 对照的工业级实现
- microsoft/qlib `qlib/data/ops.py` —— 真正的算子树（本 Demo 用正则模拟）
  https://github.com/microsoft/qlib/blob/main/qlib/data/ops.py
- WorldQuant 101 Alphas —— Formulaic Alpha 的经典出处（论文）：
  https://arxiv.org/abs/1601.00991

## Demo 用到 / notes 里提到的技术点
- `pandas.eval`：https://pandas.pydata.org/docs/reference/api/pandas.eval.html
- `re`（正则，本 Demo 的「伪解析器」）：https://docs.python.org/3/library/re.html
- 为什么裸 `eval` 危险（RCE）、工业级该用 AST/沙盒：
  `asteval` https://newville.github.io/asteval/ 、Python `ast` https://docs.python.org/3/library/ast.html

## 同 cookbook 内的相关条目
- `qlib/expression_internals/` —— qlib 真正怎么把表达式组成计算树
- `pitfalls/rolling_index_misalign/` —— `mean_func` 里 `groupby().rolling()` 的对齐坑
