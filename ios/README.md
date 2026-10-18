# Reach Gateway（最小 iOS 前台网关）

2026-10-17 活动期间新增（分支 `feat/reach-ios-gateway`，从 reachguard `main` 开出）。未改动任何后端代码或接口。

链路：Arduino 按钮长按 → BLE Alert notify → 本 App 解码并持久化事件映射 → BLE ACK 写回 → `POST /api/device-events`（`help_request`）。

按钮映射沿用固件：D2 Emergency、D3 Medical、D4 Family。后端目前没有类型字段，三种都上传为 `help_request`，含义都是**向可信联系人求助**；本 App 不联系急救或警方。类型只在 App 内显示，后端展示待接口对齐。首要验收目标是 D2 的真实链路。

## 协议来源（不是猜测）

全部取自固件仓库 `Iridium0317/WearableEmergencyAssistanceSystem`：`lib/protocol/alert_protocol.h`、`src/drivers/ble_link.cpp`、`lib/app/state_machine.h`（提交 629b442 起未变）。

| 项 | 值 |
|---|---|
| 广播名 | `WEA-Nano33`（App 按服务 UUID 扫描） |
| Service | `8f1d0001-6c2a-4b7e-9e3d-5a4c3b2a1f00` |
| Alert（notify） | `8f1d0002-…`，6 B：version 1, type 0x01 ALERT / 0x02 CANCEL, alert_id u16 LE, 类型 1 Emergency / 2 Medical / 3 Family, attempt |
| Ack（write） | `8f1d0003-…`，4 B：`01 81 <id lo> <id hi>`，App 用 write-with-response |
| Status（notify/read） | `8f1d0004-…`，6 B：version, state（IDLE…ERROR 共 8 个）, alert_id, 类型, attempts |

固件重试：最多 3 次，ACK 超时 5 s，退避 2 s；重试复用 alert_id；alert_id 只在 RAM，板子复位后从 1 重新计。

## 稳定 event_id 映射

`ReachCore/Sources/ReachCore/EventLedger.swift`。收到 ALERT 先写盘，再 ACK，再上传。

一条 ALERT **沿用**已有 event_id，当且仅当：同一块板（CoreBluetooth peripheral id）、同 alert_id、同类型、attempt 更大、该事件的 ACK 尚未被设备确认、距首次收到 ≤ 60 s。否则视为新报警，生成新 ID（形如 `nano-01-20261018T022105Z-a1-9ee5ae8d`）。

依据：固件接受 ACK 后不再发送该 alert_id，因此“ACK 已确认后又来同 ID”只能是复位后的新报警。拿不准时偏向“新事件”（后端可能多一条）而不是合并（可能丢一条报警）。HTTP 重试和手动重试一律沿用同一 event_id；映射在 App 重启后保留。

## 显示语义

每个事件分三行独立显示：**BLE 已接收**、**BLE ACK 已被设备接受 / 未确认**、**后端已记录（201 / 200 重复）/ 上传中 / 上传失败**。界面不出现“联系人已接手”之类表述；后端记录只表示服务器保存了求助意图。

- 收到报警时若**未配置后端**，事件照常 ACK、保存，但标记为“仅存本机”，之后配置好也**不会自动上传**（只能手动上传），避免 BLE 单独测试的按键变成真实求助请求。
- 取消沿用固件机制：长按松开后 3 s 内按任意键取消，设备不发包；发出后再按键，设备发 CANCEL。
- 设备 CANCEL 只在本地标注；设备凭证没有取消接口，所以后端记录不会被撤销，界面会写明。
- 失败分类：401/403/409/413/422 及响应内容不符 → 不自动重试；网络错误/超时/408/429/5xx → 退避 2,4,8,16,30… s，最多 8 次，之后可手动重试。启动时只自动续传 15 分钟内的事件。
- 状态查询**未接入**：help 状态 API 需要 owner/contact/dashboard 角色凭证，设备凭证无权读取。“联系人接手”只在 Dashboard 查看。

## 配置与存储

- Backend URL、Device ID（默认 `nano-01`）存 UserDefaults；设备凭证只存钥匙串（`WhenUnlockedThisDeviceOnly`），保存后界面不回显。
- URL 必须 https；http 仅允许 IP、`.local`、localhost（局域网联调）。
- 源码、日志均不含 URL 或凭证；日志只打 event_id、alert_id、HTTP 状态。
- 无 `UIBackgroundModes`：只在前台工作，前台时禁止自动锁屏。

