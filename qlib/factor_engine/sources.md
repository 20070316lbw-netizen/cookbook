# 出处和参考

读 microsoft/qlib 文档与源码整理的因子引擎概览。

## qlib 文档
- 仓库主页：https://github.com/microsoft/qlib
- Data Layer / Expression 引擎（Formulaic Alpha 语法、`$close` 字段、算子）：
  https://qlib.readthedocs.io/en/latest/component/data.html
- 缓存机制（`MemCache` / `ExpressionCache` / `DatasetCache`）说明同上文档页

## qlib 源码
- `qlib/data/dataset/loader.py` —— `QlibDataLoader`（示例里用它直接加载表达式计算结果）
  https://github.com/microsoft/qlib/blob/main/qlib/data/dataset/loader.py
- `qlib/data/filter.py` —— `ExpressionDFilter` / `NameDFilter`（动态股票池过滤）
  https://github.com/microsoft/qlib/blob/main/qlib/data/filter.py
- `qlib/data/cache.py` —— `DiskExpressionCache` / `DiskDatasetCache` 的实现
  https://github.com/microsoft/qlib/blob/main/qlib/data/cache.py

## 同 cookbook 内的相关条目
- `qlib/expression_internals/` —— 表达式引擎底下每个算子是怎么实现的
- `qlib/data_flow_concepts/` —— 因子引擎在整条工作流里的位置
