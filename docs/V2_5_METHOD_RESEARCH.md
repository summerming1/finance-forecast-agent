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

N0完成：3ef2e5c封存唯一合同/ADR007/路线及权限，原状态4测试通过/34.63s/exit0，diff检查通过。
N1基础接口：先新增负例，n1-red.xml因缺新模块1 collection error/exit1；保留。
新增有界版本响应/认识更新验证、原plan冻结挂载点，尚未在新profile执行（N2/N3继续）。
命令`python -m pytest -q tests/test_focused_v25_methods.py tests/test_focused_feature_contract.py tests/test_focused_v24_judgment.py -k 'not no_third and not distinct and not two_' --basetemp=.t25n1r --junitxml=.v250/n1-regression.xml --tb=short`：62 passed/1 deselected/6.87s/exit0；13新合同测试含stop/request_review及旧合同负例。Ruff/compileall/diff均exit0。无Provider或真实行情。

N2：n2-red.xml原9项因尚无training_policy失败，exit1；保留。新增显式v4候选/完整方法身份、单轴control编译与diff，旧v3/legacy序列化未改。`python -m pytest -q tests/test_focused_v25_compile.py tests/test_focused_v25_methods.py tests/test_focused_feature_contract.py tests/test_focused_v24_judgment.py -k 'not no_third' --basetemp=.t25n2 --junitxml=.v250/n2.xml --tb=short`：71通过/1未选/6.00s/exit0。首次Ruff实际exit1（F401未使用预备import、PIE800测试dict写法），前条误记通过在此更正；不影响71项pytest实际exit0。移除预备import并简化测试构造后，Ruff exit0，原71项在n2b.xml再次通过/1未选/5.73s/exit0。diff检查exit0。新profile真实训练尚未接通，N3继续。

N3：接通三范围/成熟后取窗口、实际DataFrame fit/Scaler统计回执、固定公共分组、完整方法缓存与独立观察。n3-red.xml两项原不支持scope失败/exit1；n3a.xml双向实际训练2通过/58.12s/exit0；n3b.xml新合同/编译/执行及V2.4诊断/准入55通过、2未选/58.34s/exit0。n3c.xml固定selected的无依赖扰动与合法历史回看、成熟先于窗口2通过/9.14s/exit0。实际24研究fit、2规划、HTTP0；同最终方法预测复用而控制观察不同，完成后恢复不再规划。Ruff首次3项格式问题及补测2项import排序失败均保留并修复，无历史fixture更改。N4交付/工作区待贯通。

N4阶段验证：n4.xml首次2通过/2失败/21.64s/exit1，失败为新测试脚本错误（不存在的submit动作、不完整FeatureProgram），保留并修正。n4b.xml两个原入口/窗口refit4通过/173.86s/exit0。n4c.xml扩大为真实worker+续接+研究包、带特征窗口包、新进程预测及旧包/原价格UI回归20通过/355.58s/exit0。新scope接入原UI/worker/Mission，续接完整保留窗口及特征；refit v4按成熟标签及最终窗口选行，旧v2/v3保持旧语义。已保存原始失败，未碰用户生产库。随后实际入口审查新增Scaler算法负例fit-red.xml（2失败/exit1），已加显式类型/参数及每折参数回执检查，正在N5重跑。原J0—G6及47目标负确认不因此签收。
静态扩大检查：全仓Ruff实际97错误/52文件/exit1，全部位于本轮未修改文件，原始txt/json在.v250；不作全仓lint通过。定向修改文件Ruff、Python编译、三个前端JS node --check、diff检查均已实际exit0。最终冻结后复核。

N4贯通后N5首轮：n5a.xml 35通过/602.44s/exit0，包括实际Scaler算法拒绝、双向/累计两特征/消融、停止/待审核的实际更新、同域有限简单顺序、本地HTTP四项参考/认识更新两臂各2次请求及严格离线Replay、实际进程kill与28fit恢复（原失败计费），不是Live质量。browser-stage.xml Chromium 1通过/382.42s/exit0，含模型包/研究包、浏览不改推荐、700/1280布局、刷新/新上下文、续接/原父不变，页错误0；但人工核图发现新窗口对比被旧训练范围等式错误阻断。comparison-red.xml两项真实失败/8.77s/exit1：同目标窗口不可比、参考臂省略新语义字段被拒绝。两项继续在N5修复，不据上述绿灯宣布最终验收。


## 8 实际API、操作及解释边界

唯一新profile为 `change_scope="feature_window"`，新候选 `focused_candidate_v4`。
`TrainingPolicy` 的两个精确字段为 `mode`、`sessions`：
`{"mode":"expanding","sessions":null}` 或 `{"mode":"rolling","sessions":504}` / 756。
特征操作声明 `declared_axis="features"`；窗口操作声明 `declared_axis="training_window"`。
各训练项明确给出相同的已接受 `parent_candidate_id` / `control_candidate_id`。
前者提交完整继承的FeatureProgram（或合法ablate/simplify操作），后者只提交新TrainingPolicy。
模型/参数/seed/内置组固定；不把窗口缩短引起的Scaler统计及Ridge有效正则环境变化
误说成已经识别的单独因果机制；只能评价这项整体窗口方法。

新响应 `method_research_advice_v1` 包含 `hypotheses` 和 `research_update`。
第一轮/One-shot为null，第二轮update-J必须给有界对象；四项风格参考及R/D/Random
可省略这个新语义字段，编译为同一个null含义，不能因缺新语义误拒合法参考。
原规则正文和hash随原decision链接投影；OFF只获得原事前规则及允许的旧结果/执行失败，
不获得新诊断观察。执行失败引用原RuntimeDB failure记录的安全事实，不是候选结果权限，
更新必须execution_incomplete；不能冒充科学负面结论、控制或缓存成功。
同方法旧尝试失败但无接受预测时标skipped_failed_execution，仍为不完整研究。

原Benchmark新增可选参数 `method_profile="spy_feature_window_v1"`、
`feedback_support="reference"|"update"`；旧调用保持。示例：
`run_benchmark_arm(frame,dataset,raw_history=raw,project_dir=isolated_dir,arm="adaptive_batch",
spec=BenchmarkSpec(candidate_budget=4,batch_size=2),method_profile="spy_feature_window_v1",
feedback_support="update",context_mode="compact_v1")`。
用三个独立目录分别运行reference/update以及arm=random的有限同域简单策略。
复用原Controller、登记、报告和summary，不新增规划/评价权威。共同28fit上限、同源同环境、
同资料/工具域/冷历史；简单策略只检查预登记的四项方法，逐决定记录draw及重复，不暗中全枚举。
Provider配置不同的参考/更新报告拒绝汇总。模拟/规则结果不升级成真实LLM理解或选择价值。

原工作区：启动 `.\.venv\Scripts\python.exe -m streamlit run apps/streamlit_app.py`，
新建研究选择“V2.5 特征＋训练窗口”，加载已许可原始价格JSON及来源元数据。
本轮证据只用simulation_only；真实研究未获本轮授权，不自动开始。
“没有现成模型”及“已有模型配置”均复用原入口；新profile研究起点仅Ridge。
默认两轮四槽/最多32研究fit；One-shot与有限简单策略显式选择，不把预算当完成量。
结果页读实际单轴改动、控制、MAE分母和第二轮已冻结认识更新；详情查看实际selected/eligible
与Scaler/模型fit回执。成果页默认交付冻结推荐，不因浏览其它候选而换对象。
显式生成模型包另拟合一次，v4模型包遵循最终窗口与全部特征；已有包下载及无标签推理不重训。
继续研究创建新Campaign，保留完整方法及原曝光/信任边界，原Campaign不修改。

N5增量日志：comparison-red两项已修，n5c.xml 21通过/168.45s/exit0；n5b误用不存在测试路径，
exit4/no tests，不能算通过。benchmark-red.xml原无新profile入口1失败/6.61s/exit1，保留。
后续完整身份筛重时错误复用了起点派生hash，n5d.xml 28通过/4失败/311.73s/exit1，
browser-comparison.xml因此在等完成时失败/183.27s/exit1；已修为从完整原始方法重新计算身份。
failure-red.xml 1失败/45.88s/exit1，确认混合失败未进入认识更新；已接入原failure事实及失败缓存拒绝。
n5e.xml 27通过/498.82s/exit0，包含混合真实fit失败、最大文本ON/OFF、三臂原Benchmark。
browser-verified.xml已通过窗口比较/包/零增量浏览，但新context恢复默认5秒就绪等待超时，
1失败/225.88s/exit1；server无异常。仅改就绪等待为与启动一致的30秒，状态、资源和交付断言不改。
最终冻结/全仓及浏览器结果尚待后续实际运行，不以本段阶段测试替代。

最终首冻728e14f/238文件：browser-final.xml四模式2通过/2失败/785.82s/exit1，旧price preflight及v25续接dialog均在异步iframe挂载后的默认5秒断言超时，原内容/资源断言不改。现统一该测试就绪预算30秒并重新冻结。full-final2首跑因测试源码将改变主动中断，实际exit15，非完整回归；原stdout/start及full-interruption.json保留，不以其中已运行用例代替完整验收。完整适用集合为939/941，2项真实股票harness重训按本轮权限单列NOT_RUN，不改原测试。为减少等待，下一次按原测试文件分片隔离执行，同一冻结源码/依赖，逐条核对939个收集node与实际JUnit案例/exit；不是抽样定向验收。

