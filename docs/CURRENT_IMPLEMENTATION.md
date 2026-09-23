# 当前版本功能与技术实现说明

## 2026-09-23 用户授权续测（已结束，工程 PARTIAL）

续测起点 `887eff033053d3f2bb36e7b4b82dad431e0234a1` 已正常推送；该 SHA 的 Linux Python 3.11/3.13 各 234 项、Chromium 1 项及冻结 SPY 交付 CI 均通过（35803915631 / 35803915635 / 35803915637）。下文 2026-09-22 的失败矩阵和 Windows 限制保留为历史证据。

最小提示词修复 `84d3221b2f6643a34f0b10769b44a0aa96850f4c` 已推送：补全条件字段、父配置约束与目录原子引用，没有放宽编译器、预算或评价。4 项新合同测试、35 项相关回归通过。Windows 累计 235 passed / 1 failed / 2 skipped / 3882.16s；匹配隔离 PDF 环境全仓 398 passed / 1 failed / 3 skipped / 2412.77s，两者 exit 1，唯一失败为 symlink fixture WinError 1314（BLOCKED_ENV）。当前代码 Chromium 1 passed / 177.62s，Ruff/compile 通过；同修复 SHA Linux Python 3.11/3.13 各 238 passed，Chromium、冻结 SPY CI 均通过。

完整结果见 [2026-09-23 报告](validation/V22R_SUPPLEMENT_20260923.md) 与派生 JSON。主矩阵 Random 8/9、TPE 9/9、One-shot 4/9、Adaptive 0/9 完成；独立补测完成失败 Random、两个 One-shot 和一个真实 Adaptive（advisor_stop，no_improvement），不改写原失败。含补测 49 attempts / 2200 charged fits / 140 logical calls / 182 HTTP；696 预测、1794 哈希、117 提示词独立核对。混合模型/时限不是统一设置的完整价值对照，R5 FAIL。新 Live→断网 Replay 各 20 fits、2/0 请求一致；真实 Windows crash/resume、网页审核、真实数据模拟 BYO 与显式外部特征候选包新进程通过。R6 仍 code_committed_validation_pending；不启动另一轮矩阵或 V3。

用户明确无法确认 2026 年 SPY 是否曾用于调参/研究。因此新下载不构成独立未暴露确认：原权威库拒绝 unknown provenance，0 confirmation fits。R6 本次参与者由助手模拟、行情为真实数据，不能计为真实客户。macOS/GPU 按用户要求不执行；不开发 V3。

## 唯一当前状态来源：V2.2-R 能力与验收加固

正式分支：`feat/mission-research-v2`。V2.2-R 实施起点：`6e4f194453f77037929052a0a978cc76bc2017b7`。R6 产品实现提交：`3fdd2d6403bc425d172d15eba749bcdc925f33e2`；本轮补充验收起点：`625283636cef4faa080f8521683f81491611b5ff`。后续测试/文档提交不表示新增产品能力。

原 PR-1～PR-6 已有模块实现；此前“全部验收完成”的表述过度。验收缺口现在按 R0→R6 修复，不重写项目，也不自动开始 V3。

