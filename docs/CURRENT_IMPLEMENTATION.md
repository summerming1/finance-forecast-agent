# 当前版本功能与技术实现说明

## 2026-09-29 V2.3：C1–C5已交付，C6工程审计完成、最终门禁与外部验证分轴

合并方案及实施批准已提交c60d173、0eda9d3；批准范围见 [V2_3_FEATURE_RESEARCH.md](V2_3_FEATURE_RESEARCH.md) 和accepted [ADR_MISSION_PRODUCT_005.md](ADR_MISSION_PRODUCT_005.md)。C0本地420通过/1项symlink权限失败/2跳过；同c60d173的Linux3.11/3.13核心及两套浏览器CI通过，原冻结输入CI仍BLOCKED_ASSET。

C1现已实现不可变FeatureProgram结构、代码拥有的能力边界、严格候选读取、旧golden hash兼容、DSL确认前置拒绝和原MethodCard可选审核配方字段。新结构测试41通过；相关旧回归141通过/1项既有Windows symlink权限失败；静态通过。01c9812同SHA Linux3.11/3.13核心及两套Chromium CI均成功，原冻结输入仍BLOCKED_ASSET。

C2实现价格-only AST纯计算、严格XNYS原始历史验证和固定W64研究行映射，相关96项通过；手算、因果性、保护除法、溢出、1074行门槛与资源观测另见版本日志。原本地历史输入仅做HTTP=0/fit=0转换，3959行，未替换旧资产验收。33915c6同SHA Linux3.11/3.13及两套浏览器CI通过；下载的3.11 JUnit为472通过、0跳过。

C3已在原Controller/RuntimeDB中接入price_features模式、原始历史/目标行绑定、固定模型的程序动作、整批预检、最多4提案槽和独立规划次数、确定性/Random策略、真实worker/续接及Memory协议/as-of筛选。模型实际训练与Manifest记录AST及列顺序。首次集成104通过、相关旧回归107通过；随后Snapshot别名和恢复fixture校验补修后98项边界通过，收据及各源码阶段见V23日志。当前raw ModelBundle与页面能力见下方C4/C5，不再是C3阶段的尚未开放状态；没有新付费Provider或真实确认/真人验收。

2a21890同SHA Linux3.11/3.13核心与旧Chromium已通过。新工作区CI复现测试同步竞态：结果落库先于Queue退出；仅补测试等待Queue及组件状态，本地真实Chromium1通过/90.55s，生产执行代码未改。修订测试同SHA CI另核对，不能把原失败覆盖成通过。冻结输入仍BLOCKED_ASSET。

C4现已支持显式refit后原始价格ModelBundle v3、新进程一致推理、末行保留和程序/环境/可信登记核验，旧v2保持。受限程序导出降级、完整包fit前权限拒绝、撤销后拒绝加载/下载。失败refit亦计入同RuntimeDB账本，注册与完成同事务。相关94项通过；来源/用时/命令见V23日志。同SHA累计CI另核对，不能代替新模式浏览器或真实文献审核。

C4同69101c7的Linux3.11/3.13核心与新旧Chromium均已通过。C5新增价格公式模式已接原工作区：预算/权限预检、实际AST与差异、原队列、受信包、完整公式续接。固定模型文献能力与模拟来源传递问题已复现并修正；最终相关121项、真实Windows Chromium新旧两流程2项通过。源码/输入hash及计数见V23日志；新模式真人清单在FRONTEND_USER_GUIDE。

C5同2e5e5ed的Linux3.11/3.13核心与两套Chromium已通过。C6现有新协议三臂deterministic历史工程例，3959监督行、80研究fits、HTTP=0；29份聚合及116份fold指标、三个审计包所有成员hash、新Python原始无标签推理逐值一致、末行保留。额外审计refit累计4次，包括一次失败后保留的真实成本。新benchmark继续使用原Controller，旧TPE保留目录语义；新CLI有4槽/28fits有界预注册及执行顺序冻结。24项新旧benchmark回归通过；本地模拟HTTP→严格离线Replay通过，不是付费Live。

最终全仓pytest及C6同SHA CI仍待完成，收据见V23日志§12。工程用户闭环已模拟验证，真实历史例只作development evidence；Live/真人/文献真实语义不由助手模拟关闭。整体验收未完成，原冻结输入缺失、A/L剩余状态、历史科学结果及47目标负确认不改。未来计划不得冒充当前能力。

