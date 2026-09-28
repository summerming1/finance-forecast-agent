# Agent 风格研究工作区：接入与使用

## 1. 接入范围

本次是已批准 HTML/CSS/JavaScript 页面与现有 Streamlit/Python 项目的接入，不是静态演示。默认入口仍是 `apps/streamlit_app.py`，页面通过 Streamlit 自定义组件与 Python 双向通信，不增加独立 API 服务、前端构建工具或第二套研究引擎。

界面功能：项目/研究列表，三步新建向导，原始数据与配置预检，实际队列任务及状态刷新，研究过程/实验/成果三视图，候选审阅，实际参数差异与 Manifest 可比性，显式 refit 及候选绑定模型下载，研究包导出，同 Mission 新 Campaign 续接，原队列取消/恢复与人工审核入口。页面不是通用聊天或自由研究任务编辑器。

正式集成以 `feat/mission-research-v2` 实际 HEAD 为准；开发验证分支为 `feat/agent-workspace-ui`，基于 `a75e72a068be6bb07ffc17e99b74b8e8d663a773`，保留已完成的录制硬中断修复。未修改 `src/finance_forecast_agent` 下研究源码、固定任务、评价规则或历史确认。

## 2. 更新与启动

先确认正在运行的任务状态及本地工作区。不要 reset、clean 或强制覆盖本地修改。停止旧网页服务不等于取消后台队列；有活动任务时先按原流程处理，不边更换环境边恢复旧合同。

工作区干净且位于正式分支时：

```powershell
git status --short
git fetch origin
git switch feat/mission-research-v2
git pull --ff-only origin feat/mission-research-v2
```

沿用原来项目的 Python 虚拟环境。没有新的 npm/Node 运行依赖；浏览器资源随仓库提供。原环境已满足项目声明时无需升级依赖。新建环境或缺少依赖时才按现有 extras 安装：

```powershell
python -m pip install -e ".[ui,byo,benchmark]"
```

**已有研究必须指向原来使用的状态数据库。** 下方路径是占位示例，替换为操作者已确认的原路径。不要复制一份空库、改库来解决研究列表为空或权限问题；不要把测试用数据库用于真实研究。

```powershell
$env:FFA_WORKSPACE_STATE_DB = "D:\你的原工作区\runtime.sqlite3"
if (-not (Test-Path -LiteralPath $env:FFA_WORKSPACE_STATE_DB)) {
    throw "找不到原状态数据库；停止启动，先核对原路径。"
}
python -m streamlit run apps/streamlit_app.py --server.address 127.0.0.1 --server.port 8507 --browser.gatherUsageStats false
```

打开 `http://127.0.0.1:8507`。这是需要本机服务的真实界面，不能用双击 `apps/workspace_frontend/index.html` 代替启动。已有服务占用端口时先核实并停止自己的旧服务，或选空闲端口；不要批量结束无关 Python 进程。

可选操作者配置：`FFA_WORKSPACE_TENANT`（默认 default）、`FFA_WORKSPACE_PROJECT_DIR`（新项目默认目录）。不改变原租户、状态库与项目关系。首次使用全新项目可以按原规则创建状态库，但这不能洗掉任何已有真实研究的暴露或信任历史。

## 3. 页面使用

**已有研究：** 左侧选择原项目的研究任务；顶部批次按钮切换同一 Mission 的运行。任务不存在时首先在左下“本地工作区”核对数据库和租户。旧的仅 JSON、未登记历史不伪造迁移，必要时用旧版工具查看。

**新建：** 目标与起点 → 数据与依据 → 运行与预算。无模型默认使用原固定基线；已有起点仍仅接受受支持配置。数据路径是在运行 Python 服务的机器上，不是任意远程上传。CSV/Parquet 必须具备原时间/标签/特征合同；快速预设不保证一定提出候选，更不保证改善。

**预检与开始：** 先由 Python 核对实际输入字节、来源、参数、预算和资料版本。确认摘要通过后再明确提交。编辑配置或输入变化后必须重新预检。普通浏览和预检不运行训练或提供者请求。

**研究/实验：** 页面读取原结果与反馈。切换候选同步右侧审阅、比较与成果；不自动 refit。数值最好、当前选中、开发门槛通过互相独立；部分执行、等待提供者、无改善等照实显示。原始提案不替代实际参数差异。

**成果：** 生成模型包需确认额外一次 refit；实际 `model.joblib` 与 `bundle.json` 通过原可信登记和候选检查后下载。已有对应包可以直接下载；切到另一个候选不能下载前一个候选的包。研究包由原导出器生成并遵守资料再分发限制。

**继续与恢复：** 继续研究先预览父候选、继承范围与原预算，再明确创建新的 Campaign，保留同 Mission 和父记录；不复制预测免除新训练。恢复只调用原队列恢复，仍受原源码/环境/资料/响应身份约束。审核批准/拒绝登记后，执行恢复另外确认。