| 能力 | 有实现 | 原工程测试 | 真实运行 | 用户/科学验收 | 尚未关闭的合同 |
|---|---|---|---|---|---|
| 预测/Manifest/确定性反馈 | 是 | focused 通过 | 冻结历史 SPY | 非独立金融证据 | 身份已加固；恢复绑定 R2 |
| Mission/Workspace | R6 持久工作区代码已提交 | AppTest/队列/导出/刷新及双版本核心 CI；补测见下 | 本轮 Windows Chromium 完整 E2E 两次通过；候选切换/新上下文/下载不增研究 fit | 非技术用户试用待测 | 单机可信操作者；同 SHA 新 CI 和平台缺口见验收报告 |
| Live/Replay | 已实现 | 可见性/篡改/引用负例通过 | 新qwen3.8-flash两轮Live→清凭证断网Replay，各20fits、2/0请求，逐行预测一致 | 不是科研质量证明 | 实际请求无隐藏哨兵；成本未知 |
| 动作与 Memory | 已实现 | 动作/隔离/父配置回归通过 | 强模型cold/warm各20fits/2calls，0→0重复；网页approve/reject通过 | 历史小样本不证明泛化 | flash warm缺statement失败保留；未证明减少重复 |
| Queue/恢复 | R2 事务 + R6 提交关联 | 原子提交/代次/预算/缓存/held-link修复 | 本轮 Windows 真实 SPY 完整 Campaign 进程树终止→新进程恢复，基线/A不重训、预算不退回 | 单机工程验收 | macOS 未测；Windows 原生符号链接权限受限 |
| Confirmation | 已实现 | 数据错绑/一次性/篡改门禁通过 | 179个2026真实目标unknown provenance被拒绝，0 confirmation fits | BLOCKED_NO_ELIGIBLE_DATA | 用户无法确认外部使用，新下载不等于未暴露 |
| ModelBundle | 包外可信登记 | 篡改/路径/租户/环境负例 | 两个选定ext候选包原可信库新进程一致 | 非样本外效果 | Windows symlink权限受阻；portable trust migration NOT_IMPLEMENTED |
| Benchmark | 同一Controller/evaluator | 真实TPE/身份/账本通过 | 主矩阵Random8/9、TPE9/9、One-shot4/9、Adaptive0/9 | 完整价值矩阵FAIL | 含补测49attempts/2200fits/140逻辑调用/182HTTP；额外成功不覆盖原失败 |
| BYO | 受控表格/审核数值特征/内置配置 | CSV/Parquet负例与交付通过 | 两个真实数据simulation_only参与者 | BLOCKED_NO_REAL_USER | 本地路径导入不是远程上传，特征因果仍须人工审核 |

## R 批次执行状态

- R0：统一状态、默认关闭原型独立确认标签、标记旧对照结果；本批测试记录见版本日志。
- R1：统一内容/目标/配置身份，可见证据共享投影，v2 不可变 LLM 录制与哈希校验；本地 87 项累计回归及真实 SPY smoke 通过。
- R2：既有 Queue/Controller 使用事务状态，冻结计划、缓存和预算可恢复；本地 focused 104 项加共享队列 4 项通过，真实 SPY smoke 通过。
- R3：实际控制动作、父模型约束、剩余资源上下文和有界 Memory 已实现；本地 128 项累计及共享回归通过。
- R4：封存数据与冻结确认授权、单次执行、包外可信 ModelBundle 已实现；验收记录见版本日志和条款映射。
- R5：实际策略对照已接入同一 Controller，使用真正 Optuna TPE；默认规则/回放仅为工程证据，验收见版本日志。
- R6：持久网页、受控特征 BYO、导出/审核/恢复接口代码已实现并提交为 `3fdd2d6403bc425d172d15eba749bcdc925f33e2`。原始提交的 Python 3.11/3.13 累计核心回归各 **203 passed**，Ruff/compile、冻结真实 SPY final acceptance 通过；原始 Chromium run `35691460214` 失败记录保留。本轮 Windows 修复后浏览器两次通过，但剩余外部门禁仍须分别报告，R6 保持 `code_committed_validation_pending`，不是全部验收完成。

## 当前边界

仅 SPY、日频、下一 XNYS 交易日调整收盘收益回归、MAE、forecast_only。单机可信操作者；租户过滤不等于 OS 级隔离。不执行任意用户代码、模型反序列化上传、自动交易或新资产任务。

## 历史证据：2026-09-22（当前结论以上方 2026-09-23 为准）

用户另行批准的额度替换续测已结束，详见 [本轮完整报告](validation/V22R_LLM_RETRY_20260922.md) 与 [逐臂数值](validation/V22R_LLM_RETRY_20260922.json)。从 `5040c61` 开始，最小 prompt 修复 `02acafe`、测试隔离修复 `92a8189`；新 Windows 累计 **231 passed / 1 symlink 权限失败 / 2 skipped**（2290.47s），当前代码真实 Chromium **1 passed / 137.25s**，交付物复算/原可信库新进程一致性通过。全仓 **391 passed / 3 failed / 3 skipped**（3245.62s），三项逐一保留：符号链接权限、历史 PDF 解析版本、旧已采集的界面测试；后两项在隔离匹配环境/测试修复后合并 **27 passed**。缺失原始历史资产已从固定来源恢复，但没有重跑 GPU/native training。主环境 PDF 严格回放仍有版本边界。新报告取代旧记录的“当前未测”描述，不改写旧失败。