## Agent 风格前端接入（2026-09-28）

用户已批准将交互原型接到现有项目。默认 `apps/streamlit_app.py` 改为 Agent 风格工作区，使用 Streamlit 自定义组件及 apps/ 薄适配层连接原 workspace API，无独立 API 服务、npm/CDN 或第二套执行/状态系统。研究/实验/成果视图、三步向导、实际预检和队列、候选审阅、真实 refit/ZIP 下载、同 Mission 续接、恢复/审核/取消入口已接线。原研究 package 源码及 a75e72a 的录制恢复修复保持；`?legacy=1` 与 `?lab=1` 保留旧入口。

启动、原状态库配置、动作和范围详见 [AGENT_WORKSPACE_UI.md](AGENT_WORKSPACE_UI.md)。本轮验证使用模拟行情、真实模型训练及真实浏览器/worker，不调用付费LLM或新金融确认，不替代真人使用。发布前候选 `a5562df` 的同SHA CI已核对：新适配与真实浏览器共16项通过、受影响原功能54项通过、Ruff/compile/JS语法通过；具体身份和边界见接入说明。先前未完成浏览器流程的失败保留，后续发布SHA验证另行核对。原冻结资产及完整B5开放边界不因UI接入关闭。

## 唯一当前状态（V2.2-R / B5 增量验证，2026-09-28）

验收缺口分轴保留；后续批次的计划不得冒充实际完成。

### B5 录制硬中断收口

发布8817d68的Linux CI发现新增测试的POSIX子进程回收冲突（8 failed/400 passed），已仅修正测试为由multiprocessing创建者kill/join，Windows原生tree验证保持。最终SHA重验结果见交付收据；该父提交失败不隐藏，也不把Chromium通过等同全部CI通过。

基线6056c3e上真实子进程/本地模拟HTTP复现：缺少可靠响应登记的硬中断恢复会重复请求；HTTP=0的预检权限失败又被错误永久阻断。最小修复复用原HTTP/Advisor账本，在跨进程恢复前拒绝未知响应的自动重发；前置故障独立记录，同路径修复后允许原合同恢复。完整已接受响应/计划继续复用；正常429/503有界重试未改。损坏失败收据不能作为新请求授权。DB不可写可能缺账，绝不承诺任意故障下恰好一次计费。
新证据与原A04/A05/A06/A08/A23/L18关联见 [B5_RECORDING_RECOVERY_20260928.md](validation/B5_RECORDING_RECOVERY_20260928.md) 及原验收JSON新增节。测试均simulation_only，无新付费LLM、资料外发、真实DB写入或确认。旧冻结资产/真人/真实语义缺口保留，整体仍PARTIAL。
收口最终本地累计405 passed/1 Windows symlink权限失败/2 skipped；Chromium1 passed；相关Ruff/compile通过。同发布SHA CI单列，旧6056c3e证据不冒充新源码结果。可以进入受控真人试用，不等于完整B5或V3验收通过。

9月27日独立 Windows 补测保留在 [B05_SUPPLEMENT_20260927.md](validation/B05_SUPPLEMENT_20260927.md)。9月28日增量见 [B5_INCREMENT_20260928.md](validation/B5_INCREMENT_20260928.md)：最终相关累计393 passed/1 symlink权限失败/2 skipped；全仓532 passed/10环境或资产失败/3 skipped（全仓在最后文献提示修复前，之后受影响累计已重跑）。真实 Chromium 通过。用户已审核两条短文献观点及一条引用用途，但不代表真人产品试用通过。整体仍PARTIAL。

正式分支：`feat/mission-research-v2`。B 批次演进基线：`a3c6ec69c9bd14d18b1cdb493795669a9452c800`；本轮独立补测源基线：`5ec8042f7623470646c92953404b65f21abc4f7c`。
批准方向见 ADR_MISSION_PRODUCT_004.md，B0→B5 范围见 PROJECT_ROADMAP.md。计划不是已实现能力。

