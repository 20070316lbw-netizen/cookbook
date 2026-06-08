"""
to_csv(index=False) 速查：为什么写 CSV 几乎总要带 index=False。
跑一下看两种写法落地的 CSV 差别。
"""
import pandas as pd
from io import StringIO

df = pd.DataFrame({
    "symbol": ["MMM", "AOS", "ABT"],
    "security": ["3M", "A. O. Smith", "Abbott"],
})

# ❌ 默认 index=True：把行号 0,1,2 也写进 CSV，多出一列无名列
buf_wrong = StringIO()
df.to_csv(buf_wrong)                    # 没传 index
print("--- ❌ 默认（index=True）---")
print(buf_wrong.getvalue())
# ,symbol,security        ← 第一列是空表头的行号
# 0,MMM,3M
# 1,AOS,A. O. Smith
# 2,ABT,Abbott

# ✅ index=False：只写真正的数据列
buf_right = StringIO()
df.to_csv(buf_right, index=False)
print("--- ✅ index=False ---")
print(buf_right.getvalue())
# symbol,security
# MMM,3M
# AOS,A. O. Smith
# ABT,Abbott

# 验证：错误写法读回来会多一列垃圾
print("--- 默认写法读回来 ---")
print(pd.read_csv(StringIO(buf_wrong.getvalue())).columns.tolist())
# ['Unnamed: 0', 'symbol', 'security']  ← 那列垃圾变成了 Unnamed: 0

print("--- index=False 写法读回来 ---")
print(pd.read_csv(StringIO(buf_right.getvalue())).columns.tolist())
# ['symbol', 'security']  ← 干净
