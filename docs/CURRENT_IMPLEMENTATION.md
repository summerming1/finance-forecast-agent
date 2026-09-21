# 当前版本功能与技术实现说明

## 唯一当前状态来源：V2.2-R 能力与验收加固

正式分支：`feat/mission-research-v2`。实施起点：`6e4f194453f77037929052a0a978cc76bc2017b7`。

原 PR-1～PR-6 已有模块实现；此前“全部验收完成”的表述过度。验收缺口现在按 R0→R6 修复，不重写项目，也不自动开始 V3。

| 能力 | 有实现 | 原工程测试 | 真实运行 | 用户/科学验收 | 尚未关闭的合同 |
|---|---|---|---|---|---|
| 预测/Manifest/确定性反馈 | 是 | focused 通过 | 冻结历史 SPY | 非独立金融证据 | 身份已加固；恢复绑定 R2 |
| Mission/Workspace | 是 | AppTest 通过 | Codex 报告浏览器可运行 | 完整持久流程未验收 | R6 |
| Live/Replay | 是 | 录制单测通过 | Codex 报告百炼两轮与无凭证回放 | 不是科研质量证明 | R1 已加固；本轮真实 provider 待测 |
| 动作与 Memory | 原型 | 基础测试通过 | 有限规则策略 | 未证明研究增益 | R3 |
| Queue/恢复 | R2 事务路径 | 原子提交/代次/预算/缓存通过 | Linux 完整 Campaign kill/resume 已测 | 单机工程验收 | UI 集成与其他平台 R6 |
| Confirmation | 原型，默认禁用真实标签 | 模拟保护测试 | 无可信未见金融数据 | 未完成 | R4 |
| ModelBundle | 显式 refit/加载 | 无 label/新进程通过 | 历史数据推理 | 不是样本外效果 | 包外信任 R4 |
| Benchmark | 旧代理策略脚本 | 流程测试通过 | 旧结果保留 | 不具备 Agent 比较资格 | R5 |
| BYO | 内置模型配置/受控表格 | 两模拟客户 | 无真实客户 | 未完成 | 完整特征/时间与用户路径 R6 |

## R 批次执行状态

- R0：统一状态、默认关闭原型独立确认标签、标记旧对照结果；本批测试记录见版本日志。
- R1：统一内容/目标/配置身份，可见证据共享投影，v2 不可变 LLM 录制与哈希校验；本地 87 项累计回归及真实 SPY smoke 通过。
- R2：既有 Queue/Controller 使用事务状态，冻结计划、缓存和预算可恢复；本地 focused 104 项加共享队列 4 项通过，真实 SPY smoke 通过。
- R3～R6：待实施。每批先测试，再提交、核验远端，再开始下一批。

## 当前边界

仅 SPY、日频、下一 XNYS 交易日调整收盘收益回归、MAE、forecast_only。单机可信操作者；租户过滤不等于 OS 级隔离。不执行任意用户代码、模型反序列化上传、自动交易或新资产任务。

## 已有证据与未测

基线本地 Linux/Python 3.13.5：66 passed（45.96s）；原远端 3.11/3.13 CI 也成功。Windows 65 passed/1 skipped、百炼与浏览器结果来自 Codex 报告，不是本轮重跑。真正未暴露确认、真实用户、前瞻和 macOS 仍缺证据。

历史科学记录保留在 `HISTORICAL_PLATFORM_STATUS.md` 和原版本文档中；不作为本轮测试通过的证明。具体 R 验收映射见 `validation/v22r_acceptance.json`；批准方案见 `V2_MISSION_RESEARCH.md`。

## R1 使用与兼容说明

新录制位于 `<fixture_dir>/<schema>/records/`，每次调用有独立 call_id；相同 prompt 的多个调用不会覆盖，回放须明确选择。CLI 的 `--replay-call-map path.json` 接受 prompt hash → call_id 映射。未指定且存在多份记录时拒绝歧义，不选“最新一条”。

新记录校验完整 response/record SHA256，provider metadata 与核心字段隔离；录制不等于通过研究校验。旧 v1 fixture 可按显式 legacy 兼容读取，已有 response_hash 会校验，缺完整性信息不会被升级成 v2。

数据原始字节哈希保留；规范化 float64 观测、目标集合、目标内容与配置/执行身份分开。CSV/Parquet 或来源显示名改变不创造新目标。旧数据指纹不会自动迁移为可信新身份，旧记录仍可查看。R2 现在将这些身份绑定到实际执行、缓存和恢复合同。

## R2 持久执行与兼容边界

`LocalTaskQueue` 公共接口保留，SQLite 是任务/attempt/预算/计划的权威存储；JSON/JSONL 是只读导出视图，修改导出不能复活取消的任务。focused 提交让 Queue 与 Controller 共享同一事务库。

新 Campaign 每个基线/候选先预留预算，再运行；失败或中断的预留不免费退回。`fit_calls` 是保守占用预算，`resource_usage` 另列观察到的 fit 开始、完成和不确定消耗。恢复读取冻结计划与 Memory 快照；已接受预测/Manifest/Feedback 校验哈希后复用，不重训。不同数据、切分、预算、代码或环境不能沿用同一 campaign_id。

旧 worker 的 generation 不能提交新 attempt 的结果；取消先持久化再终止经过 PID+创建时间核对的进程树。存活检测不发送信号。真实 queued Campaign 在候选 A 完成、B 一折训练完成时强制终止后由新进程恢复：A/基线/计划哈希保持，重试消耗计费，最终研究包可导出。

旧 R2 之前 Campaign 可查看，但无足够 attempt 事实时不伪造恢复。代码更新前应完成或取消运行中的 Campaign；跨执行合同的继续研究应创建新 Campaign。当前网页仍在 R6 接入队列前，不据此宣称整条网页异步流程已经完成。