| 能力轴 | 当前证据 | 开放边界 |
|---|---|---|
| 基础执行与逐行评价 | 既有真实 SPY、Manifest、复算和受控模型训练 | forecast_only，不是交易性能 |
| Live/Replay | 新 kimi-k3 两轮与五组对照完成；普通与 Batch 严格断网 Replay 一致 | 旧缺 statement 失败保留；有限成功不证明长期稳定性 |
| 恢复/审核/动作 | 既有 Windows 全 Campaign 恢复、approve/reject/stop | 受影响修改必须回归，不重称从未测试 |
| 交付/受控 BYO | 既有 CSV/Parquet 审核数值特征、网页和模型交付 | 本地路径不是上传服务；B2 双入口/交付绑定已实现，真实用户未验证 |
| 金融确认 | 一次47目标真实固定留出负确认，原收据保留 | 用户声明+本地审计，非前瞻；不得重挑该窗口 |
| 研究价值 | 新 G2A Random/TPE/One-shot/Adaptive/Batch 五臂均完成，各44 fits；历史 Memory cold/warm 小对照保留 | 单窗口单种子不足证明一般优越性；原失败和完整矩阵缺口保留 |
| 文献 | 新独立 L0/L1 均完成4候选/28 fits/2真实调用；L1严格断网Replay一致 | 两组最佳MAE相同，无额外精度收益证据；旧失败及模型解释矛盾保留 |
| 真人使用 | 工程模拟参与者 | BLOCKED_NO_REAL_USER |

## B 批次状态

| 批次 | 状态 |
|---|---|
| B0 | 已发布 81012ee；文档与批准合同同步，原240项回归和文档门禁收据保留 |
| B1 | 已实现分类错误、硬调用时限、HTTP/时间账本、等待提供者与同决策恢复；定向14项、相关累计254项通过；真实服务/Windows补测单列 |
| B2 | 已发布49a486a；267项双Python与Chromium通过，源码树与发布一致；外部用户未验证 |
| B3 | 已发布257ed0f；精确树b825b6f的304项双Python累计回归和Chromium通过，正式同SHA三套CI通过；初始失败收据不覆盖 |
| B4 | 已发布e983c4d；精确源码双Python324项与Chromium通过，正式同SHA核心/浏览器通过；真实SPY远端因旧输入产物缺失FAIL，不能报全CI绿 |
| B5 | 已发布4c5aba9；发布前335项双Python累计回归与Chromium通过，含五臂/显式文献成对工程集成和统一补测；后续文档回归与最终同SHA CI单列，20条开放/部分条款不冒充通过 |

## 原能力、证据与兼容

原 R0–R6 报告：[V22R_R0_R6_REPORT_20260923.md](validation/V22R_R0_R6_REPORT_20260923.md)。原长程矩阵和补测：[V22R_SUPPLEMENT_20260923.md](validation/V22R_SUPPLEMENT_20260923.md)。历史变更见 V2_MISSION_RESEARCH.md；数值结果/失败不能因新版本重写。

单机可信操作者，沿用 RuntimeDB/LocalTaskQueue/Controller/Evaluator/Memory/MethodCard。JSON 是投影而非第二套状态。相关项目必须复用原受控数据库；空库不代表数据未曝光。升级前完成或取消旧运行，跨代码/数据/环境/调用政策的合同不强行恢复。

现有 CLI：`scripts/run_focused_spy_campaign.py`；现有网页：`apps/streamlit_app.py` 下 Research Mission。双入口已发布；文献工程代码已通过B3精确源码树验收，真实服务与文献贡献单列。

ModelBundle 通过平台显式 refit、包外可信登记后加载；复制包不自动迁移信任。独立确认只从固定授权加载登记数据，消费后不可重试挑分数。新研究不能继承确认指标作开发反馈。

## 当前边界

SPY、日频、下一 XNYS session 调整收盘收益回归、MAE、forecast_only。一个审核数值特征和内置模型配置，不执行任意 Python/notebook/pickle/Docker。不扩大任务、模型结构或自动交易，不启动 V3。

Windows symlink 权限仍 BLOCKED_ENV；macOS/GPU 按用户范围不测；原论文小时级训练不因本轮客户端改动重跑。旧资产/PDF 环境失败与后来补测均保留，focused 通过不等于全仓科学通过。

## B1 当前调用边界

客户端在单一 killable HTTP 子进程中执行非流式 JSON 请求；连接/读取空闲和逻辑调用总deadline分别冻结。额度/权限等永久错误不盲重试；429/暂时服务错误有界退避；不自动切换模型或付费。使用既有 RuntimeDB 记录每次 HTTP 请求，崩溃未观测区间保守保留预留；费用未知为 null。

