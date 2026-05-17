import pandas as pd

def make_label_wrong(df):
    # 模拟内部进行了某种排序（比如按 ticker 排序）
    # 返回的 Series 顺序与输入 df 不一致
    return df.sort_values("ticker")["close"].shift(-1)

def make_label_right(df):
    # 即便是乱序的，只要返回的是 Series，带有原本的 index 即可
    return df.sort_values("ticker")["close"].shift(-1)

# 构造一个故意不是严格按 ticker 排序的 df
df = pd.DataFrame({
    "ticker": ["B", "A", "B", "A"],
    "date": ["2023-01-01", "2023-01-01", "2023-01-02", "2023-01-02"],
    "close": [10, 100, 11, 101]
}, index=[0, 1, 2, 3])

print("--- 原始 df ---")
print(df)

# ❌ 错误写法：加上了 .values，破坏了 index 对齐
df_wrong = df.copy()
# df_wrong["label"] = make_label_wrong(df_wrong).values 
# 上面这行会产生难以察觉的错位：
# 因为 sort 之后 A 在前 B 在后，.values 拿出来的数组顺序是 [101, NaN, 11, NaN]
# 硬塞回原 df 时，原 df 第一行是 B，却拿到了 101 这个属于 A 的标签！
try:
    df_wrong["label"] = make_label_wrong(df_wrong).values
    print("\n--- ❌ 错误结果 (静默错位，B 拿到了 A 的标签) ---")
    print(df_wrong)
except Exception as e:
    print(f"Error: {e}")


# ✅ 正确写法：去掉 .values，依赖 index 自动匹配
df_right = df.copy()
# 此时虽然 make_label_right 内部排了序，但是返回的 Series 保留了原有的 index（1, 3, 0, 2）
# 赋值时 Pandas 会根据 index 1, 3, 0, 2 去原 df 找对应的行。
df_right["label"] = make_label_right(df_right)
print("\n--- ✅ 正确结果 (通过 index 完美对齐) ---")
print(df_right)
