# UCLA 现场：独立设备意图收件箱

2026-10-17；本场新增。已有文本、AssemblyAI、联系人核验及模拟授权属于既有功能。
硬件侧按钮 → BLE → iPhone 由队友负责；本服务接收 iPhone 的 HTTP 请求，不直接实现 BLE。

## 本机启动（WSL）

在项目根目录，使用单独终端。以下交互仅在你自己的终端输入新建的设备专用凭证，勿复用 participant/reviewer 凭证；不要截图、提交或发进聊天。凭证至少 32 个 ASCII 非空白字符，两个凭证必须不同。服务不读取 `.env`、现有密钥文件，也不打印凭证。

```bash
read -r -s -p 'New nano-01 device token: ' DEVICE_TOKEN; echo
read -r -s -p 'New read-only viewer token: ' CALLGATE_DEVICE_VIEWER_TOKEN; echo
export CALLGATE_DEVICE_VIEWER_TOKEN
export CALLGATE_DEVICE_TOKENS="$(DEVICE_TOKEN="$DEVICE_TOKEN" .venv/bin/python -c 'import os,json; print(json.dumps({"nano-01":os.environ["DEVICE_TOKEN"]}))')"
unset DEVICE_TOKEN
.venv/bin/python -m scripts.start_device_events
```

打开 `http://127.0.0.1:8780/`，输入只读 viewer token，点连接，每两秒刷新最近 100 条。凭证仅保存在页面内存，不写入 URL 或浏览器存储；断开清除。静态页面外壳公开，事件数据必须通过 viewer Bearer 认证；设备凭证不能读事件。
服务只监听 WSL `127.0.0.1:8780`。默认 SQLite 文件 `device-events.sqlite3`（已被 gitignore 忽略），重启保留去重记录。可用 `CALLGATE_DEVICE_DB` 指定路径。勿运行多个不同配置的服务共享同一个 DB。

## iPhone 接口 / curl

`POST /api/device-events`，`Authorization: Bearer <device-token>`，`Content-Type: application/json`。
在 iPhone Shortcuts / 原生应用中设置同样的 URL、headers 和 JSON；设备凭证属于 iPhone HTTP 桥接端，并不证明请求来自真实 Arduino。

```bash
# BASE_URL 初次为 http://127.0.0.1:8780；远程联调改为 HTTPS 隧道地址。
# DEVICE_TOKEN 在调用端安全注入；勿把实际值写入脚本或提交。
curl --silent --show-error "$BASE_URL/api/device-events" \
  -H "Authorization: Bearer $DEVICE_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"event_id":"nano-01-unique-001","device_id":"nano-01","event_type":"verify_request"}'
```

| 字段 | 约束 |
|---|---|
| event_id | 1–128 字符，字母数字及 `_ . : -`；建议 UUID；重试必须沿用原 ID |
| device_id | 1–64 同上字符；必须匹配该凭证在服务启动时登记的设备 |
| event_type | 仅 `verify_request` 或 `help_request` |

不接受额外字段，不接受金额、付款批准、联系人选择或任意指令。JSON 请求体最多 2048 字节。
成功示例：

```json
{"status":"received","event":{"event_id":"nano-01-unique-001","device_id":"nano-01","event_type":"verify_request","received_at":"2026-10-17T20:00:00+00:00"},"intent_only":true}
```

| HTTP | 含义 / 调用方行为 |
|---|---|
| 201 | 首次持久化接收 |
| 200 | 相同 ID、设备、类型重试，`status=duplicate`；原时间不变 |
| 401 | 缺失、错误凭证或使用错误角色的凭证；不要盲目重试 |
| 403 | 凭证与 device_id 不匹配 |
| 409 | 全局 event_id 已被不同内容占用；检查调用端 ID 生成 |
| 413 / 422 | 请求过大 / JSON 或字段不合法 |

网络断开、超时或 5xx 可采用退避重试，沿用 event_id。收到 201/200 仅证明服务记录意图，不代表真人收到求助、身份核验完成或付款获准。
`GET /api/device-events` 需单独 viewer Bearer，返回最近 100 条（新到旧）。不开放 CORS、Swagger 或现有业务路由。

当前不自动通知联系人，不自动创建已有 workflow 会话。后续接入需增加可信本地适配层，由用户确认后选择已登记联系人，再走原核验流程；设备事件不得生成批准证明或执行付款。

## HTTPS 联调准备（尚未启动 / 部署）

使用 WSL 内的 cloudflared，只将固定的独立服务端口作为 origin。不要把 8765/8766/8767 或 Windows 测试服务配置成 origin。隧道通过 WSL 主动出站，不依赖手机访问校园局域网。

