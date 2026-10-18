import Foundation
import XCTest
@testable import ReachCore

final class AlertProtocolTests: XCTestCase {
    func testDecodesAlertLittleEndian() throws {
        let msg = try AlertProtocol.decodeAlertCharacteristic(Data([1, 0x01, 0x34, 0x12, 1, 2]))
        XCTAssertEqual(msg, .alert(alertID: 0x1234, kind: .emergency, attempt: 2))
    }

    func testDecodesCancel() throws {
        let msg = try AlertProtocol.decodeAlertCharacteristic(Data([1, 0x02, 7, 0, 3, 0]))
        XCTAssertEqual(msg, .cancel(alertID: 7, kind: .family))
    }

    func testRejectsMalformedAlerts() {
        let cases: [(Data, ProtocolError)] = [
            (Data([1, 1, 1, 0, 1]), .badLength(5)),
            (Data([2, 1, 1, 0, 1, 1]), .badVersion(2)),
            (Data([1, 9, 1, 0, 1, 1]), .badType(9)),
            (Data([1, 1, 0, 0, 1, 1]), .badAlertID),
            (Data([1, 1, 1, 0, 4, 1]), .badAlertKind(4)),
            (Data([1, 1, 1, 0, 0, 1]), .badAlertKind(0)),
            (Data([1, 1, 1, 0, 1, 0]), .badAttempt(0)),
        ]
        for (data, expected) in cases {
            XCTAssertThrowsError(try AlertProtocol.decodeAlertCharacteristic(data)) {
                XCTAssertEqual($0 as? ProtocolError, expected)
            }
        }
    }

    func testEncodesAckMatchingFirmwareDecoder() {
        XCTAssertEqual([UInt8](AlertProtocol.encodeAck(alertID: 0x0201)), [1, 0x81, 0x01, 0x02])
    }

    func testDecodesStatus() throws {
        let s = try AlertProtocol.decodeStatus(Data([1, 7, 3, 0, 1, 3]))
        XCTAssertEqual(s.state, .error)
        XCTAssertEqual(s.alertID, 3)
        XCTAssertEqual(s.attempts, 3)
        XCTAssertThrowsError(try AlertProtocol.decodeStatus(Data([1, 8, 0, 0, 0, 0])))
    }
}

final class EventLedgerTests: XCTestCase {
    private var counter = 0
    private let t0 = Date(timeIntervalSince1970: 1_800_000_000)

    private func makeLedger(url: URL? = nil) -> EventLedger {
        EventLedger(fileURL: url) { device, alert, _ in
            self.counter += 1
            return "\(device)-a\(alert)-\(self.counter)"
        }
    }

    private func ingest(_ l: EventLedger, id: UInt16 = 1, kind: AlertKind = .emergency, attempt: UInt8,
                        at seconds: TimeInterval, board: String = "P1", autoUpload: Bool = true) throws -> (GatewayEvent, Bool) {
        let r = try l.ingestAlert(peripheralID: board, alertID: id, kind: kind, attempt: attempt,
                                  deviceID: "nano-01", autoUpload: autoUpload, now: t0.addingTimeInterval(seconds))
        return (r.0, r.isNew)
    }

    func testRetryOfUnackedAlertReusesEventID() throws {
        let l = makeLedger()
        let (a, newA) = try ingest(l, attempt: 1, at: 0)
        let (b, newB) = try ingest(l, attempt: 2, at: 7)
        let (c, newC) = try ingest(l, attempt: 3, at: 14)
        XCTAssertTrue(newA)
        XCTAssertFalse(newB)
        XCTAssertFalse(newC)
        XCTAssertEqual(a.eventID, b.eventID)
        XCTAssertEqual(a.eventID, c.eventID)
        XCTAssertEqual(c.notificationCount, 3)
        XCTAssertEqual(l.events.count, 1)
    }

    func testFirstSeenAttemptCanBeAboveOne() throws {
        // Attempt 1 may fail on the device (not yet subscribed); attempt 2 is still new to us.
        let l = makeLedger()
        let (a, isNew) = try ingest(l, attempt: 2, at: 0)
        XCTAssertTrue(isNew)
        XCTAssertEqual(a.lastAttempt, 2)
    }

