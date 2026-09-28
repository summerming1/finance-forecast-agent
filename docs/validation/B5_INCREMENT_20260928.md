# B5 增量修复与真实验证（2026-09-28）

## 范围与版本

本报告补充而不覆盖原 R0–R6/B0–B5 验收及失败记录。不启动 V3，不新增金融确认。
原阶段完整记录：[R0–R6](V22R_R0_R6_REPORT_20260923.md)、[补充矩阵](V22R_SUPPLEMENT_20260923.md)、[9月27日 B0–B5](B05_SUPPLEMENT_20260927.md)。本轮没有重做旧48条全部外部流程；不可将累计单测通过等同于重跑原平台/研究验收。
正式目标分支 `feat/mission-research-v2`；起始远端 `2883b15f4ae389ac8dba14678e1c3d3aa9a84c9b`。
Windows 11 / Python 3.13.3 / i5-12500 / UHD770。macOS、GPU 按用户要求不测。
原工作区及未跟踪资产保留；修改位于已有隔离工作树。

修复提交：

- `6f3d8ed`：必填 statement 提示、候选来源/开发门槛/部分终态分离、录制写入预检及失败后同决策禁止自动重发。
- `1d26760`：真实 Manifest 可比性检查、只读候选比较、快速试跑预算、显式续接费用预览、实际响应模型别名记录。
- `3829647`：明确现有文献引用双字段一一对应要求；校验器不变，不替模型补引用。

每次修复保留 red tests；没有删除失败测试或放宽研究门禁。一个 Controller/Queue/Evaluator/Memory/RuntimeDB 不变。

## 本地工程结果

| 收据 | 结果 | pytest 时间 | exit |
|---|---|---:|---:|
| literature_binding_target | 73 passed | 22.91s | 0 |
| core_increment_literature_final | 393 passed / 1 failed / 2 skipped | 374.44s | 1 |
| browser_increment_final_r2 | 真实 Chromium 1 passed | 79.06s | 0 |
| full_increment_nvme | 532 passed / 10 failed / 3 skipped | 403.93s | 1 |
| lint_increment_final | 所有本轮相关文件 Ruff 通过 | 收据见 JSON | 0 |
| compile_increment_final | src/apps/tests compileall 通过 | 收据见 JSON | 0 |

累计测试覆盖 focused、queue、memory 及相关 MethodCard/UI 回归。最终引用修复源码与 `3829647` 一致；执行时尚未提交，原收据 HEAD 为 `1d26760`，不能据此冒称当时 commit 已包含修复。全仓运行在引用修复之前；最终受影响累计回归另列。
浏览器验证真实训练候选切换、候选比较及计数不变、刷新/新 context、下载、续接预览和显式新 Campaign。参与者/浏览器输入为 simulation_only，不是用户试用。

10 项全仓失败逐项异常与恢复方式见配套 JSON：1 项 WinError1314（符号链接创建权限，BLOCKED_ENV），3 项缺 multi_benchmark_suite.json，3 项缺原生 patch/source，1 项缺 MTGNN MethodCard，2 项缺 DLinear 原始 PDF（均 BLOCKED_ASSET）。不是本轮引入的产品回归；不删除或统一 skip。恢复必须使用原授权资产/固定源码。此前原资产环境复验是历史证据，不冒充本次全仓通过。

## 真实 LLM 与研究对照

实际 provider 为 Bailian，requested/response model 均 kimi-k3，alias_unresolved；未遇到额度耗尽，未轮换模型。金额未知为 null，未测人工分钟为 null。无 deterministic fallback。
输入 SHA256 `0bb0896126adb0393f34ae09b90487cb501b2c6aa681a66d2a8f02348669036b`，4002 行，2010-02-03 至 2025-12-30，已暴露 development 数据。
复用原 RuntimeDB，不用空库重置曝光/信任。新目录保存独立 cohort；原失败不覆盖。

G2A (`inc_g2a_kimi`) 源 `1d26760`：同一数据/目标行/固定基线/候选目录/Controller/Evaluator、search seed42、estimator seed42、memory cold、每臂8候选/44 fits。TPE 为真实 Optuna，4 startup + 4 model-based decisions。

| 臂 | 最佳 MAE | 相对同窗最佳基线改善 | 实际 LLM 次数 | 墙钟秒 |
|---|---:|---:|---:|---:|
| Random | 0.005015140774319799 | 0.370084% | 0 | 60.13 |
| TPE | 0.0050228733284286235 | 0.216471% | 0 | 68.28 |
| One-shot | 0.0050228733284286235 | 0.216471% | 1 | 220.12 |
| Adaptive | 0.005014199810696815 | 0.388777% | 8 | 500.93 |
| Adaptive Batch | 0.005014199810696815 | 0.388777% | 4 | 398.16 |

