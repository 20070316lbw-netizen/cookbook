用 GitHub 给你的「隐私邮箱」

格式长这样:12345678+你的用户名@users.noreply.github.com
这是 GitHub 自动给每个用户分配的「中转邮箱」,公开了也没事
怎么找:登录 GitHub → 右上角头像 → Settings → Emails → 看 "Keep my email addresses private" 那一段,下面会显示你的 noreply 邮箱

```powershell
git config --global user.name "你的GitHub用户名"
git config --global user.email "12345678+你的用户名@users.noreply.github.com"
```

参数说明:
--global:全局设置,在你这台电脑上以后所有 git 仓库都用这个身份。建议加上,不然每个新仓库都要重新配一次
user.name:显示名,随便起,但建议跟 GitHub 用户名一致,看起来整齐
user.email:就是上面选的那个

如何验证
```powershell
git config --global --list
```

