import lightgbm as lgb
import pandas as pd
from typing import Dict, Any


# 把参数提到外面(以后做配置驱动就是把它移到 yaml 文件)
DEFAULT_PARAMS = {
    'objective': 'regression',
    'metric': 'rmse',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1,
}


def train_lightgbm(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_valid: pd.DataFrame = None,
    y_valid: pd.Series = None,
    params: Dict[str, Any] = None,
    num_boost_round: int = 100,
) -> lgb.Booster:
    """
    训练一个 LightGBM 模型
    
    Args:
        X_train: 训练集特征
        y_train: 训练集标签
        X_valid: 验证集特征(可选,用于 early stopping)
        y_valid: 验证集标签(可选)
        params: LightGBM 超参数字典,不传则用默认
        num_boost_round: 训练多少棵树
    
    Returns:
        训练好的 LightGBM 模型
    """
    # 如果没传 params,用默认
    if params is None:
        params = DEFAULT_PARAMS
    
    # 包装数据
    train_data = lgb.Dataset(X_train, label=y_train)
    
    valid_sets = [train_data]
    if X_valid is not None and y_valid is not None:
        valid_data = lgb.Dataset(X_valid, label=y_valid, reference=train_data)
        valid_sets.append(valid_data)
    
    # 训练
    model = lgb.train(
        params,
        train_data,
        num_boost_round=num_boost_round,
        valid_sets=valid_sets,
    )
    
    return model


def predict(model: lgb.Booster, X: pd.DataFrame) -> pd.Series:
    """用训练好的模型预测"""
    return model.predict(X)


if __name__ == "__main__":
    # 这里写「自测」逻辑——单独跑这个文件时执行
    # 真正用的时候是别的文件 import 这两个函数
    
    # 假数据
    import numpy as np
    X = pd.DataFrame(np.random.randn(100, 5), columns=[f'f{i}' for i in range(5)])
    y = pd.Series(np.random.randn(100))
    
    # 训练
    model = train_lightgbm(X, y)
    
    # 预测
    preds = predict(model, X)
    print(f"预测前 5 个: {preds[:5]}")