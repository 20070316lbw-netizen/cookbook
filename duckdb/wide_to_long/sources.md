# 出处和参考

## 长表 / tidy data 概念的源头
- Hadley Wickham. *Tidy Data*. Journal of Statistical Software, 2014.
  https://vita.had.co.nz/papers/tidy-data.pdf
  → 「每行一个观测、每列一个变量」就是这篇定义的。R 里 `tidyr`、
  Python 里 `pandas.melt` 的设计都来自这里。

## qlib (微软量化平台) —— MultiIndex 长格式的工业用法
- 仓库主页: https://github.com/microsoft/qlib
- `qlib/data/data.py` —— `DatasetProvider` / `LocalDatasetProvider` ,
  负责把底层「长存」的 .bin 文件拼成 `(datetime, instrument)` MultiIndex DataFrame
  https://github.com/microsoft/qlib/blob/main/qlib/data/data.py
- `qlib/data/dataset/__init__.py` —— `DatasetH` / `DataHandlerLP` ,
  对模型暴露的就是 MultiIndex DataFrame
  https://github.com/microsoft/qlib/blob/main/qlib/data/dataset/__init__.py
- `qlib/contrib/data/handler.py` —— `Alpha158` / `Alpha360` ,
  Alpha 因子全部基于 `groupby("instrument")` + rolling , 也就是长表的写法
  https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/handler.py

## Alphalens (Quantopian) —— 因子分析的标准长格式
- 仓库: https://github.com/quantopian/alphalens
  → `get_clean_factor_and_forward_returns` 的输入就是
  MultiIndex `(date, asset)` 的 Series ,跟 qlib 一脉相承。

## DuckDB 文档 (UNPIVOT / PIVOT 的具体语法)
- UNPIVOT: https://duckdb.org/docs/sql/statements/unpivot.html
- PIVOT:   https://duckdb.org/docs/sql/statements/pivot.html
  → DuckDB 的 PIVOT/UNPIVOT 借鉴自 Snowflake / SQL Server , 比标准 SQL
  好用很多 (支持 `COLUMNS(* EXCLUDE ...)` ) 。

## pandas 文档 (melt / stack / unstack)
- Reshaping and pivot tables:
  https://pandas.pydata.org/docs/user_guide/reshaping.html
- `DataFrame.melt`: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.melt.html
