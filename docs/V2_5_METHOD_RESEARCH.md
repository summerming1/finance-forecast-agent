# V2.5.0 受控两轴方法研究与反馈更新 唯一实施合同

2026-10-19用户明确批准N0—N5及R1—R4全部修订与训练依赖扰动限定。
批准不是完成；实际状态只见CURRENT_IMPLEMENTATION。分支
feat/mission-research-v2，实施基线c6bdd282dd97952cab37cc64e8edb7f4549cb70f，
tracked clean。保留既有未跟踪证据。ADR007 accepted。

来源：整合提案2.0主稿SHA256
18a329e463d2818dd98cc3eff71d16f49f667848ed155897e063de258377e01c，ZIP
310176118e13e03cd2bf95a7c7a099d543613fededeaacaba06b37cd0b6e8ba7；
本对话审核报告与本次用户直接批准。外部稿不是并行执行合同；历史V2.4及
旧单窗口方向保留历史身份，本版scope以本合同为准。

## 1 范围与不变量

新change_scope=feature_window，profile=spy_feature_window_v1。
SPY/daily/next-session adjusted-close return/forecast_only，原MAE/0.0025与
原四折63目标、purge1、756最小前缀、64共同预热，252共同目标。
新研究候选仅StandardScaler+Ridge，固定有效参数/seed/内置组/处理算法及
uniform权重。原RF/GBDT/朴素对照仍是固定对照，不开放研究模型替换。

沿用FeatureProgram v1的合法AST增/改/删/消融/简化及最大两生成特征，
继承项计入。新增TrainingPolicy v1：expanding或rolling，有限域504/756
来自版本化profile，不散布不可扩展常量。每项从可见、已完成且可比较的
实际control完整复制，只改变declared_axis=features或training_window。
首版parent=control；成绩差/未推荐不影响控制资格。同批未来对象不可引用。
no-op/重复不产生免费槽或新发现。两次规划，每次最多2槽，总4槽；One-shot
一次冻结全计划。原正常28/独特起点32研究fit容量，显式refit额外1次。

不执行权重、HPO、新预处理/模型、任意代码、知识自动接入、Memory学习、
概率/排序、新数据自动更新、动态能力、自动发布或交易。复用唯一Controller、
Queue、RuntimeDB、Evaluator、Memory及MethodCard。P/F/M、内部模型改写、
K1/K2在正式路线保留明确条件包，不从本次批准扩展执行。

## 2 R1 响应与认识更新

新method_research_advice_v1仍是原一次响应。hypotheses保留原动作/四项事前
判断；research_update是每个决定最多一份research_update_v1：items最多2项，
分别绑定上一批proposal_id/design_hash/rule_hash及真实可见evidence_refs，
before/finding/assessment/open_question，外加本决定choice_reason。
assessment为local_support/expectation_not_supported/not_distinguished/
unchanged/execution_incomplete，均是有范围的Advisor陈述，不是数值裁决。
字符串总量上限1200字符，单个自然语言字段240字符，引用最多4项/记录；
原每design合计1000字符、Prompt64000上限保持，不静默删负结果。

新版J第二次规划有可见结果时须更新，包括stop/request_review；第一轮和
One-shot的research_update为null。不要求强制换动作。R/D/Random参考合同
明确不伪造语义更新；同底模同配置的新旧支持比较分别冻结。更新与原advice/
plan一起不可变保存，不新增状态权威、不增加Provider调用；第二批后只有
确定性收尾。非法响应保持原slot/HTTP/录制/恢复语义。旧响应与fixture不改。

已有数值观察、原判断链接复用。actual_feedback_update保留原确定性审计
性质，不机械复制通用文字冒充真实研究认识。权限筛选在投影前；OFF不读新
诊断/观察，不从别臂借用结果；更新引用不能扩大控制资格或改写旧事前内容。

## 3 R2 三种范围与实际训练

comparison/calibration范围：固定共同目标、原split和公共状态校准行。
eligible_train：该折截止已成熟、满足原purge及特征可用性的有序监督行。
selected_train：expanding取全部eligible，rolling取最后恰好W行；不足拒绝，
不缩W/删折/改变共同目标。首版每折拟合一次，预测该折完整63目标。

先在合法原始历史上计算past-only确定性特征，再选择训练行，selected上
fit Scaler/Ridge。窗口之前的合法历史仍可供特征回看，不能先截raw到W。
训练侧方差/冗余/保护事件统计用selected，公共状态校准不随W变化。

