# 如何第一次commit

```bash
# 看看 git 知道了哪些文件(应该是 4 个新文件)
git status

# 把所有文件加入暂存区
git add .

# 再看一眼(应该全变成绿色的 new file)
git status

# 第一次提交
git commit -m "init: 仓库初始化,加入模板和 README"

# 设置默认分支名为 main
git branch -M main

# 关联到 GitHub 上你刚建的仓库(用你自己的 URL!)
git remote add origin https://github.com/你的用户名/cookbook.git

# 推上去
git push -u origin main
```