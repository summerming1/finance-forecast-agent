# V2.3 受控价格特征研究：合并修改、测试与产品迭代方案

日期：2026-09-30。状态：**V2.3功能已实现；复核发现四项合同缺口，正在分批修复与回归，工程收口暂为PARTIAL。9月29日通过记录保留为历史证据；Live、真实语义与真人未完成。功能状态以CURRENT_IMPLEMENTATION为准**。

本文件合并原产品方案、R1–R10对抗审查、S1–S7复核及最终三项澄清，是本里程碑唯一详细规范和后续增量日志。验收矩阵保留完整计划；实际分批证据只见§12，不能把局部通过写成整个条款完成。

审阅基线：`feat/mission-research-v2`，HEAD `fad63bc8effc6bd3a8e98f7ad94b9896a599c321`，tree `8df2d8bde98d2c943b6b5d18cbb97bf73c5cf933`。实施时重新核对实际HEAD；不reset回此基线。

范围见已接受的 [ADR_MISSION_PRODUCT_005.md](ADR_MISSION_PRODUCT_005.md)。用户已批准功能实现、测试、必要前端修改及验证后普通推送/同SHA CI；付费LLM另需模型/预算授权，不授权真实确认、未许可资料外发或V3。实际能力只见 [CURRENT_IMPLEMENTATION.md](CURRENT_IMPLEMENTATION.md)；旧开放项仍见 [CODEX_V22R_REMAINING_VALIDATION.md](CODEX_V22R_REMAINING_VALIDATION.md)。

## 1. 产品目标与最小范围

让Agent在批准的语法内提出固定菜单外的新价格特征，由原确定性链路校验和训练，留下真实diff/反馈/失败，并交付能从无标签原始历史推理的模型。不是任意算法研发，也不保证精度改善或盈利。

| 纳入首版 | 明确不纳入 |
|---|---|
| SPY、daily、下一XNYS session调整收盘收益回归、MAE、forecast_only | 新资产/频率/分类任务、交易与自动晋升 |
| 目标/已有起点双入口；新增明确的构造特征模式 | 第二个工作区、通用聊天到任意任务 |
| 原Ridge/RF/GBDT；新模式锁模型、有效参数、seed、训练规则和预处理 | 模型/特征联合自由搜索、自动换模型 |
| 价格内置组base_lags/momentum/volatility；最多2条生成特征含继承 | 新模式liquidity、ext_*及任意用户代码；旧模式继续原能力 |
| 一至两条审核配方；至少一条文献迁移语义需人工核对 | 为凑数量编造论文机制、自动检索/代码生成、strict复现声明 |
| 原恢复、动作、Memory、ResearchPackage、显式refit和ModelBundle | 新队列/数据库/评价器/Memory/方法库 |
| 工程预览、授权Live小试验、真人形成性试用分轴 | 以模拟用户代真人、以开发成绩代独立确认 |

若没有可用的文献配方，可以先用明确标注的工程假设跑工程闭环；文献语义门禁保持BLOCKED，不把理论限制文章强改成可执行特征。

现有工作区可先让产品所有者真实走查。所有者本人操作不是simulation，但不等于独立目标用户验证；新DSL界面的可用性仍需新版本再测。

## 2. 合同、身份与兼容

### 2.1 一份候选执行配置

扩展原CandidateConfig，引用版本化不可变FeatureProgram。TaskSpec/CampaignSpec仍拥有任务/数据/切分/预算；MethodCard只拥有版本化来源和配方；结果留在Manifest/PredictionArtifact/Feedback。不要再建另一份可变ResearchProgram复制上述内容。

保持三层身份：configuration identity不含estimator seed；execution identity包含seed及影响执行的输入/协议/预处理/程序/环境；研究事件身份包含假设、引用和尝试。引用变化不创造新数值实验，但不覆盖旧叙述或权限事实。

新执行绑定raw内容及revision、共同目标行、内置配方版本、AST、实际列顺序、编译器实现/环境、有效模型参数和训练行。只规范JSON键顺序及已定义默认值，不重排浮点代数，不因当前输出碰巧相同合并程序。

首版缓存复用仅限当前Campaign已接受结果。各benchmark arm不共享搜索结果；跨Campaign显示旧记录不是免费复用新实验。续接的新fit独立计费。

### 2.2 旧格式允许，新语义不能静默降级

当前旧CandidateConfig没有独立schema字段。严格符合已知旧格式、没有新语义字段的对象继续按原规则读取，保留历史序列化/hash；合法派生身份字段按旧约定验证。不要要求所有历史候选补版本或重新序列化。

含FeatureProgram等新语义字段必须有明确新schema/domain。未知schema、缺新版本、伪装旧格式、字段被过滤均拒绝，不允许“取已知字段”后当旧模型运行。新dataclass默认字段也不能改变旧对象身份。旧二进制不承诺可安全读取新包。

新schema上线的同一增量就建立DSL确认拒绝：UI、CLI、直接API、grant创建/执行、refit后确认等全部在确认标签读取/建授权/确认fit前拒绝。不能只隐藏按钮。

### 2.3 能力来源不是hash本身

能力来自当前程序实现且批准的集合，调用方只能引用或在创建Campaign时收窄；不能自报更深AST/新算子再重算hash取得权限。能力、共同样本和预算在任何研究结果及Provider请求之前冻结，批间不得扩大或改写。

request_review的批准只继续原合同内的暂停；不支持能力只记录需求/原因，不能通过approve解锁。新能力需开发、批准与新合同。

## 3. 特征程序与数据协议

### 3.1 首版拟冻结语法

FeatureProgram是JSON数据，不是代码字符串。以下为首版工程政策，不是文献最优结论；C1/C2先用边界算例核对后固定版本，不能看研究成绩再调规则。

| 项目 | 约定 |
|---|---|
| 终结符 | 仅当期已可见的return_1；从调整收盘P生成r_t=P_t/P_(t-1)-1。原始P仅是依赖推导基元，不自动成为可搜索终结符 |
| 算子 | lag、rolling_mean、rolling_std、add、subtract、multiply、abs、safe_divide |
| 参数域 | rolling窗口2/5/10/20/60；lag位移1/2/5/10/20；整数不接受bool；无任意常数/字符串表达式 |
| 复杂度 | 每表达式最多16节点、深度4（叶节点深度1）；每候选最多2条生成特征，含父继承 |
| rolling | 右对齐、含t，窗口[t-w+1,t]，min_periods=w，std ddof=1；不居中、不负lag |
| safe_divide | 有限输入下abs(den)<1e-8输出0，否则num/den；等于阈值不保护；记录触发次数 |
| 数值 | float64；合法预热缺值与数据缺损区别处理；有效依赖范围内任何中间NaN/Inf/溢出均拒绝，不能用保护除法遮盖 |
| 预处理 | 原Ridge的StandardScaler仅训练fold fit；树模型沿用原实现；不增加可搜索填补/标准化/winsorize |
| 权限 | 无文件路径/import/eval/网络/循环/系统调用；只消费受控适配器数组 |

JSON解析前检查字节上限，解析后检查重复键/未知字段、节点/深度/类型，再分配数组。必须设最大raw行数和计算内存上限；C1定义这些不可省略的capability字段，C2在纯函数边界测试中确定具体上限并冻结版本，任一未设限不能进入C3实际研究或发布。不要把上述限制宣称为多租户OS隔离或整个Campaign的硬墙钟保证。

建议AST结构：input用`op/name`，lag和rolling用`op/arg/periods或window`，abs用`op/arg`，二元用`op/left/right`；精确schema在C1冻结，不允许同一语义存在未定义的另一种解析入口。输出按冻结的内置列顺序及生成列顺序构建，禁止与原列重名或重复ID。

### 3.2 共同预热W与实际回看L

依赖递推：L(P)=0；L(return_1)=1；L(lag(x,k))=L(x)+k；L(rolling(x,w))=L(x)+w-1；abs不增；二元取max。最大L<=64。

新协议建议ID `feature_research_dev_v1`：所有固定对照、起点和候选统一W=64，不随实际公式缩短。特定包的L_bundle取全部内置特征和AST的最大依赖，推理至少需要L_bundle+1个完整有效价格session。rolling_mean(return_1,60)需要61个点；再lag5导致L=65，应拒绝。

当前切分最少1009个监督样本：756+1+4×63。若raw完整、丢前64行、最后1行label未成熟，最少1074行raw。1073/1074是该假设下的边界，不是全项目魔数；旧模式仍按旧规则。缺session/时点不合格不能靠数量满足放行。

冻结raw→监督行→训练/评价目标行映射。所有模型都用新协议共同样本重新运行；旧4002行结果只作历史展示，不直接减分数宣布提升。新语义协议不重置原raw/targets曝光。

### 3.3 输入与时点

需要session、合法调整收盘序列、来源revision/hash、来源/时点声明；严格XNYS顺序、完整性、唯一性、有限正价格。不能以close替代缺失adj_close。不向AST暴露label、时间戳或任意外部列。

无标签推理单独验证输入，不经过删除末行标签的监督清洗入口；最后可预测行必须保留。实际训练与推理共用特征构造器。未来扰动/截断前缀不改变过去特征只证明计算因果，不能证明Yahoo历史复权数据是point-in-time，也不能补造到达时间。

## 4. 动作、规划、预算与恢复

### 4.1 固定起点与真实动作

目标入口使用版本固定的Ridge起点，不从本次结果事后挑最好模型免费作为默认。已有起点可用原受支持估计器；依赖liquidity/ext_*时新模式预检拒绝，不能偷偷丢列。原内置组在一个新模式Campaign中固定，Agent只改生成特征。

improve可增/换生成特征；ablate从实际已接受父配置只删一条声明的生成特征；simplify保持模型/seed并严格降低已定义节点/深度或特征数；diagnose复用已有确定性残差/fold/时期诊断；stop保存原因；request_review为合同内暂停。消融回到已有起点时可复用同Campaign结果，但标记复用，不能宣称新增训练证据。

