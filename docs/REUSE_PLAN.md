# CallGate 开源整合清单

本轮结果：14 个上游仓库已经本地克隆并固定提交，见 `upstreams.json`。这不是已完成 14 个云端 Fork，也不是已集成 14 套功能。GitHub 连接器确认账号是 Cyberchopin；但 CLI 登录无效、浏览器要求登录，且连接器没有 Fork 方法。`scripts/fork_upstreams.py` 已准备好，登录后可以创建并逐个验证 Fork，不会覆盖同名独立仓库。

## 已经真正复用

1. **Silero VAD 原版模型**：复制未经修改的 16kHz ONNX 模型及 MIT 许可证，记录 SHA256 并在加载时核对。本地 CPU 推理；每个会话有独立状态。接入音频 WebSocket，输出说话活动，而不删掉静音、打断 STT 或把 VAD 当诈骗分数。
2. **Pipecat 1.8.1 真正的 frame/pipeline API**：CallGateProcessor 放在 STT 后，利用 AssemblyAI Turn 元数据处理修订，输出 RiskDecisionFrame。真实 Pipecat 管线回放测试确认临时转录→最终转录→去重，并且原始文本不流向下游。它是可接入 Pipecat 的组件；当前麦克风页面仍用原本已验证的 AssemblyAI adapter，没有声称已整体迁移到 Pipecat transport。

安装隔离环境：`python -m venv C:/短路径/cg-int`，然后用其中的 Python 安装 `requirements-integrations-lock.txt` 和 `pip install --no-deps -e .`。Windows 环境路径过长可能导致 ONNX Runtime 安装失败；本机测试环境在 `C:/Users/wangs/Documents/Codex/work/cg-int`，不会替换原来的基础环境。`CALLGATE_VAD=silero` 启用语音活动传感器；未配置时原有流程保持可用。

## 每个项目的亮点、接法和边界

下表中的“缺口”是针对 CallGate 目标的适配缺口，不能理解成我们已审计证明整个上游不存在某项功能。没有复现的论文/README 准确率不算 CallGate 的成绩。

| 上游 | 最有价值的现成能力 | 当前接入方式 | 对 CallGate 仍有的缺口 |
|---|---|---|---|
| Pipecat | frame 管线、语音服务适配、打断和生命周期 | 已实现并测试风险 processor，固定 PyPI 1.8.1 | 还需真实 Pipecat 音频 transport 联调、时延/断线评测 |
| Silero VAD | 轻量本地语音活动识别 | 原模型已接入音频接口 | 不知道说话者是谁，不检测诈骗/克隆 |
| LiveKit Agents | WebRTC、电话接入、远程参与者管理 | 固定源码，作为正式双向通话候选 | 要解决渠道角色映射及部署；不与 Pipecat 重复堆叠 transport |
| pyannote.audio | diarization、重叠语音与 embedding | 固定源码，待独立说话人评测 | 模型使用条款/令牌、性能；speaker label 不等于真实身份 |
| AASIST | 官方音频反伪造研究实现 | 固定源码、检查 LICENSE/NOTICE，暂不放入运行时 | 权重、依赖、电话噪声/未见生成器验证；部分附带评测代码非商业许可 |
| ASVspoof 2021 | 标准语料协议、声学基线和评价方法 | 独立研究 checkout | 不是诈骗对话数据；数据与代码许可证须分开处理 |
| PhishIntention | 同时看品牌冒充和索取凭证意图 | 复用概念，源码待网页链接检测模块使用 | 输入是网页截图/HTML，不能直接喂通话文本 |
| PyOD | 多种异常检测模型与统一接口 | 固定源码，后续行为特征实验 | 需要真实特征/标签；没有通用诈骗对话语义 |
| NeMo Guardrails | 可配置对话约束 | 固定源码，评估后续语义提取约束 | 仍需我们自己的独立核验与能力网关 |
| garak | 多种攻击 probe、模型漏洞扫描 | 固定源码，待接入真实语义模型时运行 | 目前规则基线没有 LLM，不能虚报 LLM 红队已通过 |
| Promptfoo | 声明式模型对照、回归和报告 | 固定源码，后续替换提取模型时使用 | 需要确定性断言和独立标注；不能只靠另一个模型打分 |
| AgentDojo | 正常任务与攻击成功分开评测 | 固定源码，采纳双指标设计 | 当前未运行其完整代理 benchmark；不能把它的任务当电话语料 |
| Voice UI Kit | 会话状态、字幕和通话组件 | 固定源码，正式 React 界面候选 | 当前是简单本地测试页，不为了用组件先重写 UI |
| CallShield | 音频/文本双通道与增量风险交互 | 固定源码、检查文本分析器和 prompts | 检查到文本模型请求最长 timeout 120s，提示与 transcript 拼接；不能直接当低延迟、隔离的安全边界 |

源码定位：Pipecat `src/pipecat/services/assemblyai/stt.py`、`frames/frames.py`；Silero `src/silero_vad/utils_vad.py`；AASIST `NOTICE`；CallShield `backend/services/text_analyzer.py`、`backend/prompts/templates.py`。每个 checkout 的确切 commit 在 manifest 中，可构造永久 GitHub blob 链接。

## 我们优先解决的产品问题

1. **委婉表达、引用、否定与跨句意图**：现有规则仍有引用误报。下一步是带证据范围的受限语义提取，不是继续无限增加关键词。
2. **从检测到行动前保护**：目前 Guardian 是提示。需要独立核验、一次性授权和模拟高影响操作的真实拒绝路径，不能用“看起来像本人”放行。
3. **谁在要求谁做什么**：双向通话中区分来电方的要求和接听者的复述；speaker embedding 不能授予身份。
4. **可解释的不确定性**：音质差、断线、模型缺席、语言不支持时明确未知；声音合成不代表诈骗，真人声音也不代表安全。
5. **可复现的真实性能**：独立 held-out 对话、噪声/编解码、多语言、首次危险请求到提醒的时延。当前合成样例和用户测试不是泛化证明。

## 完成顺序

先用这两项通过测试的复用组件建立接口边界；然后选择一个受限语义提取模型并完善 ScamBench；再加入独立核验和模拟工具网关。最后根据双向通话需求选择 Pipecat/LiveKit transport、说话人传感器和最小前端。所有上游代码/模型保持归属与版本记录，参赛披露区分现成组件和本队新增能力。

已归档的 LLM Guard 和本轮未验证的其他小型候选不进入运行依赖。“功能更多”不等于“安全更完整”；每个运行组件必须有输入合同、失败行为和实际测试。

## 本轮验证结果（2026-09-08）

- 集成环境完整测试：39 passed；有 3 条上游弃用提示，未影响运行。
- 真实本地 WebSocket → AssemblyAI → CallGate，并启用 Silero：106 条语音活动观测，检测到合成语音，状态依次进入 CHALLENGED、COOLING_OFF，正常完成。记录在 `scambench/integrated-live-smoke.json`。
- 已重启 localhost:8765 服务并启用 Silero。浏览器刷新后加载新提示。
- 这些是功能与链路测试，不是实际诈骗识别准确率，也不是已完成电话网络部署。