N5容量修订（真实失败保留）：第二次冻结2aeddb1/源码hash
6be0285ad2769166ef91b0321b27ee2bea9b810ac15a22f0387f3c8f9a921f25，完整适用939项
实际928通过/4失败/7跳过，四分片exit=1,0,1,1；不是全绿。两项旧缺资产/Windows权限，
两项新worker在并行负载超过原120秒等待，随后同源码/原120秒条件隔离2通过/225.59s/exit0。
原分片失败不覆盖。原集合核对器错误替换参数中的Unicode转义，保留原aggregate，另据原始
收集及JUnit仅规范文件名重新逐条核对939项无遗漏/额外/重复，coverage_reconciliation.json。
全四模式浏览器3通过/1失败/591.76s/exit1：新v25带特征续接第二轮真实超过64000上下文，
不是等待问题。该浏览器仅有start身份，修复前未写end身份，不追填伪造冻结结束收据。
原全仓、浏览器、模型轨迹及失败均留在.v250/final3，不能冒充后续源码验收。

新增版本化compact_method_context_v1/compact_json_v1：容量按实际Provider prompt JSON
计算，旧profile的默认JSON字节保持原样。method_reference_projection_v1只共享相同的原规则
及已完整展示候选的方法值，不删数值、负例或原理由；带原始投影hash及可验证的逆变换。
引用在权限筛选及原紧凑上下文构造后产生，引用不扩大可见范围。不是新增记忆/事实权威，
没有额外LLM调用，没有放宽64000。context-final.xml阶段28通过/557.62s/exit0，含本地HTTP/
严格Replay/kill恢复；随后逆变换位置修订及真实wire/篡改负例，context-last.xml20通过/
91.33s/exit0。最长备注/带特征续接的原始红例和首次ON失败仍保留。最终源码需再冻结回归。
更正早期n5b：外层执行返回exit1，错误pytest路径未运行测试；pytest内部独立exit未捕获，
前段写exit4不作为精确收据。其他逐次pytest结果以原XML及实际执行返回为准。

N5第二次容量修订：结构压力只作探测，不直接叫Bug；随后隔离实际15节点AST/4000备注/
1000设计在第二轮真实失败，max-ast-probe与max-ast-red.xml保留（1失败/1通过/2未选，
84.48s/exit1）。当时final4两分片完整回归尚未完成，按实际owner PID/birth中断以修功能，
外层exit1；未捕获的各分片exit不推测，原stdout/start、full-interruption.json保留，
不将途中通过冒充完整回归。final4四模式浏览器4通过/74检查/无页错误属于当时源码，
后续源码验收必须重新运行。

首次特征定义去重max-ast-fix.xml38通过/1失败/694.19s/exit1；只共享表达式的
max-ast-last.xml22通过/1失败/166.54s/exit1，均仍在最大ON组合触及64000，保留。
最终compact_method_context_v3 / method_reference_projection_v3在同一只读投影共享
重复规则、AST和程序元数据，特征名/位置保留，差异值可引用已展示的完整方法组件。
以原始投影hash验证逆变换、幂等与篡改检出；内部规划/编译先恢复，提交AST不允许引用
标记，真实候选/制品/模型不采用展示格式。旧wire/fixture不改，无新权威/调用/数值裁决。
真实失败上下文重投影63691字符；max-ast-header.xml24通过/168.00s/exit0（最长组合
普通/15节点AST各ON/OFF、原wire、实际loopback HTTP、完整逆变换与非法DSL负例）。
整体上限64000仍保留；不承诺任意附加资料和全部合法字段的笛卡尔积都能容纳，超限
仍显式拒绝，不能静默删事实/负例。新一轮最终源码/依赖/输入绑定及适用回归在final5，
未结束前本段不是最终验收。


## 9 最终实施、验收与交接报告（2026-10-19）

结论：N0—N5在本次授权的隔离合成工程范围内收口；R1—R4已进入实际代码、原工作区和交付。
完整适用回归为939通过、2历史失败、7跳过，actual exit1，**不是全仓全绿**。
59个不同的V2.5测试用例全部通过，没有靠隔离重测覆盖本次完整回归失败。
最终四模式Chromium4通过/550.37s/exit0（17+17+20+20=74项检查、页错误0）；
同源码本地HTTP/严格Replay/kill恢复3通过/269.28s/exit0；双轨迹交付驱动exit0。
原试用G6已尝试有问题待本人复核，不能由本报告代签。

### 9.1 批次与修订映射

| 批次/修订 | 已实现内容 | 关键位置与验证 |
|---|---|---|
| N0 | 唯一V2.5合同、ADR007、当前必读顺序、两轴正式路线；外部稿只为来源 | 本文§1—§8、AGENTS、PROJECT_ROADMAP、ADR007；不改V24历史及A/L |
| N1 / R1 | method_research_advice_v1同次响应的research_update；原命题/规则/可见结果绑定；第二轮继续/停止/待审核，首次及One-shot为null | focused_methods.validate_research_update、focused_research._bind_research_design；methods/acceptance/recovery测试 |
| N2 | v4完整方法身份；parent=control；特征/窗口单轴diff；继承窗口/全部特征，累计最多2条；差成绩控制合法 | focused_research.CandidateConfig、compile_hypotheses；compile/acceptance测试 |
| N3 / R2 | 固定comparison/calibration、成熟eligible、policy-selected三范围；每折一次拟合/63目标；入口捕获实际行/列/参数/Scaler统计 | focused_methods.training_scopes/fit_method、focused_research.evaluate_candidate、focused_diagnostics；execution测试含756与历史依赖扰动 |
| N3 / 身份 | 完整方法缓存，预测与比较/观察身份分开；相同最终方法复用，方向/分母/时点各自保存；失败不当成功 | focused_research._observe_research、原RuntimeDB及缓存；双路径、失败/恢复测试 |
| N4 / R3 | 原两个入口/worker/续接/研究包；同一许可快照、显式 training_asof 下的窗口refit、原完整特征及真实行身份；v4可信包/新进程无标签推理；旧包语义保留 | focused_delivery.refit_model_bundle/predict_model_bundle、research_mission、原UI service；delivery及浏览器 |
| N5 / R4 | 原Benchmark适配器的四项风格参考/认识更新/同域有限简单策略；同配置/权限/预算，各臂仅用自身结果；同目标不同窗口可比 | focused_benchmark、focused_summary；benchmark/comparison/recovery测试；不是实际LLM价值结果 |
| N5 / 容量 | compact_method_context_v3、可逆method_reference_projection_v3、实际wire计量；规则/AST/程序元数据共享，特征名不变；提交引用标记仍拒绝 | focused_methods.project_method_references/restore_method_references、focused_literature、llm_adapters；原始失败全部保留，最大AST/备注/设计ON/OFF在最终59项中通过 |

R1认识更新与事前feedback_update、确定性actual_feedback_update职责不同，不互相代替。
引用有效不代表因果解释正确；支持包提供更新入口，不声称真实LLM已经会研究。
研究参数/seed/内置组/处理算法在研究起点冻结，实验不搜索；504/756只是本版有限域。
不强迫换轴/用满槽/找到赢家。窗口与Scaler/正则环境联动，只解释整体方法结果。

### 9.2 最终源码、依赖、输入与命令

测试源码提交：`b10c49562124d8fdb7ea49001d83559f9092d79b`，分支`feat/mission-research-v2`。
238个执行/测试文件集合摘要（v25-tested-source-files-v1）：
`fc37b33ec3bbad6561715418790d6829b68875b0e43bae7161fbe6be464d1598`。
Python3.13.3；核心依赖与完整已安装distribution版本见机器收据。
全回归环境start/end/current版本一致；各执行收据的声明输入、源码、核心依赖及JUnit
开始/结束/当前三方匹配。输入包括pyproject、声明的simulation_only JSON/来源与驱动；
临时生成数据由冻结的测试生成器复现，各Campaign另存raw SHA/实际训练行身份。
这不是连续磁盘监控、wheel字节审计或封存标签检查。辅助fixture Git元数据不冒充运行前字节快照。

在仓库根目录，先设置`$env:PYTHONPATH='src;tests;apps;scripts'`。最终实际命令：

```powershell
.venv/Scripts/python.exe .v250/run_browser_v3.py
.venv/Scripts/python.exe -m pytest -q tests/test_focused_v25_recovery.py --basetemp=.t25recover5 --junitxml=.v250/final5/recovery-pre.xml --tb=short
.venv/Scripts/python.exe .v250/run_frozen_regression_v3.py --root .v250/final5 --basetemp-prefix .t25s5 --shards 4
.venv/Scripts/python.exe .v250/deliver_trace_models_v3.py --root .v250/final5/trace-delivery --manifest .v250/final5/preregistration.json --case-prefix '.t25s5*'
.venv/Scripts/python.exe .v250/static_final_v3.py
```

以上按列表exit依次0、0、1、0、0（最后一项是静态收集驱动结束；子检查exit逐项如下）。
四分片真实pytest argv与required集合完整记录在`.v250/final5/preregistration.json`，
每片start/end和stdout/JUnit都保存；分片exit依次1/0/1/0，案例数234/233/234/247。
收集950项，以下两项真实股票训练未授权，明确deselect后适用948项：
`test_models_and_harness::test_harness_runs_real_data`、
`test_methodcard_p0_pipeline::test_methodcard_derived_paperspec_runs_p0_harness`。
948个JUnit案例与收集node逐条一致：missing=[]、extra=[]、duplicate_count=0。
7个跳过包含4个显式浏览器opt-in（已在同源另跑4通过）与3个平台/原条件跳过，逐项原因见机器收据。

