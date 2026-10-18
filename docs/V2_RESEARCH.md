# CallGate v2：仓库检查、开源检索与实施选择

检查日期：2026-09-08（用户所在地）。范围：指定仓库完整克隆、研究文档检查、全网检索、GitHub 官方仓库页面与元数据。以下是选型研究，不是对所有第三方代码的安全审计，也未复现第三方论文成绩。Star/fork 是读取页面时的显示值，可能经缓存及取整；不作为模型有效性的证明。

## 1. 当前仓库

起点：[Cyberchopin/CallGate_PreHackathon_Research](https://github.com/Cyberchopin/CallGate_PreHackathon_Research)，原始提交 `16c469ae78f22f06df757595b8b36edd9359086e`。原仓库只有 1 个提交，页面显示 0 star / 0 fork。

已有 README、MIT LICENSE、BACKLOG、比赛边界文档、一个安全功能 issue 模板，以及 9 份设计文档：架构、威胁模型、伦理与人因、信任信封、测试证据计划、用户研究、36 小时计划、演示与叙事、产品策略。没有应用源码、依赖清单、运行入口、音频接口、模型实现、数据集、测试或 CI。

| 可复用资产 | v2 如何利用 | 原有缺口 |
|---|---|---|
| ARCHITECTURE / THREAT_MODEL | 分离证据提取和可信策略，语音不授予身份 | 未实现进程/网络隔离、实际 enforcement |
| TRUST_ENVELOPE_SPEC | extra 字段拒绝、证据引用、状态与能力分离 | 是 draft，不是已有 SDK；本次只实现较小的 Transcript/RiskEvent 合同 |
| TEST_AND_EVIDENCE_PLAN | 负面案例、失败日志、诚实的分母与延迟 | 未有可运行 benchmark；补 ScamBench 开发骨架 |
| ETHICS / USER_RESEARCH | 不指责用户、已知渠道回拨、不自动通知家属 | 尚无用户访谈或可访问性实测证据 |
| DEMO / PRODUCT_STRATEGY | 保留“行动前介入”的故事 | 不应把未来能力当作已完成 demo |
| BACKLOG / HACKATHON_36H_PLAN | 划分里程碑与验收证据 | 从 LA Hacks 单场计划调整为可披露的复用基线 |

建议保留核心定位：识别对方希望你执行什么动作，并在高影响操作前要求独立核验。声学真假只是一种不确定证据。此次已经开始构建，不能继续声称仓库是纯研究或宣称代码将在未来比赛首次完成。

## 2. 开源项目比较

链接均指向原始仓库。优先级是对 CallGate 的建议，不是项目总体排名。许可证是仓库页面标记；权重、数据集及子组件可能另有条款，正式引入时逐项核对。

| 项目 | 页面 Star / Fork | 值得借鉴的部分 | 适合 CallGate 的用法与限制 |
|---|---:|---|---|
| [Pipecat](https://github.com/pipecat-ai/pipecat) | 15.4k / 2.7k | **架构**：流式 frame 管线、STT/TTS 适配、transport、打断 | P1 候选；AssemblyAI 已在集成清单。先维持 engine 独立，再包装 processor。BSD-2-Clause |
| [LiveKit Agents](https://github.com/livekit/agents) | 14.1k / 3.7k | **架构**：WebRTC、电话接入、任务生命周期、turn detection | 双方真实通话时优先考察；无需首阶段同时引入两套语音框架。Apache-2.0；模型许可证独立 |
| [pyannote.audio](https://github.com/pyannote/pyannote-audio) | 10.5k / 1.1k | **模型**：说话人分离、重叠语音、speaker embedding | 解决谁说了什么；不是身份认证。部分模型须接受 HF 条款及令牌。MIT 代码 |
| [Silero VAD](https://github.com/snakers4/silero-vad) | 10.2k / 847 | **模型/音频入口**：轻量 VAD、ONNX、8/16kHz | 可做端侧分段与静音控制；不识别诈骗或说话人身份。MIT |
| [AASIST](https://github.com/clovaai/aasist) | 279 / 78（检索缓存） | **模型**：官方反伪造模型实现 | 声学辅助基线，不能替代语义风险或授权。先做电话编解码/未见生成器评测。MIT |
| [ASVspoof 2021](https://github.com/asvspoof-challenge/2021) | 256 / 89 | **评测/数据集**：官方 baseline、EER、min t-DCF | 单独建立 acoustic track；数据在外部下载，不等于整个仓库统一许可。不是诈骗对话标签集 |
| [PhishIntention](https://github.com/lindsey98/PhishIntention) | 257 / 23（检索缓存） | **架构/模型思路**：从网页意图识别 phishing | 借鉴“冒充谁→索取什么→验证证据”结构；模型输入是网页，不能直接用于语音。页面标 CC0-1.0 |
| [PyOD](https://github.com/yzhao062/pyod) | 10.0k / 1.5k | **模型/评测**：异常检测基线、统一比较接口 | 后续通话/交易特征异常实验；不是开箱即用 voice scam engine。BSD-2-Clause |
| [NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails) | 7.1k / 825 | **架构**：可编程对话约束、独立 rails | 借鉴确定性控制和模型隔离；不能把内容过滤当作能力授权。选型时核对具体版本 LICENSE |
| [garak](https://github.com/NVIDIA/garak) | 9.1k / 1.3k | **评测**：probe、generator、detector、evaluator 分层 | 用于未来 LLM 提取器的注入和越权测试；不是语音诈骗训练模型。Apache-2.0 |
| [Promptfoo](https://github.com/promptfoo/promptfoo) | 24.9k / 2.3k | **评测**：声明式案例、模型对照、CI 回归 | 第二阶段比较提取器提示词/模型；不能用 LLM judge 代替全部确定性断言 |
| [AgentDojo](https://github.com/ethz-spylab/agentdojo) | 808 / 207 | **评测/数据集**：攻击成功与正常任务可用性并测 | 对 ScamBench 最值得借鉴：同时测阻止攻击和良性误介入。MIT |
| [Pipecat Voice UI Kit](https://github.com/pipecat-ai/voice-ui-kit) | 411 / 68（组织页面） | **前端交互**：会话连接、字幕/语音状态组件 | 后续只借小型状态卡与字幕组件；本阶段不搭装饰性仪表盘 |
| [CallShield](https://github.com/melbinkm/CallShield) | 2 / 0 | **直接竞品/交互**：实时音频、转录、增量 verdict、REST/WS | 产品形态最接近；体量小。其 25/25 自测是作者报告，未复现，不能当通用准确率。MIT |
| [LLM Guard](https://github.com/protectai/llm-guard) | 本次未取得计数 | **历史参考**：输入/输出扫描 | GitHub 元数据确认已 archived。保留分类设计参考，不作为新系统关键运行依赖 |

补充直接相关研究候选：[VoiceGuard](https://github.com/MohammadThabetHassan/VoiceGuard) 覆盖音频 deepfake/vishing 与解释性展示；[SSL_Anti-spoofing](https://github.com/TakHemlata/SSL_Anti-spoofing) 提供 wav2vec2 与反伪造训练路线；[Fraud-Call-Detection](https://github.com/Code-r4Life/Fraud-Call-Detection) 是多特征电话诈骗研究原型。本次未可靠取得三者实时 star/fork，故不把它们列为“高 star 成熟方案”。VoiceGuard 自报的 EER/边缘模型体积需要复现，SSL 仓库的旧依赖也增加迁移成本。

## 3. 具体采用决策

**现在采用设计，而非复制整个产品：** 小型 Python engine + FastAPI + 独立 AssemblyAI v3 adapter。流式传输不能绑定特定提取模型；提取器只能提交严格的证据事件，不能提交 verified/allow/token。规则提供无密钥、可复现起点，下一阶段用受限 LLM 处理委婉语义、引用和否定。Guardian 保持确定性。

**后续按需要接入：** 双向媒体选 Pipecat 或 LiveKit；说话人归属用 pyannote 或 provider diarization，但仍需可信渠道映射 caller/recipient；AASIST 加为可缺省声学传感器；Promptfoo/garak 加入 LLM 回归；AgentDojo 的“攻击与良性任务双指标”已用于本次 ScamBench 设计。

**不做：** 根据声纹或 deepfake score 授权、把情绪当犯罪证据、直接 fork 小型 demo 后宣传为 production、用几条合成台词的满分说明真实世界有效。

数据路线：当前原创 MIT 合成 dialogue 用于开发；下一步独立编写并冻结 held-out 场景，按诈骗家族/说话人拆分，再加入授权录音。声学实验使用 [ASVspoof 官方下载与协议](https://www.asvspoof.org/index2021.html)，与语义 ScamBench 分开报告。AgentDojo 数据用于提示注入研究，不能冒充电话诈骗标注数据。

## 4. 比赛顺序与复用

| 比赛 | 已核实信息 | CallGate 展示重点 |
|---|---|---|
| [AssemblyAI Voice Agent](https://lablab.ai/ai-hackathons/assemblyai-voice-agent-hackathon/live) | 官方 live 页面写 Sep 1–30, 2026；每位参与者使用 AssemblyAI；奖池由现金与 credits 构成 | 优先：真实 streaming STT、持续风险事件、及时 Guardian。当前 adapter 不是已验证的真实集成成绩 |
| [AI Infra Summit / lablab](https://lablab.ai/ai-hackathons/ai-infra-summit-hackathon) | 页面写线上 Sep 10–16，现场 Sep 15–17，现场 invitation-only | 紧接：可替换组件、超时/错误路径、延迟分解、可复现评测 |
| [AI Infra Summit 主站](https://www.ai-infra-summit.com/ai-infra-hackathon?azletter=S) | 主站描述 Sep 15–16 两日 sprint；赞助商各有 challenge，详情后续公布 | 与 lablab 日程口径不同；待具体 sponsor track 确定后增加适配，不能假定 AssemblyAI 满足全部赛道 |
| 后续 Devpost / Stanford / LA Hacks | 本次没有明确每场的官方具体活动 URL 和完整规则；Devpost 本身是平台 | 复用 engine/API/benchmark，按场次记录新增部分；不假设允许相同作品重复提交 |

实施顺序：① 本次核心 engine/接口/评测骨架；② 语义提取 + held-out case + AssemblyAI 真音频联调；③ 独立验证 + 模拟高影响工具的实际阻断；④ 故障、延迟、双向媒体验证；⑤ 最小可解释交互与参赛证据包。

当前代码已跑通本地测试和开发评测，但仍属于可测试基线。最需要优先补的是语义提取（本次已测出委婉语漏检及引用误报）以及真实 provider 延迟，而不是 UI。
