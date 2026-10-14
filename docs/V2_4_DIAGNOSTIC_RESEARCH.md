# V2.4 确定性诊断研究：唯一实施合同与批次日志

当前最新批准与实施为末节“2026-10-14 试用前P1—P5/G0—G6增量”。限定工程及结束输入快照修复已完成；新冻结全仓879通过/2历史失败/6跳过，整体PARTIAL，输入开始/结束/当前绑定BOUND。G6本人预演未完成，目标用户准入仍NO-GO。下方旧批准/收据保留历史身份，最新收口见末节勘误与最终验证。

日期2026-10-09；用户已批准D24-0—D24-5工程及D24-6准备。基线95760e264eddb4388a44df6d35442b6ce8d90928，tree 8d081ef18dd7fde0b3e45f3a593e929e3adb530d。实际结果以本文件日志及收据为准，不把计划写成通过。

来源（只作provenance，不是并行合同）：实施提示词SHA256 b1194dac113195ef66715eaf2792dfea58149c5efc672f16d0bf1933f0f38d1a；基稿4c4877486bcdceaed043892a417ec5beeb82bda6798a02457e7e6a87e98a58a3；最新复审1d993d98c2bbf0b9462d087abf7b82fe99ebcbd71ffa662048dd1c19f17fe98a。R1—R4/P1—P4已合并如下。旧PROPOSED不覆盖本次明确实施批准。

## 1 合同及授权

### 2026-10-13 S0—S4统一收口批准与S0记录

本轮实际基线df98b92ed30b052ea6e71965401eeb8571307608；tracked clean，既有未跟踪证据保留。独立统一方案与ZIP内统一MD逐字节相同，SHA256 284d8efbdb4957bbe462f9d6d8f2dbc87e8200d91e0489f7325d4d6f7e7fda14。用户批准默认S0—S4，当前日志承接唯一规范；讨论/42项文本核验不作为软件验收。未批准RMSE/知识投影/未来执行能力、Provider/确认/生产迁移/推送。正式路线不变，§8条件性新增路线仍需单独批准。

S0红例`.v24s/s0-red3.xml`：10 failed/4 passed、exit1（6.74s），复现全失败分类及重复/错身份预测包。此前s0-red为沙箱默认临时目录14 setup errors，s0-red2含4测试构造路径错误；均保留。最小修复先验证绑定/覆盖/exit，再分类实际失败，未知失败不降级；ZIP和索引路径唯一，逐accepted candidate/config/合同/声明引用核对覆盖，缓存只引用原预测。s0-green：27 passed/16 deselected、exit0/11.39s；后续真实包及最终回归仍待执行，不提前写完整验收。

2026-10-13 S1增量：复用原不可变observation对象冻结prediction provenance / analysis novelty / evidence tier及形成序列引用。比较测量对称身份、方向规则身份分开，反向相对改善重算分母；标题/候选别名不制造新预测。首次模板的缓存统计可为派生分析；反向全目标贡献比较为已知对，仍保留真实成本与规则结论。缓存已可见结果后的新问题标posthoc_exploratory，不追称事前。重建comparison_index只从原记录投影，不重新分类自身；ON已知摘要与OFF空摘要分开，旧记录不迁移。`.v24s/s1-red.xml`8失败；s1-green 36通过/352.09s，s1-projection 12通过/23 deselected/155.58s，均simulation_only且exit0；相关Ruff/compile exit0。S0静态首次C408已在d07285f修正并重验；其行为没有变化。

#### S0—S4施工合同（统一方案§4/§9/§10，非历史验收重写）

- S0：真实失败先于passed=0分类；未知失败不降级。包审计按唯一索引/ZIP路径、已接受执行、实际配置、合同、预测引用及逐行指标核对，不以预测个数代替覆盖。缓存共用原预测。
- S1：原RuntimeDB观察对象记录三轴信息及首次事件。对称预测对与有方向的观察身份分开；原精度、执行seed/config、数据/标签/切分/范围必须一致。反向比值重新算分母，标题/别名不能造新发现。全量审计与臂内规划可见性分开；重建只还原既有首次记录，不重分类自身。
- S2：显式`diagnostic_research_v3`/`diagnostic_price_advice_v3`、`research_decision_v1`。四项为`visible_basis`、`experiment_question`、`priority_reason`、`feedback_update`；每段文本最多2000字符、引用最多8个，反馈分支为supports/weakens/not_distinguished/next_step。沿research_design事前冻结，实际数值更新另存，不事后补理由；确定性收尾不追加第三HTTP。R/D兼容旧design并明确不是结构化判断证据，未知字段仍拒绝。J优先有预算的未回答条件比较；A局部失败不宣布A永远无用。D只用本臂可见已知信息，R不获得新增去重支持；相同编译器/物理缓存/冷Memory/资源与推荐政策。ON/OFF技术权限相同，OFF无新诊断/观察/比较摘要，不能用后台信息暗中筛动作。两规划四槽、One-shot整体冻结、原Random draw/失败账本不变。
- 新规划的`observation_planning_v1`保留全部原数值、规则、control及状态；详细information/actual_feedback_update留不可变审计，有限身份摘要另投影。这是显式的有界审计/规划分离，不静默截断，64000上限不变；原v1/v2 fixture字节/hash不迁移。旧活动Campaign继续原源码合同或显式新Campaign，不能强改hash。
- 推荐仍主MAE/0.0025。无研究才null；全部变差或未过门槛保留真实best_research。completed可合法retain_start；partial/failed/cancelled保守留合格起点且保留失败。最佳可用模型与推荐不同；贡献观察通过不能推荐更差child。推荐相对起点增益与研究候选成绩分列，不能用失败回退洗出成功。
- S3：在原研究/实验/成果页显示实际问题/理由、parent/control/公式diff、观察及三轴、推荐角色/成本/来源，不新增工作区。后台、ResearchPackage同源；ModelBundle保持显式refit、可信登记及原无标签推理。只读操作不新增fit/HTTP。
- S4：最后功能修改后冻结src/apps/scripts/tests、依赖及输入，绑定实际exit/JUnit/覆盖；原四臂门槛保留，R/D/J另做有限规则挑战而不冒充真实LLM策略实验。真人清单由实际操作者填写。没有真实干预阻塞记录时，下一工具选择暂缓；本轮不开发未来能力、可选包或接入45卡。

S2进行中证据：`.v24s/s2-red.xml`5失败复现旧机械选择及缺四项合同；`s2-roles-red.xml`2失败/2通过/5 deselected复现partial/failed推荐问题。`s2-integration1.xml`50通过/5失败/1137.707秒：两个旧fit计数（新J真实24而非旧缓存20）、新字段使compact超限、模拟HTTP沙箱连接未到达、审计读取错误campaign层级；均保留。修复后`s2-unit2.xml`33通过/9.36秒/exit0，`s2-integration2.xml`6通过/325.16秒/exit0，含正常权限本地HTTP1→严格Replay HTTP0及各20fits一致。新J普通流程24fits、三实际研究候选，物理缓存行为由独立显式缓存用例继续验证，未通过改计数取消缓存断言。累计受影响回归仍在执行，不能提前声明S2/S3/S4通过。

S2累计门槛完成：`.v24s/s2-regression.xml`99 passed/6 deselected/983.39秒/exit0；6个排除节点已在integration2逐项通过，不是跳过缺口。包括真实子进程crash/resume、原预算、ON/OFF、缓存、坏设计、包与原推理绑定。Ruff及compile exit0。`run_v24_engineering_validation.py --output-root .v24s/s2-support-pilot --run-engineering --decision-support-challenge` exit0，R/D/J均PASS，20/20/24 fits、各2逻辑决策/3槽/HTTP0、8/8/9预测包复算；wall 52.763/53.749/60.975秒。三臂都retain_start，最佳研究MAE同为0.007331007277095696，J多做一次条件实验但未改善；不是LLM质量或策略优势证明。输入raw 0798460be4a950b39cb848833148b324cb35b642b834cb110b8e161e135ea8bd，独立冷Campaign且不跨臂继承研究结果，费用null。以上是S2阶段证据，S3/S4仍待执行。

#### 统一方案T01—T36实施映射

下列是具名行为映射，不是把42项文档核验改叫项目测试。最终通过/失败以源码冻结后JUnit及独立browser报告为准；`tests/`前缀省略。引用旧测试表示本轮回归复用其断言，不代表历史收据冒充本轮执行。

| 条款 | 真实实现/测试入口 |
|---|---|
| T01 | `test_focused_v24_closure_audit::test_bound_all_failed_is_execution_not_not_run`：产品全失败仍FAIL |
| T02 | 同上ENV/ASSET/UNKNOWN/混合参数：仅明确环境资产可PARTIAL |
| T03 | `test_focused_v24_review_fixes::test_manifest_binding_cannot_invent_a_pass`、`test_collector_no_manifest_or_allskip_or_count_mismatch_cannot_pass` |
| T04 | `test_focused_v24_closure_audit::test_package_normal_and_cached_reference`及重复ZIP/index负例 |
| T05 | `test_package_exact_identity_not_counts[missing_with_duplicate]` |
| T06 | 同函数unknown/wrong_config/wrong_ref/changed_params/wrong_campaign：重算真实配置，不信自报fingerprint |
| T07 | 正常cache_alias包及`test_cached_observation_in_next_on_prompt`：原引用、16fits不加训 |
| T08 | `test_focused_v24_information::test_reverse_reuses_base_but_recomputes_denominator_and_template`及真实cached观察 |
| T09 | `test_two_feature_ablation_is_actual_new_execution_not_blanket_duplicate`：实际两→一特征新训练，其余config不变 |
| T10 | `test_title_ids_do_not_manufacture_new_analysis_but_group_does`：首次合法组统计是缓存派生，非新预测 |
| T11 | 同函数及反向比值测试；原`test_group_rule_all_folds_small_samples_and_precision` |
| T12 | `test_changed_contract_cannot_reuse_pair`、原完整target/fold对齐及固定规则校验 |
| T13 | `test_package_exact_identity_not_counts[conflicting_candidate]`、原`test_focused_feature_contract`配置/列顺序/身份门禁 |
| T14 | `test_first_event_projection_rebuild_does_not_reclassify_itself`、真实`test_real_v24_worker_crash_reuses_context_rule_A_and_charges_B`核对首次observation原对象；browser提供起点续接 |
| T15 | `test_focused_v24_judgment::test_new_judgment_does_not_delete_failed_feature_back_to_start`及R/D/J实际Controller挑战 |
| T16 | 原feature_execution控制可见性门禁、`test_bounded_demand_design_persisted_without_fit`（04/05需求，不执行窗口组合） |
| T17 | `test_relative_group_losses_follow_location_not_global_mae`、`test_v2_policy_same_group_and_mae_but_different_weakness`及OFF领域假设 |
| T18 | 原`test_focused_provider_json_boundary`、`test_focused_b5_crash_recording`和`test_focused_feature_recovery`未知投递/重复/非法/计账 |
| T19 | `test_explicit_diagnose_uses_original_decision_and_slot`、初始/更新诊断实际HTTPfit=0 |
| T20 | `test_same_legal_ast_on_visible_basis_off_domain_basis`、隐藏Memory拒绝、cached ON/OFF空投影 |
| T21 | 原`test_focused_feature_campaign`One-shot四槽、`test_focused_price_sampler`draw/恢复、pilot失败分母 |
| T22 | `test_different_questions_have_different_directions_and_no_recommendation_override`、高波动局部/整体护栏 |
| T23 | `test_selection_no_candidate_all_worse_ties_partial_and_determinism`、`test_worse_and_nonselected_candidates_not_cleared_or_baseline_substituted` |
| T24 | `test_v24_research_package_has_context_rules_recommendation_and_recomputable_predictions`、DB/制品篡改、browser同源显示 |
| T25 | `tests/browser/test_agent_workspace.py`三模式：切换/刷新/new-context/公式/包只读0增量，显式refit另计；原fresh-process bundle推理 |
| T26 | 原feature_contract golden、Provider/Replay原字节；四项未知/缺字段显式版本门禁，R/D兼容无J字段 |
| T27 | `test_compact_two_decisions_provided_start_and_resume`64000上限；原diagnostics缺训练/连续来源unavailable |
| T28 | `test_incomplete_flow_cannot_turn_better_so_far_into_successful_recommendation`，late取消freeze同样保守 |
| T29 | `test_worse_and_nonselected_candidates_not_cleared_or_baseline_substituted`保留真实候选，正常retain_start增益0；极小分母比值null |
| T30 | 同上劣于起点与原selection all-worse；UI同时保留成绩/选择原因 |
| T31 | 反向分母/模板身份/规则篡改；cached形成状态posthoc且`predeclared_observation_supported=false` |
| T32 | 首次/已知/反向分类及cached ON/OFF，完整审计不反馈OFF |
| T33 | `test_four_parts_pretraining_bound_and_visible_reference_gate`，DB plan/context篡改拒绝，两轮实际执行和确定性收尾 |
| T34 | B+A真实已完成control、组弱点位置改变提案、具名常数各fold门禁；只支持有限工程行为，不宣称排除所有原因 |
| T35 | `test_support_challenge_same_floor_cold_arms_and_failure_denominator`、R/D无J字段兼容；独立三臂实际运行及原四臂门槛 |
| T36 | 本轮人工范围审计+原unsupported capability/confirmation前置拒绝；FRONTEND_USER_GUIDE要求真实阻塞后另批。未运行知识试点/未来训练/金融标签，不能写PASS |

