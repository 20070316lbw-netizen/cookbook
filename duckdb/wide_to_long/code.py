"""
宽表 (列=股票/品种,行=日期) ↔ 长表 (每行一个 (datetime, instrument, value)) ,
以及 qlib 风格的 MultiIndex DataFrame: index=(datetime, instrument), columns=features。

原则: **数据库里只存长表**。 宽转长应该发生在「入库之前」的 pandas 侧
(stack / melt) , 入库后增量更新就是纯 append 行, 不用动 schema 。
DuckDB 的 UNPIVOT 只在「数据已经以宽表形态躺在库里」时当补救用。

为什么这么做、谁在用,看 notes.md 和 sources.md。
"""

import duckdb
import pandas as pd


# ---------- 1) 首选: pandas stack , 宽表一步到 qlib 风格 MultiIndex ----------

def wide_to_long_stack(
    df: pd.DataFrame,
    id_col: str = "date",
    name_col: str = "instrument",
    value_name: str = "value",
) -> pd.Series:
    """
    宽表 → 长表的首选写法: set_index + stack 。

    宽表 (df):  date | AAPL | MSFT | GOOG | ...
    返回:       MultiIndex (date, instrument) 的 Series

    比 melt 的优势: 直接得到 (datetime, instrument) 两层索引, 就是 qlib /
    Alphalens 要的形态, 不用再 set_index; 入库时 reset_index() 即是
    (date, instrument, value) 三列长表, 直接 INSERT 。
    """
    s = df.set_index(id_col).stack(future_stack=True).rename(value_name)
    s.index.set_names([id_col, name_col], inplace=True)
    return s.dropna()


# ---------- 2) pandas melt: 要平铺三列长表 (入库) 时用 ----------

def wide_to_long_pandas(
    df: pd.DataFrame,
    id_col: str = "date",
    name_col: str = "instrument",
    value_name: str = "value",
) -> pd.DataFrame:
    """melt 版: 跟 stack 等价, 但返回平铺的三列 DataFrame (没有索引层级)。"""
    return df.melt(
        id_vars=[id_col],
        var_name=name_col,
        value_name=value_name,
    )


# ---------- 3) 补救: 宽表已经在 DuckDB 里时, 用原生 UNPIVOT ----------

def wide_to_long_sql(
    con: duckdb.DuckDBPyConnection,
    table: str,
    id_col: str = "date",
    value_name: str = "value",
    name_col: str = "instrument",
) -> pd.DataFrame:
    """
    用 DuckDB 的 UNPIVOT 把库内宽表转长表。 只该出现在「历史遗留的宽表
    已经在库里」的一次性迁移脚本里 —— 新数据应该在入库前就转成长表。

    宽表 (table):  date | AAPL | MSFT | GOOG | ...
    长表 (返回):   date | instrument | value

    注意: 这里 ON COLUMNS(* EXCLUDE (id_col)) 会把**除 id_col 外**的所有列
    都融成一列 value 。 如果表里同时有多个 feature (close 和 volume) ,
    它们会被混到一起 —— 这种情况要么先按 feature 拆表分别 UNPIVOT,
    要么显式列出要融的列。
    标识符加了双引号, 这样列名带 $ / 空格 / 大小写敏感时也能用 (qlib 的 $close 就是)。
    """
    sql = f"""
    UNPIVOT {table}
    ON COLUMNS(* EXCLUDE ("{id_col}"))
    INTO
        NAME "{name_col}"
        VALUE "{value_name}"
    """
    return con.execute(sql).fetchdf()


# ---------- 4) 长表 → qlib 风格 MultiIndex ----------

def to_multiindex(
    long_df: pd.DataFrame,
    datetime_col: str = "date",
    instrument_col: str = "instrument",
) -> pd.DataFrame:
    """
    把长表变成 qlib / Alpha158 期待的格式:
        index 两层 (datetime, instrument), 其他列就是 features。

    必须 sort_index() , 否则后续 .loc 切片会有 PerformanceWarning。
    """
    df = long_df.copy()
    df[datetime_col] = pd.to_datetime(df[datetime_col])
    # instrument 列重复度高, 转 category 大幅省内存
    df[instrument_col] = df[instrument_col].astype("category")
    return df.set_index([datetime_col, instrument_col]).sort_index()


# ---------- 5) 反向:长表 → 宽表 (做画图/对比时常用) ----------

def long_to_wide_sql(
    con: duckdb.DuckDBPyConnection,
    table: str,
    id_col: str = "date",
    name_col: str = "instrument",
    value_col: str = "value",
    agg: str = "first",
) -> pd.DataFrame:
    """
    DuckDB PIVOT, 长表回宽表。

    agg: 聚合函数名 (first / sum / mean / max ...) 。 默认 first,
         如果 (id_col, name_col) 不该有重复, 用 first 会把脏数据藏起来,
         调试时可以换成 sum/mean 或先 GROUP BY 校验唯一性。
    """
    sql = f"""
    PIVOT {table}
    ON "{name_col}"
    USING {agg}("{value_col}")
    GROUP BY "{id_col}"
    """
    return con.execute(sql).fetchdf()


if __name__ == "__main__":
    # 自测: 宽表 (源头) → stack 成长表 → 入库 → 取出来变 MultiIndex → 回宽表
    wide = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "AAPL": [100.0, 101.0, 102.5],
        "MSFT": [200.0, 201.0, 199.0],
        "GOOG": [300.0, 299.0, 305.0],
    })
    print("== 宽表 (源头拿到的形态) ==")
    print(wide)

    long_s = wide_to_long_stack(wide, value_name="close")
    print("\n== 长表 (pandas stack, 首选) ==")
    print(long_s.head(6))

    long_df_pd = wide_to_long_pandas(wide, value_name="close")
    print("\n== 长表 (pandas melt, 平铺三列) ==")
    print(long_df_pd.head(6))

    # 入库: 数据库里只存长表, 之后每天的新数据 append 行即可
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE prices_long AS SELECT * FROM long_df_pd")

    mi = to_multiindex(con.execute("SELECT * FROM prices_long").fetchdf())
    print("\n== 库里取出来 → MultiIndex (qlib 风格) ==")
    print(mi)

    # 画图 / 对比时偶尔要回宽表
    wide_again = long_to_wide_sql(con, "prices_long", value_col="close")
    print("\n== 长 → 宽 (DuckDB PIVOT) ==")
    print(wide_again)

    # 补救路线: 假如宽表已经在库里了, 才轮到 UNPIVOT
    con.register("prices_wide", wide)
    long_from_sql = wide_to_long_sql(con, "prices_wide", value_name="close")
    print("\n== 长表 (DuckDB UNPIVOT, 库内迁移用) ==")
    print(long_from_sql.head(6))