完整替换模型矩阵有 37 次执行尝试（36 臂 + 1 额度重试），1660 计费 fits；71 返回记录、526 预测与 1356 文件哈希独立核对。额度切换成功不等于研究建议有效；工程仍 **PARTIAL**，真实用户和独立确认仍 **BLOCKED**，V3 **NOT_READY**。本轮新增生产修改尚未推送，之前同 SHA Linux CI 不冒充新 SHA 验收。

2026-09-22 Windows 补测详见 [逐项报告](validation/V22R_WINDOWS_SUPPLEMENT_20260922.md)。已完成真实 Live→严格离线 Replay、真实 SPY 进程树 crash/resume、实际网页审核 approve/reject、CSV/Parquet 两个模拟客户、研究包复算与 ModelBundle 新进程一致性。浏览器测试最小修复已在本机连续两次通过；Windows 等待时限修复保留所有语义断言。全仓首轮 **343 passed / 20 failed / 3 skipped**，失败逐项列明。测试修复提交 `6299ca4` 的 Windows 累计 **229 passed / 1 symlink 权限失败 / 2 skipped**，exit 1 保留；同 SHA Linux Python 3.11/3.13 各 **232 passed**，Chromium 和冻结 SPY CI 通过。不宣称全仓或所有平台通过。没有真实客户、合法未暴露确认数据或 macOS 环境。R6 总状态仍是 `code_committed_validation_pending`，不写 fully accepted。

历史基线 Linux/Python 3.13.5：66 passed（45.96s）；原远端 3.11/3.13 CI 也成功。旧 Windows 65 passed/1 skipped 是历史记录，不替代上述本轮补测。真正未暴露确认、真实用户、前瞻和 macOS 仍缺证据。

历史科学记录保留在 `HISTORICAL_PLATFORM_STATUS.md` 和原版本文档中；不作为本轮测试通过的证明。具体 R 验收映射见 `validation/v22r_acceptance.json`；批准方案见 `V2_MISSION_RESEARCH.md`。

## R1 使用与兼容说明

2026-09-22 替换模型补测：Advisor prompt 明确要求既有顶层 `hypotheses` JSON，不允许以 schema 名再包一层；validator 保持严格拒绝。`qwen3.7-flash-2026-07-15` 两轮真实调用和新进程断网 Replay 已复验一致，31 项 supplemental 测试通过。完整价值矩阵与工程总验收仍须单独判定，不能由小预算 smoke 推定通过；测试进程覆盖模型名，不修改用户 `.env`。

新录制位于 `<fixture_dir>/<schema>/records/`，每次调用有独立 call_id；相同 prompt 的多个调用不会覆盖，回放须明确选择。CLI 的 `--replay-call-map path.json` 接受 prompt hash → call_id 映射。未指定且存在多份记录时拒绝歧义，不选“最新一条”。

新记录校验完整 response/record SHA256，provider metadata 与核心字段隔离；录制不等于通过研究校验。旧 v1 fixture 可按显式 legacy 兼容读取，已有 response_hash 会校验，缺完整性信息不会被升级成 v2。

数据原始字节哈希保留；规范化 float64 观测、目标集合、目标内容与配置/执行身份分开。CSV/Parquet 或来源显示名改变不创造新目标。旧数据指纹不会自动迁移为可信新身份，旧记录仍可查看。R2 现在将这些身份绑定到实际执行、缓存和恢复合同。

## R2 持久执行与兼容边界

`LocalTaskQueue` 公共接口保留，SQLite 是任务/attempt/预算/计划的权威存储；JSON/JSONL 是只读导出视图，修改导出不能复活取消的任务。focused 提交让 Queue 与 Controller 共享同一事务库。

新 Campaign 每个基线/候选先预留预算，再运行；失败或中断的预留不免费退回。`fit_calls` 是保守占用预算，`resource_usage` 另列观察到的 fit 开始、完成和不确定消耗。恢复读取冻结计划与 Memory 快照；已接受预测/Manifest/Feedback 校验哈希后复用，不重训。不同数据、切分、预算、代码或环境不能沿用同一 campaign_id。

旧 worker 的 generation 不能提交新 attempt 的结果；取消先持久化再终止经过 PID+创建时间核对的进程树。存活检测不发送信号。真实 queued Campaign 在候选 A 完成、B 一折训练完成时强制终止后由新进程恢复：A/基线/计划哈希保持，重试消耗计费，最终研究包可导出。