静态：本轮受管修改文件Ruff、Python compileall、三份修改JS的node --check、git diff --check均exit0。
`ruff check src apps scripts tests`实际exit1：97项/52个既有未修改文件，当前修改文件命中0。
`ruff check .`在完整回归前138项、后140项，额外包含保留的临时历史证据、本轮验收辅助脚本及
新生成探针的样式问题，不声称工作区全量lint通过，也不为求绿修改已哈希的冻结验收脚本。
精确分类见`.v250/final5/lint_scope_review.json`与原始输出。

两项完整回归失败均保留：
1. `tests/test_p1_real_validation_artifacts.py::test_dlinear_strict_live_card_replays_without_an_api_call`：原`2c05bfd22af27435.json`匹配fixture缺失，BLOCKED_ASSET；未造新fixture替代。
2. `tests/test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink]`：Windows创建symlink的WinError1314，尚未进入加载，BLOCKED_ENV；未改全局权限。

本次完整回归没有两个新入口的120秒等待失败；旧final3并行等待失败/隔离通过、final4未完成中断、
最大上下文数次原始红例仍是历史原貌，不能拿旧通过替代本次证据。最终机器收据：
[受管副本](validation/v25_local_acceptance.json)，完整原始目录`.v250/final5`。

### 9.3 可复现轨迹与完整模型交付

轨迹A：`baseline_ridge`→特征`r1_c1_3cfadc9f`（expanding）→窗口
`r2_c1_c1ffd8a2`（rolling504，保留gen_mean）。另一分支先得窗口
`r1_c2_e43b290d`再加同特征，`r2_c2_93670e2a`复用前者预测；各自控制、观察与时点不合并。

轨迹B：已有rolling504的`user_start`→两生成特征`r1_c1_fa01e116`→消融
`r2_c1_d276ae71`（仅移除gen_mean，保留gen_second和rolling504）。未推荐的父候选仍合法作control。
两轨迹均第一轮无认识更新、第二轮有绑定真实可见结果的更新，2次规划、外部HTTP0，研究fit各24。
原冻结推荐分别仍是baseline_ridge和user_start，未因浏览或演示交付而改写。

| 演示 | 显式交付对象 | selected训练行 | 保留特征 | 新进程输出逐值一致 | 另计refit |
|---|---|---:|---|---:|---:|
| feature→window | r2_c1_c1ffd8a2 | 504 | gen_mean | 1094行，exit0 | 1 |
| window→feature→ablate | r2_c1_d276ae71 | 504 | gen_second | 1080行，exit0 | 1 |

这是**显式其他已接受候选**交付演示，绝不是把它们偷偷改成推荐或金融赢家；推荐包默认交付另由原工作区测试验证。
每条研究包9份预测制品完成审计；真实asof、列序/有效参数、实际fit入口及行哈希均在完整模型metadata。
两份模型ZIP与完整控制/反馈/观察/推荐在`.v250/final5/trace-delivery/receipt.json`及同目录。
上述两次额外fit独立计费；其他单元/worker/browser测试各有自己的隔离计数，不混成一个Campaign预算。
同快照显式refit与无标签predict已验证，不包含新数据自动更新或跨机信任迁移。

复现实验使用两个原测试：`test_focused_v25_execution.py::test_both_axis_paths_reuse_same_final_method_but_keep_distinct_observations`
和`test_focused_v25_acceptance.py::test_window_to_two_cumulative_features_then_ablate_poor_accepted_control`。
必须使用新的basetemp；交付驱动支持`--root`、`--manifest`、`--case-prefix`，可选择新输出目录，拒绝覆盖原证据。
原实际驱动命令与输入hash见trace-delivery/start.json；重新生成模型是新的显式refit，不当作免费复用。

### 9.4 使用、迁移、未测边界与G门

启动`.venv/Scripts/python.exe -m streamlit run apps/streamlit_app.py`。
选V2.5特征＋窗口范围，原“没有现成模型”和“已有模型配置”两入口均可用；本轮只验证合成输入。
先预检再确认执行；研究页看真实control/单轴diff/第二轮认识更新；详情核对eligible/selected和实际回执。
成果页默认交付冻结推荐；浏览不会换包。其他候选需显式选择并核对ID；生成新包额外1fit，已有包下载不fit。
继续研究是新Campaign，继承完整窗口及特征；无标签推理只transform/predict。原活动需原源码/依赖绑定，
不改旧hash迁移；旧v2/v3包保留语义。本次无生产DB迁移、依赖新增或新平台。

| 门/证据轴 | 本轮状态 |
|---|---|
| G0 研究合同/判断 | 新范围单元/集成通过；原J红例和行为历史保留 |
| G1 软件/源输入绑定 | 限定工程GO；全仓实际PARTIAL，2历史阻塞+全量lint问题不伪装绿灯 |
| G2 真实开发输入与两入口 | 旧所有者授权真实输入历史不改；新V2.5两入口合成实际fit通过，真实行情研究本轮NOT_RUN |
| G3 包复算/可信推理/只读 | 本轮合成研究包/同主机新进程通过；不等于跨机任意模型导入 |
| G4 主持/操作准备 | 原指南已同步新范围；不是本人操作签收 |
| G5 Agent模式 | 规则/本地模拟HTTP/严格Replay工程通过；真实LLM理解与等预算选择价值未验证 |
| G6 本人/用户 | 已尝试有问题，待本人复核；独立目标用户未签收，不退回“从未试用” |

结论分开：工程完成（限定合成与受支持本机路径）；真实LLM理解NOT_RUN；研究选择价值
NOT_ESTABLISHED；独立预测效果NOT_RUN。目标用户邀请不由AI代签，仍按原G6复核条件；
不是因缺无关旧资产而阻止其它获准工程。P/F/M、受控内部改写、K1/K2、权重/参数、V2.6/V3等
仅保留PROJECT_ROADMAP顶部的具体条件包，本轮不执行。没有付费/真实Provider、外发、封存标签、
真实市场研究、生产迁移、全局权限修改、推送或远端CI。原A/L、47目标负确认和科学失败不关闭。

### 9.5 本地提交与收口

以下为本轮实现提交；最终文档/收据以仅文档提交收口（哈希见git log及交付回复）。全部本地，无推送，执行源保持上述238文件摘要。

```text
3ef2e5c docs(v25): freeze approved two-axis research contract and gates
6378e44 feat(v25): bind bounded research updates to versioned advice and plans
5046c85 feat(v25): compile versioned complete methods with one-axis controls
ee860ce fix(v25): clear N2 static checks and correct staged validation log
33686fd feat(v25): execute selected training windows and preserve comparison observations
e9fd06c feat(v25): connect window-aware refit bundles workspace and continuation
728e14f feat(v25): close failure feedback comparison and fair benchmark gates
2aeddb1 test(v25): synchronize all workspace assertions with component readiness
961eb8c fix(v25): preserve bounded lossless context for feature-bearing continuation
b10c495 fix(v25): losslessly project complex feature contexts within the frozen budget
```

源码测试后仅同步文档和受管收据；文档状态回归结果另存`.v250/final5/docs-check.xml`，
最终再次核对源文件摘要不变。原所有未跟踪证据和用户文件保留，不清理回滚。

文档收口实际结果：`pytest -q tests/test_focused_r0_status.py tests/test_focused_b0_plan.py --basetemp=.t25doc5 --junitxml=.v250/final5/docs-check.xml --tb=short`，4通过/2.18s/exit0；所读AGENTS/README/路线/CURRENT/handoff在开始/结束绑定。执行/测试238文件集合摘要仍为fc37b33e…d1598，无功能修改。

## 10 文档一致性与发布状态同步（2026-10-20）

用户要求核对并正确更新供后续Codex使用的功能/路线文件。核对基线为正式分支
`feat/mission-research-v2`、HEAD `4f8b2c65d281de3171f7e1ccf7e10a446f3038c5`；
tracked工作区干净，原未跟踪数据/运行证据保留。V2.5主体文档此前已更新；本次只补
仍将V2.4标为当前的README/交接/指南标题、旧读序、当前与历史指令优先级、下一步和发布状态，
不改产品范围、代码、ADR accepted状态、历史科学证据或旧验收JSON。

同步位置：AGENTS、README、PROJECT_ROADMAP、CURRENT_IMPLEMENTATION、
CODEX_FOCUSED_HANDOFF、CODEX_V22R_REMAINING_VALIDATION、FOCUSED_ARCHITECTURE、
FOCUSED_ACCEPTANCE_TEST_PLAN、FRONTEND_USER_GUIDE及本文。AGENT_WORKSPACE_UI与ADR007
已核对，原功能/操作和批准边界无需另改。P/F/M、内部受控模型改写、K1/K2等明确条件性位置
保留，不自动实施。N0—N5限定工程已完成；G6已尝试有问题待本人复核，不退回未尝试，
也不以合成两轴演示代签真人/真实LLM/研究选择或独立预测效果。

发布勘误为追加记录，不回填§9或原机器收据：用户后续明确批准“全部提交并且推送”，
2026-10-20普通push将`c6bdd28..4f8b2c6`的11个实现/文档提交同步至远端；
`git ls-remote origin refs/heads/feat/mission-research-v2`返回完整4f8b2c6 SHA，
本地/远端领先落后为0/0，push exit0。该动作不是远端CI验收；本地原始数据、数据库、
模型及运行证据目录未上传。后续本次文档提交身份以实际git log为准，不冒充b10c495测试执行源。