One-shot 一次生成冻结计划；Adaptive 逐步读取实际反馈；Batch 每批读取反馈后提出两个候选。13 次真实请求的 wire/prompt hash、既有 StructuredFeedback、实际剩余预算检查通过。所有臂8 unique candidates、44 charged fits；没有因不同 execution identity 把相同配置当新候选。
本次 Batch 与 Adaptive 最佳误差相同且少4次调用；有限目录、单窗口/单种子不证明普遍优越，不是完整45臂矩阵。不能把开发筛选收益写成金融泛化。

普通2轮 Live 和严格离线 Replay 完成，各20 fits。Batch Replay 完成44 fits，14个预测文件及配置/假设实质字段/反馈一致，并独立复算指标；清空凭证且阻断网络/Provider，0 provider 请求。Replay 重训单独计费为本地 fits，不是免费继承。
Replay 审计脚本最初路径及 baseline lookup 出错，修正后只读复核已完成结果；保留原失败收据，没有为了绿灯再跑收费请求。

## 文献 L0/L1

首次 `inc_g2b_kimi` L1 在12 baseline fits、1真实请求后因论文 ID 缺 evidence_refs 被拒绝，0候选 fits；L0 未执行。不是额度耗尽。用户批准最小提示修复后独立重跑 `inc_g2b_binding_kimi`，预算每臂4候选、9逻辑调用、48 HTTP预留、3600 provider秒。新 L1/L0 均 completed，退出0，总563.52s；各4候选/28 fits/2真实调用。L1墙钟313.50s，L0为246.14s，最佳MAE均为0.0050336970303899884，未观察到文献额外精度收益，不追加寻找赢家。

L1严格断网 Replay PASS（45.86s，exit0），28独立本地 fits、10份逐行预测/指标一致、0网络尝试；假设实质字段/配置/反馈一致。4次 L0/L1 实际 wire/prompt hash、上一轮反馈和剩余预算审计通过。记录量、命令、exit、时间、source/input哈希、用量与全仓10项异常见 [JSON收据](B5_INCREMENT_20260928.json)。收集到的真实记录共246883 tokens（含保留的失败响应），不等于人民币费用；费用仍null。

新 L1 已完成4候选/28 fits/2真实调用（313.50s），最佳 MAE 0.0050336970303899884。第二轮实际读取第一轮失败反馈，识别首轮同时改变 alpha 与 volatility 的混杂，提出删除 volatility 的真实 parent ablation；另一候选将 Cawley 观点仅作选择偏差限制，并明确不是 SPY 证据。这个链路说明文献与反馈确实进入实验，不证明引用导致收益改善。
解释质量仍需人工判断：新 L0 第一轮 statement 一面称加强正则，一面给出 alpha=0.5（从1.0下降，实际是减弱）并自我纠正；结构校验不保证自然语言完全一致。实际参数由确定性编译器执行，不能将这段叙述升级为科学结论。此次仅记录，不为追求表述绿灯追加付费重试。

## 交付与其边界

`delivery_increment` PASS：14份 PredictionArtifact、56项fold指标独立复算，ResearchPackage49成员SHA校验；显式额外1次refit登记原trusted registry，新Python进程8行无标签预测一致。包hash `80f0ef6d6a440762d320aae603d1d693fc7d5f3e415e01bbb6d01b31e51981e6`。
输入是训练尾部去标签，只验证接口一致性，不是样本外表现。跨机信任迁移未实现，下载成功不等于信任迁移。

旧冻结验收所需原始 `5fb282...` 输入及配套metadata缺失；本次 `0bb...` 不能替代。新开发数据 smoke 完成3轮/20 fits/no_improvement，但原冻结 CI 仍需恢复原字节。

## 尚未闭合

- 真人产品试用/自然复访：BLOCKED_NO_REAL_USER；已有清单，用户需要实际操作反馈，助手模拟不能通过。
- 原冻结远端数据资产：BLOCKED_ASSET；不能重新下载新行情冒充旧hash。
- Windows symlink：BLOCKED_ENV；需有权限环境验证，Linux CI 单列。
- 完整多窗口多seed及稳健研究/文献增量：本轮有限对照不足，不扩大为一般优势。
- macOS/GPU 未测；小时级 native training NOT_RUN_COST。
- 原47目标固定留出负确认保留；本轮未新增独立金融证据，不反复选择窗口。

总体工程仍 PARTIAL；真实用户 BLOCKED；V3 NOT_READY。Linux/Chromium 同最终发布 SHA 的 CI 需在推送后核对，不以其他提交的绿色替代。

阶段对照：R0 文档一致性更新；R1 新Live/Replay与写入失败负例；R2 queue/recovery受影响累计回归（原完整crash证据保留，本轮不声称重新杀进程）；R3 动作/Memory累计及真实反馈链（cold/warm本轮未新增）；R4 可信包新进程通过、原负确认不变、Windows symlink仍阻断；R5 新五臂及L0/L1有限真实对照；R6 Chromium切换/恢复/预览/交付通过、真人未完成。各阶段历史事实与本轮命令分别查阅，不概括成 R0–R6 全部 PASS。