S3中间记录：只读渲染红例1失败/1通过；最小UI后2通过。工作区/feature UI/公式/AppTest/B2累计39通过/373.30秒/exit0。初次实际浏览器3通过/1失败/490.87秒/exit1：旧入口冷启动仍在Streamlit Running，5秒默认断言先超时；改为等待真实`.brand-name`就绪、上限30秒，不固定sleep、不跳过。V24父24/续接24 fits、18 attempts、refit1另计，19项检查、Chromium153.0.8010.12、page_errors=[]；这次矩阵不是全绿，正在完整复跑。增益极小分母红例2失败，新增固定1e-12报告边界（不改变MAE主筛选），零/极小分母null；缓存数值模板命中与事前成功计数分开。相关30项/127.42秒/exit0，均隔离模拟。

S3门槛完成：完整browser重跑`.v24s/s3-browser-recheck.xml`4 passed/518.36秒/exit0，旧入口/价格模式/V24/旧Mission均实际Chromium，不是AppTest替代。`.v24s/s3-behavior.xml`2 passed/99.89秒/exit0，实际两特征消融新训练20fits/HTTP0，以及真实进程kill后原首次观察对象、A制品、计划/上下文保持并计入B重试。UI/相关core的Ruff、compileall、node --check、diff --check均exit0。保留首次browser失败与ratio红例。至此功能/测试冻结，接下来S4全仓；未提前宣布最终收口。

S4收尾复现并最小修复说明性缺陷：`.v24s/s4-oneshot-red.xml`1失败/5.81秒/exit1，One-shot的事前next_step误称还有第二规划，执行器实际仍只调用一次。现在分别按One-shot/Adaptive第一决策/最后决策生成冻结说明，最后仅确定性收尾，未知原因不代评议。`s4-oneshot-green.xml`16通过/100.89秒/exit0，包括实际两轮Campaign及本地HTTP严格Replay；Ruff/compile通过。不触碰已录制fixture。7e16f5c上的第一轮全仓被主动停止，其start manifest/full.log/独立四臂结果全部保留在`.v24s/final`；未完成JUnit，pytest实际exit未取得（null），外层收据命令因无完整报告exit1，不能当作产品失败数或通过。改后重新冻结并使用新目录跑完整回归，不覆盖原证据。

#### 2026-10-13 S4最终收据与停止线

S0/S1/S2/S3/S4限定工程均已实现并执行对应验收；整体全仓/外部验收仍PARTIAL。上述“进行中/待执行”是按时间保留的阶段日志，以本段最终结果为准。没有为了绿灯删除旧断言、换原始输入或重写fixture。统一方案T01—T35的具名行为由最终回归及独立浏览器覆盖；T36本轮只完成范围审计和未来授权门禁，真实新干预/知识试点未授权，NOT_RUN，不能当已实现能力。正式PROJECT_ROADMAP未变，下一工具需要所有者真实阻塞与另行批准；无阻塞则暂缓。

Git基线df98b92ed30b052ea6e71965401eeb8571307608；最终执行源码de00ec3b55d3fb6ea64bd3fde15b7d732526b0a5，tree 6fd5f2428ffeaecc798ead7df46bfced9b2dabd5。新增本地提交d3a5f7b、d07285f、cca4275、6bf5d2f、7e16f5c、de00ec3分别为收据/包、静态修正、有限信息身份、判断/推荐、原UI、One-shot说明修复；后续仅验收文档提交，最终HEAD/tree由delivery_receipt记录，不能回填为测试开始SHA。运行前后225个src/apps/scripts/tests文件、核心依赖、Python、平台及pyproject输入一致；required coverage、JUnit实际用例和真实exit核验BOUND。

运行环境Windows/i5-12500/Python3.13.3/Chromium153.0.8010.12。下面`python`实际为`.venv/Scripts/python.exe`，工作目录仓库；OMP_NUM_THREADS/MKL_NUM_THREADS/OPENBLAS_NUM_THREADS=1。测试进程删除OPENAI_API_KEY/DASHSCOPE_API_KEY/TEACHER_API_KEY，默认状态库及项目分别为`.v24s/final-r2/default_safety.sqlite3`、`default_project`，测试另用隔离临时库，不修改用户原库。没有新付费调用、资料外发、确认标签读取或生产迁移。

| 最终执行命令 | 实际结果/exit | 身份与范围 |
|---|---|---|
| `python -m pytest -q --basetemp=.tsfull2 --junitxml=.v24s/final-r2/full-final2.xml --tb=short` | 846 passed / 2 failed / 6 skipped / 9 warnings，6486.70s，exit1 | JUnit suite 6486.687s；V24 111项全部通过且包含于846内，不与阶段测试相加 |
| `python -m pytest -q tests/browser/test_agent_workspace.py -k v24 --basetemp=.tsbr3 --junitxml=.v24s/final-r2/browser.xml --tb=short` | 1 passed / 2 deselected，272.533s，exit0 | `FFA_BROWSER_E2E=1`、`FFA_UI_BROWSER_ARTIFACTS=<repo>/.v24s/final-r2/browser`；实际Chromium/worker，start/end绑定BOUND |
| `python scripts/run_v24_engineering_validation.py --output-root .v24s/final-r2/pilot-source-final2 --run-engineering` | 4/4 PASS，exit0 | 原四臂工程门槛，不是Live或金融证据 |
| `$taskChangedPy = @(git diff --name-only df98b92ed30b052ea6e71965401eeb8571307608 -- '*.py'); python -m ruff check @taskChangedPy` | All checks passed，exit0 | 本轮全部修改Python |
| `python -m compileall -q src/finance_forecast_agent apps scripts` | exit0 | 相关Python目录 |
| `node --check apps/workspace_frontend/views.js`；`git diff --check` | 各exit0 | 前端语法、差异空白 |
| `python scripts/verify_frozen_spy_acceptance.py --inputs inputs --check-input-only --receipt .v24s/final/frozen-input-check.json` | exit1，BLOCKED_ASSET | 没有运行替代smoke或读取确认标签 |

全仓命令前使用`collect_v24_receipt.py --evidence-root .v24s/final-r2 --begin-run full-final2.xml --command <上表完整命令> --input pyproject.toml`，required-node为closure_audit/information/judgment/recovery/delivery五个V24测试文件、test_workspace_ui.py、test_workspace_ui_formula.py、test_focused_provider_json_boundary.py。执行后先捕获`$LASTEXITCODE`，再`--end-run full-final2.xml --exit-code 1`；不从JUnit推断实际exit。浏览器同样begin/end，required-node为tests/browser/test_agent_workspace.py。全仓JUnit SHA256 `572a22466b64ae7d72b109cb87987a9b368cce7618adc6f11a129db384e4a11a`，pyproject SHA256 `ce40d239b9681568c6eb56d32f32920054ca4c36f6fe50566217c848c84aaebd`。归集命令`python scripts/collect_v24_receipt.py --evidence-root .v24s/final-r2 --browser-name browser`只读取证据，不执行模型；最终receipt区分source SHA与文档最终SHA，source hash为b3f4c962df5cb99f1afad6e12632953519ccd7f9fe260bb9675f99dd14877b10。

最终四臂OFF/ON/Random/One-shot：24/24/28/28 charged fits，总104；9/9/10/10预测制品，共38逐行和fold复算；43/43/48/46索引成员，共180 SHA核验；逻辑规划2/2/2/1，外部HTTP0，provider cost及human operation minutes为null。raw输入SHA256 `0798460be4a950b39cb848833148b324cb35b642b834cb110b8e161e135ea8bd`，dataset `e7a1fc373a8f1a86b8004e32bff559150f48a2fdf3d86793e08961869844eb58`，预登记hash `68528b3c6b403c8aef134674b72e13e5defbf6760ab2bba72905eadb4bb2473c`。均simulation_only、真实本地估计器，不是真实行情表现；全部retain_start，未强迫获胜。与并行回归同机的wall只作运行审计，不作效率优势证明。

可复现当前演示：用新目录运行上表pilot命令，读取`rule_on/focused_campaigns/rule_on/`的初始diagnostics、contexts、batch_plans、observations、campaign.json及research_package目录。实际链为初始诊断→第一轮两个合法单特征候选真实训练→确定性观察→第二轮基于已完成control的双特征条件实验→冻结retain_start→完整研究包。三个候选均completed、prediction_provenance=new_execution；其中第二轮观察does_not_meet，如实保留。当前J不再机械删除首轮失败特征回到起点；显式缓存/贡献消融仍由独立用例验证。原章节§11的旧删除消融演示保留为历史，不冒充当前J。

浏览器最终报告`.v24s/final-r2/browser/v24/report.json`包含19项检查：3个完成候选切换、刷新、新context、只读公式/包、续接预检、原Mission新Campaign、父记录不变、诊断篡改拒绝和显式refit。研究父24+子24=48fits、18attempts，refit1单列；只读无新增fit/HTTP，page_errors=[]。输入是cb063f4b608912b32e4ac2ea905a1d542389bbae80a6c974c51f97e129bc457b模拟数据。`.v24s/s3-browser-recheck.xml`的4通过为S3工作树阶段证据；只有上述1项明确在de00ec3执行并绑定，不能把4项都冒称同最终SHA重跑。

| 最终失败/跳过或开放项 | 准确分类、原因及恢复路径 |
|---|---|
| `tests/test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink]` | BLOCKED_ENV：创建模拟symlink时WinError1314，尚未进入joblib加载。需合法符号链接权限或另行批准平台；本轮不改全局权限、不删断言 |
| `tests/test_p1_real_validation_artifacts.py::test_dlinear_strict_live_card_replays_without_an_api_call` | BLOCKED_ASSET：原`projects/finance_agent/llm_fixtures/method_card/2c05bfd22af27435.json`不存在。必须恢复匹配原字节/上下文，不用其他fixture改名、不补Live |
| 4个tests/browser opt-in skip | 全仓没有开启浏览器flag；本轮阶段完整矩阵4通过、最终V24另1通过，证据身份分别保留 |
| `test_queue_recovers_real_interrupted_worker` | NOT_RUN：原POSIX process-group probe；Windows原生worker另测，不冒充POSIX通过 |
| `test_package_rejects_symlink` | BLOCKED_ENV/原平台skip：symlink permission unavailable |
| 原冻结SPY输入 | BLOCKED_ASSET：同名raw文件存在但不是规定5fb282原始字节，spy_source.json缺失；不拿当前修订字节或模拟数据替换 |

9 warnings为8条已有record_property/xunit2警告及1条故意构造duplicate ZIP的负例警告，不删除负例求无警告。历史两失败未改测试，本轮没有观察到新增产品失败。旧A/L的全部原对象与基线逐项保持，只追加本轮关联；47目标负确认不变。

分轴：限定S0—S4工程PASS；全仓总体PARTIAL；有限规则行为PASS（simulation_only，R/D/J未证明J胜出）；真实Provider语义、策略价值、所有者/独立用户、独立金融效果均NOT_RUN。自动collector的strategy_behavior保守为NOT_RUN，其定义不是有限规则单测，不从全仓通过推导策略增益。Linux同SHA CI/推送、macOS、GPU/大型native、可选O/K、V2.5+均NOT_RUN；全仓历史适配测试不代表小时级原论文训练。后续只有所有者按用户指南真实操作、记录主动时间/帮助/一项阻塞；恢复历史资产/平台或Live需相应条件/授权。本轮到此停止。

