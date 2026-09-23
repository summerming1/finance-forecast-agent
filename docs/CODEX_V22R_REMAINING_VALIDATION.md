# Codex：R0–R6 加固完成后的剩余独立验收

## 最新结论：2026-09-23

本轮安排的补测已结束，完整命令/结果见 `validation/V22R_SUPPLEMENT_20260923.md`。工程 PARTIAL；R0–R3 PASS，R4 BLOCKED_NO_ELIGIBLE_DATA，R5 FAIL，R6 BLOCKED_NO_REAL_USER。Windows 全仓 398/1/3，唯一失败为 symlink 权限；Linux 同源码核心两版本各 238 passed、Chromium/冻结 SPY CI 通过。主矩阵 Random 8/9、TPE 9/9、One-shot 4/9、Adaptive 0/9，独立长时限补测成功不冒充统一设置矩阵通过。真实数据模拟用户不是独立客户；2026 行情外部使用无法确认，不能宣称未暴露。macOS/GPU 按用户要求不测；不自动再跑矩阵或开发 V3。下文 2026-09-22 数量与当时发布状态均为历史记录。

## 2026-09-22 补测更新

**最新续测**：用户另行批准了额度耗尽时依次换模型。本轮从 `5040c61` 开始的真实 3×3 补跑已结束：Random/TPE 各 9/9、One-shot 3/9、Adaptive 0/9；原始及新模型额度 403 均实际记录，最后切到 qwen3.8-flash 后仍有最终超时。14 项建议合同失败没有用换模型抹去。当前代码 Windows 累计 231/1/2、Chromium 1/1；真实 Live→离线 Replay、Live Memory cold/warm、下载包复算/新进程均补测。原始缺失资产恢复，匹配 PDF 环境的 27 项相关复验通过。精确命令、失败与当前发布边界见 `validation/V22R_LLM_RETRY_20260922.md`。下段 18 个 LLM 臂失败是**此前历史矩阵**，不是本次新结果。工程仍 PARTIAL，R6 仍 validation pending；不继续自动重跑或开发 V3。

本轮从 `625283636cef4faa080f8521683f81491611b5ff` 继续，没有重新应用 R6。Windows 正常 Chromium 完整 E2E 已两次通过；真实百炼两轮录制→清凭证并禁止网络的新进程 Replay、真实 SPY Campaign 进程树终止/恢复、实际网页 approve/reject、模拟 CSV/Parquet 交付及可信模型新进程一致性均已补测。真实 3窗口×3种子×4臂已全部尝试（exit 1）：Random/TPE 18臂完成，18个 LLM 臂失败；47逻辑请求中29返回/18失败，费用和人工分钟数未知。不能以规则结果替换失败或声明 Agent 优势。详细最终数量/提交/CI 和未闭合项见 `validation/V22R_WINDOWS_SUPPLEMENT_20260922.md`、派生矩阵 JSON 与 `CURRENT_IMPLEMENTATION.md`。本轮结束后停止，后续诊断/重跑须另行启动，不自动开发 V3。

下方“正式提交结果”和原始阻塞是历史基线；验收流程仍保留供复验，不表示上述项目尚未测试。真实用户、合法未暴露确认、macOS、历史资产/native/GPU、实际人工时间和可移植信任迁移仍不能宣称已通过。Windows symlink 创建权限阻塞没有通过改 skip 消除。

## 任务与边界

仓库 `summerming1/finance-forecast-agent`；正式分支 `feat/mission-research-v2`。R6 已提交 `3fdd2d6403bc425d172d15eba749bcdc925f33e2`（tree `4f740f79335a0a25edc78668f0aecdd9d4a5db62`）。不要重新应用 R6 patch，也不要 merge `validation/r6-20260922`；先从正式分支拉取并确认 HEAD。

本轮只做剩余验收、对抗审查和最小 bug 修复。不要重写已存在的 R0–R6，不开始 V3，不扩展资产/频率/任务，不增加第二套 Controller/Queue/Evaluator/Memory，不解除任意代码、反序列化模型或确认权限边界。模拟样例不等于真实用户/供应商/金融能力。

