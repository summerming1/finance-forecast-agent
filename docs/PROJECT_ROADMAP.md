# Finance Forecast Agent 项目迭代路线图

## 定位

本项目是从原 `p0-finance-research-core` 分支迁出的独立金融研究项目。近期目标不是无人值守交易，而是金融论文驱动、真实数据驱动、可审计的自动化研究系统。

## 模式边界

- `strict_reproduction`：论文原始数据或许可镜像、协议、模型、特征、成本、切分全部可比。
- `exploratory_real_data_reproduction`：使用本地真实数据验证论文观点，不声明 strict。
- `paper_inspired_local_study`：论文仅提供研究思想。
- `simulation_only`：仅流程联调。

## P0：可信研究内核

能力边界：

- PaperSpecCard、DatasetCard、ComparabilityReport。
- ReplayLLM 固定 fixture。
- ResearchContract 和 ExecutionManifest。
- purged walk-forward / rolling-origin。
- Cost-aware metrics 与 cost scenarios。
- PaperDatasetRegistry 可用。
- MLflow / DVC adapter：环境安装时使用真实后端，未安装时降级为可测试本地后端。
- LSTM、Transformer、GA-LSTM 真实 adapter。
- Streamlit UI 展示 PaperSpec、Dataset、Comparability、候选 lane、Audit。

验收：真实数据 golden workflow 通过；strict 不被误放；deep candidates 不再用 proxy。

## P1：研究记忆与数据注册增强

- ExperimentMemoryStore 参与 Scheduler prior。
- PaperDatasetRegistry 增加字段映射、许可、可得性、替代数据说明。
- strict benchmark memory isolation。
- 前端增加 Approvals、Memory、Registry 页面。

## P2：搜索效率增强

- Hyperband / Successive Halving / Bayesian optimization。
- 多成本情景下的 Pareto candidate selection。
- Drift monitor 与自动再研究任务。

## P3：部署治理

- shadow / paper / live 分层。
- BrokerFacade 默认关闭 live。
- 审批 Gate、kill switch、审计日志、策略卡、模型卡、风险卡。

## 修改原则

新想法必须先判断是否破坏：复现分层、时间因果、成本真实、LLM 权力边界、人工审批。通过评估后再修改本文件。
