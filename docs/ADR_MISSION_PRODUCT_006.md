# ADR-MISSION-PRODUCT-006：确定性诊断与受控观察研究

- status: accepted
- approved_by: user
- approved_at: 2026-10-09
- authoritative_branch: feat/mission-research-v2
- implementation_base: 95760e264eddb4388a44df6d35442b6ce8d90928

## 决策

在原价格研究链增加版本化诊断、有限ObservationRule、配方依据、最终选择政策及Diag-OFF/ON投影。唯一详细合同为[V2_4_DIAGNOSTIC_RESEARCH.md](V2_4_DIAGNOSTIC_RESEARCH.md)。复用Controller、Queue、Evaluator、RuntimeDB、Memory和MethodCard；纯函数模块不成为第二个执行权威。

用户批准D24-0至D24-5工程和D24-6准备、本地分批提交。默认不推送，不运行远端CI；不调用外部Provider、不外发资料、不读取独立确认标签、不迁移生产库。后续版本只维护路线。自动诊断新增fit=0/HTTP=0；显式diagnose仍占原槽。原MAE/0.0025、两规划/四槽、DSL确认禁用保持。

收益是可反驳的研究与可查推荐；风险是错误数据来源、观察方向、信息泄漏和身份漂移。以原制品身份、训练范围、不可变规则/上下文、只读UI及原恢复门禁控制。工程验收不代表Provider理解、策略优势、真人价值或金融独立证据。
