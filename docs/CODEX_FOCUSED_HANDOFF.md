# Codex handoff — V2.2-R

唯一当前状态：`CURRENT_IMPLEMENTATION.md`。正式分支 `feat/mission-research-v2`；不要按旧 PR 数字推断完成。
先读 AGENTS、Roadmap、当前状态、ADRs、Architecture、Acceptance 和 V2_MISSION_RESEARCH。

本轮只做批准的 R0→R6：状态收口；身份/Evidence/Replay；持久执行；真实动作/Memory；确认/模型信任；真实策略对照；Workspace/BYO 集成。前一批新旧相关测试通过并提交后才能开始下一批。

保留一个 Controller/Queue/Evaluator/Memory。单机事务存储可以替换脆弱文件状态，JSON 是导出而非第二个状态真源。旧 Campaign 只读，缺合同不得自动恢复。默认不信任外部文献指令、任意代码、包内 trusted 标记或 self-declared sealed。

测试要绑定条款、源码 SHA/tree、命令/exit code、环境和真实/模拟等级。资产缺失和真正科学/客户证据不足单列；不能把阻塞悄悄变成跳过后“全部通过”。本轮不得启动完整 V3。
