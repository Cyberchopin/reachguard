# ReachGuard：现场英文演示入口

2026-10-17，CallGate × Reach 的展示层改造。

**Reach someone you trust. Before you act.**

本次新增品牌、英文文案、响应式布局和操作指引；没有新增身份验证、支付控制、通知送达或硬件证明能力。原 policy、挑战、签名、两分钟有效期、重放保护和事件幂等仍由已有服务执行。

## 当前准确入口

| 角色 | 地址 | 授权边界 |
|---|---|---|
| ReachGuard 主操作台 | http://127.0.0.1:8781/fusion | 本地 operator / participant 权限；不能批准 |
| 语音 / 文本请求端 | http://127.0.0.1:8781/ | 同一融合实例的原 participant 路径 |
| 独立联系人核验页 | http://127.0.0.1:8782/ | 独立 reviewer 权限；operator 权限无效 |

操作台顶部的 **Open request view** 和 **Open contact view** 打开上述实际本地入口，不携带 reviewer 凭证。已有授权标签页可继续使用；新浏览器标签页如没有角色授权，应在自己的 WSL 桌面终端运行：

```bash
.venv/bin/python -m scripts.open_fusion_page operator
.venv/bin/python -m scripts.open_fusion_page reviewer
# 需要独立语音/文本页时：
.venv/bin/python -m scripts.open_fusion_page participant
```

该本机 CLI 从权限受限的当前 runtime 角色文件打开正确链接，不打印实际值。operator 与 participant 属于已有发起方权限；reviewer 始终使用自己的文件与凭证。工具不是 HTTP 接口，不把 reviewer 凭证交给 operator 页面、设备 API 或公共页面。对 Windows/WSL 优先使用 PowerShell 从本地文件打开角色入口；没有桌面浏览器打开器时会提示失败。当前受测服务器环境没有实际启动 Windows GUI，桌面打开器仍需操作者在自己的终端验证。

当前准确端口已实际核对。工具会从私有角色文件解析地址，适用于 launcher 的端口回退；界面顶部的 contact 快捷入口针对本次已核对的 8782。若以后改端口或启动多联系人，先重新核对入口配置，不能默认任意旧标签页仍属于同一实例。

## 最短演示路径

1. 用 operator 启动命令打开主操作台；如已有授权入口，刷新页面加载新版静态资源。没有授权时可输入本机 operator access code 后 **Connect workspace**。
2. 打开 **Session setup**。按需 **Allow this test session**，提交虚构文本 **Analyze test text**，选择真实当前 session、设备和已登记联系人，设置模拟金额/目标，点 **Confirm session and action**。既有同意和绑定没有被本轮改造清除；已经有效则无需重做。
3. 让队友沿原设备 API 发送新事件。在 **Choose an event** 选择本次事件，点 **Request verification**。旧消费事件不能重复创建；新事件不会自动替换当前选中卡片。
4. 在本地 **One-time challenge** 区域查看码与剩余时间，通过另一条约定渠道告诉核验者。在独立 contact 页面点 **Check for a request**，核对金额/目标，输入码 **Confirm simulation** 或直接 **Deny this request**。
5. 回主操作台查看真实时间线和最终结果。成功明确显示 **Simulated action completed. No real payment was made.**

不要在 pending 期间重新提交证据或重置会话；新证据会使原请求失效。UI 禁用常见的误操作入口，但后端原失效规则仍是最终依据。拒绝、过期、内容改变或已使用时，不显示可用旧码，也不会扩大原两分钟期限或重新消费同一事件。

## 界面实际行为

- 海军蓝/暖白/石板灰，青绿色品牌强调、琥珀等待、红色拒绝/故障；系统字体回退，无外部字体或图片请求。
- 主区域按文本/证据、模拟操作、事件时间线组织；配置与原始数据渐进展开，原始状态名和 request_id 放入 **Developer details**。
- 文本区域默认是明确标注的未分析例句；不会把例句当作已有语音转录。主操作台展示当前会话真实证据类别和来源数量；实时语音原文仍在 request view，不伪造跨页转录同步。
- 连接指示基于 fusion API 实际读取；设备区域只说明收件箱读取情况，不显示伪造的 BLE 连接、联系人在线或送达状态。
- `Local test` 适用于约定测试 ID，以及操作者明确分类的已知本地人工事件 `-983168`（见本地人工核验记录）。其他接口接收事件标为 `Device event`，仅证明通过 HTTP 收件，不宣称来自 BLE 硬件。
- 事件选择固定；新到事件只更新列表，不自动跳卡、不自动滚动、不自动创建请求。
- 已请求卡片只有在当前 session、pending、原 expires_at 和连接状态均有效时才显示六位码。完成/失效/过期/断连隐藏码；断连后不得仅凭缓存状态继续操作。
- 核验页分别处理等待、已完成、拒绝、到期、成功的空响应、错误凭证和网络失败。两种决定同样可见，不自动批准；确认需要原码，拒绝不需要码。
- 所有真实操作仍经过原 API；没有增加可用外观的短信、支付、电话接通、硬件在线等按钮。
- 无新遥测端点，不增加转写、凭证、挑战码或交易内容的观测发送。原后端隐私过滤测试保持通过。