## 构建与测试

```bash
cd ios/ReachCore && swift test          # 协议、映射、响应分类单测
# 可选：对真实后端做上传集成测试（值来自本地环境，不要写进文件）
REACH_TEST_BACKEND_URL=http://127.0.0.1:8780 REACH_TEST_DEVICE_TOKEN=... swift test --filter BackendIntegrationTests
open ios/ReachGateway.xcodeproj          # Signing & Capabilities 选自己的 Team；如 bundle id 冲突改 PRODUCT_BUNDLE_IDENTIFIER
```

## 真机操作步骤

1. 板子刷 `pio run -e nano33ble -t upload`，串口 115200 打开（看 `BLE`/`BLE_RX`/`SM` 日志）。
2. 后端负责人启动设备收件箱并提供 HTTPS 地址；设备凭证通过单独可信渠道交给你（`.test-tmp/device-live/device.token` 的内容）。
3. Xcode 选真机运行。首次弹窗允许蓝牙（局域网 http 联调时还会请求本地网络）。
4. 在“后端配置”填 URL、`nano-01`、凭证 → 保存。显示“已保存”。
5. 等 BLE 显示“已连接，已订阅 Alert”；串口应出现 `ev=connected` 和 `ev=subscribed char=alert`。
6. 长按 D2 ≥1.5 s 松开，3 s 内不碰任何按钮。
7. 期望：
   - App 新增事件，“BLE 已接收”“BLE ACK 已被设备接受”“后端已记录（HTTP 201）”。
   - 串口 `BLE_RX msg=ACK id=N`（N 是 App 上显示的 alert_id，不是 event_id），状态到 `ACKNOWLEDGED`。
   - 后端接收页（viewer 码）出现与 App 上**完全相同**的 event_id。
8. 把该 event_id 记在下面的验收表。
9. 可选补充：
   - 断网（飞行模式后再开蓝牙）再长按 D2：应显示“上传失败…自动重试中”，恢复网络后变“后端已记录”，后端仍只有一条该 event_id。
   - 长按后 3 s 内按任意键：不应产生事件（固件 PENDING 取消不发包）。
   - 已发送后再按键：事件出现 CANCEL 标注，后端记录不变。
   - 长按 D3/D4：同样 ACK 并上传 `help_request`，App 显示对应类型。
   - 未配置后端时长按：事件显示“仅存本机”，保存配置后不会自动上传。

## 验收记录（真机后填写）

| 日期 | iPhone / iOS | 固件提交 | event_id | HTTP | 串口 ACK id | 后端页面一致 |
|---|---|---|---|---|---|---|
| | | | | | | |

## 已验证 / 未验证（截至 2026-10-17）

已验证（本机）：
- `swift test`：17 项单测通过（协议编解码、映射规则、持久化、未配置时仅存本机、HTTP 响应分类、URL 校验），集成测试默认跳过。
- 上传集成测试：用本分支未改动的 `callgate/device_events.py` 在本机 127.0.0.1 起服务（临时合成凭证与临时 DB），依次得到 201 → 同 ID 200 duplicate → 错误凭证 401 → device_id 不符 403。测试事件 ID `nano-01-20261018T022105Z-a1-9ee5ae8d`（仅存在于该临时 DB，不是硬件事件）。
- `xcodebuild` iOS Simulator 与 iphoneos（未签名）构建均 BUILD SUCCEEDED，0 警告；产物 Info.plist 含蓝牙用途说明、无后台模式。

未验证：
- 真机运行、CoreBluetooth 连接/订阅/ACK 写入（模拟器无 BLE）。
- 与真实 Arduino 的端到端链路，真实硬件 event_id。
- 经 HTTPS 隧道上传到队友后端。
- 断线重连期间的重试映射、App 被杀后续传的真机表现。
- 联系人送达或接手（本 App 不涉及，也不声称）。

## 待确认问题

1. 固件 alert_id 复位后从 1 重计，App 只能用上面的启发式区分“重试”与“复位后新报警”。是否同意在下个协议版本加入每次上电随机的 boot id？（会改包格式，需固件负责人批准。）
2. 三种按钮类型何时、以何种字段在后端展示？目前统一为 `help_request`，后端看不出类型。
3. 设备 CANCEL 是否需要后端可见？现有设备凭证没有取消接口，需后端负责人决定是否增加。