    func testSameIDAfterConfirmedAckIsNewAlarm() throws {
        // Firmware stops sending an alert once it accepted the ACK, so the same
        // alert_id again means the board reset and counted from 1 again.
        let l = makeLedger()
        let (a, _) = try ingest(l, attempt: 1, at: 0)
        try l.update(a.eventID) { $0.bleAckConfirmedAt = self.t0 }
        let (b, isNew) = try ingest(l, attempt: 2, at: 5)
        XCTAssertTrue(isNew)
        XCTAssertNotEqual(a.eventID, b.eventID)
    }

    func testAttemptOneAgainIsNewAlarm() throws {
        let l = makeLedger()
        let (a, _) = try ingest(l, attempt: 1, at: 0)
        let (b, isNew) = try ingest(l, attempt: 1, at: 5)
        XCTAssertTrue(isNew)
        XCTAssertNotEqual(a.eventID, b.eventID)
    }

    func testDifferentTypeBoardOrStaleIsNewAlarm() throws {
        let l = makeLedger()
        let (a, _) = try ingest(l, attempt: 1, at: 0)
        XCTAssertNotEqual(a.eventID, try ingest(l, kind: .medical, attempt: 2, at: 1).0.eventID)
        XCTAssertNotEqual(a.eventID, try ingest(l, attempt: 2, at: 1, board: "P2").0.eventID)
        let l2 = makeLedger()
        let (x, _) = try ingest(l2, attempt: 1, at: 0)
        let (y, isNew) = try ingest(l2, attempt: 2, at: EventLedger.retryWindow + 1)
        XCTAssertTrue(isNew)
        XCTAssertNotEqual(x.eventID, y.eventID)
    }

    func testPersistsAndReloadsMapping() throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("ledger-\(UUID()).json")
        defer { try? FileManager.default.removeItem(at: url) }
        let l = makeLedger(url: url)
        let (a, _) = try ingest(l, attempt: 1, at: 0)
        try l.update(a.eventID) { $0.upload = .failed(reason: "network_error(-1009)", httpStatus: nil,
                                                       retryable: true, attempts: 1) }
        // App restarted before the ACK reached the board: the retry must map to the same event.
        let reloaded = makeLedger(url: url)
        let (b, isNew) = try ingest(reloaded, attempt: 2, at: 7)
        XCTAssertFalse(isNew)
        XCTAssertEqual(a.eventID, b.eventID)
        XCTAssertEqual(reloaded.event(a.eventID)?.upload,
                       .failed(reason: "network_error(-1009)", httpStatus: nil, retryable: true, attempts: 1))
    }

    func testUploadStateIsFixedAtReceipt() throws {
        // Unconfigured at receipt: stays local even when a retry arrives after configuration.
        let l = makeLedger()
        let (a, _) = try ingest(l, attempt: 1, at: 0, autoUpload: false)
        XCTAssertEqual(a.upload, .localOnly)
        let (b, isNew) = try ingest(l, attempt: 2, at: 7, autoUpload: true)
        XCTAssertFalse(isNew)
        XCTAssertEqual(b.upload, .localOnly)
        XCTAssertEqual(try ingest(l, kind: .medical, attempt: 1, at: 8).0.upload, .pending(attempts: 0))
    }

    func testCancelMarksLatestEvent() throws {
        let l = makeLedger()
        let (a, _) = try ingest(l, attempt: 1, at: 0)
        let cancelled = try l.noteDeviceCancel(peripheralID: "P1", alertID: 1, now: t0)
        XCTAssertEqual(cancelled?.eventID, a.eventID)
        XCTAssertNil(try l.noteDeviceCancel(peripheralID: "P1", alertID: 9, now: t0))
    }

    func testDefaultEventIDIsBackendValid() {
        let id = EventLedger.defaultEventID(deviceID: "nano-01", alertID: 65535, now: Date())
        XCTAssertTrue(BackendConfig.isValidIdentifier(id, maxLength: 128), id)
        XCTAssertTrue(id.hasPrefix("nano-01-"))
    }
}

final class UploaderTests: XCTestCase {
    private let config = BackendConfig(baseURL: URL(string: "https://example.invalid")!,
                                       deviceID: "nano-01", token: String(repeating: "x", count: 40))