收尾文档检查：`python -m pytest -q tests/test_focused_b0_plan.py tests/test_focused_r0_status.py --basetemp=.tsdocs3 --junitxml=.v24s/final-docs.xml --tb=short`，4 passed/5.86秒/exit0；不与全仓846相加。验收JSON所有原顶层字段与df98b92逐项序列化比较，变化0；只新增v24_s0_s4_20261013。git diff --check exit0。此后仅本地文档提交和只读收据归集，不再改功能源码。

### 2026-10-10 批准的复审收口

以3097ece为本轮实际基线，修复复现的输入/恢复/上下文/收据缺口，不扩研究能力。新增planning_projection_v2及diagnostic_price_advice_v2显式合同；v1纯投影读取保留，旧fixture/hash不修改，活动任务按原源码版本处理而非强行迁移。64000字符上限不提高；训练/组范围与共同来源确定性去重，完整审计继续原RuntimeDB和制品。固定baseline_ridge为相对诊断参照，在Campaign前冻结，不按组内成绩重新挑控制；正loss_delta表示候选更差，与观察的control-minus-child改善符号区分。样本门槛仍是描述性而非显著性。

RCP-04/05允许有界diagnose需求设计并持久保存，不执行窗口或组合；缓存消融完成的是新观察，不是新模型或免费fit，仍消耗原槽，仅允许剩余的第二次规划。ON投影读取所有已完成提案观察，OFF不接收新增诊断源或观察。异常结构进入原proposal_invalid终态，不自动修复/补请求。

pilot在输入预检前登记四臂分母，构造/执行/导出/校验全部纳入失败收据；只有执行完成且包审计通过才PASS。新测试收据需运行前start manifest及结束后的实际exit/hash；缺绑定、零测试、全跳过、计数不一致或覆盖不足均不能PASS，策略行为不继承全仓PASS。历史收据只作历史，禁止覆盖。

本轮五批限定修复与适用工程验证完成，完整产品/外部验收仍PARTIAL。实际执行提交7be2fab6db4a6e6ea5154423e07538d7d3dfdf53，tree 06f8e4153e3fd885ae115632fdaac3260112e515；基线3097ece873108ac80253078c6f39bb9fe483124a。后续只提交验收文档，准确最终HEAD/tree由收据记录，不回填测试启动SHA。Windows/i5-12500/Python3.13.3；执行源码419dd4b245bc6f4315dcd147df5bcac924bf9657b3b1667195544fa9558f0cce，核心依赖及全部222个源码/前端/脚本/测试文件身份在运行前start和运行后end中绑定；实际exit1、JUnit SHA256 37e60b6eae3086c20aec1bb58ae6468ef46db6c9c0fb79a59f23a0c026ac8d6f。归集使用与执行一致的正常进程权限；受限沙箱枚举不全时应拒绝绑定而非PASS。

| 批次/复审行为 | 最小实现与真实负例归属 | 本轮结论 |
|---|---|---|
| 收据真值/失败分母 | pilot预检、构造、导出、审计失败；manifest缺失/计数错误/全跳过/exit或源码或覆盖不匹配；test_pilot_all_failure_stages_remain_failed、test_shared_input_failure_preserves_all_arms_and_nonzero_cli、test_manifest_binding_cannot_invent_a_pass | PASS，模拟故障 |
| 非法结构/需求设计 | 共用结构门禁先于字段访问；null、混合列表等7负例终态且resume不重规划；RCP04/05自定义有界需求保留设计而不训练 | PASS，assistant fixture，基线12fits/研究0fits |
| 缓存观察/原预算 | 首轮全缓存消融产生新观察，引用实际复用模型，ON第二规划接收、OFF无泄漏；只用原第二规划，恢复不refit | PASS，实际本地训练及缓存 |
| compact两轮 | 显式v2来源去重/列式规划投影；ON/OFF、提供起点、约3900字符备注、两次规划及resume，64000上限未变 | PASS，无真实Provider |
| 有限策略依据 | 完全对齐候选/Ridge预测的相对组损失；相同全局MAE但弱点位置不同；具名特征必须每fold常数，移除实际组件而非数组末项 | PASS，手算/规则行为，非策略价值证明 |
| 原UI/交付/累计回归 | 两轮真实worker、提供起点续接、只读切换/刷新/新context、包及显式refit；本轮新增27项与原V24 44项 | PASS，simulation_only实际Chromium/训练 |

证据根目录`.v24-review-assessment-20261010`，不覆盖历史收据。最终命令：`.venv/Scripts/python.exe -m pytest -q --basetemp=.t24full --junitxml=.v24-review-assessment-20261010/final-delivery/full-final2.xml --tb=short`，OMP/MKL/OPENBLAS_NUM_THREADS=1，运行前`collect_v24_receipt.py --begin-run full-final2.xml --command <上述命令> --required-node tests/test_focused_v24_review_fixes.py --required-node tests/test_focused_v24_delivery.py --required-node tests/test_focused_v24_recovery.py --required-node tests/test_workspace_ui.py`，运行后`--end-run full-final2.xml --exit-code 1`。805 passed、2 failed、6 skipped、5592.52秒/exit1；其中V24 71 passed/0 failed/0 skipped（含27新增，不额外相加）。全仓工程轴PARTIAL。两个失败：`tests/test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink]`，首异常WinError1314/BLOCKED_ENV，需合法symlink权限或另行批准的平台验证；`tests/test_p1_real_validation_artifacts.py::test_dlinear_strict_live_card_replays_without_an_api_call`，首异常FileNotFoundError/BLOCKED_ASSET，需原匹配2c05bfd22af27435.json及上下文，不能改名其他fixture。原5fb282冻结SPY资产仍缺，本轮未另跑原smoke。4 browser opt-in跳过已由独立矩阵验证；另2跳过为POSIX process-group probe及Windows package symlink权限，不能写PASS。

实际浏览器矩阵4 passed/590.53秒/exit0（browser-matrix.xml），Chromium153.0.8010.12、page_errors=[]。复现方式：设置FFA_BROWSER_E2E=1及独立FFA_UI_BROWSER_ARTIFACTS/FFA_BROWSER_ARTIFACTS输出目录，运行`.venv/Scripts/python.exe -m pytest -q tests/browser --basetemp=<新的短临时目录> --junitxml=<新的报告.xml>`；不要覆盖本轮browser-matrix及browser-matrix-old证据。V24报告19项检查、研究fit总44（父20/续接24）、attempt17；显式refit1另计；候选只读切换/刷新/new-context没有新增fit或HTTP。模拟输入raw cb063f4b608912b32e4ac2ea905a1d542389bbae80a6c974c51f97e129bc457b。

离线四臂：`.venv/Scripts/python.exe scripts/run_v24_engineering_validation.py --output-root .v24-review-assessment-20261010/pilot-repair --run-engineering`，exit0，OFF20/ON20/Random28/One-shot28共96fits，逻辑规划2/2/2/1、外部HTTP0、费用null、真人主动时间null；4 PASS必须执行完成且导出/审计完成。36预测制品逐行及fold复算，172索引文件；4臂均retain_start，不要求ON获胜。raw 0798460be4a950b39cb848833148b324cb35b642b834cb110b8e161e135ea8bd，dataset e7a1fc373a8f1a86b8004e32bff559150f48a2fdf3d86793e08961869844eb58，预登记bc757a71d8c81968d3459061b9bf3948184246762be4d8b8d55823d3b1e075ad。纯simulation，不是市场表现或真实模型质量。

本地HTTP录制→严格离线Replay在正常权限/短临时路径下1 passed/88.38秒/exit0（delivery-http.xml），模拟HTTP1、Replay HTTP0、各独立Campaign20 fits且计划/数值一致。此前target-frozen.xml为70 passed/1环境路径失败/1326.72秒；delivery-short.xml为8 passed/1沙箱HTTP未到达失败/157.54秒；不能称这两次全绿，最终全仓该节点已通过。更早fixes-first/second/third、compact/start容量失败及browser-repair启动失败全部保留；部分中间合同不匹配源于测试期间修改源码，最终改为冻结后完整重跑，未删除断言或扩大上限。适用Ruff8文件、compileall src/apps/scripts、node --check views.js及git diff --check均exit0。

正常与负例的新证据关联T07—10/T15—17/T19—20/T22/T26/T28/T30/T33—36；原A/L与47目标负确认逐字段保留。完整审计中保留所有来源/范围与生成特征相关对；规划v2只给有界摘要及完整审计hash/引用，不宣称所有原始数组都进入prompt。相对fold_reference列顺序为fold_id/group/rows/reference_mae，fold_values为candidate_mae/loss_delta；正值更差，不是统计显著性。

基线tree d6584e7dd462359dfc21f843a87f033c1a0056af。离线四臂wall分别52.40/51.48/73.48/71.93秒，合计249.29秒；当时有并行测试，不能用于研究效率优劣论断。全仓控制台5592.52秒与JUnit suite 5592.506秒是不同计时边界。最终源码不再变化，后续文档提交不等于重跑测试。历史复用仅引用旧证据；本轮重跑、模拟/真实、PASS/FAIL/BLOCKED/NOT_RUN按上述项区分。自动收据不从全仓PASS推导策略轴，strategy_behavior保守标NOT_RUN；本节有限规则行为由具名负例单独证明，Live语义及真实研究价值仍未验证。

限制：极端DB/输出均不可写可能无法完整持久化，证据缺口需明确，缺记录不能自动重发，也不承诺恰好一次计费。有限策略行为PASS不代表Live语义/策略价值；后者、所有者/独立用户、独立金融证据均NOT_RUN。DSL独立确认仍不支持。原资产/权限缺口保留；Linux同SHA CI、macOS、GPU大型native、推送、生产迁移及V2.5+均NOT_RUN。不调用付费Provider，不外发、不读取确认标签。可以结束本轮限定代码修复，按FRONTEND_USER_GUIDE进入所有者实际试用；不能代签真人验收或启动下一版本。

SPY daily下一XNYS session调整收盘收益回归、forecast_only；主筛选MAE/0.0025/development_only。原价格DSL、参数域、两条生成特征（含继承）、固定模型/参数/seed/预处理/内置组、共同W64和四fold不变。新协议显式选择；旧候选/fixture/hash/模型数值语义不改。保留原Exposure/Trust/RuntimeDB和47目标负确认。

Adaptive最多两次规划、每次两槽、总四槽；One-shot一次冻结四槽计划，执行单元两项。显式diagnose占规划和槽，不能新增第三轮。非法/重复/失败/draw/HTTP/refit按原账本，无生成式修正、自动换模型或搜到赢家才停。纯诊断fit/HTTP=0，实际计算耗时另记。三基线四fold=12 fits，四新候选16；独特起点再4，实际缓存/配置决定容量，显式refit额外计费。

本轮仅隔离simulation数据/库与本地HTTP工程测试；不操作用户真实任务。不推送/远端CI，不付费调用/资料外发/独立确认/V3-P；API key不构成授权。GPU/macOS/大型native不执行。

## 2 诊断数据权威（R3）

首次规划前在起点/基线完成后自动生成，接受实验后更新；版本、输入/目标/训练范围、成本绑定，缓存不可变。MAE/残差（pred−true）/分位数/预测幅度从完整PredictionArtifact派生，逐行身份、顺序、fold、label、split、candidate/hash必须吻合。错合同为contract_error，不裁有利交集，也不标样本不足。稀疏预测窗口不作连续自相关。

过去20日收益波动来自合同绑定raw调整价格及相同return构造，映射真实raw行。每fold q75只取共同协议训练校准行，固定linear quantile、strict >。未来价格不影响过去状态；不能对预测y_true滚动。真实X/实际训练mask计算方差、冗余、生成列；safe_divide分别记录节点事件、distinct触发行和0—1行率，明确范围与分母，不用全历史聚合冒充训练。训练预测缺失则train-dev gap unavailable，无隐式重训/下载。

残差均值非零不授权平移；近常数不是失败；低相关不保证组合更好。只允许一个事前固定、完全对齐的既有预测对作0.5/0.5只读损失诊断，不创建组合候选/推荐/包。

## 3 观察与配方（R1/P1/P2/P3）

代码拥有有限规则模板，禁止eval、任意算子/阈值。增加特征：整体严格MAE改善，或高波动组改善且全局不退化。高波动默认30总行、至少两fold各10行、至少两fold改善，所有合格fold均报告。贡献消融：删除后更差可满足局部贡献观察，但不能推荐更差child。简化：声明复杂度减少且其它不增加，容忍退化0；等分更简单不是预测增益或统计非劣效。纯diagnose只有有来源观察，0新候选。

