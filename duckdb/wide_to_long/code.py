"""
把存进 DuckDB 的「宽表」(列=股票/品种,行=日期) 转成「长表」
(每行一个 (datetime, instrument, value) ),再升一档变成 qlib 风格的
MultiIndex DataFrame: index=(datetime, instrument), columns=features。

为什么这么做、谁在用,看 notes.md 和 sources.md。
"""

import duckdb
import pandas as pd


# ---------- 1) SQL 侧:DuckDB 原生 UNPIVOT ----------

def wide_to_long_sql(
    con: duckdb.DuckDBPyConnection,
    table: str,
    id_col: str = "date",
    value_name: str = "value",
    name_col: str = "instrument",
) -> pd.DataFrame:
    """
    用 DuckDB 的 UNPIVOT 把宽表转长表。

    宽表 (table):  date | AAPL | MSFT | GOOG | ...
    长表 (返回):   date | instrument | value
    """
    sql = f"""
    UNPIVOT {table}
    ON COLUMNS(* EXCLUDE ({id_col}))
    INTO
        NAME {name_col}
        VALUE {value_name}
    """
    return con.execute(sql).fetchdf()


# ---------- 2) pandas 侧:melt ----------

def wide_to_long_pandas(
    df: pd.DataFrame,
    id_col: str = "date",
    name_col: str = "instrument",
    value_name: str = "value",
) -> pd.DataFrame:
    """pandas 版,等价于 DuckDB 的 UNPIVOT。"""
    return df.melt(
        id_vars=[id_col],
        var_name=name_col,
        value_name=value_name,
    )


# ---------- 3) 长表 → qlib 风格 MultiIndex ----------

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


# ---------- 4) 反向:长表 → 宽表 (做画图/对比时常用) ----------

def long_to_wide_sql(
    con: duckdb.DuckDBPyConnection,
    table: str,
    id_col: str = "date",
    name_col: str = "instrument",
    value_col: str = "value",
) -> pd.DataFrame:
    """DuckDB PIVOT, 长表回宽表。"""
    sql = f"""
    PIVOT {table}
    ON {name_col}
    USING first({value_col})
    GROUP BY {id_col}
    """
    return con.execute(sql).fetchdf()


if __name__ == "__main__":
    # 自测: 构造宽表 → 长表 → MultiIndex → 回宽表
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE prices AS
        SELECT * FROM (VALUES
            ('2024-01-01', 100.0, 200.0, 300.0),
            ('2024-01-02', 101.0, 201.0, 299.0),
            ('2024-01-03', 102.5, 199.0, 305.0)
        ) AS t(date, AAPL, MSFT, GOOG)
    """)

    print("== 宽表 ==")
    print(con.execute("SELECT * FROM prices").fetchdf())

    long_df = wide_to_long_sql(con, "prices", value_name="close")
    print("\n== 长表 (DuckDB UNPIVOT) ==")
    print(long_df)

    long_df_pd = wide_to_long_pandas(
        con.execute("SELECT * FROM prices").fetchdf(),
        value_name="close",
    )
    print("\n== 长表 (pandas melt, 等价) ==")
    print(long_df_pd)

    mi = to_multiindex(long_df)
    print("\n== MultiIndex (qlib 风格) ==")
    print(mi)

    # 把长表灌回 DuckDB, 再 PIVOT 回宽表
    con.register("long_df", long_df)
    wide_again = long_to_wide_sql(con, "long_df", value_col="close")
    print("\n== 长 → 宽 (DuckDB PIVOT) ==")
    print(wide_again)
