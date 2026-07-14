# Finance Forecast Agent 前端使用指南

## 1. 启动

```powershell
conda activate finance_fa
cd "D:\AI Agent\finance_forecast_agent"
$env:PYTHONPATH="src"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
python -m streamlit run apps/streamlit_app.py
```

打开 `http://localhost:8501`。当前本机 8501 和 8502 均有健康的 Streamlit 服务；日常只保留一个即可。

## 2. 五步流程

```text
1 文献库 -> 2 方法审核 -> 3 复现配置 -> 4 运行实验 -> 5 结果审计
```

### 第 1 步：文献库

选择本地论文。状态“已提取”表示已有 MethodCard：

- “使用已有方法卡”：不调用 LLM，直接进入审核。
- “复用已有，仅新文献调用 LLM”：已有卡不重复收费，新论文才调用。
- “Replay 回放”：使用 fixture，不联网。
- “全部重新调用 LLM”：强制使用严格 profile 实时提取，并记录 Replay fixture。
- “规则兜底测试”：只测流程，不能当高质量方法卡。

DLinear 正式卡已由当前 `.env` 的真实 LLM 严格抽取成功；PDF 同名 context 文件提供固定 commit 的官方实现和数据清单证据。其他卡仍可能需要人工审核，API 成功不代表自动 strict。

### 第 2 步：方法审核

先读“预测方法摘要”，再读 EvidenceSpan。重点确认：

- 预测对象、资产池、频率、horizon 和标签；
- 数据来源与样本日期；
- 特征和预处理；
- 模型结构与超参数；
- 时间切分、回测和评价指标；
- 论文报告值与证据是否对应。

审批只表示“接受当前方法卡内容”，不等于完整复现。旧卡 EvidenceSpan 的章节为 unknown 时，可继续用于探索，但不能通过 P1 strict 证据门禁。

### 第 3 步：复现配置

页面有三个独立状态：

- 方法卡审核：是否接受抽取内容。
- 执行就绪：条件必填字段是否都有值，并已人工确认可执行。
- Strict 就绪：全部必填值是否来自绑定的论文证据，且有可检验论文结果。

每个字段选择来源：

- “论文证据”：必须已有对应 EvidenceSpan；可支持原生 strict。
- “官方实现/数据证据”：必须有来源 URL、固定 revision 或数据 hash；可补足论文未展开的实现细节并支持原生 strict。
- “人工假设”：用你的选择补足论文缺口；只能探索性运行。
- “基准统一值”：由 BenchmarkTask 固定；只能统一基准适配。

填写后勾选“确认该计划可以进入执行”，点“保存复现计划”。仍有必填缺口时，“进入运行”保持禁用。

实验类型会决定必填项：纯预测不要求交易成本；信号回测和组合强化学习必须补齐信号、仓位、成本和回测协议。

### 第 4 步：运行实验

运行模式分为：

1. **原生复现**：尽量保持论文数据与协议，用于检验论文 claim。
2. **统一基准**：固定任务、数据、特征信息、fold 和指标，只比较 MethodAdapter。

原生复现和统一基准的结果不会混为一类，也不会共享 Memory prior。

### 第 5 步：结果审计

原生复现展示论文值、本地值、数据与协议一致性、结果容差和治理门禁。统一基准展示共享任务 fingerprint、可比性审计、方向准确率 95% 区间、训练折朴素基线、方向能力结论和历史 Memory 均值。

Raw JSON 默认折叠，只在开发排错时展开。

## 3. 测试完整原生复现

使用 `arxiv_2205.13504`：

1. 文献库选择 `arxiv_2205.13504.pdf`，使用已有方法卡。
2. 方法审核中确认 DLinear、Exchange-Rate、336 输入、96 输出、MSE/MAE 和论文值 `.081/.203`，保存为“批准”。
3. 复现配置中检查所有必填项都有“论文证据”，勾选执行确认并保存。
4. 进入运行，选择“原生复现”。
5. 点击“运行官方协议复现”。CPU 上通常几十秒内完成。
6. 结果审计应显示“完整复现通过”。本轮实测为 MSE `0.0810795`、MAE `0.2060906`。

若只想直接重跑后端：

```powershell
python scripts/run_p1_validation.py
```

## 4. 测试统一基准

推荐比较：

- `arxiv_2209_02407` -> LSTM 序列适配；
- `arxiv_2310_16855` -> Random Forest 表格适配。

操作：

1. 分别在方法审核中批准两张卡。备注应保留“只批准统一基准适配，原生字段仍有缺口”。
2. 第 4 步选择“统一基准”。
3. 勾选两篇论文方法，主指标选择 `directional_accuracy`。
4. 点击“运行统一基准”。
5. 在结果审计确认 task fingerprint 相同、两个方法都产生 128 个预测、共享 8 个 folds。

当前实测两种方法方向准确率均为 `0.484375`，朴素基线为 `0.4765625`，95% 区间约 `[0.3995, 0.5701]`，`p=0.791`，页面应显示“方向能力未显示”。LSTM 的 MAE/RMSE 略低。这一结果证明比较流程可运行，不证明策略可交易，也不证明模型在其他任务上无效。

## 5. 人工缺口如何填写

当论文没有写清某字段时：

- 先在审核备注中记录缺口。
- 在复现配置填写你采用的具体值，例如 `StandardScaler fit on train only`。
- 来源选择“人工假设”。
- 保存后可以运行，但结果应显示探索性复现。

不要为了让 Strict 变绿而手动选择“论文证据”。P1 门禁还会检查该字段是否真正绑定 EvidenceSpan，没有证据仍不会 strict。

## 6. 文件位置

```text
projects/finance_agent/method_cards_local_llm/  方法卡
projects/finance_agent/reproduction_plans/      复现计划
projects/finance_agent/data/external/           冻结数据
projects/finance_agent/reports/                 运行报告
projects/finance_agent/experiment_memory/       实验记忆
projects/finance_agent/review_state/             审核状态
projects/finance_agent/llm_fixtures/             Replay 响应
```

## 7. 常见问题

- **运行按钮不可用**：方法卡未批准，或 ReproductionPlan 未执行就绪。
- **Strict 不通过**：检查 EvidenceSpan、人工假设、数据 hash、模型协议和论文报告值。
- **统一基准可选方法少于两种**：需要至少两张已批准且有通用 MethodAdapter 的卡；DLinear 是专用原生 adapter，不出现在通用列表。
- **401 Unauthorized**：`.env` 中的 key、base URL、provider 和模型不属于同一服务；修改后必须重启 Streamlit。
- **页面训练时暂时无响应**：当前仍是同步训练，等待完成后页面会自动进入结果审计。