先确认本机页面和带凭证 POST 正常，再由操作者自行安装 cloudflared 并运行：

```bash
cloudflared tunnel --url http://127.0.0.1:8780
```

复制其生成的 `https://…trycloudflare.com` 地址作为 iPhone BASE_URL。这个命令会实际公开最小服务，因此本次工作没有执行它。临时入口由 Cloudflare 终止 HTTPS，应用的设备 / viewer Bearer 认证仍然必需；URL 本身不是凭证。不要打开 debug/请求体日志。没有设置 Cloudflare Access 登录，以免 iPhone API 请求被浏览器登录页阻断。

远程验收：无凭证 POST 得到 401；正确设备请求得到 201，再次发送得到 200；本机页面只出现一条；远程 GET 无 viewer 凭证得到 401；`/participant`、`/reviewer`、`/openapi.json` 得到 404。手机改用蜂窝网络可验证无局域网依赖。Ctrl+C 停止隧道后再停止服务，清除终端环境变量并轮换本次凭证。

官方说明：https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/ 。Quick Tunnel 是临时联调入口；本环境未安装 cloudflared，未验证校园出站策略或 iPhone 真机。

## 验证与边界

`.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_device_events.py`

覆盖设备/页面权限分离、错误设备、严格字段、未知授权事件拒绝、重启幂等、ID 冲突、并发重复、请求大小和路由隔离。
SQLite 去重随数据库保留；不要清库后仍期望防重放。当前没有速率限制、自动清理或联系人通知队列，适合受控短时联调。只显示最近 100 条不等于删除历史，停服务后由操作者按实际保留需求清理数据库。

本次结果：新增服务 10 项测试通过；其余回归（排除缺失 `hypothesis` 的 `tests/test_safety_properties.py`）255 passed、3 skipped；Node UI 测试通过，diff 检查通过。全量收集受缺失依赖阻塞，未擅自修改虚拟环境。测试客户端在沙箱外验证通过；未做真实 iPhone/隧道联调。

## 2026-10-17 真机联调执行状态（替代上述“尚未启动”状态）

用户明确授权后，已启动独立设备服务，实测仅监听 `127.0.0.1:8780`。cloudflared 官方二进制已安装到 `.test-tmp/device-live/cloudflared`，版本 `2026.10.1`；未安装系统服务，未读取已有 Cloudflare 账户配置。使用专用空配置，仅指向 `http://127.0.0.1:8780`，通过 HTTP/2 出站。

分配的临时地址：`https://device.example.invalid`。
**目前不可用**：公网无凭证 POST 返回 HTTP 530，尚未到达应用，不能视为认证拒绝验证通过。cloudflared 启动自检显示 TCP/UDP 7844 均失败，HTTP/2 连接 `198.41.192.107:7844` 超时；启动自检的两个官方区域 TCP 端点均报告不可达。因此公网有效事件、绑定、重复事件尚未验证。隧道进程保留自动重试；换网络后需重新检查地址及连通性。

本地 HTTP 实测已通过：无凭证 GET/POST 401；有效 verify/help 201；重复 200 且原记录不变；错误 device_id 403；冲突 ID 409；设备读取 401；viewer 读取 200 且去重后只一条；participant/reviewer/openapi/.env 路由均 404。测试写入的 `smoke-*` 为人工联调事件，不代表真实硬件触发。

本次专用凭证保存在 Git 忽略的 `.test-tmp/device-live/`（目录权限 700，凭证文件 600）：

- `device.token`：只交给负责 iPhone 桥接的队友，设备 ID 固定 `nano-01`。
- `viewer.token`：本机页面只读凭证，不交给硬件，不作为设备凭证使用。

实际值未写入文档、回复或日志。由操作者在本机查看并通过单独可信方式交接；不要上传整个 runtime 目录。入口 URL 不是凭证。

本次进程及本地停止工具保存在上述目录。停止隧道和服务：

```bash
.venv/bin/python .test-tmp/device-live/stop.py
```

该脚本先检查 PID 对应进程，再停止 tunnel 和 service，不会停止已有 participant/reviewer。只停止隧道可用：

```bash
kill -TERM "$(cat .test-tmp/device-live/tunnel.pid)"
```

换网络后，若原隧道仍在重试，直接验证；如已停止，可重新启动（会分配新 URL）：

```bash
.venv/bin/python .test-tmp/device-live/start_tunnel.py
```

