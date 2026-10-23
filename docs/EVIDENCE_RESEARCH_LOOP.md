# 证据驱动研究闭环：唯一里程碑合同

2026-10-23 用户在对话中明确批准交接v1.1的01/02实施E0—E5。实际基线
`e361b0ef3418b09f7c5168caf5a381870634b9e3`，`feat/mission-research-v2`；tracked clean。
未跟踪历史运行证据保留。授权仅隔离合成工程及本地分批提交；无新真实Provider、
真实行情研究、外发、封存标签、生产迁移、全局权限、推送或远端CI。
本文件是本轮唯一施工合同；下面完整纳入交接v1.1的01要求，不重开V2.5 N0—N5。
原稿“待批准/拟批准”是形成时的历史语境，已由上述可信用户指令批准工程范围，
并不表示任何科学/真人验收通过。E0—E4工程已实现并完成整链验证，E5已执行冻结验收；
结果为新增关键路径通过、全仓仍有既有资产/权限失败，工程限定交付而非全面PASS。
原A/B、旧fixture/hash/47负确认不改。实际状态只见CURRENT_IMPLEMENTATION。

## 最终工程交付收据（2026-10-23；非全仓/科学/真人全面验收）

实际起点e361b0ef3418b09f7c5168caf5a381870634b9e3；最终测试源码
`384102d6c21e06f756b619af996b71e716d311f6`，原分支feat/mission-research-v2。
后续只有本收据/Current/索引/指南等文档提交；包含本收据的提交由
`git log -1 -- docs/validation/evidence_research_acceptance.json`解析，最终回复给出实际HEAD。
tracked起点干净，原未跟踪证据保留；运行证据/数据库/输入/模型仅本地，未推送/远端CI。
下面工作日志保留各阶段当时的未完成/失败，不覆盖本段最终事实。

### E0—E5结果及ER口径

| 批次 | 已实际交付/验证 | 结果边界 |
|---|---|---|
| E0 | 唯一合同、ADR008、新旧分发、联合容量及原资源口径冻结 | 工程完成；旧schema/fixture/hash不迁移 |
| E1 | 六类真实诊断、具名相关/共同尾掩码、实际scope/内容缓存/计算回执 | 合成算术/原制品/6种诊断→更新→干预通过 |
| E2 | 稳定问题、不可变假设版本、关系级评估/暂缓、同响应更新/原子恢复 | 结构和执行工程通过，不证明LLM理解 |
| E3 | goal/provided_start原worker、父末批完整请求到子首轮、完整双轴继承/可信交付 | 实际fit/predict/refit与新进程一致通过 |
| E4 | 原三臂公平流程/简单策略、双比较/成本、六对语义材料及人工rubric | 合成工程通过；真实B/C无本轮授权，NOT_RUN |
| E5 | 最后功能源下完整适用回归、六模式浏览器、静态/身份/条款/文档收口 | 已完成验收执行；整体partial，不给全仓/负载全面PASS |

[ER01—ER40实际索引](validation/evidence_research_acceptance.json)逐条给真实node、运行命令引用、
实际exit、制品SHA、范围及未覆盖原因。237个不重复映射node均通过；它们与全仓及阶段
运行有重叠，绝不相加为独立测试数。ER29（原A/B匹配运行时只读）、ER32（真实语义判断）、
ER35（并行负载风险）和ER39（完整回归/静态非全绿）为partial，其余36条仅在各自
工程声明范围passed。ER37/38/39/40含文档/收据审阅，不伪造pytest用例。

### 最终精确运行与身份

仓库根、现有.venv，Python3.13.3、Windows11 build26200；Node24.0.0、Chromium
153.0.8010.12。75项实际安装分发版本、265个源码/测试文件逐文件SHA及全部1118个
精确node已冻结在`.evidence-loop/final6/preregistration.json`及分发索引；不是只列依赖约束。
运行前、各组运行后、最终当前再次核对：源码/测试无缺失或额外文件，75项依赖一致。
`pyproject.toml` SHA256 `ce40d239b9681568c6eb56d32f32920054ca4c36f6fe50566217c848c84aaebd`；
runner `15f6532945ec212f035a50ce9c4bd92718afca57addf617b83e10544eea4896f`。
source identity（evidence-final-source-v1）
`514a73f0dc65c7c49b791a78be89b6e977834fc19508754130ab536605230c14`。
静态输入/生成合成输入的配方由冻结源码绑定；各案例的运行生成数据另由原合同/制品身份
绑定，展示案例raw SHA见下方轨迹。不把负例故意篡改的临时输入说成始终未变化，亦未重新
计算或声明所有者原A/B的真实预测/数据科学结果。

```powershell
.venv/Scripts/python.exe scripts/run_evidence_regression.py --out .evidence-loop/final6 --temp-prefix .erfinal6 --shards 3
```

runner先精确collect，再串行交付组及3个文件组；每组完整Python argv（含全部文件、两条
deselect、独立basetemp/JUnit）、开始/结束source/deps/input、实际exit和stdout均保留。
OMP/MKL/OPENBLAS=1，PYTHONPATH=src/apps/scripts的绝对路径，移除真实API Key、
真实数据admission和浏览器gate环境变量；不复用旧额度。不是以合成替换两个真实行情研究
节点：`test_models_and_harness.py::test_harness_runs_real_data`及
`test_methodcard_p0_pipeline.py::test_methodcard_derived_paperspec_runs_p0_harness`
明确因本轮不授权新真实行情研究而排除，其原测试/断言不改。

| 最终run | 实际结果 | pytest报告耗时 | 实际exit |
|---|---|---|---|
| final6 part0 | 9通过 | 441.66秒 | 0 |
| final6 part1 | 355通过/1失败/6跳过 | 4838.09秒 | 1 |
| final6 part2 | 349通过/2跳过/1原真实行情节点deselected | 4838.74秒 | 0 |
| final6 part3 | 395通过/1失败/1原真实行情节点deselected | 5283.35秒 | 1 |
| aggregate | 1108通过/2失败/8跳过；1118/1118精确node，无missing/extra/duplicates | 并行组不相加计墙钟 | 1 |

94个本轮新增非浏览器node全部通过；新增browser参数与另5个模式在独立运行通过。
`.evidence-loop/final6/aggregate.json` SHA
`4e3c4255f63315185509101624bd2aa77d758f852ec67e63e4efe48d86cc10be`，
preregistration SHA `a8774b69e856b0fbae4f23035d7fcc87baa985687cafb5ce8d74bcf38ed26136`。
两处原始失败逐字堆栈保留：

- `tests/test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink]`：
  第237行创建测试symlink时WinError1314，尚未到load门禁断言。无全局权限修改，不用
  junction/mock或跳过替代安全验收。
- `tests/test_p1_real_validation_artifacts.py::test_dlinear_strict_live_card_replays_without_an_api_call`：
  缺`projects/finance_agent/llm_fixtures/method_card/2c05bfd22af27435.json`。
  不手写新fixture、不换hash、不实际调用API填洞。该旧测试源及依赖实现未由本轮更改。

8跳过中6个是显式浏览器gate（已另跑全部6个）；另外两个为Windows symlink权限和
POSIX process-group kill探针。原JUnit警告亦保留。不能把这些跳过计成通过。
之前final/final2/final3/final4/final5完整尝试因真实发现的接线/容量/格式/兼容回归中止，
原ABORTED、原失败、复跑关系保留，不能拼接它们代替final6。阶段失败目录及SHA索引见
`.evidence-loop/raw-failure-catalog-stage.json`；阶段green-JUnit但非零exit也未升级为通过。

### 浏览器、容量、静态及未关闭的负载边界

独立六模式命令：

```powershell
.venv/Scripts/python.exe -m pytest tests/browser/test_agent_workspace.py tests/browser/test_research_workspace.py -q --basetemp=.erbrowser6 --junitxml=.evidence-loop/browser-final6/browser.xml --tb=short
```

PYTHONPATH同上，三BLAS线程=1，FFA_BROWSER_E2E=1，真实admission环境清空，
FFA_UI_BROWSER_ARTIFACTS指向`.evidence-loop/browser-final6/artifacts`。
6通过/848.50秒（pytest报告时间）/exit0，start/end源/依赖/input一致；XML SHA
`0f71c2b1383d6d54fe442a7eb69e09c334f9bde24f900ae56c1e14da043378bf`。
原120秒等待断言未放宽。新协议实际截图700/1440及1280成果/推荐布局、三次额外新
context重开、刷新/导航/只读、父末批到子首轮、推荐隔离和模型/研究包均通过。
5个Agent模式报告page_errors=[]、page_crashes=[]；旧工作区第6节点亦实际通过。
截图作助手视觉复核，不是所有者/独立用户签收。

保留browser-final5：与三重回归并行时3通过/3个120秒完成等待超时，exit1；
该源为230cf1e，之后只修了旧最小摘要可选字段兼容，不能将旧失败重签为384源。
后台完成不等于界面通过；负载是观察条件而非已证明唯一根因。失败报告无page_errors
字段且无FAIL截图，不能宣称那次零页面错误。后续独立完整6模式通过不消除高负载
稳定性风险，不承诺并行负载SLO已通过。

最后源联合容量原制品：`.erfinal63/test_joint_actual_two_slot_con0/` ON两次
47179/61653字符、56492/70966 UTF8字节；con1 OFF两次31076/39577字符、
40389/48890字节。均完整新schema、两槽/三活跃假设/父末批/4000中文备注/继承两公式；
受64000实际wire字符及结构上限共同准入，字节另记、token未知。不是任意字段所有最大
值的笛卡尔积或科学小样本保证。完整历史保留，工作视图明确归档为deferred，必要当前
反证不静默丢弃，超限HTTP前拒绝。

最后源静态实际执行：修改Python的`ruff check --output-format json` exit0；
`python -m compileall -q src apps scripts tests` exit0；`node --check`分别检查
actions.js/core.js/forms.js/views.js均exit0；`git diff --check e361b0e` exit0。
完整`python -m ruff check src --output-format json`仍74项/32文件/exit1，全部与
e361b0e对应Git blob相同，不是新增/受影响文件；原JSON和实际命令/退出保留在
`.evidence-loop/final-static-all.json`、`final6-static-results.json`。不称全仓lint全绿。

### 实际代码、报告与可信模型交付

关键源：`focused_diagnostics.py`为纯诊断；`research_state.py`为纯状态归约/新协议边界/
工作视图；`focused_research.py`复用原计划接受/结果接线/执行；`research_mission.py`
复用原Mission/Queue/显式续接及成本；`focused_summary.py`原报告/中文主线；原
workspace_ui_service和workspace_frontend为原界面集成。无第二Controller/事实库/evaluator。
测试位于16个`tests/test_evidence_research_*.py`及原browser新增参数，详见ER索引。
原数学候选v4/FeatureProgram/TrainingPolicy/旧诊断枚举和原推荐政策未迁移。

下方final6真实轨迹给出alpha10父两批→差父候选显式子两批，52总charged fit；两方向
完整单轴继承另由交付测试验证。父末批DQ04→子首轮完整请求/判断轨迹为44fit、4次
loopback HTTP；最终对应node均通过，不只绑定candidate或round_index。
新模型包回执候选r2_c1_aa2c45a1、Ridge(alpha=1)、rolling504、6列及一条gen_mean，
实际504训练行、明确额外1fit；model SHA
`b146ac6bac4760a621a94ecc295a3f76ebff4fb1d6ac63989aaeab3cc969442f`与当前文件一致。
新进程原`predict_model_bundle(bundle,state,unlabeled)`退出0且数组rtol=1e-8/
atol=1e-12一致的最终测试通过；这是可加载/一致性，不是D独立预测有效性。
原用户A/B没有重训，匹配旧runtime只读验证本轮BLOCKED，不重签源码hash绕过。

浏览器研究包真实重新审计9份预测/47个索引成员，package SHA
`7817254459faf3fac77f66cd9c82c62bfbe9bd0a5340b2a6eaca15ee3bbdb456`；REPORT为
中文实验报告，派生叙述沿原资料权限裁减。查看候选不改冻结推荐，已有包下载/重开只读
0增量；新模型包须明确额外refit。展示的合成研究可以no_improvement并保留起点。
实际操作命令和新协议三步入口见下方“本轮工程复核的实际操作入口”及操作指南。

### 五证据轴、剩余事项与提交

| 轴 | 本轮结论 |
|---|---|
| A 工程 | 新增/受影响关键路径实测通过；全仓/完整lint/负载全面状态partial，不能整体PASS |
| B 真实研究行为 | NOT_RUN；12份语义挑战/原字段/人工rubric已准备，无新Provider授权，不拿fixture/Replay签LLM理解 |
| C 研究选择价值 | NOT_RUN；同域三臂信息/资源公平工程通过，不证明更新更好或小MAE改善有价值 |
| D 独立预测 | NOT_RUN；可信新进程一致性不等于未暴露未来数据的独立效果；原47负确认保留 |
| E 真人价值 | NOT_RUN；助手截图/自动浏览器不代表本人理解、省时、错误率或客户价值 |

