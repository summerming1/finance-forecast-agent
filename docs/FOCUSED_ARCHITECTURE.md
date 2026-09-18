# 聚焦版结构、接口与实施方案

> 状态：APPROVED / ADR-FOCUS-001 已于 2026-09-18 经用户批准。本文作为 focused 路线的设计与开发约束；具体已实现范围以 CURRENT_IMPLEMENTATION.md 与版本说明为准。

## 1. 修改后的产品

它是“限定领域的预测研究工作台”，而不是一段自动训练脚本，也不是无限代码 Agent。用户选择真实数据任务与文献，系统可在批准范围内完成假设、实施、评价、批判和下一轮。结论可以是有效、无效或证据不足。

推荐保留 Python + Streamlit；复用既有 MethodCard、ReproductionPlan、BenchmarkTask、PredictionArtifact、ExperimentMemory、任务队列与 MLflow/DVC。新名字只用于当前缺失的责任，不再创建第二套同义 Paper/Dataset/Run 实体。

## 2. 逻辑结构（不是必须一项一个进程）

```text
Streamlit / CLI
      |
      v
ResearchController (one authority, deterministic state machine)
      |
      +-- MethodCardAgent (LLM, ingestion only)
      +-- ResearchAgent (LLM, hypotheses based on evidence + development results)
      +-- CriticAgent (LLM, explanation + next direction; no numerical authority)
      |
      v
Stable Tool Facade / Policy Checks
      |
      +-- Dataset & Feature Services
      +-- Plan Compiler & Model Registry
      +-- Existing LocalTaskQueue -> local training worker
      +-- Evaluation Service -> separate confirmation worker
      |
      v
PredictionArtifact + EvaluationArtifact + actual execution manifest
      |
      v
existing Memory + MLflow/DVC lineage + campaign/event store
      |
      +--------------------> controller -> next round
```

实现工具与 Controller 可以同属 Python 包。不要引入 LangGraph、Prefect、Dagster、RD-Agent、DeepSeek 五套编排；先用现有队列加一个受测试的状态机。

## 3. 职责和权力

| 角色 | 使用 LLM？ | 允许 | 不允许 |
|---|---|---|---|
| MethodCardAgent | 是；或同请求 Replay | 提取论文事实、claim、证据与 unknown | 把本地实验写回成论文事实 |
| ResearchAgent | 是；Record/Replay 同接口 | 根据开发结果提出可证伪假设、受限配置变更 | 读取 final 标签、换主指标、审批自己 |
| CriticAgent | 是；Record/Replay 同接口 | 分析已有指标、失败、机制和反证 | 自己编指标或裁决 strict/晋升 |
| PlanCompiler | 否 | 校验参数、映射真实实现、计算配置哈希 | 将未知模型转换成 Ridge 继续跑 |
| Evaluator | 否 | 分割、指标、成本、配对比较、权限核验 | 根据 LLM 建议删差结果或改分数 |
| Controller | 否 | 状态、预算、队列、重试、恢复、晋升门禁 | 无限循环直至出现赢家 |
| 人工审核 | 人类 | 批准任务边界、来源/许可、范围外新能力、最终晋升 | 将不满足数据条件的实验点成严格复现 |

三个 LLM 角色可使用同一个模型服务，但提示、可见上下文与可用工具分开。首次不需要三个常驻服务。

CodingAgent 在 F1 是可选外部开发入口：缺失能力形成任务，人或 Codex 在隔离分支实现和验收后注册。它不是每轮必须经过的层。以后嵌入 DeepSeek/RD-Agent coder 时也只能写允许的 workspace，不能写评估器或 final 数据。

## 4. 主任务合同：消除方向分类与收益回归混用

新任务建议 ID：`spy_daily_next_return_research_v2`，这是拟议 ID，不是已有功能。

默认 `task_type=return_regression`；标签为 `C_adj[t+1]/C_adj[t]-1`，其中 t、t+1 是交易日索引。主指标 MAE，方向一致性和 RMSE/R2 只作辅助。所有标签公式、缺失行与复权来源须冻结；`adjusted close` 的未来公司行为修订风险须在 DatasetContract 中公开，不宣称机构级 point-in-time 数据。

预测决策时刻设为 t 日收盘数据可获取之后；此合同是 forecast-only。成交收益需另外定义已批准的 next-open 等 ExecutionSpec；不得用 t 收盘信息同时假设以 t 收盘成交。加入交易任务会产生新 task/protocol 版本。

现有 SPY 数据已用于先前 benchmark，不能简单重新分出尾部便叫未看过的 final。F0 可使用整个已知快照进行历史开发与接线；未暴露历史区间的资格需要记录，无法证明时采用后续前瞻数据确认。