三态meets_predeclared_observation/does_not_meet/insufficient_evidence，合同错误独立。原精度比较，展示四舍五入无权改变判定；观察、主筛选、最终推荐分别存储。文本与数值冲突标解释需复核。

每项实验冻结依据（可见事实或domain_hypothesis）、竞争解释或unknown、实际parent/control、不变条件、具体AST、规则实例、预期及否证。引用必须已接受/兼容/可见，不引用同批未来结果。RCP-01尺度表达实例不限5/20，仍在现有合法DSL域；RCP-02单真实特征消融；RCP-03真实简化；RCP-04窗口需求与RCP-05组合需求只记录，不执行后续功能。

## 4 选择与三层冻结（R4）

Campaign前冻结能力/诊断/模板/预算/选择政策；实验前冻结具体依据/规则/AST/parent/control；外层揭示前冻结最终推荐/动作/完整config/输入/context/policy。结果后改rule/control或揭示后重选均拒绝。

选择保留原筛选参照：固定控制与合格用户起点的最佳MAE，改善门槛0.0025；parent和起点差另列。研究候选和最终推荐分开：无候选research=null，退化保留真实分数；保留合格起点不是新发现。候选须完整可比，满足主筛选且不比起点差；同分保留起点，其余固定ID排序不依赖完成次序。无合格起点unresolved；取消/失败/部分保留失败状态，即使保守保留起点亦不洗成研究成功。best_available_model独立含控制，不当兜底起点。

## 5 信息公平与恢复（R2/P4）

Diag-ON/OFF同编译器、能力、配方/模板域、原反馈、固定模型、预算、静态提示及冷Memory。仅新增诊断—观测反馈包的可见性不同。ON可真实诊断依据；OFF可旧可见结果或domain_hypothesis，空symptom refs/unknown合法，同合法AST两组均能训练。实际引用两组同门禁；不按隐藏诊断缩小OFF动作域。OFF不能从摘要、Memory、tools、文字或人工介入得到新诊断；后台审计与planning projection分离。相同行动合理，不强迫制造差异。

冻结上下文/计划/诊断/规则/推荐沿原RuntimeDB不可变对象与artifact机制复用。已接受工作不重训，成本不回退；HTTP=0临时前置修复、已录制非法响应、未知投递按原三条恢复规则，无自动补请求。完整录制校验原prompt/schema/call-ID。新schema显式分派，未知语义拒绝，不能改旧hash强行恢复。

## 6 UI、交付与验证

只增量接原研究/实验/成果：实际诊断/公式diff/control/竞争解释/规则数值/状态/限制、选择角色与成本。刷新/切换/new-context/读公式/读包HTTPfit=0。ResearchPackage含版本/上下文清单/诊断/观察/推荐且遵循原许可投影；不可见证据不导出。ModelBundle保持显式refit、原可信登记、fresh-process原始无标签推理，解释JSON不是模型。

预登记OFF/ON+同语法Random参考的小simulation矩阵，所有停止/失败/无候选入分母；不把失败MAE填0，不把开发比较当独立预测。模拟外层拒绝访问是协作式工程边界，不是生产多租户隔离；DSL confirmation_supported=False保持。

## 7 批次与验收映射

D24-0合同；D24-1诊断；D24-2规则/配方；D24-3UI/包/选择；D24-4诊断策略/冻结恢复；D24-5公平对照/模拟隔离；D24-6只准备预检/脚本/真人收据入口。本轮不以D24-6未授权停止工程。

| 条款 | 行为与测试归属 |
|---|---|
| T01—T02 | 完整制品合同/hash/行身份，无交集 |
| T03—T06 | 手算残差/MAE/均值反例/常数/组合反例 |
| T07—T08 | raw past-only状态、训练校准阈值 |
| T09—T14 | 观察样本/全fold/方向/精度/冻结/文本矛盾/缺来源 |
| T15—T18 | 引用/真实消融/简化/原能力负例 |
| T19—T22 | 自动0fit/显式槽/one-shot/真实抽样账本 |
| T23—T27 | 原JSON边界/容量/HTTP恢复/篡改/审核能力 |
| T28 | ON/OFF所有规划投影权限 |
| T29—T31 | 推荐角色/null/失败分母/外层前冻结 |
| T32—T36 | 原曝光/只读UI/旧身份/证据分类/包绑定 |

每条具体nodeid、命令exit/JUnit、来源hash、HTTPfit和未测边界写最终收据；历史复用与本轮重跑分开。负例→定向→相关回归→静态→worker/browser→最终全仓一次。保留Win symlink权限、匹配DLinear fixture及原5fb282冻结输入BLOCKED，不改断言/旧hash/统一skip。旧A/L只有新增关联。

### 原D24-T01—T36条款（编号及行为要求保留）

| 条款 | 反例/行为 | 必须结果 |
|---|---|---|
| D24-T01 | 候选/控制目标、label、split或数据身份不同 | 比较拒绝，不取任意交集 |
| D24-T02 | 行乱序、重复、损坏hash或非法缺行 | 明确合同错误，不伪标小样本 |
| D24-T03 | 人工小数组MAE、残差与分位数 | 数值、符号、单位与独立手算一致 |
| D24-T04 | 残差均值非零而中位数为零 | 不产生自动均值修正或成功结论 |
| D24-T05 | 合理近常数基线 | 不因幅度小直接判模型失败 |
| D24-T06 | 低相关但更差的等权组合 | 显示实际组合损失，不能自动推荐 |
| D24-T07 | 未来收益修改、未来日期插入 | 过去特征/状态不变；不合法数据前置拒绝 |
| D24-T08 | 分组阈值试图使用全开发或未来数据 | 只用冻结训练校准范围；分组版本可查 |
| D24-T09 | 组总量不足、仅一折够数、诊断unavailable | insufficient_evidence，保留理由 |
| D24-T10 | 组内改善但整体退化；或改善仅一折 | does_not_meet，主MAE政策不被覆盖 |
| D24-T11 | 规则边界值、严格/非严格比较、展示四舍五入 | 使用原精度及冻结算子判定 |
| D24-T12 | 运行后改阈值、参照或组定义 | 原规则不可变；新政策不得改当次结果 |
| D24-T13 | LLM文本称成功但数值不满足 | 确定性状态不改，解释标复核 |
| D24-T14 | 缺训练预测或跨窗口存在时间空隙 | 不新增fit，不拼接连续自相关 |
| D24-T15 | 引用不可见、不同权限或同批未来证据 | 编译拒绝；文献保持原authority |
| D24-T16 | 空生成程序消融、删除不存在特征、消融同时增项 | 训练前拒绝 |
| D24-T17 | simplify增加另一复杂度；配方改变锁定模型/seed | 训练前拒绝 |
| D24-T18 | 偷加窗口/权重/ensemble/未知DSL/schema字段 | 不降级、不忽略、不代理执行 |
| D24-T19 | 首次基线完成、诊断重新载入、刷新重算 | 初始诊断存在，新增HTTP/fit为零，计算成本可查 |
| D24-T20 | 首轮或第二轮显式diagnose | 占对应规划/槽；无免费第三决定 |
| D24-T21 | One-shot前两项完成后提出重写后两项 | 不重新规划；冻结全计划可回放 |
| D24-T22 | 非法/重复提案、无效sampler draw、超总槽 | 原计数与逐决定draw上限一致，不补额度 |
| D24-T23 | 原始Provider/Replay重复JSON key、超限/非有限值 | 首个raw边界拒绝，不等AST才拒绝 |
| D24-T24 | 28 fits配置增加独立起点、诊断或refit | 预检真实容量；计数和授权独立，失败预留不退款 |
| D24-T25 | HTTP=0修复、已记录非法响应、未知交付后重启 | 三种恢复路径按原合同；无自动付费补发 |
| D24-T26 | 冻结prompt/诊断/配方/规则或制品被篡改 | 恢复拒绝，不用新内容改历史结果 |
| D24-T27 | review批准后试图增加特征/确认权限 | 保持capability与原确认拒绝 |
| D24-T28 | OFF臂通过解释、Memory、工具读到新增诊断或外层信息 | 所有投影入口验证拒绝，泄漏会使对照无效 |
| D24-T29 | 无完成研究候选，或全部差于基线 | 研究指标null/真实劣化；兜底角色单列 |
| D24-T30 | 某臂失败/早停/不输出推荐 | 留在预登记分母；质量比较另报覆盖，不赋MAE=0 |
| D24-T31 | 外层揭示后换推荐、挑任务或补跑赢家 | 冻结身份校验拒绝；记录协议偏离 |
| D24-T32 | 旧数据换目录/别名或换seed声称blind | 曝光谱系不变，独立声明拒绝 |
| D24-T33 | UI切换/刷新/新context/打开公式/读包 | HTTP/fit不增加，队列无重复任务 |
| D24-T34 | schema新旧混读、旧hash/fixture回放 | 已知legacy兼容；未知新语义拒绝；旧字节保持 |
| D24-T35 | 工程模拟、助手fixture或owner操作被标真人/Live | 证据类别准确，不能关闭真实条款 |
| D24-T36 | 诊断包、推荐配置、ModelBundle来源不一致 | 交付拒绝；原trusted loader/refit防护保持 |

## 8 条件性后续路线（本轮只维护）

| 版本/一句话 | 重点、功能与框架 | 边界/进入条件 | 简单例子与证据 |
|---|---|---|---|
| V2.5.0：选择哪些历史行 | 原Controller新增TrainingPolicy有限expanding/rolling | 实际窗口需求、批准共同目标/eligible行政策；不同时改特征 | 比较756窗口；专家非平稳实践，增量待完整流程外层验证 |
| V2.5.1：降低旧样本权重 | 固定窗口，有限半衰期、同normalized_w传Scaler/Ridge | 窗口工程稳定、政策批准；同时改变标准化尺度及正则效果 | uniform/衰减；数值等价容差事前定，旧hash不变 |
| V2.6：按需交付两个预测成员 | 原交付链固定0.5/0.5、成员身份 | 实际互补/交付需求，批准总复杂度；不嵌套/学权重，不是V3前置 | 两成员平均，专家组合实践；需实际损失及成员选择独立验证 |
| V3-P：先记录固定基线未来预测 | 可单独批准并行时点/修订/成熟记录 | 新输入/运行合同，真实时钟，不回填冒充未来 | 今日冻结预测、明日成熟；不交易 |
| V3.0：候选/对照Shadow | 原授权模型配对前瞻、准时覆盖与评价 | 候选合格、隔离与新能力批准；不自动换生产 | 退化提示新Mission，预测增益需前瞻证据 |
| V4.0：经验帮助研究方向和预算 | 原Memory检索→有限方向选择→可选多保真 | 多样合格episode、固定规则不足、独立meta评价 | 优先消融；专家经验实践，检索/bandit增量需cold/warm验证 |
| V4.1：一个相邻任务或可信源 | 复用原合同/曝光，单维扩展 | 需求/许可/as-of与单独ADR；可提前单独审查 | QQQ或一种可信数据，不同时扩多个维度 |
| V5：窄研究接口与受控扩展 | 原预检/提交/读状态/下载接口 | 重复需求/价值/隔离审查；不任意代码/交易平台 | 外部工具查诊断；接口效率需真人验证 |

以上专家实践不继承预测优势；潜在诊断可见性、经验选择和效率增量必须实验/真人验证，不宣称超过专家或消除泄漏。

## 9 本轮日志

D24-0：核对正式分支/HEAD，tracked clean，原10个未跟踪证据目录保留。Windows/i5-12500/Python3.13.3；未调用Provider/读取确认/变更全局环境。实现与实际测试后逐批补记。

D24-1/2/3/4工程：纯诊断及问题规则沿原Controller持久化，0自动fit/HTTP；实际parent/control/规则/公式与投影绑定；cold OFF/ON、新工作区和选择角色；原ModelBundle refit/trust加已核实推荐来源。先保留red1导入失败、诊断样本范围断言和实际消融复用计数失败；实现后20项/191.32s、旧相关111项/8.95s、扩展30项/541.64s通过。后续发现并保留浏览器1续接投影错误、delivery1耗时进入pair prompt导致Replay hash不等，以及browser2新refit绑定被旧白名单拒绝。最小修复后delivery2 8项/152.21s；browser3续接独特起点预算不足时规则策略仍提2项，保留失败并修为按剩余fold容量提案（不加预算），budget-fix 5项/4.94s、browser4 1项/100.56s通过。最终target 16项/46.94s包含文本矛盾、坏fold、来源缺失和已接受诊断恢复。上述均模拟/本地真实fit，不是付费Live。