旧 R2 之前 Campaign 可查看，但无足够 attempt 事实时不伪造恢复。代码更新前应完成或取消运行中的 Campaign；跨执行合同的继续研究应创建新 Campaign。R6 网页现在使用同一队列并从账本读取状态，不通过浏览器请求同步执行研究。显式单模型 refit 是独立操作者操作，不自动推广或部署。

## R3 动作与记忆

`stop` 不创建虚假 Candidate；`diagnose` 对已有预测做只读残差/fold 摘要；`request_review` 保存暂停，不再调用模型。通过 `focused_runtime.resolve_campaign_review(state_path, campaign_id, review_id, tenant_id=..., decision="approve"|"reject", reviewer=...)` 记录操作者决定，再以相同冻结合同恢复。批准只允许继续原研究合同，不修改数据或评价。

消融从实际对照派生，只移除一个已有特征组；简化保持模型族/seed，减少声明的维度。未知动作、LLM 自报指标或评价覆盖被拒绝。Memory 保存真实配置、假设、diff 与可定位预测；写入按租户和 run_id 隔离，损坏文件不会当空库覆盖。相同数据的 warm Memory 可减少重复研究，但不把旧分数当本轮结果，也不声称泛化增益。


## R4 确认与模型交付：使用、信任和兼容

沿用 `RuntimeDB`，不新增数据库后端、Queue、Controller 或数值 Evaluator。API 属于**单机可信操作者**，不是给不可信用户/Advisor 的权限系统；调用者能修改主机文件或权威数据库时，不宣称 OS 级安全。所有关联项目必须使用同一受控 `runtime.sqlite3`，创建空库不代表已有历史变成未暴露。

### 确认协议

`register_delivery_dataset` 登记实际训练/确认帧、Task/Snapshot、原始来源、审核者、目标集合与实际文件哈希。确认帧被复制到受控 Parquet，工作者只接受授权 ID；不接受调用者任意指定的 frame、split 或模型路径。登记过的开发目标（含旧 Campaign 暴露区间）不能再封存；改标签值、文件名、来源名或等价日期写法不产生新的未见目标。日频 session 字段只接受无时区的午夜/日期表示，实际时刻使用额外的 `decision_at`、`label_available_at`。

`create_confirmation_grant` 冻结候选、基线、Task、训练/确认登记、评价阈值、代码和依赖环境。首版协议仅 `fit_training_once_fixed_holdout_v1`：基线与候选各训练一次，评价相同留出目标。训练标签可用时刻必须严格早于首个留出决策时刻。不支持静默滚动再训练。真实数据需要可信操作者审核封存来源；`sealed_before_research` 是需负责核实的来源声明，不是系统自动证明人类从未见过数据。

```bash
python scripts/run_focused_confirmation.py --state-db projects/finance_agent/runtime.sqlite3 --grant-id <已登记的授权ID> --tenant-id default
```

授权在执行前原子消费。并发调用不能重复训练；成功重读返回相同封存结果。异常/进程崩溃保留已消费状态，无自动重试、更不能重发授权反复看结果。失败只能由操作者调查，不提供自动“重置资格”接口。结果存于权威账本及 `delivery_artifacts/confirmations/<grant>/result.json`，不进入当前研究 Memory。任何模拟输入使输出保持 `simulation_only_confirmation`。

### ModelBundle

模型包只能由平台 refit 产生，必须由**包外**权威数据库登记。包内 `trusted_internal_bundle` 不再授予信任。加载前检查来源、租户、环境、元数据和模型字节哈希、路径和符号链接；反序列化使用已验证的同一份字节。输出目录已存在则拒绝覆盖。

```python
from finance_forecast_agent.focused_delivery import refit_model_bundle, predict_model_bundle
state_db = project_dir / "runtime.sqlite3"   # 固定受控配置，不从上传的模型包取得
bundle = refit_model_bundle(frame, selected_candidate, task=task, dataset=snapshot,
                            out_dir=project_dir / "models" / "new_bundle_id",
                            state_path=state_db, tenant_id="default")
predictions = predict_model_bundle(bundle, unlabeled_frame, state_path=state_db, tenant_id="default")
```

