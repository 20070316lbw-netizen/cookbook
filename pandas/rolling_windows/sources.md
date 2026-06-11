# 出处和参考

## 原始来源

- pandas 官方文档 Windowing operations:
  https://pandas.pydata.org/docs/user_guide/window.html
- qlib 的 Rolling 算子家族 (`qlib/data/ops.py`, `Mean`/`Std`/`Ref` 等) ——
  panel 上"按 instrument 各自滚动"的工业参照

## 相关链接

- `Series.rolling` API: https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html
- `GroupBy.transform`: https://pandas.pydata.org/docs/reference/api/pandas.core.groupby.DataFrameGroupBy.transform.html

## 同 cookbook 内的相关条目

- `lightgbm/quant_pipeline_basics/` —— `_roll` 就是这里 panel 写法的实际使用
- `pitfalls/rolling_index_misalign/` —— `.groupby().rolling()` 多包一层索引导致赋值错位
- `qlib/expression_internals/` —— qlib Rolling 算子家族 (N=0 是 expanding, 0<N<1 是 ewm)