先执行 `git status --short`、`git fetch origin`、`git branch --show-current`、`git rev-parse HEAD`、`git log -12 --oneline`。有用户未提交修改时保留，不 reset/stash/强推。记录 branch/base SHA/tree、工作区 diff、Python/OS/依赖以及 input hashes。保持原来的受控状态库；不要新建空库来重置暴露记录。更新代码前完成或取消旧运行，跨执行合同的新研究创建新 Campaign。

阅读顺序：AGENTS.md → docs/PROJECT_ROADMAP.md → docs/CURRENT_IMPLEMENTATION.md → 接受的 ADR 001/002/003 → FOCUSED_ARCHITECTURE.md → FOCUSED_ACCEPTANCE_TEST_PLAN.md → V2_MISSION_RESEARCH.md → docs/validation/v22r_acceptance.json → FRONTEND_USER_GUIDE.md → 本文。CURRENT 是当前状态；V2 中旧阶段的结果是历史记录，不是新 SHA 的测试证据。

### 已知 R6 原始正式提交结果（历史）

- Focused Mission validation `35691460180`：Python 3.11 / 3.13 各 203 passed，Ruff 通过。
- Focused final acceptance `35691460205`：成功。
- Focused browser acceptance `35691460214`：失败；当前失败位于候选切换后的 combobox value 断言。应先复现这个失败并做最小修复，再继续完整浏览器路径。
- 以上不代表真实 provider、真实客户、合法未暴露 confirmation 或 V3 已通过。

## 0. 证据格式与已测范围

每阶段报告 PASS / FAIL / BLOCKED_ENV / BLOCKED_ASSET / BLOCKED_CREDENTIAL / NOT_RUN_COST。给出实际命令、exit code、JUnit或日志路径、源码身份、输入身份、模拟/真实等级。不能仅说“测试通过”。无法运行要记录原因，不将其写成自动 skip 后的全绿。

已经覆盖的工程路径请先复验，不重新实现：R0状态一致性；R1身份、隐藏正文过滤、不可变录制和严格回放；R2事务预算/generation/真实进程中断；R3停止/审核/消融/诊断和Memory；R4封存授权、篡改/并发/崩溃和包外模型信任；R5真正Optuna TPE、实际Advisor/共享Controller与账本遥测；R6持久网页/审核继续/研究包/受控数值特征。专用 Chromium CI 使用模拟输入和真实后台子进程，不是客户验收。此前环境的本地浏览器策略阻塞是历史记录；本轮 Windows 使用正常安装的 Chromium 通过实际 E2E，没有绕过主机策略。

## 1. 当前源代码累计回归与平台矩阵

按 `.github/workflows/focused-v1-validation.yml` 当前命令运行 focused + shared queue + Memory、Ruff、compileall。Linux shell会展开 glob，PowerShell 不要把未展开的字符串直接交给 pytest：

```powershell
$tests = Get-ChildItem -Path tests/test_focused*.py,tests/test_task_queue*.py,tests/test_*memory*.py | Select-Object -ExpandProperty FullName -Unique
python -m pytest -q $tests --junitxml=validation/local-cumulative.xml
```

Python3.11/3.13分别建立环境。没有相应解释器时记录BLOCKED_ENV，不能把其他提交的CI算成本机验证。Windows重点复验无副作用存活检查、PID创建时间、进程树取消、generation fencing、Parquet、路径空格/Unicode、模型包新进程推理。macOS同样单列。Linux POSIX kill测试跳过不等于Windows恢复正确。

## 2. R1/R3/R5/R6：真实百炼 live → 不可变录制 → 严格离线 replay

使用用户现有合法provider凭证；不要打印/提交API key，不修改实际模型名称来假装可用。当前上下文/feature contract比旧fixture增加了字段，必须在最终SHA上重新录制。

先运行2轮、每轮1候选、小预算的真实live。保存每轮prompt/call_id/provider/model/response及record hash、usage、HTTP重试、编译结果、真实候选/Feedback。格式错误明确拒绝；允许的重试要有成本和失败记录，不silent fallback。

随后选择同一组call_id，以同Task/Data/Protocol/能力/Memory快照运行replay。**清除环境key不等于严格断网**；使用隔离进程和可验证的网络请求禁用/网络命名空间/测试HTTP入口断言，确认provider请求次数为0。不要修改生产网络安全策略。`.env`可能重新加载凭证，必须考虑这个路径；禁止网络而不是猜测无凭证。