脚本和凭证均为本机临时运行材料，不提交到 Git。公网检查工具 `.test-tmp/device-live/smoke.py` 从本机文件加载凭证，仅输出 HTTP 检查结果，可运行：

```bash
.venv/bin/python .test-tmp/device-live/smoke.py https://实际当前地址.trycloudflare.com
```

iPhone Shortcuts：使用“获取 URL 内容”，方法 POST，URL 为该 HTTPS 地址加 `/api/device-events`；设置 `Authorization: Bearer <通过单独方式收到的 device.token>` 和 `Content-Type: application/json`；JSON 字段 `event_id` 使用新 UUID、`device_id` 为 `nano-01`、`event_type` 为 `verify_request`（求助时 `help_request`）。网络重试沿用原 UUID。待公网验证通过后，切换手机到蜂窝网络，实际按硬件按钮并确认本地页面出现新记录，才算真机端到端完成。

依赖与回归已补齐：按 `requirements-safety.txt` 安装 `hypothesis==6.168.5` 和 `sortedcontainers==2.4.0`（使用 uv，现有 venv 无 pip）。性质测试 1000 组样例通过；性质 + 设备测试 11 passed；完整 Python 测试 256 passed、3 skipped、2 条现有测试客户端弃用警告。没有推送或合并，没有公开 participant/reviewer。

## ngrok 替代入口准备 — 2026-10-17

按用户新指令，仅停止 cloudflared PID 3341；保留设备服务 PID 2797、127.0.0.1:8780、原凭证和数据库。没有运行 `stop.py`。电脑继续使用校园网络。

官方安装与网络说明已核对：
- https://ngrok.com/download/linux （需要 ngrok 账号 / authtoken）
- https://ngrok.com/docs/gateway/agent/connectivity （主连接 `connect.ngrok-agent.com:443`；证书吊销检查 `crl.ngrok-agent.com:80`）

使用官方独立 Linux amd64 二进制，安装到 `.test-tmp/device-live/ngrok`，版本 3.39.11。无凭证、限时网络诊断通过：DNS/TCP/TLS/隧道协议全部 OK，区域 us-cal-1，报告延迟约 47ms。诊断已退出，未在后台留下网络重试。

**当前等待操作者配置账号，尚无可用 ngrok HTTPS 请求地址，也没有宣称公网业务验证通过。**

1. 操作者自行注册 / 登录 https://dashboard.ngrok.com/get-started/your-authtoken 。不要发送 token 到聊天。
2. 在项目 WSL 终端运行：

   ```bash
   .venv/bin/python .test-tmp/device-live/configure_ngrok.py
   ```

   在隐藏提示中输入 authtoken。工具使用权限 600 新建本次专用 `.test-tmp/device-live/ngrok.yml`，不读取或修改默认账户配置，不显示实际值。配置关闭请求内容检查和远程管理，管理接口仅监听 127.0.0.1:4040。不需要 ngrok API key，也不要把设备 Bearer 当作 ngrok authtoken。
3. 告诉协作助手“已配置”，随后启动工具：

   ```bash
   .venv/bin/python .test-tmp/device-live/start_ngrok.py
   ```

   只启动 `ngrok http http://127.0.0.1:8780`，只加载本次专用配置，禁用 HTTP introspection。工具检查实际 upstream；35 次短轮询仍无入口即停止本次 ngrok 进程，不留下持续重试。启动器不读取 authtoken；ngrok 正常加载自己的配置。输出地址保存于 `ngrok-base-url.txt`。
4. 公网验收工具：

   ```bash
   .venv/bin/python .test-tmp/device-live/ngrok_smoke.py https://实际ngrok地址
   ```

   检查无凭证 401、有效事件 201、重复 200、device_id 不匹配 403、冲突 409、页面读取权限与隔离路由。使用独立 `ngrok-check-<UUID>` 事件 ID；finally 只移除本轮两个测试 ID，保留既有数据和手机事件。测试结果单独写入 `ngrok-public-smoke.json`，不会使用手机演示 ID。验证失败不得将入口交作“已验证可用”；网络失败后停止 ngrok，记录原因。

公网验收通过后，队友使用 iPhone Shortcuts “获取 URL 内容”：
- URL：实际 ngrok HTTPS 地址加 `/api/device-events`。
- 方法 POST，Header `Authorization: Bearer <单独交接的 device.token>`、`Content-Type: application/json`；可增加 `ngrok-skip-browser-warning: 1` 避免免费入口浏览器提示页。
- JSON：`event_id` 为新 UUID，`device_id` 为 `nano-01`，`event_type` 为 `verify_request` 或 `help_request`。
- 每次真实按钮事件新建 UUID；网络重试沿用 UUID。收到 201/200 后检查本机页面，不能将“已收件”表述为核验成功或付款获准。