候选不同观察窗口的预热区间按本 campaign 最大 lookback 统一剔除。不能某个候选因为缺行而拥有更容易的评估日期。跨候选的 y_true、目标时间、entity、horizon、fold 必须相同。

## 5. 核心数据结构：在已有 schema 上最小扩展

### CampaignSpec（新增，小范围编排实体）

包括 campaign_id、task_id/version、dataset_content_hash、method_card_versions、protocol_hash、feature_registry_version、allowed_changes、budget、review_policy、holdout_policy、evaluation_schema_version、creation_git_sha。

`allowed_changes` 与预算批准绑定整份合同哈希。模型卡、协议、许可或变更范围变化后，不沿用旧审批。

### HypothesisSpec（若已有同义结构则扩展它）

包括 hypothesis_id、parent_candidate_id、statement、mechanism、source_claim_ids、development_evidence_refs、expected_effect、counter_evidence_test、proposed_changes、risk、stop_condition。

每条 proposed_change 是结构化字段路径、旧值、新值和理由；不接收任意 shell/Python 字符串。支持反向例：较复杂模型无增益时改成更强正则、更少特征，而不是只会增加复杂度。

### Candidate/Contract/Manifest（复用）

必须记录实际生效的模型超参数、seed、训练窗口、特征公式与 lookback、预处理器、输入张量语义、代码 revision 和 adapter version。配置哈希改变不算验证，必须检查模型实例参数及特征产物确实改变。

`candidate_fingerprint` 去掉随机 ID、叙述和时间戳，只基于执行实义计算；不同 ID 的相同实验不可重复计为新研究。

### EvaluationArtifact（扩展现有报告）

分开记录 `execution_status`、`implementation_conformance`、`research_verdict`、`reproduction_tier` 与 `promotion_status`。例如 execution=success 但 research=not_supported 是正常研究结束。

评估字段区分 development 与 confirmation。Critic 输入只引用由 Evaluator 落地的指标、fold/时间段诊断和数据质量摘要；它的叙述不能覆盖数值源。

### Memory（扩展，不新建第二数据库语义）

保留已实现的 mode/task 隔离，再加入数据内容、协议、评估 schema、模型实现版本、是否 final 暴露和失败类别。旧成本/错误序列等受影响记录可保留历史展示，但不得进入新 prior。

技术失败与假设无效不同：机器缺依赖不应被记成“LSTM 科学上无效”。相似任务的经历仅作弱先验，不直接平均不同资产/时期的净收益来排序。

## 6. 一次真实研究如何进行

0. 用户选择方法卡，系统显示其原始协议与本地任务差异。缺字段可以阻断 strict，但不伪造；本地任务在独立合同下可继续。
1. 用户批准冻结数据、开发 folds、候选空间和预算。BaselineSuite 在完全相同的目标行上执行。
2. ResearchAgent 读取方法卡证据、可用数据字段、已执行 baseline 的开发报告、Memory，提出不超过两条假设。
3. PlanCompiler 检查可执行性和预算；同义重复被标记 skipped_duplicate；不支持方法生成 backlog。
4. 在已批准配置范围内自动执行；越界候选等待人工审批，审批拒绝保留事件，不回退偷偷运行。
5. Evaluator 核验真实配置、计算结果和相对 baseline 差异。无输出、缺预测行、NaN、错误目标等不进入 leaderboard。
6. CriticAgent 引用实际结果给出支持/不支持/证据不足与下一方向；Controller 按规则决定是否继续。
7. 下一轮输入包含上一轮真实报告及拒绝原因。父子变更与假设来源可被 UI 查看。
8. 达预算或停止条件后冻结开发候选；有合格未暴露 final 才请求确认。没有则输出历史开发结论并等待前瞻确认。
9. 人工晋升、拒绝或保留基线。终态可为 `completed_no_improvement`；不得要求继续到必胜。

## 7. 最小工具集

下面是拟议能力接口，而非当前已有工具函数名称。优先包裹已有 service；禁止 UI 或 Agent 绕过门禁直接调用低层库。

| 能力 | 输入 | 输出 |
|---|---|---|
| inspect_research_context | task/card/allowed artifacts | 当前可见上下文和证据引用 |
| validate_experiment_plan | hypothesis + plan | approved-scope / blocked / needs_review |
| submit_experiment | 合法 contract + idempotency key | task_id、manifest |
| get_experiment_result | task_id | 原始产物引用、状态、数值报告 |
| compare_development_runs | 相同任务的 run IDs | 配对差异、基线结果和诊断 |
| record_research_feedback | validated critique | 不覆盖原数值的解释记录 |
| request_review | hash-bound request | approved / rejected / pending |
| cancel_campaign | campaign_id | 取消状态、已完成结果引用 |

最终确认不作为 ResearchAgent 可自由调用的工具；Controller 在冻结和独立批准后调用专属评估入口。

