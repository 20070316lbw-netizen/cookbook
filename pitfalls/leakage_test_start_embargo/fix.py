import pandas as pd
import numpy as np

# 构造简单的交易日数据（假设每天都是交易日，这里只做演示）
dates = pd.date_range("2023-01-01", "2023-01-15")
df = pd.DataFrame({
    "date": dates,
    "close": np.arange(10, 25)
})

# label 是未来 3 天后的价格变化
df["label_3d"] = df["close"].shift(-3) - df["close"]

train_end = pd.to_datetime("2023-01-05")

# ❌ 错误写法：测试集紧挨着训练集
test_start_wrong = pd.to_datetime("2023-01-06")
train_df_wrong = df[df["date"] <= train_end]
test_df_wrong  = df[df["date"] >= test_start_wrong]

print("--- ❌ 发生泄露的切分 ---")
print("Train 最后一个样本的 date:", train_df_wrong["date"].max())
# 此样本的 label 算到了 1月8日 的价格！
print("Train 最后一个样本的 label 用到的终点: 2023-01-08")
print("Test 的第一个样本 date:", test_df_wrong["date"].min())
print("🚨 泄露发生：Test 中 1月6日~8日 的价格，在 Train 的 label 里已经被剧透了！\n")


# ✅ 正确写法：使用 embargo (这里 embargo 必须 >= 3 个交易日)
embargo_days = 3
trading_days = pd.Series(df["date"].unique()).sort_values().tolist()
idx = trading_days.index(train_end)
test_start_right = trading_days[idx + embargo_days] # 算出来是 2023-01-08

train_df_right = df[df["date"] <= train_end]
test_df_right  = df[df["date"] >= test_start_right]

print("--- ✅ 无泄露的正确切分 ---")
print("Train 最后一个样本的 date:", train_df_right["date"].max())
print("Test 的第一个样本 date:", test_df_right["date"].min())
print("🔒 成功隔离！Test 开始时，Train 的 label 早已结算完毕，不会产生偷看。")
