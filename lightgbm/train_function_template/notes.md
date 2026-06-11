关于lightgbm里面的参数配置  --code.py里面有完整代码示例
原生风格(LightGBM 文档里更常见,有大字典)
```python
import lightgbm as lgb

# 这就是你说的"大字典"
params = {
    'objective': 'regression',
    'metric': 'rmse',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1,
}

# 数据要先包装成 Dataset 格式
train_data = lgb.Dataset(X_train, label=y_train)
valid_data = lgb.Dataset(X_valid, label=y_valid, reference=train_data)

# 训练
model = lgb.train(
    params,
    train_data,
    num_boost_round=100,
    valid_sets=[valid_data],
)
```

用方法写出来就是先在顶部写参数
```python
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
```

然后在下面写方法:
```python
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
        X_valid: 验证集特征(可选,训练时打印 valid 上的 metric)
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
```


关键设计要点(这才是真正想让你学的)
1. 参数字典抽出来当常量或参数
```python
# ❌ 不好:写死在函数里
def train(X, y):
    params = {'num_leaves': 31, ...}
    ...

# ✅ 好:抽出来
DEFAULT_PARAMS = {...}
def train(X, y, params=DEFAULT_PARAMS):
    ...
```
为什么:你想调参时不用改函数内部,只要传新的 params 进去。这就是「配置和逻辑分离」。


2. 把「训练」和「预测」拆成两个函数
```python
def train_lightgbm(...): ...  # 只负责训练
def predict(...): ...          # 只负责预测
```
为什么:训练只做一次(花时间),预测要做很多次(每天对新数据)。拆开后:
训练完可以把 model 存到磁盘
预测时直接 load 模型,不用每次重训


3. if __name__ == "__main__": 里写「自测」
这是 Python 的标准结构:模块被 import 时不执行,直接跑文件时执行。
```python
# 别的文件这么用
from lightgbm.train import train_lightgbm, predict

model = train_lightgbm(my_X, my_y)
preds = predict(model, new_X)
```
这就是「写成方法」的真正意义——让别的文件能 import 你的功能,而不是复制代码。

4. 类型提示
```python
def train_lightgbm(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    params: Dict[str, Any] = None,
) -> lgb.Booster:
```
这里 Dict[str, Any] 表示「键是字符串、值可以是任意类型的字典」——params 字典里既有 int(31)也有 float(0.05)也有 str('regression'),所以用 Any。