只留给真人：所有者对原A/B及新报告作只读G6理解复核（控制/单轴/正负结果/未决/
冻结推荐/研究报告与模型包/额外refit），不代签；独立用户正常使用记录主动时间、求助
次数和错误，不能由助手扮用户。B/C/D是另需新数据/发送/资源/评价授权的自动试验，
不是必须手工点击的测试；六对语义挑战要保留原回答并按冻结rubric人工判定，不预设换轴。
旧runtime/fixture及Windows权限边界单列；若要求高并行稳定性，需单独明确负载与延迟
准入并继续定位，当前不承诺通过。不得为补这些边界擅自安装/外发/读封存标签或改全局权限。

实现本地提交：8303e2a5849154e6349c4e6b54bf2bb273bc550c；
1c359079bd5133f41a50fb42c2fe21e501a2823c；
258cc2a3f74f146964f55981894e95502e360496；
230cf1e06c0abe6ce51f4b4eaf60746d61fc3bc7；
384102d6c21e06f756b619af996b71e716d311f6。
后续仅文档/收据提交，最终HEAD见本轮最终回复或上述git log命令；无推送/远端CI，
无新真实Provider/真实行情计算/外发/封存标签/生产或全局权限变更。

## 实施工作日志（不是最终验收）

### 2026-10-23 E0及基础负例

ZIP SHA256 `c28bde76a7d4f0dcec5d32dc90e9526ab8b4660fd290e51a0c48cafa7ab5c758`。
已核对实际HEAD/分支/tracked状态；原未跟踪证据不动。新增ADR008及分发级ER索引，
同步AGENTS/路线/Current/架构/验收/handoff/原剩余入口/UI指南/README的当前入口。
下方v1.1主方案完整保留要求；没有把后续裁剪/权重/RF等标成已实现。

当前实际代码：focused_diagnostics新增具名相关、线性q01/q99尾部描述/同掩码配对、
版本化有界请求和六类分发；research_state为纯归约/新容器校验，非新状态库。
新Controller参数research_protocol_id仅显式evidence_research_v1且原feature_window，
不设置时不往旧spec/Hypothesis序列化增加字段。原计划冻结记录单份update及证据上下文；
当前仅Controller合成链路已开始联测，尚未接通worker参数/UI/续接/交付全部路径。

E0的具体表示草案已编码并接受负例检验（尚非E0最终通过）：
- 新响应evidence_research_advice_v1，单research_update=evidence_research_update_v1；
  base_state_hash/questions/hypotheses/evidence_assessments/choice_reason。
- 每问题id/goal/scope/basis_refs/importance/status；假设id/version/question_id/
  claim/conditions/support_refs/counter_refs/alternatives/status。每行动可关联hypothesis_refs。
- 判断绑定evidence_id/hypothesis_id/hypothesis_version/assessment/finding/open_question/
  disposition（evaluated/deferred）。pending按最新对应关系归约，末批新增事实只投影待处理。
- evidence_request_v1为id/question/expected/branches/depends_on/query；诊断query精确
  evidence_diagnostic_query_v1的kind/object_ids/scope/variable_pairs/factor/parameters。
  旧diagnostic枚举不修改，适配仅供原编译器准入，实际执行保存的完整query，不能丢参。
- 结构草案：每update最多3问题操作/6假设操作/12判断，最多3同时活跃假设，非独立
  活跃问题业务限额；单文本320、标识96（证据引用160）、每引用字段8；深度12。
  update所有字符串值（包括ID/枚举、不含键）总8000、JSON字符30000；整响应字符串
  值总16000、JSON字符48000；完整实际Prompt仍64000。UTF-8字节另记、token未知。
  必须继续用完整新协议联合构造确认合法联合域，不以这些初始数值冒充科学保证。
- 诊断总变量对按对象数合计≤8；每尾部请求1因子，最多2对象，参数固定无搜索。
  Pearson/Spearman有限配对n≥2且非近常量才返回系数，average并列秩；近常量容差
  ptp≤1e-13*max(1,maxabs)。n<20/尾部n<10仅low_support提示，不代表显著性；
  不默认p值，不删主评价目标。无已保存训练预测/合格来源仍unavailable。

原始负例在.evidence-loop：e1-red.xml collection error（新函数缺失）；e2-state-red.xml
collection error（新模块缺失）；dispatch-red.xml 2失败；pair-bound-red.xml 1失败，
复现双对象各8对的越界后收紧为总计8；nonfinite-key-red.xml 1失败，修为原始浮点数组
内容哈希（不把NaN放进JSON身份）；pending-red.xml 1失败；envelope-red.xml缺新函数。
e1-arithmetic.xml虽案例执行29通过，实际exit1为系统Temp清理WinError5，不记通过退出；
后续使用仓库内全新basetemp，不改权限/不删除原临时证据。原失败及JUnit均保留。

阶段实际命令均在仓库根、现有.venv执行：
`python -m pytest tests/test_evidence_research_diagnostics.py tests/test_evidence_research_state.py tests/test_focused_v24_diagnostics.py tests/test_focused_v25_methods.py -q --basetemp=.evidence-loop/foundation-v2-temp --junitxml=.evidence-loop/foundation-v2.xml`
结果64通过/3.75秒/exit0。
`python -m pytest tests/test_evidence_research_envelope.py tests/test_evidence_research_state.py -q --basetemp=.evidence-loop/envelope-green-temp --junitxml=.evidence-loop/envelope-green.xml`
15通过/2.27秒/exit0。
阶段容量/原回归/文档合跑foundation-checkpoint.xml为78通过/76.52秒/exit0；期间有后续
新代码改动，明确不是E5冻结证据。新纯函数定向foundation-local-final.xml 34通过/2.32秒。
所有这些有重复node，不相加为独立覆盖数。受改Python Ruff和编译阶段通过，完整最终
静态/回归/浏览器仍待E5，不借用上轮1014通过称本轮全仓通过。

integration-red.xml复现Controller未接参数；integration-first.xml在第二次规划前因
新诊断缺diagnostic_id失败，补入实际分发结果，保留旧证据投影要求；integration-second.xml
原依据门禁正确拒绝测试提案漏填evidence_refs，补测试引用、不放宽原bind_design。
integration-third.xml原Controller真实合成“纯诊断→第二次更新→rolling504干预”
1通过/29.46秒/exit0，16总charged fits、2次规则规划、Provider HTTP0。
该结果不是worker/完整父子/UI/可信交付或最终冻结通过；新协议完整容量联测继续。
所有者A/B、原额外refit、旧fixture/hash/47负确认均未改，无新真实数据或外发。

E0—E5目前总体implementation_in_progress，不能将函数/字段/一条Controller轨迹作为
完整增量交付；E0联合容量/协议尚需最终收敛，E1—E5各项未覆盖原因会随实际证据更新。

### 2026-10-23 第二检查点：实际父子worker及联合容量

新增完整原队列goal/provided_start父子测试，`parent-child-worker.xml`实际5通过，
196.60秒，exit0。两入口均显式同Mission续接，新首轮评估父末批证据，父payload未改，
父子各含初始对照/起点的charged fit合计≤64、HTTP0；不是原A/B重训。
`joint-v4.xml`实际4通过/109.59秒/exit0（现有.venv/Scripts/python.exe），
含ON/OFF完整两槽首轮、第二次更新、新协议、4000中文备注、继承两公式、三活跃假设、
父正/负及低尾样本证据的联合构造，另含DQ02纯诊断到第二次更新与实际rolling504。
构造的父事实为assistant_authored_fixture，不是Live理解或科学证据。

容量收敛保留原始失败：new-protocol-real-context、current-chain、joint-exact-two-slots、
lossless-joint、resolved-timing、hash-joint均存在ON超限；key-joint/two-entry-worker曾因
可逆输入键别名未在观察形成时还原导致candidate_id KeyError。现已在验证原Prompt hash
后还原，未降低测试或更改旧fixture。新协议专用的可逆输入表示v4，对重复值/字段和完整
hex64身份作等价引用与无损base64url编码，response_schema始终原样内联；输出仍须完整原
字段/AST，绝不把内部$v/@引用当作输出语法。两个逆映射阶段以原内容hash核对。
只读已保存合成上下文探针从64243字符/72244 UTF8字节降为61870/69871；探针无fit/HTTP。
该数字不是所有字段最大值笛卡尔积的保证。合法联合域以完整序列化≤64000且所有结构
限制同时满足为准，超限HTTP前拒绝、不默删反证、不自动摘要。Provider token未实测。
最终源码后仍须重跑并保存每次实际测量；这些不是E5冻结成绩。

新UI在原第三步显式选择新协议；旧默认和旧批次不迁移。原REPORT.html/summary新增
中文问题/版本/判断/取证分支/pending和数值来源投影，不生成新语义解释。原受限导出
白名单不复活来源派生叙述。summary-red有缺函数和测试错误问题ID；summary-green
11通过/1失败（单独运行原测试未加apps路径）；随后显式PYTHONPATH=src;apps执行
strict-summary-green，44通过/7.45秒/exit0。form-summary为3通过/2.44秒/exit0。
strict-shape-red保留4失败/28通过，复现重复问题、bool版本及target/prediction冒充尾部
因子的门禁缺口，修复后上述44项通过。系统默认python缺pytest的exit1也未记作测试通过；
实际测试使用仓库现有.venv，不安装新依赖。

进行中：新DQ03/04/06原Controller实际链路、新协议公平参考/更新/简单策略、故障恢复、
浏览器、模型fresh-process及最终全仓；新资料发送范围也须显式保护，不沿用历史Live额度。
目前无新真实Provider/真实市场计算/外发/封存标签；B/C/D/E非工程轴仍NOT_RUN。

### 2026-10-23 第三检查点：完整链路与可读交付

tool-benchmark.xml实际5通过/250.75秒/exit0：新协议原基准适配的合理参考（update=null）、
更新臂、同域简单策略三独立冷历史运行；原Controller四种DQ02/03/04/06纯诊断进入下次
同响应认识与真实窗口干预。三臂同工具/合同/初始底模/权限/资源上限；不宣称Agent优越。
benchmark-red保留旧入口不接协议的TypeError，后扩展原适配器而非创建新基准评估器。
recovery-tool.xml实际5通过/257.55秒/exit0：模拟loopback两HTTP、严格Replay HTTP0、
完成重开不调用，以及DQ03查询回执落DB后故障恢复，不重算查询或重放认识。
delivery-capacity.xml实际5通过/212.49秒/exit0：两方向完整继承、同最终方法去重、
显式1次新合成refit保留rolling504及公式、fresh-process无标签预测一致，One-shot四槽。
最新联合构造实际ON首/次45046/61865字符、53047/69866字节；OFF27971/37300字符、
35972/45301字节，token未知。原64k门槛不变；原旧模型schema/math身份不升级。

新纯函数和工作视图进一步补边界：working-view.xml21通过/2.86秒，relations-send.xml
45通过/3.05秒，projection-prep.xml14通过/3.11秒。次数有重叠，不相加为独立覆盖。
version-relation-red.xml1失败，补新假设版本明确support/counter引用后该版本独立pending。
send-dependency-red.xml2失败，修复当前显式依赖必须评估/有理由暂缓，以及新协议Live需
另行声明获准发送字段。新Live/续接不能默认继承旧授权；无此确认在fit/HTTP前拒绝。
permission-limited资料仍用原逐源权限，父研究状态必须同当前诊断可见性和文献快照。

当前工作视图超过阈值时，保留至多9假设ID（优先所有活跃≤3）、每ID最近2版本、
其问题≤12、最近12判断/4计划键、12待处理关系及8待分配引用；必要支持和反证完整保留。
其它历史只有数量、原内容hash/来源及explicitly_deferred状态，不标为已评估/结束。
工作视图的state_hash指向完整原状态；原计划冻结完整accepted evidence_context，校验和
归约使用原事件完整状态，不把省略历史当空状态，也不允许编造不可见旧版本依据。
必要反证联合仍超64k则拒绝，不按成绩挑子集。未新增检索/语义库/总结调用。

atomic-variable.xml3通过/1失败/136.39秒，失败为新测试误预期proposal_rejected；产品按
原语义返回partial/proposal_invalid且没有接受plan/认识。修正原状态断言后单项
atomic-negative-corrected.xml1通过/30.13秒。原失败保留，不覆盖全组原exit1。
其余实际stop/review拒绝后恢复、已接受AST在未训练该列的control上定义同公式阈值
均通过；无隐式control重训，无把执行失败当科学反证。

browser-stage.xml因测试定位器仍假定只有1更新，strict mode失败；修成明确最后一条，
不删除断言。browser-stage2.xml在700px实验报告长ID横向溢出失败，为真实UI问题。
修原报告body/cell换行后browser-stage3.xml1通过/190.07秒/exit0；含源组件/worker、
两轮、47成员hash/9预测重算、明确2个独立refit、推荐隔离、三次额外重开0fit、显式
父子和子首轮父末批评估、篡改诊断拒绝。均为助手技术模拟，不代签真人接受。
扩展新主线展开pending的700px检查仍待最终运行，不用旧测试代替。

