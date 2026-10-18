# CallGate：图、概率与密码学复用方案

检索日期：2026-09-09。下面 stars/forks 来自本轮 GitHub API，随时间变化；均未标记 archived。热度不是安全认证。本轮为研究与接入设计，未新增云端 Fork、模型训练或运行依赖。

## 候选与优先级

| 项目（官方仓库） | Stars / Forks | 现成能力 | CallGate 用法与条件 |
|---|---:|---|---|
| [NetworkX](https://github.com/networkx/networkx) | 17,254 / 3,595 | 图结构、遍历与网络算法 | P0：会话内证据图，关联转录、身份声称、操作和独立验证；身份解析必须有来源 |
| [cryptography](https://github.com/pyca/cryptography) | 7,759 / 1,821 | 成熟密码学接口 | P0：用 Ed25519 验证独立核验者签发的凭据；必须预先信任签发者公钥 |
| [pgmpy](https://github.com/pgmpy/pgmpy) | 3,323 / 1,156 | 概率图模型与推断 | P1：离线比较风险证据组合；条件概率须从合适数据估计或明确标为假设 |
| [River](https://github.com/online-ml/river) | 6,090 / 816 | 流式机器学习 | P1：监测特征或误差变化；标签需审核，避免自动吸收攻击者反馈 |
| [PyG](https://github.com/pyg-team/pytorch_geometric) | 24,071 / 4,047 | 图神经网络、异构图、采样 | P2：有足量合法关联数据后，研究账号—设备—号码—收款方关系 |
| [PyGOD](https://github.com/pygod-team/pygod) | 1,496 / 139 | 图异常检测 | P2：图模型基线；异常不能直接标为诈骗 |
| [DGFraud](https://github.com/safe-graph/DGFraud) | 757 / 167 | 图欺诈检测研究工具箱 | 复现论文与评测设计；旧依赖隔离，原数据领域效果不等于电话效果 |
| [OpenFGA](https://github.com/openfga/openfga) | 5,743 / 487 | 基于关系的授权检查 | 多机构、多角色时采用；无法代替注册身份、凭据签名或交易防重放 |
| [Semaphore](https://github.com/semaphore-protocol/semaphore) | 1,083 / 297 | 匿名群组成员证明 | P2：证明属于已注册核验者群组，减少身份披露；需群组治理与撤销设计 |
| [Circom](https://github.com/iden3/circom) | 1,690 / 376 | 零知识电路编译器 | 定制 ZK 的研究工具；不能直接变成诈骗识别模型 |
| [cadCAD](https://github.com/cadCAD-org/cadCAD) | 620 / 276 | 动态系统与策略仿真 | P3：举报奖励、刷号成本、误罚代价的假设实验；当前无需发行 token |

附加基础工具：[SciPy entropy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.entropy.html) 提供 Shannon entropy 和 KL divergence。它们能测量指定分布的不确定性或差异，不能自行定义诈骗概率。

## 让数学真正约束系统

1. **证据图 G=(V,E)**：节点记录证据类型、来源和转录 revision；边区分“声称”“请求”“支持”“反驳”“经独立渠道验证”。相同电话号码或文字提及不能自动合并为同一真人。先实现会话内图；跨会话图需要额外的数据保留与访问设计。
2. **概率 P(F|E)**：F 是严格定义的风险标签，E 是观察到的证据。相关证据不能按独立事件重复相乘，例如“立刻”和“今晚”通常来自同一施压行为。合成案例不足以估计现实先验；现有 35/100 必须继续标注启发式分数。
3. **信息增益 IG(q)=H(F|E)-期望[H(F|E,回答q)]**：可研究哪些核验问题最有价值。该目标只有在概率模型可信时才有效；来电者可撒谎，其回答不构成独立验证。问题选择还应考虑用户负担和误导风险。
4. **密码学验证**：签名绑定版本、签发者、session、action、resource、expiry、nonce；验证签名后仍须检查范围、时效与一次性消费。签名证明密钥持有者签过数据，不证明现实中的身份声明真实。[Ed25519 官方接口](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)。
5. **最终授权条件**：有效签名 AND 已注册签发者 AND 会话与动作匹配 AND 未过期 AND nonce 未消费 AND 所需人工确认 AND 当前策略允许。nonce 消费必须原子化。任何模型分数都不能替代这些条件。

这些公式是设计要求，尚未在当前运行时全部实现。当前 Guardian 仍为建议模式，尚无真实受保护工具网关。

## 第一轮接入范围

优先增加 NetworkX 证据图适配器及独立验证凭据模块，保留现有 transcript → events → deterministic policy 接口。密码学通过标准库依赖复用，不复制实现椭圆曲线算术。

随后将 pgmpy/River 放入独立实验环境，按同一个 ScamBench 协议与规则基线对照。时间、主体、诈骗话术家族分别隔离，防止训练测试泄漏；报告误报、漏报、校准误差、拒答覆盖率与时延。标签延迟、漂移及反馈投毒需单独测量。

密码学验收必须包含篡改消息、错误公钥、过期、跨会话、扩大 scope、重复使用和并发重放；图验收必须包含伪造边、同名不同人、转录修订和重复证据。真正的数学严谨性在于假设、边界和反例能被检查。

## 复用与许可证

PyG、pgmpy、Semaphore、cadCAD 的仓库 API 报告 MIT；PyGOD 为 BSD-2-Clause，River 为 BSD-3-Clause，DGFraud 与 OpenFGA 为 Apache-2.0，Circom 为 GPL-3.0。NetworkX 与 cryptography 的 API 返回 NOASSERTION，不能据此认定无许可证；采用时须核对固定版本的 [NetworkX 许可证](https://github.com/networkx/networkx/blob/main/LICENSE.txt) 与 [cryptography 许可证](https://github.com/pyca/cryptography/blob/main/LICENSE)。模型权重、数据集及子模块另查。

常规库优先固定依赖版本；只有需要维护上游修改才 Fork。研究仓库在隔离环境复现。Circom 工具链、电路和生成产物的许可证分别核对。ZK 的群组成员资格不等于真人唯一性、诚实性或转账授权；tokenomics 的激励也不能替代安全策略。