本次实际检查：设置`PYTHONPATH=src;tests;apps;scripts`后执行
`.venv/Scripts/python.exe -m pytest -q tests/test_focused_r0_status.py tests/test_focused_b0_plan.py --basetemp=.v250/docs-sync-20261020-090745/temp --junitxml=.v250/docs-sync-20261020-090745/docs-check.xml --tb=short`，
4通过/3.02s/exit0。另核对10份修改仅为MD、原238个执行/测试文件逐文件SHA256匹配
final5预登记、6份历史/验收/已正确指南及ADR受保护文件无差异、53处相对MD/JSON链接有效，
检查exit0；`git diff --check` exit0。检查索引在
`.v250/docs-sync-20261020-090745/document_check.json`；提交前再次核对源码和diff。
完整948项回归、四模式浏览器与模型交付本次不重跑，仍按§9准确引用；
不把旧2失败/7跳过改成全绿，不更新原机器验收收据或伪造新金融/Provider/真人证据。

## 11 2026-10-20 定向修补（限定工程完成；以下过程记录按时序保留）

本轮基线3f45a3e514d819f32ec9d4fe9461334afd852e8d、正式分支、tracked clean。
不重开N0—N5、不扩路线；保留原B、额外refit、旧fixture/包/hash及全部失败。
授权只用于隔离合成工程、真实本地worker/HTTP/Replay/browser及本地提交；
不新增外部Provider/付费、真实行情研究、标签读取、生产迁移或远端CI。

1. 通信：单一线程一次communicate完整输入，主线程轮询取消/deadline；
   终止后有界wait/join，不用第二次communicate清理，不以清理失败掩盖原错误。
   正常瞬态HTTP重试及跨进程未知投递禁重发语义不变；未知费用仍null。
2. 快速入口：One-shot一次规划、最多四槽、原执行单元两项；Adaptive两次规划。
   不放宽核心门禁，不允许同计划未来控制；范围下拉仅一个selected。
3. refit：只补最终候选窗口及快照/selected区别、明确额外成本；不新增精确预览状态。
   实际asof/行数仍来自原执行回执；提交前取消零fit，提交后不保证零消耗。
   原operation幂等及失败/未知留账保留；不禁止有明确新授权的新refit。
4. Benchmark：原最佳研究候选和旧mae_delta含义保留；只读验证原冻结推荐、
   自身Campaign/合同/数据/政策/上下文/已接受结果/预测及目标身份，不重新选择。
   新delivery_comparisons两种绝对差均为左MAE减右MAE、收益率小数单位、负数左优。
   各臂相对自身起点的原gain为另一比例；不同臂不要求execution/hash相等。
   仅完整且可比的推荐进入成对推荐比较，旧缺记录不补算，损坏明确报错，
   failed/partial回退可保留展示但不构成成功对照，无研究候选仍保持研究指标null。

负例与分批原始证据置于`.v25fix/`，不覆盖`.review25-20261020`或`.v250/final5`。
red-io.xml四失败、red-default.xml入口/DOM失败、red-rec.xml九失败均保留。
transport-defaults.xml：26通过/114.77s/exit0（本地模拟HTTP、提供者回归、默认预检、
确认框；不含之后新增测试）。default-worker.xml：17通过/90.90s/exit0。
Windows3.13.3/WSL Linux3.10.12真实子进程屏障测试各success/cancel/deadline通过，
HTTP/fit0；这是通信专项，不是Linux全项目验收。受限沙箱第一次loopback失败保留，
允许本机loopback后重跑；未放宽生产timeout或断言。最终冻结回归及浏览器待后续记录。

历史包兼容边界：保留旧schema语义不等于历史实物包可以在任意当前源码加载。
原B的v3编译源字节绑定历史环境，当前源不匹配仍拒绝；不得改hash或重训替代。
匹配环境实际加载未验证，不把只读历史源码比对当加载PASS。

后续实测追加：last-targeted.xml39通过/194.84s/exit0；原新旧Benchmark相关
recommendation.xml37通过/1167.83s/exit0，均为阶段证据。第一次冻结浏览器
final/browser.xml4通过/886.75s/exit0，原74项流程检查、页面错误0，已检查确认框
与700宽成果截图。随后新增零fit/HTTP探针复现：推荐已冻结但后续导出报错时，
新汇总错误拒绝整个失败臂。red-post-final.xml1失败/5.74s/exit1保留；最小修订为
保留原冻结状态，显式执行错误仍是failed、paired_eligible=false，不能进入成功比较；
没有重写原推荐或免费重算。post-final-green.xml6通过/5.94s/exit0。
第一次完整回归尚未结束，按精确PID/birth终止本轮专属测试树以修复此缺口，
外层exit1、未完成，不推测各分片exit。原stdout/start及interruption.json保留。
此后最终验收使用final2新目录，不能把final的浏览器/中途通过冒充修订后同源收口。

历史B实物核验追加：原登记库以SQLite只读连接查询，原验证器仍检查登记hash、
依赖版本、模型/metadata字节及五个编译文件；不创建替代信任库、不更改登记。
当前源码拒绝三份旧包（编译实现不匹配）。隔离归档c6bdd28、恢复记录时的原换行
字节后，三份编译源和已登记依赖精确匹配，分别在新进程中实际可信加载并对明确
模拟的无标签输入两次预测，233/247/233行逐值一致、fit/HTTP0，原DB hash不变。
这是历史编译/依赖匹配的有限实物推理，不是整个历史OS重建或金融表现。
最初换行不符的BLOCKED与处理记录另存，不把初次失败擦去；未修改旧包hash。

第二次冻结final2：四模式浏览器4通过/617.54s/exit0；推荐专项22通过/62.23s/exit0，
含实际_report后置导出错误路径。随后事件延迟对抗发现新测试脚本仅在第三次轮询
释放子进程，晚就绪可误报deadline。该问题仅在测试屏障，不是新增产品故障；
旧脚本与final2开始清单SHA256 `c1d7eb1f…2e6f838`完全一致的副本已保存，
原事件延迟负例再次真实exit1、HTTP/fit0，日志late-old-red.stdout.txt保留。
最小测试修订为实际就绪后只释放一次，增加第四次才就绪负例，产品deadline不变。
final2完整回归未结束，按本轮精确PID/birth终止，外层exit1、不推测分片exit；
原始目录及第二份interruption.json保留，不用中途结果交付。

最终final3冻结242源码/测试文件，集合摘要
`d5fdf1cfc5398d0e5abda9202584299b2021ee41442f2f2e6e23ebb0add8849f`。
四模式Chromium4通过/547.24s/exit0；修订管道11通过/8.42s/exit0；
Windows/WSL Linux实际子进程专项各3条通过（stdlib实际方法，不是Linux全项目），
HTTP/fit0。修改文件Ruff、compileall、修改JS语法、diff检查exit0；全目录Ruff
仍97项/52个未修改文件/exit1。最终完整适用回归正在执行，后续只追加事实收据。

### 11.1 最终冻结回归事实（2026-10-20）

final3完整回归已结束：**979 passed / 2 failed / 7 skipped，actual exit1**；
不是全仓全绿。收集990项，按原权限明确排除2项真实股票重训后适用988项；
实际988个JUnit节点与预登记逐条一致，missing/extra均空、重复0。
四分片依次229/185/334/240项，exit1/0/1/0；其中新增40个修补用例与原59个
V2.5用例全部通过，均已包含在979内，不把重复阶段测试相加。
并行运行起止收据包络3997.73秒（不是把四个分片时长相加当墙钟）。
242文件摘要仍为上面的d5fdf1cf…8849f，开始/结束/收据收集时一致；声明输入、
核心依赖及完整installed-distribution版本前后相同，环境版本摘要
`0fabb551aa7cb50f542cba6ea1f28402410de06bcd41859e74a3745f01d3e09d`。
本机Python3.13.3、Windows11 build26200、12逻辑CPU。原始收据
`.v25fix/final3/receipt.json`保存实际命令、JUnit/清单hash、覆盖、失败与平台边界。

实际执行（仓库根目录；先设`PYTHONPATH=src;tests;apps;scripts`）：

```powershell
.venv/Scripts/python.exe .v25fix/run_browser.py .v25fix/final3 .t25bfix3
.venv/Scripts/python.exe -m pytest -q tests/test_provider_pipe_ownership.py --junitxml=.v25fix/final3/pipe.xml --tb=short
.venv/Scripts/python.exe .v25fix/run_platform.py .v25fix/final3/platform.json
.venv/Scripts/python.exe .v25fix/run_static.py .v25fix/final3
.venv/Scripts/python.exe .v25fix/run_final_regression.py .v25fix/final3 .t25fix3s
.venv/Scripts/python.exe .v25fix/collect_receipt.py
```

上述exit依次0/0/0/0/1/0；静态驱动的broad-Ruff子命令exit1单列，不称全部lint通过。
回归实际调用原`.v250/run_frozen_regression_v3.py --root .v25fix/final3/regression --basetemp-prefix .t25fix3s --shards 4`，
每片pytest完整argv在preregistration.json和机器索引中。无需调度包装器时，可以
`python -m pytest -q --deselect=tests/test_models_and_harness.py::test_harness_runs_real_data --deselect=tests/test_methodcard_p0_pipeline.py::test_methodcard_derived_paperspec_runs_p0_harness`
复现同一适用集合；这是新的运行，须用新输出目录，不能覆盖本次证据。

原失败逐项：

