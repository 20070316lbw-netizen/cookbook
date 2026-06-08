"""
最小复现：裸 raise 在没有活跃异常时会变成 RuntimeError。
"""

# ❌ 错误：else 分支里裸 raise，此处没有正在处理的异常
def wrong():
    flag = False
    if flag:
        print("ok")
    else:
        raise          # 这里炸：RuntimeError: No active exception to reraise

# ✅ 正确用法一：在 except 里裸 raise，原样再抛
def right_reraise():
    try:
        int("not a number")
    except ValueError:
        print("记一笔日志，然后把原异常原样抛出去")
        raise          # 合法：重新抛出刚捕获的 ValueError

# ✅ 正确用法二：主动报错就指定类型和信息
def right_new_error():
    flag = False
    if not flag:
        raise FileNotFoundError("我明确知道自己要报什么错")


if __name__ == "__main__":
    print("--- ❌ wrong() ---")
    try:
        wrong()
    except Exception as e:
        print(f"{type(e).__name__}: {e}")   # RuntimeError: No active exception to reraise

    print("\n--- ✅ right_reraise() ---")
    try:
        right_reraise()
    except Exception as e:
        print(f"{type(e).__name__}: {e}")   # ValueError: invalid literal ...

    print("\n--- ✅ right_new_error() ---")
    try:
        right_new_error()
    except Exception as e:
        print(f"{type(e).__name__}: {e}")   # FileNotFoundError: 我明确知道...
