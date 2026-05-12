# 出处和参考

## 论文

- **DDG-DA: Data Distribution Generation for Predictable Concept Drift
  Adaptation** (AAAI 2022)
  Wendi Li, Xiao Yang, Weiqing Liu, Yingce Xia, Jiang Bian
- arXiv: https://arxiv.org/abs/2201.04038
  - 关键创新: 用元学习器对**未来数据分布**做预测, 然后用预测的分布反向给
    历史样本分配权重 (re-sampling 视角) 。
  - 我代码里的"网格搜 half_life"对应论文的"learn the resampling policy",
    只是把 PyTorch 网络简化成了单参数搜索。
- 论文实验在 qlib + Alpha158 + 中国股票上, 跑的是 Linear / LightGBM /
  神经网络三种 base model, 都有提升。

## 官方实现 (qlib)

主要简化对象:

- `qlib/contrib/rolling/ddgda.py` —— 主驱动, 编排 4 步: 数据预处理 →
  proxy model 训练 → meta model 训练 → 用 meta model 给每个 rolling task
  注入 reweighter。 我的 `code.py` 把这 4 步简化成了 `learn_half_life` +
  `rolling_walk_forward` 两个函数。
  https://github.com/microsoft/qlib/blob/main/qlib/contrib/rolling/ddgda.py

- `qlib/contrib/meta/data_selection/model.py`
  `class MetaModelDS(MetaTaskModel)` —— 真正的元学习器。 我代码没抄, 因为
  它依赖 PyTorch 和 qlib 的 MetaTask 协议。 它学的是
  `time_weight = self.tn(meta_input["time_perf"])` , 也就是 "看到一段
  时间的 IC 表现轨迹, 输出对应的样本权重" 。
  https://github.com/microsoft/qlib/blob/main/qlib/contrib/meta/data_selection/model.py

- `qlib/contrib/meta/data_selection/dataset.py`
  `class InternalData` / `MetaDatasetDS` —— 构造元数据 (一组 rolling 历史
  fold 的 IC 表现) , 给 MetaModelDS 作输入。 我的"内部 walk-forward"等价
  做这件事, 只是不保留为 MetaDataset 对象。
  https://github.com/microsoft/qlib/blob/main/qlib/contrib/meta/data_selection/dataset.py

- `qlib/data/dataset/weight.py`
  `class Reweighter` —— LightGBM 模型 fit 时会调 `reweighter.reweight(data)`
  把权重塞进 `lgb.Dataset(weight=...)`。 我代码里直接用 `weights=` 参数,
  没走这个抽象。
  https://github.com/microsoft/qlib/blob/main/qlib/data/dataset/weight.py

跑通用的 example + 配置:

- `examples/benchmarks_dynamic/DDG-DA/`
  https://github.com/microsoft/qlib/tree/main/examples/benchmarks_dynamic/DDG-DA
  - `workflow.py` —— 入口, 4 步串成 fire CLI
  - 配套的 `workflow_config_linear_Alpha158.yaml` /
    `workflow_config_lightgbm_Alpha158.yaml` —— 实盘 horizon=20, segments=0.62
    这些参数的来源, 我代码里 `train_window_days/test_window_days` 的量级
    跟这里对齐。

- `qlib/contrib/rolling/base.py` `class Rolling` —— walk-forward 的基类,
  我的 `rolling_walk_forward` 简化自这个。
  https://github.com/microsoft/qlib/blob/main/qlib/contrib/rolling/base.py

## 同类工作 (背景)

- DoubleAdapt (KDD 2023): 在 DDG-DA 之后, 进一步给每段 fold 也学一个适配头。
  - arXiv: https://arxiv.org/abs/2306.09862
  - 代码: https://github.com/SJTU-DMTai/DoubleAdapt
- (我自己偷偷翻 SJTU-DMTai 的 Quant-Reading-List 时, 还有别的相关 paper,
  那个不在这一篇范围里。)

## LightGBM API

- `lgb.Dataset(weight=...)`:
  https://lightgbm.readthedocs.io/en/latest/Python-API.html#lightgbm.Dataset
  这就是 DDG-DA 学出来的权重怎么"喂"给 LightGBM 的方式。
- 关于 `weight` 是否做归一化 LightGBM 官方 FAQ:
  https://github.com/microsoft/LightGBM/issues/1351#issuecomment-377057559
  ("weights are not normalized; they enter the gradient linearly")

## 同 cookbook 内的相关条目

- `lightgbm/quant_pipeline_basics/` —— 单次训练的 baseline, 这一篇把它
  包到 rolling-window 里。
- `lightgbm/double_ensemble/` —— 治"段内样本质量", 跟这一篇治"段间分布
  漂移"互补。
- `evaluation/alphalens_basics/` —— 是不是要上这一篇的诊断信号 ("IC 时序
  近端差远端好") 在那一篇里测。
- `evaluation/risk_metrics/` —— rolling 出来的 prediction 接 long-short
  策略后, 看夏普 / 回撤就是去那一篇。
- `backtest/event_driven_loop/` —— walk-forward 给出的 prediction 接到
  事件驱动回测的下一站。