| nodeid | 首个异常及归属 | 处理/恢复 |
|---|---|---|
| test_p1_real_validation_artifacts.py::test_dlinear_strict_live_card_replays_without_an_api_call | FileNotFoundError：原method_card/2c05bfd22af27435.json缺失，BLOCKED_ASSET；非本轮引入 | 恢复匹配原录制、原上下文和来源；不能改名或合成替代 |
| test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink] | 测试创建链接时WinError1314，尚未到反序列化，BLOCKED_ENV；非本轮引入 | 由所有者另行批准提供symlink权限环境，或在已获准适用平台验证；不删断言或更改全局权限 |

7个跳过的实际构成为**5个opt-in浏览器**（原Research Workspace一项＋Agent四模式），
以及POSIX进程组probe、Windows package symlink权限各一项，不沿用旧收据的不同分组说法。
Agent四模式已在同一最终冻结源码独立4通过/547.24s，74项检查、页面错误0。
原Research Workspace另补实际浏览器：首跑在初始标题的默认5秒expect就绪处失败、
页面仍Running、未提交训练，12.20s/exit1；原文件与5秒门槛均未修改，同源码复跑
1通过/146.40s/exit0，完成原完整流程。首跑不改绿，冷启动就绪稳定性风险仍保留，
不能把复跑通过当作从未失败。两项平台条件跳过继续保留。

四个Agent模式的原始计数（每行含本模式父/续接的独立Campaign，不能当成单Campaign预算）：

| 模式 | attempts / 研究fits | 显式refits | 检查 / JS错误 |
|---|---:|---:|---:|
| legacy配置 | 15 / 36 | 1 | 17 / 0 |
| price_features | 16 / 40 | 1 | 17 / 0 |
| V2.4 | 18 / 48 | 2 | 20 / 0 |
| V2.5 | 19 / 52 | 2 | 20 / 0 |

One-shot快速入口真实隔离worker另记录1次规划、4冻结槽、4候选、28研究fits、
外部HTTP0（default-worker.xml）；32是预算上限，不硬改执行结果配旧计数。
包索引/预测复算、实际refit/可信包、刷新/new context/只读零增量、续接保留原父均有
上述模拟技术证据；不是所有者G6签字、Live质量或金融增量。

### 11.2 本批交付结论

通信、默认入口、范围选择、窗口refit告知及冻结推荐报告五项限定修补工程完成；
源/测试冻结后完整适用回归已结束，不重开N0—N5。机器索引见
[v25_repair_acceptance.json](validation/v25_repair_acceptance.json)，包含准确命令、退出码、JUnit及身份。
测试执行时HEAD为3f45a3e及其工作区改动；后续代码提交只封存这组已测字节，不能倒称测试在新提交上启动。
本批本地提交，不推送、不运行远端CI。旧验收A/L及47目标负确认保持，路线未改变。
下一步为所有者按用户指南只读复核原B及交付对象；独立用户签收、Live理解/研究选择价值、
独立金融效果均未验证。旧工作区冷启动就绪稳定性、原录制缺失及权限问题保留，不宣称全面验收。

封存代码提交517b2cc79b4c159278744ad49bc8c9b77a0075cb；文档收口另验
`python -m pytest -q tests/test_focused_r0_status.py tests/test_focused_b0_plan.py --basetemp=.t25fixdocs --junitxml=.v25fix/final3/docs.xml --tb=short`：
4通过/4.30s/exit0；`git diff --check` exit0。提交后逐文件核对242源码/测试hash不变；
统一旧验收JSON除新增本批索引外所有原值相同。原数据/数据库/模型/失败记录未提交或清理。

## 12 本轮推送后的状态同步（2026-10-20）

用户随后要求“帮我推送本轮修改后代码”。执行`git push origin feat/mission-research-v2`，
exit0，远端由3f45a3e前进至5d3f576；随后`git ls-remote --heads origin refs/heads/feat/mission-research-v2`
exit0，返回`5d3f57687592b46693e687cc0611bd492adac065`，与当时本地一致，tracked工作区干净。
代码提交517b2cc、文档提交5d3f576；未force push、未上传本地数据/状态/模型目录。
这是已测工程分支交付，不是正式产品全面验收；本轮未创建tag/GitHub Release、未核查远端CI。
§11及原验收JSON保留收集时的“未推送”状态；本节追加后发生的事实，不回填原收据。

用户本次要求同步路线和发布状态。仅更新AGENTS、README、路线、CURRENT、handoff、
剩余验证入口和本日志；不改研究范围/里程碑顺序、代码、测试、依赖、原验收或数据库。
下一步保持所有者G6只读复核原B，再核对A的新任务及权限；新V2.5真实研究另核授权。
旧B不重训，独立用户、Live研究理解/选择价值和独立预测效果仍未签收，不自动推进后续能力。

本次文档检查：`PYTHONPATH=src;tests;apps;scripts`下执行
`.venv/Scripts/python.exe -m pytest -q tests/test_focused_r0_status.py tests/test_focused_b0_plan.py --basetemp=.t25statussync1 --junitxml=.v25fix/status-sync-20261020.xml --tb=short`，
4通过/4.44s/exit0；`git diff --check` exit0。242个已验源码/测试文件逐文件与修补收据相同，
仅7个MD变化，原验收JSON及本地原始收据未改。本次不重复全仓或浏览器，不触发训练/Provider。
状态同步为后续本地文档提交，尚未推送；前述5d3f576是已核实的修补交付SHA，不冒称本次文档SHA。

## 13 所有者A反馈修复与三阶段补测（2026-10-20—21）

本批基线b29142a5a99107dbd407dc9cc23745c39c71e0f8，原分支不变。
用户要求先修实际界面阻塞，验证后做三阶段补测并汇总；不重开N0—N5、不改路线。
原A/B数据库、曝光、额外refit和旧包只读保留，不修改旧合同恢复或替所有者签字。

### 13.1 实际反馈与已实施的最小修复

所有者A=StandardScaler+Ridge(alpha=10)、base_lags、扩展起点；本次实际Campaign
`persistent-48505fe9ae2131256a34c174`，原B身份不变。
用户原ZIP SHA256=12b3a7fb9f9c339229b0c3fa7e6b76b010c6aedfe0092ff31dbbb4af3e72b075，
原行情5fb282f6278d14000592e0e432fe69a5c00fdb6f7b48cbb56368fc0e3185bbcd。
只读审计49索引文件/10份预测，各252相同评价目标，四fold指标/原标签复算及
20个Ridge fold的Scaler训练行统计一致；不是新训练、独立确认或许可认证。
A使用28研究fits、HTTP0、2计划/3实际候选，无额外refit；推荐R1C1 MAE
0.005290705400779901，相对alpha10起点降低0.320553%，达到原0.25%开发门槛。
窗口504两项均变差，负结果保留；不能因此证明特征机制、显著性或收益可交易。

实际体验问题：所有者无法理解英文JSON；期待实验报告但ZIP仅原始证据；
步骤标题不可点；登记输入填入后仍显示手动；旧包校验失败仅英文；启动相对目录风险。
这些是失败/阻塞，不记作用户未测试，也不把先前助手解释算首次理解通过。

实现仅沿原投影/导出/向导：中文上一轮事实和本轮控制/改动/比较，原JSON折叠，
规则来源明确非LLM；REPORT.html加入原ZIP及SHA256索引，转义HTML且不外联，
受限导出不重新带入叙述；步骤按钮沿原校验；输入匹配原路径；错误中文指导仍拒绝不可信旧包。
新启动脚本必须原绝对DB/项目路径且拒绝缺失DB，不设置全局环境或清理状态。
Windows C:relative与根相对路径也必须拒绝。

### 13.2 本批预登记的三阶段与授权

阶段1：合成/零fit的历史结果扰动、两轴选择/合法控制/预算负例，及中文/受限导出/
步骤校验；报告不从最低MAE重选推荐。阶段2：既有原Controller/worker的两轮与
One-shot、缓存/中断恢复/三层训练范围/真实fit账本/窗口一致refit与新进程推理，
四模式Chromium及冻结完整回归。合成结果与原A只读审计分别记录。
阶段3：真实Provider有限语义挑战、严格录制回放及独立两轮研究；不拿规则模板
或自拟LLM fixture证明真实模型质量，不预设Adaptive必须赢或必须换轴。

用户批准：现有百炼配置，模型按deepseek-v4.1-flash-1017、deepseek-v4.1-flash、
glm-5.3、deepseek-v4-pro-0813、qwen3.8-max、qwen3.7-flash顺序，仅额度错误切换。
最多6次冻结语义挑战+2次研究规划，合计HTTP≤16（失败也计）、每次输出≤4000token、
每次超时≤180秒、Provider活动≤1800秒。只发送SPY合同、alpha10配置及获准诊断/
汇总指标/反馈；不发原始行情、逐行标签/预测、权重或文献。不购买额度；
用户确认账号已设免费用尽即停，API本身不能核实账单，金额未知不能写0。
新真实行情Campaign/refit具体计算额度仍待答复，不沿用旧A的一次训练授权。
随后用户明确批准上述3个隔离Campaign、每个研究fit≤32及额外refit≤2；
因此本批可执行这些新计算，不改原A/B库，不读独立确认标签。
模型不在已冻结Campaign中静默替换；中途额度失败保留状态，不能改旧hash继续。

### 13.3 测试运行日志（待最终补全）

