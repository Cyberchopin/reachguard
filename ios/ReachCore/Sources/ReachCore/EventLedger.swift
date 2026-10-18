import Foundation

/// Backend upload outcome for one event. Kept separate from BLE receipt so the
/// UI can never present one as the other.
public enum UploadState: Codable, Equatable, Sendable {
    /// Received while no backend was configured (e.g. BLE-only testing). Kept
    /// on the phone and never uploaded automatically, so test presses cannot
    /// later appear as real help requests; the operator may upload it by hand.
    case localOnly
    case pending(attempts: Int)
    /// 201 (`duplicate == false`) or 200 retry of the same event (`duplicate == true`).
    case recorded(httpStatus: Int, duplicate: Bool, receivedAt: String)
    case failed(reason: String, httpStatus: Int?, retryable: Bool, attempts: Int)
}

public struct GatewayEvent: Codable, Identifiable, Equatable, Sendable {
    public var id: String { eventID }
    public let eventID: String
    public let deviceID: String
    /// CoreBluetooth peripheral identifier (stable per phone for one board).
    public let peripheralID: String
    public let alertID: UInt16
    public let kind: AlertKind
    public let firstSeenAt: Date
    public var lastSeenAt: Date
    /// Highest ALERT attempt number received for this event.
    public var lastAttempt: UInt8
    public var notificationCount: Int
    /// Set when the ACK write completed with a GATT write response: the
    /// firmware's BLE stack accepted it. Says nothing about backend or contacts.
    public var bleAckConfirmedAt: Date?
    public var bleAckError: String?
    /// The device sent CANCEL for this alert. Not forwarded: the device
    /// credential has no cancel API on the backend.
    public var deviceCancelAt: Date?
    public var upload: UploadState
}

/// Stable mapping from firmware alerts to backend event IDs, persisted to disk
/// before the BLE ACK is written.
///
/// Firmware facts this relies on (WearableEmergencyAssistanceSystem):
/// - Every retry of one alarm reuses its alert_id; only `attempt` grows (1..3).
/// - alert_id lives in RAM and restarts at 1 after a board reset.
/// - Once the firmware has accepted an ACK for alert_id it stops sending it
///   (ACKNOWLEDGED, or ERROR if the ACK was late).
///
/// So an ALERT continues an existing event only if it is from the same board,
/// same alert_id and type, has a higher attempt number, that event's ACK has
/// not been confirmed, and it arrives within `retryWindow` of the first
/// notification. Anything else is a new alarm and gets a new event_id. When
/// uncertain this errs toward a new event (a duplicate backend record) rather
/// than merging two alarms (a lost one).
public final class EventLedger {
    /// Firmware worst case from attempt 1 to attempt 3 is about 14 s
    /// (5 s ack timeout + 2 s backoff, twice); this leaves room for reconnects.
    public static let retryWindow: TimeInterval = 60
    public static let maxStoredEvents = 200

    public private(set) var events: [GatewayEvent] = []
    private let fileURL: URL?
    private let makeEventID: (_ deviceID: String, _ alertID: UInt16, _ now: Date) -> String

    public init(fileURL: URL?,
                makeEventID: @escaping (String, UInt16, Date) -> String = EventLedger.defaultEventID) {
        self.fileURL = fileURL
        self.makeEventID = makeEventID
        if let fileURL, let data = try? Data(contentsOf: fileURL),
           let stored = try? JSONDecoder().decode([GatewayEvent].self, from: data) {
            events = stored
        }
    }

    /// e.g. `nano-01-20261017T201530Z-a7-3f9c21ab`. Only characters the
    /// backend accepts (letters, digits, `_ . : -`).
    public static func defaultEventID(deviceID: String, alertID: UInt16, now: Date) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(identifier: "UTC")
        f.dateFormat = "yyyyMMdd'T'HHmmss'Z'"
        let nonce = UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(8).lowercased()
        return "\(deviceID)-\(f.string(from: now))-a\(alertID)-\(nonce)"
    }

    public func event(_ eventID: String) -> GatewayEvent? {
        events.first { $0.eventID == eventID }
    }

    /// Records an ALERT notification and returns the event it belongs to.
    /// Persists before returning so the caller can ACK afterwards.
    public func ingestAlert(peripheralID: String, alertID: UInt16, kind: AlertKind, attempt: UInt8,
                            deviceID: String, autoUpload: Bool, now: Date) throws -> (GatewayEvent, isNew: Bool) {
        if let i = events.firstIndex(where: { $0.peripheralID == peripheralID && $0.alertID == alertID }),
           events[i].kind == kind,
           events[i].bleAckConfirmedAt == nil,
           attempt > events[i].lastAttempt,
           now.timeIntervalSince(events[i].firstSeenAt) <= Self.retryWindow {
            events[i].lastAttempt = attempt
            events[i].lastSeenAt = now
            events[i].notificationCount += 1
            try save()
            return (events[i], false)
        }
        let event = GatewayEvent(eventID: makeEventID(deviceID, alertID, now), deviceID: deviceID,
                                 peripheralID: peripheralID, alertID: alertID, kind: kind,
                                 firstSeenAt: now, lastSeenAt: now, lastAttempt: attempt,
                                 notificationCount: 1, bleAckConfirmedAt: nil, bleAckError: nil,
                                 deviceCancelAt: nil, upload: autoUpload ? .pending(attempts: 0) : .localOnly)
        events.insert(event, at: 0)  // newest first; lookups above find the latest match
        if events.count > Self.maxStoredEvents {
            events.removeLast(events.count - Self.maxStoredEvents)
        }
        try save()
        return (event, true)
    }

    /// Marks the most recent event for this board and alert_id as cancelled on the device.
    @discardableResult
    public func noteDeviceCancel(peripheralID: String, alertID: UInt16, now: Date) throws -> GatewayEvent? {
        guard let i = events.firstIndex(where: { $0.peripheralID == peripheralID && $0.alertID == alertID }) else {
            return nil
        }
        events[i].deviceCancelAt = now
        try save()
        return events[i]
    }

    public func update(_ eventID: String, _ change: (inout GatewayEvent) -> Void) throws {
        guard let i = events.firstIndex(where: { $0.eventID == eventID }) else { return }
        change(&events[i])
        try save()
    }

    private func save() throws {
        guard let fileURL else { return }
        let data = try JSONEncoder().encode(events)
        #if os(iOS)
        try data.write(to: fileURL, options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
        #else
        try data.write(to: fileURL, options: .atomic)
        #endif
    }
}