拟合入口捕获实际行ID/列序/有效参数/fit次数与计划核对；Manifest包含
eligible及selected身份、数量、截止/成熟依据与处理拟合范围，不能仅抄计划。
第一折expanding与rolling756实际相等应允许相同预测，不改seed制造差异。
扰动测试固定selected，只有修改不参与其特征构造的非训练数据才应不影响
训练矩阵/Scaler；改变合法前置回看依赖可以改变训练特征，不因此判泄漏。

## 4 R3 身份与交付

新候选focused_candidate_v4显式携带完整TrainingPolicy和FeatureProgram；
旧v3/legacy序列化/身份不改。方法身份不含故事/parent；执行仍绑定真实数据、
选择行、seed、代码/环境与合同。比较身份绑定目标/单位/共同切分/评价，
不同方法可比较；观察独立绑定control、方向、规则、分母和形成时点。
缓存按完整方法复用；首次事件与反向结论不能恢复时重分类。

新refit policy先按显式training_asof取同一许可快照成熟eligible，再用最终
TrainingPolicy取selected，按完整特征/顺序/参数拟合。窗口不退回全历史，
特征不重置，实际行/截止/处理范围进可信包。旧all-development策略与包保持。
fresh-process原始无标签推理只transform/predict，无隐式fit或自动数据更新。
浏览候选不改变推荐交付；已有可信包下载不重训；显式其它候选保持原门禁。
续接为新Campaign，保留完整方法/曝光/费用；旧活动任务按原合同，不强改hash。

## 5 R4 比较与预算

语义挑战给参考与新增支持同一冻结上下文；只检验符号/control/反证/理由，
同动作可合理。完整流程同初始资料/权限/工具域/资源，各臂只见自身当时
已接受结果，不能补齐别臂未试结果。参考四项规划与新增认识支持使用同底模/
Provider配置；投影及Prompt同时变化只归因整包。无新语义的参考合同不误拒。
另保留有限顺序/合理随机同域简单策略；全枚举超4槽或fit预算须单列额外成本。
draw、非法/重复、失败、缓存、资源及未知费用均保留，不恢复旧Bug作参考。

研究候选、起点、冻结推荐和最佳可用保持不同角色。未推荐不清空best_research；
失败回退仍失败，没有赢家是合法终态。工程/Live语义/选择价值/独立预测/真人
分轴，不能相互代替。原A/L、36条、47目标负确认不覆盖。

## 6 实施与验收批次

N0：合同/ADR/批准文档、当前基线/权限、新旧schema与范围冻结。
N1：更新与原响应/投影、继续/停止/审核、引用/容量/Replay负例。
N2：完整继承/单轴编译、差控制、未来控制拒绝、累计两特征、旧hash。
N3：真实合成worker、双向路径、三范围/成熟/fit消费、固定分组、缓存与中断。
N4：两个入口、窗口一致refit/可信包/新进程预测、续接/恢复、原UI与推荐隔离。
N5：同域简单策略/语义挑战工程验证、最后功能修改后冻结源/依赖/输入，
全仓及适用worker/browser/static；精确exit和历史缺口，不以JUnit计数冒充通过。

至少包含：特征→窗口；窗口→特征及消融；差候选作control；跨轴丢状态/
越轴拒绝；756相等与504真截取；成熟后取W；原始依赖扰动；selected统计与
固定校准不同；方法别名缓存/观察方向/首次事件；两个入口28/32容量；缺更新/
坏引用/停止更新；最大文本ON/OFF；失败/中断/严格Replay；窗口refit/无标签预测；
取消与只读0增量；推荐交付与浏览分离；旧schema/fixture/确认拒绝保持。

测试使用隔离simulation_only数据/库，允许真实本地fit/predict/refit、worker、
本地模拟HTTP/严格Replay、适用浏览器/静态/全仓。本地仅提交本轮变更，不推送。
不调用新真实Provider/收费/外发、真实行情研究/封存标签、生产迁移、全局权限或
远端CI。缺资源单独NOT_RUN/BLOCKED，不停止无依赖工程。G6已尝试发生问题待本人
复核，不退回从未试用、不代签。最终命令/身份/轨迹/提交在本日志及具名收据。

## 7 批次日志

N0进行中：已核对正式分支及c6bdd28干净tracked工作区，保留旧证据。
本文件是施工合同，不是软件或金融验收。后续逐批写实际结果。
