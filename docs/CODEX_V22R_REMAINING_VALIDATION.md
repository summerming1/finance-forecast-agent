# Codex：B0–B5 交付后的统一补测任务

## V2.3实施关联（2026-09-29，C4模型包本地验证后）

本文件继续是旧A/L剩余项的唯一交接入口。[V2_3_FEATURE_RESEARCH.md](V2_3_FEATURE_RESEARCH.md)为用户已批准的V23实施方案；[ADR005](ADR_MISSION_PRODUCT_005.md)已accepted，不改变旧48条状态，也不自动执行下面的付费/真实确认/真人步骤。V23-T/X以实际收据更新；C0必须映射相关旧门禁，不能一句“旧B5不阻塞”一笔豁免。

只整理文档时不重复旧已有效完成的收费G2A/G2B；原冻结输入缺失、真实语义负例和真人参与缺口继续如实保留。新特征协议的工程预览、Live小试验与真人试用分别验收。当前Agent工作区验收须显式包含`tests/test_workspace_ui*.py`及`tests/browser/test_agent_workspace.py`，不能仅靠focused文件通配符覆盖。

C0–C4收据见V23日志§12；新特征已在原Controller/worker训练，raw ModelBundle及权限导出相关94项通过，原trust回归31通过/1项Windows symlink权限失败。C5–C6继续按门禁实施，尚未交付完整用户闭环。旧A/L状态不由新工程测试关闭；2a21890核心/旧浏览器通过，新工作区同步竞态已在b80bdb4修测试，其新旧浏览器CI通过；C4同SHA另核对。原SPY资产仍缺，真人/真实语义尚未补齐。新Live预算仍需明确批准，不重复旧付费G2A/G2B。

## 既有B0–B5补测范围

本文件是当前补测入口，替代旧“R0–R6尚未跑通”的清单，不改写历史验收收据。
2026-09-28 增量证据见 [B5_INCREMENT_20260928.md](validation/B5_INCREMENT_20260928.md)；旧失败及48条原条款保留，不因新小样本完成而全部关闭。
随后限定的录制硬中断收口见 [B5_RECORDING_RECOVERY_20260928.md](validation/B5_RECORDING_RECOVERY_20260928.md)；新证据已追加关联原A04/A05/A06/A08/A23/L18。不要重复付费G2A/G2B；下一步可做受控真人试用，原冻结资产、Windows权限及真实语义负例仍分别保留。旧源码合同不能在新版强改hash恢复。
正式分支 `feat/mission-research-v2`；B4已发布 `e983c4dfb90bb96d314fb0d2a8474e31537d1223`。
B5最终HEAD以拉取后实际Git与同SHA CI为准；不得把文档中的父提交当最终提交。
当前状态只见 CURRENT_IMPLEMENTATION.md，批准范围见 ADR_MISSION_PRODUCT_004.md。

8817d68的Linux新增硬中断测试因POSIX回收冲突失败，已修正测试所有权回收路径，必须核对后续最终SHA核心CI；保留该8项失败历史，不以Windows通过代替Linux。

## 交给 Codex 的完整指令

你要做的是独立补充验收与必要最小修复，不启动V3，不重写Controller/Queue/Evaluator/Memory/MethodCard，不扩任务、资产、任意代码和交易功能。

### 0. 安全读取与证据基线

先 `git fetch origin`、检查 `git status --short`、分支及HEAD。工作区不干净时保留用户修改，在单独worktree验收；不得reset、clean或force push。只允许 `pull --ff-only`，分歧时先检查而非覆盖。
读取顺序遵循AGENTS.md：Roadmap → Current → 最新相关版本日志（V2.3提案与原V2/B5日志）→ 相关ADRs并检查批准状态 → Architecture → Acceptance → Handoff → 本文件及validation/v22r_acceptance.json。涉及工作区时再读AGENT_WORKSPACE_UI.md与FRONTEND_USER_GUIDE.md。
记录base/head、源码树、Python/OS/关键依赖、输入hash、命令、exit和JUnit。每项用PASS/FAIL/BLOCKED/NOT_RUN；跳过、缺凭证、未调用provider都不能写PASS。
原R1真实Live/Replay、R2 Windows恢复、R3审核动作、原浏览器与47行负确认已经有历史证据，不能再说从未实现；本轮补的是新合同/新代码/新环境。

### 1. 本机核心回归与真实浏览器

建议Python3.13与3.11；本地没有某版本就记录BLOCKED_ENV，不用3.9替代。
安装原声明extras：`python -m pip install -e ".[dev,ui,pdf,byo,benchmark,browser]"`。
在Windows下用Python glob构造路径，避免shell通配差异：

```python
import glob, subprocess, sys
paths = sorted({p for pattern in ('tests/test_focused*.py','tests/test_task_queue*.py','tests/test_*memory*.py') for p in glob.glob(pattern)})
paths += sorted(glob.glob('tests/test_workspace_ui*.py'))
paths += ['tests/test_method_card_v3.py','tests/test_streamlit_review_gate.py','tests/test_p09_review_backlog_timeline.py']
raise SystemExit(subprocess.call([sys.executable,'-m','pytest','-q',*paths,'--junitxml=validation/local-core.xml']))
```

