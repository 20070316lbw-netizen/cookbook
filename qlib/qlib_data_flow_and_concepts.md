# 微软 Qlib: 核心架构、数据流向与关键概念讲解

微软开源的 Qlib 是一个基于 AI 导向的量化投资平台。它的核心设计理念是将量化投资的各个环节高度模块化，从而让研究人员可以灵活地定制、替换其中的组件。

本文将为您梳理 Qlib 中数据从开始到结束的完整流向，并详细讲解其中的关键概念（Component）。

---

## 1. 整体架构与工作流 (Workflow)

在 Qlib 中，一个完整的量化投研工作流通常包含以下几个阶段：

1. **数据准备 (Data Initialization)**: 从本地或远程加载原始的行情和基础数据。
2. **数据预处理与构建 (Dataset & Data Handler)**: 筛选股票池、计算因子（Features）和标签（Labels），处理缺失值和去极值等。
3. **模型训练与预测 (Forecast Model)**: 训练机器学习或深度学习模型，并在测试集上输出预测分数 (Prediction Score)。
4. **策略与投资组合生成 (Strategy & Portfolio)**: 基于预测分数生成目标仓位或交易订单。
5. **回测与评估 (Backtest & Record)**: 在模拟撮合环境中执行订单，记录交易日志并计算收益、风险等指标。

在代码实现中，Qlib 通过 `qrun` 命令和一个 YAML 配置文件来串联这整个 Workflow。配置文件的层级结构非常直观地反映了整个数据流：
*   **Data_handler / Dataset** -> **Model** -> **Record / Strategy / Backtest**

---

## 2. 数据流向拆解与关键概念

### 阶段一：数据加载与预处理 (Data Handler & Processor)

一切量化研究的基础都是数据。Qlib 将这一层抽象为了 **Data Handler** 和 **Dataset**。

*   **数据流向**: 原始数据 (如 `.bin` 文件或 CSV) -> 解析因子公式 -> 过滤股票池和时间段 -> 执行预处理操作 -> 产出标准化后的特征矩阵和标签矩阵。
*   **Data Handler**: 负责定义如何从原始数据中提取特征 (Features) 和标签 (Labels)。在 Qlib 中，通常使用如 `Alpha158` 或 `Alpha360` 这样的内置 Handler。Handler 会接收一个股票池配置 (如 `csi300`) 和起止时间。
*   **Processor**: 附着在 Data Handler 上的组件，负责对数据进行流水线式的清洗。例如：
    *   `DropnaProcessor`: 删除空值。
    *   `CSZScoreNorm`: 横截面 Z-score 标准化。
    *   `MinMaxNorm`: 归一化。
*   **Dataset**: 对 Data Handler 的封装，它的作用是**切分数据集**。例如，将 Handler 处理好的全量数据，切割为 `train` (训练集)、`valid` (验证集) 和 `test` (测试集) 的片段，提供给模型直接使用。为了适应不同的模型（如 LGBM 和 MLP 对数据的要求不同），Dataset 会将数据打包成特定模型易于消化的格式。

### 阶段二：模型训练与预测 (Forecast Model)

获取了标准化的 Dataset 后，数据流入了模型层。

*   **数据流向**: Dataset `train` 和 `valid` 切片 -> Model `fit()` 进行训练 -> Model `predict()` 对 `test` 切片进行推断 -> 输出 Pandas DataFrame 格式的预测分数 (Prediction Score)。
*   **Forecast Model**: 这是一个可学习的模型模块。你可以使用 Qlib 提供的 baseline 模型，比如 `LGBModel` (基于 LightGBM)、`MLP`、`LSTM` 等。
*   **Prediction Score (预测得分)**: 模型的输出是一个多重索引 DataFrame `(datetime, instrument)`。得分越高，代表模型认为该股票在未来的收益表现越好。*注意：Qlib 默认不对分数进行显式的业务反归一化，得分仅代表一个排序或强弱的相对指标。*

### 阶段三：策略信号与订单生成 (Strategy)

预测得分本身只是信号，需要通过**策略 (Strategy)** 将其转化为交易意图。

*   **数据流向**: 预测分数 (Prediction Score) -> 策略逻辑 (如 TopK 选股) -> 生成目标仓位 (Target Positions) 或 目标订单 (Target Orders)。
*   **Strategy**: Qlib 提供了多种基础策略。最常见的是 `TopkDropoutStrategy`：
    *   **Topk**: 每天根据预测得分，挑选得分最高的前 K 只股票作为候选。
    *   **Dropout**: 为了降低换手率，如果当前持仓的股票得分跌出了前 K，但没有跌出 K+N_drop 范围，可以选择暂不卖出。
*   策略的输出直接指导下一阶段的模拟交易。

### 阶段四：回测与评估 (Backtest & Record)

*   **数据流向**: 目标仓位/订单 -> 交易模拟器 (SimulatorExecutor) 结合每日实际行情计算成交 -> 生成账户收益流 -> Risk Analysis 生成绩效报告 (年化、夏普、最大回撤等)。
*   **Executor (执行器)**: 负责模拟真实市场的撮合。你需要配置滑点 (limit_threshold)、买入/卖出成本 (open_cost, close_cost) 和最小交易费用 (min_cost)。
*   **Record**: Qlib 的实验管理组件（底层可选配合 MLflow），负责记录实验中的关键过程：
    *   `SignalRecord`: 记录模型的预测得分，并计算信号层面的评估指标（如 IC, Rank IC）。
    *   `PortAnaRecord`: 记录回测过程，并产出最终的投资组合风险/收益指标报告 (Excess Return 等)。

---

## 3. 核心机制总结

纵观 Qlib，我们可以发现其设计非常优雅，体现了以下核心机制：

1. **分离关注点 (Separation of Concerns)**: Alpha 研究员只需关注 `Dataset` 和 `Model` 层面的 IC 表现；而 PM 或交易员只需关注 `Strategy` 和 `Backtest` 层的组合优化和执行细节。
2. **基于配置 (Configuration-driven)**: 通过 YAML 格式的参数化配置 `init_instance_by_config`，可以不用改动一行 Python 代码，仅仅修改配置文件就能完成不同因子、不同模型、不同起止时间的对比实验。
3. **缓存机制 (Cache Mechanism)**: Qlib 的数据和因子计算具有极强的 `MemCache` 和 `DiskCache` 机制。复杂的公式 (Expression) 计算结果会被缓存，极大加速了日常的回测速度。

综上所述，Qlib 的数据流是一条**单向但可追溯**的高速公路，从底层的二进制日线行情起步，途经因子挖掘、机器学习模型的提炼，最后在回测引擎中完成策略的模拟执行，为量化从业者提供了一套端到端的强大工具链。