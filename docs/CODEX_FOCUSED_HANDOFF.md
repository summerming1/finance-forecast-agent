# Codex handoff：B0–B5 文献驱动研究交付

以 CURRENT_IMPLEMENTATION.md 为唯一状态，PROJECT_ROADMAP.md / ADR_MISSION_PRODUCT_004.md 为批准范围。正式分支 feat/mission-research-v2；执行前检查工作区、HEAD 与远端，不覆盖用户工作。

读取 AGENTS → Roadmap → Current → ADRs → Architecture → Acceptance → V2 log / validation/v22r_acceptance.json。B0→B1→B2→B3→B4→B5：每批新增负例和受影响回归、Ruff/compile 通过后提交/推送，再开始下一批。同源码 CI 结果和未知项分别记录。

B1 复用客户端/RuntimeDB，B2 复用 Mission/Controller，B3 复用 MethodCard/审核/EvidenceIndex，B4 只读投影与显式新 Campaign，B5 分离工程/Live/真人/增量。禁止第二套运行或论文事实源。

用户已批准文献修订方案：文献不负责动态默认模型；必须能定位原文、版本审核、使用角色、迁移差异、实际实验和后续反馈。1–3条本地资料足够，理论/限制用途不降低strict复现门禁。无资料允许基础研究，不可伪称使用；原始全文许可不明确时不导出。

旧真实Live/恢复/浏览器/负确认不重复标未实现。历史R5失败、47行负确认不改，缺真实凭证或用户写BLOCKED。旧合同保持只读/显式兼容；不新建空库重置暴露或信任。

新功能测试必须记录源码树、命令、exit、输入身份、JUnit/日志；模拟fixture仅工程证据。B5真实策略与文献贡献小对照分开，不自动放大成巨型矩阵。详见 FOCUSED_ACCEPTANCE_TEST_PLAN.md。

### B1增量
客户端记录独立连接/read/deadline与重试策略。`waiting_provider` 使用已有队列，恢复保留HTTP与fit账本；响应已落盘则复用，未落盘可能服务端已计算，费用仍未知。CLI增加 `--max-http-requests`、`--max-provider-seconds`。同合同只读旧证据，不能换policy后冒充同一次运行。B2仍按原双入口/成果身份任务继续。
