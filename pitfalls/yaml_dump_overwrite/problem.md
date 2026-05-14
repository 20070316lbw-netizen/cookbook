# yaml.dump 整个覆盖文件,冲掉手写的其他配置块

## 坑长什么样

`config.yaml` 里有两块内容:`data`(脚本生成的)和 `model`(手写的):

```yaml
data:
  start: '2024-05-12'
  end: '2025-05-12'
  splits: { ... }
model:              # 手动加的 lightgbm 超参
  objective: regression
  num_leaves: 31
  learning_rate: 0.05
```

`generate_config.py` 里这样写:

```python
config = {"data": {...}, "splits": {...}}
with open(output_path, "w") as f:
    yaml.dump(config, f)
```

跑一次 `generate_config.py` 后,**整个 `model` 块消失了** ——
后面 `train_lgb.py` 读 `cfg["model"]` 直接拿不到东西。

## 为什么会炸

`open(path, "w")` 是**覆盖写**:打开就先清空整个文件。
`yaml.dump(config, f)` 只把 `config` 这个 dict 写进去。
`config` 里只有 `data`,没有 `model` —— 所以 `model` 块被冲没了。

脚本"只生成 data",但写文件的方式是"重写整个文件",
两者不匹配 —— 凡是脚本不知道的内容,全部丢失。

## 解决:先读后改再写,只动自己负责的 key

```python
# 1. 文件已存在就先读出来
if output_path.exists():
    with open(output_path, "r", encoding="utf-8") as f:
        existing = yaml.safe_load(f) or {}
else:
    existing = {}

# 2. 只替换自己负责的那个 key
existing["data"] = data_block   # model 等其他 key 原样保留

# 3. 写回
with open(output_path, "w", encoding="utf-8") as f:
    yaml.dump(existing, f, default_flow_style=False,
              allow_unicode=True, sort_keys=False)
```

## 教训

1. `open(path, "w")` 会先清空文件。配置文件如果由"多个来源"共同维护
   (一部分脚本生成、一部分手写),绝不能整体覆盖。
2. 模式:**读 → 改自己那部分 → 写回**。脚本只碰自己负责的 key。
3. `yaml.dump` 加参数:
   - `allow_unicode=True` —— 中文不被转义成 \uXXXX
   - `sort_keys=False` —— 保持 dict 原顺序,不按字母重排,人读着顺
   - `default_flow_style=False` —— 用展开的块状格式,不挤成一行
4. 用 `yaml.safe_load`,不要用 `yaml.load`(后者能执行任意对象,不安全)。
5. 脚本的 docstring 里写清楚"本脚本只负责 X 部分",避免下次自己也忘了。
