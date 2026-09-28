# B5 录制硬中断收口（2026-09-28）

## 范围与身份

审阅/实施 base：`6056c3e3ef4b7693dede5337cf7f2b75fc6b1373`，base tree：`f45807051c05ec8a27fb5ce93e12d61b5ee8bd68`。
开始 fetch 后远端同 base，无新提交。沿用已有干净验证 worktree；原项目目录的旧 HEAD/未跟踪资产未改动。
本轮仅录制与恢复边界、测试和原验收映射。无付费请求，无资料外发，无原真实 RuntimeDB 写入，无新金融确认，无 UI 改造/V3。
Windows 11、Python3.13.3。每个新测试使用自己的 `simulation.sqlite3`、合成 SPY 和本机 HTTP；这不是新的生产状态库或 provider 稳定性证据。
新进程测试的合成输入SHA256：`d5322b6cdc540cd21a42329d094a1fa1624d7ffb4dcdd9f965da32547caae98a`。权限与DB故障通过测试包装注入PermissionError/OperationalError；不更改本机ACL或制造真实磁盘损坏。HTTP与进程终止是真实执行，内容和故障来源为simulation_only。

## 复现，而不是推测

原源码新增负例：`hardcut_red`，exit1，6 failed/4 passed，90.31s。

| 原行为 | 观测 |
|---|---|
| 第2次 HTTP 已到达本地服务，但 outcome 尚未登记时终止 owner | 恢复静默请求第3次；fit保持16 |
| HTTP outcome 已登记，但 fixture 尚未可靠完成时终止 | HTTP 2→3 |
| 写出半个 JSON 后终止 | 坏文件未被当作恢复阻断，HTTP 2→3 |
| 完整 fixture 写完、returned_advice 尚未登记时终止 | 未接受的孤立文件没有可靠复用关系，恢复重新请求，HTTP 2→3 |
| 请求前临时权限故障 | HTTP=0，却被 recording_failure 永久阻断 |
| 第1次HTTP后数据库所有后续写入失败 | 无 recording_failure，恢复HTTP 1→2 |

已登记完整响应的恢复和已登记响应的坏JSON/hash拒绝在原实现就通过。没有重复开发这些能力。
使用 multiprocessing spawn 创建真实 owner，通过 Pipe 屏障确认具体边界；父进程调用既有、绑定PID出生时间的原生进程树终止函数。没有用固定 sleep 猜中断时机。

## 最小修复依据

`focused_runtime.py` 在新规划请求前读取既有 `advisor.call_reserved` 事件及 HTTP/Advisor 账本：

- 本决策已发生 HTTP 但无可靠接受响应/完整失败收据时，拒绝跨进程自动重发。
- 未知投递不等于没有调用；HTTP、fit、Advisor和provider时间预留不回退，金额仍null。
- 孤立完整fixture不自动升级成已接受计划；既有 returned_advice/冻结计划继续走原校验和复用路径。
- 显式恢复一个已经完整记录的 provider failure，仍可产生新的、独立记账HTTP尝试；复用原失败记录须与原DB收据完全一致。坏文件不删除、不绕过。
- 正常进程内部的429/503有界瞬态重试没有改变。

`llm_adapters.py` 在预检时明确记录 `preflight_failed / not_sent / http_attempts=0`。
`focused_research.py` 将其写成不永久封锁决策的前置失败事实；同路径临时权限修复后可以按原合同恢复。改变fixture根目录仍是合同变化，拒绝强改hash恢复。

数据库不可写时异常向上失败，可能连失败标记都写不进去。既有发送前事务成功时可保留HTTP reservation，后续恢复据此阻断；发送前事务失败则不会发HTTP。不承诺数据库丢失/损毁等任意灾难下完整留账，也不承诺恰好一次计费。需要原状态恢复/人工审计，不能删除账本后宣称安全重试。

## 测试与关键计数

- `hardcut_target`：67 passed，111.48s，exit0。
- `hardcut_extended`：66 passed，185.09s，exit0；包含新进程案例、原provider、R1完整性、R2恢复和共享Queue。
- `core_hardcut_final`：405 passed / 1 failed / 2 skipped，512.03s，exit1。唯一失败为 `test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink]` 在创建fixture时WinError1314，BLOCKED_ENV；不是本轮恢复回归失败。
- `browser_hardcut_final`：真实Chromium 1 passed，78.54s，exit0。
- `lint_hardcut_final`、`compile_hardcut_final`：exit0；本轮3个生产文件及新测试Ruff通过，src/apps/tests编译通过。
- 本轮未重跑全仓historical/native，复用父提交报告且不升级为新源码全仓通过。未重新执行付费G2A/G2B。

精确展开命令、退出码、运行时间、JUnit/log路径和SHA256、各hard-cut断言属性及源码哈希见 [JSON收据](B5_RECORDING_RECOVERY_20260928.json)。本地运行时HEAD仍为6056c3e但源码含未提交修复；收据同时固定实际source_hashes，不冒称父提交包含修复。最终提交只整理文档/收据，生产源码与上述最终回归一致。
JUnit保存在实施worktree的 `validation/b05_20260927/{hardcut_red,hardcut_target,hardcut_extended,core_hardcut_final,browser_hardcut_final}.xml`，原red收据和坏记录保留，不覆盖。