工程对照pilot1四臂通过，HTTP=0，分别20/20/28/28fits，ON/OFF最终最佳研究MAE相同且均保留起点。没有强迫不同答案或胜出；Random也保留实际draw账本。这是本轮早期源码证据，最终源码pilot-final/完整回归另列，不把阶段收据当同HEAD验收。core1在浏览器3发现预算问题后显式终止，保留临时证据；没有完整JUnit，不计PASS。

交付边界补测：binding-red复现同candidate_id但不同实际配置仍进入refit；最小修为同时核验原contract/tenant/dataset/accepted config fingerprint及推荐hash，binding-fix 7项/171.15s、独立config/tenant/dataset三负例73.31s通过，相关原合同/JSON/编译回归80项/47.61s通过。browser-delivery-final 1项/150.10s含模型来源绑定、诊断篡改导出拒绝；较早完整新旧浏览器4项/708.86s通过，来源版本分别保留。

evidence-red发现新增诊断未同步原EvidenceIndex可见ID/投影hash；最小修为复用同一个EvidenceIndex，ON增加真实ID、OFF保持旧可见范围。首次修复遗漏局部import导致4项NameError，失败JUnit保留；静态及0fit入口1项/2.82s通过后，ON/OFF同合法AST与local HTTP→严格Replay三项/184.09s通过。原core2/full在binding-red复现后主动终止，不计完整回归PASS；最新功能源码hash50368ab46305d0e6091b383cd2ff2f384dd9e88cfc9445fecf51ccb7482a90cc，此后冻结src，在full-final/browser-source-final/pilot-source-final完成最终验收。

D24-6预检/清单/收据准备已实现：离线驱动默认NOT_RUN/不读取凭证/不dispatch；显式本地计算才创建隔离目录，拒绝覆盖历史。`collect_v24_receipt.py`只归集JUnit/git/输入身份和分轴状态，不运行模型。真人签名/主动用时不由助手填写；真实Provider/政策价值/独立金融轴依旧需单独授权和条件。

## 10 逐项实施/测试索引（结果以最终JUnit/收据为准）

下表V24文件均为`tests/test_focused_v24_*.py`；旧用例表示原能力复用，并由本轮受影响回归再次核对，不是新建另一实现。

| D24条款 | 真实行为用例 |
|---|---|
| T01/T02 | diagnostics::test_complete_artifact_identity_rejects_no_intersection；campaign::test_initial_and_updated_diagnostics_frozen_rules_recommendation_and_resume |
| T03/T04/T05 | diagnostics::test_mae_mean_bias_counterexample_and_constant_is_not_failure |
| T06 | diagnostics::test_low_correlation_does_not_authorize_combination；固定Ridge/RF一对实际初始组合诊断，无新模型交付 |
| T07/T08 | diagnostics::test_volatility_uses_price_prefix_and_training_calibration_not_labels；原test_focused_feature_program因果性/XNYS用例 |
| T09/T10/T11 | diagnostics::test_group_rule_all_folds_small_samples_and_precision |
| T12 | 同上规则篡改；recovery::test_db_body_tampering_rejected_even_with_original_file_hash |
| T13 | 不满足时解释需复核，数值状态独立；campaign初始/更新观察用例 |
| T14 | diagnostics残差用例明确unavailable，不重训、不拼连续序列 |
| T15 | campaign::test_invalid_v24_design_no_repair_no_candidate_fit；原EvidenceIndex与文献权限回归 |
| T16/T17 | 原test_focused_feature_execution::test_feature_ablation_rejects_joint_change / test_feature_simplification_must_reduce_actual_complexity；V24第二轮实际贡献观察 |
| T18 | 原test_focused_feature_contract::test_new_or_unknown_fields_never_silently_downgrade / test_expression_boundary_rejected_before_execution |
| T19 | campaign初始诊断/完成恢复；recovery::test_diagnostic_export_failure_reuses_db_body_without_fit_or_replanning |
| T20 | campaign::test_explicit_diagnose_uses_original_decision_and_slot，两种轮次 |
| T21 | recovery::test_real_v24_worker_crash_reuses_context_rule_A_and_charges_B；One-shot全部计划冻结，不重规划后两槽 |
| T22 | 原test_focused_price_sampler两计数用例；原feature_campaign重复/整计划拒绝用例 |
| T23 | 原test_focused_provider_json_boundary首次raw解析/模拟HTTP/Replay负例，原字节未修改 |
| T24 | 原feature_bundle失败refit计费；原feature_campaign预算与独特起点容量；V24中断尝试不退款 |
| T25 | 原test_focused_b5_crash_recording / feature_recovery，前置修复/未知投递/坏录制三种路径 |
| T26 | recovery DB/prompt/plan/recommendation篡改；campaign诊断文件篡改 |
| T27 | campaign::test_v24_review_retains_frozen_context_and_original_budget；原feature_contract确认前置拒绝 |
| T28 | campaign::test_same_legal_ast_on_visible_basis_off_domain_basis / test_v24_rejects_hidden_memory_and_uncontrolled_evidence_before_fit；pilot公平权限冻结 |
| T29 | diagnostics::test_selection_no_candidate_all_worse_ties_partial_and_determinism；invalid设计无研究结果null |
| T30 | pilot::test_pilot_failure_denominator_frozen_before_original_controller_dispatch；全部预登记臂保留，费用null |
| T31 | recovery推荐篡改拒绝；原feature_contract::test_confirmation_preflight_and_grant_reject_before_any_authority_or_labels / test_legacy_selection_and_simulation_confirmation_reject_program_before_frame_access，在模拟读取/fit函数上设置失败哨兵，实际前置拒绝；外层标签没有授权也没有读入；模拟隔离不称生产安全证明 |
| T32 | 原test_focused_r4_trust曝光更名/等价时间负例；新DSL确认仍前置拒绝 |
| T33 | tests/browser/test_agent_workspace.py[v24]，真实worker/Chromium；复用旧两模式浏览器 |
| T34 | 原feature_contract golden identity、原fixture边界；delivery新协议local HTTP→无key严格Replay |
| T35 | pilot::test_d24_6_preflight_no_dispatch_no_credentials_read；receipt分开simulation/Live/owner/独立用户；真实条款仍NOT_RUN |
| T36 | delivery研究包逐成员SHA/逐行原evaluator复算；原feature_bundle fresh-process/trusted加载；页面模型与当前候选绑定 |

R1=问题方向与选择分开（T09—13/16—17/29）；R2=OFF领域假设同AST合法及冷Memory（T15/28）；R3=raw/X/prediction来源与不可用（T01—08/14/19）；R4=三层冻结/选择动作（T12/26/29—31/36）。P1=合法AST非固定菜单；P2=q75/30/10/2描述性门槛不作显著性；P3=本地模拟隔离及present_day_research边界；P4=原2规划4槽/有限1对只读组合、后续窗口/权重仅需求记录。

D24-6操作：先运行`python scripts/run_v24_engineering_validation.py --output-root <新目录>`只预检。加`--run-engineering`才运行隔离模拟4臂；不读取key。提供已有真实开发输入还需`--raw-spy-json <path> --allow-development-compute`明确许可与开发用途，不能冒称独立确认。默认不覆盖已有目录。真实Live/所有者/独立用户、政策价值和金融轴需后续分别授权/实际操作，不能用工程收据代替。

## 11 功能源码验收及可复现演示

功能提交68ba12ef5e8a68da6bb0fdc5d12e67567904dde9的所有包内Python模块执行源码身份为50368ab46305d0e6091b383cd2ff2f384dd9e88cfc9445fecf51ccb7482a90cc，browser-source-final与pilot-source-final完成期间未改src。full-final出现旧B5六项summary精简上下文的AttributeError，定向legacy-summary-red 6失败/2.60s、b5-final-probe 37通过/6失败/104.91s保留；只终止已核实PID/出生时间/命令的本次全仓进程，未完成JUnit不计PASS。最小兼容修复只在summary用getattr取得可选diagnostic_policy，不改原六个断言/终态/筛选；legacy-summary-fix 6通过/2.36s。新最终源码身份faa6b0801e330b050a50b902cc5ed81b2ac14c91cf555af6151b9a1952554fd8，在full-final2/browser-source-final2/pilot-source-final2启动前冻结，旧完整/中止证据另列。后续收据/文档提交不是远端同SHA CI；本轮不推送。较早源码通过记录不合计成最终测试数量。

命令工作目录为仓库，Python均为`.venv/Scripts/python.exe`，OMP_NUM_THREADS、MKL_NUM_THREADS、OPENBLAS_NUM_THREADS均为1。

| 最终执行 | exit/结果 | 收据与范围 |
|---|---|---|
| `python -m pytest -q --basetemp D:/b05runs/v24-20261009/full-final2-temp --junitxml D:/b05runs/v24-20261009/full-final2.xml --tb=short` | 1；778 passed、2 failed、6 skipped，5566.01s | 最终全仓，2既有环境/资产阻断单列；非全仓全绿。44项V24均通过且已包含在778内 |
| `python -m pytest -q tests/test_focused_b5_increment.py tests/test_focused_v24_diagnostics.py tests/test_focused_v24_campaign.py --basetemp D:/b05runs/v24-20261009/legacy-summary-reg-temp --junitxml D:/b05runs/v24-20261009/legacy-summary-reg.xml --tb=short` | 0；71 passed，733.89s | 保留原43项B5、新14项纯诊断和14项实际Campaign行为 |
| `FFA_BROWSER_E2E=1 FFA_UI_BROWSER_ARTIFACTS=D:/b05runs/v24-20261009/browser-source-final2 python -m pytest -q tests/browser/test_agent_workspace.py tests/browser/test_research_workspace.py --basetemp D:/b05runs/v24-20261009/browser-source-final2-temp --junitxml D:/b05runs/v24-20261009/browser-source-final2.xml --tb=short` | 0；4 passed，721.81s | Windows真实Chromium153.0.8010.12、原真实worker；新V24/旧价格/legacy和原Research Workspace review流程。无页面JS错误 |
| `python scripts/run_v24_engineering_validation.py --output-root D:/b05runs/v24-20261009/pilot-source-final2 --run-engineering` | 0；4/4臂工程PASS | rule_off/on/random_reference/one_shot_demo，20/20/28/28 fits；外部HTTP=0 |
| 原focused CI的Ruff文件集合，另含`apps/workspace_ui*.py tests/test_workspace_ui*.py scripts/run_v24_engineering_validation.py scripts/collect_v24_receipt.py` | 0；All checks passed | 文件集合按PowerShell Get-ChildItem展开，不依赖外部命令处理通配符 |
| `python -m compileall -q src/finance_forecast_agent apps scripts` | 0 | 全相关Python |
| `node --check apps/workspace_frontend/forms.js`；`node --check apps/workspace_frontend/views.js` | 各0 | 曾误用不存在的workspace_ui_frontend路径返回MODULE_NOT_FOUND，属于检查命令路径错误；未改JS掩盖问题 |
| `git diff --check` | 0 | 无空白错误 |

浏览器V24保存19项实际检查、16个attempt/40 charged campaign fits（父20+续接子20），另有显式refit1。读公式、切换、刷新、新context、续接预览均不增加HTTP/fit；篡改模拟诊断文件后导出拒绝。截图/研究包/真实模型ZIP在`browser-source-final2/v24/`；报告的raw SHA256为cb063f4b608912b32e4ac2ea905a1d542389bbae80a6c974c51f97e129bc457b，仅模拟数据。前一源码browser-source-final的4通过/626.46s继续保留为独立历史收据。

最终离线pilot-source-final2原始模拟输入SHA256为0798460be4a950b39cb848833148b324cb35b642b834cb110b8e161e135ea8bd；dataset fingerprint e7a1fc373a8f1a86b8004e32bff559150f48a2fdf3d86793e08961869844eb58；预登记hash b5b8693b4d1ed44f0d09293d56c20833979a3823212df4bf9b7553dc8c651911。1100原始行→1035监督行/252开发target。四臂政策/来源/source hash/seed/能力在任何dispatch前冻结。实际逐臂wall73.12/76.54/95.81/92.72s（同机并发回归期间，不能当效率优势）；自动诊断新增fit/HTTP=0，CPU秒不可取得、费用/人工主动用时null。36份PredictionArtifact聚合和fold指标从完整行用原evaluator重算，172个包成员SHA逐个核对。四臂均retain_start，没有要求ON或Adaptive获胜。推荐时间沿原不可变final/campaign.json中的created_at和原events记录，完整final绑定同一推荐body/hash；不另建时钟或状态库。

