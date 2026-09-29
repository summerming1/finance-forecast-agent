# V2.3 受控价格特征研究：合并修改、测试与产品迭代方案

日期：2026-09-29。状态：**用户已批准实施；C1同SHA核心/浏览器通过，C2纯计算本地验证完成、累计CI待核对；功能状态以CURRENT_IMPLEMENTATION为准**。

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

以下全部为计划，不是当前已实现功能。每批：复现/负例→最小修改→定向→相关累计→静态→涉及的worker/browser→记录→获准时提交；前一批相关安全/正确性红灯不越过。

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

C0基线现已核对；C1已冻结结构合同（§12），尚未上线特征计算或规划预算执行。下表中的C2–C6仍为待实施/待验收，不因文档或结构测试提前完成。

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

## 8. 验收矩阵（全部PLANNED）

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

最终分别给C6a工程、C6b真实Provider、C6c真人、研究价值、独立金融证据、前瞻能力；只允许由对应证据支持。工程通过可交受控预览，不显示“产品/金融全部验证”。所有V23-T/X目前PLANNED，无新增功能PASS。

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

本轮只给架构/验收/交接增加指向本文件的计划入口，不复制55条到多份文档。README、安装、环境示例、前端指南没有实际功能变化，暂不写新按钮/参数。旧ADR和历史验收正文不重写。开工后每批更新本文件日志和实际Current，再按实际UI改变更新用户指南。

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