实际生产修改仅 `focused_runtime.py`、`focused_research.py`、`llm_adapters.py`；新测试 `test_focused_b5_crash_recording.py`。其余修改为Current/V2日志/统一入口/原条款映射及本报告收据。未修改UI、数值评价器、Queue、Replay文件格式或原始行情。

同最终SHA的远端CI在推送后核对，结果随交付记录给出；父提交396项/Chromium绿色不是本轮408项的结果。原冻结数据CI失败继续单列，不采用continue-on-error。

最终新测试共12个：硬中断6种边界；同合同权限修复与改根目录拒绝；已登记记录JSON/hash破坏2种；数据库前/后失败2种；损坏的已记录provider失败拒绝重试。

| 修复后场景 | HTTP / fit |
|---|---|
| 未登记outcome、未完成fixture、半JSON、孤立fixture | 恢复前后HTTP 2/2，fit 16/16；拒绝未可靠保存计划 |
| 已接受响应、已冻结计划 | HTTP 2/2，fit 16/16；正常完成，无基线/候选重训 |
| 前置权限失败，修复同一路径后恢复 | 第一次HTTP0/fit12；恢复后总HTTP2/fit16；基线未重训 |
| 改fixture根目录 | HTTP不增加；合同不匹配拒绝 |
| 已接受记录被损坏 | HTTP2/fit16；坏字节原样保留，拒绝 |
| 数据库发送前写入失败 | HTTP0/fit12；恢复DB后正常研究 |
| 数据库响应后写入失败 | HTTP1/fit12；DB修复后仍不自动重发 |

已接受结果、计划、fixture字节及资源预留保持；known returned usage=13模拟tokens断言保留。Junit内记录HTTP/fit before/after。`record_property`产生xunit2兼容警告，不是跳过或隐藏失败。

## 原条款关联，不重写历史

在 `v22r_acceptance.json` 追加本次补充证据，而不覆盖原条款定义、历史科学记录或整体状态：

- A04/A05：本轮模拟HTTP+真实进程重跑，未知投递/硬中断/预算保留PASS。
- A06：本轮重跑原Queue并发幂等与owner fencing；原同决策并发provider补测作为历史复用，不冒充本轮重新进行了完整并发服务实验。
- A08：原截断/部分JSON拒绝本轮回归；新增坏落盘文件及记录破坏拒绝PASS。
- A23：原合同/旧Replay完整性保护本轮回归；新旧源码合同不强行迁移，通用旧schema迁移仍未认证。
- L18：本轮只复用既有真实L1 Replay历史证据，相关模拟文献回归单列；未新调用真实LLM或发文献。

## 剩余边界与停止

### 发布 CI 发现的测试进程回收问题

修正后Windows定向12项通过（`python -m pytest -q tests/test_focused_b5_crash_recording.py --basetemp=C:/b5tmp/hardcut_posix_harness_short --junitxml=validation/b05_20260927/hardcut_posix_harness_short.xml`，exit0，wrapper101.98秒），Ruff/compileall/diff检查exit0。此前未指定短basetemp的重跑12项执行完后，pytest退出清理旧Temp/pytest-current遇到WinError5、exit1，收据hardcut_posix_harness保留，未删除旧Temp或改权限。生产源码与累计405项及Chromium本地收据一致，测试仅POSIX终止适配；完整Linux适用核心由最终SHA CI重跑。

8817d6894a7032037b66ab193789f7af6dc9ce0a 的 Linux CI（run 36387508167）两版本均8 failed/400 passed：Python3.11为425.95秒，3.13为433.39秒。8项均在新测试 `_kill` 的 `Process.is_alive()` 断言失败，尚未运行恢复断言，不是8次重复HTTP。POSIX下 `psutil.wait_procs` 与 `multiprocessing.Process.join` 争用waitpid；测试改由创建者 `Process.kill/join` 回收自身子进程。Windows继续使用现有原生tree终止。生产终止/Queue代码未改，不删除测试或放宽HTTP/fit断言。该失败保留；修正后的最终SHA CI另行交付。该SHA Chromium1 passed/82.13s；冻结SPY因focused-real-inputs不存在失败。

旧冻结 `focused-real-inputs` 缺失继续BLOCKED_ASSET。Windows symlink权限仍单列；Linux同SHA结果不能冒充Windows本机通过。
真人实际操作/自然复访仍BLOCKED_NO_REAL_USER；真实语义负例未全部完成。旧47目标负确认、付费G2A/G2B保持历史，不重跑。
本轮不做macOS/GPU/大型native；不补不相关UI功能或扩大提示词示例工作。源码变化不支持直接恢复旧合同，旧结果只读/使用原版本；没有修改旧hash或历史文件。
适用回归及同SHA CI核对后，可结束这个代码收口并进入受控真人试用；不等于完整B5或V3资格PASS。
