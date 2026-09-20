# 2026-09-20 交付核验：V1.1 + PR-0 准备，不是 PR-4 完成版

## 1. 权威状态与纠正

核验分支：`feat/mission-product-pr0-pr6`。
本轮开始时 HEAD：`9f8148d674030cfaa5462662d54f30cd053944cb`。
核验源码树：`a3e22f44f774fa84e29562fef291e1097b0c5c6b`。

从 CI 原始源码包恢复工作目录后，以 `git write-tree` 重建得到完全相同的 tree SHA。相对 V1.1 基线 `571beb91ad8911cdb540192f6a0543755da6edb6`，远程只有四个准备提交、两个新增文件：

- `.github/workflows/mission-product-validation.yml`：focused 回归和源码/依赖归档。
- `docs/ADR_MISSION_PRODUCT_003.md`：PR-0 至 PR-6 的批准方向与模拟测试边界。

没有 `src/`、`apps/` 或 `tests/` 的业务改动。当前可访问运行目录、源码包和 Library 检索未找到此前声称的 `finance_mission_pr0_pr4_checkpoint.zip`、PR-1 至 PR-4 补丁或 48 项测试日志。因此撤回此前的“PR-1～PR-4 已完成、48 项通过”交付声明；不能按 V2-A/V2-B 已交付处理。这不证明过去从未有过临时文件，但现在没有可发布、可复验的对应实现。

**当前产品功能版本仍是 V1.1 reliability。** `pyproject.toml` 的包版本 `0.2.0`、TaskSpec 的 `task_version=v2` 和分支名中的 v2 都不表示 Mission 产品 V2 已实现。PR-0 已有 ADR/CI 准备；既有 Roadmap、Architecture、Acceptance、Handoff 与该增补 ADR 的系统性对齐仍应收口。

## 2. 本轮实际新增什么

本提交只增加核验和验收资产，不替代缺失的业务代码：

- 本文：更正版本与交付状态，记录真实结果和未完成门槛。
- `docs/FOCUSED_TEST_RUNBOOK.md`：可直接执行的 focused、真实输入、live/replay、手工 UI 和后续验收流程。
- `scripts/probe_focused_failure_semantics.py`：不修改生产代码，通过故障注入复现 PR-1 的待修语义问题。
- `docs/validation/20260920-focused-audit.json`：机器可读的本地环境、源码身份和验证结果。

业务 Controller、Queue、模型、特征、split 和 evaluator 均未改写；没有新增 Mission、研究包、恢复、Memory 接入或 BYO 功能。没有合并到主分支，也不将计划 PR 编号冒充 GitHub Pull Request 编号。

## 3. 本次实际运行的验证

环境：Linux / Python 3.13.5；NumPy 2.3.5、pandas 2.2.3、scikit-learn 1.8.0、exchange-calendars 4.13.1、pytest 9.0.2、Streamlit 1.64.0、Ruff 0.16.8。完整记录见配套 JSON。

| 验证 | 实际结果 | 能证明的范围 |
|---|---|---|
| focused + Streamlit AppTest | 19 passed，9.77 秒 | 17 项数据/协议/研究测试实例和 2 项 AppTest；测试数据为构造夹具 |
| focused 与新增探针 Ruff | exit 0 | 指定文件静态规则通过，不是整库 lint |
| compileall | exit 0 | 指定源码、页面和探针可编译 |
| 整库 pytest collect-only | 191 tests collected，exit 0 | 只收集清单；不代表 191 项执行通过 |
| 真实 SPY 原始输入三轮 smoke | exit 0；4002 行、28 fits、无实质改善 | 真实历史数据从原始 JSON 到受控研究闭环可运行 |
| 空 replay 目录负例 | FileNotFoundError、exit 1，符合拒绝预期 | 缺 fixture 没有静默退回 deterministic；不是完整 replay 成功验收 |
| 全部候选失败的新增语义探针 | **验收失败，exit 1** | 预算保留正确，但失败仍误报 scientific no_improvement；PR-1 尚须修复 |

真实输入来自 GitHub Actions run `35204186327` 的 `focused-real-inputs`，artifact `10488604477`。归档 SHA256 为 `ff90e7f9409bcecdfa1ab7f24bd7f345265bb58fe2a6bba99c209d7eeca4c090`，与服务返回 digest 相符。原始 SPY JSON SHA256 为 `5fb282f6278d14000592e0e432fe69a5c00fdb6f7b48cbb56368fc0e3185bbcd`。

本次真实运行：

```text
supervised rows: 4002
period: 2010-02-03 -> 2025-12-30
fit calls: 28 / 40
best baseline: baseline_ridge
baseline Ridge MAE: 0.0050337535958270355
terminal: completed_no_improvement
confirmation: not_run_historical_data_exposed
claim: forecast_only
```

这里的“真实”指输入来源，不表示独立确认、前瞻预测或可交易收益。原始数据不随本提交公开新增到 Git。

## 4. 已复现的未修问题

新增探针让两个新候选都抛出训练异常，而基线正常执行。结果为：

```text
candidate failures: 2
fit calls: 20 (12 baseline + 8 reserved candidate fits)
stop_reason: round_failed_no_completed_candidate
terminal_status: completed_no_improvement
execution_status: missing
research_outcome: missing
```

要求应为执行 `partial/failed`、研究 `inconclusive`，而非“模型研究无改善”。现有 19 项测试只检查该路径的预算与失败记录，没有覆盖新的终态验收。不能因此宣称“全部验收绿灯”。探针在当前基线故意返回非零；修复 PR-1 并满足断言后才应返回 0，不应放宽断言求绿。

## 5. 当前能力边界

主线仍是 SPY / 日频 / 下一交易日 adjusted-close return / MAE 主指标 / Ridge、RF、GBDT / 固定 development folds / 受控多轮建议 / 同步运行 / 终点保存 campaign JSON。

LLM 只能提案；数据时序、标签、split、指标和预算由确定性代码负责。已暴露历史 SPY 不可改名为 blind final。deterministic 仍为轮次模板对照，不能充当自适应研究效果证据。历史高级路径已有 LocalTaskQueue、MethodCard、Memory 等资产，不等于这些已完整接入 focused 主线。

## 6. 未执行或未完成的门槛

- 未执行真实 live-provider 调用，也未获得本轮 live-record 后离线 replay 的成功记录。
- 未进行手工浏览器完整交互验收、Windows/macOS 或本地 Python 3.11 复跑；AppTest 不替代真实浏览器。
- 未执行全部 191 项测试，未重跑历史 native 论文训练、外部数据/源码/环境验收。
- PR-1 的逐行预测/Manifest/朴素基线/Feedback/Exposure 以及正确失败语义没有对应新交付。
- PR-2 Mission/Workspace，PR-3 文献反馈研究与四臂对照，PR-4 focused 恢复与 ResearchPackage 没有可核验交付。
- PR-5 Memory/Confirmation/ModelBundle，PR-6 BYO 同样未完成。
- 没有独立确认、前瞻表现、Agent 相对优势或真实客户付费验证。

## 7. 下一步的顺序

先收口 PR-0 文档一致性，再完成 PR-1 并让本探针及新增验收通过；随后依次推进 PR-2、PR-3、PR-4、PR-5、PR-6。每个增量保留源码 commit、累计 JUnit、输入 hash 和已知限制，前一阶段未通过不得以现有 19 项绿灯替代。模拟用户/数据和人工编写 LLM fixture 只用于功能验证，必须显式标注。