父候选的全部生成特征在续接中继承并计入2条上限。新Campaign不得只带模型参数。One-shot或同批未训练成员不能被引用为已完成parent/control/feedback；产品消融闭环可由后续Adaptive规划基于已接受父结果完成，不强迫每个One-shot计划包含这种跨批证据。

### 4.2 规划单元与执行单元

- One-shot：一次逻辑生成规划最多4个提案，整份计划冻结；按最多2个候选的执行单元处理，不读中间feedback重新规划。
- Adaptive Batch：最多两次逻辑生成，每次最多2个提案；下一次使用真实已接受反馈及实际剩余预算。
- Random：同样最多4个规划槽、相同合法语法/复杂度/模型/样本；无Provider调用。采样器边界见第7节。

首版不自动生成式修正，不保留原稿“8槽/4次含修正”预设。请求更少、提前stop允许少用，不要求凑满候选。

整个规划单元先做schema、来源权限、引用/固定模型、静态AST、预算及可在训练前完成的特征可计算性检查；失败则该单元0候选fit。进入训练后逐候选记账，允许A完成、B运行失败；A与费用不回滚。所有权限在实际动作发生前仍按原机制复查。

### 4.3 计数政策（新协议；不倒改旧账本）

| 事件 | 提案/规划计数 | fit与调用处理 |
|---|---|---|
| 准备一个规划决定 | 在原RuntimeDB绑定decision/prompt及本次槽位额度；总最多4，One-shot最多1个生成决定，Adaptive最多2个 | 必须先持久预留再HTTP；现有调用尝试事件继续保留 |
| 合法普通提案 | 每个占1槽 | 去重后、实际执行前按原策略预留fold fits |
| 合法短响应 | 消耗实际提案数，未用额度明确结算；仍受总槽位及规划次数上限 | 不为补满结果追加调用 |
| 重复候选 | 占1槽，skipped_duplicate；不连带否定其他合法项 | 0新fit，不补发 |
| stop/request_review | 单独响应，占1槽及该次生成决定；不能混在训练批 | 0候选fit，已发生HTTP照记；批准不赠新轮次 |
| diagnose | 占1槽及所在生成决定的额度 | 原确定性诊断，0候选fit；不能强制创建dummy模型 |
| 无效/不可解析/超量响应 | 消耗该决定预留额度，记录proposal_invalid并终止规划；超量不能突破总上限 | 不训练合法子集；实际请求/usage保留，不再生成修正 |
| 同Campaign重读已记录决定/恢复/批准 | 不重复扣该决定槽位，不重新问模型 | 已接受候选不重训，原费用不退 |
| HTTP=0前置故障修复后恢复 | 仍为同一冻结决定/额度，不重新获得提案机会 | 保留原预留及失败事件，实际内部调用尝试照记；不能把未发生HTTP算已付费响应丢失 |
| 新的独立Replay验证运行 | 重现规划的逻辑计数；不能把原成本归零 | 实际HTTP=0；本次训练独立记账，历史Provider费用作为引用不重复收费 |

规划决定数量与既有`advisor_call_reservations`/HTTP尝试不是同一指标：C3必须显式映射，不能直接把现有max_advisor_calls=1当作One-shot所有恢复情形的正确实现。预检失败重入可有内部调用尝试，但不能产生第二份新答案；无响应/投递未知时仍按下面的阻断政策。不回退已有预留计数、不覆盖事件，也不隐藏恢复尝试。

标准训练上限按原fit预检计算：3固定估计器×4fold=12，加最多4候选×4=16，独特用户起点再加4，最多32；相同执行的起点复用，朴素统计单列。已失败/孤儿attempt继续占预算，可能无法跑满4候选。显式交付refit另列1次并授权，不能挤进隐含免费操作。配方若直接启动一个额外研究候选，也占4槽之一；若用户显式选它作为起点则按起点角色计费，不能两种角色反复免费切换。

Live pilot建议每臂HTTP上限8、累计Provider活动秒1200；每次超时、重试次数、token上限、实际模型等在调用前单独批准并冻结，不是本文件授予费用权限。One-shot一次逻辑生成可包含已授权的有界瞬态HTTP重试，不宣称只发生一次真实计费。未知金额为null；不保证总墙钟或固定人民币费用。

### 4.4 必须区分的失败与恢复

| 情况 | 结果与恢复 |
|---|---|
| 已可靠保存但不合法的模型提案 | proposal_invalid终止规划；已有结果可看/导出；重复resume不新问模型，不当no_improvement |
| HTTP=0临时路径权限等前置失败 | 同路径/同合同修复后按原机制恢复；改fixture根目录/源码等合同字段需新运行或原环境路径 |
| HTTP已发生、未可靠登记响应/未知投递 | 阻断跨进程自动重发，保留预留与未知费用；不训练未接受计划 |
| 损坏JSON/hash不符/记录缺失 | 明确拒绝，不删除坏记录后重新请求 |
| 完整响应或计划已可靠接受 | 校验原schema/prompt/call-ID/合同复用，已接受baseline/A不重训 |
| A已接受，B运行期原生错误或硬中断 | 按原attempt/恢复机制保留部分完成、失败和预留；新retry另记真实计算，不免费 |
| 已知暂时429/503 | 保留原批准的有界HTTP重试，不把跨进程未知响应阻断误扩为禁止所有重试 |
| DB也不可写 | 尽可能保留证据缺口并阻断，不承诺任意故障完整留账或exactly-once |

源码/语义变化需新版本运行，保留parent/曝光/历史费用；不得改旧hash。真实测试用隔离simulation库，不破坏用户RuntimeDB。

## 5. 文献、Memory与交付

MethodCard配方绑定source/card/review版本、原观点位置、用途/audience/导出条件、机制/输入/时点/适配器/模板及迁移差异。兼容后才展示，不以论文分数动态推荐默认模型。无资料可研究，理论限制可作依据但不伪造公式来源。

在选择配方/起点时提前显示三项能力：本地可执行、审计包可导出、完整可重现模型包可导出。哈希只可核对，不能替代不能分发的程序内容；受限材料仍按原权限降级，不能通过完整新进程推理门禁。演示端到端使用权限足够的材料。来源语义人工核对，不由hash证明。

复用ExperimentMemory，保留hypothesis、实际config/diff、结果/反证、来源实验及条件；兼容筛选加protocol/program/capability/compiler/as-of。旧记录时点未知保持未知，不补造；确认结果、其它租户或未来证据不入prompt。事实、解释分字段即可，不拆四个存储。

ResearchPackage可保存失败/取消的审计事实，受限projection明确省略内容与不可独立复现。ModelBundle必须完成显式refit，包含实际内置特征配方+AST+列顺序+拟合预处理/模型+raw输入合同+L_bundle+数据revision/训练cutoff/环境。无标签新进程输出与同一refit参考一致，不与旧fold模型要求相等。

包外原可信注册在反序列化前核验模型/AST/metadata/路径/tenant/环境。下载不迁移信任；不复制SQLite冒充跨机可信。不注册半训练包；改字段不变hash仍拒绝。

## 6. 工作包与代码落点

以下是批准的工作包与出口，不是全体已通过的声明；实际实现与收据见§12。每批：复现/负例→最小修改→定向→相关累计→静态→涉及的worker/browser→记录→获准时提交；前一批相关安全/正确性红灯不越过。

| 批次 | 修改位置（相对仓库） | 出口 |
|---|---|---|
| C0 | 本规范、ADR005、AGENTS、路线/验收/交接入口 | 明确实施批准；核对实际base/head/tree、旧A/L依赖、运行中任务、数据资格、费用权限；不把文档齐全当工程PASS |
| C1 | src/finance_forecast_agent/focused_research.py、focused_protocol.py、focused_identity.py、focused_delivery.py；原MethodCard/focused_literature.py | schema/能力来源、旧golden身份、新字段不降级；DSL确认0读标签/0grant/0fit；精确AST与预算字段定义 |
| C2 | 新纯函数focused_feature_program.py及focused_data.py | 手算算例/前缀/数值/资源边界；raw到同一矩阵/样本；不持有运行状态 |
| C3 | focused_research.py、focused_runtime.py、focused_evidence.py、原Advisor；research_mission.py、focused_persistence.py、scripts/run_focused_spy_campaign.py、experiment_memory.py | 提交/worker/冻结计划/预算/动作/Memory/续接均携带程序；本地模拟HTTP和真实子进程恢复；旧generation不能覆盖 |
| C4 | focused_delivery.py、原persistence/mission接口 | 新包可信登记、无标签原始推理、新进程一致；权限投影；旧包及旧确认回归 |
| C5 | apps/workspace_ui_service.py、workspace_ui.py、workspace_frontend/forms.js/views.js/actions.js/core.js、focused_summary.py | 原双入口/三步向导增模式和能力提示；显示真实公式/diff/成本；两个训练候选切换、刷新、新context、导出及续接 |
| C6a | 原benchmark/验收脚本/CI | 原真实历史数据新合同deterministic工程例、指标独立复算、相关核心与真实浏览器及同SHA CI；工程预览结论 |
| C6b | 原BenchmarkAdvisor和runner的小扩展 | 授权Live→record→严格离线Replay；Random/One-shot/Adaptive Batch预注册小试验；不重跑整套旧付费G2A/G2B |
| C6c | 原真人清单/收据 | 真实参与者完成、理解、导出再使用；所有者与独立用户分层；不由助手代填 |

C0文档准备已提交，实施授权已取得，当前进行环境/旧门禁基线核验。C1/C2资源数字和预算映射未冻结不能进入C3真实研究；无需先恢复无关native资产才能写纯函数，但适用门禁不能无证据豁免。

C0基线已核对；C1–C5实现及C6新增证据见§12。下表保留完整验收目标；Live、真实语义与真人不能因工程测试提前完成。

## 7. 研究价值、Live与真人计划

### 7.1 三臂pilot

一个预注册开发窗口×一个search seed，Random、One-shot、Adaptive Batch；相同raw/样本/模型/训练seed/协议/能力/最多4槽/fit规则，Memory cold。LLM臂固定同一Provider、模型和策略服务政策；Random无Provider是设计差异，费用单列。不是一次普遍优越性证明。