**运行方式：** 默认 deterministic。Live 必须明确选择并确认费用及数据/文献发送，在服务器配置提供者；客户端不保存或接收 API key。Replay 需匹配的旧源码、环境和明确调用映射，不能拿新界面修改旧合同。

## 4. 兼容与边界

- `?legacy=1` 保留旧版入口，随后可进入原 Research Mission 页面；`?lab=1` 保留高级论文工作台。不要把旧使用指南中的控件名称当作新页面控件名称。
- UI 的操作 ID 在原 RuntimeDB 中记录，重复同一请求返回已有结果；不完整操作不自动再次执行。浏览器刷新未收到响应时显示不确定提示，先检查原记录，不连续点击收费操作。
- 项目路径、权限、确认资格和数值评价仍由已有 Python 层负责；前端禁用按钮不是唯一安全边界。
- 本次未新增独立金融确认入口、任意 Python/pickle 执行、自动交易、跨机器模型信任迁移或公共多租户部署。只面向可信本机操作者，默认监听 loopback。
- HTML 原型中的演示场景和假下载已移除，正常页面只显示当前数据库返回的记录。测试截图如标 simulation_only，来自模拟数据上的实际训练，不代表真实金融效果。
- 浏览器产物传输上限为 64 MiB；超限明确提示使用既有本地导出路径，不悄悄截断 ZIP。

## 5. 代码接线

| 层 | 位置 | 职责 |
|---|---|---|
| 路由与宿主 | apps/streamlit_app.py、apps/workspace_ui.py | 默认页面、事件去重、查询参数和组件通信 |
| 界面资产 | apps/workspace_frontend/ | 原生 HTML/CSS/JS，任务视图、草稿和确认交互，无 CDN |
| 薄适配层 | apps/workspace_ui_service.py | 原接口参数校验、只读快照、预检绑定与操作回执 |
| 原领域接口 | src/finance_forecast_agent/research_mission.py | 真实提交、查询、恢复、续接、refit、导出；本轮未改 |
| 研究与状态 | 原 Controller / Queue / RuntimeDB / Evaluator | 执行和证据的原唯一权威，本轮未重建 |

UI 代码放在 apps/ 下，避免仅修改界面就改变 package 全部 Python 文件的研究源码身份。但旧运行能否恢复仍须满足原合同，不能作自动兼容保证。

## 6. 验证口径

新增 `tests/test_workspace_ui.py` 验证实际预检、数据/模式/租户限制、动作确认、重复请求、候选绑定、真实 refit/下载、续接和预算上限语义。

`tests/browser/test_agent_workspace.py` 启动真实 Streamlit、自定义组件及队列子进程；输入为 simulation_only，模式 deterministic。覆盖两候选实际训练、浏览不训练、下载真实模型 ZIP 与研究包哈希、1280布局、页面刷新/新浏览器上下文恢复，以及明确续接的新 Campaign 与不变父记录。禁止提供者请求。

CI 入口是 `.github/workflows/workspace-ui.yml`，同时覆盖 UI 分支及正式分支。每次保存 exact HEAD/TREE、源码快照、JUnit、浏览器截图与报告。

已独立读取并核对发布前候选 `a5562df196199e3484dc971c01fa41510daedaca` 的 CI：

| 范围 | 结果 | 耗时 |
|---|---|---:|
| 新适配测试 + 完整真实 Chromium 路径 | 16 passed，0 failure/error/skip（含15项适配测试和1项浏览器测试） | 68.526秒 |
| 受影响既有 delivery/comparison/workspace/Streamlit 回归 | 54 passed，0 failure/error/skip | 94.837秒 |
| Python Ruff、compile、JavaScript语法 | 通过 | 以作业步骤为准 |

运行ID `36398389422`；源码树 `5ee439276023099c4e060e8dcba34dbfaac2bf54`；artifact ID `10959527048`，ZIP SHA256 `eee7e895c3d0af6ccefbbb0c703fdfff80403e29eff36c79d8d1cb5f723e81f8`。浏览器报告记录17项流程检查，无页面JS错误，无provider请求。上述16项已包含浏览器，不再重复累加。本地另跑15项适配测试是重复平台证据，不是额外15项独立覆盖。

保留先前失败：`77293b2` 的两候选测试只声明了动量特征，实际单候选/16 fits是合法预算上限行为；补齐模拟测试的波动率声明后仍保留两候选/20 fits断言，并加负例验证窄范围不会强制凑候选。`ffbffec` 已走到续接，但测试先看到了父任务的已完成提示；修正为先等确认响应和不同子Campaign，再核对完成及原后台状态。该提交的fixture导入Ruff问题通过把同一负例移回原测试模块解决，没有删除断言。旧失败收据不改成成功。

后续文档发布或正式分支快进产生的验证，须读取对应新SHA。上表只归属于已记录的候选提交，不能冒充后续提交已测试。

既有验收中的原冻结 SPY 输入缺失、Windows 特定环境、真人操作、研究价值及新金融证据缺口保持不变。不为了 UI 验收下载新行情冒充旧输入，也不调用付费模型补漂亮演示。