省略 `state_path` 仅允许操作者预设 `FFA_DELIVERY_STATE_DB`；未配置就拒绝。不自动相信包旁的数据库。旧未登记包不自动迁移为可信，需从原训练数据重新 refit/签发。复制/导出包不自动把另一个环境变为可信加载端；可信转移登记与跨环境转换尚未提供。

训练截止同时记录最后 session、最后标签可用时刻及 `training_asof`。有 timezone-aware `label_available_at` 时使用显式值；否则**明确记为按 XNYS 收盘假定的可用时刻，不是实测供应商到达时间**。这不是 V3 前瞻生命周期实现。

### R4 未测边界

没有取得合法未暴露真实金融数据、没有真实独立确认结论。本轮 Windows 模型包新进程加载/预测已通过；符号链接负例因主机权限阻塞，macOS、安全隔离部署及实际客户端跨机信任迁移仍未验收。当前真实 SPY 仍为历史 development；删除训练尾部 label 后推理只证明接口，不是样本外表现。R5、R6 工程补测不关闭真实金融确认限制。


## R5 真实策略对照及使用边界

`focused_benchmark.BenchmarkAdvisor` 只选择候选/动作，实际编译、预算、attempt、fit、逐行预测和评价仍由原 Controller 执行。Random、Optuna TPESampler（冻结有限配置ID的分类搜索）、一次性原 Advisor 和逐轮原 Advisor 共用合同。不是额外的候选评测循环。TPE 的启动数、实际进入模型采样的决策数、拒绝重复采样次数明确记录；无静默回退。

`python scripts/run_research_value_benchmark.py --raw-spy-json inputs/spy_chart_2010_2025.json --candidate-count 12 --startup-trials 4 --seeds 17 42 91 --windows 2010-01-01 2013-01-01 2016-01-01 --out validation/benchmark.json`

缺省 `--llm-mode deterministic` 明确是实际规则 Advisor 的工程对照，不是真实LLM。真实对照用 `--llm-mode live --fixture-dir <目录>`；录制后用 `--llm-mode replay --replay-call-map <prompt到call_id映射>`。prompt改变后旧录制不自动适配。

`--memory-mode ablation --memory-store <审核过的固定先验>` 为每组复制独立先验并冻结；cold/warm不得混合成为同一公平四臂结果。输出分别记录唯一配置、已计费fit、成功/失败/重复/无改善实验、逐fold稳定性、真实调用与回放、usage/cost及未知值。wall_seconds 是本次命令耗时；恢复运行不伪造历史停机耗时。人工分钟数未测时为null。search_seed、estimator_seed分开；deterministic重跑和重叠窗口不能增加独立样本量。

六配置空间仅作枚举正确性参照，较大目录仍是受控离散空间；不将TPE离散ID采样包装成任意连续参数优化。旧R5前的greedy/fixture报告保留但不用于真实Agent强弱判断。新版工程验收要求比较对象正确，不要求Agent获胜。


## R6 持久工作区、受控外部特征与交付流程

正式产品入口仍是现有 Streamlit 的 Research Mission 页面。启动前由可信操作者固定 `FFA_WORKSPACE_STATE_DB`（默认 `projects/workspace/runtime.sqlite3`）及可选 `FFA_WORKSPACE_TENANT`。关联项目共用同一权威数据库；不从 URL、上传的模型包或客户备注获取信任数据库路径。不支持多租户 SaaS 身份认证或 OS 级隔离。

模板只接受固定 SPY 日频 next-session return 的中英文名称。备注单列，明确不改变任务/评价/权限。允许特征、起点内置基线配置、预算、选中的至多三条已审核文献/领域证据、录制模式共同冻结在 Campaign 合同；改变它们应开始新 Campaign，不能强行恢复旧执行。

提交过程：持久保存提交意图 → 创建薄 Mission → 既有队列 held task → 写入 Mission/Campaign 引用 → 激活队列。关联完成前任务不能执行；中断后可修复 held 关联并由操作者恢复。查看、切换候选、刷新、打开历史任务及下载均不重新训练。相同表单的重复提交在该会话保持同一 operation ID；有意重复研究须点击“Prepare a new intentional repeat”。新浏览器用已注册 project/campaign ID 恢复，不依赖旧 WebSocket 会话。

