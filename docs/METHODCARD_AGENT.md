# P0.5 MethodCardAgent 设计与使用说明

## 目标

P0 已经具备可信研究内核：DatasetCard、PaperSpecCard、ComparabilityReport、ResearchContract、ExecutionManifest、时间序列评估、成本回测和 ReproductionAudit。P0.5 的目标是在不破坏这些确定性服务的前提下，补上真正的论文读取入口：

```text
PDF / TXT / MD
  -> PaperTextLoader
  -> MethodCardAgent
  -> MethodCard JSON
  -> PaperSpecCard
  -> P0 Harness
```

## 为什么不是直接让 LLM 控制后续流程

LLM 只负责阅读论文、抽取 MethodCard、给出 evidence spans 和 unknowns。它不负责：

- 数据切分
- 指标计算
- 成本模型
- strict reproduction 判定
- 训练执行
- broker/live action

这些仍由确定性代码完成。

## 核心模块

```text
src/finance_forecast_agent/method_cards.py
```

包含：

- `PaperTextLoader`：读取 `.txt` / `.md` / `.pdf`。PDF 需要安装 `pypdf`。
- `MethodCardAgent`：通过 ReplayLLM 或未来真实 LLM 生成 MethodCard。
- `MethodCard`：论文方法卡结构。
- `method_card_to_paper_spec`：把 MethodCard 转成 P0 Harness 可用的 PaperSpecCard。
- `rule_based_method_card`：开发调试用 fallback，输出必须 `approval_required=true`。

## 固定 LLM / 无 key 测试

无 key 环境下，使用 ReplayLLM fixture：

```bash
PYTHONPATH=src python scripts/generate_methodcard_fixtures.py
```

它会生成：

```text
projects/finance_agent/papers/text/<paper_id>.txt
projects/finance_agent/method_cards/<paper_id>.json
projects/finance_agent/method_cards/method_card_catalog.json
projects/finance_agent/llm_fixtures/method_card/<prompt_hash>.json
```

然后可运行：

```bash
PYTHONPATH=src python scripts/extract_method_cards.py \
  --papers-dir projects/finance_agent/papers/text \
  --out-dir projects/finance_agent/method_cards \
  --write-paper-specs
```

## 真实 LLM 接入点

未来接入真实 LLM 时，不需要改后续 P0 Harness，只需要实现一个新的 LLM adapter，使它提供与 ReplayLLM 相同的：

```python
complete_json(prompt_payload: dict, schema_name: str) -> dict
```

真实 LLM 的输出仍必须落地为 MethodCard JSON 和 fixture，提交到 repo 后才能作为可复现测试输入。

## MethodCard 字段

MethodCard 至少包含：

- method_id
- paper_id
- title
- venue_or_source
- paper_url
- task_type
- target_asset
- asset_universe
- frequency
- horizon
- label_definition
- data_requirements
- feature_groups
- model_families
- training_protocol
- evaluation_protocol
- metrics
- cost_assumptions
- reported_results
- strict_requirements
- unknowns
- evidence_spans
- extraction_metadata
- approval_required

## 进入 P0 Harness 的条件

MethodCard 可以被转为 PaperSpecCard，但 strict reproduction 仍由 ComparabilityEngine 决定。即使 MethodCard 抽取成功，只要 DatasetCard 不满足论文原始数据、频率、资产池、标签、评估协议等条件，仍然只能是 exploratory。

## 下一步

P1 应该补：

1. 真实 PDF 下载与缓存。
2. 摘要/方法/实验/附录 section splitter。
3. 真实 LLM adapter。
4. MethodCard human approval UI。
5. MethodCard 版本管理与差异审查。
