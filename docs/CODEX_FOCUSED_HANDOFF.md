# Codex handoff — V2.2-R

当前状态唯一来源：`CURRENT_IMPLEMENTATION.md`；实际门禁：`validation/v22r_acceptance.json` 和同 SHA 的 CI。正式分支 `feat/mission-research-v2`。先检查工作区、远端 HEAD，再按 AGENTS 阅读 Roadmap、当前状态、ADRs、Architecture、Acceptance 和 V2 版本日志。不要按旧 PR/R 编号或包版本推断完成。

R0–R6 是原能力的验收加固，不是新产品主线。保留同一个 Controller/Queue/Evaluator/Memory；RuntimeDB 是唯一运行状态权威，JSON 是导出。R5 已提交为 `1bfe5ef78dd475d12f386c528ace44638e27434c`。R6 已提交为 `3fdd2d6403bc425d172d15eba749bcdc925f33e2`，接通持久工作区、审核/继续/导出和一个已审核数值特征的同任务 BYO；R6 当前是 code committed / validation pending。没有启动 V3。

下一轮只做 `CODEX_V22R_REMAINING_VALIDATION.md` 的补充验收与最小 bug 修复，不重复实现 R0–R6，不扩资产/任务/任意代码权限。每个修复先留失败证据，再定向/累计测试，最后逐批提交与正常推送，不能静默放宽门禁。

升级前完成或取消旧运行。旧 Campaign 缺合同只读；跨代码/环境/特征/数据协议不强行恢复。旧 ModelBundle 不因包内 trusted 字段获得信任，需操作者重发；复制包不迁移注册授权。相关项目必须共用原权威数据库，空数据库不代表历史未暴露。

live 与 replay 分开；模型/人工成本未知时保持 null。确定性或手写 fixture 只作工程证据。真实客户、未见金融数据、前瞻和研究优越性需要独立证据；一组通过的单元测试或模型包加载不关闭这些门禁。


## 当前第一优先级

从正式分支最新 HEAD 开始，不重新应用 R6 patch，也不要 merge `validation/r6-20260922`。原始 run `35691460214` 的 candidate-selection 失败已经在 Windows 复现；本轮测试修复后完整 Chromium E2E 连续两次通过。真实百炼录制→严格离线回放、Windows 完整 Campaign 崩溃恢复、真实网页审核及模拟 CSV/Parquet 交付也已补测。精确提交、累计回归、同 SHA CI 和失败保留见 `validation/V22R_WINDOWS_SUPPLEMENT_20260922.md`，不要把这些已完成工作重新标成未实现。

仍按 `CODEX_V22R_REMAINING_VALIDATION.md` 逐项处理真实 LLM Benchmark 完整性/研究质量、macOS、真实用户、合法 confirmation 和历史资产/native 等独立门禁。测试发现 bug 时做最小修复、单独提交；不要扩产品范围或启动 V3。
