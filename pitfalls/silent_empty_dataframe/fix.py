"""失败返回空 DataFrame vs 诚实失败(None / raise),可直接运行对照。"""

import pandas as pd
from loguru import logger

# ---------- 错误写法:静默返回空 DataFrame ----------


def fetch_wrong(fail: bool) -> pd.DataFrame:
    try:
        if fail:
            raise ConnectionError("模拟网络失败")
        return pd.DataFrame({"close": [1.0, 2.0]})
    except ConnectionError as e:
        logger.error(f"抓取失败 - {e}")
        return pd.DataFrame()  # ← 调用方分不清"空数据"还是"出错"


# ---------- 正确写法 1:None 表示"没拿到",逼调用方处理 ----------


def fetch_optional(fail: bool) -> pd.DataFrame | None:
    try:
        if fail:
            raise ConnectionError("模拟网络失败")
        return pd.DataFrame({"close": [1.0, 2.0]})
    except ConnectionError as e:
        logger.error(f"抓取失败 - {e}")
        return None


# ---------- 正确写法 2:要么给数据,要么炸 ----------


def fetch_or_die(fail: bool) -> pd.DataFrame:
    try:
        if fail:
            raise ConnectionError("模拟网络失败")
        return pd.DataFrame({"close": [1.0, 2.0]})
    except ConnectionError as e:
        logger.error(f"抓取失败 - {e}")
        raise


if __name__ == "__main__":
    # 错误写法的危害演示:空 DataFrame 安静流过下游
    df = fetch_wrong(fail=True)
    combined = pd.concat([df, pd.DataFrame({"close": [3.0]})])
    print(f"出错了但管道照跑,结果悄悄少了数据: {len(combined)} 行")  # 只有 1 行

    # 正确写法 1:调用方被迫面对失败
    result = fetch_optional(fail=True)
    if result is None:
        print("fetch_optional: 明确知道失败了,走降级逻辑")

    # 正确写法 2:失败当场炸,错误不过夜
    try:
        fetch_or_die(fail=True)
    except ConnectionError as e:
        print(f"fetch_or_die: 当场暴露 - {e}")