prepare_evidence_live_challenges.py仅准备材料：以已冻结合成context生成6组12份
标为assistant-authored counterfactual的配对语义题，保留相同原任务/工具/schema，
给多种合法决策的盲评量表和每份字段/字符/字节/hash，不执行候选或HTTP。
实际prepare命令exit0，输出.evidence-loop/semantic-materials-stage，12份、fit0/HTTP0。
这不是12次获准Live；B/C/D/E继续NOT_RUN，未来必须新确认发送/模型/重试/费用上限。

阶段scoped Ruff通过；一次广泛src Ruff报告74项旧区域问题、exit1，未改无关老代码；
最终须保存完整静态输出及受影响路径结果。final runner新增准确node/source/input/deps
冻结和原断言分片编排；只排除两项实际run_harness真实行情计算，原因在注册中公开。
E5、条款映射、本地提交与最终分轴结论尚在进行，不记全仓通过。

### 2026-10-23 封板与一次明确重启

browser-stage4.xml新协议含展开pending的700px检查1通过/182.77秒/exit0。
人工查看该技术截图发现规则演示的finding仍直接格式化英文指标dict，且窄屏左标签被
挤成竖排；finding-red.xml1失败/3通过，修为确定性中文指标标签、保留原数值，样式
只固定新主线标签的收缩行为；finding-green.xml4通过/2.42秒。不是再生成机制解释。
collision-red.xml1失败/2通过：合法稳定ID可能与内部$v/@0别名相撞。新输入投影v5
选择原文不存在的值标记和键别名，完整逆向hash核对；旧v1—v4投影仍只读支持，
旧候选/原fixture不改。last-foundation.xml51通过/3.04秒，含引用碰撞、原schema内联。
failure-reuse.xml1失败/23通过为测试误查不存在的failed_attempts字段；改为原失败item
断言，failure-reuse-corrected.xml24通过/38.80秒，真实失败预留4fit及execution_incomplete
进入后续更新；DQ01/02/05逐字段复用原数值/回执，查询fit/HTTP0。

首次final注册1097节点后，封板复核补出真实边界：一个原先只关联H1的事实被本次
新判断明确关联H2并暂缓，pending必须新增H2关系。newly-deferred-red.xml1失败/11通过。
停止经PID/命令/birth核对的本次隔离回归进程，保留.evidence-loop/final全部原始文件
及ABORTED.json；实际进程exit1，中断结果不当完整最终回归。没有终止用户原服务或库。
归约将显式assessment关系也计入关系集合；closure-fix.xml52通过/3.02秒/exit0。
重新以.evidence-loop/final2、.erfinal2*全新目录冻结1098节点、264源码/测试/资产文件、
全部已安装依赖及输入，精确运行原断言。尚未取得最终exit，不记E5通过。
final runner串行原交付/新双入口worker后再分3片，原120秒worker/浏览器门槛不放宽；
额外检查串行阶段结束后源码/依赖未变，防止继续跑已失效冻结。无删除原失败/fixture。

当前静态：受影响Ruff0；compileall src/apps/scripts/tests exit0；四个前端脚本node
--check均exit0；git diff --check exit0。全src Ruff仍74错误、exit1，分布32个文件，
逐一git hash-object与HEAD blob一致（全部未改），原始JSON在static-all.json，非本轮
引入也不称全仓lint绿。本轮最终静态随最后冻结再次记录，不借阶段结果隐藏全仓失败。

### 2026-10-23 完整请求、续接容量及Replay闭包（仍非最终验收）

原冻结final/final2因发现真实功能缺口中止，ABORTED.json、已执行exit/JUnit保留，
不能相加为最终完整回归。final2串行9通过/446.63秒，仅代表当时源码。浏览器最终批
也已中止；阶段190.07/182.77秒通过不冒充当前冻结通过。

已修新响应三键封套与冻结reference的null指导不一致、完整可执行诊断字段指导缺失、
纯诊断时间线误显示新模型字段，以及新H2显式暂缓关系丢失等负例。参考严格wire
阶段13通过/362.75秒；完整指导阶段23通过/226.74秒；具体失败XML保留。
输入可逆表示已至v6：值引用使用不与用户字符串冲突的保留前缀，完整逆映射核对，
原schema/hash不改。强化联合构造包含两个完整请求/分支：ON47477/63244字符、
56790/72557字节；OFF31186/39731字符、40499/49044字节，3通过/83.46秒。
这仍是实际构造的联合域，不是所有字段最大值同时可用或科学有效性保证。

新增实际父末批定向诊断→子worker测试复现子第二规划Prompt超限（request-closure、
closure-integrated），新增纯查询严格Replay复现易变plan_hash/墙钟污染模型输入
（query-replay-red）。已将稳定请求ID改绑owner/round/operation/原请求；完整计划hash
和实测耗时仍在原账本，只从新模型投影视图排除。原计划保存完整未删上下文。
工作视图仅保留每证据×版本最新判断、当前正反判断及所需事实，归档有数量/hash；
重复基线/旧无关视图不代替反证或自动清pending。修复仍须完整链路通过，不提前PASS。

原accepted observation按提案进入可评估事实，包括缓存提案实际child/control MAE、
配对规则、观察形成和样本身份，不增加独立样本、不建立第二评估器；OFF仍不暴露。
主线用中文标签显示原对照和两项MAE，原数值推荐/研究包/显式refit权威不变。
closure-projection-clean实际20通过/2.50秒/exit0。前一默认系统Temp测试虽20项执行绿，
会话清理WinError5实际exit1，保留，不修改全局权限，后续使用全新仓库内basetemp。
新变量control未训练该因子、消融后仍合法请求两个实际执行测试也已阶段通过。
无真实Provider/市场研究/外发/封存/原A/B训练/推送或CI，本轮其它证据轴仍NOT_RUN。

随后namespace-lineage实际1通过/207.48秒/exit0，包含父末批DQ04请求/完整分支与
数值→子首轮认识→第二轮原worker，四次loopback规划、父子各≤32fit、无refit，
父payload逐字未改。namespace-capacity为4通过/1失败/296.44秒/exit1，强化ON联合
构造仍超限，不能以其它四通过覆盖；继续收敛原工作视图的重复基线，不提高64k门槛。
新v7只对重复的证据owner/type命名空间做可逆等价引用，原content/hash不改；14个
投影/可读报告/工作视图测试2.52秒通过。此前query-replay-fix的第二规划严格回放已
完成，但末尾恢复/另批父子在工程源码变动期间触发原source mismatch，均按失败保留，
不绕过源身份；现在复测期间不改代码。closure-local48通过/2.68秒/exit0。

最终收敛前的固定源码阶段：namespace-replay三臂3通过/386.55秒，纯诊断也严格
回放、完成后重开0HTTP；cost-capacity5通过/331.41秒，cost-lineage1通过/234.72秒，
cost-tools6通过/363.14秒，均exit0。加强联合构造ON两轮47179/61653字符、
56492/70966字节，OFF31076/39577字符、40389/48890字节。原64k门槛不改。
工作视图阈值不是业务假设/问题上限：原完整事件保留，当前必要支持/反证和pending
始终优先；同一evidence×版本取最新判断，旧已评估中性记录和无关基线按显式归档。
不可容纳的必要证据仍预HTTP拒绝，不默删反证、不自动关闭或新增总结调用。
新诊断现在只实际计算请求变量，原方法其它列不全量重算。DQ02/03/04/06→更新与
窗口干预、未训练因子/消融后变量均实际执行通过；模型交付24charged fit加单独1refit，
fresh-process一致；One-shot仍一次冻结4槽/原单元，不借同批未来结果。
定向查询墙钟和完成数进入原resource_usage，OFF也保留实际成本但不见结果；父链
分别保留规划/Provider/自动诊断/查询/显式refit成本，金额/CPU未知不写0。
这些阶段证据不代替即将执行的最后源码完整验收，原失败仍保留。

### 2026-10-23 六工具与最后冻结前复核

本地实现提交8303e2a；格式提交1c35907/258cc2a只处理末尾空行，不改行为。
final3因diff-check发现新增EOF空行中止，源身份重新冻结；final4交叉检查发现DQ01/05
嵌套行范围投影遗漏而中止，ABORTED及原退出保留，二者都不作为最终回归通过。
新增nested-scope-red精确复现2失败后，将所有具名嵌套scope ID列表投影为数量/哈希；
完整列表仍在原accepted查询，原method-domain selected_train_hash保留，新query域另列
projection_hash，不重签旧包。范围字段不是测量指标；阈值、MAE、Pearson等数值不删。
新增evidence_query_projection_v2仅用于新请求投影；旧diagnostic枚举/原fixture不改。

six-tools-capacity实际10通过/404.63秒/exit0，覆盖六类请求各自实际分发→第二更新→
真实rolling504干预（DQ03另含查询回执后中断恢复）、OFF计算账本及加强ON/OFF容量。
browser-nested-stage实际新协议Chromium1通过/272.16秒/exit0：原双入口worker/同Mission
显式续接、父末批证据→子首轮、原推荐隔离、REPORT/成员hash/预测重算、两次显式refit、
新进程/源篡改门禁、700px/1280px截图、刷新及三次重开零增量。原A/B未改/未训。
最后只读数值显示补充每个对象/control/范围和原配对差，53项display-last通过/2.51秒；
query范围中不可得不当反证。受改Ruff及diff-check均exit0。当前下一步为新目录完整
冻结全仓/六模式浏览器/静态，现有阶段数不相加、不借旧失败掩盖未完成E5。

### 2026-10-23 最终冻结仍在执行：并行浏览器原始失败

冻结实现230cf1e；final5登记1118唯一节点、265源码/测试文件及依赖/输入，串行交付
part0实际9通过/464.10秒/exit0，后续三组尚未完成，不能提前按JUnit计数推通过。
受改Ruff/compileall/四个JS语法/diff-check均0；全src Ruff74项/32文件仍exit1，
各offender的git内容均与原e361b0e相同，不用“新作用域绿”代替全src绿。

browser-final5与三组回归并行，完整六节点3通过/3失败/1156.62秒/实际exit1，
source/deps/start/end身份保留；V24/V25/新协议均在原120秒“已完成”徽标等待失败，
不改超时/断言。其后台记录各两轮/24fit且最终completed，但这不是界面验收通过。
失败report保留page_crashes=[]，失败分支未完整落page_errors/FAIL截图，不能由字段
缺失推定没有JS错误；以原trace及事件/模型/服务器记录为准。后续在全仓结束后同源
完整六模式串行复核，不以只补三项、阶段272秒通过或后台完成覆盖此次原失败。
并行就绪性能/环境影响仍为开放边界，不提前称普遍稳定。

离线材料已从final5串行provided_start子首轮的原RuntimeDB冻结Prompt提取；原
prompt hash a066c770029feefda0f4核对原plan通过，保留2个父末批pending关系。
live-preparation-final输出12份载荷，逐成员SHA256核对，最大43956字符/44325字节，
Provider token未知，准备HTTP/fit均0。原context与来源指针/hash留本地，实际Provider
未授权/未运行。后续若外部验证，按下段字段/资源新授权，不复用旧Live剩余额度。

### 2026-10-23 旧最小摘要上下文回归修复（需重新冻结）

final5分组2在旧test_focused_b5_increment的六个origin/screen/terminal用例失败，
不是历史环境失败。legacy-summary-red独立原断言复现6失败/2.57秒/exit1：新可选
research_protocol_id在_campaign_summary被直接读取，旧SimpleNamespace没有此属性。
修为缺省None走旧协议，仅兼容调度，不改变筛选/终态数学；没有改旧测试/fixture。
原六用例legacy-summary-green6通过/2.27秒；连同新状态/诊断/投影/报告的完整
summary-compat-fast-all59通过/2.48秒/exit0。一次-k预检仅执行6、其余90 deselected，
明确不把它称为59项或完整回归，后续已用精确node函数选择验证。

final5已按真实回归中止，ABORTED、part0原9通过/464.10秒、分组2原六失败进度及
原exit保留，不以单项复跑覆盖全仓。下一冻结先独立完整六模式浏览器，再跑全仓，
不再把重型回归和界面120秒就绪同时施压；并行失效仍报告，不放宽原断言。
230cf1e来源的离线材料保留为阶段证据；最后冻结后须从新上下文重新生成/核验，
不得改写旧source/hash冒充当前。E5仍未完成，B/C/D/E无新授权仍NOT_RUN。

### 2026-10-23 修复源的独立六模式验收

修复提交384102d；browser-final6实际完整六模式6通过/848.50秒/exit0，原断言和
120秒门槛不改。start/end源码265文件、依赖、pyproject输入一致；五个Agent模式
report均包含完整page_errors=[]/page_crashes=[]及截图/动作/计数，另一个旧工作区
原节点也通过。正常隔离调度验证通过不抹掉前次并行1156.62秒的3失败，不能据此
宣称已验证满并行负载下的120秒就绪SLO。现在同源final6全仓冻结正在执行，尚未
结束不得给E5 PASS，也不把59项或单独浏览器结果当全仓退出。

