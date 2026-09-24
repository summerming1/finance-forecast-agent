# 当前版本功能与技术实现说明

## 唯一当前状态（V2.2-R / B2 双入口与交付身份，2026-09-24）

验收缺口分轴保留；后续批次的计划不得冒充实际完成。

正式分支：`feat/mission-research-v2`。本轮基线：`a3c6ec69c9bd14d18b1cdb493795669a9452c800`。
批准方向见 ADR_MISSION_PRODUCT_004.md，B0→B5 范围见 PROJECT_ROADMAP.md。计划不是已实现能力。

| 能力轴 | 当前证据 | 开放边界 |
|---|---|---|
| 基础执行与逐行评价 | 既有真实 SPY、Manifest、复算和受控模型训练 | forecast_only，不是交易性能 |
| Live/Replay | 既有真实两轮百炼与严格断网一致 | B1 本地HTTP故障/离线链通过；新真实百炼/长期稳定性未验证 |
| 恢复/审核/动作 | 既有 Windows 全 Campaign 恢复、approve/reject/stop | 受影响修改必须回归，不重称从未测试 |
| 交付/受控 BYO | 既有 CSV/Parquet 审核数值特征、网页和模型交付 | 本地路径不是上传服务；B2 双入口/交付绑定已实现，真实用户未验证 |
| 金融确认 | 一次47目标真实固定留出负确认，原收据保留 | 用户声明+本地审计，非前瞻；不得重挑该窗口 |
| 研究价值 | 实际策略已接共用引擎，原矩阵完整尝试 | 旧 R5 FAIL 保留，可靠性/公平比较仍待完成 |
| 文献 | 有证据投影和引用接口，原 MethodCard/审核资产存在 | B3 版本绑定/实际使用链/贡献对照待实现 |
| 真人使用 | 工程模拟参与者 | BLOCKED_NO_REAL_USER |

## B 批次状态

| 批次 | 状态 |
|---|---|
| B0 | 已发布 81012ee；文档与批准合同同步，原240项回归和文档门禁收据保留 |
| B1 | 已实现分类错误、硬调用时限、HTTP/时间账本、等待提供者与同决策恢复；定向14项、相关累计254项通过；真实服务/Windows补测单列 |
| B2 | 已实现双入口、起点/固定对照分离、固定模型特征研究、同候选refit/下载；本地13项定向/267项相关累计通过；发布须同源码浏览器/双Python门禁；外部用户未验证 |
| B3 | planned |
| B4 | planned |
| B5 | planned |

## 原能力、证据与兼容

原 R0–R6 报告：[V22R_R0_R6_REPORT_20260923.md](validation/V22R_R0_R6_REPORT_20260923.md)。原长程矩阵和补测：[V22R_SUPPLEMENT_20260923.md](validation/V22R_SUPPLEMENT_20260923.md)。历史变更见 V2_MISSION_RESEARCH.md；数值结果/失败不能因新版本重写。

单机可信操作者，沿用 RuntimeDB/LocalTaskQueue/Controller/Evaluator/Memory/MethodCard。JSON 是投影而非第二套状态。相关项目必须复用原受控数据库；空库不代表数据未曝光。升级前完成或取消旧运行，跨代码/数据/环境/调用政策的合同不强行恢复。

现有 CLI：`scripts/run_focused_spy_campaign.py`；现有网页：`apps/streamlit_app.py` 下 Research Mission。当前尚未因方案更新自动成为双入口文献闭环。

ModelBundle 通过平台显式 refit、包外可信登记后加载；复制包不自动迁移信任。独立确认只从固定授权加载登记数据，消费后不可重试挑分数。新研究不能继承确认指标作开发反馈。

## 当前边界

SPY、日频、下一 XNYS session 调整收盘收益回归、MAE、forecast_only。一个审核数值特征和内置模型配置，不执行任意 Python/notebook/pickle/Docker。不扩大任务、模型结构或自动交易，不启动 V3。

Windows symlink 权限仍 BLOCKED_ENV；macOS/GPU 按用户范围不测；原论文小时级训练不因本轮客户端改动重跑。旧资产/PDF 环境失败与后来补测均保留，focused 通过不等于全仓科学通过。

## B1 当前调用边界

客户端在单一 killable HTTP 子进程中执行非流式 JSON 请求；连接/读取空闲和逻辑调用总deadline分别冻结。额度/权限等永久错误不盲重试；429/暂时服务错误有界退避；不自动切换模型或付费。使用既有 RuntimeDB 记录每次 HTTP 请求，崩溃未观测区间保守保留预留；费用未知为 null。

`waiting_provider` 不代表科学无改善；同合同显式恢复使用冻结提示词和已接受实验。完整已录制响应在冻结计划前中断，可直接读取原始不可变记录，无新请求。新代码/时限合同不得强行恢复旧运行。

已实现 Campaign HTTP 请求数和累计提供者活动秒数上限；模型训练仍以 fit 上限限制，不宣称硬保证整个 Campaign 的墙钟时限或精确人民币费用。预检不查询账户余额、不产生网络请求；显式 probe 仍属于一次可收费调用。SSE/供应商结构化输出和新真实Live验收未在本批宣称完成。

## B2 使用与兼容

默认 `entry_mode=goal` 不要求模型/论文，只允许选择受支持模板，必须有合法数据。`provided_start` 接受内置模型配置；旧字段 `starting_baseline` 作为输入兼容名，现在是独立用户起点，不替换固定三模型与朴素对照。若执行指纹相同复用固定对照，不同则额外预检并计入 folds 次训练。旧运行合同不强制迁移。

`change_scope=features_only` 在编译和执行前都锁定实际起点的模型、有效参数、seed与匹配父模型，仅允许审核特征组变化；普通探索仍走原能力白名单。结果分别保存 incumbent、fixed controls和research candidates，无改善不扩大为无信号。

网页用模板、起点参数与数据合同表单；高级JSON仍是显式选择，不双写权威。当前候选是详情、显式refit、下载的唯一来源。refit和candidate关系存在既有RuntimeDB，刷新可读；下载验证原包外注册与相同字节，不反序列化。交付refit单列1次训练，不冒充研究预算中的一次候选。私有数据、真实Live与真人试用未由工程测试证明。

B2 草稿合同使用稳定控件标识；切换输入路径不能覆盖已编辑的来源、模拟标记或特征。表单/高级JSON要求明确来源与provenance，非法对象阻断，不通过默认值静默运行。
