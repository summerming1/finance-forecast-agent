# ADR-MISSION-PRODUCT-004：可靠执行、双入口与文献驱动研究

- status: accepted
- approved_by: user
- approved_at: 2026-09-23
- supplements: ADR-FOCUS-001, ADR-MISSION-002, ADR-MISSION-PRODUCT-003
- authoritative_branch: feat/mission-research-v2
- implementation baseline: a3c6ec69c9bd14d18b1cdb493795669a9452c800

## 决策与边界

用户明确批准本轮文献驱动修订方案，按 B0→B5 测试后逐批提交。继续单机受控金融机器学习研究工作台；不新建 Controller、Queue、Evaluator、RuntimeDB、Memory 或方法卡事实源。不启动 V3。

默认入口是“只有研究目标”，从版本固定的内置基线开始；第二入口接受同任务数据、受支持模型配置和一个审核数值特征。两者使用同一研究引擎。扩大用户起点，不扩大任务：SPY / daily / 下一 XNYS 交易日 adjusted-close return / regression / MAE / forecast_only。

文献不是动态默认模型供应器。已审核观点、条件与限制持续参与本地假设、对照、消融、诊断、反证和下一批决策；无文献可基础研究。最多三条本地版本绑定投影，无自动每轮检索或陌生代码执行。

严格分开：作者原观点、本地迁移假设、实际实验事实。研究用途审核允许有来源的机制/限制段落，不降低 strict reproduction 的数值/协议门禁。引用是可追溯解释，不是因果证明或预测优势；独立做有/无显式文献比较。

## 执行设计

- B1：分类错误、有界重试、真实 deadline、调用账本、外部依赖暂停和同合同恢复；失败/未知费用不归零。不自动付费/换模型。
- B2：目标/已有起点双入口、表单、incumbent 与固定控制分离、固定模型仅研究特征约束、唯一候选到显式 refit/下载身份。
- B3：来源/方法卡版本→审核→EvidenceIndex→本地假设→实际配置/反馈；批内冻结、批间自适应；紧凑确定性上下文；真实策略与文献贡献分别比较。
- B4：确定性研究总结、显式续接新 Campaign、确认能力预检/朴素控制、导航和依赖收敛。
- B5：离线对抗→小预算真实调用→有效小矩阵→真人试用→同源码发布验收。缺资源保持 BLOCKED。

技术恢复继续原合同；新研究创建有谱系的 Campaign，保留暴露和费用历史。一次性金融确认不采用提供者故障自动重试。已披露47行负确认及历史 R5 FAIL 不能重跑改绿。

## 权威与迁移

CURRENT_IMPLEMENTATION.md 只写实际状态；PROJECT_ROADMAP.md 只写批准方向；验收映射在 validation/v22r_acceptance.json，历史收据不改。旧合同只读或显式兼容；不得重算旧 hash 以强行恢复。

所有输出缺凭证/真实用户/来源/平台时分别声明。模拟数据与 assistant-authored fixture 不冒充 Live、客户或金融证据。macOS/GPU 不在本轮范围。