当前384102d冻结源的离线材料已另存，不重签230cf1e阶段材料：
`.evidence-loop/live-context-final2.json`来自final6串行provided_start子研究的原始
`prompt:1`，原Prompt hash `fbbc929467b32fa914a5`，父末批pending关系2条。
`.evidence-loop/live-context-final2.source.json`保存源DB/namespace/commit；
`.evidence-loop/live-preparation-final2/PREPARATION.json`及12份载荷的输入与逐成员SHA256
全部核对相等，最大43958字符/44327 UTF8字节，Provider token仍未知。
命令仅离线构造，0发送/fit，`NOT_RUN_NEW_AUTHORIZATION_REQUIRED`。
六模式当前截图已人工视觉查看700/1440主线与REPORT：中文问题/主张/竞争解释/原判断/
未决/pending具名显示，长来源ID可换行；这只是助手视觉工程复核，不是用户理解验收。

### final6串行实际轨迹（完整回归仍在运行）

`tests/test_evidence_research_workspace.py::test_original_queue_worker_executes_new_protocol_for_both_entries`
两入口已在final6 part0真实通过；以下只读该批provided_start原campaign.json，不额外执行研究。
源目录`.erfinal60/test_original_queue_worker_exe1/project/focused_campaigns/`，合成输入
SHA256 `cb063f4b608912b32e4ac2ea905a1d542389bbae80a6c974c51f97e129bc457b`。
父`persistent-77cbfeaf6bbc6beb5de8f077`，子`persistent-99ccf896745d0001f5b1cfec`。

| 阶段/实际对象 | 实际control/改动 | 原MAE |
|---|---|---|
| 父起点user_start | StandardScaler+Ridge(alpha=10)，base_lags，expanding | 0.007345684420938911 |
| 父R1 r1_c1_ecea3511 | user_start→features；窗口仍expanding | 0.007331065989772755 |
| 父R1 r1_c2_b978aae9 | user_start→training_window rolling504；原特征不变 | 0.007377579351201807 |
| 父R2 r2_c1_de043b5a | 从R1C1完整继承特征，只改rolling504 | 0.0073987905201885985 |
| 子起点user_start | 显式选择较差且未推荐的父R1C2；重算rolling504起点 | 0.007377579351201807 |
| 子R1 r1_c1_ecea3511 | 从子起点加特征，保留rolling504 | 0.0073987905201885985 |
| 子R2 r2_c1_111d85cf | 从子R1完整继承特征，只改rolling756 | 0.007349605954063493 |

父总charged fit28，子24，合计52≤64，已包括各自对照/起点，不免费复制父预测；
各两次逻辑规划、Provider HTTP0，无模型包refit。问题forecast_quality稳定，有限规则
method_effect v1保留；父两次update判断数0/4，子2/2；两末批均保留2条pending关系。
这些规则判断明确not_distinguished，不是Live提出新机制或假设版本演进的证据；
多假设/版本/相反结果/关系暂缓由单独结构和整链fixture覆盖，不能混成科学理解PASS。
两研究均`no_improvement`，冻结推荐均各自user_start，原选择原因
`research_candidate_did_not_qualify_to_replace_start`、推荐相对起点增益0。
筛选仍相对`best_fixed_control_or_user_start`且0.0025，不能只看R1C1比起点小降就称通过。
最佳研究候选与冻结推荐是两个原字段：父最佳研究R1C1，子最佳研究R2C1；未改推荐器。
这条轨迹展示正常“不替换起点”的闭环，不证明规则/Agent有增量选择价值。
原父payload不变、诊断可见性/续接binding篡改拒绝亦由原测试断言；其余三组仍需完整退出。

final6 part1运行中已生成完整父末批诊断续接和新模型回执；此处只列实际产物，完整
JUnit/退出仍须part1结束后绑定，不先把该组判为通过：

- `.erfinal61/test_parent_last_query_and_ful0/project/focused_campaigns/`：父
  `persistent-0b19c6e7255cb94b998707dc`两批/20fit，末批请求last_tail为DQ04，
  结果`query:154d25801bb1f76d0ed633758336e4e71287ffeef378fad9f0f655926d0b7134`。
  显式子`persistent-dd52e6deb23427834beae45f`两批/24fit；其首批计划对该父query
  以method_effect v1作not_distinguished/evaluated，理由“规则不作机制归因”，
  未决仍为机制及独立预测增益未确立。父请求完整branches和原owner保留，子末批再有
  自己的DQ04请求/结果。父/子各完成1查询，新增fit/Provider请求均0，墙钟分别
  0.11142080000718124/0.11452040000585839秒，CPU未知；当前成本与祖先成本分列。
  两个研究各2次loopback规划HTTP，合计4；这是本地assistant_authored_fixture，
  绝非4次真实Provider或LLM质量证据。父/子末批各1条pending关系。
- `.erfinal61/test_both_directions_keep_full0/explicit-bundle/bundle.json`：
  实际候选r2_c1_aa2c45a1，Ridge(alpha=1)、rolling504、base_lags＋
  gen_mean=rolling_mean(return_1,5)，6列，实际504训练行，额外reserved_fit_calls=1，
  refit-8bcddaedbdb3438eb636d819485e2ba8。原model_sha256
  `b146ac6bac4760a621a94ecc295a3f76ebff4fb1d6ac63989aaeab3cc969442f`。
  这是独立合成方法交付测试，不是上述alpha10 A起点或所有者原模型重训。
  测试原子进程命令以该bundle/原state/unlabeled.json调用predict_model_bundle，
  断言子进程exit0与当前数组rtol=1e-8/atol=1e-12一致，最终case状态待整组JUnit核对。

### 本轮工程复核的实际操作入口

若需查看本轮隔离合成轨迹，可在空闲端口用已有启动脚本打开该测试库（不要替换原A/B库，
不要从本命令推断任何新真实数据/Provider授权）：

```powershell
& 'D:/AI Agent/finance_forecast_agent_v1/scripts/start_workspace.ps1' -StateDb 'D:/AI Agent/finance_forecast_agent_v1/.erfinal60/test_original_queue_worker_exe1/state.sqlite3' -ProjectDir 'D:/AI Agent/finance_forecast_agent_v1/.erfinal60/test_original_queue_worker_exe1/project' -Port 8516
```

此为操作说明，非本轮另一次已执行启动。原浏览器实测由pytest在独立临时库/端口启动。
查看父/子研究的“研究”页可对照上述轨迹；“事实来源与诊断数值”显示原数值及范围，
技术原文仍可展开。成果页推荐对象独立于当前查看候选。导出研究包先读REPORT.html，
不要拿它做新预测。已有受信模型包下载只读；生成新模型包必须看到并确认额外1次refit。
旧包若源/环境不匹配，保留拒绝，不以新签hash或重训原B绕过。
新建流程第一步选V2.5特征＋窗口，第三步显式选证据驱动协议；未选仍旧协议。
真实数据/Live的点击提交仍须新的适用授权；本说明只给产品操作路径，不执行它们。

### 离线试验材料与下一次授权边界（未运行，不追加本轮权限）

`scripts/prepare_evidence_live_challenges.py --context <新协议冻结Prompt.json> --out <全新目录>`
只准备材料，不读取Key、不建Provider、不训练/发送；输出六对/十二份明确标注
assistant_authored_counterfactual_fixture的载荷、原context/hash、逐成员SHA256、实际
JSON字符/UTF8字节及rubric。token未知，不以字符冒充token。假设事实是练习覆盖层，
不是新接受的市场事实；其响应不能直接提交原Campaign执行。

准备的六对：相关不等于有害；绝对波动/相对误差；单对象/共同掩码双对象尾部；
少尾部/更多尾部样本；窗口正反结果与竞争原因；父末批正反事实及两个版本的pending。
允许多个合理动作、停止/审核/暂缓；不以解释变长、强制换轴、填满实验或小MAE改善
判成功。原回答/失败/未知投递全部保留，盲序人工逐题审阅事实忠实、反证/不足、
竞争解释、取证分支、版本/来源和合法工具成本；结构测试不能代替这一步。

实际发送前须新明确批准实际模型/Provider/effective配置、thinking、免费保护、
输出token、HTTP/重试、单次超时/活动时间和以下逐项字段，不继承本轮或旧批剩余额度：

- 冻结SPY日频next-session/forecast_only任务合同、起点完整方法/alpha/seed/内置组，
  许可特征AST和expanding/rolling504/756；不含拟合后的Ridge系数/模型文件。
- 获准开发汇总/折指标、诊断数值/阈值/配对方向/有效n/low_support、训练截止及
  行范围数量/hash、列名和来源。DQ01可含Scaler均值/尺度等训练汇总，须显式列入
  新发送审阅，不能把“诊断”一词当作无限白名单；原固定诊断比较权重[0.5,0.5]
  不是sample_weight，也不应隐瞒该字段。完整具名scope行清单留在本地审计。
- 当前问题/假设版本、原判断/竞争解释、请求分支及关系级pending；仅本臂当时
  已接受历史和显式父研究获准证据。安全失败类型/预留fit可发，原异常文本/堆栈不发。
- 已审核文献只在另获准的权限范围内投影，受限摘录/派生叙述不经状态/研究包旁路。
- 不发原始行情、逐行标签/预测、权重文件、凭据、客户资料或未获准个人备注；
  具体冻结载荷须审阅，新增字段/来源不能由旧同意推定。金额/计费无法确认时停。

可选§10.4的16次逻辑小试仅是十二份新支持包语义练习＋单条父两批/子两批四次
规划；每Campaign≤32总charged fit、父子≤64（含各自基线/起点）、本小试refit=0。
HTTP不重试时仍最多16真实HTTP，任何重试/模型切换都另占获准预算。所有这些都是
待新批准的提案，不是执行授权。两种支持包对同一批材料各自调用、多臂全流程或
多seed比较需要额外预登记及预算，不能塞进这16次或据单轨迹宣称C研究选择价值。
公平试验须同数据/起点/工具/权限/底模有效配置/资源，own-lineage和结果缓存隔离，
同时报告best_research与冻结recommended、失败/取证/规划/HTTP/charged fit成本。

B真实行为、C研究选择、D独立预测、E真人价值本轮均NOT_RUN；没有读取独立确认标签。
所有者原A/B已操作，G6理解复核仍开放：本人只读辨认推荐/实际control/正反结果/
未决/包与额外fit的区别，记录帮助、错误理解与实际使用；再按原条件安排独立用户。
原包源不匹配没有匹配运行时即BLOCKED，不重签/重训代替，不由助手代签理解/劳动节省。

# Finance Forecast Agent：证据驱动研究闭环与全周期路线——唯一实施方案

版本：交接 v1.1（对抗复审修订）；日期：2026-10-23。

状态：待用户将本包作为实施指令转交；本次仅形成方案。后文“应当实现”“验收”均是要求，不是已完成声明。包内 02 是操作提示，03 是本方案的条款索引，04 是依据，05 是本次复审记录，均不另立施工路线。v1.1 取代 v1.0 交接要求；旧包保留作来源。本次不改变近期三轮目标，不扩大实施权限。

## 0. 设计目标和实际基线

### 0.1 产品仍然帮助用户改进预测方案

用户可以只有研究目标，也可以带受支持的配置和因子。系统应建立或接入起点，依据实际事实与方法知识提出假设，通过真实取证或受控模型修改获得结果，再修订认识和选择下一步，最后交付可使用的完整预测方案与有边界的结论。

近期同时推进两个核心：决策更有依据，实施工具更多样且准确。诊断、记忆、解释和页面服务于这两个核心，不替代模型研究。不要求先解释清所有病因才准改进，也不要求每轮换轴、填满槽、找到赢家。没有异常时允许明确标为领域启发的合理探索。

事实、原因判断、数值采用分开。高相关不等于有害；消融有效不自动证明冗余是原因；窗口改善不单独识别历史失效；成绩好不证明解释正确，差候选也可以继续提供研究线索。

### 0.2 本次核对的实际仓库

- 项目：summerming1/finance-forecast-agent。
- 目录：D:/AI Agent/finance_forecast_agent_v1。
- 分支：feat/mission-research-v2。
- 实际本地 HEAD：e361b0ef3418b09f7c5168caf5a381870634b9e3；本次检查时 tracked 工作区干净。
- 外部主稿历史静态基线：5d3f57687592b46693e687cc0611bd492adac065；它不是实施时必须回退的基线。
- 来源：v1.3 主稿及本次审核；来源身份见 04。

实施开始重新检查分支、HEAD、工作区和现行批准文件；保留后续提交、用户修改、未跟踪证据。不 reset、clean、强制回退或覆盖原库。以下代码位置按 e361b0e，之后以等价职责定位。

### 0.3 已完成的能力复用，不重复修补

V2.5 两轴、实际控制完整继承、窗口实际训练、研究更新、缓存观察分离、可信窗口 refit、双入口、恢复和续接已有工程实现。后续已修大请求通信、One-shot 快速预算、范围选项、冻结推荐 Benchmark，以及中文事实投影、REPORT.html、导航和续接等问题。

最新验收索引报告 1023 项：1014 passed、2 历史 failed、7 skipped，实际 exit1。最终相关浏览器为四模式加旧工作区分别通过；旧失败和负载风险仍保留。本次核对 246 个源码/测试文件与索引逐文件哈希相同，但没有重跑该回归。

有限 Live 已完成两次规划和一个新候选；第二次重复相同公式，更新通用、与示例接近。技术闭环不能证明实质反馈驱动选择。这是本轮要改进的重点，不再以“字段合法”“引用正确”代替研究行为。

