# Cookbook

我的个人代码素材库,收集从各处学到的代码片段,改写成通用形式后归档。

## 结构

每个主题一个文件夹,每个具体技术一个子文件夹,包含:
- `code.py` — 通用化后的代码
- `notes.md` — 输入输出、关键细节、坑
- `sources.md` — 出处和参考链接

不是每个子文件夹都三件齐全:偏概念的笔记可能只有 `notes.md`,纯代码片段可能没有
`sources.md`。新建条目时从 [`_templates/`](_templates/) 复制对应模板起步。

例外:`pitfalls/` 收录自己实际踩过的坑,每个子文件夹是两件套:
- `problem.md` — 坑长什么样、为什么会炸、怎么解、教训
- `fix.py` — 错误写法 vs 正确写法,可直接运行对照

## 索引

- **duckdb/**
  - [`wide_to_long/`](duckdb/wide_to_long/) — 宽表 ↔ 长表:入库前 pandas stack/melt 转长表 (首选),库内遗留宽表才用 UNPIVOT;qlib 风格 MultiIndex
  - [`count_distinct_vs_groupby/`](duckdb/count_distinct_vs_groupby/) — `COUNT(DISTINCT)` 只要数量 vs `GROUP BY` 要列表
- **pandas/**
  - [`rolling_windows/`](pandas/rolling_windows/) — 滚动窗口:单序列基本款 + panel 上按 instrument 分组滚动 (transform)
  - [`dataframe_constructor/`](pandas/dataframe_constructor/) — `pd.DataFrame()` 能吃哪些形态:list of dict / dict of list / 嵌套 list
  - [`to_csv_index_false/`](pandas/to_csv_index_false/) — 写 CSV 几乎总要 `index=False`,否则读回来多一列 `Unnamed: 0`
- **python/**
  - [`class_return_types/`](python/class_return_types/) — 同一列表里循环处理的方法,返回值类型必须一致
  - [`path_and_syspath/`](python/path_and_syspath/) — `__file__` / `.parent` 路径拆解与 `sys.path.insert`
- **lightgbm/**
  - [`train_function_template/`](lightgbm/train_function_template/) — 训练/预测函数模板,参数字典抽离
  - [`quant_pipeline_basics/`](lightgbm/quant_pipeline_basics/) — 量化最小可跑流水线 (qlib 简化版):打标签 / 写特征 / 训练 + IC 评估
  - [`double_ensemble/`](lightgbm/double_ensemble/) — DoubleEnsemble (ICDM 2020):样本重加权 (SR) + 特征选择 (FS) 治样本噪声
- **backtest/**
  - [`event_driven_loop/`](backtest/event_driven_loop/) — 事件驱动回测心跳 (zipline-reloaded 简化版):mark-to-market + rebalance
- **evaluation/**
  - [`risk_metrics/`](evaluation/risk_metrics/) — 业绩 / 风险指标 (empyrical-reloaded 简化版):年化收益 / 波动 / 夏普 / 最大回撤 / Calmar / Sortino
  - [`alphalens_basics/`](evaluation/alphalens_basics/) — 因子诊断核心 (Alphalens 简化版):IC / IR / 分位单调性 / 换手
  - [`concept_drift_ddgda/`](evaluation/concept_drift_ddgda/) — 概念漂移下的样本时间加权 (DDG-DA 简化版):walk-forward + 指数衰减权重
- **qlib/** — 微软 Qlib 源码与机制阅读笔记
  - [`data_flow_concepts/`](qlib/data_flow_concepts/) — 整体架构与数据流向:Data Handler → Model → Strategy → Backtest
  - [`factor_engine/`](qlib/factor_engine/) — 因子引擎概览:表达式引擎 (Formulaic Alpha)、动态过滤、多级缓存
  - [`expression_internals/`](qlib/expression_internals/) — 表达式内核:Expression 基类 / Feature 叶子 / ops 算子四大家族
  - [`mini_factor_engine/`](qlib/mini_factor_engine/) — 手写一个最小可跑的 Qlib 风格表达式引擎 (含 Demo 到工业级的差距)
- **logging/**
  - [`loguru_basics/`](logging/loguru_basics/) — loguru 入门
- **git/**
  - [`connect_my_git/`](git/connect_my_git/) — 账号 / 命令配置
  - [`commit_and_push_workflow/`](git/commit_and_push_workflow/) — 提交代码标准流程:个人库直推 main vs 协作项目分支 + PR
  - [`manage_code/`](git/manage_code/) — `.gitignore` 等
- **pitfalls/** — 自己踩过的坑(`problem.md` + `fix.py`)
  - [`groupby_index_vs_column/`](pitfalls/groupby_index_vs_column/) — `groupby(level=...)` vs `groupby('列名')`,接口不一致会炸
  - [`rolling_index_misalign/`](pitfalls/rolling_index_misalign/) — `groupby().rolling()` 后 index 变 MultiIndex,赋值回 df 错位
  - [`feature_label_naming/`](pitfalls/feature_label_naming/) — 特征/标签命名撞概念(`return_5d`),埋数据泄漏隐患
  - [`script_import_modulenotfound/`](pitfalls/script_import_modulenotfound/) — 直接跑子目录脚本报 `ModuleNotFoundError`
  - [`yaml_dump_overwrite/`](pitfalls/yaml_dump_overwrite/) — `yaml.dump` 整体覆盖,冲掉手写的配置块
  - [`pandas_assign_values_misalign/`](pitfalls/pandas_assign_values_misalign/) — 给 DataFrame 赋值时滥用 `.values` 导致索引静默错位
  - [`leakage_test_start_embargo/`](pitfalls/leakage_test_start_embargo/) — 测试集起始日硬编码，未考虑隔离带导致未来数据泄露
  - [`add_features_hurts_ic/`](pitfalls/add_features_hurts_ic/) — 加因子反而让 IC 下降:共线特征在弱信号下稀释而非增强(研究认知坑,非代码 bug)
