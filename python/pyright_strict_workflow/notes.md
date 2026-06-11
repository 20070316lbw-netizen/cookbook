# pyright strict 模式生存指南

## 1. 核心心法:看到红,先读规则名

每条报错末尾括号里都有规则名。悬停看一眼,九成的"pyright 烦"当场消失:

| 规则名 | 意思 | 怎么办 |
|---|---|---|
| `reportUnusedImport` | 导入了没用 | 草稿期正常,写完还红的删掉 |
| `reportUnusedVariable` | 变量存了没读 | 接着写下去,或删掉 |
| `reportReturnType` | 某条路径的返回值和签名不符 | 见下面第 3 条 |
| `reportMissingTypeArgument` | 泛型没写参数 | `dict` → `dict[str, str]`,`list` → `list[str]` |
| `reportUnknownMemberType` | 第三方库类型信息缺失 | 不是你的错,可按规则名关闭 |
| `reportMissingImports` | 找不到模块 | 配置项目根目录,不是代码问题 |

## 2. 配置哲学:严格程度是项目的事,不是编辑器的事

写进**每个项目自己的 `pyproject.toml`**,不要改 VSCode 全局设置:

```toml
[tool.pyright]
typeCheckingMode = "strict"
# 依赖栈类型信息差(yfinance/pandas/duckdb)时,按名关掉最吵的:
# reportUnknownMemberType = "none"
```

效果:自己的项目是严师,clone 来的第三方老库(qlib 等)没配置文件,
回落到默认 basic,不会满屏红。

## 3. strict 报错的统一视角:签名是承诺,逐条路径验收

反复踩的同一类问题,本质都是"签名的承诺"和"某条代码路径的实际行为"对不上:

- 函数声明 `-> pd.DataFrame`,except 分支 log 完就结束 → 那条路径返回 None,违约
- if 返回 DataFrame、else 没 return → else 路径违约
- 子类重写方法不写返回类型 → 签名不会从基类自动继承,要自己写全

修法永远是二选一:让那条路径**也返回承诺的类型**,或让它 **raise**
(raise 的路径不需要返回值)。绝不是塞一个空 DataFrame 蒙混过关
(见 pitfalls/silent_empty_dataframe)。

特例:函数体**仅有** `...`(或 docstring + `...`)时按 stub 豁免检查——
这就是抽象方法只写 `...` 不报错的原因;一旦有了真代码,豁免失效。

## 4. 为什么不直接关掉

- Protocol 的全部价值依赖静态检查器,关了等于白写
- pyright 抓拼错方法名、传错参数、漏 return 是实打实的免费 bug 检测
- repo 里一份严格但合理的 `[tool.pyright]` 配置,本身就是给招聘方看的信号
