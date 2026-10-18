# Reach iOS Gateway MVP：实际接口契约

核对日期：2026-10-17。第一阶段只上传三字段 `help_request`，优先验证实体按钮 → BLE → 前台 Swift Gateway → 后端。

## 第一阶段：已上线的上传接口

从本机 `.test-tmp/device-live/ngrok-base-url.txt` 获取当前 HTTPS origin，通过可信渠道交给开发者。App 在运行时配置 origin、`device_id` 和该设备的上传凭证。当前设备为 `nano-01`；不把实时域名或凭证写进源码。

```http
POST /api/device-events
Authorization: Bearer <device credential>
Content-Type: application/json

{"event_id":"nano-01-alarm-unique-001","device_id":"nano-01","event_type":"help_request"}
```

只允许以上三个字段。`event_id` 长度 1–128，`device_id` 长度 1–64；字符仅限 `A-Z a-z 0-9 _ . : -`。JSON 请求体最多 2048 字节。旧的 `verify_request` 仍被接受，第一阶段求助使用 `help_request`。

首次持久化返回 201：

```json
{"status":"received","event":{"event_id":"nano-01-alarm-unique-001","device_id":"nano-01","event_type":"help_request","received_at":"<server UTC ISO-8601>"},"intent_only":true}
```

| HTTP | Swift 处理 |
| --- | --- |
| 201 | 首次持久化成功。只显示后端已收到，不显示联系人已收到或已接受。 |
| 200 | 同一事件重试成功，`status` 为 `duplicate`，保留原始 `received_at`。 |
| 401 | 上传凭证缺失或无效；检查本机配置，不循环重试。 |
| 403 | 凭证不属于请求中的设备；检查设备配置。 |
| 409 | `event_id` 已用于另一设备或事件类型；报告 ID 冲突，不自动换 ID 重发同一警报。 |
| 413 | 超过体积上限。 |
| 422 | 字段、类型或 JSON 无效，包括多传 `alert_type`。 |
| 网络超时／连接失败／5xx | 结果可能不确定；退避后使用同一三字段载荷和同一 `event_id` 重试。 |

同一个实体警报必须在 BLE 重传、HTTP 重试及 App 恢复后继续使用原 `event_id`；只有新的警报才生成新 ID。该 ID 应由固件／Gateway 协议共同确定，本文不猜测 GATT、ACK 字节或帧格式。BLE ACK 只代表手机收到消息。

## 第二阶段：当前均未实现

| 能力 | 当前实际状态 | App 现在的处理 |
| --- | --- | --- |
| `alert_type` 上传字段 | 未实现；代码模型禁止额外字段，当前服务拒绝该字段 | 不发送 |
| 设备范围取消 | 未实现；没有设备凭证可用的取消 API | 不调用、不借用 owner 凭证 |
| 设备范围状态查询 | 未实现；没有设备凭证可用的求助状态 API | 不轮询求助角色接口 |

以上三项均不属于“已实现未上线”或“已上线验证”。未来路由、请求体、状态及设备授权语义尚未确定，本文不提供可调用示例。

已存在的 `/api/help-requests`、`/api/help-requests/{event_id}` 读取接口需要独立的 owner、contact 或 dashboard 凭证；响应接口仅限 contact，取消接口仅限 owner。它们用于浏览器角色页面，不属于 Gateway MVP 的设备契约。

## App 凭证边界

App 只持有所属设备的上传凭证，保存于 iOS Keychain，不进入 URL、日志、分析事件或源码。App 不持有 viewer、owner、contact、dashboard 凭证，也不从角色页面提取这些凭证。配置和数据库路径只供本机操作人员使用，不向 App 暴露。

上传成功不等于联系人通知、接受、到场或救援送达。实体按钮及 Swift Gateway 完整链路仍需双方现场验证。
