# Codex 开发与迁移交接说明

> 状态：APPROVED / ADR-FOCUS-001 已于 2026-09-18 经用户批准。本文作为 focused 路线的设计与开发约束；具体已实现范围以 CURRENT_IMPLEMENTATION.md 与版本说明为准。

## 1. 先审阅，不自动开工

没有用户明确批准 ADR-FOCUS-001 时，只做只读审计与计划差异；禁止改正式 PROJECT_ROADMAP、创建远端工作分支、改功能代码、迁移数据或提交。

这份文档包含未来批准后的指令，不是批准本身。执行前必须重新读取当前 Git HEAD，因为本方案固定快照可能已被用户继续修改。

## 2. 每次会话强制阅读

1. 仓库已有 AGENTS.md 与目录局部说明；不能用本文件覆盖既有约束。
2. 正式 `docs/PROJECT_ROADMAP.md`。
3. `docs/CURRENT_IMPLEMENTATION.md`。
4. 最近两到三个版本 MD（按内容版本，不仅按修改时间）。
5. 已批准的方向决策、当前里程碑和 `ACCEPTANCE_TEST_PLAN.md`。

遇到冲突：展示变更目标与旧路线冲突、收益/风险/迁移成本，请用户决定；不能自认“只是细化”而改变验收范围。

## 3. 仓库和分支策略

只使用现有 `summerming1/finance-forecast-agent`。建议工作分支 `feat/p1-focused-us-equity-loop`，基于审计时最新版 `codex/arxiv-methodcards`。不新建仓库，不为每次小修复开新分支。

只读核对命令：

```powershell
git status --short
git remote -v
git fetch origin
git log -1 --oneline origin/codex/arxiv-methodcards
git log -1 --oneline origin/main
git log --left-right --cherry-pick --oneline origin/codex/arxiv-methodcards...origin/main
git diff origin/codex/arxiv-methodcards origin/main -- src/finance_forecast_agent tests
```

用户批准且工作树处理妥当后才运行：

```powershell
git switch --create feat/p1-focused-us-equity-loop origin/codex/arxiv-methodcards
```

若分支已存在，读取它并核对未合并工作；不能 reset/force-push。存在未提交修改时先停止并说明，不自动删除或 stash 用户修改。最终通过测试才 push 工作分支。main 是否合并另外审核，保护公开可运行演示与许可证边界。

## 4. F0 的任务清单

A. 产出迁移矩阵：main 的 data/models/evaluation/harness 修改与高级研究分支的 method_adapters/benchmark/native 功能逐项比对。
B. 写能暴露成本、信息泄漏、模型参数、序列语义和 final 污染的失败测试，再修代码。
C. 必须行为级移植。不得 `git checkout main -- src/...` 整体覆盖并丢失高级能力。
D. 审计当前 SPY CSV 的真实可得性、DVC remote、来源/许可与标签构造。DVC 指针不是数据已存在的证明。
E. 冻结一个新任务版本；保留旧 task ID 和旧指标，不修改历史证据以适应新结果。
F. 统一评估 schema 和 Memory 兼容门禁；标明历史报告哪些需重验。
G. 实际跑现有全量可执行回归和 T01–T14；说明受环境限制的项并定向解决，不虚报通过。
H. 写入当前 F0 版本说明和 CURRENT_IMPLEMENTATION，测试通过后提交工作分支。不得顺手实现全部 F2/F3。

## 5. F1 的任务清单

A. 在现有实体基础上实现 Campaign 与 ResearchController、Hypothesis/Feedback 结构，复用队列和执行器。
B. 用完整请求哈希接通 live/record/replay；不修改源 MethodCard 事实；新建议必须含执行可用字段。
C. 初始限定 Ridge/RF/GBDT 和已批准特征注册项，不偷偷加入 shell 任意代码路径。
D. 至少一个 real-data Replay campaign 的第二轮候选依赖第一轮报告，实际模型/特征变化由产物验证。
E. 研究预算、工程重试、去重、审批、失败分类、恢复、事件、UI 一起形成纵向切片。
F. 首版 UI 增量改造，不删除旧提取/审核/native 页面。AppTest + 真浏览器操作都做。
G. 完成 T15–T40 与旧回归。输出无提升和拒绝候选的正常案例，不只演示成功路径。
H. 版本 MD 和 CURRENT 记录实际已接通的功能，分别标明 live API 未测与 Replay 已测。通过后提交。