工作区显示实际状态、研究结论、预算、基线/候选详情、真实 diff、Feedback、Exposure 和事件。request_review 是持久暂停，可在页面批准/拒绝并恢复；取消与恢复沿用 R2 generation/预算逻辑。ResearchPackage 从权威状态生成，检查被接受的产物哈希与路径；符号链接和篡改拒绝。ModelBundle 必须显式 refit 并写入 R4 包外可信登记；下载文件不授予另一台机器加载信任。

### 最小 BYO 合同

仅接 CSV/Parquet 和内置 Ridge/RF/GBDT 的配置，保留原任务。可附加**一个**已审核 `ext_*` 数值列，注册为 `external_numeric` 特征组，复用相同特征注册/编译/执行/评价/Manifest/模型包路径。审核项包含名称、版本、审核者、来源说明和可选逐行 available_at 列。没有任意代码、动态 import、表达式执行或陌生 pickle 模型加载。

按同一份原始字节解析并哈希；重复 CSV 列、映射碰撞、非数值/非有限值、缺失或多余交易日、周级标签冒充 next-session、无效时间、未来特征及自报 sealed 状态都会拒绝。session 字段用无时区日期，实际时刻另列 timezone-aware `decision_at` / `label_available_at`。没有实测到达时间的情况明确标为收盘假定。

标签有供给价格时复算；最后目标没有 next_adj_close 时明确记为未验证。有 next_adj_close 则核对整段及最后目标。没有原始价格则为 `user_declared_unverified`，不能称系统已核验。特征 availability 时间戳检查只证明提供的时间声明一致，不证明来源无前视泄漏。改变来源备注、CSV/Parquet 格式或 exposure 声明不能清洗同一目标的暴露身份。

模拟输入仍输出 `simulation_only_no_financial_evidence`；真实未知来源不获得独立确认。R4 固定确认接口暂不接自定义外部特征，明确拒绝而非代理执行。

### 验收和下一步

R0–R6 的定向/累计工程证据、精确源码树和运行层级见 `docs/validation/v22r_acceptance.json`、CI、`V2_MISSION_RESEARCH.md` 与补充报告。此前环境的浏览器管理策略阻塞是历史边界；本轮 Windows 正常安装 Chromium 的实际 E2E 已运行两次并通过，没有绕过主机策略，也没有用 AppTest 替代浏览器。

剩余外部证据集中在 `CODEX_V22R_REMAINING_VALIDATION.md`：真实 provider 失败原因与可靠性/研究质量、实际人工时间、真实客户、合法封存金融确认、macOS、Windows 原生 symlink 权限、历史资产/native/GPU。本轮真实 3×3 矩阵已完整尝试但 live 门禁 FAIL，不是没跑；Live→严格离线 Replay、Windows 完整 crash/resume 和浏览器已通过相应补测。整体工程验收 **PARTIAL**，不启动 V3；标签成熟时刻合同不等于已实现前瞻记录生命周期。


### R6 原始提交边界（历史检查点）

R6 正式分支可供本地拉取和继续修复，但浏览器真实 E2E 尚未关闭。已知 CI run `35686627733` 中 Python 3.11/3.13 核心累计回归、Ruff/compile 通过，browser job 失败；失败证据必须保留并由本地 Codex 从当前正式分支继续复现/修复。不能据此宣称 R6 用户工作流已经验收。


## R6 原始正式提交的同 SHA 证据（历史，失败保留）

正式 R6 commit：`3fdd2d6403bc425d172d15eba749bcdc925f33e2`，tree：`4f740f79335a0a25edc78668f0aecdd9d4a5db62`。

- Focused Mission validation run `35691460180`：Python 3.11 **203 passed**（278.22s），Python 3.13 **203 passed**（227.19s），Ruff passed。
- Focused final acceptance run `35691460205`：冻结真实 SPY **4002 rows**、**20 fit calls**、`research_outcome=no_improvement`、`confirmation_status=not_run_historical_data_exposed`，ResearchPackage / ModelBundle smoke 成功。
- Focused browser acceptance run `35691460214`：**FAILED**。当前失败点是候选切换后，Playwright 期望 combobox value 为 `r1_c1_e78a28dd`，实际断言未满足。该失败保留为 R6 工程验收开放项，不能被 AppTest 或核心回归替代。

该历史检查点的产品口径是：**R0～R5 delivered；R6 code committed / validation pending；V3 not started。** 本轮补测的新证据与限制见本文顶部当前表和补充报告。