`waiting_provider` 不代表科学无改善；同合同显式恢复使用冻结提示词和已接受实验。完整已录制响应在冻结计划前中断，可直接读取原始不可变记录，无新请求。新代码/时限合同不得强行恢复旧运行。

已实现 Campaign HTTP 请求数和累计提供者活动秒数上限；模型训练仍以 fit 上限限制，不宣称硬保证整个 Campaign 的墙钟时限或精确人民币费用。预检不查询账户余额、不产生网络请求；显式 probe 仍属于一次可收费调用。SSE/供应商结构化输出未实现；本轮有限真实Live补测见上表，不等于全面可靠性验收。

## B2 使用与兼容

默认 `entry_mode=goal` 不要求模型/论文，只允许选择受支持模板，必须有合法数据。`provided_start` 接受内置模型配置；旧字段 `starting_baseline` 作为输入兼容名，现在是独立用户起点，不替换固定三模型与朴素对照。若执行指纹相同复用固定对照，不同则额外预检并计入 folds 次训练。旧运行合同不强制迁移。

`change_scope=features_only` 在编译和执行前都锁定实际起点的模型、有效参数、seed与匹配父模型，仅允许审核特征组变化；普通探索仍走原能力白名单。结果分别保存 incumbent、fixed controls和research candidates，无改善不扩大为无信号。

网页用模板、起点参数与数据合同表单；高级JSON仍是显式选择，不双写权威。当前候选是详情、显式refit、下载的唯一来源。refit和candidate关系存在既有RuntimeDB，刷新可读；下载验证原包外注册与相同字节，不反序列化。交付refit单列1次训练，不冒充研究预算中的一次候选。私有数据、真实Live与真人试用未由工程测试证明。

B2 草稿合同使用稳定控件标识；切换输入路径不能覆盖已编辑的来源、模拟标记或特征。表单/高级JSON要求明确来源与provenance，非法对象阻断，不通过默认值静默运行。

## B3 使用与权限

平台提供冻结内置基线；文献只作为研究依据，不能改label/split/预算/固定模型约束。`scripts/review_focused_literature.py` 是可信本地操作者的显式审核入口，复用 `method_card_versions` 与 `review_state/methodcard_approvals.json`。审核具体来源字节、卡版本、claim和用途；无数值结果的理论资料可作研究用途，strict gate保持不变。PDF语义忠实性仍是操作者审核，不由哈希证明。

Controller接受 `literature_project`、最多3个 `literature_review_ids`；原自由JSON不再能自报paper_claim。任务/能力不匹配保留限制说明，不假装实现。每次live规划检查实际来源与当前授权，每次HTTP重试/取消检查刷新权限。provider需在审核audience中显式允许；撤销后不能继续发送。新版本不可替换旧快照。

论文被引用时必须给出literature_uses（角色/迁移差异/理由），与实际candidate/config diff/feedback关联。规则控制不解释论文、不装饰性引用；未使用不等于资料无效。compact_v1按固定规则去掉重复文本，保留全实验状态、数值与反例，超限先阻断，不悄悄裁剪。首次建库/人工审核费用未实测，仍未知。

新增adaptive_batch，旧adaptive单步不替换。G2A共享实验合同、分别保存策略服务合同；L0/L1显式文献对照单列G2B，不称无文献模型没有预训练知识。只有完成臂进入成对误差表，失败、费用和best-so-far仍保留。不宣称当前规则/回放测试证明真实Agent或文献收益。

受限文献不自动导出原文或衍生叙述：ResearchPackage转为reference_only，保留数字预测和受控manifest字段、来源哈希及省略清单；完整本地审计不删除。跨机信任迁移、多用户OS隔离和许可审核仍非本轮已解决能力。

B3 初始检查点的292/2失败保存在历史日志；关闭收据见257ed0f及验证Run35975040348，不再描述为未发布。最终retry测试与严格deadline测试分离；无文献浏览器路径明确展开方法依据。

## B4 使用与边界

只读 `workspace_research_summary` 从原RuntimeDB/逐实验事实投影状态、控制/用户起点、实际修改、fold、文献原观点/本地迁移/实际反馈。等待提供者、未完成研究、仅基线和开发无改善分别显示。金额、人工时间和文献准备费用没有实测时仍为null；不合成研究评分，不推断因果、独立确认或收益。

