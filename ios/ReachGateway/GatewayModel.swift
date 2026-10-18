import Foundation
import os

/// Alert pipeline: BLE notification -> persist stable event mapping -> BLE ACK
/// -> backend upload. BLE receipt, BLE ACK and backend receipt are tracked as
/// separate facts; none of them means a contact received or accepted help.
@MainActor
final class GatewayModel: ObservableObject {
    @Published private(set) var link: BLEGateway.LinkState = .bluetoothUnavailable("启动中")
    @Published private(set) var deviceStatus: DeviceStatus?
    @Published private(set) var events: [GatewayEvent] = []
    @Published private(set) var lastProblem: String?
    @Published private(set) var configured = ConfigStore.load() != nil

    /// Pending uploads older than this are not resumed automatically on launch.
    static let autoResumeAge: TimeInterval = 15 * 60

    private let log = Logger(subsystem: "ReachGateway", category: "gateway")
    private let ble = BLEGateway()
    private let ledger: EventLedger
    private let uploader = DeviceEventUploader()
    private var uploadTasks: [String: Task<Void, Never>] = [:]
    /// Event IDs whose ACK writes await a write response, in write order.
    private var pendingAcks: [String] = []

    init() {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        ledger = EventLedger(fileURL: dir.appendingPathComponent("reach-events.json"))
        events = ledger.events

        ble.onLinkState = { [weak self] state in self?.linkChanged(state) }
        ble.onAlertData = { [weak self] data, peripheral in self?.handleAlert(data, peripheralID: peripheral) }
        ble.onStatusData = { [weak self] data in self?.deviceStatus = try? AlertProtocol.decodeStatus(data) }
        ble.onAckWriteResult = { [weak self] error in self?.ackWritten(error: error) }
    }

    func start() {
        ble.start()
        resumeUploads(maxAge: Self.autoResumeAge)
    }

    // MARK: Configuration

    func saveConfig(baseURLText: String, deviceID: String, token: String) throws {
        try ConfigStore.save(baseURLText: baseURLText, deviceID: deviceID, token: token)
        configured = ConfigStore.load() != nil
        resumeUploads(maxAge: Self.autoResumeAge)
    }

    func clearConfig() {
        ConfigStore.clear()
        configured = false
    }

    // MARK: BLE

    private func linkChanged(_ state: BLEGateway.LinkState) {
        link = state
        if state == .reconnecting || state == .scanning {
            // Write responses for these can no longer arrive.
            for id in pendingAcks {
                record(id) { $0.bleAckError = "disconnected_before_write_response" }
            }
            pendingAcks.removeAll()
        }
    }

    private func handleAlert(_ data: Data, peripheralID: String) {
        let message: DeviceMessage
        do {
            message = try AlertProtocol.decodeAlertCharacteristic(data)
        } catch {
            lastProblem = "无法解析 Alert 包（\(error)），未 ACK"
            log.error("alert decode failed: \(String(describing: error), privacy: .public)")
            return
        }
        switch message {
        case let .alert(alertID, kind, attempt):
            // Every button type is uploaded as help_request (a request to the
            // trusted contact); the backend has no field for the type yet.
            let event: GatewayEvent
            let isNew: Bool
            do {
                (event, isNew) = try ledger.ingestAlert(peripheralID: peripheralID, alertID: alertID, kind: kind,
                                                        attempt: attempt, deviceID: ConfigStore.deviceID,
                                                        autoUpload: ConfigStore.load() != nil, now: Date())
            } catch {
                // Without a persisted mapping a retry could get a new event_id; let the device retry.
                lastProblem = "事件映射保存失败，未 ACK：\(error.localizedDescription)"
                return
            }
            events = ledger.events
            log.info("alert id=\(alertID) attempt=\(attempt) event=\(event.eventID, privacy: .public) new=\(isNew)")
            sendAck(for: event)
            startUpload(event.eventID)
        case let .cancel(alertID, _):
            if let event = try? ledger.noteDeviceCancel(peripheralID: peripheralID, alertID: alertID, now: Date()) {
                events = ledger.events
                log.info("device cancel event=\(event.eventID, privacy: .public)")
            }
        }
    }