    private func body(_ status: String, id: String = "e1") -> Data {
        try! JSONSerialization.data(withJSONObject: [
            "status": status, "intent_only": true,
            "event": ["event_id": id, "device_id": "nano-01", "event_type": "help_request",
                      "received_at": "2026-10-17T20:00:00+00:00"],
        ])
    }

    func testClassifiesResponses() {
        XCTAssertEqual(DeviceEventUploader.classify(status: 201, body: body("received"), eventID: "e1", config: config),
                       .recorded(httpStatus: 201, duplicate: false, receivedAt: "2026-10-17T20:00:00+00:00"))
        XCTAssertEqual(DeviceEventUploader.classify(status: 200, body: body("duplicate"), eventID: "e1", config: config),
                       .recorded(httpStatus: 200, duplicate: true, receivedAt: "2026-10-17T20:00:00+00:00"))
        XCTAssertEqual(DeviceEventUploader.classify(status: 201, body: body("received", id: "other"), eventID: "e1",
                                                    config: config),
                       .rejected(httpStatus: 201, reason: "unexpected_success_body"))
        XCTAssertEqual(DeviceEventUploader.classify(status: 401, body: Data(), eventID: "e1", config: config),
                       .rejected(httpStatus: 401, reason: "credential_invalid"))
        XCTAssertEqual(DeviceEventUploader.classify(status: 409, body: Data(), eventID: "e1", config: config),
                       .rejected(httpStatus: 409, reason: "event_id_conflict"))
        XCTAssertEqual(DeviceEventUploader.classify(status: 503, body: Data(), eventID: "e1", config: config),
                       .retryable(httpStatus: 503, reason: "server_unavailable"))
    }

    func testBaseURLValidation() {
        XCTAssertEqual(BackendConfig.parseBaseURL(" https://x.example/ ")?.absoluteString, "https://x.example")
        XCTAssertNotNil(BackendConfig.parseBaseURL("http://192.168.1.5:8780"))
        XCTAssertNotNil(BackendConfig.parseBaseURL("http://mac.local:8780"))
        XCTAssertNil(BackendConfig.parseBaseURL("http://x.example"))
        XCTAssertNil(BackendConfig.parseBaseURL("ftp://x.example"))
        XCTAssertNil(BackendConfig.parseBaseURL("https://x.example/?token=1"))
    }

    func testBackoff() {
        XCTAssertEqual(DeviceEventUploader.backoff(afterAttempt: 1), 2)
        XCTAssertEqual(DeviceEventUploader.backoff(afterAttempt: 4), 16)
        XCTAssertEqual(DeviceEventUploader.backoff(afterAttempt: 9), 30)
    }
}

/// Runs only when pointed at a real device-events backend, e.g. a local
/// `python -m scripts.start_device_events`. Values come from the environment.
final class BackendIntegrationTests: XCTestCase {
    func testUploadAgainstRealBackend() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let urlText = env["REACH_TEST_BACKEND_URL"], let token = env["REACH_TEST_DEVICE_TOKEN"],
              let url = BackendConfig.parseBaseURL(urlText) else {
            throw XCTSkip("REACH_TEST_BACKEND_URL / REACH_TEST_DEVICE_TOKEN not set")
        }
        let config = BackendConfig(baseURL: url, deviceID: "nano-01", token: token)
        let uploader = DeviceEventUploader()
        let id = EventLedger.defaultEventID(deviceID: "nano-01", alertID: 1, now: Date())
        print("integration event_id=\(id)")

        guard case .recorded(201, false, _) = await uploader.upload(eventID: id, config: config) else {
            return XCTFail("first upload not recorded as 201")
        }
        guard case .recorded(200, true, _) = await uploader.upload(eventID: id, config: config) else {
            return XCTFail("retry not recorded as 200 duplicate")
        }
        var wrong = config
        wrong.token = String(repeating: "w", count: 40)
        let denied = await uploader.upload(eventID: id, config: wrong)
        XCTAssertEqual(denied, .rejected(httpStatus: 401, reason: "credential_invalid"))
        var otherDevice = config
        otherDevice.deviceID = "nano-02"
        let mismatch = await uploader.upload(eventID: id, config: otherDevice)
        XCTAssertEqual(mismatch, .rejected(httpStatus: 403, reason: "credential_device_mismatch"))
    }
}
