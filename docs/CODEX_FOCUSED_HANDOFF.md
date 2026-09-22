# Codex handoff — V2.2-R

唯一当前状态：`CURRENT_IMPLEMENTATION.md`。正式分支 `feat/mission-research-v2`；不要按旧 PR 数字推断完成。
先读 AGENTS、Roadmap、当前状态、ADRs、Architecture、Acceptance 和 V2_MISSION_RESEARCH。

本轮只做批准的 R0→R6：状态收口；身份/Evidence/Replay；持久执行；真实动作/Memory；确认/模型信任；真实策略对照；Workspace/BYO 集成。前一批新旧相关测试通过并提交后才能开始下一批。

保留一个 Controller/Queue/Evaluator/Memory。单机事务存储可以替换脆弱文件状态，JSON 是导出而非第二个状态真源。旧 Campaign 只读，缺合同不得自动恢复。默认不信任外部文献指令、任意代码、包内 trusted 标记或 self-declared sealed。

测试要绑定条款、源码 SHA/tree、命令/exit code、环境和真实/模拟等级。资产缺失和真正科学/客户证据不足单列；不能把阻塞悄悄变成跳过后“全部通过”。本轮不得启动完整 V3。


## R4 已交付后继续点

R0～R4 有实现和定向/累计证据；下一批是 R5，未经请求不继续。R4 在既有 RuntimeDB 上实现封存注册、冻结固定留出协议、单次授权和包外模型信任。CLI 仅接收 grant ID；模型加载必须显式 state_path 或可信 FFA_DELIVERY_STATE_DB，不从包内字段自动信任。旧包需要重发，旧原型确认仅保留 simulation 兼容。具体接口、环境和未测项见 CURRENT_IMPLEMENTATION 与 V2_MISSION_RESEARCH。
