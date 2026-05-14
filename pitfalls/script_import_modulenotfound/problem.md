# 直接跑子目录脚本报 ModuleNotFoundError: No module named 'utils'

## 坑长什么样

项目结构:

```
quant/
├── utils/config.py
├── features/make_features.py   # 里面有 from utils.config import get_db
└── labels/make_labels.py       # 里面有 from utils.config import get_db
```

在项目根目录运行:

```bash
uv run python features/make_features.py
```

报错:

```
ModuleNotFoundError: No module named 'utils'
```

## 为什么会炸

用 `python 路径/脚本.py` 这种方式运行时,Python 把
**脚本所在的目录**(这里是 `features/`)加进 `sys.path`,
而**不是**项目根目录。

所以 `from utils.config import ...` 找不到 `utils` ——
因为 `utils/` 在项目根下,不在 `features/` 下。

(对比:`scripts/generate_config.py` 能跑,是因为它开头手动
`sys.path.insert(0, 项目根)` 了。)

## 三种解法

### 解法 1:用 `python -m` 运行(零代码改动,最干净)

```bash
# 在项目根目录下
uv run python -m features.make_features
uv run python -m labels.make_labels
```

`-m` 会把**当前工作目录**加进 `sys.path`,`utils` 就能被找到。
缺点:得记得用 `-m`,且路径分隔符是 `.` 不是 `/`。

### 解法 2:在脚本的 __main__ 块里加 sys.path hack

只在直接运行时把项目根加进 path,被 import 时不污染 path。
关键:**让核心函数本身不依赖 utils**,把依赖 utils 的 import
挪进 `__main__` 块。见 fix.py。

### 解法 3:把项目装成可编辑包(长期最佳)

`pyproject.toml` 里配好包,然后:

```bash
uv pip install -e .
```

之后 `utils` 成为环境里可见的包,从任何地方跑都行。
适合项目稳定后做,初期略重。

## 教训

1. `python path/to/script.py` 加的是**脚本所在目录**,不是项目根 —— 这是 import 失败的根因。
2. 同一个项目里别让"有的脚本能直接跑、有的不能",要么全用 `-m`,要么所有 entry 文件统一处理。
3. sys.path hack 放进 `__main__` 块,不要放文件顶部 —— 顶部会污染所有 import 它的代码。
4. 让核心函数(如 `make_features`)保持纯粹、不依赖项目配置;只有 `__main__` 自测部分才 import `utils`。
