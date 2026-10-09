# V2.4 确定性诊断研究：唯一实施合同与批次日志

日期2026-10-09；用户已批准D24-0—D24-5工程及D24-6准备。基线95760e264eddb4388a44df6d35442b6ce8d90928，tree 8d081ef18dd7fde0b3e45f3a593e929e3adb530d。实际结果以本文件日志及收据为准，不把计划写成通过。

来源（只作provenance，不是并行合同）：实施提示词SHA256 b1194dac113195ef66715eaf2792dfea58149c5efc672f16d0bf1933f0f38d1a；基稿4c4877486bcdceaed043892a417ec5beeb82bda6798a02457e7e6a87e98a58a3；最新复审1d993d98c2bbf0b9462d087abf7b82fe99ebcbd71ffa662048dd1c19f17fe98a。R1—R4/P1—P4已合并如下。旧PROPOSED不覆盖本次明确实施批准。

## 1 合同及授权

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
| T31 | recovery推荐篡改拒绝；外层标签没有授权也没有读入；模拟隔离不称生产安全证明 |
| T32 | 原test_focused_r4_trust曝光更名/等价时间负例；新DSL确认仍前置拒绝 |
| T33 | tests/browser/test_agent_workspace.py[v24]，真实worker/Chromium；复用旧两模式浏览器 |
| T34 | 原feature_contract golden identity、原fixture边界；delivery新协议local HTTP→无key严格Replay |
| T35 | pilot::test_d24_6_preflight_no_dispatch_no_credentials_read；receipt分开simulation/Live/owner/独立用户；真实条款仍NOT_RUN |
| T36 | delivery研究包逐成员SHA/逐行原evaluator复算；原feature_bundle fresh-process/trusted加载；页面模型与当前候选绑定 |

R1=问题方向与选择分开（T09—13/16—17/29）；R2=OFF领域假设同AST合法及冷Memory（T15/28）；R3=raw/X/prediction来源与不可用（T01—08/14/19）；R4=三层冻结/选择动作（T12/26/29—31/36）。P1=合法AST非固定菜单；P2=q75/30/10/2描述性门槛不作显著性；P3=本地模拟隔离及present_day_research边界；P4=原2规划4槽/有限1对只读组合、后续窗口/权重仅需求记录。

D24-6操作：先运行`python scripts/run_v24_engineering_validation.py --output-root <新目录>`只预检。加`--run-engineering`才运行隔离模拟4臂；不读取key。提供已有真实开发输入还需`--raw-spy-json <path> --allow-development-compute`明确许可与开发用途，不能冒称独立确认。默认不覆盖已有目录。真实Live/所有者/独立用户、政策价值和金融轴需后续分别授权/实际操作，不能用工程收据代替。
