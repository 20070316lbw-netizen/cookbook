# 连接 GitHub 账号 + 第一次 commit

## 1. 配置 git 身份（用 GitHub 隐私邮箱）

GitHub 给每个用户分配一个「中转邮箱」，格式：`12345678+你的用户名@users.noreply.github.com`，
公开了也没事。怎么找：登录 GitHub → 右上角头像 → Settings → Emails → 看
"Keep my email addresses private" 那一段，下面会显示你的 noreply 邮箱。

```powershell
git config --global user.name "你的GitHub用户名"
git config --global user.email "12345678+你的用户名@users.noreply.github.com"
```

参数说明：
- `--global`：全局设置，这台电脑以后所有 git 仓库都用这个身份。建议加上，不然每个新仓库都要重配。
- `user.name`：显示名，建议跟 GitHub 用户名一致，看起来整齐。
- `user.email`：就是上面选的那个 noreply 邮箱。

验证：

```powershell
git config --global --list
```

---

## 2. 第一次 commit 并推上 GitHub

```bash
# 看看 git 知道了哪些文件
git status

# 把所有文件加入暂存区
git add .

# 再看一眼（应该全变成绿色的 new file）
git status

# 第一次提交
git commit -m "init: 仓库初始化，加入模板和 README"

# 设置默认分支名为 main
git branch -M main

# 关联到 GitHub 上你刚建的仓库（用你自己的 URL！）
git remote add origin https://github.com/你的用户名/cookbook.git

# 推上去
git push -u origin main
```
