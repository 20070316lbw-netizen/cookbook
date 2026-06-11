# 重构/移动文件后怎么提交:git 的 rename 检测

## 1. 核心认知:git 没有"重命名"概念,全靠猜

git 只存内容快照。所谓 `renamed:`,是 git 对比时发现
"删掉的 A 和新增的 B 内容相似度超过阈值(默认 50%)",在**展示层**标成 rename。
你不需要也没法"声明"重命名,只需要让 git 同时看到删除和新增。

## 2. 标准流程

```powershell
git add -A          # 暂存全部变化:修改 + 删除 + 新增
git status          # 此时大部分移动会自动显示为 renamed: A -> B
git diff --staged   # commit 前逐块过一遍即将提交的内容
git commit -m "refactor: ..."
```

坑点:平时习惯的 `git add <文件>` **不会暂存"删除"这个动作**,
status 里就会出现 deleted 一堆、untracked 一堆的分裂状态。`-A` 一网打尽。

## 3. 边搬边大改的文件,显示 delete + add 是正常的

rename 检测看的是内容相似度。移动同时大幅重写的文件,相似度低于阈值就
老老实实显示为 delete + create——**这不是错误,不用强行修**。
commit 输出里的百分比就是相似度:

```
rename {data => pipeline/source}/fetch_universe.py (98%)   # 几乎纯移动
rename {data => scripts}/build_db.py (69%)                 # 搬 + 改
delete mode 100644 data/fetch_edgar.py                     # 重写太多,不算 rename
create mode 100644 pipeline/source/edgar.py
```

## 4. add -A 之后必查两眼

`-A` 是大网,commit 前人工确认 `git status` 没把这些扫进来:
- 数据文件(`*.duckdb`、CSV 大文件)
- `__pycache__/`、`.venv/`

按理 `.gitignore` 该挡住,但值得每次确认。

## 5. commit message(Conventional Commits)

结构性改动用 `refactor:`,写"是什么/为什么"层面
(引入了什么抽象、为什么重组),不写"移动了哪些文件"的流水账——diff 自己会说。

```
refactor: 重组 data 层为 pipeline 包,引入 DataSource 抽象基类
```

新分支第一次推送:`git push -u origin <分支名>`,`-u` 绑定远端,
之后裸 `git push` 即可。