原 A/B 已由所有者实际操作，不得退回“从未试用”；理解复核、独立用户、研究选择价值和独立预测效果各自开放。

## 1. 本轮范围、权限和交付定义

### 1.1 本轮必须一起交付

1. 初始事实画像及定向诊断的真实分发，复用已有数值，补 DQ-03/04/06 的实际缺口。
2. 稳定问题、假设版本、证据请求和有来源的研究状态；原事实权威不变。
3. 新版本响应中，诊断/训练/获准失败等实际证据进入认识更新，并影响同次响应选择的下一步。
4. 两批研究及一次显式续接贯通；子研究首次获准规划能处理父研究末批未决证据。
5. 继续使用现有特征/窗口工具实际修改模型，保留完整继承、实际训练、推荐和可信模型交付。
6. 原工作区和研究包显示同一研究主线；查看不生成新解释、训练或调用。
7. 工程、真实语义、选择价值、独立预测和真人价值分轴交付。

### 1.2 本轮不实施的能力

裁剪、时间权重、参数搜索、新模型族、RF 研究替换、四组合、学习式特征筛选、自动知识检索、Memory 策略学习、任意代码、自动数据更新、前瞻服务、自动发布和交易均不随本轮实施。它们的具体后续位置见第 13 节。

主任务保持 SPY 日频 next-session 调整收盘收益回归、forecast_only、均匀 MAE、0.0025 相对开发筛选；本轮研究候选仍为起点冻结的 StandardScaler＋Ridge、参数/seed/内置组固定，uniform 训练权重。现有生成特征累计最多 2 条，窗口仍为 expanding/rolling504/756。固定 RF/GBDT/朴素对照不等于开放研究模型替换。

### 1.3 工程与外部验证权限分开

用户明确转交“按本包实施”后，拟批准本轮代码、原 UI、文档、单元/集成/worker/fit/predict/refit、隔离合成数据与测试库、本地模拟 HTTP、严格 Replay、适用浏览器、静态及受影响全仓回归；可分批仅提交本轮修改的本地 commit。

这不是新真实 Provider、真实行情研究、客户材料外发、封存标签、生产迁移、全局权限、远端 CI 或推送授权。既有授权只按其实际范围复用，不重复索取有效授权，也不把旧批次剩余额度当新授权。仅发现 Key、已保存命令前缀或旧 Live 记录不构成调用许可。

不实施本项目修改的审核 AI 只生成交接包，不将正式文件或 ADR 标记 accepted。实施 AI 接到用户可信实施指令后，在 E0 记录授权来源和范围；无需每批再问相同工程批准。

## 2. 新旧协议：新增研究语义，不改旧模型身份

### 2.1 版本和唯一表示

建议在既有 research_options 中增加显式 `research_protocol_id=evidence_research_v1`，仍使用 `change_scope=feature_window` 和原方法能力域。新响应版本为 `evidence_research_advice_v1`，其中认识容器使用新的 `evidence_research_update_v1` 判别值，不能沿用旧 `research_update_v1` 却改变其含义。最终字段路径由 E0 对照现有代码一次冻结；若已有等价字段则复用，不新增同义权威。

不因为增加问题/证据状态就升级模型候选数学语义：原 CandidateConfig v4、FeatureProgram、TrainingPolicy 和完整方法身份继续复用。研究协议身份进入执行合同、Prompt、计划、恢复/续接/报告绑定，不混入“同最终方法”的纯方法身份。

旧对象缺新字段时仍按旧协议 dispatch，不能在旧序列化中偷偷补默认值、丢弃新字段、重算旧 hash、改 golden fixture。旧响应的首轮/One-shot update=null 规则不变。

新响应沿现有 hypotheses 动作列表复用原编译职责；新增关系及诊断请求须有新版本的严格校验和执行映射，并完整冻结在计划中。现有 diagnose 仅接受 residual_summary/fold_summary，不能只在 Prompt 增加 DQ 名称，或丢掉查询参数后退回旧摘要；旧枚举分支原样保留。

### 2.2 新响应内只保留一份实际认识维护

新响应使用一个 `research_update` 容器承载本次状态初始化/变更、已有假设的证据判断和 choice_reason；动作列表仍为原 hypotheses。不要再建立含义相同的 reflection、actual_update、summary_update 等并行字段。

逻辑内容至少包括：base_state_hash，问题/假设的受限创建或版本变更，evidence_assessments，安排变化及理由。E0 给出唯一 schema 与示例，不要求逻辑角色各建表。

- 全新课题：可以基于已接受基线、画像或明确领域启发初始化问题/假设；没有上一批实验时，不伪造“上轮研究结果”。
- 有未处理的可见证据：在同次响应中处理与当前问题有关的证据，或明确暂缓及理由，再给本次动作/停止/审核；不能只看 round_index，也不要求把所有历史原因解释完才可继续。处理范围按第 3.2 节绑定。
- 新协议子 Campaign 首次规划：可以处理父研究末批证据；旧协议仍保持原规则。
- One-shot 新协议：一次响应可处理进入本次规划前已有的合格证据，并一次冻结全部提案；不能伪造同批未来结果或批间更新。
- 末批之后：只确定性整理事实/差异、标记 pending_evidence；没有获准调用就不生成新的机制解释。

原 research_design 中描述新实验预期的 feedback_update 仍是事前判断；原确定性 actual_feedback_update 仍是数值观察审计。它们与新 research_update 不互相代替。

合理参考臂的策略合同在运行前冻结为 reference 时，允许 `research_update=null` 及缺少新问题关系；适配器仅做合法机械映射，不补造认识文字。不得强迫参考臂通过新支持专属的语义门禁，也不允许回答自行切换 reference 规避已冻结策略。工具域和可见性权限仍核对一致。

### 2.3 有界政策

新协议保留同时活跃假设总计最多 3 个；一个实验可以关联多个假设，不按假设数量增加槽数。问题由这些假设及尚未解决事项关联呈现，不再另加“3 个活跃问题”“12 个待研究问题”的独立业务限额。历史事件不删除；当前工作视图有界，省略项保留可追溯引用、数量和暂缓状态，不能自动当成已研究结束。

新容器包含初始化、版本变更和证据判断，未经容量测量的 1600 字符不再作为本包已验证的固定合同。E0 必须在调用前冻结：字符串值总量（含 ID/枚举的计量规则）、单字段、数组数量、嵌套深度及完整响应规模上限，并以实际序列化检查完整 Prompt 的原 64000 字符限制；字符、UTF-8 字节和 Provider token 分别记录，不互相冒充。旧协议 1200/240/items 等容量原样保留，不提高所有旧响应上限。

E0 必须用完整新 schema 通过联合边界构造，至少支持：3 活跃假设、两槽结果、长备注、两生成特征、父末批证据、必要正反证据和各自权限。若全部字段最大值不能同时支持，公开合法联合域及超过时的行为。只允许确定性去重、等价引用与显式暂缓；不静默丢反证、不让模型靠压缩解释通过、不新增摘要调用。未通过此构造不能声称合同已冻结；无须为未激活历史建设全量检索或调度平台。

新 Prompt 不能用一个可直接照抄的成功公式/认识段落作为默认答案。尽量使用字段描述和明确不可执行的占位示例；模型提案仍需输出完整合法 AST，不把内部压缩引用当可执行表达式。表示可逆和 schema 通过不等于模型理解。

## 3. 问题、假设、证据与状态的最小合同

### 3.1 角色和身份

| 角色 | 必须保存的内容 | 唯一权威/边界 |
|---|---|---|
| 问题 | 稳定 ID、用户目标关联、范围、依据、重要性、安排状态 | 原 RuntimeDB 中事件及引用；不是第二套任务 |
| 假设版本 | 稳定问题关联、hypothesis ID/version、具体主张、条件、正反依据、竞争解释、生命周期 | 改主张创建关联新版本；不覆盖旧文本 |
| 证据请求 | 请求 ID、所缺信息、工具/参数、对象/control、相关假设、预期及结果行动分支、依赖、资源 | 一个请求一项真实操作；请求不是已经取得的证据 |
| 证据 | owner Campaign/实验/动作、形成时点、实际行范围、数据/方法/预测/规则身份、结果和来源 | 原已接受结果/产物；不靠手填摘要自证 |
| 判断更新 | 对哪个原版本、实际新增何种证据、局部支持/削弱/冲突/未区分/不足/不变/执行不完整、未决和理由 | Advisor 语义陈述，不得更改数值与采用 |
| 当前状态 | 活跃问题/假设、必要支持与反证、待处理证据、请求、当前推荐引用和预算 | 从原事件/冻结计划重建的工作视图；JSON 是投影 |

证据 ID 至少绑定所属 Campaign 与实际内容身份，不能把 baseline_ridge、r1_c1 等短 ID 当跨课题全局身份。同一实验可以服务多个假设，反向比较或再次引用不增加独立证据。

安排状态与证据判断分开：待研究/活跃/暂缓/受阻/结束，与无证据/局部支持/削弱/冲突/无法区分等不是同一个枚举。

### 3.2 原子接受、已处理标记和恢复

按原数据/Provider 记录与计划机制落地：

1. 原始响应按既有规则保留，含非法回答和未知投递状态。
2. 新 schema、引用可见性、base_state_hash、动作编译及资源预检全部通过后，将 research_update 与计划一起冻结。
3. 当前认识视图仅归约已接受计划内的更新；其 plan_hash/operation key 是幂等边界，不因响应已收到就认为状态已应用。
4. 非法动作导致本批未接受时，不吞掉待处理证据、不推广其中新判断；原非法响应及已发生费用保留，之前已接受工作不回滚。
5. 已接受计划中的 update 与执行结果分别记录。执行后新增证据成为待处理；运行完成本身不能自动把科学判断改成“支持”。
6. request_review、stop 的合法认识更新也须保存；恢复从同一冻结计划读取，不再次调用或重复应用。

“已处理”不能是证据上的全局布尔值。用原计划中实际判断的 `(evidence_id, hypothesis_id, hypothesis_version)` 关系归约：只对被明确评估的关系记已评估；声明暂缓的关系仍待处理，执行失败只形成执行事实而非科学反证。同一诊断被 H1 评估，不代表 H2 已评估；修改主张产生新版本后，可复用同一事实重新判断，但不算新独立观测。无须每轮机械重评全部历史；对本次选择依赖的可见新证据应给判断或明确不足，对其它证据可以有理由暂缓。全新问题尚无关联的结果可保持待分配，不强制为它创造假设。

这些关系、暂缓及幂等键都在已有冻结计划/原事件内保存，pending 是其确定性投影，不再增加一份可独立修改的处理状态表。末批结果只能新增事实和待处理关系；没有下一次获准规划，不伪造语义结论。已有判断的权限跟随其实际来源：不能借父状态或文字摘要暴露本轮无权查看的诊断。

不要求新建通用事务/恢复引擎。复用原 RuntimeDB、冻结计划、不可变 artifact 和受控导出；文件孤儿不能成为第二权威。

### 3.3 证据失效不等于解释变弱

解释被削弱只更新认识，不能让 LLM 单方面撤销合法数值推荐。数据/预测/执行确实不符合合同，才由确定性门禁标记相关证据不合格并阻止受影响交付。

保留原冻结推荐及其 hash，追加失效原因和当前使用资格；不删除坏实验后悄悄重选“成功”。不涉及失效证据的合法结果继续可用。证据修复/新证据出现时，重新判断须追加版本，不倒写历史。

## 4. 初始画像与六类定向诊断

### 4.1 两级获取

基线接受后、首次 Advisor 前生成必要基础画像：数据/任务/时间合同、实际列与成熟范围、起点/固定对照、已有残差/分折/训练统计、能力、预算和未知项。仅复用或纯计算，不额外拟合，不调用 LLM；保存形成身份和计算成本。

主动 diagnose 占原提案槽，每槽一种冻结诊断，最多两个已接受、合法可比较的对象；不能在一种“综合诊断”里隐含统计搜索。DQ-01/02/03/05 已有部分优先复用。

E0 对新协议冻结一份可执行诊断请求表示，至少含类型/版本、精确对象引用、具名变量或变量对、范围引用及固定参数；具名变量只能引用许可原列或已获准 AST，不为诊断自由生成额外公式。引用来源、成熟/可用时点、参数和资源在执行前校验，执行回执核对实际读取的对象/列/行及所用函数。其开销是一次有界查询，不能默认扫描全部列、所有列对、滞后或模型，再只返回最有利结果。

| 类型 | 本轮实际输出 | 范围/限制 |
|---|---|---|
| DQ-01 执行核对 | 数据/标签/列/时点/成熟/实际训练回执的引用与不一致 | 不读取确认；历史价格不自动证明 PIT |
| DQ-02 预测表现 | MAE、分折配对误差、残差/幅度及明确参照 | 同共同评价目标；不能把绝对 MAE 随波动变大直接称退化 |
| DQ-03 因子关系 | 具名 Pearson/Spearman、常量、样本数、冻结时期差异 | 训练统计用每折 selected_train；公共历史比较用冻结校准范围，二者分开 |
| DQ-04 极值与误差 | 指定因子 q01/q99、尾部掩码/比例；单对象描述，或两个已接受对象的配对损失 | 单对象只报自身尾部/非尾部误差及计数，不声称相对退化；双对象使用同公式、control 每折 selected_train 阈值及同掩码；不删目标 |
| DQ-05 状态/时期 | 原固定折、波动率组的相对误差和 n | 不按结果挑好年份，不暗扩网格 |
| DQ-06 时序关联 | 因子—对应成熟目标、预测—目标的具名 Pearson/Spearman、n、常量/未知 | 分清训练关系与共同开发 OOF 预测关系；不是横截面 IC、因果或增量证明 |