所有证据在隔离.v25owner，原失败不覆盖。初始4项红例失败；Node测试render stub修正
前的1项失败保留。新增legacy缺失声明轴负例由失败转通过，不补造轴。
定向最终10通过/8.10秒/exit0（absolute-path.xml），包括Windows三类非完整路径拒绝。
受限sandbox导致原实际回环HTTP失败transport_unavailable；原断言不变、
获准本机回环后31通过/7.91秒（loopback.xml），不是外部Provider稳定性证明。
首次全仓因新增路径边界复核而主动中止，保存final/regression，不计通过；
最后功能修改后的完整回归重新开始于final2/regression，最终结果尚未取得。
浏览器阶段与最终源/输入/依赖绑定、命令/exit/语义判断后续按实际收据追加。
原两项历史失败、平台/native/旧48条A/L和47目标负确认不因本批数量关闭。

### 13.4 已取得的阶段证据（2026-10-21追加；最终冻结仍在进行）

最后备注修正前的final3完整回归999项逐条覆盖，990通过/2历史失败/7跳过，
exit1。两失败仍为原DLinear 2c05bfd22af27435.json缺失及Windows symlink权限；
未放宽、删除或换fixture。首次final3浏览器2通过/2等待完成失败（原120秒门槛），
与全仓并发时出现；同源码复跑未改门槛，首轮失败保留，不能直接归因为机器慢。
原Research Workspace也出现续接URL未在原5秒内变化的失败，非首次标题失败；
不借用上一批成功关闭本批就绪稳定性问题。
视觉/真实A只读复核另发现报告备注实际字段为research_options.notes：新增原样
负例1失败，再以原字段及明确旧fallback修正，定向11通过/10.17秒/exit0。
此后最终全仓重新冻结于final4/regression；未结束不写通过。

三条获准真实开发批次在.v25owner/real-{adaptive,one_shot,live}，均新建隔离库，
同5fb282原字节、alpha10/base_lags/seed42、诊断ON、同252评价目标（4×63）。
Adaptive实际28研究fit/2计划/3候选；One-shot32fit/1冻结计划/4候选；HTTP均0。
二者同样推荐20日收益均值+扩展窗口，MAE=0.005290705400779901，
相对用户起点改善0.320553%。公共对象指标逐值相同，Adaptive复现原A全部指标。
这只支持等预算上限下本例推荐相同，不支持Adaptive胜过One-shot；实际fit不相等，
并发/等待条件不同，不能比较97.21与93.19秒宣称效率优势。

Adaptive另显式重训两项已接受rolling504候选，各1fit：基础滞后收益和保留20日均值
的组合。实际均选504行，生成特征保持；新进程分别4018/4004行无标签预测逐值一致。
最后报告修正源码下再次只读加载预测一致，0新增fit/HTTP。没有删原B的额外重训。
所有新包索引hash及目标行、公共指标已独立只读核对；本地使用声明不是独立许可或
point-in-time认证，已暴露历史数据不升级独立确认。

Live六次挑战使用独立简化语义schema和合成汇总，不是生产Advisor完整schema验收。
实际全用deepseek-v4.1-flash-1017；窗口更好、两者变差、执行失败、fit余量0四题返回
完整JSON，逐项语义审查为有限通过；首题180秒deadline失败、delivery/usage未知；
机制未区分题输出4000token全部reasoning、text=0、finish=length，被原严格JSON拒绝。
因此完整反事实轴对照/机制边界挑战未通过，不用别题回答替代；4/6不是统计质量估计。
六份不可变记录按明确call_id严格离线回放：四份逐值一致，两份失败记录拒作成功。
已知用量合计12186token，首题用量未知，费用null，不写免费金额=0。

真实Live Campaign首轮HTTP发生SSLError/transport_unavailable，进入waiting_provider，
保留16次固定对照/用户起点fit，没有研究候选。预定两轮闭环BLOCKED_PROVIDER，
不能写研究无改善或模型不懂合同。未关闭TLS校验、改模型/预算/hash或第三次规划。
测试脚本的“只支持完整包”复算器在partial ZIP上另报KeyError：原失败收据保留；
独立partial包hash/基线制品/失败Replay审计通过，不把它说成产品导出失败或Live完成。
全部真实发送合计HTTP7、计账活动约402.88秒，真实研究fit76+显式refit2，均在批准上限内。
没有额度错误，故没有切换后五个模型；模拟额度保护通过不等于真实fallback或余额核验。

### 13.5 覆盖判断与真人边界（最终结果补全前的限定判断）

两轴完整控制继承、单轴/隐藏参数拒绝、成熟eligible→精确窗口→Scaler实际fit、
方法缓存与独立观察、研究认识更新原反馈链接、预算/暂停/kill恢复/续接、
推荐与当前查看隔离、窗口一致可信交付均由本批原测试及真实只读/新隔离计算覆盖。
新增test_v25_axis_policy三项扰动证明有限参考规则会随已有MAE选择不同合法控制/轴，
不是证明Agent理解市场机制；规则实际是预设有限分支，并非两轴全局优化。
原V2.5 59项和上一批40项测试纳入完整回归，独立用例数量不重复累加。

仍缺：生产schema下真实LLM两轮实际更新/执行闭环、真实额度切换、LLM选择增量价值、
独立金融确认、同SHA远端CI/未授权native平台。上述不是都必须真人执行的项目；
应分别补网络/Provider、预算内自动工程及合格独立数据协议，不能混成一份“真人待测”。
必须真人的部分：所有者无需助手解释的中文摘要/报告理解复核；独立目标用户A/B入口
真实任务、主动时间/帮助/错误；账号免费策略及资料许可/时点的责任人确认。
所有者已听过解释，后续不称首次无辅助理解；机器不代签G6或代表性可用性。

### 13.6 最后功能修改后的最终冻结回归

final4/regression四分片已结束。999适用项逐条对账，无缺失/额外/重复；
990通过、2历史失败、7跳过，实际aggregate exit1。两个失败nodeid仍为
`test_p1_real_validation_artifacts::test_dlinear_strict_live_card_replays_without_an_api_call`
（原2c05bfd22af27435录制缺失）和
`test_focused_r4_trust::test_model_bundle_tamper_rejected_before_load[symlink]`
（WinError1314）。不放宽原断言、不下载替代录制、不改系统权限求绿。
244个py/js/html/css源码/测试文件四个start/end及当前相同，摘要
8a543ee59daa11b0d8d2aedaec83d2e885415f06ac09b78949cc1ea1dac31d42；
新PowerShell启动脚本另以正向/拒绝负例及单独hash绑定，不混称包含在244内。
新定向11项已含在990中；Ruff/compile/三JS/差异空白6项静态检查均exit0。
原2个未授权real/native harness保持deselect，不冒称它们执行。

从System32启动原明确绝对测试DB的正向检查通过并关闭本测试服务；不创建空库。
原A的独立新只读中文HTML在1280/700实际Chromium渲染通过，原ZIP不改。
此时完整回归已完成，最终独立Agent四模式及旧Research Workspace浏览器继续复核；
其结果取得前不写无界面问题或全面产品验收通过。此前等待失败和源改变前阶段记录保持。

### 13.7 最终浏览器与交付封存

最终四模式命令仍为原test_agent_workspace.py及原断言：final4/browser合跑
3通过/1失败，466.45秒/exit1。失败为V2.5在context.new_page重新打开页面时
`Target crashed`，不是指标或合同失败，但仍是实际浏览器失败，不能删除或直接归因环境。
单独执行原V2.5 node、不改断言/超时：final4/browser-v25-isolated，
1通过/193.18秒/exit0，23项检查、page_errors为空；包括步骤导航、中文事实、
报告hash/实际渲染、700窄屏、可信交付、重开恢复、父任务不变和无Provider。
它覆盖本次可复现修复路径，不证明合跑崩溃/冷启动等待风险消失。

代码和测试本地封存为bc327dc（测试执行HEAD仍为b29142a及相同工作区字节），
未推送或运行远端CI。原Research Workspace最后复核1失败/130.91秒/exit1，
仍在原line222的续接URL 5秒等待；前面的队列、切换、重开、下载/索引、显式refit及
历史打开已走过，但子任务后续断言未取得，不补记通过。与此前同类失败分开保存。
本批不追加真实研究/模型重训/外部调用来追求全绿，也不以延长断言掩盖。

本批结论PARTIAL_BROWSER_FAILURE_LIVE_BLOCKED_HUMAN_OPEN：核心两轴/本地交付
重点已有工程与限定真实开发证据，但未达到“界面没有问题且全部补测通过”。浏览器
稳定性/旧工作区续接、生产Live两轮和真实额度切换均保持缺口；不是所有者或金融验收。
唯一可分发机器索引[本批收据](validation/v25_owner_recheck.json)，原始本地封存
.v25owner/final4/delivery_receipt.json；244源字节、依赖、声明输入、各JUnit及
真实预算逐项绑定核对通过。原A-L条款JSON未改，正式路线不变。

本地TEST_RESULTS.html为可读测试总结；A_EXPERIMENT_REPORT.html仅为原A的新增只读
中文投影，不改旧ZIP、不用于新预测。需要真人的理解/独立操作/责任人确认与可自动补的
网络/策略/独立数据验证分开列出。当前配置凭证精确扫描374个文本文件无命中；
不等于全面安全审计，后续新增文件须另核。文档收口检查及提交身份后续追加。

文档收口命令：`PYTHONPATH=src;tests;apps;scripts`下运行
`.venv/Scripts/python.exe -m pytest -q tests/test_focused_r0_status.py tests/test_focused_b0_plan.py --basetemp=.t25owner-finaldocs --junitxml=.v25owner/final4/docs.xml --tb=short`，
4通过/2.53秒/exit0；`git diff --check` exit0。测试总结在1280/700实际渲染，
窄屏无横溢、无pageerror/外联；技术原始收据与可读报告分离。G6准入未满足前
不自动邀请独立用户，当前仍是所有者复核及工程/Provider缺口。