## 8. LLM Record / Replay 的可信性

同一协议的 live、record、replay 共用 schema 校验、来源检查和质量门禁。记录 request ID、prompt template version、schema version、模型 ID、sampling 参数、MethodCard/证据 hash、开发结果 hash、工具 schema version、原始响应与校验结果。

回放键基于完整标准化请求，不仅是 paper_id；移动本地目录不应改变语义键，内容变化必须改变。缺匹配即失败；不能退回 catalog 里“同 paper 的任意建议”。

记录是录制数据，不自动代表人已批准。原始响应先保存为未校验；有效响应经校验后才可供下游，拒绝与错误也有独立记录。禁止把 API key、Authorization、.env 进入可提交产物。

离线测试证明接线、语义约束和 determinism；真实 LLM 研究质量需要真实调用 campaign。两种测试结果分别报告，不用 one-shot stub 替代 Agent 决策后宣称在线验证。

## 9. 状态、恢复与预算

Campaign 最小状态：draft → awaiting_approval → running → awaiting_review / paused → completed / completed_no_improvement / cancelled / failed。候选有 proposed、blocked、queued、running、completed、failed；科学 verdict 是另一维。

统一使用现有队列，不在 UI 再写独立训练循环。单机可用 SQLite 事务记录 campaign、事件与候选映射；JSON 是导出，不做多 worker 共享可变状态的唯一依据。若已有等效事务存储则复用，不为名字重建。

训练进程不得在数据库长事务中执行。提交幂等、状态转换原子；进程退出通过 heartbeat/reconciliation 标为 interrupted，不把缺结果记为成功。F1 可按候选边界恢复，暂不承诺每个模型 mid-epoch 恢复。

所有请求和完成事件有 event_id、campaign_id、candidate_id、attempt_id、time、status、artifact hash。UI 必须显示实际开始/结束/失败；并行展示以真正重叠执行为依据。

## 10. 前端不是另一个大项目

保留现有七阶段工作台与历史报告；增加一个“研究任务”入口作为默认闭环，原生复现与跨领域能力放高级入口。不重写 React/FastAPI，不丢失旧审批与提取功能。

闭环默认展示五块：
1. 任务合同：预测什么、何时可见、哪些数据、主指标、预算与确认资格。
2. 本轮研究：假设、证据、为什么值得试、如何反证。
3. 候选执行：并发/串行真实状态、参数和特征变化、实际运行模型、停止原因。
4. 结果与反馈：同日期基线对比、每个候选 verdict、下一轮来源。
5. 研究结论：开发与确认分开、是否保留基线、审核和全部历史。

折叠层展示完整 Manifest、工具调用、Prompt/Replay 来源、stderr、追踪链接。未运行用“未运行”，不靠方法卡存在推断流程完成。

## 11. 迁移文件级建议

| 现有模块 | 修改策略 |
|---|---|
| data.py / splitters.py | 审计信息时点、标签区间与真实来源，参数通过合同传递 |
| evaluation.py / benchmark.py | 迁入 main 成本修正；加入开发/确认分层和同目标行配对输出 |
| models.py / method_adapters.py | 实际超参数贯通；时间维/变量维明确；不丢失高级分支的 3D 与目标缩放 |
| harness.py / candidate_execution.py | 新闭环复用确定性执行路径；旧脚本保持兼容但共享相同内核 |
| experiment_memory.py / memory_scheduler.py | 同任务结果前置使用，失败分类与版本隔离 |
| task_queue.py / run_timeline.py | 统一任务事实；真实事件、幂等与恢复 |
| method_cards.py / method_card_v3.py | 沿用证据和版本；不在本期重建提取器 |
| streamlit_p09.py / frontend_workbench.py | 增量接入 campaign 页；按需提取页面组件，不整站重写 |
| native_claim_* / source_data_contracts.py | 保持接口与已有回归，非当前主线不扩展 |

可新增一个 `research_loop.py` 和必要 schema/service 辅助文件；目录名只是建议，Codex 先检查现有同义实现再决定。绝不把每个表格行做成独立服务。

## 12. 外部项目的大方向启示

RD-Agent 教我们：研究方向、工程实现、实验反馈是不同责任，下一轮必须受上一轮证据影响。
DeepSeek Harness 教我们：模型不应知道每个底层实现；工具、状态与权限应稳定，执行过程本身是可观察数据。
自己的金融项目提供：什么是合法数据、可比实验、真实实施、可靠结论。

综合原则：开放“提出什么假设”，约束“如何执行和判定”；对外保留扩展接口，对内先把单一领域产品做完。[E01–E04]

来源索引见 [CURRENT_IMPLEMENTATION.audit.md](CURRENT_IMPLEMENTATION.audit.md)。