设置 `FFA_BROWSER_E2E=1`、`FFA_BROWSER_ARTIFACTS`和`FFA_UI_BROWSER_ARTIFACTS`分别指向本次新的证据目录，安装正常Playwright Chromium，执行 `python -m pytest -q tests/browser --junitxml=validation/local-browser.xml`（实际运行换新的收据路径，不覆盖旧失败）。不绕过管理员浏览器/网络策略。
重点：两个入口、数据草稿不丢、当前候选A导出A、切B不误标A、刷新/新会话不训练、总结不触发LLM、确认预检不读标签/不创建授权、新Campaign与resume区别、同Mission与正确父ID、子任务自己的完成提示、父记录不变与新增费用可核对。
Windows符号链接权限缺失标BLOCKED_ENV，不改系统策略；macOS/GPU按用户本轮范围不执行。

### 2. 冻结真实SPY及过期CI产物恢复（优先）

已发现旧CI `focused-real-inputs` 的run `35204186327` 产物不可用，B4发布run `36291075239` 实际FAIL于下载，模型步骤未执行。不能把它写成算法失败，也不能把本地通过写成远端通过。
使用原始合法本地副本，原raw SHA256必须为：
`5fb282f6278d14000592e0e432fe69a5c00fdb6f7b48cbb56368fc0e3185bbcd`。
源元数据还需与raw一致。不要重新向Yahoo下载一份再假装同一冻结输入；用户后来0BB0…等其它副本也不是本收据的同一字节版本。

```text
python scripts/verify_frozen_spy_acceptance.py --inputs INPUT_DIR --check-input-only --receipt validation/input-check.json
python scripts/run_focused_spy_campaign.py --project-dir RUN_DIR --raw-spy-json INPUT_DIR/spy_chart_2010_2025.json --source-metadata INPUT_DIR/spy_source.json --advisor-mode deterministic --rounds 3 --candidates-per-round 2 --max-fit-calls 40 --state-db STATE_DB
python scripts/verify_frozen_spy_acceptance.py --inputs INPUT_DIR --campaign-root RUN_DIR/focused_campaigns/ACTUAL_CAMPAIGN_ID --state-db STATE_DB --output-dir NEW_AUDIT_DIR --receipt validation/real-spy-audit.json
```

每次换新输出目录/收据名；不得覆盖原失败。该auditor复算8份预测、检查完整包索引和哈希、显式refit一个已接受Ridge、在新进程执行8行无label推理；推理输入是训练尾部接口样本，不能称样本外预测。
如已合法将相同字节存于可访问Actions artifact，可在workflow_dispatch指定 `frozen_input_run_id`，或显式配置repo变量 `FFA_FROZEN_INPUT_RUN_ID` 后运行**同一HEAD**。workflow仍按固定hash核验、缺资产仍失败，保存BLOCKED_ASSET收据。
不上传原行情到公开Git、不降低许可限制。没有合法存储/副本就保留BLOCKED_ASSET，不能把CI改成skip/continue-on-error制造绿灯。

### 3. 新合同真实Live→记录→严格离线Replay及长程稳定性

仅使用用户已授权的provider/model和费用范围。无凭证或费用授权写BLOCKED_NO_PROVIDER/BLOCKED_NEEDS_AUTH，不自动关闭免费限额或换模型，不公开key。
先检查实际policy：connect/read/deadline、HTTP请求上限、累计provider活动秒、max tokens、temperature、模型别名。预检不是余额查询；别名不是可保证固定的模型版本。记录提供者实际返回标识及别名风险。
从2轮小任务开始，不直接重跑36/45臂。CLI先 `--help` 核实：`--max-advisor-calls`、`--max-http-requests`、`--max-provider-seconds`、`--fixture-dir`、`--state-db`、`--no-memory`。总训练仍fit受限，不宣称整个Campaign墙钟或人民币硬上限。
验证第N轮超时/额度故障后waiting_provider，恢复同合同不重训前N-1轮、原计划不变；迟到响应/并发恢复同决策最多接受一份计划，新HTTP尝试仍计费、未知费用为null。
在新进程禁止网络且移除keys后Replay，使用显式prompt-hash→call-ID映射；核对proposal、实际diff、反馈引用、逐行预测、数值和源版本。仅清key不等于系统级断网。至少完成一条代表性长程轨迹，几次成功只能作初步可靠性证据。

### 4. 文献真实语义与权限（G1）

准备2–3篇合法原始资料，审阅实际段落/页码而非只看模型摘要。通过既有MethodCardVersionStore与review_focused_literature.py按具体版本审核；哈希只证明一致性。
至少一条当前可执行思想和一条限制/反证：原文事实→迁移差异→真实LLM假设→实际单因素或明确联合修改→反馈→下一批决策→Replay。无关/不支持观点应合理拒绝；不要求输入不同就强行输出不同模型。
provider必须在audience许可中。对抗测试：原文注入指令不能改label/预算/权限；正确ID但误引不能被视为语义通过；运行中撤销权限后含重试不能再发送；版本替换不能无审计继承；受限ResearchPackage不含原文、prompt或派生私有叙述。
文献准备和人工审核成本未知时保留未知，不填零。现有确定性规则不解释论文，fixture证明工程，不证明真实理解。

