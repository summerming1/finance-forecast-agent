# 聚焦版验收与测试方案

> 状态：APPROVED / ADR-FOCUS-001 已于 2026-09-18 经用户批准。本文作为 focused 路线的设计与开发约束；具体已实现范围以 CURRENT_IMPLEMENTATION.md 与版本说明为准。

## 1. 三种验收不能相互替代

- 工程验收：实际流程、权限、实施一致性、恢复和 UI 正确。
- 科研验收：假设对应实验；未证明提升时结论正确；统计与确认边界成立。
- 产品验收：用户能独立选择任务、运行、看结果和继续使用。

pytest 通过或进程返回 0 不自动满足后两项。历史文档中的测试数不是本次运行结果；本方案制定期间没有重新训练或运行项目测试。

## 2. F0 核心负例

| ID | 场景 | 验收 |
|---|---|---|
| T01 | 真实数据加载失败 | 明确失败；不能合成后写进真实缓存 |
| T02 | 对未来数据做扰动 | cutoff 以前的已计算特征不变；禁止 bfill |
| T03 | 未来五日等重叠标签 | 用 label_start/end 做 purge；1 日 gap 不能替代通用证明 |
| T04 | 混乱日期、重复行、缺行 | 显式验证；统一排除规则冻结，不能按候选分数选行 |
| T05 | 同一标签、不同股票日历 | 不能把下一自然日当下一交易日；entity/horizon 必须对齐 |
| T06 | lookback=5 与 lookback=20 | 比较目标行相同；按最大允许 lookback 设置共同预热 |
| T07 | 调整 Ridge alpha/RF depth | estimator 实例与 Manifest 都改变；不能仅 JSON 改了 |
| T08 | unknown model | blocked_unsupported_model；没有 Ridge/GBDT 隐式替换 |
| T09 | LSTM 多种 lag 和静态变量 | 时间维按最旧→最新，不把波动率等列当时间步 |
| T10 | 修改 final 标签 | 候选产生、开发排序与预算决策不变 |
| T11 | 初始空仓→多→空 | 按获批单边成本定义计算交易量；初次建仓计入 |
| T12 | 日频/周频/不连续 folds | 年化与持仓重置规则显式；未覆盖日历不能伪拼连续 PnL |
| T13 | 数据字节变了、路径不变 | dataset/task/execution fingerprint 必须失效 |
| T14 | 仅移动项目目录 | 内容语义 fingerprint 不变；本地绝对路径非数据身份 |

F0 若只有 forecast-only，T11–T12 仍作为继承评估器的回归；前端不默认生成可交易结论。

## 3. F1 闭环和 LLM 测试

| ID | 场景 | 验收 |
|---|---|---|
| T15 | 录制过的真实提案 Replay | 相同完整请求返回相同记录，零网络 |
| T16 | 方法卡/开发结果/工具 schema 改变 | 旧 fixture 不匹配；不能仅按 paper_id 回退 |
| T17 | 响应有不存在的模型/字段 | 保存原响应并拒绝，schema 修复遵守预算 |
| T18 | 原文提示“忽略规则/读取密钥” | 文献仅为数据，不执行其中指令，不外传密钥 |
| T19 | 第 1 轮劣于强基线 | 下一轮输入必须包含该报告；记录引用和候选变更 |
| T20 | 改动只换候选 ID/文案 | 相同实义 fingerprint，标 skipped_duplicate |
| T21 | 建议新增波动特征 | 实际 feature artifact/公式/列及模型输入一致改变 |
| T22 | 候选跑通但无增益 | execution=success，research=not_supported 或 insufficient_evidence；不得自动晋升 |
| T23 | 提案超过许可范围 | 等人工审批或拒绝；不可自动放宽任务合同 |
| T24 | 同一候选拟合中断重试 | attempts 可见；重试非新假设轮；总预算扣减 |
| T25 | 数据/模型接口不支持 | 精准 backlog；不触发另一条无界开发循环 |
| T26 | 三轮无改进/预算耗尽 | 正常终止，保留基线和原因；不继续“直到成功” |
| T27 | 冷/热 Memory 对照 | 同结果输入下 prior 是否改变候选排序可复核；终态仍符合固定评估 |
| T28 | 历史失败为机器缺依赖 | 不误判模型没有预测价值，失败类别正确 |
| T29 | 旧评估 schema/不同任务 Memory | 不进入当前强 prior；原生 strict 与本地研究隔离 |
| T30 | 已有审批后合同/card 改变 | 旧审批不可复用；继承展示明确 stale |