核对prompt、计划、CandidateConfig、逐行预测、指标一致；source/时间/运行ID允许按设计不同。负例：缺录制、重复prompt多个call_id未指定、修改response/record/metadata、跨provider误选、隐藏证据哨兵正文、错误parent/control/feedback角色、超范围参数，均失败且不开始训练。

没有凭证：BLOCKED_CREDENTIAL。手写fixture和deterministic绝不能填成live结果。

## 3. R2/R3/R6：完整网页和实际中断验收

固定 `FFA_WORKSPACE_STATE_DB` 为操作者原来的权威库；URL只使用已登记的project/mission/campaign ID。按照 `.github/workflows/focused-browser-acceptance.yml` 或本地已授权浏览器运行：

```text
创建固定中/英文模板 → 配置真正生效的起点基线/允许特征/预算
→ 提交到队列 → 候选A/B切换 → 页面刷新
→ 关闭浏览器 → 新上下文打开历史URL/历史选择器
→ 下载ResearchPackage → 独立哈希核对与指标复算
→ 显式refit并下载ModelBundle
```

操作期间研究attempt数不能因查看/下载增长。相同表单重复提交保持同operation；有意新一轮先显式准备新任务。错误task（weekly volatility/QQQ/trading）不能静默映射SPY。Arrow混合类型警告不能通过丢弃原始diff解决。

再使用可追踪Replay计划触发request_review，真实网页批准/拒绝/恢复；等待阶段不额外调用LLM或fit。仅AppTest/API通过时不能写真实浏览器审核已通过。

真实queued Campaign完成基线及候选A，在B的可控同步点终止进程树；Windows用正常原生终止接口，Linux用POSIX。恢复后检查A/基线零重训、冻结计划及Memory快照不变、失败预留不退回、重试新attempt计费、旧worker迟到不能覆盖。保留中断时点、PID+创建时间、DB/事件及文件hash。测试进程已训练但未提交、已保存预测但未提交状态、取消与完成竞争、活着的孤儿子进程、同时提交同key、held任务关联中断等边界。

使用测试创建的任务/PID，不能误终止用户其他任务。

## 4. R4：真实确认资格与可信模型包

工程负例必须复验，但真实金融确认没有合格输入就保持 BLOCKED_NO_ELIGIBLE_DATA。旧SPY、模型开发中见过的时段、改名/改标签/改变特征/换seed均不成为未见目标；用户自报sealed不能直接授权。确认数据来自可信操作者审核的封存来源，不是系统自动证明人类没见过。

首版只支持冻结训练集各fit一次的固定留出；模型/基线/目标行/评价/代码/环境必须先冻结。Worker只按grant ID加载实际登记数据；模拟输入或模拟来源的结果必须保持simulation_only_confirmation。确认结果不能作为当前研究Memory或Advisor调参反馈。并发、失败和训练后崩溃消费资格；没有“自动重置资格”补测。

ModelBundle加载前检查包外DB、租户、元数据/模型hash、路径/符号链接、环境。改包内trusted字段无效；不得为便于搬迁而自动信任包旁数据库。未经审核的旧包重发；真正跨机器可信登记迁移尚未实现，记录BLOCKED_UNSUPPORTED而不是解除校验。自定义ext特征模型交付可测，但当前确认协议不支持该特征，不能假装已有custom-feature confirmation。

验证训练截止包括已成熟标签。训练尾部删label后预测只证明接口；必须另外使用真实未来/样本外输入才能讨论预测效果。

## 5. R5：有意义的真实LLM策略对照和Memory消融

使用新版 `scripts/run_research_value_benchmark.py`，而不是旧proxy结果。四组Random/真实OptunaTPE/实际one-shot Advisor/实际adaptive Advisor，所有fit仍经同Controller/evaluator/账本。模式明确live/replay/deterministic，不把规则策略标LLM。

先六配置枚举验证去重，再冻结足以越过TPE startup的有界搜索空间和预算。参考命令（实际成本先核查现有许可与预算，不能无限扩大）：

```text
python scripts/run_research_value_benchmark.py --raw-spy-json inputs/spy_chart_2010_2025.json --source-metadata inputs/spy_source.json --candidate-count 12 --startup-trials 4 --seeds 17 42 91 --windows 2010-01-01 2013-01-01 2016-01-01 --llm-mode live --fixture-dir validation/live-benchmark --out validation/value-live.json
```

