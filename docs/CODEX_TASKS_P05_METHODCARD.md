# Codex 任务说明：P0.5 MethodCardAgent

## 背景

当前项目已经有 P0 可信研究内核。P0.5 新增了真正的论文入口：`PDF/TXT/MD -> MethodCardAgent -> MethodCard -> PaperSpecCard -> P0 Harness`。

## 当前已实现

- `src/finance_forecast_agent/method_cards.py`
- `scripts/generate_methodcard_fixtures.py`
- `scripts/extract_method_cards.py`
- `tests/test_methodcard_agent.py`
- `docs/METHODCARD_AGENT.md`

## 约束

1. LLM 不能直接跑训练、切分、指标计算或 strict 判定。
2. LLM 输出必须落地为 JSON MethodCard。
3. 无 key 测试必须使用 ReplayLLM fixture。
4. MethodCard 不确定的字段必须写进 `unknowns`，不能臆测。
5. fallback 抽取必须 `approval_required=true`。
6. MethodCard 转 PaperSpec 后，strict 仍由 ComparabilityEngine 判定。

## 推荐下一步任务

### Task 1：真实 LLM Adapter

实现：

```text
src/finance_forecast_agent/llm_adapters.py
```

接口：

```python
class LLMJsonClient:
    def complete_json(self, *, prompt_payload: dict, schema_name: str) -> dict: ...
```

要求：真实 LLM 输出后必须同时写入 ReplayLLM fixture。

### Task 2：PDF Section Splitter

实现：

```text
src/finance_forecast_agent/paper_sections.py
```

输出：

```text
abstract
introduction
data
method
experiment
appendix
unknown
```

### Task 3：前端 MethodCard 面板

展示：

- MethodCard JSON
- evidence spans
- unknowns
- approval_required
- PaperSpecCard conversion

### Task 4：严格测试

新增测试：

- PDF/text 可加载。
- fixture 缺失时报错。
- fallback 必须 approval_required。
- MethodCard -> PaperSpec 字段一致。
- MethodCard 缺关键字段不能进入 strict。

## 常用命令

```bash
PYTHONPATH=src python scripts/generate_methodcard_fixtures.py
PYTHONPATH=src python scripts/extract_method_cards.py --papers-dir projects/finance_agent/papers/text --out-dir projects/finance_agent/method_cards --write-paper-specs
PYTHONPATH=src python -m pytest tests/test_methodcard_agent.py -q
```