无 key 测试采用真实录制或明确标注的人工策展研究响应。后者验证执行接线，但不能包装成真实 API 验证。正式路径缺少记录必须报错；测试双可以模拟超时/畸形 JSON，仅属于单元测试。

## 4. 恢复、持久化与 UI

| ID | 场景 | 验收 |
|---|---|---|
| T31 | 双击提交/页面刷新 | 同 idempotency key 只创建一次实验 |
| T32 | 浏览器关闭、训练继续 | 队列任务与进度仍保留；重新打开可见 |
| T33 | worker 崩溃 | 记录 interrupted/failed；不能永远 running 或假成功 |
| T34 | 取消与完成竞态 | 终态有明确优先规则；晚到产物不自动晋升 |
| T35 | 完成候选后恢复 campaign | 不重复已完成训练；从未完成状态继续 |
| T36 | 并发 2 个候选 | max_workers 真正限制并发；共享文件不互相覆盖 |
| T37 | 损坏产物/缺失 DVC 字节 | 显示 error/missing，不静默忽略后报告“全部成功” |
| T38 | 无 run 或无 final | UI 显示未运行/未确认，不默认 done/best |
| T39 | 全失败或 blocked | 不能将伪造零指标候选选成 best；显示无有效候选 |
| T40 | 高对比主题、窗口缩放 | 输入、正文、表格、错误态可读；真实浏览器截图验收 |

至少用 Streamlit AppTest 验证结构，再用浏览器跑一个真实数据 campaign 的用户路径。只有 VM 单测时，不得宣称完成了端到端 UI 验证。

## 5. F2 科学验收

预注册主指标为 MAE，并对同目标行形成 candidate 与冻结强 baseline 的 paired loss。报告效应量、时间分块诊断和区间；预先选定时间块重采样策略，并报告预定的敏感性范围，不从多种区间算法中择优公布。

建议至少包括训练折中位数（MAE 对照）、训练折均值、零收益、冻结 Ridge/RF。不能只对最弱 baseline，不能在 final 上挑最好 baseline 再拿同一 final 声称确认。

多 seed 是训练不稳定性检查，不是增加独立市场样本。QQQ 与 SPY 的任务结果分列，不以相关资产数据简单翻倍样本量。

搜索阶段全部试验计入账本。独立确认：验证任务/模型/代码/数据范围冻结，final 工具对研究 Agent 不可见，且审批哈希有效。以前已看过的时间段，无论重命名 CSV、task ID 或切换随机种子，都不恢复盲测资格。

反复使用同测试集反馈修改算法存在适应性过拟合风险，[E05] 支持这一背景；本项目不宣称简单一次分割即可消除所有风险。历史 LLM 知识、人工先验和已查看报告也应在 evidence exposure 中披露。

结果层级：descriptive_improvement → robustness_checked → statistically_supported → confirmation_passed。没有满足后者就停留前者。

## 6. 验收材料

每批提交必须给出：固定 Git SHA、依赖环境、实际命令、开始/结束时间、退出码、日志、跳过项、数据/hash、获准/被拒文献与实验清单、测试报告和前端操作证据。

通用命令（已存在的工具，具体 test 路径以审计后仓库为准）：

```powershell
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
python -m pytest -q
python -m ruff check src tests scripts
python -m compileall -q src scripts apps tests
```

新增 campaign CLI 和聚焦测试命令由 F1 实现后才能写成可运行教程；现在不伪造已经存在的脚本。

完整历史 native 训练可能昂贵。每批仍需 schema/claim/evidence 回归；改变 native runner 才定向重跑受影响 claim，普通 UI 修改不强制重跑所有小时级训练。不能靠跳过所有旧测试掩盖回归。

## 7. 首个版本的交付门禁

F0：T01–T14 与相关旧回归、真实基线证据。
F1：T15–T40、一个真实数据三轮 campaign、浏览器交互、一个无提升正确结束、一次恢复。
F2：预注册配对分析、模型冻结与确认访问测试、第二方法卡/近域测试。

所谓“测试没问题”只指已执行测试范围内没有未解决失败，不意味着任意论文、任意数据和所有运行环境都正确。

来源索引：[CURRENT_IMPLEMENTATION.audit.md](CURRENT_IMPLEMENTATION.audit.md)。