## 6. 禁止事项

- 不将“out-of-sample/backtest”直接改写成已执行 purged walk-forward 的事实。
- 不将未知方法用 Ridge/GBDT 等代理并宣称实现原方法。
- 不把特征列顺序随意作为 LSTM 时间轴。
- 不以缺 DVC/网络为由用 synthetic 数据冒充真实验收。
- 不在运行时覆盖真实录制 fixture；不得自动把录制等同于人工 approved。
- 不让任何 Agent 直接改最终指标、标签、切分、选样和 strict 审计器。
- 不用同一个已经看过的 final 不断修模型直到通过。
- 不把 execution=success 当 scientific_gain=true。
- 不因为“追求通用性”增加新市场/框架依赖或重写已有数据实体。
- 不声称一次普通 pytest 重跑了已有所有 native 论文训练。
- 不上传 .env、key、私人数据、无再分发许可 PDF 或全部本地运行目录。

## 7. 文档落地规则

用户批准后，将方向提案保存为 ADR，按决定更新正式路线；旧 broad acceptance 原样保留为延后目标，不能修改历史已批准日期或假称已通过。

每个 F 里程碑建议维护一份版本说明，如 `docs/P1_FOCUS_F0.md`、`docs/P1_FOCUS_F1.md`；同一里程碑内所有修复更新原文，不新建 validation-final-v2 一类文档。

`CURRENT_IMPLEMENTATION.md` 必须只有一个权威“当前状态”段，包含 branch/commit、完整流程、哪些是 template/Replay/live、数据范围、验证范围、未解决问题、后续目标。它不是路线许愿清单。

## 8. 可并入 AGENTS.md 的约束补充（批准后再合并）

```text
Before changing code, read PROJECT_ROADMAP.md, CURRENT_IMPLEMENTATION.md,
recent version notes, and the approved milestone acceptance plan.
Do not change research scope or weaken evaluation gates without user approval.
Do not create a second research controller, evaluator, memory store, or task queue.
Preserve current user changes and existing artifact compatibility.
Separate execution success, implementation conformance, scientific evidence,
strict reproduction, and model promotion.
Update the current milestone MD for small fixes and update CURRENT_IMPLEMENTATION.
Run the relevant old and new tests before remote submission; report exact limits.
```

## 9. 给 Codex 的首条提示词

```text
先执行只读审计，不修改代码。

请阅读本仓库 AGENTS.md、docs/PROJECT_ROADMAP.md、
docs/CURRENT_IMPLEMENTATION.md、最近几个版本说明，以及提供的聚焦方案包。
确认 ADR-FOCUS-001 是否已有用户明确批准。未批准时只给差异和影响分析。

批准后，以 finance-forecast-agent 的 codex/arxiv-methodcards 为功能基础，
在 feat/p1-focused-us-equity-loop 分支实施 F0。
对照 main 的真实/合成隔离、成本、development/confirmation 和序列布局修正，
制定行为级迁移矩阵。保留方法卡、原生 claim、benchmark、Memory、审批和前端能力。
先写回归负例，再修改；不整文件覆盖，不新建第二套同义实体。

本批只做 F0，并实际使用一个冻结 SPY 日频真实数据任务验收。
旧数据若已被查看，不得重新命名后声称 final 未暴露。
验收不要求出现盈利或优于强基线；要求实施、评价和结论正确。

完成后更新 F0 版本说明与 CURRENT_IMPLEMENTATION，列明真实执行命令、
日志、测试/未测项和迁移风险。所有必要测试通过才提交工作分支。
F1 在 F0 验收后另一个提交批次实现，不擅自扩展到 F2/F3。
```

提示词中的“批准后”是显式前提；本方案包当前不包含批准。