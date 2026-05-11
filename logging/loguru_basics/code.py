from loguru import logger

logger.add("test.log")   # 加这一行
logger.info("这条会同时在终端和文件里")
logger.warning("这条也是")
logger.debug("这是 debug 信息")
logger.info("这是普通信息")
logger.warning("这是警告")
logger.error("这是错误")
logger.critical("这是严重错误")