可复现演示（新目录，不能覆盖既有证据）：

```powershell
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:OPENBLAS_NUM_THREADS="1"
.\.venv\Scripts\python.exe scripts/run_v24_engineering_validation.py --output-root D:/b05runs/v24-my-demo --run-engineering
```

查看`rule_on/focused_campaigns/rule_on/`中的`campaign.json`、`diagnostics/`、`contexts/`、`observations/`、`batch_plans/`与`research_package.zip`。此CLI演示不会自称注册成原UI中的用户Mission。实际链：初始Ridge残差/raw/X诊断→合法rolling_mean(return_1,20)提案→4fold真实训练，MAE0.007331007277095696→整体观察meets（相对Ridge绝对改善0.000014991978354799741）→第二轮真实删除该特征的贡献消融，编译配置命中已接受Ridge，按原缓存语义不refit；删除更差支持贡献观察，仍不是推荐更差模型→主0.0025筛选未达→冻结retain_start→包逐行审计。另一个rolling_std(return_1,5)候选MAE0.007349511754582295，does_not_meet；退化数值没有藏入最佳基线。该流程只证明工程与有限策略行为，不证明市场机制或金融增益。

用户界面操作沿用FRONTEND_USER_GUIDE末尾清单：原环境/状态库启动Streamlit→新研究/受控价格特征→诊断可见/规则演示/Adaptive Batch/2轮2槽32fits→实际候选详情→成果中的选择角色/研究包→显式refit及可信模型。不得为演示重置原曝光或信任。所有者和独立操作者的主动时间、帮助与结果需本人填；助手没有代签。

## 12 最终交付状态与未完成边界

| 批次 | 实际实现/复用 | 结果 |
|---|---|---|
| D24-0 | AGENTS/ADR006/唯一合同/路线/条款与实际基线，完整保留T01—T36 | PASS；原48条A/L语义与状态和95760e逐项相等 |
| D24-1 | 纯诊断投影、原Controller自动调用、原RuntimeDB持久化；raw/X/预测来源与unavailable | PASS；自动新增fit/Provider=0 |
| D24-2 | 有限问题规则、实际parent/control、竞争解释、不变条件及合法AST配方；原compiler/evaluator | PASS；MAE/贡献方向/简化反例及实际观察 |
| D24-3 | 原工作区增量面板、选择角色、原研究包和显式refit/trust、配置/租户/数据绑定 | PASS（限定工程）；历史symlink平台覆盖缺口单列 |
| D24-4 | 真实诊断驱动的有限策略、原两决定/四槽、whole One-shot、原HTTP恢复与严格Replay | PASS（模拟、本地真实fit/worker）；不是付费Live语义PASS |
| D24-5 | 同Controller/caps/compiler/budget/cold Memory四臂预登记，原账本/失败分母/模拟外层访问拒绝 | PASS（工程）；无生产隔离或独立收益证明，四臂均保留起点 |
| D24-6准备 | 无dispatch预检、工程驱动、真实操作者清单及只读收据 | PASS（准备）；实际Provider/真人/价值/金融NOT_RUN |

最终全仓JUnit SHA256：50b624b09445595e19353e7bedd98b02175cfc00d541ff4ebff22b1e965d39f9。适用核心/Queue/Memory/MethodCard/review/工作区从同一JUnit归集629 passed/1 failed/2 skipped（632项），不是另一次运行；全部44项V24通过。71定向、44新增、629子集与778全仓有重叠，不能累加。4项真实浏览器独立开启flag通过，解释全仓4个opt-in skip，不掩盖另2个平台未运行项。

| nodeid/资产 | 首个异常及分类 | 与本轮关系、恢复要求 |
|---|---|---|
| `tests/test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink]` | 创建模拟bundle symlink时OSError/WinError1314，尚未进入joblib加载；BLOCKED_ENV | 与基线同环境失败；known-symlink-env.xml也exit1/1失败/4.81s。需合法symlink权限或另行授权的Linux，不能删断言/擅改全局权限 |
| `tests/test_p1_real_validation_artifacts.py::test_dlinear_strict_live_card_replays_without_an_api_call` | FileNotFoundError：`projects/finance_agent/llm_fixtures/method_card/2c05bfd22af27435.json`；BLOCKED_ASSET | 与基线同缺口。恢复匹配的原录制/源文档/上下文，不改名别的fixture、不改hash、不用deterministic卡替代；未发送API |
| 原冻结SPY SHA256 5fb282f6278d14000592e0e432fe69a5c00fdb6f7b48cbb56368fc0e3185bbcd | 原字节不可用；BLOCKED_ASSET/该验收NOT_RUN | 不拿0bb089修订历史或模拟行情替代，也不下载新确认标签 |

其余2个全仓skip：`tests/test_focused_pr4_persistence.py::test_queue_recovers_real_interrupted_worker`为POSIX process-group probe，Windows原生和新增spawn恢复另测但不冒充该POSIX用例；`tests/test_focused_r6_workspace.py::test_package_rejects_symlink`原平台条件因symlink权限跳过。8个warning是原record_property/xunit2兼容警告，未删属性求无警告。

分轴：限定工程PASS、有限规则策略行为PASS（simulation_only）、真实Provider语义NOT_RUN、研究策略价值NOT_RUN、独立预测NOT_RUN、所有者/独立真实用户NOT_RUN；整体产品/科学验收仍PARTIAL。Windows/Python3.13.3/Chromium153实际执行；Linux无本轮远端执行/同SHA CI，macOS/GPU/大型native NOT_RUN。全仓含历史/native适配回归，不表示小时级原论文训练已重跑。没有生产迁移、历史清理、外发、付费调用、推送或V3-P实跑。

最小后续事项：所有者先实际试用并填主动时间/帮助/失败；独立用户另找真实操作者。测Provider语义/策略价值须另行明确模型、额度/HTTP/token/时间费用预算、发送内容和预登记协议；独立预测须另行批准支持的协议及合格数据/前瞻时点，不能解锁当前DSL确认或洗白历史曝光。资产/平台缺口按上表恢复，不新增大平台规划。

本地提交与最终HEAD/tree、各组JUnit路径/哈希、Python/依赖、输入/政策/成本及失败原因以`D:/b05runs/v24-20261009/delivery_receipt.json`为审计收据。脚本expected_exit从JUnit推导，实际exit在上表列明。该脚本不执行模型/读取API key/关闭原A/L条款。后续文档/收据改动未改变已测试faa6b080…执行源码身份，不能称远端同SHA CI。

浏览器复现需PowerShell显式设置（上表env前缀仅表示环境，不是PowerShell命令）：

```powershell
$env:FFA_BROWSER_E2E="1"
$env:FFA_UI_BROWSER_ARTIFACTS="D:/b05runs/v24-browser-my-run"
.\.venv\Scripts\python.exe -m pytest -q tests/browser/test_agent_workspace.py tests/browser/test_research_workspace.py --junitxml D:/b05runs/v24-browser-my-run.xml
```

每次用新的报告/临时目录保留证据。启动/真实操作见FRONTEND_USER_GUIDE；完整工程演示见上一节。本轮完成后停止，不自行进入后续开发或外部活动。

最终文档检查首次误用不存在的test_focused_roadmap_contract.py，执行exit1/0 tests；final-docs.xml空报告保留为NOT_RUN，不算通过。改用实际原test_focused_b0_plan.py和test_focused_r0_status.py重跑，exit0/4通过/2.24s，见final-docs2.xml；这是执行命令路径错误，不是被删除或改名的测试。
## 2026-10-14 试用前 P1—P5 / G0—G6 增量（限定工程完成，G6待本人）

本轮用户直接批准必要工程修正及试用准备。附件与ZIP同名方案字节一致，SHA256 `78db8ddd3772a756fdd69564d86cf0e43bc5089ab94e716b2fb509b5371d5191`；讨论材料是来源，不是第二合同。实际起点 `8f8e45069478af637bcfcc76098ea4ba0427414a`，branch `feat/mission-research-v2`；tracked clean，所有旧验证目录保留。正式路线不变，原36项、A/L和47目标负确认不改。

先运行外部原始 `review_s0_s4_20261014/test_independent_edges.py`，**3 failed / 33.27s / exit1**，`.v24p14/red.xml`：当前J缺四项仍通过；纯函数与实际One-shot重复缓存均错误标为事后。不是把审核推测直接认定为缺陷。

新运行使用 `diagnostic_research_v4` / `diagnostic_price_advice_v4`，旧活动合同必须原源码恢复，不改hash迁移。P1强制J训练四项且与response_schema一致；R/D及Random参考设计不伪造理由，stop/review无dummy训练字段。P2从冻结计划/上下文可见结果判断形成时点，缓存来源单列，未知时序明确unknown；不可变历史不重分类。P3仅投影已有计划及获准反馈；OFF不读新增观察，原逻辑两次/四槽预算不变。P4仅有界条件/命名常量简化/已知停止/无症状领域探索。P5仅现有入口、事实显示与本机交付验证，不新建权威系统。

阶段负例与失败均留在 `.v24p14/`。最大设计文本+4000备注+独特起点的第二轮容量负例已复现64k阻断（`.v24p14/admission-first.xml`与`capacity-detail.xml`），不得截断、提高64000上限或增加生成调用求通过。最终源码/测试/依赖/输入冻结后另跑全仓，阶段结果不冒充最终通过。

真实输入：既有 `inputs/spy_chart_2010_2025.json`，SHA256 `0bb0896126adb0393f34ae09b90487cb501b2c6aa681a66d2a8f02348669036b`。用户在2026-10-14针对该精确文件的本机开发与受控试用权限确认回复“能”；来源依据保留原Yahoo获取/开发日志。`.v24p14/real-source.json`是本次所有者确认元数据，不是独立法律审核/再分发授权；不下载新数据、不替换5fb282、不读取确认标签。两入口实际计算/可信交付的最终收据见本节末。主机预演/目标用户理解只能本人完成，助手不得代签。

当前 **NO-GO（G6主持人本人预演未完成）**；下方最终证据确认G0—G5限定技术准备，allowed_advisor_mode仅`deterministic`，不是Live通过。Live L0—L3、本轮远端CI/推送、GPU/macOS/大型native、金融效果均NOT_RUN。不把目标用户完成试用设为招募前循环门槛。

### 本轮协议与验收映射

v4在任何规划前冻结每份design所有字符串值合计1000字符（包含既有研究理由及J四项），不截断已返回的文本；R/D/Random显式参考合同，旧无此标志的v1参考设计兼容。新schema给出可执行的J示例而不是漏字段的旧模板。为容纳两次决定的完整原判断，规则表用shared/columns/values，诊断公共字段和训练scope哈希用递归ref共享，保存原数值与完整制品；未扩大64000上限、结果范围或OFF权限。新source/version不用于强行恢复旧冻结合同。

N01—N22是行为映射，不是22次独立运行；测试集合之间会重叠，结果不得相加。simulation_only指数据/HTTP回复，估计器fit、worker与浏览器本地实际运行。

| 条款 | 实际测试/入口 | 证据性质 |
|---|---|---|
| N01—03 | `test_focused_v24_pilot_admission` J必填/旧合同/R/D/Random/schema；`test_focused_v24_delivery` local HTTP缺J拒绝、保留录制及离线重放 | 模拟回复，实际入口；不是Live质量 |
| N04—07 | 原独立三负例；`test_focused_v24_information`、pilot_admission cache/timing四路径 | 冻结上下文时点、缓存来源、unknown、反向/模板身份；不改历史 |
| N08 | `test_focused_v24_recovery::test_real_v24_worker_crash_reuses_context_rule_A_and_charges_B` | 真spawn进程中断，保留已接受A/冻结计划；20→24 charged fits |
| N09—11 | pilot_admission `test_schema_links_max_designs_long_notes_and_real_recovery` ON/OFF；review_fixes compact独特起点 | 原四项/规则hash/反馈关联；1000字符每design、4000备注，两决定；OFF无新增观察 |
| N12 | pilot_admission `test_four_limited_strategy_challenges`；原judgment/review_fixes策略负例 | 条件、具名常量简化、已知停止、无症状探索；不强迫差异或赢家 |
| N13—14 | 原judgment无候选/更差/失败/取消与diagnostics选择；campaign、feature_strategy、provider runtime/recording测试 | 复用原账本/筛选，最终全仓确认 |
| N15 | pilot_admission授权/hash/曝光三负例；原workspace/feature_contract预检 | 不合法输入前置拒绝0dispatch；不造假行情 |
| N16—17 | `scripts/verify_v24_trial_admission.py`；browser `[v24]` | 既有真实0bb089输入；goal/provided_start，2轮×2槽、32研究fits上限，显式refit另计 |
| N18—20 | delivery包身份/复算；真实两入口driver与browser；原feature_bundle/R4 trust | 原状态权威、包逐SHA/指标复算、只读0增量、新进程无标签预测；symlink权限缺口单列 |
| N21 | 最后源码冻结的全仓、actual worker/browser、Ruff/compileall/node/diff | 以实际exit、JUnit和开始/结束manifest为准；无远端CI |
| N22 | FRONTEND_USER_GUIDE主持清单及G6本人记录 | NOT_RUN，助手不可代签；目标用户NO-GO |