### 4.2 必须冻结的参数和小样本行为

- 沿原原始数据/AST/行数能力上限；每查询最多两个对象。DQ-03/06 总计最多 8 个事前具名变量对，不是每个对象各 8 对或一次返回全矩阵；两个统计函数及原固定折属于该声明范围。DQ-04 首版每次只检一个具名因子。未知类型/自由 SQL/任意函数/滞后搜索拒绝；不加第三个自动查询入口。
- 诊断默认 q01/q99、线性分位数算法，固定类型参数不在看到结果后调整。公开每折实际样本数/阈值来源/比较行身份。
- 数值可计算与科学支持分开：Pearson/Spearman 至少两对有限且非恒定的配对值才返回系数，恒定/不足则 null 并给原因；并列秩算法、近常量数值容差、缺值政策在 E0 固定。缺值不改变主评价目标或改算删行后的主 MAE；诊断有限配对子集必须单列原 n/有效 n/排除原因。
- 不把 n=20、尾部 n=10 写成通用“可靠/不可靠”分界。若保留它们，只作为预先冻结的 low_support 提醒，不隐藏可计算描述值，不在越线后自动宣告支持/反证。尾部至少报告每折 n_tail/n_other、两对象有效配对 n；零尾部为不可估，少尾部为证据薄弱，任何较大 n 也不自动保证独立性、显著性或外推。首版不默认输出 IID p 值，也不顺势新建置换/显著性平台。
- 252 个目标、近似同分布下，q01/q99 尾部总数期望约 5，故 insufficient 是正常可交付结果，不得靠放宽阈值或制造数据取得“明确结论”。
- 新特征在 control 模型中未使用时，可在其许可原始历史和训练范围纯计算同一合法公式来定义阈值；注明“研究变量，非 control 训练列”，不隐式拟合新 control。删特征后仍能引用原受检变量。
- DQ-04 的冻结对照阈值，与后续裁剪工具在候选 selected_train 学习的阈值，不是同一份参数。
- DQ-06 首版只做同一目标身份下逐行对齐的同期关系，不搜索滞后。允许对预先声明的非连续日期集合计算 Pearson/Spearman，并同时给原分折结果；聚合值只是这些行的描述，不称连续轨迹或独立样本。禁止把相隔多日/跨折的相邻数组行误当相邻交易日来 shift、差分或构造新滞后。缺训练预测继续 unknown，不为查看页面额外拟合。
- 不要求新增显著性平台、自动因果发现或全资产风格库。没有相应数据/识别条件就明确不可得。

### 4.3 结果接线与缓存

diagnose 不再仅根据 kind 标签返回同一通用 MAE 摘要。每种类型真实调用其对应数值函数，结果作为有界可见证据接入下一轮的 EvidenceIndex、新认识更新和研究包。

缓存键至少包含类型/版本、参数、对象及完整方法、数据修订、实际训练/校准/评价范围、control、阈值和公式/掩码定义、必要代码身份。只根据短候选 ID 或“尾部诊断”名称缓存不合格。

保存预测身份、比较身份和观察形成身份的原区分；相同预测复用不是新的独立样本，同一已取得结果的多次引用不重复计生成成本，新查询实际计算/读取仍记账。缓存与不可用状态也进入请求收据。完整流程对照的缓存不得让一臂直接看见另一臂未自行取得的结果；默认沿原隔离命名空间，不新增跨臂复用优化。

自动诊断和已有产物引用保持权限筛选先于投影。OFF 不通过状态摘要、父研究更新或旁路引用得到原本不可见内容；如新对照另有明确同信息策略，则以新合同冻结，不能偷偷改变旧 OFF。

## 5. 规划、取证、续接与费用

| 项目 | Adaptive Batch | One-shot |
|---|---|---|
| 一次 Campaign 的逻辑规划 | 最多 2 次 | 1 次 |
| 提案槽 | 每次最多 2，总计 4 | 一次冻结最多 4 |
| 执行单元 | 沿原单元，最多 2 项 | 沿原单元，不能把未来单元当已接受 control |
| 同批是否可看结果改计划 | 不可；依赖结果移下一批 | 不可；无隐藏第二次规划 |
| 认识处理 | 同一次获准响应先处理可见证据再选动作 | 可处理进入本次规划前的证据，不伪造同批反馈 |

最多 3 个活跃假设不等于多出实验槽。diagnose、重复、无效、停止/审核等沿实际原槽/决定结算语义，不提供新免费重试。正常 HTTP 瞬态重试沿原政策，逻辑规划与实际 HTTP 次数分开；未知投递/计费保持 unknown，不承诺恰好一次收费。

单 Campaign 沿原 `max_fit_calls≤32`：这是包含固定模型基线、需要独立拟合的用户起点、研究候选及失败/中断保留预留额的 `charged_fit_calls` 上限，不是额外 32 次研究候选 fit。保留 reserved/observed_started/observed_completed 三种口径。当前三种估计器基线×4折=12；若用户起点另占4，则32中最多剩16个正常候选fit，即4候选×4折；goal 默认起点若已由基线覆盖不重复算。失败/重试仍消费剩余额度，不能按成功数重置。

每折一次拟合、预测完整63目标，不重设共同目标。朴素统计对照沿原真实计费语义；Scaler fit、额外 predict、统计计算另列操作量，不谎称已包含为新的估计器fit或完全无成本。显式模型refit是另获准的1次额外估计器fit，不偷塞进候选余额。

诊断硬边界为槽数、固定类型、输入规模和操作数量；记录实际计算 wall、缓存和读取，达到获准查询/计算预算后拒绝后续请求。若仅有事后耗时检查，准确称软耗时门槛，不能假称硬 CPU 截止；不为此新增执行服务。

### 5.1 显式续接

仍是同 Mission 下的新 Campaign；保留实际完整父方法、原曝光、已发生费用和原任务事实。当前同快照续接规则保持，不借本轮添加新数据自动更新。

新增父研究状态快照引用：问题/假设版本、必要正反证据、未处理末批证据、适用性和权限。默认不搬运全部历史长文本，也不免费复用父预测作为子研究的新训练结果。旧 `prediction_reuse=False` 等原义不静默改变。

子首次规划处理父末批，不能让 `round_index=1` 强制丢弃。父源/环境/数据/协议不匹配时按门禁拒绝，不改 hash 续跑；跨协议读取旧事实需要显式、只读、可核验的适配，本轮默认拒绝无法验证的迁移，不建设旧环境管理平台。

### 5.2 场景预算必须覆盖第三次及以后规划

父两次规划后至少一次子规划，已经至少三次，不能叫两次规划闭环。

单条工程演示可预登记最多两个 Campaign（父＋子），每个≤32个上述计费fit/2规划，共≤64个计费fit/4规划；64已含各自的固定基线/起点预留额，不能再额外加一轮基线。One-shot 各自仍≤1规划。该示例最多另计 1 次显式 refit，新包成功时实际 1 fit；不是金融实验证据或授权。两个入口各自使用隔离案例，不能拿此额度作为所有测试共享且无限复用的真实资源许可。

真实试验需逐场景另批准项目累计预算。每次显式续接都是新增授权或已有明确项目政策下的消费，不是换 ID 免费重置。

## 6. 决策行为和可展示案例

### 6.1 每项选择应可检验

给出当前事实/领域启发、反解释、尚缺证据、真实可用工具、对照、不同结果会如何影响后续行动和成本。优先级可定性，不造精确信息增益或概率。

允许：直接改进、低成本排除一个重要方向、继续同一方向、暂缓、停止。不能强制“必须先 diagnose”或“每次必须换轴”。有成绩差但合法、已完成且可比较的控制仍可作父方案；不拿推荐列表替代已接受列表。

### 6.2 必须有一条完整案例

以下仅是合成设计例，实际方向不预设：

1. 已有受支持 Ridge 和合法因子，或从目标入口产生对应研究起点。
2. 基础画像显示高相关长期存在，最近相对退化是否集中尾部未知；提出 H1 极值解释、H2 训练历史解释，允许并存。
3. 第一次规划可冻结尾部查询＋合法消融，二者从同一已接受状态出发。查询只用现有起点，或起点与已接受对照，不能引用同批尚未完成的消融；仅有一个对象时只描述自身误差，不能伪造相对退化。
4. 若有足够范围的相反事实则削弱相应解释；若尾部太少则保持未决，不能把“没检出”当证伪。消融更差只反对本次删除建议，不自动证明相关性无害。下一次更新须保留这些区分，不把“高相关”写成充分原因。
5. 第二次规划可选择已有窗口方向或有理由停止；改窗口保留特征，实际 fit/predict/反馈贯通。即使改善，也不声称唯一原因已找到。
6. 末批事实形成 pending，冻结推荐由原政策决定，页面同时显示当前推荐、认识和未决；不追加第三次总结。
7. 用户显式续接，新 Campaign 首次获准规划处理旧 pending，再作新选择。问题身份、旧主张、反证和历史成本保留。
8. 对一个明确合格对象显式 refit，窗口/特征/参数完整，可信包新进程推理一致；浏览其他对象不换推荐交付。

如工程 fixture 预置了分数和响应，标 assistant_authored_fixture/simulation_only。不能将其写成真实大模型理解或市场改进。

## 7. 代码落点与适配方式

| 位置 | 本轮修改 | 不能做的事 |
|---|---|---|
| focused_diagnostics.py | 补缺失数值与有界类型分发；阈值/行/常量/n 的回执 | 不重写已有数值评价器，不自动因果判定 |
| focused_research.py | 版本调度、初始画像、新动作关系、诊断证据接线、状态补丁与计划冻结 | 不新建 Controller；不改原推荐数学政策 |
| focused_methods.py | 保留旧 validator；新协议认识/schema/投影适配 | 不放宽旧 first/One-shot/null 或旧 hash |
| focused_adaptive.py / focused_evidence.py | 原 EvidenceIndex 接纳合格诊断/父证据及权限和身份 | 不从自由摘要自证、不混入封存信息 |
| focused_runtime.py / 原 RuntimeDB | 原事件/计划绑定、幂等读取与产物恢复 | 不创建第二个队列/数据库/状态权威 |
| 可选小 research_state.py | 纯归约、有限版本关系、适用性和状态投影 | 若已有等价逻辑则复用；不持有新 Memory |
| research_mission.py | 续接绑定状态快照和末批证据，累计成本 | 不改变原同快照/源绑定规则、不清曝光 |
| focused_summary.py / apps/workspace_* | 同源中文主线/证据/实际动作投影 | 不生成新的 LLM 理由，不重排推荐 |
| focused_delivery.py / 原导出器 | 研究包携带状态和证据引用；模型数学不变 | 不强行重签旧包、不自动 refit 原 A/B |
| focused_benchmark.py | 复用已修最佳研究/冻结推荐比较，增加行为和成本数据 | 不重启选择政策或恢复旧 Bug 做参考 |
| experiment_memory.py | 复用来源/范围和现有隔离；本课题状态不靠全库召回 | 不做新的策略学习或永久方法黑名单 |

下一轮没有理由修改候选模型内部数学。若为了导出改 focused_delivery.py 等编译绑定文件，须披露旧包源码兼容影响；同 schema 可读取不等于所有历史实物包可在当前源码加载。保留原包与登记，使用匹配原源码/依赖只读验证；找不到则 BLOCKED，不重训替代。

## 8. E0—E5 实施批次和退出条件

| 批次 | 工作 | 退出条件 |
|---|---|---|
| E0 合同冻结 | 实际 Git/授权/现有能力差异；确定新里程碑及研究协议/schema/容量，不升级候选数学profile；冻结文档归属、预算和条款映射；先识别负例 | 可执行诊断表示、按假设版本处理证据、联合容量构造及总fit口径冻结，新旧表示无歧义 |
| E1 事实工具 | 初始画像和 DQ 真实分发、训练/评价范围、共同掩码、样本不足、缓存回执 | 手算/负例及原诊断回归通过；真实类型输出不同，不只换标签 |
| E2 认识协议 | 问题/假设/证据关联，单响应更新＋动作，新版本归约和原子接受 | 纯诊断反馈、反证、失效、stop/review、无效响应、中断幂等及容量测试通过 |
| E3 完整链路 | 原两个入口、worker、两批、显式续接、研究包/可信交付及最小 UI | 实际合成数据两入口链路，末批→子首轮，原推荐隔离与只读0增量通过 |
| E4 行为与比较 | 公平参考/新支持/简单策略；结构 fixture、语义试验材料、评分标准 | 工程对照完成、无答案泄漏；未授权语义/价值项明确未验，不冒充失败或通过 |
| E5 冻结验收 | 最后功能修改后冻结源码/测试/依赖/输入，适用回归/浏览器/静态，准确文档和交付 | 新增/受影响关键路径实际通过；仅定位失败不算修好，阻塞按范围NO-GO；无关历史失败单列，五轴分别结论 |

