# ipdb 调试速查

## 定位

日常调试主力。停下来直接敲 pandas / 任意 Python 表达式查变量，零键位玄学。
覆盖约 80% 场景。复杂 bug 才上 VSCode 图形断点；远程无头服务器用 debugpy attach。
VizTracer / PuDB 知道有就行，特定场景才掏，不是日常。

## 两种启动方式

| 方式 | 命令 | 行为 | 适合 |
|------|------|------|------|
| 软件断点 | 代码写 `breakpoint()` + 配 `PYTHONBREAKPOINT=ipdb.set_trace`，跑 `python x.py` | 跑到断点才进 | 从某点开始看 |
| 外部接管 | `uv run python -m ipdb x.py` | 从第一行接管，且脚本抛异常时自动停在出错帧（验尸） | 不想埋断点 / 专抓崩溃 |

一劳永逸配置（写进 shell rc，让 `breakpoint()` 默认走 ipdb）：

    export PYTHONBREAKPOINT=ipdb.set_trace

临时禁用所有断点不删代码：

    export PYTHONBREAKPOINT=0

## 进去后常用命令

执行控制

- n          单步跳过（next，不进函数）
- s          步入（step，进函数）
- c          继续到下一个断点 / 结束
- r          运行到当前函数 return
- until      不带参 = 运行到比当前行号大的行（跳出循环常用）
- until 20   带参 = 运行到第 20 行
- q          退出

看代码 / 栈

- l          看当前位置周围代码
- ll         看当前整个函数
- l 1,20     看第 1~20 行
- w          看调用栈（where）
- u / d      在栈帧间上 / 下移动

看变量

- p x        打印 x
- pp df      美化打印（看 dict / 嵌套结构 / DataFrame 更清楚）
- 直接敲表达式 df.shape / row.ticker / df.head() 即可

下断点（运行中临时加，不用写 `breakpoint()`）

- b 10                       第 10 行下断点
- b 10, row.ticker=="ABT"    带条件断点（逗号是「行号 / 条件」的分隔符，一行搞定）
- b utils.py:42              别的文件下断点
- b _parse_facts             在函数下断点（不用记行号）
- tbreak 10                  临时断点，命中一次后自动消失
- b                          不带参数 = 列出所有断点
- cl 1                       清除编号 1 的断点（clear）
- disable 1 / enable 1       临时禁用 / 启用，不删

事后验尸（程序已崩，进交互后）

- import ipdb; ipdb.pm()     停到最后一次异常的出错帧

## 坑

1. `*** Blank or comment`
   在空行 / 注释行 / 超出文件末尾的行下断点会报这个。
   ipdb 只能在「会实际执行的代码行」下断点。
   先 `l 行号` 瞄一眼那行是什么，挪到最近的可执行行。

2. 变量名和 ipdb 命令撞车
   想给变量赋值但名字是 ipdb 命令（如 n、s、c、p）会被当命令执行。
   用叹号强制当 Python 执行：`!n = 5`

3. `-m ipdb` 启动 ≠ `breakpoint()`
   `-m ipdb` 从第一行就停，且自带异常验尸；
   `breakpoint()` 是跑到那行才停。抓崩溃用前者，定点查用后者。

4. 验尸模式里 `c` / `s` 会重启程序
   `-m ipdb` 崩溃后进的是 post mortem（验尸）状态，提示
   "Running 'cont' or 'step' will restart the program"。
   想查完就走，直接 `q`；敲 `c` 会从头再跑一遍，不是「继续」。

## 启动方式对照（含其它工具）

- ipdb 主力：`breakpoint()`（本地定点） / `python -m ipdb`（外部接管 + 验尸）
- 复杂 bug 备用：VSCode 行号左边点红点 → F5。条件断点右键红点 → 编辑 → 表达式。
  F10=next  F11=step  F5=continue。
- 远程无头服务器：`python -m debugpy --listen 5678 x.py`，本地 VSCode attach，
  界面在本地、进程在服务器。（未来需要时再展开）

## 记忆口诀

> 定点用 `breakpoint()`，抓崩用 `-m ipdb`；
> 停下直接敲表达式，撞命令名加叹号。