冻结grammar、终结符/参数域、合法性、Random采样器版本/分布/seed/去重/max_sampler_draws，不枚举全部AST。若Random只覆盖子集，全部臂限同子集或明确降级不同空间系统对照。每次抽样无需覆盖全部合法程序；不挑有利目录、不换seed求赢家。TPE旧目录只保留回归，不冒充新DSL同空间TPE。

所有预注册运行都入清单：规划/有效/唯一/重复/失败数量、已耗/预留fits、状态、LLM逻辑决定和实际HTTP、usage、费用、墙钟、人时。无有效候选标无结果，MAE不填0，不用起点成绩冒充新候选。失败臂的best-so-far明确部分证据，不进入只含完成且可比预测的胜负表。

One-shot四项整体预检与Adaptive每次两项的失败暴露不同；报告有效率和产品行为差异，不能全部归因于自适应更聪明。执行顺序预先随机化/交错；不为某臂失败免费补跑。不要求Agent赢、不把重复seed/重叠窗口当独立金融样本；披露LLM预训练历史知识限制。

独立Live录制必须保留实际请求/返回模型标识、prompt/hash/call-ID/response hash/候选/结果；新进程移除凭证并阻断Provider和网络验证Replay，不能deterministic fallback。缺授权/凭证/记录分别BLOCKED，不造Live收据。

### 7.2 文献和Memory另轴

新显式文献L0/L1只在提出具体价值问题且单独批准预算时运行，同配方/能力/起点/模型/冷Memory，唯一差异是可见文献。若配方也不同，标整体系统对照。Memory cold/warm另用冻结snapshot，不与文献同时变化。旧有效G2A/G2B保留原SHA，不借新功能重跑全部收费矩阵。

### 7.3 真人与产品推进

先产品所有者走查当前版本；工程预览可用后招募真实目标研究者。建议3–5位覆盖两入口，记录主动操作分钟、帮助/代操作、结果理解、正确导出及实际再次使用。拟议推进门槛：至少3位中2位无需工程师改代码完成且导出；参与者能解释开发不等于盈利/确认；至少2位约两周内自愿再次研究。它是形成性决策规则，不是统计市场验证。

仅1–2人、尚未发生回访则PARTIAL/NOT_RUN；无参与者BLOCKED_NO_REAL_USER。所有者真人记录单列，助手模拟仅simulation_only。不得把未知人时记0或以“愿意用”代实际复用。若既无精度增量，也不减少劳动/改善判断/排除错误，产品价值假设不受支持，先改流程而不是扩平台。

## 8. 验收目标矩阵（实际证据与剩余边界见§12）

使用V23命名空间，避免与原A/L/R编号相撞；以下T01–T34对应原方案，X01–X21合并两轮补充。编号不是新测试框架。后续每条映射实际nodeid/步骤，旧48条JSON不因本表自动改变。

| ID | 必测场景/期望 |
|---|---|
| V23-T01 | 旧对象身份不变；新schema/任务越权字段拒绝 |
| V23-T02 | 引用不制造新执行，AST/seed/compiler/data实变身份；事件分别保留 |
| V23-T03 | MethodCard来源/版本/撤权/适配器不符拒绝或只作研究依据 |
| V23-T04 | 目标/起点/无文献/理论限制双入口一致，不伪造实现 |
| V23-T05 | 负lag/中心窗/未知op/深度/类型越界编译拒绝、0候选fit |
| V23-T06 | label别名/路径/import/网络/时间戳不可作为AST输入或执行 |
| V23-T07 | 独立手算mean/std/ddof/累计lag，与冻结容差一致 |
| V23-T08 | 未来扰动/前缀/晚到数据；计算因果不升级PIT声明 |
| V23-T09 | 改测试极值不改scaler训练统计，训练推理同变换 |
| V23-T10 | 长短AST共同行，原始历史不足/缺session预检阻断 |
| V23-T11 | epsilon正负边界、极值、NaN/Inf中间值、warm-up掩码正确 |
| V23-T12 | 困难日产生非法值必须拒绝，不能删行或另切分 |
| V23-T13 | 实际AST/输入/列顺序与Manifest一致，旧缓存不能误命中 |
| V23-T14 | 偶然同输出不证明未执行；非退化算例发现错误编译 |
| V23-T15 | 固定模型不能改alpha/seed；消融仅声明组件改变 |
| V23-T16 | baseline/起点/候选预算预检；提案/fit/refit分开 |
| V23-T17 | 无效/重复/timeout/硬中断不清成本、不自动补答案 |
| V23-T18 | 换路径/供应商/任务不重置原targets暴露 |
| V23-T19 | Memory/资料权限、tenant、确认结果、未来证据不可泄漏 |
| V23-T20 | DSL确认各入口0标签读取/0grant/0fit，旧能力回归 |
| V23-T21 | 同机新进程无label raw推理最后可预测行，与同一refit一致 |
| V23-T22 | AST/模型/metadata/trusted/path/symlink/tenant/environment篡改在反序列化前拒绝 |
| V23-T23 | 换候选/刷新/旧包/取消导出，审计包与完整模型包分开 |
| V23-T24 | 文献提示注入不能改权限/指标/资料外发；撤销有效 |
| V23-T25 | 下一批真实反馈；局部负结果不写成全局事实 |
| V23-T26 | 模拟/历史修订/unsupported/未知费用，UI与包说明一致 |
| V23-T27 | 保存逐行预测独立复算MAE/RMSE/方向/folds，精确行映射 |
| V23-T28 | 真实浏览器两入口/队列/候选切换/审核/恢复/下载/续接，不隐式训练 |
| V23-T29 | 不同搜索能力/样本/预算拒绝强比较；旧五臂回归 |
| V23-T30 | 真实pilot无改善/提前stop/失败全部保留，不补跑求赢家 |
| V23-T31 | 配方准备/审核/用户主动操作成本单列，未知非0 |
| V23-T32 | 正确ID但误引/解释与AST矛盾人工拒绝，结构通过非语义通过 |
| V23-T33 | 真人理解、完成、导出、再次使用；角色与模拟分开 |
| V23-T34 | 无源码/输入hash/exit/同SHA/分轴状态不得声称完整验收 |

| ID | 追加反例/观察 | 原条款关联 |
|---|---|---|
| V23-X01 | 新语义经读取/确认不丢失或降级；标签/grant/fit=0 | T01/T20；A18/A23 |
| V23-X02 | 无独立schema的旧候选/方法卡/包golden兼容、不重写hash | T01/T23；A23 |
| V23-X03 | 父2条AST精确续接，第三条拒绝，父费用不变 | T13/T15/T23；A05/A17 |
| V23-X04 | liquidity/ext_*起点新模式0fit拒绝，旧模式仍可用 | T04/T10；A09/A10 |
| V23-X05 | L64/65、1073/1074、假日/缺session/未成熟末行 | T07/T08/T10/T21 |
| V23-X06 | mixed有效无效/不可解析/超长响应前置整单元拒绝，计数可核对 | T16/T17；A04/A05/A08 |
| V23-X07 | One-shot冻结后注入反馈，不再次生成或改计划 | T29/T30；A12/A21 |
| V23-X08 | 非法op经review approve仍拒绝 | T05/T20/T24；A09/L09 |
| V23-X09 | 不同引用/浮点重排/碰巧同输出/列交换身份与缓存正确 | T02/T13/T14；A14 |
| V23-X10 | 巨量深层JSON/bool窗口/重复键/中间Inf在资源限内拒绝 | T05/T06/T11 |
| V23-X11 | 受限配方两类导出，失败可审计但半模型不可注册 | T22/T23/T24；L23 |
| V23-X12 | 源码/环境变更、迟到generation、refit中断不强恢复/注册 | T17/T22/T28；A05/A06 |
| V23-X13 | A已接受、B第二fold故障/硬中断；A不重训、B费用不消失 | T17；A05 |
| V23-X14 | 无效响应反复resume不重问；HTTP=0前置修复可恢复；同决定不重扣槽 | T16/T17；A04/A05/A08 |
| V23-X15 | 自报更多能力并重算正确hash、伪装旧schema仍拒绝 | T01/T05/T20；A18/A23 |
| V23-X16 | Random窄支持/重复/达采样上限即停，不扩域换seed | T29 |
| V23-X17 | 某臂无提案/提前stop/失败全部入清单，不记MAE=0、不免费补跑 | T29/T30；A22 |
| V23-X18 | One-shot后半执行读取中间反馈不能触发新生成 | T17/T30；A12 |
| V23-X19 | 受限recipe研究前提示，只审计包不能过完整推理验收 | T21/T22；L23 |
| V23-X20 | W64下长短模型L_bundle正确，旧模式短数据不受新魔数误伤 | T10/T21 |
| V23-X21 | C6a通过但b/c未完不显示全验收；所有者/外部/模拟不混计 | T31/T33/T34 |

补充计数反例并入X14：stop/review/diagnose、合法短响应、审批重入、独立Replay与原成本引用。损坏record/DB不可写/HTTP未知复用并扩展原B5测试，不新增恢复引擎。

## 9. 测试执行、证据和旧缺口

### 9.1 分阶段命令与环境

实施时记录OS/Python/依赖/CPU、base/head/tree、dirty diff、输入hash、准确命令/exit/duration/JUnit。建议新增`tests/test_focused_feature_program.py`、`test_focused_feature_execution.py`、`test_focused_feature_delivery.py`；这是计划文件名，创建前不得声称命令已通过。

先跑本批定向，再累计focused/queue/Memory/共享审核及新UI。PowerShell示例（获准实施后执行）：