## 已执行的验证

- 完整 Python：**277 passed、3 skipped**，2 条既有 TestClient 弃用警告。
- Node 前端逻辑：**21 passed**；包含同意/麦克风撤回、过期与失效码、拒绝/成功、角色访问与英文错误区分。
- Chromium 真浏览器合成验收：**11 组行为检查通过，10 张截图，0 个 pageerror**。桌面 1440×1150，手机尺寸 390×844，开启 reduced motion。
- 覆盖等待、成功、拒绝、到期、断网、无效权限、空请求、事件选择保持、显式发起、键盘焦点、手机按钮高度/横向溢出、request view 的同意/联系人前提。
- 另做真实 API 的浏览器只读检查：operator 成功同步；reviewer 成功读取空请求；**0 个写请求，不截图真实数据**。
- 实际 HTTP：本地主操作台、request/reviewer HTML、原 8780 页面和现有 ngrok 根页均 200；公网设备 API 无授权 401；公网 `/fusion`、`/api/fusion`、`/api/review/pending` 均 404。
- 原设备服务仍 PID 2797；本地融合/reviewer 仍原 PID 5272/5271。ngrok 仍 `https://device.example.invalid` → `http://127.0.0.1:8780`。未重启服务、改设备凭证、改 API 格式、改收件箱或切换隧道。

截图来自实际运行的 HTML/CSS/JS，但 **所有 /api 请求均被合成测试夹具拦截**；每张图有 **UI PREVIEW · SYNTHETIC LOCAL TEST** 标识。不作为真实联系人响应、手机、BLE 或硬件证明。没有向队友的数据库插入截图测试事件。

本机截图与报告（Git 忽略的测试产物）：

- [桌面等待](../.test-tmp/reachguard-ui/operator-waiting-desktop.png)
- [桌面成功](../.test-tmp/reachguard-ui/operator-success-desktop.png)
- [桌面拒绝](../.test-tmp/reachguard-ui/operator-denied-desktop.png)
- [手机核验等待](../.test-tmp/reachguard-ui/reviewer-waiting-mobile.png)
- [手机核验拒绝](../.test-tmp/reachguard-ui/reviewer-denied-mobile.png)
- [手机核验过期](../.test-tmp/reachguard-ui/reviewer-expired-mobile.png)
- [浏览器报告](../.test-tmp/reachguard-ui/report.json)

## 复跑截图检查

可选 Playwright 安装在独立 `.test-tmp/ui-browser`，不改变项目生产依赖。当前环境 Chromium 缺少共享库、且无法交互 sudo；所需三个包仅下载/提取在独立目录，没有安装系统包。当前可复跑：

```bash
LD_LIBRARY_PATH="$PWD/.test-tmp/ui-browser/libs/usr/lib/x86_64-linux-gnu" \
PLAYWRIGHT_BROWSERS_PATH=.test-tmp/ui-browser/browsers \
.test-tmp/ui-browser/bin/python scripts/check_reachguard_ui.py
```

脚本 `scripts/check_reachguard_ui.py` 不读取真实角色文件；它只用公开测试字符串和合成数据，拦截所有 API 调用。不要将这些截图当成现场真实过程照片。

## 仍未验证

新的英文 UI 尚未在队友真实 iPhone Safari、实际 BLE 按钮链路或 Windows 桌面打开器中验证。Chromium 手机尺寸不等于 iPhone 真机测试。没有做正式无障碍审计、评委 30 秒理解度研究、独立真人身份登记或通知送达验证，也没有真实支付。

受保护的 8780 旧诊断页保持原样；本轮 ReachGuard 产品入口为本地 fusion/request/reviewer 页面。没有公开这些角色服务，没有推送、合并或部署。
