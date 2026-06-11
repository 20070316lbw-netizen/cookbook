# try / except / raise 固定形状

## 1. 标准三件套

```python
try:
    resp = requests.get(URL, headers=HEADERS)
    resp.raise_for_status()
    return parse(resp.json())
except requests.RequestException as e:   # ① 捕谁 + 起名
    logger.error(f"抓取失败 - {e}")       # ② 先记日志
    raise                                 # ③ 再原样重抛
```

分工铁律:`except` 行只负责"捕到谁",块体内才是"捕到之后干什么"。
log 一行、raise 一行,各占一行,不要挤进 except 那一行。

## 2. raise 的两种写法

```python
raise ValueError("没拿到数据")  # 主动抛:必须带异常类型
raise                          # 重抛:只能在 except 块里
```

裸 `raise` 的语义是**重新抛出当前正在处理的异常**。在 except 之外写裸 raise,
没有"正在处理的异常"可重抛,直接
`RuntimeError: No active exception to re-raise`(见 pitfalls/bare_raise_outside_except)。

"log 完再裸 raise" 是数据管道的标准动作:日志留痕,异常原样上抛,调用方该炸还炸。

## 3. except 跟什么类型

原则:**只捕你预期会发生、且知道怎么处理的**,其余让它炸。

- 裸 `except:` 是大忌——连 `NameError`(拼错变量)、`KeyboardInterrupt`(Ctrl+C)
  都吞,bug 被消音而不是被消灭
- requests 场景:`ConnectionError` 只管"连不上";`raise_for_status()` 抛的是
  `HTTPError`(403/404 等)。要两个都接住,捕它们共同的父类
  `requests.RequestException`
- 常用异常一只手数得过来:`ValueError`(值不对)、`KeyError`(键不存在)、
  `TypeError`(类型不对),加上具体库自己的异常

## 4. requests 的暗坑

`requests.get` 拿到 403/404 **不抛异常**,安静返回一个错误响应。
必须主动 `resp.raise_for_status()` 让非 2xx 变成异常。
调用过它之后,后面再写 `if resp.status_code != 200` 就是死代码——
能走到那一行,状态码必然是 2xx。
