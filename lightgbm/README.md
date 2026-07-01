# lightgbm/ 目录说明

这个目录下大部分内容按仓库惯例放在子文件夹里 (`code.py` / `notes.md` /
`sources.md` 三件套, 见根目录 `README.md`) 。 下面两个文件是例外: 直接放在
`lightgbm/` 下面, 不是新技术, 只是把各子文件夹的方法"调出去"接成完整的
训练 + 评估示范, 方便一眼看到整条流水线怎么串起来、几种训练方式差在哪。

- **`demo_full_pipeline.py`** —— 三种训练方式在同一份 (15% 标签被污染的)
  合成数据上对比日均 IC:
  1. `train_function_template.train_lightgbm` (最朴素版)
  2. `quant_pipeline_basics.train_lgb` (规范单模型, early stopping 走 callbacks)
  3. `double_ensemble.train_double_ensemble` (SR + FS, 治样本/特征噪声)

- **`demo_walk_forward.py`** —— 把 `evaluation/walk_forward_validation/`
  的通用 walk-forward + "信号 vs 噪音"检验接到单棵 LightGBM 和
  DoubleEnsemble 上, 在同一份合成量化面板数据上跑, 看两者的样本外 IC
  是否显著甩开"label 打乱后"的零分布, 以及谁更稳。

两个都直接 `python lightgbm/demo_xxx.py` (在仓库根目录) 就能跑。

## 跨文件夹 import 的坑: 包名撞车

`quant_pipeline_basics/`、`double_ensemble/`、`train_function_template/`
都没有 `__init__.py`, 也没装成包 (跟 `pitfalls/script_import_modulenotfound/`
描述的情形一样) 。 这两个 demo 文件用的写法是:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # 加进 lightgbm/ 这个目录

import quant_pipeline_basics.code as qpb
import double_ensemble.code as de
```

**千万不要**写成 `import lightgbm.quant_pipeline_basics.code`——
`lightgbm` 这个顶层包名已经被 pip 装的真正 LightGBM 库占用了。 Python 的
路径查找器在 `sys.path` 的每个入口里找 `lightgbm`, 只要任何一个入口下有
*regular package* (带 `__init__.py`, 也就是 site-packages 里那个真正的库) ,
它就会赢过本地这个只是"一堆目录"形成的 *namespace package* , 于是
`lightgbm` 解析到的是真正的 LightGBM 库, 根本走不到
`quant_pipeline_basics` 子模块, 报 `ModuleNotFoundError`。 反过来,
`import lightgbm as lgb` 在 `code.py` 内部之所以还能正确拿到真正的库,
是因为同样的优先级规则——只要 site-packages 在 `sys.path` 里, 真库永远
赢。 这两者不矛盾, 只是"永远不要用 `lightgbm.` 前缀去 import 本仓库自己的
文件"。

`demo_walk_forward.py` 还需要跨到 `lightgbm/` 之外的
`evaluation/walk_forward_validation/`, 多加了一行把仓库根目录也塞进
`sys.path`, 通过 `evaluation.walk_forward_validation.code` 这条路径进去——
这条路径不涉及 "lightgbm" 这个名字, 不会有上面的撞车问题。