```powershell
$env:PYTHONPATH = "src"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
# 使用每次新的短路径；pytest --basetemp 会清理指定目录，不能指向旧失败证据。
$v23Run = Join-Path 'D:/b05runs' ('v23-' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $v23Run | Out-Null
$v23Core = @(Get-ChildItem tests -File | Where-Object { $_.Name -like 'test_focused*.py' -or $_.Name -like 'test_task_queue*.py' -or $_.Name -like 'test_*memory*.py' -or $_.Name -like 'test_workspace_ui*.py' } | ForEach-Object FullName)
$v23Core += 'tests/test_method_card_v3.py','tests/test_streamlit_review_gate.py','tests/test_p09_review_backlog_timeline.py'
.\.venv\Scripts\python.exe -m pytest -q @v23Core --basetemp "$v23Run/core-temp" --junitxml "$v23Run/core.xml"
$v23CoreExit = $LASTEXITCODE
Write-Output "core_exit=$v23CoreExit"
```

在项目受控环境安装原声明extras，缺依赖先报告而不改全局环境。Linux CI核对Python3.11/3.13；Windows重点真实worker/Queue/取消/恢复/Parquet/包/浏览器；macOS/GPU及小时级native不在本次拟议范围。Windows symlink权限失败仍BLOCKED_ENV，不删断言。

浏览器不能以AppTest替代。复用`tests/browser`，明确`FFA_BROWSER_E2E=1`、`FFA_BROWSER_ARTIFACTS`和`FFA_UI_BROWSER_ARTIFACTS`各指新的证据目录。测试两入口、真正两个已训练候选值/详情、切换不增fit/attempt、刷新及新context恢复、review approve/reject、下载hash和显式refit/续接。用隔离simulation数据及原库类型，不操作用户真实DB。

Ruff检查全部实际变更Python文件；compileall检查`src/finance_forecast_agent`、`apps`、`scripts`、`tests`；改JS则逐文件`node --check`。最后全仓pytest一次，保留每项失败首个异常和资产/环境/产品分类，不统一skip求绿。无需为纯文档收口执行以上训练/浏览器全套。

### 9.2 旧A/L门禁映射先于开工

| 门禁轴 | C0必须登记、后续怎么验 |
|---|---|
| A04/A05/A06/A08/A23/L18恢复/身份 | 查原B5可靠记录与硬中断测试；C1/C3新对象路径受影响必须重跑；历史通过不替新源码 |
| A09–A12/A14/A18–A19固定任务/模型/确认 | 新模式必须负例全绿；旧模式行为不能回归 |
| A13/A15–A17交付/UI | C4/C5重跑候选身份、只读、原DB续接与新进程包；实际浏览器 |
| A20–A22/L19–L21基准 | 原失败保留逻辑已存在，做新协议集成回归；新Live无授权即BLOCKED |
| L01–L18/L22–L24文献/权限 | 结构与权限工程回归；真实误引/注入/迁移语义需独立人工和授权Live证据 |
| 原冻结SPY字节缺失 | 原hash验收仍BLOCKED_ASSET；合法其他数据仅可作单独新协议工程例，不能替换旧收据 |
| 真人/Windows权限/native资产 | 逐项保持原状态；C6预览门禁说明适用性，不笼统说旧B5不阻塞 |

原48条状态不由本规划修改。[validation/v22r_acceptance.json](validation/v22r_acceptance.json)保持历史数值/失败/剩余清单；以后有实际新证据才追加V23关联，不建第二份竞争的当前状态库。原47目标负确认保持只读，不为本版重新计算或挑新窗口。

发布需实际同SHA核心及适用Chromium CI；父提交CI单列。未提交的本地diff测试不是同HEAD已提交源码证明，应记录diff身份；文档后续提交产生新SHA也不能借父CI写成同SHA。普通推送遵循当次明确授权，不force push。

### 9.3 交付收据

每批列：修改文件、是否先复现、修复依据、测试nodeid/步骤、命令/exit/数量/耗时、数据与源码身份、模拟/真实、HTTP/规划/fit计数、JUnit/日志、旧证据复用和本轮重跑、剩余原因及下一步。未知费用/人时为null。

最终分别给C6a工程、C6b真实Provider、C6c真人、研究价值、独立金融证据、前瞻能力；只允许由对应证据支持。工程通过可交受控预览，不显示“产品/金融全部验证”。V23-T/X按§12的具体覆盖与边界读取，不将55个目标笼统写成全部PASS。

## 10. 后续产品迭代路线（建议，不是执行授权）

| 阶段 | 交付与选择条件 | 不做什么 |
|---|---|---|
| 当前B5/新工作区 | 保留已有运行与开放项，先实际所有者走查；按相关条款修真正阻塞 | 不重做底座、不改历史失败为绿 |
| V2.3 | 本规范有限价格特征闭环；C0–C6分轴，优先安全纵向切片 | 不扩模型/资产/任务，不要求必须赢 |
| V3-P薄前瞻记录（另审） | 固定合格基线或获准模型、输入as-of/decision_time/prediction_created_at/target_session/label成熟与修订合同；先保存预测再评价 | 不需等Coding Agent，不自动允许DSL，不交易或自动晋升 |
| 一个研究维度扩展（择一另审） | 用户重复受阻时，在训练窗口/权重或上涨概率任务中只选一个；样本/标签/评价/包全链路新合同 | 不同时扩所有自由度；旧曝光派生标签不变盲 |
| 完整Shadow（另审） | 前瞻候选/对照、成熟后评分、缺失/迟到/修订、漂移与人工版本审阅，经实际日历观察 | 不把预测误差当成交收益、不定期自动挑赢家上线 |
| 稳定接口与流程评价 | 用户确有集成需求时再做SDK/MCP/导出adapter；外层评价与完整人工流程成本预注册 | 不先造接入平台来代替产品使用证据 |
| 受控代码/邻近市场（独立立项） | 有反复且DSL无法表达的需求、预算及隔离验收，再选一个维度 | 不借AST悄悄开放任意代码、团队多租户或全资产 |

顺序不强制全部都做；前瞻与后续研究设计可规划并行，但工程启动仍需独立授权和前一阶段适用门禁。金融证据所需时间由真实数据与问题决定，不许用“一个月/几次seed足够”保证有效。4–6周仅是原粗估，C1/C2后根据实测复杂度重估，不以减测试换期限。

## 11. 文档权威、阅读顺序与维护

1. `AGENTS.md`：执行约束、授权边界、读取顺序。
2. `PROJECT_ROADMAP.md`：已批准V23方向与另需批准的后续选项。
3. `CURRENT_IMPLEMENTATION.md`：仅实际能力和已验证状态。
4. 本文件：合并后的V23详细计划与后续唯一增量日志；`V2_MISSION_RESEARCH.md`：原B/R历史、相关B5修复。
5. ADR001/002/003/004及已接受ADR005：历史决定与本版新增范围的区别。
6. `FOCUSED_ARCHITECTURE.md`、`FOCUSED_ACCEPTANCE_TEST_PLAN.md`、`CODEX_FOCUSED_HANDOFF.md`。
7. 统一剩余入口、原验收JSON、受影响B5收据及`AGENT_WORKSPACE_UI.md`/`FRONTEND_USER_GUIDE.md`。

文档准备时只给架构/验收/交接增加本文件入口，不复制55条到多份文档。实施后前端指南已按实际按钮/参数更新；旧ADR和历史验收正文不重写。每批继续更新本文件日志和实际Current。

## 12. 本次文档整理记录

### 实施授权与C0启动（后于下面的历史文档收据）

用户明确要求“提交相关修改，按方案实施相应修改和测试，前端配合”，并回复允许普通推送及核对同SHA CI。文档快照已提交c60d173。git fetch后origin无新增提交；原10个未跟踪证据目录保留。检测到仓库旧Streamlit进程，未检测到对应研究worker，不结束无关进程。开始在隔离临时目录执行修改前累计回归；模型调用预算另行确认，不擅自收费。功能尚未宣称完成。

### C0基线收据：生产代码尚未改动

