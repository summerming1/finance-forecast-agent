# P0.9 Research Workbench UX Refresh

> 历史版本说明：P1.2 已增加可编辑 ReproductionPlan，本文中“尚不能在前端写入预处理和超参数”的限制已不再适用。当前操作以 `FRONTEND_USER_GUIDE.md` 为准。

## 背景

旧前端按内部数据结构拆成七个页面，同一审核控件同时出现在 MethodCard Review 和 Flow Trace，Raw JSON 又直接占据主视图。它适合开发排错，但没有把用户真正需要做的决策串成流程。

本次刷新将前端改成五步研究工作台：

```text
文献库 -> 方法审核 -> 复现配置 -> 运行实验 -> 结果审计
```

## 关键变化

1. 一次围绕一篇论文工作，避免用户误触全量提取或全量运行。
2. 已有卡复用和重新提取成为两个明确动作。
3. MethodCard 先以中文业务表格展示，Raw JSON 默认折叠。
4. EvidenceSpan 保留原文；旧卡缺少 section 时显示“未标注”，不猜测章节。
5. 审核操作只有一处，状态继续持久化到 review state。
6. 复现配置页并排展示论文要求与本地实际配置。
7. strict reproduction 与 exploratory reproduction 在运行前后都明确区分。
8. 结果页先展示指标、候选与阻塞项，治理资产和完整 JSON 收入技术细节。
9. 自定义主题改为中性深色与青绿色操作色，按钮保持深色背景和白色文字。

## `unknown` EvidenceSpan 处理

`arxiv_1706_10059` 的旧 MethodCard 含有证据摘录，但 LLM 输出没有章节字段。标准化层只能使用 `section="unknown"`，不能从短摘录可靠推断论文原始章节。

质量门禁现在会：

- 统计未标注章节的证据数量；
- 在质量分中加入最高 0.15 的可追踪性扣分；
- 全部证据均缺少章节时要求人工审核；
- 不修改或伪造证据原文。

未来重新提取协议应增加 page/section/paragraph locator，并对 PDF 文本块保留页码元数据；这需要升级 MethodCard schema 和 Replay fixture 版本，不能仅靠前端显示修复。

## 复现等级规则

完整复现至少需要：

- 原始或经确认等价的数据集；
- 一致的资产池、频率、预测周期和标签定义；
- 足够详细的特征、预处理、模型、超参数和训练协议；
- 一致的数据切分、回测、成本和指标定义；
- 可定位的论文证据；
- 实际 ExecutionManifest 与上述要求一致。

任一关键条件不满足时应降级为探索性复现或 paper-inspired local study，并显示原因。

## 尚未完成的产品能力

当前 MethodCard schema 没有独立的预处理协议、超参数空间和人工 override 结构。工作台会把这些缺口显示为“需要人工决定”，但尚不能让用户在前端选择后直接写入 ResearchContract。

建议后续新增：

1. `PreprocessingSpec`：缺失值、缩放、异常值、窗口和防泄漏约束。
2. `ModelConfigSpec`：模型 adapter、固定超参数与搜索空间。
3. `HumanOverride`：记录人工选择、原因、操作者与时间。
4. `ReproductionPlan`：冻结数据、特征、模型、切分、成本、指标和验收阈值。
5. 论文结论验收规则：把 reported results 转成可比较指标和容差，而不是仅展示文字。

## 验证

- Streamlit AppTest 覆盖五个步骤逐页渲染。
- 审核页断言只有一个保存审核动作，且不再出现两套 Approve/Reject。
- EvidenceSpan 可读视图、论文清单和复现就绪度具有独立单元测试。
- MethodCard 质量门禁覆盖全部证据章节未知的回归用例。
