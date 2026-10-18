import SwiftUI

struct ContentView: View {
    @EnvironmentObject var model: GatewayModel
    @State private var urlText = ConfigStore.baseURLText
    @State private var deviceID = ConfigStore.deviceID
    @State private var token = ""
    @State private var configMessage: String?

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text("三个按钮目前都作为“向可信联系人求助”上传（help_request），本 App 不会联系急救或警方。")
                        .font(.footnote)
                    Text("请保持本 App 在前台并亮屏。BLE ACK 只表示手机收到；“后端已记录”只表示服务器保存了求助意图。两者都不代表联系人已收到或接手。")
                        .font(.footnote)
                }
                Section("BLE") {
                    LabeledContent("连接", value: linkText)
                    if let s = model.deviceStatus {
                        LabeledContent("设备状态", value: "\(s.state.label) · alert_id \(s.alertID) · 第 \(s.attempts) 次")
                    }
                    if let p = model.lastProblem {
                        Text(p).font(.footnote).foregroundStyle(.orange)
                    }
                }
                Section("后端配置") {
                    TextField("Backend URL（https://…）", text: $urlText)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
                    TextField("Device ID", text: $deviceID)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    SecureField(ConfigStore.hasToken ? "设备凭证已存钥匙串（留空保持不变）" : "设备凭证", text: $token)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    Button("保存") { save() }
                    Button("清除配置", role: .destructive) {
                        model.clearConfig()
                        urlText = ""
                        token = ""
                        configMessage = "已清除"
                    }
                    if let m = configMessage {
                        Text(m).font(.footnote)
                    }
                    if !model.configured {
                        Text("未配置：收到的报警会 BLE ACK 并只保存在本机；之后配置好也不会自动上传。").font(.footnote).foregroundStyle(.orange)
                    }
                }
                Section("事件（新到旧）") {
                    if model.events.isEmpty {
                        Text("尚无事件。长按 D2 / D3 / D4 1.5 s 松开，3 s 内按任意键可取消，否则发送。").font(.footnote)
                    }
                    ForEach(model.events) { EventRow(event: $0) }
                }
            }
            .navigationTitle("Reach Gateway")
        }
    }

    private var linkText: String {
        switch model.link {
        case .bluetoothUnavailable(let why): return why
        case .scanning: return "扫描 \(ReachGATT.deviceName)…"
        case .connecting: return "连接中…"
        case .discovering: return "发现服务…"
        case .ready: return "已连接，已订阅 Alert"
        case .reconnecting: return "已断开，等待重连…"
        }
    }

    private func save() {
        do {
            try model.saveConfig(baseURLText: urlText, deviceID: deviceID, token: token)
            token = ""
            configMessage = model.configured ? "已保存" : "已保存 URL；仍缺设备凭证"
        } catch ConfigStore.SaveError.invalidURL {
            configMessage = "URL 无效：需 https，或局域网 IP / .local 的 http"
        } catch ConfigStore.SaveError.invalidDeviceID {
            configMessage = "Device ID 只允许字母、数字及 _ . : -（≤64）"
        } catch {
            configMessage = "保存失败：\(error)"
        }
    }
}

struct EventRow: View {
    @EnvironmentObject var model: GatewayModel
    let event: GatewayEvent

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(event.eventID).font(.caption.monospaced()).textSelection(.enabled)
            Text("\(event.kind.label) · alert_id \(event.alertID) · 最高 attempt \(event.lastAttempt) · 通知 \(event.notificationCount) 次")
                .font(.caption)
            Label("BLE 已接收 \(event.firstSeenAt.formatted(date: .omitted, time: .standard))",
                  systemImage: "antenna.radiowaves.left.and.right")
            ackLine
            uploadLine
            if let t = event.deviceCancelAt {
                Label("设备于 \(t.formatted(date: .omitted, time: .standard)) 发出 CANCEL；后端记录未撤销（设备凭证无取消接口）",
                      systemImage: "xmark.circle").foregroundStyle(.orange)
            }
        }
        .font(.footnote)
    }

    @ViewBuilder private var ackLine: some View {
        if event.bleAckConfirmedAt != nil {
            Label("BLE ACK 已被设备接受", systemImage: "checkmark.circle")
        } else if let e = event.bleAckError {
            Label("BLE ACK 未确认：\(e)", systemImage: "exclamationmark.triangle").foregroundStyle(.orange)
        } else {
            Label("BLE ACK 发送中", systemImage: "clock")
        }
    }

    @ViewBuilder private var uploadLine: some View {
        switch event.upload {
        case .localOnly:
            VStack(alignment: .leading) {
                Label("未配置后端时收到：仅存本机，不会自动上传", systemImage: "iphone")
                    .foregroundStyle(.secondary)
                Button("手动上传（同一 event_id）") { model.retryUpload(event.eventID) }
                    .buttonStyle(.bordered)
            }
        case .pending(let n):
            Label("上传中（第 \(n) 次）", systemImage: "arrow.up.circle")
        case let .recorded(status, duplicate, receivedAt):
            Label("后端已记录（HTTP \(status)\(duplicate ? "，重复提交" : "")）received_at \(receivedAt)",
                  systemImage: "tray.and.arrow.down").foregroundStyle(.green)
        case let .failed(reason, status, retryable, attempts):
            VStack(alignment: .leading) {
                Label("上传失败：\(reason)\(status.map { " HTTP \($0)" } ?? "") · \(attempts) 次\(retryable ? "，自动重试中" : "")",
                      systemImage: "xmark.octagon").foregroundStyle(.red)
                Button("用同一 event_id 重试") { model.retryUpload(event.eventID) }
                    .buttonStyle(.bordered)
            }
        }
    }
}
