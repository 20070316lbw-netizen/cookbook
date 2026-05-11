初级写法:
```python
print("缺失值检查完成")
print(f"发现 {n} 处异常")
```

用loguru:
```python
from loguru import logger

logger.info("缺失值检查完成")
logger.warning(f"发现 {n} 处异常")
```

看起来就是把 print 换成 logger.xxx,但效果差别巨大。
---
为什么不直接用 print?
print 的 3 个致命问题:
问题 1:print 不分级
```python 
print("数据加载完成")           # 这是普通信息
print("发现 5 处缺失值")        # 这是警告
print("数据库连接失败!")        # 这是严重错误
```
所有 print 看起来都一样。代码量小时无所谓,但你 quant 项目以后跑起来,屏幕上滚几百条 print,你根本分不清哪些重要、哪些可以忽略。
logger 解决这个,它有 5 个等级(从低到高):

DEBUG     调试细节,平时不看   "进入了 check_ohlcv 函数"
INFO      正常流程信息        "数据加载完成"
WARNING   有点不对劲但能继续  "发现 5 处缺失值"
ERROR     出错了但程序没崩    "某只股票拉取失败,跳过"
CRITICAL  严重错误,程序要崩   "数据库连不上,无法继续"

怎么写:
```python
logger.debug("...")     # 灰色
logger.info("...")      # 蓝色
logger.warning("...")   # 黄色
logger.error("...")     # 红色
logger.critical("...")  # 红色加粗
```


问题 2:print 没有时间戳
```python
print("数据加载完成")
# 输出:数据加载完成
pythonlogger.info("数据加载完成")
# 输出:2026-05-11 14:32:18.421 | INFO | 数据加载完成
```
时间戳意味着:你能看出来某一步花了多久。比如:
```txt
2026-05-11 14:32:18 | INFO | 开始拉取标普500数据
2026-05-11 14:47:02 | INFO | 数据拉取完成
```


问题 3:print 没法记到文件里
print 只在终端显示,关掉就没了。
logger 一行配置就能同时写到文件:
```python
from loguru import logger

logger.add("logs/quant.log", rotation="10 MB")
# 之后所有 logger.xxx 调用,既在终端显示,也写到 logs/quant.log
# rotation="10 MB" 意思是日志文件超过 10MB 自动切新文件
```
这件事有多重要:你 quant 项目跑一晚上回测,跑完关掉终端,第二天发现结果不对——日志在文件里,你能翻回去看;用 print,你只能重新跑一遍。


最后接上代码示范  --code.py
```powershell
uv add loguru
```
```python
from loguru import logger

logger.debug("这是 debug 信息")
logger.info("这是普通信息")
logger.warning("这是警告")
logger.error("这是错误")
logger.critical("这是严重错误")
```

警告写入文件
```python
from loguru import logger

logger.add("test.log")   # 加这一行
logger.info("这条会同时在终端和文件里")
logger.warning("这条也是")
```