内部可分 commit/PR，但对用户只交付一个完整产品增量；E1 的函数或 E2 的字段不是下一轮产品完成。获准范围内无需每批再次等待批准。遇到新增权限/数据/付费或超范围能力，先完成其它可独立工程，再明确相应阻塞，不暗扩权限。

## 9. 测试矩阵和执行方法

### 9.1 必须有负例的条款

03 索引逐项记录 ER01—ER40。下列组是最少覆盖，不是要求一个条款一个重型 Campaign：

| 组 | 主要条款 | 必须验证 |
|---|---|---|
| DQ 数值 | ER01—ER08 | 现有诊断复用；具名相关/常量/n；尾部手算与 control 共享掩码；新增列；时间对齐、未来扰动、unknown；缓存身份；零fit/LLM |
| 状态/更新 | ER09—ER18 | 诊断进入更新；稳定版本；保留反证；一个实验多假设；无效提案/中断幂等；stop/review；失效类型；父 pending；First/One-shot 旧兼容；容量/权限 |
| 预算/研究 | ER19—ER23 | Adaptive/One-shot 上限；各动作槽/HTTP/fit；同批未来拒绝；差控制合法；父子累计及失败恢复 |
| 实际链路 | ER24—ER29 | 两入口真实 worker；完整继承；研究包引用；refit/新进程；取消/重复请求；旧包源边界、只读0增量 |
| 比较/行为 | ER30—ER34 | 最佳研究与推荐分开、无候选 null、partial、同模型/工具/预算/历史公平、事实对照、规则与Live分轴、简单策略 |
| 界面/发布 | ER35—ER40 | 同源最小 UI、导航/刷新/重开、字段发送边界、文档/历史、冻结身份、原失败及精确结果、最终交付 |

时间扰动限定：只修改不参与相应训练特征构造的未来/非训练数据，应不改变过去训练画像。selected_train 之前的合法历史可能参与滚动特征回看；修改这些依赖可以改变训练特征，不能一律判为泄漏。研究执行路径禁止读取真实封存标签；测试使用合成 canary 拒绝读取。

### 9.2 测试层次

1. 纯函数/结构：合成数组、伪结果和手算，可覆盖大多数状态/比较分支；不得每个报表边界都重训。
2. 集成/worker：少量隔离合成真实 fit/predict、队列、恢复和计划冻结；测试报告注明来源。
3. 交付：显式新 refit，核对真实行/列/参数及现有窗口，包成员 hash 和 fresh-process 无标签预测一致；训练外截止与成熟正确。
4. UI：受影响 AppTest/组件及实际 Chromium，保留当前四模式与旧工作区，并新增或参数化新协议模式，不能只跑旧V2.5代替新闭环覆盖。两个入口×规划方式×预算的多数组合用预检/纯逻辑测，少量代表路径跑完整 Campaign。
5. Provider/Replay：本地 loopback HTTP 及严格断网 Replay，重试/未知响应/恢复不多发请求；不是 Live 模型质量。
6. 真实语义/研究价值/独立预测/真人：只在各自授权后运行，按第 10 节记录。

### 9.3 精确命令的形成与冻结

在仓库根、现有 .venv 中执行。先确认依赖已声明，不为跑测试自动安装可选新平台。建议新测试按职责归到 `tests/test_evidence_research_diagnostics.py`、`..._state.py`、`..._protocol.py`、`..._continuation.py`、`..._integration.py`、`..._benchmark.py` 与受影响现有 UI/浏览器测试；已有同义测试则扩展，不重复造入口。

定向命令示意（新文件实现后才能执行，当前不是已跑命令）：

```powershell
$env:PYTHONPATH='src;tests;apps;scripts'
.venv/Scripts/python.exe -m pytest -q tests/test_evidence_research_diagnostics.py tests/test_evidence_research_state.py tests/test_evidence_research_protocol.py --basetemp=<本次新临时目录> --junitxml=<本次新证据目录>/targeted.xml --tb=short
.venv/Scripts/python.exe -m pytest --collect-only -q tests
```

尖括号必须替换成唯一新路径。实施者交付中提供实际完整 argv，不照抄占位符。全回归实际选择集合必须从最终源码 collect，依据授权列出 deselect；原真实/native harness 若仍未获准，保留精确 ID 和原因，不用模拟输入替换。新增工程用例不能因为无 Live 凭证而一起跳过。

现有回归复用当前适用 V2.5/repair/Provider/Replay/Runtime/Queue/Memory/summary/delivery/continuation/UI 测试及 tests/browser/test_agent_workspace.py、旧浏览器入口。先 rg --files 确认实际名称，不对 Windows shell 假定通配符能展开。最终将相关定向测试包含进适用全仓，而不相加重复计数。

JS 修改运行 node --check；受管 Python 修改运行相应 Ruff/compileall；git diff --check。完整目录 lint 若有既有债，保留实际 exit 与命中路径，不写全部绿。原坏 fixture/断言、120秒续接和浏览器门槛不能为绿改掉。

E5 最后功能修改后冻结源码和测试逐文件 SHA、已安装核心依赖、pyproject/锁/声明输入、合成生成器/原始 JSON/来源、test node 清单、环境及原 A/B 保护清单。每次长运行记录开始/结束/当前身份、真实 exit、stdout、JUnit；三时点核对不是连续监控。后续只写文档时只补适用检查；再改功能则重做受影响冻结验收，不能拿父源码收据充新源通过。

已知负载敏感的交付/浏览器可沿现有合理串行编排，记录实际资源，不通过放宽断言求绿。单独复跑只有诊断意义，不能覆盖完整运行中的失败；失败若确因实现修复，保留原反例和修复后同源完整结果。

### 9.4 当前已经存在的回归入口示例

以下路径在e361b0e实际存在。均为未来实施时的命令示例，不是本包执行结果；先替换新目录占位符，并按最终变更范围和实际collect调整。涉及长时实际worker的文件可串行，不需为了数字每批全跑。

```powershell
$env:PYTHONPATH='src;tests;apps;scripts'
.venv/Scripts/python.exe -m pytest -q tests/test_focused_v25_methods.py tests/test_focused_v25_compile.py tests/test_focused_v25_execution.py tests/test_focused_v25_acceptance.py tests/test_focused_v25_comparison.py tests/test_focused_v25_benchmark.py tests/test_focused_v25_recovery.py tests/test_focused_v25_delivery.py --basetemp=<新目录>/v25-temp --junitxml=<新目录>/v25.xml --tb=short
.venv/Scripts/python.exe -m pytest -q tests/test_provider_pipe_ownership.py tests/test_focused_b1_provider.py tests/test_focused_provider_json_boundary.py tests/test_provider_thinking_contract.py tests/test_v25_default_repairs.py tests/test_v25_axis_policy.py tests/test_v25_owner_feedback.py tests/test_workspace_continuation_callback.py --basetemp=<新目录>/affected-temp --junitxml=<新目录>/affected.xml --tb=short
```

浏览器使用干净测试子进程，不能继承 `FFA_ADMISSION_REAL_RAW`、`FFA_ADMISSION_SOURCE`、`FFA_ADMISSION_SHA256` 的真实输入开关。仅设置本进程环境，不修改系统/用户全局环境或权限；使用合成测试项目和新证据目录。

```powershell
$env:FFA_BROWSER_E2E='1'
$env:FFA_UI_BROWSER_ARTIFACTS='<新目录>/agent-browser'
$env:FFA_BROWSER_ARTIFACTS='<新目录>/legacy-browser'
.venv/Scripts/python.exe -m pytest -q tests/browser/test_agent_workspace.py tests/browser/test_research_workspace.py --basetemp=<新目录>/browser-temp --junitxml=<新目录>/browser.xml --tb=short
```

须新增/参数化本轮新协议浏览器案例，原四模式加旧工作区通过不能替代它。无本地Chromium/对应平台时标BLOCKED_ENV，不擅自安装可选组件、发起远端CI或调整安全政策。

当前已知两项未授权真实/native harness：`tests/test_models_and_harness.py::test_harness_runs_real_data` 和 `tests/test_methodcard_p0_pipeline.py::test_methodcard_derived_paperspec_runs_p0_harness`。最终全仓先collect并审核全部潜在外部/真实输入案例，再显式deselect未授权项、保存精确集合；不能只机械排除这两项就假设以后所有新增case都已授权。

## 10. 行为、价值、Live 与真人验收

### 10.1 五条证据轴

| 轴 | 需要的证据 | 未具备时怎样交付 |
|---|---|---|
| A 工程 | 真实类型计算、实际执行、身份、时间、预算、恢复/包与UI验证 | 关键新增路径失败则相应功能 NO-GO；无关历史资产阻塞单列 |
| B 真实研究行为 | 获准实际模型在反例、诊断结果和续接中作有范围更新与有依据选择 | 无授权/未跑为 NOT_RUN；fixture 仅工程 |
| C 选择价值 | 同域、同初始权限/资源/底模的流程对照，推荐/候选/完成率/成本及错误 | 小样本只试点，不宣布普遍优势 |
| D 独立预测 | 未参与研究器设计/选择的数据或合法前瞻，单独协议 | NOT_RUN，保留原47负确认，不重命名历史 |
| E 用户价值 | 所有者/独立用户实际完成、理解、帮助量、人时及成果复用 | 不代签、不用模拟用户关闭G6 |

LIMITED_ENGINEERING_GO 不等于 B/C/D/E 通过。两历史失败与 skips 保持真实 exit1；新增/受影响关键路径必须实测通过，已解释但未修复的关键失败、未执行关键路径不能写PASS。必要平台缺失标相应BLOCKED，未受影响且已验证部分可单列交付，不能宣称完整闭环工程已成。无关历史资产阻塞与未获准Live不阻止独立工程，也不要求为数字全绿修无关旧失败。

### 10.2 不再用模板复制证明理解

使用六类人工审阅情景：前提不成立；前提成立但不足；证据冲突/两假设并存；需跨批/续接；无明确新增信号但允许探索/停止；缺工具/预算。

其中包含最小事实对照：只改尾部集中事实、时间变化是否存在、证据是否已取得等。预先写允许的合理动作/理由和不可接受归因，不把标准答案/机制标签发给模型。相同动作可合理，但必须真实响应关键证据；不同动作、解释更长、换轴或实验更多都不自动成功。

记录：事实引用正确性、过强归因、反证保留、下一步与证据的关联、重复无信息实验、越权/隐藏调用、完成/成本、推荐。说明每个分母和错误严重性；不新增默认收费裁判 Agent。旧合理参考不因没有新语义字段被拒绝。

### 10.3 两类公平比较

- 语义挑战：同一冻结原始事实、同工具域/权限/实际底模与Provider配置。参考与新支持的表示/Prompt可以不同，这是支持包处理；同时改变就只归因整包。
- 完整流程：同初始数据/起点/工具能力/预算上限，各臂只看到自己的合法祖先及本臂当时已接受结果；不要求后续字面同历史，也不借用别臂结果/认识。固定原始输入可共用，跨臂结果缓存默认隔离；诊断/LLM/预留fit/实际计算账本均给出，不能只对齐四槽却让一臂额外免费取证。保留合理同域简单策略。

支持包比较使用相同诊断可见性合同；不能将不可见新增信息的旧 OFF 臂称为同信息参考。OFF/ON 信息增量可另列实验，沿原权限不旁路，不把其收益再次归给新认识状态。

保留当前 Benchmark 的 best_research_mae_delta 与 recommended_mae_delta，沿原明确左右差值与单位；不得改旧 mae_delta 含义。无研究候选仍 null；双方正常保留同一起点时推荐差可为0；partial/failed回退不进入成功配对。少量情景/重复seed不是独立金融样本。

### 10.4 可选16次逻辑规划小试验：仅供另批

费用与发送范围另获准后，可选择六对语义情景12次＋一条父两批/子两批实际轨迹4次，共≤16次逻辑规划。HTTP重试另设真实上限；固定实际底模、thinking、token、timeout、Prompt/投影身份和允许载荷；金额未知仍 null。

这是替换原“两条各两轮但未明确续接”的预算安排，不额外免费添加续接。若要求两条完整父子 Live 轨迹，重新列调用/fit总量并审批，不能塞进旧16次算术。

真实输入使用权限、外发字段和派生摘要逐项明确。当前已有固定诊断 weights=[0.5,0.5] 的发送边界待所有者复核；它不是拟合权重，也不能未经说明假称完全无权重字段。新诊断/研究状态同样不能默认继承旧载荷白名单。用本地模拟HTTP冻结待批准载荷，确认在最后一步，不为准备审核先调用真实服务。

### 10.5 真人复核

保持原G6真实状态。旧A/B只读检查，不重训复验理解、不清库、不把技术预演换名为真人试用。所有者核对：当前推荐是谁、相对谁、上轮事实怎样影响本轮、还有何未决、包与额外fit区别。再按原准入条件邀请独立用户。