samewindow内成对比较；目标重叠的窗口不是独立样本；确定性重跑不增加统计样本量。检查独特配置、重复提案、真实有效seed、实际fit预留/开始/完成/不确定消耗、失败候选、无改善但有效的实验、fold稳定性、LLM/HTTP调用、usage和成本。provider未返回usage或定价未知则保留null，不报0；人工时间必须有实际测量，不能由token或walltime虚构。

主对照Memory cold。单独固定一个审核过的先验文件，使用`--memory-mode ablation --memory-store ...`，各arm独立副本、同一初始快照、不互看结果。确认减少的是重复实验或操作时间，不把历史最好分数当本轮结果。Agent不必胜过TPE；不删失败/负结果、不换threshold找赢家。报告有限结论与不确定性。

## 6. R6：真实用户受控BYO及验证等级

需要真实设计合作用户的非核心CSV/Parquet、一个审核数值因子和内置基线配置。仅支持SPY日频next-session任务，ext_*一个数值列；不上传LightGBM/joblib/脚本来伪称兼容，不增加自动代码执行。

记录来源、许可、标签定义、逐行时点、reviewer、feature版本、data raw/semantic/target IDs、接入人工分钟数、研究结果可读性、是否愿意第二次使用。没有用户就BLOCKED_NO_REAL_USER；两个模拟客户只证明复用，不证明需求/付费或低接入成本。

对照复算有价格/无价格/最后标签无下一价格三种情况；无价格保留user_declared_unverified，提供的时间戳一致不证明特征来源无泄漏。测试duplicate header/column mapping collision、NaN/Inf、非交易日、缺session、周级horizon、最后目标、错timezone、feature available_at>decision_at、自报sealed、未审核feature、变metadata清洗exposure。两个客户端必须走导入→队列→Controller→Manifest→反馈→研究包→模型包，而不只测loader。

## 7. R0及整个仓库：历史资产、文档与长期可复验

核对README/Roadmap/Handoff只引用当前能力，不让历史“PR已完成”代替R验收。保存每条新失败的nodeid、首个异常、缺失文件、期望hash、是否R5基线同样失败、修复归属。不能删除历史native测试，不能把缺资产标科学成功。

全仓测试可先collect-only，再在明确时间/GPU预算内执行。缺PDF、method card、官方checkout/patch、DVC数据、长训练环境分别标记BLOCKED_ASSET/BLOCKED_ENV/NOT_RUN_COST。CI中老的冻结SPY artifact有保留期；使用用户保存的冻结副本和hash，不换最新下载制造同名“冻结数据”。如果artifact过期，修复可复验的资产供应方式，不降低断言。

R0–R6当前使用单机可信操作者。多主机SQLite共享、恶意同OS用户、真正SaaS认证/权限、巨大文件DoS、长时间生产运维不在已验收范围；不要在本轮暗中创建企业平台。

## 8. V3准备而非开发

分别报告：INTERNAL_FORWARD_RECORDING_READY、EXTERNAL_PILOT_READY、RESEARCH_VALUE_EVIDENCE。内部前瞻准备检查模型/输入版本、decision_time、prediction_created_at、input_asof、target_session、label_end_time、label_available_at、修订规则、不可覆盖记录。没有真实客户或尚未击败TPE不是内部记录的绝对阻塞，但时间/完整性不可靠时不能开始。当前没有实现正式prediction生命周期或定时Shadow平台，本轮不新增。

## 修复与最终交付

发现bug先保存失败测试/步骤，最小修复，定向回归→累计相关回归→lint/compile→有影响的真实数据/浏览器→单独commit及非强推→核对同SHA CI。不要修改评价来让模型赢，不隐藏前一批失败日志，不把未推送本地源码说成已交付。

最终给出每阶段状态、各OS/Python矩阵、实际live次数、严格断网回放证据、真实/模拟BYO、合法确认与缺口、Benchmark分布与限制、全仓失败清单、截图/日志/包的位置、base/finalSHA和用户实际操作流程。明确哪些新能力未实现而非仅未测试。停止在补测与修复，不自动进入V3。
