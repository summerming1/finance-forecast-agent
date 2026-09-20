# Focused 分层测试操作手册

适用：V1.1 + PR-0 准备分支。不要将尚未实现的 V2 验收当作已有命令。实际核验结果见 `VERIFIED_DELIVERY_20260920.md`。

## 1. 同步代码并记录版本

先在仓库执行 `git status --short`。工作区有未提交改动时先自行保存，不执行 reset、强制切换或 force-push。

```bash
git fetch origin
git switch feat/mission-product-pr0-pr6
git pull --ff-only
git rev-parse HEAD
```

后续在仓库根目录运行。用 Python 3.13 建独立环境；3.11 可另建环境复测，不共用 site-packages。

```bash
python -m venv .venv
```

Windows PowerShell 激活：`.\.venv\Scripts\Activate.ps1`。Linux/macOS 激活：`source .venv/bin/activate`。

以下为 focused 轻量安装，主动不安装历史 native/GPU/tracking 环境；`--no-deps` 不代表全项目依赖已满足：

```bash
python -m pip install --no-deps -e .
python -m pip install numpy==2.3.5 pandas==2.2.3 scikit-learn==1.8.0 exchange-calendars==4.13.1 pytest==9.0.2 streamlit==1.64.0 ruff==0.16.8 requests plotly
python -c "from pathlib import Path; Path('validation').mkdir(exist_ok=True)"
python --version
python -m pip freeze > validation/environment.txt
```

依赖版本是本次实际运行版本，不是宣称永远适用的最新版。真实数值对比需冻结依赖、输入和任务参数。

## 2. 当前可执行的自动回归

```bash
python -m pytest tests/test_focused_data_research.py tests/test_focused_streamlit_page.py -q --junitxml=validation/focused.xml
python -m ruff check src/finance_forecast_agent/focused_data.py src/finance_forecast_agent/focused_protocol.py src/finance_forecast_agent/focused_research.py scripts/run_focused_spy_campaign.py scripts/probe_focused_failure_semantics.py apps/pages/8_Focused_Research.py tests/test_focused_data_research.py tests/test_focused_streamlit_page.py
python -m compileall -q src/finance_forecast_agent scripts/probe_focused_failure_semantics.py apps/pages/8_Focused_Research.py
```

当前 pytest 期望 19 项通过，属于构造数据和 AppTest。覆盖复权字段、交易日缺口、时间因果、split、不足预算、参数边界、真实参数传递、失败计费和页面流程；不证明真实 LLM、恢复或新 Mission 能力。

整库测试另用完整环境，根据 `INSTALL.md`、项目 extras 和 native 专用环境准备外部资产后执行：

```bash
python -m pytest --collect-only -q
python -m pytest tests -q --junitxml=validation/full.xml
```

第二条才是真正执行。缺 PDF、DVC 数据、官方 source checkout 或历史报告时，应记录失败/缺失资产，不删测试。此轮只做过整库收集（191 项），没有跑过第二条。

## 3. 真实 SPY 原始数据端到端

使用已审计的 `spy_chart_2010_2025.json` 和 `spy_source.json`，放入 `inputs/`。不能以普通 close 代替 adjusted close，也不能使用合成数据后标成真实 smoke。

仓库历史 Actions run `35204186327` 曾提供 `focused-real-inputs`；该 artifact 的到期时间为 2026-09-24，之后应使用你自己保存的冻结副本，不依赖永久在线。源文件 SHA256 见核验报告。

```bash
python scripts/run_focused_spy_campaign.py --project-dir validation/real-spy --raw-spy-json inputs/spy_chart_2010_2025.json --source-metadata inputs/spy_source.json --advisor-mode deterministic --rounds 3 --candidates-per-round 2 --max-fit-calls 40
```

查看输出指向的 `campaign.json`：固定样例应有 4002 行、28 fits、`forecast_only`、`not_run_historical_data_exposed`；本次为 `completed_no_improvement`。允许以后合法实现产生不同开发结论，但不得通过换数据或阈值制造改善。每次保留完整产物和依赖版本。

## 4. 当前已知失败：PR-1 必须修

```bash
python scripts/probe_focused_failure_semantics.py --raw-spy-json inputs/spy_chart_2010_2025.json --source-metadata inputs/spy_source.json --output-dir validation/failure-probes
```