阶段真实浏览器`.v24p14/browser-real-stage.xml`实际exit0、1 passed/174.14s；Chromium153.0.8010.12、19检查、父子48研究fits/18 attempts、refit1另计、HTTP0、页面错误为空，包9预测/46成员复算。这是助手技术验证，非主持人预演。阶段两入口driver `.pr14a/receipt.json` exit0，24/28研究fits，另各1refit；各4004无标签输出与fresh Python完全相等。此为阶段记录，最终冻结源码绑定见下节。

### 2026-10-14 最终收据与准入结论

实际源码提交`1bdcacebb99788877b880e22fe402bc49cecdc86`、tree `bafe569db414e7b2d5c8477867405ea67c5a7e86`；起点8f8e450，既有用户/历史目录保留。本次没有改正式路线、原36条和48条A/L内容。最终文档提交与源码提交分开，最终HEAD/tree以本地git及`.v24p14/final/delivery_receipt.json`为准，不能称远端同SHA CI。227源码/测试文件、所记录核心依赖运行前后相同，实际exit写入end manifest。勘误：两个输入仅有开始快照与汇总时核对，结束输入快照未记录，不能据此证明运行结束时哈希相同；旧收据不补写快照。未发现真实输入被替换的证据，但证据缺口不能作完整输入BOUND。

目标环境Windows11 build26200、i5-12500、Python3.13.3、Chromium153.0.8010.12；numpy2.5.3/pandas3.0.6/sklearn1.9.1/Streamlit1.64.0/pytest9.1.1/ruff0.16.8/Playwright1.63.0/Optuna4.9.0。命令均在仓库根运行，`python`表示`.\.venv\Scripts\python.exe`。最终全仓PYTHONPATH=`src;tests`，真实driver/浏览器=`src`，OMP/MKL/OPENBLAS线程数显式1。测试集合有重叠，不能累计成一次通过数。

| 实际命令（省略前述python完整路径） | actual exit / 结果 | 证据 |
|---|---|---|
| `python -m pytest -q --basetemp=.tp14full --junitxml=.v24p14/final/full-final2.xml --tb=short` | **1；867 passed、2 failed、6 skipped；stdout6460.78s，JUnit6460.745s** | 最后功能变更后的全仓；132项V24全通过并包含在867内；9 warnings，不是全绿 |
| `python -m pytest -q tests/test_focused_v24_delivery.py tests/test_focused_v24_pilot_admission.py tests/test_focused_v24_pilot.py tests/test_workspace_ui_formula.py --basetemp=.tp14j --junitxml=.v24p14/last-targeted.xml --tb=short` | 0；35 passed、706.87s | 阶段定向，后由最终全仓覆盖 |
| `python -m pytest -q 'C:/Users/13716/.codex/visualizations/2026/09/29/01a0eaf6-ca29-7db3-832d-e208ce48acca/review_s0_s4_20261014/test_independent_edges.py' tests/test_focused_b0_plan.py tests/test_focused_r0_status.py --basetemp=.tp14orig --junitxml=.v24p14/independent-green.xml --tb=short` | 0；7 passed、58.46s | 原3负例未修改，另4状态/文档测试 |
| `python -m pytest -q 'tests/browser/test_agent_workspace.py::test_agent_workspace_real_backend[v24]' --basetemp=.tp14br2 --junitxml=.v24p14/final/browser.xml --tb=short` | 0；1 passed、281.54s | FFA_BROWSER_E2E=1；实际Chromium/worker，真实0bb089数据；start/end身份一致 |
| `python -m pytest -q tests/browser/test_agent_workspace.py tests/browser/test_research_workspace.py -k 'not v24' --basetemp=.tp14br3 --junitxml=.v24p14/final/browser-legacy.xml --tb=short` | 0；3 passed、1 deselected、449.69s | FFA_BROWSER_E2E=1；模拟旧工作区/价格/原Research Workspace，实际Chromium/worker |
| `python scripts/verify_v24_trial_admission.py --output-root .pr14b --raw inputs/spy_chart_2010_2025.json --source-metadata .v24p14/real-source.json --expected-sha256 0bb0896126adb0393f34ae09b90487cb501b2c6aa681a66d2a8f02348669036b --allow-local-development-compute` | 0；两入口PASS，159.74/150.93s（并发回归期间，不作速度承诺） | 源码1bdcace、tracked_changes为空；`.pr14b/receipt.json`保存实际配置、库/项目/任务/包ID和模块hash |
| 原focused CI Ruff集合+workspace UI/测试+三个V24脚本 | 0；All checks passed | 完整集合展开命令见下方 |
| `python -m compileall -q src apps scripts tests` | 0 | 最终源码检查 |
| `node --check apps/workspace_frontend/forms.js`；`node --check apps/workspace_frontend/views.js` | 各0 | 最终前端语法 |

Ruff实际PowerShell集合：

```powershell
$files = @(Get-ChildItem src/finance_forecast_agent/focused*.py, tests/test_focused*.py, tests/browser/*.py, apps/workspace_ui*.py, tests/test_workspace_ui*.py | ForEach-Object FullName) + @('src/finance_forecast_agent/research_mission.py','src/finance_forecast_agent/task_queue.py','src/finance_forecast_agent/experiment_memory.py','src/finance_forecast_agent/replay_llm.py','src/finance_forecast_agent/llm_adapters.py','src/finance_forecast_agent/review_state.py','scripts/review_focused_literature.py','scripts/verify_frozen_spy_acceptance.py','scripts/run_focused_spy_campaign.py','scripts/run_research_value_benchmark.py','scripts/verify_price_feature_pilot.py','scripts/run_focused_confirmation.py','scripts/probe_focused_failure_semantics.py','scripts/run_v24_engineering_validation.py','scripts/verify_v24_trial_admission.py','scripts/collect_v24_receipt.py','apps/pages/8_Focused_Research.py')
.\.venv\Scripts\python.exe -m ruff check $files
```

最终全仓SHA256 `791a8e5587f9ec69a8314f28e1ff71cbc39a42f804eeda88bcc516710d3cab83`。真实raw SHA为0bb089…；来源/权限声明SHA `8a50b99524ff0f3a12fdbc5f140ced835d38f71c1334fee0bd660d9735ef754b`。后者是所有者本机许可声明，不是独立法律/point-in-time审核或再分发授权。数据未下载/替换，4024原始行→3959监督行，2010-04-07至2025-12-30、historical_development_only；不是5fb282验收或独立确认。

浏览器完整环境：真实运行使用`FFA_UI_BROWSER_ARTIFACTS=<repo>/.v24p14/final/browser-source-final2`，`FFA_ADMISSION_REAL_RAW=<repo>/inputs/spy_chart_2010_2025.json`、`FFA_ADMISSION_SOURCE=<repo>/.v24p14/real-source.json`、`FFA_ADMISSION_SHA256=0bb089…完整hash`；旧矩阵没有这三个REAL开关，artifact根为`<repo>/.v24p14/final/browser-legacy`。legacy start manifest的命令描述误写`-k not-v24`，实际工具执行的是上表`-k 'not v24'`；原收据未修改，更正单为`browser-legacy.command-correction.json`。真实浏览器旧自动化任务名仍含synthetic，这是自由任务标题而非数据来源：界面实际显示历史开发/3959行，输入hash/metadata明确真实；保留截图原貌，不把标题当数据身份。本次本人预演使用`.pr14b`的技术任务，不使用做过篡改负例的浏览器临时库。

最终真实两入口均completed、冻结`select_research_candidate`：先测mean(return_1,20)与std(return_1,5)，再以已接受的单特征候选作control测组合，保留更好的单特征研究候选。这里是有限规则行为，不是模型理解或市场机制证明。goal24/提供起点28 charged fits、attempt9/10；各2逻辑决定/3实际槽/4预留槽/1未用结清槽，HTTP0；各显式refit1次另计，不影响原研究账本。研究包各9/10预测、46/49成员用原evaluator逐行复算/SHA核对。各4004行原始无标签输入，fresh Python退出0且逐值等于原进程；不是样本外表现。两入口只读切换/new service快照及预测后计数不变。真实浏览器另外验证父子48fits/18attempts、refit1、19检查、刷新/新context/切换/读包0新增HTTP或fit，页面错误=[]；包9预测/46成员复算。费用与人工主动用时为null；不同运行的计算没有相互冲销。

| G gate | 结论与实际边界 |
|---|---|
| G0 | PASS：原红例→绿；J/schema、缓存时点、原判断关联、OFF及四挑战行为有实际测试 |
| G1 | PASS（本次试用路径，历史例外明确）；全仓实际exit1/PARTIAL而非全绿，未知新产品失败0，源码/核心依赖/输入绑定及实际worker/browser通过 |
| G2 | PASS：所有者确认的真实开发输入、两个入口预检0fit/HTTP、真实训练/冻结推荐/交付；操作者是助手技术验证，不是用户验收 |
| G3 | PASS：原目标主机研究包复算、原可信登记+新进程无标签推理、只读0增量；不提供跨机信任或任意模型导入 |
| G4 | PASS（准备）：FRONTEND_USER_GUIDE含短任务书A/B、真实配置/启动/ID、主持步骤、失败处理和空白记录表 |
| G5 | PASS（仅规则工作流）：allowed_advisor_mode=deterministic，Live L0—L3 NOT_RUN/未批准；四段齐全不证明LLM会研究 |
| G6 | NOT_RUN：所有者/主持人未提交本人真实操作预演记录；助手浏览器不能代签 |

**目标用户试点NO-GO；允许进入主持人本人预演。** G6完成且无新阻塞后，仅放行1—3人的规则工作流试点；不要求先有目标用户验收才允许招募。Live理解/策略增量、真实用户价值、独立金融效果仍未验证，不从工程PASS推断。Windows实际执行，Linux/同SHA远端CI未授权，macOS/GPU/大型native、本次付费Provider/外发/确认标签/生产迁移/后续版本NOT_RUN。没有推送。

### 历史例外与保留的失败

全仓失败1：`tests/test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink]`，fixture创建symlink时报WinError1314，未进入joblib；BLOCKED_ENV。需合法Windows权限或另行授权的平台验证，不删断言/改全局权限。本次实际路径只使用自己生成、原登记的本机包；`.pr14b`159条目检查无symlink/junction，不能据此声称该攻击在Windows已验证。

全仓失败2：`tests/test_p1_real_validation_artifacts.py::test_dlinear_strict_live_card_replays_without_an_api_call`，FileNotFoundError缺`projects/finance_agent/llm_fixtures/method_card/2c05bfd22af27435.json`；BLOCKED_ASSET。DLinear不在本次Ridge试用路径，须恢复匹配原录制/原上下文，不能用其他fixture改名。无API调用。上述两文件的失败与基线相同，相关生产实现未被本次修改，不豁免新产品失败。

6 skipped：4个opt-in浏览器在同源码独立4通过；`test_focused_pr4_persistence::test_queue_recovers_real_interrupted_worker`为POSIX进程组探针，Windows真实spawn/Queue恢复另测但不冒充POSIX；`test_focused_r6_workspace::test_package_rejects_symlink`因Windows权限跳过。原5fb282输入缺失、A/L开放项和47目标负确认均历史复用、不重写为PASS。

