"""
一句话说明这段代码是什么、从哪学来的、通用化成了什么形式。

输入/输出的统一约定写在这里（比如「输入是一个 daily returns Series，
index 是日期，值是单期简单收益率」），细节和坑放 notes.md，出处放 sources.md。
"""

import numpy as np
import pandas as pd


# 参数/配置抽成模块级常量，方便以后换成 yaml 配置驱动
DEFAULT_PARAMS = {
    # "key": value,
}


def do_something(data: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
    """
    一句话说明这个函数做什么。

    Args:
        data: 输入数据的形状/索引约定
        params: 超参数字典，不传则用 DEFAULT_PARAMS

    Returns:
        返回值的形状/含义
    """
    if params is None:
        # .copy() 防止函数内修改 params 时反过来污染全局 DEFAULT_PARAMS
        params = DEFAULT_PARAMS.copy()
    raise NotImplementedError


if __name__ == "__main__":
    # 自测：构造最小可跑的样例数据，直接 python code.py 就能看到效果
    pass
