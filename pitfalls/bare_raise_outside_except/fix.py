"""裸 raise 的错误位置 vs 正确位置,可直接运行对照。"""

from loguru import logger

# ---------- 错误写法:普通路径上裸 raise ----------


def fetch_wrong(ok: bool) -> str:
    if ok:
        return "data"
    else:
        logger.error("没拿到数据")
        raise  # RuntimeError: No active exception to re-raise


# ---------- 正确写法 1:普通路径主动抛,带类型 ----------


def fetch_right_explicit(ok: bool) -> str:
    if ok:
        return "data"
    logger.error("没拿到数据")
    raise ValueError("没拿到数据")


# ---------- 正确写法 2:except 块里 log + 裸 raise 重抛 ----------


def fetch_right_reraise() -> str:
    try:
        raise ConnectionError("模拟网络失败")
    except ConnectionError as e:
        logger.error(f"抓取失败 - {e}")
        raise  # ✅ 这里有"正在处理的异常",裸 raise 合法


if __name__ == "__main__":
    print(fetch_right_explicit(True))

    try:
        fetch_right_explicit(False)
    except ValueError as e:
        print(f"主动抛,正常接住: {e}")

    try:
        fetch_right_reraise()
    except ConnectionError as e:
        print(f"重抛,原异常完整上来: {e}")

    try:
        fetch_wrong(False)
    except RuntimeError as e:
        print(f"错误示范的下场: {e}")