`continue_workspace_campaign` 是用户显式启动的**新Campaign**，沿用同一Mission、项目和状态库，冻结父candidate、已接受结果、final与合同哈希。双击同operation保持幂等；实际worker再次核验。仅支持同一冻结数据、可训练估计器起点；数据变化请新建明确研究，replay续接需另行准备新映射。原结果不改、不复制预测；新fit独立计费，谱系费用只展示不重扣。技术恢复仍使用原resume接口。新研究不重置曝光/信任历史，旧确认分数不进入开发。

`preflight_confirmation` 只检查模型/特征/协议/环境能力，不读数据或确认标签，不建库/授权。它不是eligible结论。创建授权先做此预检，再核验注册数据、时间和独立资格。未来固定留出支持zero/train_mean/train_median作对照，仍复用原train-only数值实现；mean/median仅用授权训练标签，统计计算独立记账，不冒充estimator.fit。朴素对照不因此变成可导出模型；审核自定义特征确认仍不支持。原47行负确认/一次性消费边界保持不变。

主页给出任务入口，高级论文工作台保留在`?lab=1`与原模块；ResearchPackage包括可分发总结。受限文献仍采用reference_only，不自动导出派生叙述、原文或私有路径。旧合同不改hash强行恢复。PDF旧fixture环境在constraints/pdf-legacy-validation.txt显式选择，本机未安装该版本不能报strict解析验收成功。

## B5 验收与交接

`tests/test_focused_b5_acceptance.py`在原Controller/Optuna上执行五臂和独立L0/L1工程集成，不建立另一套runner/数值评价。两组规则策略未调用真实LLM，Synthetic来源不代表文献理解；增量标志保持false。

`verify_frozen_spy_acceptance.py`核验原始输入hash、逐行复算MAE/RMSE/方向准确率、包索引与每个文件hash、显式refit及新进程无标签接口；零预测按既有指标的>=0定义，不改原评价器。费用与外部科学证据不由该脚本升级。输出目录/收据不可覆盖；失败仍非零退出。

冻结SPY同SHA远端验收的旧7天产物已不可用：B4 run36291075239在下载处FAIL，未训练。B5支持显式指定冻结输入run或repo变量并固定核验原hash；不自动拉新行情，缺资产继续fail closed并保存BLOCKED_ASSET。当前容器已恢复原始合法副本并在B4运行4002行/20 fits/8预测复算/27文件hash/1次refit/8行新进程接口通过，但这不替代远端资产恢复。

补测唯一入口：`CODEX_V22R_REMAINING_VALIDATION.md`。48条A/L按实际自动化覆盖、语义/平台/真人边界分别标记，未闭合ID保存在JSON；不是全部PASS。B5最初发布时没有新增付费provider；后续9月27日真实Live补测见顶部及独立报告，不能与发布前状态混淆。完整45臂、真人产品试用和新金融确认未由该补测完成；整体证据仍PARTIAL，V3仍未启动。

### 2026-09-28 增量

共用提案提示明确每个动作必填非空statement；编译器准入不放宽。候选来源与开发门槛独立，部分失败不再显示completed终态。真实调用前预检记录路径；响应后写入失败拒绝计划，并在原RuntimeDB保留可观察用量和禁止同决策重发标记。DB本身不可写仍可能缺账，不承诺恰好一次计费。旧结果只读；旧Replay需匹配源码/环境/提示，包内任一Python源码变化都可能改变执行身份，不强行恢复旧合同。定向工程负例已通过，累计及真实外部边界另列，非全部验收。

只读比较从已接受Manifest核对任务、数据、切分、实际目标行和评价政策，再展示各参照的MAE与分折差值；不重新评价训练。续接预览展示继承范围及新增预算，明确新ID在提交时生成。现有项目请求可作为输入选择，快速试跑按原fold与配置身份计费；不会自动启用Live。任务匹配资料只按task_id过滤取最多3条。新源码累计393 passed/1 Windows symlink权限失败/2 skipped，真实Chromium1 passed；用户起点角色和可比性均有负例。同SHA CI另列。真实用户尚未完成操作反馈，整体仍PARTIAL。

文献提示明确既有 literature_uses 与 evidence_refs 绑定及条件必填字段；validator 未改变，缺引用仍拒绝。普通无文献提示保持原合同。真实响应模型名记录为 response_model，供应商别名未解析不能宣称固定权重。