- 本地Windows 11 Pro 10.0.26200、Python3.13.3、i5-12500（6核/12线程）；GPU/macOS未测试。base=fad63bc8effc6bd3a8e98f7ad94b9896a599c321；文档HEAD=c60d173244b3ef0a1e95828f0a01845bfaf0c05f，tree=9f14b772e543699927ac2664b2d2a87c86d7fdbb。原10个未跟踪目录保持，新增负例与授权文档待后续提交。
- 累计命令按§9.1文件集合执行（focused/queue/Memory/workspace UI及3项共享审核文件），`--basetemp D:/b05runs/v23-base-caa545c9/temp --junitxml D:/b05runs/v23-base-caa545c9/core.xml`；线程环境均1。**420 passed / 1 failed / 2 skipped，3514.79s，exit1**。唯一失败`test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink]`发生在创建测试symlink，WinError1314，列为BLOCKED_ENV，不改断言；Linux同源码覆盖。无产品失败，但不称本地全绿。
- 授权文档检查5 passed/2.18s/exit0，`c0-doc.xml`；命令同下方历史5项，新basetemp=`c0-doc-temp`。原A/L、47目标负确认和旧失败未改。
- 普通推送c60d173成功。同SHA核心CI[36544392964](https://github.com/summerming1/finance-forecast-agent/actions/runs/36544392964) Python3.11/3.13均成功；已下载3.13 JUnit及HEAD到本地`ci313`，**408 passed/0 skipped/528.929s**。同SHA旧浏览器[36544392932](https://github.com/summerming1/finance-forecast-agent/actions/runs/36544392932)及新工作区[36544392934](https://github.com/summerming1/finance-forecast-agent/actions/runs/36544392934)成功。这些是修改前基线，不覆盖后续C1源码。
- 冻结SPY CI[36544392953](https://github.com/summerming1/finance-forecast-agent/actions/runs/36544392953)失败于原run35204186327的`focused-real-inputs` artifact缺失，未训练，BLOCKED_ASSET。本地443821字节输入SHA256=`0bb0896126adb0393f34ae09b90487cb501b2c6aa681a66d2a8f02348669036b`，不是原5fb282…；仅可作另列的新协议历史开发工程例，不能替换原验收。
- C1先行负例收据`c1-full-red.xml`：39 failed/2.98s/exit1（新能力尚未实现）；独立旧入口复现`downgrade-red.xml`：1 failed/2.43s/exit1，`_candidate`确实静默丢弃未知feature_program。首次红测未指定basetemp导致默认pytest目录清理WinError5，后续隔离重跑，不删除旧目录。
- 费用授权仍单列等待；本批无新付费Provider、无真实确认/新标签读取、无真人验收。C0适用基线已核对，可以进入C1；Windows权限、原资产和真实语义/真人边界不是PASS。

### C1：候选版本、不可变程序、确认拒绝与审核配方结构

- 基于0eda9d39badc2c84922fcd317e06aa3a6d961837实施；源包内容身份`delivery-source-v1=6b959524ee51b900d11e099a302fda12e556ddf8bb9520a649a7efee15bb5252`（不包含后续文档）。统一CandidateConfig.from_dict替换恢复、续接、页面和交付的丢字段读取；旧无schema对象保留原序列化/两个golden hash，新字段必须显式focused_candidate_v3，不得伪装旧格式。
- 新FeatureProgram为不可变规范JSON，能力由代码提供，引用hash不授予能力。结构冻结16KiB程序JSON、20000 raw行、32MiB数值工作区估算上限；节点/深度/回看/参数域按§3。C2仍必须验证实际计算和资源估算；不声称整个Python进程或OS级内存隔离。
- DSL候选在selection/prototype/preflight/grant创建/执行入口于标签读取前拒绝；执行grant也不能凭自报正确hash放行。旧bundle禁止携带新程序语义，并在反序列化前严格读取候选。此阶段evaluate/refit显式拒绝FeatureProgram；没有“只算旧列”的临时降级执行。
- 配方是原MethodCard审核记录的可选版本绑定字段，保留机制/迁移差异/输入时点/程序再分发许可；旧review无新增字段、无hash重写。展示本地执行、审计包、完整模型包三种能力。仅simulation_only配方测试，未声称真实文献语义审核或可用性通过。
- 先行红测39 failed/2.98s已保留；实现后`pytest -q tests/test_focused_feature_contract.py tests/test_focused_feature_recipe.py --basetemp D:/b05runs/v23-base-caa545c9/c1-boundary-temp --junitxml D:/b05runs/v23-base-caa545c9/c1-boundary.xml --tb=short`：**41 passed/4.41s/exit0**。
- 相关累计定向：上述2文件加`test_focused_r1_contracts.py test_focused_r4_trust.py test_focused_pr5_delivery.py test_focused_b3_literature.py test_focused_b4_delivery.py`，`--basetemp .../c1-target-temp --junitxml .../c1-target.xml --tb=short`，线程均1：**141 passed/1 failed/567.74s/exit1**；唯一失败仍WinError1314 symlink创建，BLOCKED_ENV。该批收集在追加最后2个边界测试之前，两者单独包含于41项结果中。
- Ruff检查本批7个生产/入口Python文件及2个新测试文件exit0；`python -m compileall -q src/finance_forecast_agent apps scripts tests`与`git diff --check` exit0。新增模块亦包含在Ruff中。完整累计核心/浏览器以本批提交的同SHA CI另核对，不借c60d173结果冒充。
- 关联原A18/A23/L09/L23及V23-T01/T02/T03/T05/T06/T20、X01/X02/X09/X10/X15/X19的**结构部分**；完整执行、资源数值、真实配方语义及页面仍未完成，相应整条保持PARTIAL/PLANNED。HTTP=0、新候选训练fit=0、新真实确认=0；旧回归只在隔离simulation数据库训练。

### C2：纯计算与固定研究数据协议（尚未接入训练）

- C1提交01c9812e3a71910d840d9036d1433795e1b3c3ef的同SHA核心[36549859024](https://github.com/summerming1/finance-forecast-agent/actions/runs/36549859024) Python3.11/3.13均成功；旧浏览器36549859101、新工作区36549858836成功。冻结输入36549859052仍失败于下载原artifact，BLOCKED_ASSET，不是PASS。
- C2先行红测`c2-red.xml`18 failed/2.41s/exit1；实现后新边界`c2-boundary.xml`64 passed/3.88s/exit0。最终命令：`python -m pytest -q tests/test_focused_feature_program.py tests/test_focused_feature_contract.py tests/test_focused_feature_recipe.py tests/test_focused_data_research.py tests/test_focused_pr6_byo.py --basetemp D:/b05runs/v23-base-caa545c9/c2-regression-temp --junitxml D:/b05runs/v23-base-caa545c9/c2-regression.xml --tb=short`，OMP/MKL/OPENBLAS线程1，**96 passed/63.33s/exit0**（1项JUnit属性格式警告）。本批4个Python文件Ruff、全src/apps/scripts/tests compileall及diff检查exit0。
- 数值层按原始价格计算有限AST，ddof=1、完整右对齐窗口、每层有限性检查；实际列顺序与只读输出冻结。研究严格W64并去掉末行未成熟label；1074原始行才有1009监督行。raw输入拒绝缺失/乱序/非交易日等，不排序或填补。Snapshot新增协议只在新模式输出，旧Campaign序列化保持。
- 模拟最大规模观测：20000行、两棵共30节点AST、11输出列，tracemalloc峰值3695200 bytes，预先估算13760000 bytes，0.0067558s。收据`c2-boundary-temp/test_maximum_grammar_numeric_w0/resource-receipt.json`；这是数值工作区工程观测，不是整个Python进程RSS或OS级内存隔离承诺。
- 真实历史本地转换命令：调用`build_spy_feature_research_frame('inputs/spy_chart_2010_2025.json')`，exit0，HTTP=0、fit=0。原始4024行，监督3959行，2010-04-07至2025-12-30；raw hash为上述0bb089…，不是旧冻结资产。dataset fingerprint=`0a46dc5be7165d932b64ea231311aa89eb74b766571e0bd7f8f81c607ea331f5`，raw history=`dd1aac3f5c4647cbb98723f79c5af6211cb29c4bd7b68ede4f5c4fe3b01010c6`，row mapping=`0ec1a931c7a9d07aea29c04d605fcb06e1d29a06b187a49d1ce0a84d57183466`。point_in_time=false；可用时间是收盘后声明，不是观测到的provider回执。
- 源包身份`delivery-source-v1=8956b7d3e4f7092b251d92b026d45c30c98f03393931bdc2db5d8902205d58bf`。全部收据根为`D:/b05runs/v23-base-caa545c9`。新增数学/数据测试simulation_only；既有相关回归使用隔离测试库。没有用户运行DB修改、新付费LLM、新确认或真人证据。
- 本批仅完成T07–T12相关纯计算/数据部分；Campaign规划/预算/恢复、ModelBundle和页面仍未完成，不能用96通过关闭整体验收。C2提交后同SHA核心/浏览器待核对，C3按累计门禁继续。

### C3：复用执行链、规划账本、恢复与Memory

- 基于33915c62af710c8d2b95ad91c3f9954f31d3c380。C2同SHA核心36553822813 Python3.11/3.13成功，两套浏览器36553822753/36553822737成功；本地`c2-ci311`下载HEAD与JUnit核对一致，472 passed/0 skipped/457.833s。原冻结输入36553822812失败于下载原资产，仍BLOCKED_ASSET。
- 新模式仅扩展原Controller/compiler/evaluator/RuntimeDB/Memory和mission/worker选项，不创建另一套状态或执行器。模型、有效参数、seed、内置组固定；程序计算绑定完整raw前缀、W64目标行及数据revision。One-shot整体最多4项、执行单元最多2；Adaptive至多两次规划×2槽。原内部Advisor尝试、HTTP重试、未知计费与fit账本保持，新增逻辑决定/预留/结算是同DB中的对象。
- 明确整批schema/权限/父引用/计算/预算预检。无效整批proposal_invalid终止、只保留基线和既有结果，不训练合法子集；重复占槽不fit；短响应结算未用额度。stop/review无dummy模型，approve不赠规划轮次。Random使用price_ast_uniform_depth_v1：0–2特征、深度上限4、终结符/算子及批准参数均匀抽样、非法回看最多128次有界拒绝，重复候选不重抽；它与Live提案使用同一语法，未称Agent质量或TPE比较。
- 先行`c3a-red2.xml`11 failed/9 passed/3.33s/exit1（接口尚未实现；此前初版测试Evidence ID字段错误也保留）；`c3b-red.xml`8 failed/3.15s/exit1；Memory红测1 failed/2.20s。实现后纯边界90 passed/5.21s。首次Campaign集成7 passed/1测试字段名错误/192.44s，按既有manifest_execution_conformant字段修正，没有放宽断言。
- C3集成命令：`python -m pytest -q tests/test_focused_feature_campaign.py tests/test_focused_feature_recovery.py tests/test_focused_feature_memory.py tests/test_focused_feature_execution.py tests/test_focused_feature_program.py tests/test_focused_feature_contract.py tests/test_focused_feature_recipe.py --basetemp D:/b05runs/v23-base-caa545c9/c3-integration-temp --junitxml D:/b05runs/v23-base-caa545c9/c3-integration.xml --tb=short`：**104 passed/531.03s/exit0**。包括真实后台worker及继承完整父程序的新Campaign，不使用用户DB。
- 相关旧回归命令：`python -m pytest -q tests/test_focused_r1_contracts.py tests/test_focused_r3_actions.py tests/test_focused_b2_product.py tests/test_focused_b3_literature.py tests/test_focused_b4_delivery.py tests/test_workspace_ui.py --basetemp D:/b05runs/v23-base-caa545c9/c3-regression-temp --junitxml D:/b05runs/v23-base-caa545c9/c3-regression.xml --tb=short`：**107 passed/771.46s/exit0**。两组期间冻结生产源码；这些结果先于下面两处新模式边界补修，不冒充补修后的全量同源码回归。
- 补充复现一：调用者修改Snapshot嵌套字典会改变CampaignSpec展示合同，`c3-mutable-red.xml`1 failed/2.88s；Spec改为绑定内部副本。补充复现二：已冻结计划的fixture响应被修改、原hash保留，旧路径仍训练至20 fits，`c3-fixture-red.xml`1 failed/40.50s。新模式未完成计划恢复前增加原schema/prompt/call-ID/完整record及plan绑定核验；坏JSON/hash/缺失记录拒绝，不重发、不训练。已经完成Campaign的只读结果仍是原DB已接受事实，不保证丢失fixture仍可重新Replay。
- 补修后最终命令：`python -m pytest -q tests/test_focused_feature_recovery.py tests/test_focused_feature_execution.py tests/test_focused_feature_memory.py tests/test_focused_feature_contract.py tests/test_focused_feature_recipe.py tests/test_focused_feature_program.py --basetemp D:/b05runs/v23-base-caa545c9/c3-final-boundary-temp --junitxml D:/b05runs/v23-base-caa545c9/c3-final-boundary.xml --tb=short`：**98 passed/198.04s/exit0**；均线程1，1项JUnit属性格式警告。最终源包身份`delivery-source-v1=46588e8e6ce12d6b138176b8032bf07ab615181a608e25376d20f4c6b2971e1c`。Ruff受影响focused/mission/script/tests、compileall和diff检查通过。同提交完整核心/Chromium另核对。
- 关键计数：Adaptive 2决定/4槽/28 fits；One-shot 1决定/4槽/28 fits、2执行单元；重复4槽但16 fits；无效单元2槽且12基线fits；HTTP=0前置失败恢复内部尝试2、同一逻辑决定1、stop占1槽且12 fits。Review approve后原Campaign20 fits/3槽，reject12 fits/1槽。新进程中断B第一fold已实际fit：12基线+A4+孤儿B4+重试B4=24，A产物/冻结计划不变。未知HTTP投递中断后仍仅1次本地HTTP、12 fits；完整fixture/plan恢复1次本地HTTP、20 fits；损坏/缺失fixture保持1次HTTP、12 fits并拒绝。
- 测试均simulation_only/assistant_authored_fixture；本地模拟HTTP走真实客户端但不是真实模型能力。Memory兼容加协议/能力/编译器、严格候选程序及冻结as-of；未知旧时间不补造、未来/错tenant/确认记录不进上下文。原引用权限继续保留，reviewed_recipe通过同一EvidenceIndex投影；真实文献语义、付费Provider、真人均未验证。C4新包与C5新页面仍未完成，refit继续显式阻断新程序，不包装成全产品通过。
- 关联原A04/A05/A06/A08/A11–A15/A18/A23及L09/L18/L23的受影响工程回归；V23-T13–T19/T23–T27相关C3部分，完整页面、导出和Live部分保留待验。原48条历史状态与47目标负确认未改。

### C3追加：Chromium收尾同步

- 2a21890968f1d99aefeb4499f56703b51d3cb31b同SHA核心36559651550 Python3.11/3.13成功；旧Chromium36559651608成功。工作区36559651571的适配/浏览器步骤失败，受影响回归及静态成功；下载原HEAD、JUnit、截图和日志于`D:/b05runs/v23-base-caa545c9/c3-ci-workspace`。失败为Campaign final已完成但Queue尚在running收尾的瞬时断言，不是模型训练异常。原冻结输入36559651492仍失败于Download frozen audited SPY inputs，BLOCKED_ASSET。
- 仅修改浏览器测试同步：已有`_wait_task`等Queue完成，再等组件消费Queue最终状态；不放宽完成状态、候选数、20 fits、包hash或续接断言。生产源码未变。
- 本地命令`python -m pytest -q tests/browser/test_agent_workspace.py --basetemp D:/b05runs/v23-base-caa545c9/c3-browser-fix-temp --junitxml D:/b05runs/v23-base-caa545c9/c3-browser-fix.xml --tb=short`，FFA_BROWSER_E2E=1、线程1：**1 passed/90.55s/exit0**。真实Windows Chromium/Queue/worker、simulation_only数据、HTTP=0；Ruff及diff检查exit0。修订测试的同SHA远端结果仍另核对。

### C4：原始价格可信ModelBundle与受限程序导出

- 基于b80bdb4；其同SHA新工作区36561525100与旧Chromium36561525068已成功，核心结果另核对。C3生产源码未因浏览器同步修正改变。
- 新包显式focused_model_bundle_v3，保存代码拥有的raw输入合同、实际内置配方/AST/列序/L、数据revision、训练cutoff/label可用时间、环境与编译器源文件hash；原v2加载不变。研究W64和推理L分开，推理保留最后一行、不要求未来label。编译器相关源文件变化后新包要求重建，不承诺跨版本隐式兼容或跨机trust迁移。
- 复用原RuntimeDB：显式refit在fit前预留1次，失败/未知不抹除；完全训练及包完整后，可信注册与完成记录同一事务。新工作台费用汇总读取该账本并兼容无新receipt的旧已完成refit，不双计。DB不可写时可能留下证据缺口，不声称任何故障都完整留账。
- reviewed_recipe的程序再分发权限独立于摘录权限。受限程序包降级reference_only并明确不可独立执行；完整ModelBundle在fit前拒绝。允许程序但不允许摘录时只保留最小来源绑定，不输出摘录；加载/下载再次核验原审核记录及撤销状态。权限测试均simulation_only，不是人工语义审核。
- 先行`c4-red.xml`7 errors/3.55s/exit1（新接口不存在）；`c4-rights-red.xml`2 failed/3.12s/exit1，明确复现允许摘录但禁止程序时未降级。实现后`c4-first.xml`11 passed/18.92s/exit0。
- 最终相关命令：`python -m pytest -q tests/test_focused_feature_bundle.py tests/test_focused_feature_export.py tests/test_focused_feature_contract.py tests/test_focused_feature_recipe.py tests/test_focused_pr5_delivery.py tests/test_focused_b4_delivery.py tests/test_workspace_ui.py --basetemp D:/b05runs/v23-base-caa545c9/c4-regression-temp --junitxml D:/b05runs/v23-base-caa545c9/c4-regression.xml --tb=short`，线程1：**94 passed/276.73s/exit0**。fresh Python子进程与同一refit独立参考逐值一致；60日均值61点输出1行、60点拒绝，最后行保留。metadata/AST/compiler/model/错tenant/未登记路径均在joblib前拒绝；撤销权限拒绝；失败refit计1且无可信包。
- Ruff受影响3个生产文件和2个新测试文件、全src/apps/scripts/tests compileall、diff检查exit0。源包身份`delivery-source-v1=c8eb2709123e5d94824c6f179530ff1b833c585c18e534403f1d4b213a3c3be0`。真实Provider HTTP=0，工程数据/文献模拟，用户原DB不修改。C5新增模式页面与C6分轴验收尚未完成。
- 原可信确认回归另跑`tests/test_focused_r4_trust.py --basetemp D:/b05runs/v23-base-caa545c9/c4-trust-temp --junitxml D:/b05runs/v23-base-caa545c9/c4-trust.xml --tb=short`：31 passed/1 failed/59.54s/exit1。唯一失败仍创建symlink的Windows1314权限，BLOCKED_ENV，断言未删改；Linux门禁继续保留。

### C5：工作台接线与真实浏览器

- C4提交69101c7同SHA Linux3.11/3.13核心36562811773、原Chromium36562811923、新工作区36562811789均成功；原冻结输入36562811838仍失败，不改原验收资产。
- 原三步向导增price_features、规划策略/种子、冻结能力和导出提示；旧features_only标明仅组合现有组。JSON/未知字段不降级。实际公式/diff/列序/L/保护除法在原候选抽屉只读呈现，规划与Advisor尝试/HTTP/fit区分。预检不训练，创建/额外refit/续接仍需明确确认。
- 先行UI接口红测`c5-red.xml`2 failed/4 passed/3.72s；另复现固定Ridge将要求RF的recipe误标可执行（`c5-cap-red.xml`1 failed/3.08s），修复为当前固定模型/内置组的能力投影，不使用平台全目录授权。模拟source字段未传到price worker的红测`c5-provenance-red.xml`1 failed/2.91s；原始来源只接受historical_development_only/simulation_only，模拟标记绑定Snapshot/task并贯穿worker/refit/页面，历史开发不误标外部未知；不允许自封sealed。
- 单元57 passed/7.88s/exit0；最终相关命令`python -m pytest -q tests/test_workspace_ui.py tests/test_workspace_ui_features.py tests/test_focused_feature_campaign.py tests/test_focused_feature_bundle.py tests/test_focused_feature_export.py tests/test_focused_feature_execution.py tests/test_focused_feature_program.py tests/test_focused_b3_literature.py --basetemp D:/b05runs/v23-base-caa545c9/c5-regression-temp --junitxml D:/b05runs/v23-base-caa545c9/c5-regression.xml --tb=short`，线程1：**121 passed/659.74s/exit0**。源包身份`delivery-source-v1=0dcc81af4813d6439379f6562bbc45c6d06d063ce9fc5505c020c74a03d84306`。
- `FFA_BROWSER_E2E=1 python -m pytest -q tests/browser/test_agent_workspace.py --basetemp D:/b05runs/v23-base-caa545c9/c5-browser-temp --junitxml D:/b05runs/v23-base-caa545c9/c5-browser.xml --tb=short`：**2 passed/222.09s/exit0**，Windows Chromium153.0.8010.12、simulation_only，旧受控CSV及新价格公式流程都通过。新输入hash cb063f4b608912b32e4ac2ea905a1d542389bbae80a6c974c51f97e129bc457b；每批20 fits、两个已训练候选切换，刷新/新context不增fit/attempt，refit v3/选错候选下载拒绝、研究包SHA256、1280布局、父公式续接均验证。父+子研究账本16 attempts/40 reserved fits，另有1次显式refit；HTTP=0、page_errors=[]。
- 内置浏览器额外在独立8512服务检查向导与零训练预检，显示1035行simulation_only、W64、快速试跑1次规划/1槽；截图`D:/b05runs/v23-base-caa545c9/manual-ui/v23-preflight.png`。这是助手工程验收，不是真人。Ruff受影响文件、compileall、所有前端JS语法通过。用户操作清单写入FRONTEND_USER_GUIDE，原AGENT_WORKSPACE_UI说明保留历史边界。
- C6历史真实输入新合同smoke/指标复算、最终同SHA门禁仍待执行；Live待明确费用批准，真人须用户操作。旧A/L和47负确认不变。

### C6：同空间三臂工程例与独立交付审计

- 基于2e5e5ed6119bce9a9a9dd35b842d7c30d3156bbe；该C5提交同SHA核心36565831917的Python3.11/3.13、新旧Chromium36565831932/36565831924均成功。原冻结输入36565831995仍失败于下载，不替换资产。C6最终提交CI另核对。
- 原benchmark入口增`--price-features`，三臂都调用原Controller的C3规划、compiler、evaluator和预算。旧目录TPE及五臂保持原接口；新AST不声称支持连续TPE。正式新pilot使用cold Memory、4槽、固定seed42估计器/样本/语法，每臂28研究fits、8 HTTP、1200 Provider活动秒；新CLI调用前登记按search seed随机化的执行顺序，Live须显式费用许可。不同hash域不可互换。
- 先行`c6-red.xml`5 failed/2.51s/exit1：原API不接受raw_history；随后命令`python -m pytest -q tests/test_focused_feature_benchmark.py tests/test_focused_r5_benchmark.py --basetemp D:/b05runs/v23-base-caa545c9/c6-benchmark-temp --junitxml D:/b05runs/v23-base-caa545c9/c6-benchmark.xml --tb=short`：**24 passed/1002.99s/exit0**。此时收集前5个新测试，后来增加的Replay、CLI和审计hash测试单列；最终全仓再覆盖最终生产源码。
- 本地模拟HTTP录制→严格离线Replay：`python -m pytest -q tests/test_focused_feature_benchmark.py::test_local_http_record_then_strict_offline_price_replay --basetemp D:/b05runs/v23-base-caa545c9/c6-replay-temp --junitxml D:/b05runs/v23-base-caa545c9/c6-replay.xml --tb=short`，**1 passed/126.08s/exit0**。录制2 HTTP/2个原生fixture/2决定/28 fits；关闭本地server、移除三种凭证并阻断请求函数后，Replay 0 HTTP/2回放/28独立fits，候选与数值完全一致。明确simulation_only，不是真实模型质量或新的付费Live。最终代码额外确保模拟数据不能标live_quality_evidence。
- CLI预注册顺序的orchestration-only spy测试`test_price_cli_preregisters_seeded_order_before_dispatch`：`c6-cli.xml`1 passed/2.97s/exit0，不冒充训练。执行/交付源码域区分测试`test_pilot_auditor_uses_execution_not_delivery_hash_domain`：`c6-audit-unit.xml`1 passed/2.85s/exit0。各自新basetemp同名加`-temp`。文档/原条款5 passed/2.21s，`c6-doc.xml`。
- 真实历史工程命令：`python scripts/run_research_value_benchmark.py --price-features --raw-spy-json inputs/spy_chart_2010_2025.json --candidate-count 4 --batch-size 2 --estimator-seed 42 --seed 42 --arms random one_shot adaptive_batch --llm-mode deterministic --memory-mode cold --out D:/b05runs/v23-base-caa545c9/c6-real-pilot.json`，**exit0，三臂completed，HTTP=0**。输入仍0bb089…，监督3959行/2010-04-07→2025-12-30，252个共同评价目标；不是原5fb282…门禁，不是新独立确认。三臂各自合同在fit前登记；本次工程运行启动时尚未加CLI全局随机顺序，实际按random→one_shot→adaptive_batch，不冒充后续正式Live随机顺序试验。

| deterministic工程臂 | 逻辑决定/槽 | 唯一候选/重复 | 研究fits | 最佳MAE | 相对同窗固定Ridge改善 | outcome | 墙钟秒 |
|---|---|---|---|---|---|---|---|
| Random | 2/4 | 3/1 | 24 | 0.005297110962052618 | 0.20484985% | no_improvement | 68.5662534 |
| One-shot规则演示 | 1/4 | 4/0 | 28 | 0.005290720923455558 | 0.32523526% | improved | 73.0527736 |
| Adaptive Batch规则演示 | 2/4 | 4/0 | 28 | 0.005290720923455558 | 0.32523526% | improved | 79.1838621 |

共同Ridge MAE=0.00530798436003082；outcome仍按原确定性评价政策，不凭小幅MAE变化改判。两规则演示使用相同程序得到相同数值，不证明自适应LLM增加研究价值；主动人时未知为null。

- 新审计脚本仅复用原`verify_metrics/verify_package`与原交付接口。第一次`c6-real-audit` exit1：审计代码误把research-execution-source-v1与delivery-source-v1比较，0额外fits；修正域并加上面的负例。第二次`c6-real-audit-v2` exit1：Random已refit1次，fresh CSV默认float解析产生最大1.47015646e-14差异；改审计子进程为`float_precision='round_trip'`，不放宽逐值相等、不改研究或模型。复用已登记包的诊断逐值一致，0新fit；两个失败目录保留。
- 修正后的完整命令：`python scripts/verify_price_feature_pilot.py --matrix D:/b05runs/v23-base-caa545c9/c6-real-pilot.json --raw inputs/spy_chart_2010_2025.json --expected-sha256 0bb0896126adb0393f34ae09b90487cb501b2c6aa681a66d2a8f02348669036b --state-db D:/b05runs/v23-base-caa545c9/c6-real-pilot_runs/runtime.sqlite3 --out D:/b05runs/v23-base-caa545c9/c6-real-audit-v3`，**exit0 / receipt.json PASS**。29份PredictionArtifact聚合及116份fold指标独立复算；三个ResearchPackage分别28/30/31成员hash全部匹配；三次fresh Python raw推理分别3962/4018/4018行，末行保留、逐值一致、Campaign hash不变。历史无标签接口测试不叫样本外效果。
- 研究80 fits保持，审计累计**4次额外refit**（v2失败1+v3成功3）全部留账，HTTP=0。matrix hash=`08b15b7bc8718112619263c0b0f966b3943b4831a92f129e8337f518f0c3320c`；执行源码=`21e1bf56b92d851752f20c6583a2b621bad81317cba75349603699a3fc03e12b`；交付源码=`d028fffc8b904c1b7843e2be072fb1c38cb3058cc453cd07bb6578bd1626a2ef`。新审计未更改旧冻结验证脚本/门禁，也不消费确认授权。
- 本批Ruff全部实际变更Python、compileall src/apps/scripts/tests、diff检查exit0。最终全仓pytest仍运行，最终同SHA CI待提交核对；不能提前称全部通过。原资产、Windows symlink权限、真实语义误引/注入和真人缺口分别保留。新Live费用授权未收到，不从推送授权推断付费授权；C6b真实Provider为NOT_RUN，C6c真人为BLOCKED_NO_REAL_USER。

### 验收目标到现有证据的索引（不是55项全通过声明）

C6功能提交`dbc4014ea5893109fa0a57181a501b17ee91b391`，tree=`21064e3a352815f05eaed1db6add4ce09435c73a`，已普通推送。开始数次上传连接中断，核对远端未变；稍后重试成功，未改全局代理或force push。同SHA核心[36572536404](https://github.com/summerming1/finance-forecast-agent/actions/runs/36572536404)的Python3.11/3.13均成功；已下载HEAD/JUnit到本地`c6-ci311/c6-ci313`：**各537 passed、0 skipped，671.239s/681.747s**。旧Chromium[36572536735](https://github.com/summerming1/finance-forecast-agent/actions/runs/36572536735)成功；新工作区[36572536285](https://github.com/summerming1/finance-forecast-agent/actions/runs/36572536285)下载核对HEAD/tree一致，**24 passed/117.979s**（含两条真实浏览器流程），相关回归**54 passed/111.838s**。原冻结门禁[36572536314](https://github.com/summerming1/finance-forecast-agent/actions/runs/36572536314)仍FAIL于`Download frozen audited SPY inputs`，未进入模型步骤，分类BLOCKED_ASSET。文档收据提交后的最终SHA须再次检查CI，不能借本段父提交结果冒称同SHA。

#### 最终本地全仓与边界归类

命令：`python -m pytest -q --basetemp D:/b05runs/v23-base-caa545c9/c6-all-temp --junitxml D:/b05runs/v23-base-caa545c9/c6-all.xml --tb=short`，三种数值线程环境均1；**703 passed / 2 failed / 5 skipped / 8 warnings，4645.92s，exit1**。不能称全仓绿。全仓运行期间src生产包保持上述d028…/21e1…身份；收集后新增的CLI预注册和审计hash域2项未混入该710项计数，另以`c6-final-doc.xml`连同文档检查**7 passed/3.18s/exit0**，并已纳入dbc4014同SHA Linux537项。八个警告为既有`record_property`与JUnit xunit2格式提示，不是忽略失败。

从同一全仓JUnit按§9.1集合抽取（focused/queue/Memory/workspace UI及3共享审核文件）为**554 passed / 1 failed / 2 skipped，共557项**；case时间合计4596.485s，不是另一条独立重跑命令或墙钟。两项晚加测试另列如上，不通过简单相加各批收据伪造独立测试总数。

| 失败nodeid | 首个异常、分类 | 本轮引入/恢复办法 |
|---|---|---|
| `tests/test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink]` | 创建测试symlink时`OSError: WinError 1314`，尚未进入反序列化；BLOCKED_ENV，缺Windows权限，不是缺Python依赖 | C0已复现，同代码Linux门禁通过；操作者可另行配置Windows符号链接权限后重测，本轮不提权、不删断言 |
| `tests/test_p1_real_validation_artifacts.py::test_dlinear_strict_live_card_replays_without_an_api_call` | `FileNotFoundError: projects/finance_agent/llm_fixtures/method_card/2c05bfd22af27435.json`；BLOCKED_ASSET，当前严格prompt无对应历史record/catalog；没有调用Provider | 测试、`method_cards.py`、`replay_llm.py`对fad63bc均无差异，未发现V23引入此路径变化。目录中仅找到不同hash的`a244047067fcaf58.json`且created_by=offline_assistant，不能改名/改hash伪造strict-live回放。需恢复原合法prompt/PDF/支持上下文对应录制；重新付费录制须另批，不能冒充原证据 |

5项跳过：两条Agent工作区浏览器和原Research Workspace浏览器因本次全仓未设置显式browser环境；它们由独立真实Windows浏览器及同SHA Chromium CI覆盖。`test_queue_recovers_real_interrupted_worker`为POSIX进程组probe，Windows不运行；`test_package_rejects_symlink`明确缺symlink权限。不得把这两项本机平台边界写PASS。

原历史/native其余测试本轮通过的是资产/协议/单元检查；**未重跑小时级原论文训练、GPU或macOS**。不能沿用旧“10/11失败”的数字描述本次，也不能把这些检查当所有论文重新训练成功。新旧数据、原DB、失败目录和47目标负确认保留；原验收JSON去掉新增V23节后与fad63bc逐结构完全相同，PowerShell核对exit0。30个本地Markdown链接、全部变更Python Ruff、compileall和前端JS语法通过。已关闭本轮8512测试服务，未结束原网页服务。

| 最终交付轴 | 结论 | 下一步 |
|---|---|---|
| C1–C6a受控工程预览 | PASS（适用核心/真实浏览器/历史开发审计；上述Windows权限与旧资产单列） | 可按FRONTEND_USER_GUIDE进入产品所有者真实走查；最终文档SHA另核对CI |
| 全仓原样零失败 / 原冻结SPY门禁 | BLOCKED_ENV / BLOCKED_ASSET | 恢复权限、匹配DLinear记录和原5fb282冻结输入；不换输入求绿 |
| C6b新DSL真实Live→Replay / 三臂模型质量 | NOT_RUN，等待本轮明确模型/费用/资料权限 | 先冻结预算与随机顺序；不重跑旧有效付费G2A/G2B，不自动换模型 |
| 文献真实配方/误引/说明与公式矛盾 | NOT_RUN / BLOCKED | 实际人工审核合法来源，工程fixture不能代替 |
| C6c所有者及独立用户、回访再使用 | BLOCKED_NO_REAL_USER | 操作者按清单真实使用并反馈人时、帮助、正确理解、导出再使用；不由助手代填 |
| 新独立金融证据 / 前瞻产品 | NOT_RUN / NOT_READY | DSL确认仍禁用；未实现或启动V3，原47目标负确认不改 |

整体验收为**PARTIAL**，不是因为未出现更好分数而追加试验。最终git身份及文档提交后的同SHA CI放在交付消息/本地`D:/b05runs/v23-base-caa545c9/delivery_receipt.json`，避免把包含自身SHA的收据反复提交造成循环；上面的功能提交CI保留其实际SHA。

测试文件均在`tests/`；下列是覆盖入口，具体参数化nodeid/运行时间见各JUnit。原条款只追加JSON关联，不重写历史PASS/FAIL。

| 目标 | 本轮证据入口 | 未被这些证据证明的部分 |
|---|---|---|
| T01/T02/T05/T06/T20，X01/X02/X09/X10/X15 | `test_focused_feature_contract.py`：legacy golden、未知字段降级、身份/能力伪造、AST边界、直接grant/API在标签与状态访问前拒绝 | 不承诺旧二进制能识别新schema；DSL独立确认仍禁止 |
| T07–T14，X05/X20 | `test_focused_feature_program.py`、`test_focused_feature_execution.py`：独立算例、未来扰动、溢出、raw/W64共同样本、实际矩阵和Manifest；C6历史产物复算 | 因果计算不证明Yahoo point-in-time；旧冻结字节仍缺 |
| T15–T17/T25，X03/X04/X06/X07/X08/X13/X14/X18 | `test_focused_feature_campaign.py`、`test_focused_feature_recovery.py`、execution/contract：整单元拒绝、冻结模型、消融、短/无效/重复槽、review、真实worker/进程硬中断与可靠record | 本地模拟HTTP不是实际模型语义；新模式浏览器review仍复用原审核界面证据与新Controller集成，未新增真实LLM review网页试验 |
| T18/T19/T24，X11/X12/X19 | 受影响原曝光/恢复/权限回归；`test_focused_feature_memory.py`、recipe/export/bundle及`test_focused_b3_literature.py` | 真实文献误引/说明与公式矛盾仍需人工/获准Provider；旧47目标负确认只保留历史 |
| T21–T23/T26–T28，X03/X11/X12/X19/X20 | `test_focused_feature_bundle.py`、export、`test_workspace_ui_features.py`、`browser/test_agent_workspace.py`；C6独立package/hash/fresh Python审计 | Windows symlink本机权限不足；同SHA Linux必须另核对；ModelBundle不迁移跨机信任 |
| T29/T30，X16/X17/X18 | `test_focused_feature_benchmark.py`及原`test_focused_r5_benchmark.py`：共享合同/目标/预算、原失败报告；C6三臂规则工程例 | 新DSL真实Live三臂尚NOT_RUN，不证明LLM自适应价值；有界Random采样不是均匀抽取所有AST |
| T31–T34，X21 | 本日志、原验收JSON追加关联、当前状态及前端真人操作清单 | 真实配方人工审核、人时/真实使用/再次使用缺口保留；费用未知null；最终提交同SHA不能借父CI |

### 2026-09-30 对抗复核与限定修复

基线2fbadca628928ae661e5549b19de6ef3a8e32c81，Windows/Python3.13.3。用户批准四项缺陷修复、必要只读展示和相关验收；不新增付费LLM、确认标签读取、GPU/macOS/native训练。旧RuntimeDB及47目标负确认不变。

复核在隔离模拟库重现：零研究候选仍拿baseline_mean配对；原始模型JSON重复键被首次解析吞掉；Random登记1而执行128、实际4+2抽样却报告0；核心构造器与旧预算字段可改变价格模式固定政策。初始复核72项通过不覆盖这些负例。证据D:/b05runs/v23-second-review-l0efdb1_。

历史工程例勘误：c6-real-pilot.json的Random登记max_sampler_draws=512，实际两次上限128，draws=4+2，报告总数0。保留原报告、注册、账本和预测；不倒改hash或追认合规预注册。三臂实际最佳固定对照均为Ridge，原政策0.0025/development_only；两规则演示最佳均为rolling_mean(return_1,20)，不是真实自适应或消融成果。

第一批将Benchmark角色显式分为研究候选/固定对照/用户起点/最佳可用模型。新报告v3的best兼容字段指向最佳研究候选；没有候选时null，有退化时保留负改善；基线MAE=0时相对值null。策略与文献比较不以旧best字段代替研究结果。已保存的旧报告字节不重写。

新失败收据位于D:/b05runs/v23-fixes-0930：red1.xml初次4失败/1测试目录设置错误；修正目录后red1b.xml真实整Campaign零候选失败。red2初次超长测试ID设置错误保留；固定短ID后red2b.xml六项JSON入口负例失败。red3.xml采样合同失败，red4.xml六项核心/恢复初始化政策负例失败。各批修复后的定向/回归及最终同SHA CI另记，不提前报通过。

第一批验证：`python -m pytest -q tests/test_focused_v23_review.py tests/test_focused_r5_benchmark.py tests/test_focused_feature_benchmark.py`，32 passed / 789.53s / exit 0，JUnit `fix1.xml`；追加空提案/全部重复/训练失败三项，3 passed / 100.50s / exit 0，`fix1-extra.xml`。均模拟数据、真实本地Controller训练，HTTP=0；相关Ruff、compileall、diff --check通过。不是Live或金融确认。

### 历史：仅文档整理时的收据

- 2026-09-29：合并原方案与两轮审核；选择价格-only、无自动生成式修正、DSL确认禁用，明确旧格式兼容、前置/响应后失败、规划与实际调用计数、部分完成及分轴交付。
- 本轮仅文档编辑；没有功能实现、训练、Provider调用、确认标签读取或远端推送。文档一致性检查结果另在本节补记；不能作为V23功能验收。
- 实施前下一步：用户明确授权范围后，将ADR005变为accepted，核验C0门禁/活动任务/实际HEAD，再做C1；不从“文档已整理”自动开工。

本轮文档验证：项目`.venv/Scripts/python.exe -m pytest -q`运行`tests/test_focused_b0_plan.py`、`tests/test_focused_r0_status.py::test_current_status_has_one_authoritative_source`、`tests/test_focused_b5_acceptance.py::test_remaining_clause_inventory_matches_actual_partial_states`、`tests/test_focused_b5_acceptance.py::test_current_guide_and_stage_do_not_instruct_obsolete_delivery`，使用新的`--basetemp D:/b05runs/v23-docs-b094a232/temp --junitxml D:/b05runs/v23-docs-b094a232/docs.xml`。结果**5 passed / 2.75s / exit 0**，仅文档/旧条款一致性，不运行训练。

PowerShell只读检查10份本次文档的UTF-8、代码围栏、30个本地Markdown链接、55个V23计划条目唯一/完整性及ADR proposed状态，exit 0；`git diff --check` exit 0。`src/apps/scripts/tests/.github/docs/validation`无本轮差异。全套功能、浏览器、Live及同SHA远端CI本轮NOT_RUN（文档范围）；未commit/push，原未跟踪证据目录保留。

来源留痕（外部文件不必存在于其他开发者电脑；执行无需再解释三份原文）：

| 来源 | SHA256 |
|---|---|
| Finance_Forecast_Agent_产品修改与测试方案_审核稿.md | 309071e618a7e29b974754a3200ea1fb36af00eab3b1d19d873365df2de2a29a |
| V23_对抗性审查与修订实施验收方案_20260929.md | 2b35a90334e5712350f89bf46d8c961257c84e414a787a2cb2395fec45c13659 |
| V23_审核意见复核与必要修正_20260929.md | 82f5d54ef6662ebb0dc522fcdc471eb798696e5519c910072edd3912c657ff8d |
