# 提交代码到仓库的标准流程(小抄)

## 0. 一条铁律先记住

**git 只对「变化(diff)」工作。** `add` 加的是 diff,`commit` 提交的是 diff。
没有改动 → `add` 进去是空的 → `commit` 报 `nothing to commit`。
所以正常节奏永远是:**先有真实改动,再走流程**。不要为了练流程去制造假改动。

---

## 关键判断:这个仓库要不要走 PR?

| 仓库类型 | 流程 | 例子 |
|---------|------|------|
| **协作项目**(多人、main 要保护) | 分支 → commit → push → PR → review → merge | 公司项目、learn_quant(练手用) |
| **个人仓库**(自己的笔记/配置) | 直接在 main 上 commit → push | cookbook、dotfiles |

**别把重型 PR 流程无脑套到所有仓库**。选流程看场景。

---

## 流程 A:个人仓库(直接推 main)—— 最常用

```bash
cd 项目目录

git status                       # ① 先看有哪些改动(养成习惯,先看再动)

git add 路径/到/文件夹            # ② 分主题 add,别无脑 git add .
git commit -m "docs: xxx"        #    一个逻辑改动一条 commit

git add 另一个主题/
git commit -m "feat: yyy"

git push                         # ③ 推上去
# 第一次推某分支报没 upstream → git push -u origin main
```

---

## 流程 B:协作项目(分支 + PR)—— 工作里的标准

**核心顺序:分支在【动手写代码之前】开,不是之后。**(这条最容易搞反)

```bash
# ① 先开分支(此刻还没写新代码)
git checkout -b feat/功能名          # -b = 建并切过去
git branch                           # 确认当前在新分支上

# ② 然后才写代码 / 改文件
#    ...写完 get_book_equity_asof 之类...

# ③ 这时才有真 diff,分批提交
git add data/xxx.py
git commit -m "feat: add point-in-time alignment"

# ④ 推分支到远程(第一次带 -u 建立追踪)
git push -u origin feat/功能名

# ⑤ 回 GitHub 网页 → 点黄条 "Compare & pull request"
#    填标题+描述 → base: main ← compare: feat/功能名 → Create PR
#    单人开发也要【自己把 diff 从头 review 一遍】→ Merge pull request → 删远程分支

# ⑥ 本地收尾
git checkout main
git pull                             # 把合并结果拉回本地 main
git branch -d feat/功能名            # 删本地分支(特性分支合完即弃)
```

---

## Commit message 规范(Conventional Commits)

格式:`类型: 英文小写动词开头的描述`(动词原形,不加句号)

| 类型 | 用于 | 例 |
|------|------|----|
| `feat:` | 新功能 | `feat: add EDGAR fundamental fetcher` |
| `fix:` | 修 bug | `fix: correct CIK zero-padding` |
| `docs:` | 文档 | `docs: add FF3 replication roadmap` |
| `refactor:` | 重构(不改行为) | `refactor: extract fetch helper` |
| `test:` | 加测试 | `test: add point-in-time unit tests` |
| `chore:` | 杂活(配置/依赖) | `chore: bump duckdb to 1.5` |

**粒度:一个逻辑改动 = 一条 commit。** 别把「加功能 + 改 README + 修 typo」混进一条。
干净的 history 是面试时直接展示「会不会协作」的证据。

---

## 常见卡点速查

- **`nothing to commit`** → 没有改动 / 忘了先 `git add`。先 `git status` 看状态。
- **新建的文件 add 不进?** → 新文件是 untracked,第一次 `git add 路径` 纳入追踪即可。
- **push 报没有 upstream** → `git push -u origin 分支名`(第一次推该分支)。
- **想反悔还没 commit 的改动** → `git restore 文件`(丢弃工作区改动,慎用)。

---

## 口诀

> 先 status 再动手;改动分主题、一改一 commit;
> 个人库直接推 main,协作项目【先开分支再写码】走 PR;
> message 用 `类型: 描述`,history 干净就是简历。
