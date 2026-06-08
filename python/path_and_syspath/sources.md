# 出处和参考

## Python 官方文档
- `__file__` / 模块导入机制：https://docs.python.org/3/reference/import.html
- `sys.path`：https://docs.python.org/3/library/sys.html#sys.path
- `pathlib`（`Path` / `.resolve()` / `.parent` / `/` 拼接）：
  https://docs.python.org/3/library/pathlib.html

## 背景
- 自己量化项目里 `scripts/` 子目录脚本 `from utils.config import ...` 报
  `ModuleNotFoundError` 时定位出来的，是 `sys.path.insert` 这一行的来由。

## 同 cookbook 内的相关条目
- `pitfalls/script_import_modulenotfound/` —— 同一个坑的「踩坑两件套」版本
