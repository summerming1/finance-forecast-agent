# V2.4 确定性诊断研究：唯一实施合同与批次日志

日期2026-10-09；用户已批准D24-0—D24-5工程及D24-6准备。基线95760e264eddb4388a44df6d35442b6ce8d90928，tree 8d081ef18dd7fde0b3e45f3a593e929e3adb530d。实际结果以本文件日志及收据为准，不把计划写成通过。

来源（只作provenance，不是并行合同）：实施提示词SHA256 b1194dac113195ef66715eaf2792dfea58149c5efc672f16d0bf1933f0f38d1a；基稿4c4877486bcdceaed043892a417ec5beeb82bda6798a02457e7e6a87e98a58a3；最新复审1d993d98c2bbf0b9462d087abf7b82fe99ebcbd71ffa662048dd1c19f17fe98a。R1—R4/P1—P4已合并如下。旧PROPOSED不覆盖本次明确实施批准。

## 1 合同及授权

### 2026-10-10 批准的复审收口

以3097ece为本轮实际基线，修复复现的输入/恢复/上下文/收据缺口，不扩研究能力。新增planning_projection_v2及diagnostic_price_advice_v2显式合同；v1纯投影读取保留，旧fixture/hash不修改，活动任务按原源码版本处理而非强行迁移。64000字符上限不提高；训练/组范围与共同来源确定性去重，完整审计继续原RuntimeDB和制品。固定baseline_ridge为相对诊断参照，在Campaign前冻结，不按组内成绩重新挑控制；正loss_delta表示候选更差，与观察的control-minus-child改善符号区分。样本门槛仍是描述性而非显著性。

RCP-04/05允许有界diagnose需求设计并持久保存，不执行窗口或组合；缓存消融完成的是新观察，不是新模型或免费fit，仍消耗原槽，仅允许剩余的第二次规划。ON投影读取所有已完成提案观察，OFF不接收新增诊断源或观察。异常结构进入原proposal_invalid终态，不自动修复/补请求。

pilot在输入预检前登记四臂分母，构造/执行/导出/校验全部纳入失败收据；只有执行完成且包审计通过才PASS。新测试收据需运行前start manifest及结束后的实际exit/hash；缺绑定、零测试、全跳过、计数不一致或覆盖不足均不能PASS，策略行为不继承全仓PASS。历史收据只作历史，禁止覆盖。

执行记录待本轮定向、回归、worker/browser及最终全仓完成后补充。不调用付费Provider，不外发、不读取确认标签、不推送。

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