    private func sendAck(for event: GatewayEvent) {
        if ble.writeAck(AlertProtocol.encodeAck(alertID: event.alertID)) {
            pendingAcks.append(event.eventID)
        } else {
            record(event.eventID) { $0.bleAckError = "ack_characteristic_unavailable" }
        }
    }

    private func ackWritten(error: Error?) {
        guard !pendingAcks.isEmpty else { return }
        let id = pendingAcks.removeFirst()
        record(id) {
            if let error {
                $0.bleAckError = "write_failed: \(error.localizedDescription)"
            } else {
                $0.bleAckConfirmedAt = Date()
                $0.bleAckError = nil
            }
        }
    }

    // MARK: Upload

    func retryUpload(_ eventID: String) {
        startUpload(eventID, manual: true)
    }

    private func resumeUploads(maxAge: TimeInterval) {
        for event in ledger.events where Date().timeIntervalSince(event.firstSeenAt) <= maxAge {
            switch event.upload {
            case .pending, .failed(_, _, true, _): startUpload(event.eventID)
            default: break
            }
        }
    }

    private func startUpload(_ eventID: String, manual: Bool = false) {
        guard uploadTasks[eventID] == nil, let event = ledger.event(eventID) else { return }
        switch event.upload {
        case .recorded: return
        case .localOnly where !manual: return
        default: break
        }
        uploadTasks[eventID] = Task { [weak self] in
            await self?.uploadLoop(eventID)
            self?.uploadTasks[eventID] = nil
        }
    }

    private func uploadLoop(_ eventID: String) async {
        var attempts = 0
        while attempts < DeviceEventUploader.maxAutomaticAttempts {
            guard let config = ConfigStore.load() else {
                record(eventID) { $0.upload = .failed(reason: "backend_not_configured", httpStatus: nil,
                                                      retryable: true, attempts: attempts) }
                return
            }
            // The event_id was minted with the device ID at receipt; a changed
            // setting must not silently re-label it.
            guard let event = ledger.event(eventID), event.deviceID == config.deviceID else {
                record(eventID) { $0.upload = .failed(reason: "device_id_changed", httpStatus: nil,
                                                      retryable: false, attempts: attempts) }
                return
            }
            attempts += 1
            record(eventID) { $0.upload = .pending(attempts: attempts) }
            let result = await uploader.upload(eventID: eventID, config: config)
            switch result {
            case let .recorded(status, duplicate, receivedAt):
                record(eventID) { $0.upload = .recorded(httpStatus: status, duplicate: duplicate,
                                                        receivedAt: receivedAt) }
                log.info("uploaded event=\(eventID, privacy: .public) http=\(status)")
                return
            case let .rejected(status, reason):
                record(eventID) { $0.upload = .failed(reason: reason, httpStatus: status, retryable: false,
                                                      attempts: attempts) }
                log.error("upload rejected event=\(eventID, privacy: .public) reason=\(reason, privacy: .public)")
                return
            case let .retryable(status, reason):
                record(eventID) { $0.upload = .failed(reason: reason, httpStatus: status, retryable: true,
                                                      attempts: attempts) }
                log.error("upload failed event=\(eventID, privacy: .public) reason=\(reason, privacy: .public)")
                try? await Task.sleep(nanoseconds: UInt64(DeviceEventUploader.backoff(afterAttempt: attempts)
                                                          * 1_000_000_000))
            }
        }
    }

    private func record(_ eventID: String, _ change: (inout GatewayEvent) -> Void) {
        do {
            try ledger.update(eventID, change)
        } catch {
            lastProblem = "事件状态保存失败：\(error.localizedDescription)"
        }
        events = ledger.events
    }
}