仅停止 ngrok（不运行会停止设备服务的 `stop.py`）：

```bash
kill -TERM "$(cat .test-tmp/device-live/ngrok.pid)"
```

运行前应核对 PID 仍属于本次 ngrok；8780 服务继续保留。不公开 participant/reviewer，不推送或合并。

## ngrok 公网验证已通过 — 2026-10-17

操作者本机配置 authtoken 后，已启动且核对 upstream 严格为 `http://127.0.0.1:8780`。
当前 HTTPS 地址：**https://device.example.invalid**。
完整请求 URL：`https://device.example.invalid/api/device-events`。

公网实际 HTTP 检查全部通过：无凭证 GET/POST 401、verify/help 首次 201、重复 200 且原时间不变、device_id 不匹配 403、相同 ID 不同内容 409、设备读事件 401、viewer 读取 200 且去重后单条。`/participant`、`/reviewer`、`/openapi.json`、`/.env` 均 404，页面外壳 200。本轮 `ngrok-check-<UUID>` 记录已清理，保留原凭证、数据库和既有记录。状态取代上节“等待账号配置”；没有读取或打印 authtoken。

队友手机操作：
1. 通过单独方式取得 `.test-tmp/device-live/device.token` 对应的设备凭证，勿使用 ngrok authtoken 或 viewer.token。
2. iPhone Shortcuts 新建快捷指令，先生成 UUID，再使用“获取 URL 内容”。
3. URL 使用上述完整请求 URL；方法 POST。
4. Headers：`Authorization: Bearer <设备凭证>`、`Content-Type: application/json`、`ngrok-skip-browser-warning: 1`。
5. 请求体选择 JSON：`event_id` 填 UUID、`device_id` 填 `nano-01`、`event_type` 填 `verify_request`（求助按钮填 `help_request`）。每个新按钮事件一个 UUID，失败重试沿用原 UUID。
6. 服务响应 `status=received` 或 `duplicate`、`intent_only=true`。本机页面应显示事件；这个结果只表示意图被记录，尚未自动通知联系人或发起已有核验流程。

本机展示页：在运行 WSL 的同一台 Windows 电脑浏览器打开 **http://127.0.0.1:8780/**，输入本机 `.test-tmp/device-live/viewer.token` 对应的只读凭证，点击“连接 / 刷新”；每两秒刷新最近 100 条。如果 Windows localhost 转发不可用，可在同机打开当前 ngrok HTTPS 根地址，使用相同 viewer 凭证；无需开放 0.0.0.0 或 participant/reviewer 端口。

当前隧道保留运行。只停止 ngrok：`kill -TERM "$(cat .test-tmp/device-live/ngrok.pid)"`（先核对 PID 仍属于本次 ngrok），8780 服务继续保留；不要运行同时停止服务的 stop.py。手机真机/BLE 按钮尚需队友实际操作验收。没有推送或合并。

## 展示页地址复核 — 2026-10-17

操作者报告 Windows 浏览器访问 `http://127.0.0.1:8780/` 得到 404。重新检查：PID 2797 的命令为本仓库 `.venv/bin/python -m scripts.start_device_events`，工作目录为当前仓库；WSL 监听地址仍为 127.0.0.1:8780。实现包含 `GET /` HTML 展示页、`GET /api/device-events` viewer 只读接口及 `POST /api/device-events` 设备接收接口。ngrok 管理 API 核实 upstream 仍严格为 `http://127.0.0.1:8780`。

实测 WSL HTTP 根页和 `https://device.example.invalid/` 根页均返回 HTTP 200、`Content-Type: text/html; charset=utf-8`，内容包含“CallGate 设备事件”。两个入口的事件读取均为 viewer 200、device 401。没有重启、修改凭证或数据库。

**当前建议 Windows 浏览器打开 https://device.example.invalid/ ，不要附加 `/api/device-events`。** 如果 ngrok 显示免费入口提示，点击 Visit Site 后进入“设备事件收件箱”。在“只读页面凭证”密码框粘贴本机 `.test-tmp/device-live/viewer.token` 的内容（只填原始凭证，不加 `Bearer `），点击“连接 / 刷新”。HTTP 测试通过不代表已验证该电脑的 Windows 浏览器与 WSL localhost 转发；该 Windows 404 的具体来源尚未定位，不将其归因于确定的端口冲突。接口 URL 与页面 URL 不同。