### 5. G2A：实际五臂小规模匹配对照

`python scripts/run_research_value_benchmark.py --help`。
用一个固定开发窗口、一个search seed先跑Random/TPE/One-shot/Adaptive-step/Adaptive-batch，实际名称为 `random tpe one_shot adaptive adaptive_batch`。
建议首个有效小比较候选预算8、startup-trials4、batch-size2，固定estimator seed、raw/目标行/切分/目录/模型/调用合同，memory冷。若实际服务预算不足，提前冻结更小方案并说明TPE是否进入model-based阶段，不拿纯startup冒充优化效果。
参考入口：`--raw-spy-json RAW --source-metadata META --arms random tpe one_shot adaptive adaptive_batch --llm-mode live --fixture-dir FIXTURES --candidate-count 8 --startup-trials 4 --batch-size 2 --seed 42 --estimator-seed 42 --windows all --memory-mode cold --out NEW_REPORT.json`。
检查所有尝试/唯一候选/失败/重复、实际fit、LLM逻辑/HTTP次数、时间、token/unknown成本。合法stop可完成，不强迫找赢家；失败best-so-far不进完成排名；不得选择性保留最佳重试。混模型/timeout必须分版本，search seed不是provider seed。
有限目录和重叠历史窗口限制明确；旧R5主矩阵FAIL保留，新结果另写有版本收据，不改历史。

### 6. G2B：文献增量单独比较

相同Adaptive策略、模型/服务、预算、目录、目标行、context模式和memory冷，对照 L0不提供显式文献 / L1固定1–3条审核观点。
入口：相同冻结参数加 `--arms adaptive_batch --literature-ablation --literature-project LIB --literature-review-ids REVIEW_ID --memory-mode cold --llm-mode live`。用新的out，不与G2A巨型全交叉。
两组的运行状态分开，只有完成且合同一致才配对；不给L0读取L1解释/Memory，但保持真实曝光历史。L0不是模型无预训练知识；L1需单列额外准备/人工费用。评价忠实性、实验设计、反例使用、劳动和误差/成本，不要求文献必胜。
另需Memory cold/warm有效增量对照时，在固定历史快照与预算下单独执行；结构上可读记忆、重复本就为零不能当成越用越聪明。

### 7. 1–3位真实研究者与受控BYO（G3）

至少覆盖无模型目标入口和已有模型/一个审核ext_*数值特征入口。用户本人操作；助手模拟不得计为真人。记录接入分钟、代操作步骤、结果理解、是否正确下载当前候选、是否把结果用于下一次研究、真实再次使用。
无真实用户写BLOCKED_NO_REAL_USER。数据时点仅声明和系统核验分开；无raw价格无法复算标签需如实降级。不能为使用便利开放任意pickle/Python/Docker。

### 8. 确认与历史/native/迁移边界

新zero/mean/median确认对照用模拟授权测试：只读训练标签，统计次数与fit分开，重复授权不执行；preflight不等于eligible。不重复使用已披露47行，不重新挑窗口/阈值/基线争取通过。真实新确认仅在合法新数据、预冻结且用户单独授权条件下执行。
复核包外可信登记、被改模型/权限路径、跨进程加载。跨机器迁移信任尚未实现，不能靠复制包/注册库自动声称支持。
旧运行schema按兼容合同只读或显式拒绝，不能改hash强行恢复、不能空库洗曝光。
执行一次全仓pytest并逐项分类当前失败，缺资产不是成功；传统PDF/native环境按 constraints/pdf-legacy-validation.txt 单独安装，记录解析器版本，禁止批量改fixture掩盖差异。无需为这次客户端/交付改动强行跑GPU/小时级论文训练。

### 9. 结果和最小修复交付

JSON中的48条A/L验收逐项核对；`remaining_clause_ids`列出未完整关闭的条款。尤其并发恢复、真实断线成本、文献提示注入/误引、批内未来证据、L0/L1污染和人为成本需要对抗检查。没有证据保持PARTIAL/NOT_RUN，不用测试总数替代条款覆盖。
发现缺陷先保留失败样例→最小修复→定向测试→受影响核心/浏览器→更新现有V2日志和CURRENT→单独提交。不得放宽证据规则、静默fallback、改历史科学结果、无限重试求赢家。
最终报告必须包含：base/head/tree、每组命令/exit/JUnit、真实/模拟输入、哪些由本次重跑哪些只引用历史、provider实际请求与费用未知、PASS/FAIL/BLOCKED清单、下一步。不承诺自主研究稳定优胜；V3仍未启动，前瞻生命周期不是本轮补测可以凭空通过的功能。