该命令实际训练基线，再对候选训练注入异常；不是市场实验。当前预期 **exit 1 / acceptance_passed=false**，同时预算计费仍正确。PR-1 修复后，应为 `execution_status=partial/failed`、`research_outcome=inconclusive` 且 exit 0。不要把这个已知失败标成“全绿”。

## 5. live-record 与离线 replay（本轮未完成成功验收）

先在本地 `.env` 或环境变量配置 `LLM_PROVIDER`、`OPENAI_BASE_URL`、`OPENAI_MODEL`、`OPENAI_API_KEY`。这些名称来自本仓库的兼容客户端；使用你实际可访问的模型和服务。不要提交密钥；记录和外发任务摘要也需要相应的数据授权。

```bash
python scripts/run_focused_spy_campaign.py --project-dir validation/live --raw-spy-json inputs/spy_chart_2010_2025.json --source-metadata inputs/spy_source.json --advisor-mode live --fixture-dir validation/live-fixtures --rounds 2 --candidates-per-round 1 --max-fit-calls 20
python scripts/run_focused_spy_campaign.py --project-dir validation/replay --raw-spy-json inputs/spy_chart_2010_2025.json --source-metadata inputs/spy_source.json --advisor-mode replay --fixture-dir validation/live-fixtures --rounds 2 --candidates-per-round 1 --max-fit-calls 20
```

第二条可断网执行。核对两次 prompt hash、假设/候选配置、相同目标行上的指标；campaign ID、时间和 advisor_source 不要求相同。live 提出非法模型时应拒绝，不能静默换成默认模型。一次成功调用不是 Agent 质量评测。

空 replay 负例（必须使用没有任何 fixture 的新目录）：

```bash
python scripts/run_focused_spy_campaign.py --project-dir validation/replay-negative --raw-spy-json inputs/spy_chart_2010_2025.json --advisor-mode replay --fixture-dir validation/empty-fixtures --rounds 1 --candidates-per-round 1 --max-fit-calls 16
```

预期非零退出和 `FileNotFoundError`，不能回退 deterministic 后称为 replay 成功。这一缺失负例本轮已验证；完整 live-record/replay 成功路径未验证。人工编写响应只能标记为 assistant-authored fixture，不能标成 live provider 调用。

## 6. 真实浏览器验收（本轮未做）

```bash
python -m streamlit run apps/streamlit_app.py
```

打开 Focused Research 页面。当前标题仍为 `Focused SPY Daily Research`，不是 Mission 首页。先填不存在的路径，确认没有合成回退；再填真实 raw JSON 和 metadata，选择 deterministic、3 轮、每轮 2 候选、40 fits，运行并核对页面指标与落盘 JSON。再测试预算不足、错误 symbol 和缺 adjusted close 的阻断。保存截图、输入 hash、结果目录和浏览器版本。

当前 focused 是同步调用。浏览器刷新恢复、并发与取消安全不能通过这个 V1.1 页面验收冒充已实现；须在 PR-4 完成后专门做。

## 7. 后续各 PR 的新增门槛（尚无对应完整实现）

| 阶段 | 需要补的功能与测试 |
|---|---|
| PR-1 / V2-A | 逐行预测复算、目标行一致、Manifest、朴素基线、反馈、Exposure、失败语义；本故障探针转为通过 |
| PR-2 / V2-A | 薄 Mission、契约变更创建新 Campaign、树与真实 diff 一致、用户完成任务流程 |
| PR-3 / V2-B | 证据引用存在/可见、反馈影响决策、真实 live/replay、Random/TPE/One-shot/Adaptive 同预算对照 |
| PR-4 / V2-B | 幂等提交、关闭浏览器/杀 worker 后恢复、已完成候选不重训、重试占预算、取消后迟到结果不覆盖 |
| PR-5 / V2.1 | Memory 兼容/租户隔离、未知或已暴露数据不能确认、Advisor 无隐藏标签访问、显式 refit、新进程加载模型 |
| PR-6 / V2.2 | CSV/Parquet 时间/标签合同、拒绝未审核代码/模型、第二个同类样例仅改配置、不改内核 |

每批同时留 commit、命令、JUnit/日志、环境、数据 hash、跳过/失败说明。无用户数据时允许明确标记的模拟输入；模拟接入不等于真实客户或商业验收。
