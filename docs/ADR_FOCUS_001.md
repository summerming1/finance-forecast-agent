# ADR-FOCUS-001：近期聚焦 SPY 日频受控研究闭环

- status: accepted
- approved_by: user
- approved_at: 2026-09-18
- working_branch: `feat/p1-focused-us-equity-loop-v1`

## 决策

近期主线从“先完成跨类型、跨数据域的通用 strict 覆盖门禁”调整为：

1. 保留历史 P0-P1.G 的 MethodCard、严格复现、数据/来源合同、Memory、lineage 和前端资产；
2. 暂缓把 `20 篇 strict / 4 类实验 / 3 数据域` 作为下一阶段全部工作的前置条件；
3. 先在一个明确的美股指数 ETF 日频任务上完成可使用、可观察、可停止的研究闭环；
4. 第一任务固定为 `SPY`、日频、下一交易日连续收益回归，方向仅为辅助诊断；
5. 第一阶段模型空间限制为 Ridge、Random Forest、Gradient Boosting；
6. 论文 strict reproduction 与本地预测研究保持两条独立轨道，任何本地 benchmark 结果不得冒充论文 strict 结论；
7. 历史 SPY 数据已经被查看，只能作为 development/historical evaluation，不能重新命名为独立 blind final。

## 不变量

- 时间因果、真实/合成数据隔离、模型实施一致性、审批、strict 门禁不降低；
- Agent/LLM 不拥有指标计算、标签、切分和 scientific acceptance 的最终权力；
- 不支持的模型不静默降级；
- execution success 与 scientific improvement 分开；
- 没有改进是合法的 campaign 终态。

## 延后但未取消

跨市场/跨实验类型 strict 覆盖、组合 RL、截面资产定价、任意论文环境自动实现、分布式 worker、通用 Agent Runtime 改写。

## 外部框架借鉴边界

- RD-Agent：借鉴 hypothesis → implementation → execution → feedback 的研究责任划分；
- DeepSeek Harness：借鉴稳定工具接口、权限/审批、事件与可恢复执行；
- 本项目保留金融数据语义、时间因果、可比性和科学验收作为核心差异化能力。
