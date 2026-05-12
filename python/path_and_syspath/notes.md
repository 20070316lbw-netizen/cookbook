# `__file__` 路径拆解 和 `sys.path.insert`

## 1. `__file__` 是什么

`__file__` 是 Python 的内置变量，代表**当前这个文件自己的路径**。

```python
# 假设当前文件是 utils/config.py
print(__file__)  # C:/Users/liu/Desktop/quant/utils/config.py
```

---

## 2. 用 `.parent` 一层层往上走

```python
from pathlib import Path

Path(__file__).resolve()          # C:/Users/liu/Desktop/quant/utils/config.py （绝对路径）
Path(__file__).resolve().parent   # C:/Users/liu/Desktop/quant/utils/
Path(__file__).resolve().parent.parent  # C:/Users/liu/Desktop/quant/   ← 项目根目录
```

- `.resolve()` — 把相对路径变成绝对路径，消除 `../..` 这种写法
- `.parent` — 往上一层目录，需要几层就写几个 `.parent`

实际用法（`utils/config.py` 里）：

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_ROOT / "database"
DEFAULT_DB = DB_DIR / "sp500.duckdb"
```

`/` 是 pathlib 的路径拼接运算符，等价于 `os.path.join`。

---

## 3. `sys.path.insert` 是干什么的

Python 跑一个文件时，去 `sys.path` 这个列表里的路径逐个查找 `import` 的模块。

**问题场景：**

```
quant/
  utils/config.py
  scripts/fetch_data.py   ← 从这里跑
```

在 `scripts/fetch_data.py` 里写 `from utils.config import ...`，
Python 默认只认识 `scripts/` 这一层，找不到 `utils/`，报 `ModuleNotFoundError`。

**解决方法：** 在文件开头手动把项目根目录塞进 `sys.path`：

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# 现在 Python 知道去 quant/ 下找模块了
from utils.config import get_db  # ✅
```

拆解：
```
__file__              →  quant/scripts/fetch_data.py
.parent               →  quant/scripts/
.parent.parent        →  quant/           ← 塞这个进 sys.path
```

---

## 4. 为什么 `utils/config.py` 自己不需要写这行

因为 `config.py` 只 import 安装好的第三方库（`duckdb`、`pathlib`），
Python 自己就能找到，不需要手动指路。

只有当你要 import **项目内部其他模块**，而运行目录不是项目根目录时，才需要这行。

---

## 5. 记忆口诀

> `__file__` 是自己，`.parent` 是往上一层，
> 需要几层就写几个 `.parent`，
> `sys.path.insert` 是"告诉 Python 去哪里找东西"。