所有迭代失败保留在`.v24p14/`：red 3失败/exit1；p12-first 64通过3失败/842.88s（并发改源码导致恢复合同不一致、测试helper错误强制非诊断J、容量问题，后续冻结及helper修复）；admission-first/second与capacity-detail/third/fourth的容量失败分别为15/1、15/1、0/1、31/1、18/1，均exit1；capacity-fifth 18通过/170.40s/exit0。delivery-recovery 22通过2失败/459.30s是沙箱localhost不可达（实际HTTP0），普通权限重测local-http-normal 2通过1失败/258.98s的剩余失败是测试错误索引stop.result，保留且修正为核对全部状态与实际训练结果；最终35定向和全仓覆盖通过。未删断言、历史fixture或失败记录。初始spy真实演练`.pr14a`和阶段浏览器亦保留，不冒充最终source-bound证据。

最终文档更新后，`python -m pytest -q tests/test_focused_b0_plan.py tests/test_focused_r0_status.py --basetemp=.tp14docs --junitxml=.v24p14/final/docs.xml --tb=short`实际exit0、4通过/7.44s；`git diff --check`退出0。此为文档检查，不替代/重写冻结全仓。总收据的通用collector历史scope描述仅作原字段保留，实际数据性质以新增scope注释、browser.input_provenance、`.pr14b/receipt.json`和`pilot_admission_receipt.json`逐运行记录为准；模拟回归与真实行情技术演练不能混淆。

### 2026-10-14 独立复审：结束输入快照修复与勘误

基线2fcdd23d4bad27d646f83143dfe1f80ac26a9a6f，正式分支不变，tracked clean、原未跟踪证据保留。两项意见均核实：P2在原收据工具中复现，P3首页仍写进行中而末节已完成。审核其余肯定结论仅按已有具名证据复用，不据审核文字新增Live/真人/金融通过。

原审核`review_pilot_20261014/test_input_end_binding.py`原样运行：`.p14fix/red.xml`，1 failed/6.54s/exit1，返回PASS/BOUND而应FAIL。所有输入均临时模拟文件，HTTP=0、fit=0；没有篡改真实SPY或历史收据。最小修复提交08ca0555a9c1167bce552b94be10ebd411285d33，tree8874d5a3752d09fa138dd64f3d66c745228f949c，只改collector及新增测试，不改研究/页面/账本/模型语义。

新start/end v3：结束时按原开始清单的精确路径记录输入SHA256，结束命令不能换输入清单；缺文件/权限错误保存null和异常类型，不丢实际exit。汇总必须开始、结束、当前三组映射完全一致。旧记录缺结束快照明确PARTIAL；不补写旧字段、不覆盖原BOUND历史输出，而以本勘误限制其解释。三次快照不是连续文件监控，不能证明快照间从未瞬时改变。运行使用受控操作者和冻结输入，未增加第二套运行权威。

新增`test_focused_v24_receipt_inputs.py`12项：正常、结束变化、变化后恢复、结束缺失、缺失后恢复、汇总变化/缺失、路径集合变化、旧格式缺结束/两端字段、结束不可读、结束CLI更换输入。`.p14fix/target.xml`24 passed/31 deselected/9.63s，pytest exit0；同次Ruff曾报PIE807，已最小改为dict并保留输出，后续Ruff exit0。原反例+12项重跑`.p14fix/green.xml`13 passed/7.49s/exit0。准确命令：`python -m pytest -q tests/test_focused_v24_receipt_inputs.py <原审核目录>/test_input_end_binding.py --basetemp=.tprfixgreen --junitxml=.p14fix/green.xml --tb=short`。compileall src/apps/scripts/tests及diff检查exit0。

冻结后新证据根`.p14fix/final`，真实两入口为`.pr14fix`，不覆盖`.v24p14/final`或`.pr14b`。全仓与浏览器begin/end使用新collector、明确required_nodes及三个输入（raw0bb089、原许可元数据8a50b9、pyproject）。全仓与浏览器完成状态待下面最终收据，不能把原867通过升级成08ca055通过。

真实两入口命令：`python scripts/verify_v24_trial_admission.py --output-root .pr14fix --raw inputs/spy_chart_2010_2025.json --source-metadata .v24p14/real-source.json --expected-sha256 0bb0896126adb0393f34ae09b90487cb501b2c6aa681a66d2a8f02348669036b --allow-local-development-compute`，actual exit0，goal/provided_start各PASS/89.958s、108.663s。两入口各4004行fresh-process预测逐值一致/child exit0、各1显式refit、只读计数不变、外部HTTP0。命令执行前后Get-FileHash核对raw和元数据相同；实际收据`.pr14fix/receipt.json`。仍是所有者授权真实开发输入的助手技术演练，不是G6本人或独立金融验证。

浏览器首次`.p14fix/final/browser.xml`：`python -m pytest -q tests/browser --basetemp=.tprfixbr --junitxml=.p14fix/final/browser.xml --tb=short`，2 passed/2 failed/396.23s/actual exit1。失败是启动命令把仅支持v24的真实输入环境开关带入legacy/price_features，二者在测试前置assert拒绝；这是本轮执行配置错误，不能把该报告整体写PASS，也没有改断言。v24真实行情与原Research Workspace两节点通过，实际19检查/页面错误空/只读零增量。关闭三个FFA_ADMISSION_REAL_RAW/SOURCE/SHA256开关后重跑：`python -m pytest -q tests/browser -k 'not v24' --basetemp=.tprfixbr2 --junitxml=.p14fix/final/browser-legacy.xml --tb=short`，3 passed/1 deselected/442.12s/actual exit0。这次是旧模式模拟输入；独立新start/end快照保留，两次合起来覆盖4个独特节点，不把重复节点相加作5项。两次均FFA_BROWSER_E2E=1，实际Chromium/worker，源码未变。

为将最终真实准入收据与旧模式分开，另在同一冻结源码单独运行原v24节点（不是修断言求绿）：`python -m pytest -q tests/browser/test_agent_workspace.py::test_agent_workspace_real_backend[v24] --basetemp=.tprfixbr3 --junitxml=.p14fix/final/browser-v24.xml --tb=short`，1 passed/211.93s/actual exit0。FFA_UI_BROWSER_ARTIFACTS指向`.p14fix/final/browser-v24-corrected`，三个真实输入开关恢复原授权raw/meta/hash。最终浏览器依据为该1项+旧模式重跑3项，首次2/2报告保留；重复训练成本不抵销。v24报告19检查、18attempts/48研究fits、显式refit另计、9预测/46包文件复算、page_errors空、刷新/new-context/切换/只读0新增HTTP或fit。源码与三个输入开始/结束快照一致，最终汇总时再核对当前字节。

#### 本次独立复审最终验证与停止线

两项审核意见属实并完成修复。上述“待最终收据”是施工阶段记录，以本段为准。执行源码08ca055、tree8874d5a3752d09fa138dd64f3d66c745228f949c；228个src/apps/scripts/tests文件及所记录核心依赖开始/结束/汇总时相同。全仓新JUnit SHA256 `8545f0ea8e8af7677ddbdf8e150c82a688467f20f5f710218641a298b6d7d433`，旧`.v24p14/final/full-final2.xml`仍为791a8e…原字节。真实raw、许可元数据、pyproject的三个输入映射开始/结束/当前均一致，`input_binding_status=BOUND_start_end_current`；新结束格式v3已实际用于CLI。三时点采样仍不证明采样间连续不变。

环境与上一轮相同：Windows11/i5-12500/Python3.13.3/Chromium153.0.8010.12；Python为`.venv/Scripts/python.exe`，工作目录仓库。PYTHONPATH=src;tests，OMP/MKL/OPENBLAS线程数1；子进程移除Provider keys。全仓默认库/项目为`.p14fix/final/safety.sqlite3`/default_project，测试另用隔离临时库。没有新外部Provider、确认标签、生产迁移或远端CI。

| 本轮最终命令 | actual exit / 结果 | 收据及性质 |
|---|---|---|
| `python -m pytest -q --basetemp=.tprfixfull --junitxml=.p14fix/final/full-final2.xml --tb=short` | **1；879 passed/2 failed/6 skipped/9 warnings，stdout6430.09s；JUnit6430.074s** | 887实际用例；全部144项V24通过，含新增12项，已包含于879；整体PARTIAL |
| `python -m pytest -q tests/browser -k 'not v24' --basetemp=.tprfixbr2 --junitxml=.p14fix/final/browser-legacy.xml --tb=short` | 0；3 passed/1 deselected，442.12s | 模拟旧模式，实际Chromium/worker；源码/依赖/输入三方BOUND |
| `python -m pytest -q tests/browser/test_agent_workspace.py::test_agent_workspace_real_backend[v24] --basetemp=.tprfixbr3 --junitxml=.p14fix/final/browser-v24.xml --tb=short` | 0；1 passed，211.93s | 真实获准开发输入；源码/依赖/输入三方BOUND |
| 前述`verify_v24_trial_admission.py --output-root .pr14fix ...` | 0；两入口PASS | 24/28 charged fits、9/10 attempts、各2规划/3槽/4预留槽、各1refit；外部HTTP0；19预测/95成员复算；各4004行fresh-process一致 |
| 适用focused+workspace+browser+验证脚本Ruff；`python -m compileall -q src apps scripts tests`；forms.js/views.js `node --check`；`git diff --check` | 各0 | 静态检查；没有修改研究/前端源码 |

开始命令为`python scripts/collect_v24_receipt.py --evidence-root .p14fix/final --begin-run full-final2.xml --command <上表完整命令> --required-node tests/test_focused_v24_receipt_inputs.py --required-node tests/test_focused_v24_recovery.py --required-node tests/test_focused_v24_delivery.py --input inputs/spy_chart_2010_2025.json --input .v24p14/real-source.json --input pyproject.toml`；结束捕获实际pytest exit，再`--end-run full-final2.xml --exit-code 1`。两个最终浏览器报告也各用独立begin/end；v24显式required_node为完整节点，legacy为两个测试文件。最后归集命令`python scripts/collect_v24_receipt.py --evidence-root .p14fix/final --browser-name browser-v24-corrected`，只读审计`.p14fix/final_audit.py`写`.p14fix/final/review_receipt.json`，记录最终Git上下文、各报告绑定与真实两入口收据。源测试SHA与后续文档SHA分列，未推送。

Ruff本轮准确集合：`$checkFiles = @(Get-ChildItem src/finance_forecast_agent/focused*.py, tests/test_focused*.py, tests/browser/*.py, apps/workspace_ui*.py, tests/test_workspace_ui*.py | ForEach-Object FullName) + @('src/finance_forecast_agent/research_mission.py','src/finance_forecast_agent/task_queue.py','src/finance_forecast_agent/experiment_memory.py','src/finance_forecast_agent/replay_llm.py','src/finance_forecast_agent/llm_adapters.py','scripts/collect_v24_receipt.py','scripts/verify_v24_trial_admission.py','scripts/run_v24_engineering_validation.py')`，随后`python -m ruff check $checkFiles`。其他命令为`python -m compileall -q src apps scripts tests`、`node --check apps/workspace_frontend/forms.js`、`node --check apps/workspace_frontend/views.js`、`git diff --check`，均exit0。

全仓两失败分别为`test_focused_r4_trust::test_model_bundle_tamper_rejected_before_load[symlink]`（WinError1314，创建链接失败、未进入加载；BLOCKED_ENV）和`test_p1_real_validation_artifacts::test_dlinear_strict_live_card_replays_without_an_api_call`（原2c05bfd22af27435.json缺失；BLOCKED_ASSET），与基线相同。6跳过包括4个opt-in browser（已独立重跑4项通过）、POSIX进程组探针、Windows package symlink权限。没有观察到本轮新增产品失败；首轮browser启动配置错误的2失败单列保留。原输入5fb282、47负确认、A/L与全部原验收JSON顶层值保持，不用新数据替代旧验收。

P2输入证据收口PASS、P3文档状态同步PASS；全仓仍PARTIAL。G0—G5限定技术准备具备，G6本人预演NOT_RUN，目标用户邀请NO-GO；可按原用户指南本人预演。允许模式仍deterministic。Live语义/策略价值、真实用户、独立金融效果、远端CI、macOS/GPU大型native及后续版本NOT_RUN。没有恢复资产/改变系统权限来求绿。本轮到此停止，Git最终HEAD/tree及本地提交见review_receipt。

最终文档检查：`python -m pytest -q tests/test_focused_b0_plan.py tests/test_focused_r0_status.py --basetemp=.tprfixdocsfinal --junitxml=.p14fix/docs-final.xml --tb=short`，4 passed/7.25s/actual exit0。`git diff --check`exit0，原验收JSON所有顶层值与2fcdd23逐项相同，只新增本复审入口；`git diff 2fcdd23 -- src apps`为空。后续仅提交本轮文档和只读归集，不重新标记旧报告或执行新研究。
