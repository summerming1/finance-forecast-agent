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