## 14 顺序修补与补测续批（2026-10-21，进行中）

用户明确要求依次处理剩余工程/Provider问题、修改后测试，再交还必须真人的部分。
基线3117b79，正式分支，tracked clean；原A/B、旧失败、§13和历史收据均保留。
不重开N0—N5、不扩大能力/路线、不调用独立确认或追加模型包重训，不推送/远端CI。

### 14.1 预登记与授权

先旧工作区续接/浏览器重开诊断与负例→最小修补/原断言浏览器→匹配新合同的
Live补测与严格离线回放→最后功能修改后的冻结全仓/源与输入绑定→真人清单。
工程模拟与真实行情/Provider分别记账；不强制找到赢家或换轴。
用户另明确批准：1个新隔离SPY Live Campaign≤32研究fits/≤2规划，另补原先
不可评的2个语义挑战；本批HTTP≤9、Provider活动≤1397秒，连同前次HTTP7/
402.88134210009594秒，合计仍≤16/1800秒。输出≤4000token/次，deadline≤180秒。
原发送白名单、原模型顺序、免费用尽即停及仅额度错误切换保持；不更改旧合同/
预算/hash续跑、不把TLS/超时/无效JSON冒充额度，不关闭证书核验、不购买额度。
新语义挑战只追加简短JSON输出要求，事实及评价边界不变；属于新提示版本，不能
冒称原相同提示下的复现或模型比较。生产Campaign仍使用原完整Advisor schema。
若批准预算内仍失败，保留失败并明确阻塞，不无限追加计算/发送求绿。

### 14.2 已复现与最小修补

新增回调5红例失败，原AppTest独立入口导入负例1失败均保留于.v25closure。
续接按钮原在fragment重绘大段父证据后才处理；改为原按钮callback先调用唯一
continue_workspace_campaign、复用原operation token，成功后导航并触发全app rerun。
失败只显示安全类别/未知提交提示，不泄露请求内容，也不自动创建第二操作。
callback内不调用Streamlit会忽略的rerun；fragment顶部只处理导航标记，不建新状态权威。
原权限/父绑定/预检/提交/队列/计账未改；没有缓存或跳过完整性检查。

5回调检查及原页面打开用例6通过/3.84秒；含实际排队研究的原AppTest合计
7通过/51.39秒/exit0。阶段旧Research Workspace保持原5秒URL断言，
1通过/166.62秒/exit0、17项原检查；该阶段修改期间开始，不作最终源码绑定声明。
只读合成原证据profiling：workspace_campaign约0.165秒、续接预览0.089秒、
输入核验0.598秒；不因此宣称全部延迟已被解释。
浏览器新增crash/阶段/可用内存诊断，原context重开保留，V2.5再追加三次重开与
零新增fit断言；历史Target crashed仍保留，根因尚未建立，不能称已修复Chromium。
定向Ruff/编译/差异空白检查通过；最终四模式/旧页/Live/全仓结果待实际收据。

### 14.3 续批结果与2026-10-22新增失败排查（不覆盖旧收据）

上述源码245文件的四模式Agent浏览器4通过/518.49秒，旧工作区最终1通过/
155.60秒，均保留原断言；V2.5额外三次重开零fit、page_crashes为空。
完整回归final/regression实际1004项精确覆盖：994通过、3失败、7跳过，exit1，
源摘要b2fe1a7cd3e6d4b21f750e748396c4b49d66b73e4641b75de695f4d7a3d8a671。
除原DLinear录制缺失及WinError1314外，新增provided_start交付/续接用例失败：
子任务在原120秒等待结束时仍running。原Queue记录随后completed/exit0，
从started_at至finished_at约119.79秒，从提交至结束约125.19秒，不是永远挂起。
2026-10-22不改测试/超时，原用例单独复跑continuation-isolated.xml：
1通过/128.42秒，父研究约51.38秒、子研究约46.66秒，完整继承/交付断言通过。
此证据提示并发/负载相关耗时，但未建立唯一系统根因；最终回归降低编排并发，
不放宽原等待、不删除失败、不改生产Queue求绿。上述单项先于下述Provider源码修改。

原失败两语义题以更短提示补测均有效，严格断网精确Replay通过（2 HTTP，
54.6786秒）；只支持有限方向/control/不确定性判断，不是同提示模型比较。
新生产Live real-live仍partial/proposal_invalid：首模型HTTP200，4000个输出token
均为reasoning、text0，16起点/对照fits、零研究候选。原harness仅据Queue completed
记PASS的语义错误另由outcome-audit.json明确纠正，不改原收据冒充两轮成功。

### 14.4 第二模型关闭思考的显式授权与实现

2026-10-22用户批准切换deepseek-v4.1-flash并关闭思考、另1个隔离Campaign≤32fit/
≤2规划，零额外模型包refit，发送白名单及免费用尽即停保持；剩余HTTP≤6/
Provider活动≤1295秒，前后仍≤16/1800。非额度错误不自动换第三模型。
客户端新增可选enable_thinking/LLM_ENABLE_THINKING，严格bool/true|false校验；
仅百炼已登记hybrid型号，未设置时不新增wire/contract/metadata字段，旧合同保持。
显式值同时进入冻结Provider合同、实际wire、generation_parameters；不修改本地.env，
不放宽JSON/模型/费用/确认门禁。已登记型号为deepseek-v4.1-flash、
deepseek-v4-flash-0731、deepseek-v4-pro、deepseek-v4-pro-0813；不猜测1017或glm支持。
参考官方https://help.aliyun.com/zh/model-studio/deepseek-api；不据文档断言账号免费余额。
thinking-red.xml实际12失败/1通过；修补后thinking-green.xml 38通过/93.25秒，含
13项新增合同/wire/metadata/配置负例及真实本地HTTP、原Provider/管道回归。

real-live-second/persistent-e030016f56feb64a7fda19d0：HTTP200/finish stop，
493正文token，输出截断未复现；但返回feature_program带method_program_header_ref，
原严格编译器invalid feature program fields，partial/proposal_invalid，16fits、零候选。
原提示词response_schema同样被输入压缩投影改成了内部引用，是可复现产品示例缺陷；
模型复制该例不能成为合法DSL。audit_second_attempt.py严格断网精确Replay并复现拒绝，
旧响应字节/hash保持，绝不事后补字段或扩大准入。此次1 HTTP/5.91645计账秒，
截至本次累计HTTP11/510.046933600086秒（准确浮点以live-budget.json为准），金额仍null。

### 14.5 输出示例修补及再次Live授权（进行中）

新增普通/嵌套AST的可复制输出示例2红例均复现invalid feature program fields。
最小修补：原project_method_references只压缩输入事实，不压缩response_schema中的
程序头或表达式；输出示例保留完整合法FeatureProgram。原无损逆投影/hash校验、
输入规划引用不能提交DSL的门禁、64000 wire上限均不变。新增实际合成两轮照抄示例
编译/执行检查；最大文本/ON/OFF/宽AST及旧投影回归实际结果另追加。
这改变新Prompt/源码身份；不强制恢复已有失败活动，也不是生成式自动修正。

用户随后明确批准修补通过后再1个隔离Live研究≤32fit/≤2规划，仍第二模型关闭思考，
HTTP≤5/Provider活动≤1289秒，前后累计≤16/1800，零refit、原白名单/免费保护不变。
原A/B、两次新Live失败和旧TLS失败保留；该新授权不代表任务已执行或已成功。

第一次示例修补的完整相关回归example-green.xml实际39通过/1失败/503.59秒，
宽AST＋4000字备注＋诊断ON的第二轮wire超过64000上限；HTTP前被拒绝，失败保留。
读取先前冻结的同一合成上下文：旧压缩63691字符，保留输出示例后64256。
继续最小无损修补：仅对prior_decision_designs中完全相同的事前decision共享输入引用，
每项design_hash/control仍独立，v4 method_decision_ref明确只用于输入，输出保持inline。
完整逆投影和source_hash核验不变，旧v3读取及无新引用的序列化保持；不合并不同判断，
不删除负结果/数值/备注、不增加64000上限。保存上下文新wire63790字符。
sharing-red.xml新增负例1失败；sharing-green.xml合同/投影23通过/3.08秒。
最后源码example-final.xml：宽/普通AST×ON/OFF四极限与实际照抄示例两轮共5通过/
212.93秒。源/测试246文件的修改范围Ruff、编译、diff三检查均exit0，static-final.json。
旧Live回答依旧严格拒绝，不能因新提示修补事后充当新Provider成功。修补后Live已按
本节最后一次明确授权新建隔离目录real-live-repaired，结果待实际收据。

### 14.6 修补后真实Live：技术闭环通过，实质研究选择价值未证明

real-live-repaired/persistent-a1d27d38bf091a2b7764ccc4：原WorkspaceUI→Queue→
Controller完成2次真实规划/2 HTTP、20研究fit（16起点/对照＋4候选），零额外refit。
第二模型deepseek-v4.1-flash、enable_thinking=false、两次finish stop、正文559/769
token，生产完整schema通过，execution_status=completed，stop_reason=
no_new_executable_hypothesis。第1轮相对user_start增加mean(return_1,20)，窗口仍
expanding、alpha=10、原内置组/seed/Scaler不改；MAE .005290705400779901，相对起点
.005307719475588726降低0.3205533918%，仅已暴露开发证据，与原A相同方法/指标。