新协议真人任务必须有本次数据/计算授权；不强迫体验不同旧代码的A/B直接做入口因果对照。记录主动操作时间、帮助/代操作、错误理解、成果实际使用；没有测量的劳动节省不填估算PASS。

## 11. 正式文档的具体修改方式

本包不直接修改这些文件。用户明确批准本轮后，E0 将新 milestone 的唯一合同及路线变更落仓；不由外部提案自签接受状态。

| 文件 | E0/实施时怎样改 | 验证后怎样改 |
|---|---|---|
| AGENTS.md | 顶部写本轮用户批准范围、唯一新合同/新协议、读序、禁区；V25继续约束旧协议及本轮复用的数学能力，不把整份旧合同作废；不复制长测试矩阵 | 只摘要实际交付/开放项并指向CURRENT；不将旧预算/权限泛化 |
| PROJECT_ROADMAP.md | 增加“闭环→裁剪/权重→RF/四组合”近期方向及三条并行路径；标清本轮与条件包；正式编号在此统一 | 状态只链接CURRENT，不重复维护一套成功表；纠正仍停留旧A未操作/Live未尝试等过期叙述 |
| CURRENT_IMPLEMENTATION.md | E0仅标本轮implementation_started及未实现，不提前写功能已成 | 顶部唯一当前摘要：实际功能、源身份、测试平台/exit、B/C/D/E状态和下一步；历史原文链接/归档保留 |
| 新里程碑唯一MD | 建议 docs/EVIDENCE_RESEARCH_LOOP.md；若已有等价文件先合并，记录本方案、唯一schema、E0—E5、失败与精确命令 | 所有本轮增量更新同一MD，不创建final-fix等竞争合同 |
| V2_5_METHOD_RESEARCH.md | 原N0—N5/§11—14历史证据不改；最多加新合同导航 | 不用新结果回填旧收据/首次Live身份/47负确认 |
| ADR | 若现行ADR不覆盖跨Campaign认识和诊断新语义，创建一个最小新决策，编号查实际未占用；可信用户指令是批准依据 | 不把accepted写成实现/金融验收；ADR007原状态/范围保留 |
| FOCUSED_ARCHITECTURE.md | 补原Controller内诊断→证据→认识→计划/续接的责任和数据流，明确纯归约状态视图 | 对照实际模块，不新画服务/队列/存储 |
| FOCUSED_ACCEPTANCE_TEST_PLAN.md | 链接ER01—ER40与五证据轴，新增案例/旧门禁映射 | 记录真实覆盖和边界，保留A/L历史，不改旧条款结果 |
| CODEX_FOCUSED_HANDOFF.md | 顶部新当前批次、读序、边界；旧“下一步”明确历史 | 精确已完成/未完成和可复现命令，不让旧5秒失败冒充尚未修好或新工程冒充真人 |
| CODEX_V22R_REMAINING_VALIDATION.md | 仍是原A/L及外部/真人剩余入口；追加本轮关联，不清零 | 同步最新真实状态；不复跑旧收费矩阵、不用新条款覆盖旧48条 |
| AGENT_WORKSPACE_UI.md | 仅写新增协议选择、研究主线、证据/未决状态和操作边界 | 与实际按钮/回执一致，不重写整个工作区 |
| FRONTEND_USER_GUIDE.md | 双入口任务书、新状态如何读、诊断/训练/复用区别、续接新预算、模型包源兼容边界 | 区分旧A/B本人操作与新协议试用；保留G6真实失败/待复核 |
| README.md | 当前定位和新协议入口/边界，链接唯一合同、CURRENT、路线 | 根据实测更新，不把工程摘要或旧Live当优势宣传 |
| docs/validation/新索引 | 新建本轮分发级planned→实际索引，引用原始本地证据hash | 保存精确exit、source/test/input/deps、唯一node覆盖、外部未测；不含原始私有数据/模型/凭据 |

正式版本号尚未批准，本包不直接占用原 V2.5.1/V2.5.2。若决定重映射编号，在 ROADMAP 唯一映射并保留来源别名。AGENTS/README/HANDOFF只放入口与短边界，不各自复制完整施工规范。

同步先修事实状态滞后，再增新功能叙述。无关历史lint、旧论文资产和长期科学账本保持原状态，不为整齐把历史MD或测试删除。历史段归档须保留原字节/可追溯路径与原链接，不能只删旧失败。

## 12. 后两轮的具体设计保留

### 12.1 第二轮：训练内裁剪与时间权重

裁剪：仅显式生成特征列，none 或 q01/q99，固定线性分位数；在最终窗口 selected_train 内拟合界限，裁剪后再拟合Scaler及模型；不裁y、不删共同评价行。常量/相等分位数/非有限行为预先固定。

权重：uniform 或 half_life=126/252交易日；按最后合格训练行的交易日位置算 age，raw_weight=2^(-age/half_life)，归一化均值1。缺行不直接等同少一个自然日；明确交易日序号依据。固定selected，首版Scaler不加权，仅Ridge实际接收sample_weight；评价MAE仍均匀。

先扩展既有方法定义/候选/实际fit回执和新包语义，记录裁剪前后矩阵、阈值训练行、Scaler实际输入、权重行映射、有效样本量和实际参数消费。不能直接放宽原 fit_method 的精确旧步骤断言后称已支持；新协议分支实际验证，旧路径原样。

两包均贯穿fit/predict/refit/trust/续接，失败成本保留。uniform/none须复现原结果；未来扰动不改变训练内参数；新进程模型包一致。两包独立提交，资源不足可先交完整裁剪、权重保留同阶段后续，不能标成均完成。

决策必须选择为何取证、裁剪、降权或保留，不强迫试满。裁剪/权重改变分布和正则环境，结论限定整体方法效果，不把某项改善叫唯一市场原因。

### 12.2 第三轮：一个RF研究适配器与四组合

优先复用已有RandomForest实现，但新研究替换保持完整特征、裁剪、Scaler、窗口、权重等声明步骤。当前Ridge构造含Scaler、RF构造不含，必须在新profile把模型与处理顺序明确分开；不能因更换family隐式删处理。

冻结一个RF有限配置、seed、n_jobs和资源边界；不同时开放所有模型/HPO。sample_weight是否真实消费及其含义另核；不支持组合明确拒绝，不自动丢字段。新包完整refit和fresh-process验证；原固定RF对照身份不改。

2×2：事前固定A原/原、B新/原、C原/新、D新/新及其余完整方法。A合法已接受时第一批B/C，第二批从B或C单轴到同一D；成绩差父候选仍可作control。四格身份/目标不一致或缺D时交互不可判定；选择不继续可以合理，但不伪造四格。

冻结损失及差分方向，例如 (L_D-L_C)-(L_B-L_A)。额外成员/模型每折拟合均计预算，不在一个tool_call里藏四模型。事后挑因素/水平只能叫开发探索，不能反称预登记交互或因果。

## 13. 完整路线：三条路径协调推进

以下是拟批准方向图，不是一起执行的清单。当前SPY、Ridge限制不是永久产品定位。

| 阶段 | 决策＋工具共同交付 | 进入/完成证据 | 前移/依赖 |
|---|---|---|---|
| 1 证据驱动闭环 | 本包第1—11节，取证与实际特征/窗口干预贯通 | 完整两批与续接、反证/更新、真实工具/交付；B/C/E另验 | 本次拟实施范围 |
| 2 诊断可干预 | 第12.1节裁剪/权重 | 两包准确执行及选择理由，不预设赢家 | 完整闭环可用后，分包交付 |
| 3 跨方法规划 | 第12.2节RF与条件组合 | 实际模型及完整处理继承、四格或有理由不做 | 不等所有原因查明；不一次开多模型 |
| 4 知识与可执行方法 | K1少量授权方法/反例检索；K2同域增量；配方起点；一个模型有限参数/训练组件 | 知识实际改变实验/不适用判断，配方真实可跑；内部trial记账 | 已有知识一直可用；K1薄接和配方可按问题提前，不等第三轮全结束 |
| 5 客户Pipeline/任务 | 忠实复现一类客户起点＋一项修改；按需一个相邻资产、概率、排序、波动/分位数或问题研究合同 | 真输入/模型/输出/单位/时间/指标/包；用户实际复用 | 一个真实客户薄切片可前移，不强迫改成SPY；不接预测就冒称可重训原模型 |
| 6 深层方法构造 | 两成员组合、声明式结构/损失/组件，确有表达缺口时隔离代码开发→验证→注册 | 新方法真实实现与完整交付，开发试错/资源也计账 | 组合不等Coding；不先造万能代码平台；权限不随代码扩大 |
| 7 前瞻/持续研究 | 薄前瞻→候选影子→事件提名研究→政策内采用/暂停/回滚 | 实际日期先预测后成熟评分；覆盖/迟到/修订保留；版本与采用可复核 | V3-P合法固定基线即可独立批准并行，不等开发赢家/所有确认工具 |
| 8 经验/必要生态 | 条件经验检索cold/warm；足够多样证据后研究策略学习；窄SDK/API/MCP、按需团队/部署 | 新任务或未来时期上的选择/成本/真实复用证据 | 窄客户接口可前移；策略学习/广泛多租户/平台化暂缓 |

三条路径：核心研发（阶段1→2→3→按问题选择4/5/6）；真实使用（所有者复核→独立小任务→客户切片→重复/付费使用）；新证据（固定基线薄前瞻→候选Shadow→触发研究→政策内采用）。它们各守必要依赖，不建立八阶段机械串行。

维护循环可以完全不调用LLM：数据检查→预测→成熟评分→按固定政策重训。方法研究循环与跨任务研究策略学习另行版本化。例行refit不要求每次短样本显著击败旧快照，也不能重训后回填旧预测。

完整方法独立确认另补执行支持：必须真实覆盖特征、裁剪、窗口、权重、模型和组合；ModelBundle可推理不等于确认可运行。原47负确认、暴露历史和一次性消费保留，不能换文件/任务名洗成盲样本。

### 13.1 与旧路线的唯一映射

| 旧方向 | 本路线位置 |
|---|---|
| V2.5.0两轴/更新 | 已有底座，不重开N0—N5 |
| V2.5.1权重、V2.5-P | 阶段2；其它权重/预处理另按需 |
| V2.5-F | 当前公式＋阶段1诊断接线；学习式选择/新输入在阶段4/5，未自动解锁 |
| V2.5-M | 阶段3一个RF研究适配器 |
| V2.5.2参数/训练工具 | 四组合在阶段3；一个模型小参数域/损失在阶段4，不把联合设计等同HPO |
| K1/K2、文献起点/迁移 | 阶段4；薄接可提前；strict复现为独立高级模式 |
| V2.6组合 | 阶段6独立小包，可在有明确互补问题时提前 |
| 客户Pipeline/相邻任务 | 阶段5，可由真实切片前移 |
| 内部组件/代码 | 阶段6的声明式→隔离开发→审核注册，不是研究运行时任意Python |
| V3-P/V3.0 | 并行薄前瞻与阶段7影子 |
| 拟议V3.1/V3.2 | 事件提名与政策内采用，不自动交易 |
| F2稳健性/迁移 | 多seed/时期、配对统计与不确定性、QQQ等近域验证在相关阶段/独立评价中；旧LSTM等模型缺口保留状态，按需求进入适配，不强设近期前置 |
| 原strict科学广度账本 | 20篇/4类/3数据域等旧目标和未完成claim/held-out状态保留独立高级路线，不要求近期产品先全完成 |
| V4经验/策略、V4.1/V5接口/团队 | 阶段5/8；窄接口可前移，策略学习需多样新证据 |

每个后续包立项仅回答六件事：为何现在做、判断怎样改变、真实执行什么、成本与权限、五证据轴如何验、失败如何退回。没有实际任务不建通用平台；不能用模块/测试/论文/Agent数量证明产品竞争力。

## 14. 最终验收与交付清单

实施 AI 最终必须交付：

1. 实际基线/最终HEAD/工作区、变更列表，E0—E5与ER条款逐项对应；代码/测试/文档位置。
2. 至少一条可复现的父两批→显式续接轨迹，包含真实控制、问题/假设版本、诊断/训练、支持与反证、更新、待处理证据、预算及冻结推荐；两个入口均有真实工程链路。
3. 原特征→窗口、窗口→特征/消融的实际执行覆盖仍有效；不强制每个Campaign两轴全用。
4. 研究包及一个获准显式模型包的完整回执，新进程预测一致；下载/取消/只读0增量，旧包边界真实。
5. 精确测试argv、环境、输入/源码/测试/依赖身份、真实exit、逐node覆盖、原始失败、复跑关系、静态及浏览器证据；原历史失败不覆盖。
6. CURRENT/路线/AGENTS/合同/ADR/架构/验收/handoff/指南/README按第11节同步，未来能力不标完成或已批执行。
7. A工程、B真实行为、C研究选择、D独立预测、E真人价值分别结论，具体未完成原因与下一步；G6本人/独立用户不代签。
8. 本地提交清单、实际启动和操作方式、未测平台/native/Live/权限边界。未获本次推送授权则不推送；若获准，另记remote SHA与CI是否核查。

不以“方案经过对抗审查”承诺软件无缺陷、金融有效或市场成功。真正新增问题须定位并修；没有实质问题的既有能力验证复用，不另造并行路线。
