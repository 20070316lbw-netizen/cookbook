"""
最小复现：方法漏括号导致 if 恒为真。
直接 uv run python fix.py 跑，对比两种写法的输出。
"""
from pathlib import Path

# 指向一个【确定不存在】的路径
ghost = Path("C:/this/path/definitely/does/not/exist")

print("ghost 真的存在吗？ ->", ghost.exists())   # False，老老实实调用

# ❌ 漏括号：拿到的是方法对象，不是结果
print("\n--- ❌ if ghost.exists （漏括号）---")
print("ghost.exists 是什么 ->", ghost.exists)          # <bound method ...>
print("它的类型 ->", type(ghost.exists))                # <class 'method'>
print("它在 if 里是真还是假 ->", bool(ghost.exists))     # True ！！！
if ghost.exists:
    print(">>> 走进了 if 分支：程序以为文件存在（错！）")
else:
    print(">>> 走进了 else 分支")

# ✅ 加括号：拿到的是 True / False
print("\n--- ✅ if ghost.exists() （正确）---")
if ghost.exists():
    print(">>> 走进了 if 分支：文件存在")
else:
    print(">>> 走进了 else 分支：文件不存在（对！）")

# ⚠️ 反例：df.empty 是属性，不加括号才对
import pandas as pd
df = pd.DataFrame()
print("\n--- ⚠️ 反例：df.empty 是属性，本就不该加括号 ---")
print("df.empty ->", df.empty, "| 类型 ->", type(df.empty))  # True | <class 'bool'>