第2轮仍从user_start提出相同公式，原去重命中skipped_duplicate，没有额外4fit，
无第三次调用。research_update绑定上一轮真实proposal/design/rule/feedback引用，
严格校验通过；但finding仍是通用文字，items基本复制输出示例，没有具体解释MAE
变化或提出新的有条件试验。两次program也都与各自提示示例相同。因此仅判
PASS_LIMITED_TWO_DECISIONS_ONE_NEW_CANDIDATE；Advisor实质研究质量为
NOT_DEMONSTRATED_TEMPLATE_LIKE_REPEAT，不升级为真正反馈驱动选择、两轴价值、
模型优势或市场机制理解。本次没有选择窗口，不要求强行换轴；重复并非新实验。
同一历史数据反复运行不能成为独立复现或盲确认；不以微小增益宣称盈利。

audit_repaired_live.py在socket构造处断网：精确call_id Replay、原normalize及编译
输出与原冻结两计划候选逐字段一致，0新fit/HTTP；原包8份预测逐行/逐折复算及
41个索引文件hash通过。原A/B campaign、A原ZIP、raw/source哈希前后相同。
API别名权重未解析，金额未知null；没有额度错误，不声称真实额度切换已验证。
累计所有获准补测（包含§13）：13 HTTP/526.204903000082 Provider计账秒，
128真实研究fit＋此前批准的2次模型包refit，本§14新refit为0；每个隔离Campaign
均未超过32fit。未用完的预算不自动用于追加Campaign/调整提示直至得到赢家。

当前246源码/测试文件摘要495aa22815d0e967098132048ad46c875dca07fda036f66858a560b943e822e6。
最后浏览器与全仓采用此源码另测，之前245文件回归与阶段失败不冒充新源验收。

发送范围补充审计outbound-scope-audit.json：冻结请求中没有检查到训练模型系数字段，
但pair_diagnostics含固定公开等权规则weights=[0.5,0.5]。这是已有获准诊断的公式配置，
不是Ridge拟合权重；也不能将原“禁止特定键”检查升级成消息没有任何weights字段或
完整隐私/白名单PASS。如果所有者的“权重”边界按全部权重字段解释，该字段需另行
澄清，不能事后替所有者签字。本轮外部调用已停止，原请求和失败不改；后续不会
凭剩余HTTP预算继续发送。这一口径与源码/技术协议、研究选择质量分别报告。

### 14.7 阶段源码浏览器及冻结全仓（当时运行中，后续中断见14.8）

final2/agent-browser四模式全部4通过/502.22秒；final2/legacy-browser旧工作区
1通过/136.49秒。保持原页面等待、续接5秒断言与全部业务断言，V2.5额外三次
context重开、零fit、诊断/推荐/报告/可信交付/父子绑定检查保留；不是延长等待求绿。
final2/sequence.json绑定同一246文件/source495aa228…822e6，严格按Agent浏览器→
旧浏览器→交付文件单独运行→其余三分片编排，不把并发成本藏成数值结果。
全仓初始收集1021适用项，原2个未授权real/native harness仍deselect；serial shard-0
原test_focused_v25_delivery.py四项全通过/221.86秒，原120秒断言未改；其余分片
尚在运行，不提前填写最终通过数。源码/测试从Live、最终浏览器至全仓保持冻结；
文档与只读证据汇总不作为功能变更。前述994/3/7和原Target crashed均继续保留。

附加已有真实窗口包只读复核：从Git3117b79提取原Python模块，逐文件在原244文件
收据中匹配LF/CRLF的实际字节哈希，复制为独立冻结运行时；不改已有包、源码哈希或
可信登记。两份已有模型在新进程socket禁网、构造训练器拒绝条件下4018/4004行预测
与前批保存数组逐值相同，原504训练行收据不变，fit0/ProviderHTTP0，原模型/库/输入
哈希前后相同，见frozen-window-readonly2/receipt.json。这是匹配旧环境的旧包保全证据，
不冒称新源码可以跨compiler版本加载旧包，也不额外消耗真实refit。初次辅助脚本在
ssl类定义前替换socket构造器导致导入TypeError，未进入预测；失败保留在独立旧目录。

### 14.8 实际导出报告发现的重复提案展示修补（最后功能改动）

检查真实Live包中的REPORT.html发现：skipped_duplicate仍为英文，重复提案本身
没有新MAE，但与沿用观察的改善比例并列，易被误读为第二次新实验。不是新训练失败，
但属于应由软件修补的可理解性问题。先保留原ZIP/报告与全部研究记录；按PID＋出生
时间＋精确命令核对，仅终止final2正在执行的测试树，原服务不动。完整中断收据
final2/regression/interruption.json，实际结束码15，不能算完整回归或将未运行项补PASS；
该源码已取得的浏览器4＋1、交付4通过及其他阶段结果仍保留。

duplicate-red.xml新增2负例失败；最小修改只在focused_summary的只读投影/报告：
重复提案明确未新增fit/预测、不产生新MAE，复用对象与沿用观察分别注明；缺引用仍
未知，不回填/制造本轮分数；常见重复/停止状态及起点模型/特征组/窗口显示中文。
不修改数值评价、任务/控制/合同、原payload或已冻结建议。duplicate-green.xml
所有者反馈/回调/Provider参数共28通过/9.74秒；Ruff/编译/diff三项通过。

从原真实Live包校验并复制40个已接受非报告成员，在新的独立导出目录重跑原导出器，
8份预测复算与全部文件索引通过；原ZIP字节不变，新的报告读起来明确区分重复提案。
该新导出不是新研究，也不重新评估选择/生成模型；fit0/ProviderHTTP0。

最后246源/测试摘要b9c29c5920507defe4b5b8f0555041b0e0e8c30ebae5ee122328d7ad6ce2c424。
与实际Live源码495aa228…822e6相比，仅focused_summary.py及其所有者反馈测试变化；
Provider/Prompt/Controller/Evaluator/训练与推理代码字节相同。没有为只读报告追加
真实Live，不能把既有调用重新标成此新源码的实际发送证据；新源码以原不可变
回答/事实的只读投影、重导出、本地HTTP/Replay及最终全仓/浏览器验证。
final3改为交付文件先单独运行，其余4分片，1023项初始收集将逐条对账；保持原
测试/超时/负例。当前全仓/浏览器未结束，不提前宣称无问题或全部验收通过。

最后源码b9c29c59阶段结果：final3/agent-browser四模式4通过/513.26秒；
final3/legacy-browser原工作区1通过/138.62秒；final3/regression交付serial文件
4通过/223.36秒。剩余4分片正在执行，1023适用项已预登记，不提前填最终计数。
真实Live新报告1280/700两宽实际渲染检查通过，无横溢/pageerror/外联；原包的英文
重复状态和未知MAE并列已在新的只读导出中明确修正，原包不改，投影不冒充新实验。

### 14.9 最后功能修改后的完整结果（2026-10-22）

final3/regression全部结束：1023项逐条精确覆盖，无缺失/额外/重复，1014通过、
2历史失败、7跳过、errors0、实际aggregate exit1，无新增失败。原provided_start
续接用例在最后源码的交付文件单独编排中通过，未放宽原120秒断言；不能据此宣布
所有并发/长时负载风险消失。两失败仍为DLinear原2c05bfd22af27435录制缺失，
及WinError1314在symlink创建处失败；不替换历史录制、不改系统权限求绿。
7跳过中5个opt-in浏览器已在同源实际另跑4＋1通过，另2为POSIX平台探针及
Windows package symlink权限条件。2个未授权real/native harness仍deselect。

246源码/测试文件在全部final3浏览器/分片start/end及当前相同，b9c29c59…ce2c424；
各运行核心依赖和声明输入一致，原始JUnit/start收据哈希及.extra.env模板哈希核验通过。
原A/B campaign、原A ZIP、raw/source保护文件结束时仍与Live前快照相同。
完整本地索引final3/delivery_receipt.json已生成；Live执行源495aa228与最后仅报告
投影修补后的b9c29c59分开标识，不冒称新源追加了真实LLM或真实模型重训。

限定工程门槛LIMITED_GO_WITH_HISTORICAL_BLOCKERS；整体
PARTIAL_ADVISOR_VALUE_NOT_DEMONSTRATED_HUMAN_OPEN。真实两次规划的结构/引用/
执行/去重/回放闭环有限通过，实质反馈驱动选择与LLM研究价值未证明；统计显著性、
独立金融效果、真实额度切换、长时稳定性及真人G6均不由这些测试代签。后续能力
包/权重/HPO/新模型/知识/Shadow未启动。旧失败、负确认47目标、原A/L保持。

本地入口收口：原8515端口健康检查未响应；以sqlite mode=ro确认原.pr14b库队列
只有4条completed、无待执行工作。尝试用既有绝对路径启动脚本后台恢复页面，被
工具策略在执行前拒绝，未用其他方式绕过，未创建数据库或启动研究。保留
final3/owner-launch-blocked.json；若需要原UI，所有者只需正常运行既有启动脚本，
不是要求其代做自动化回归或追加真实训练。静态中文报告可直接打开，不依赖该服务。

分发级审计索引为[validation/v25_closure_acceptance.json](validation/v25_closure_acceptance.json)，
包含最终源清单、逐项回归覆盖、分离的Live源、资源对账、报告及原始收据哈希；原始
数据库/行情/模型/运行证据仍仅保留本地。文档门禁4通过/2.23秒，中文汇总及真实Live
报告1280/700两宽检查通过；557个文本文件中当前API凭据精确匹配0，不冒称全面安全审计。
阶段进行中措辞仅记录当时状态，当前结论以本节为准；本批不推送、不执行远端CI。
