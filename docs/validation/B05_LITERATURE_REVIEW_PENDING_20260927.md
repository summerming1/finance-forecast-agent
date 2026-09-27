# 两份原始资料的人工审核记录

状态：用户已回复“已查看并认可，允许本次简短观点使用”。已通过既有 MethodCardVersionStore 和显式审核 CLI 登记两个版本。仅短观点和出处可发送百炼，不发送全文；人工审核分钟数未提供，保留 null。
本地 PDF 仅供本次阅读；公开可下载不等于获准公开再分发或发送完整文献给外部服务。

## 1. Breiman，Random Forests，2001

- 原始来源：https://www.stat.berkeley.edu/users/breiman/randomforest2001.pdf
- 本地：`D:/b05runs/literature_sources/breiman2001.pdf`
- SHA256：`aaa9bc464d1d63eacc807ac8251331aa93b2aeb1c9411033e58cb7e8423fb920`
- 待核对位置：PDF 第 1 页摘要（作者版本；共 33 页）。
- 拟选短引文：`These ideas are also applicable to regression.`
- 作者观点概述：随机化树集合及树间相关性是研究对象，相关思想也适用于回归。
- 本地迁移假设：在已有随机森林配置范围内研究特征随机化；具体参数由本地实验提出，不能说是论文规定的最佳 SPY 参数。
- 限制：不证明 SPY 下一日收益可预测，不把分类结果直接当收益回归成绩，不改固定时间切分或指标。

## 2. Cawley 与 Talbot，2010

- 原始来源：https://jmlr.org/papers/volume11/cawley10a/cawley10a.pdf
- 本地：`D:/b05runs/literature_sources/cawley2010.pdf`
- SHA256：`db01ac8fabef3064a0297bfcf64fb9791bf35c4d03be7a51f5862260adfca206`
- 待核对位置：PDF 第 1 页摘要，期刊页 2079（共 29 页）。
- 拟选短引文：`over-fitting in model selection as well as in training the model`
- 作者观点概述：模型选择准则也可能过拟合，进而带来性能评价的选择偏差。
- 本地用途：作为限制和反证，提醒比较开发折稳定性、保留无改善和失败，不把筛选最好分数说成独立确认。
- 限制：本文不是当前 SPY 数据研究；不得擅自把项目切分改成论文的分类协议。

## 请审核者实际确认

用户确认仅针对上述第一页、两个短观点和本次迁移用途。审核身份为 user-attested-20260927，版本和来源哈希记录在 `D:/b05runs/literature_reviewed`，实际用时未知。G1/G2B 的运行结果另外验收，人工批准不代表它们已经通过。

两个来源的第一页先由助手进行 PDF 视觉核对，再由用户实际查看并确认。两种角色分开；哈希仅用于内容绑定。没有记录不存在的人工分钟数，也没有把本次短观点授权扩大为全文外发或公开再分发许可。

## 真实回复的引用用途抽检

百炼 kimi-k3 的记录 `9b7e108387b344658516af38b1c25718` 将 Cawley/Talbot 观点作为反复挑选开发集分数可能有选择偏差的限制；alpha=5 是本地提出的实验参数，不是论文规定。回复明确论文未验证 SPY 效果，不改变冻结切分。

用户在看到上述用途说明后回复：“认可引用用途，但不代表实验通过”。这仅是此条引用用途的人工抽检，不是全部回复、所有引用或实验结果的审核。人工用时未提供，仍为 null。

同一回复漏掉必填的 statement 字段，已在候选训练前被 compiler 拒绝。G2B L1 因而为 FAIL，不能以这次人工认可覆盖执行失败，也不能据此声称文献提高了研究效果。
