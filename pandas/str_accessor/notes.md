# `.str` 访问器:对整列做字符串操作

## 1. 为什么要先 `.str`

`zfill`、`upper`、`replace`、`contains` 这些是**单个字符串**的方法。
Series 是一列字符串,不能直接调——pandas 要求先经过 `.str` 访问器,
它负责"把这个字符串方法逐元素应用到整列"。

```python
cik_map["cik"] = cik_map["cik_str"].astype(str).str.zfill(10)
#                                   ─────────  ───  ─────────
#                                   先转字符串  访问器  补零到10位
```

- 直接 `.zfill(10)` 会报错:Series 没有这个方法
- `.astype(str)` 在前:原列若是 int(如 EDGAR 的 cik_str),要先转成字符串
- `.str.zfill(10)`:左边补零到 10 位,`320193` → `"0000320193"`

## 2. 实战出处

SEC EDGAR 的 CIK 在 JSON 里是裸数字,但 API URL 要求 10 位补零字符串
(`CIK0000320193.json`)。入库前统一 `astype(str).str.zfill(10)`,
后续拼 URL 直接用。

## 3. 同族方法速记

```python
s.str.upper()          # 整列大写
s.str.replace("a","b") # 整列替换
s.str.contains("BANK") # 整列布尔筛选,常配 df[mask]
s.str.split("-")       # 整列切分
```

口诀:**单个字符串的方法,想用在整列上,中间垫一层 `.str`。**
(同理:日期方法垫 `.dt`,分类方法垫 `.cat`)
