import Foundation

/// Reach firmware BLE protocol, version 1. Mirrors
/// WearableEmergencyAssistanceSystem lib/protocol/alert_protocol.h and
/// src/drivers/ble_link.cpp. Multi-byte fields are little-endian.
///
/// Device -> phone, Alert characteristic (notify), 6 bytes:
///   [0] version (1)  [1] 0x01 ALERT / 0x02 CANCEL  [2..3] alert_id
///   [4] alert type (1..3)  [5] attempt (1..n, 0 for CANCEL)
/// Device -> phone, Status characteristic (read/notify), 6 bytes:
///   [0] version  [1] state  [2..3] alert_id  [4] alert type  [5] attempts
/// Phone -> device, Ack characteristic (write), 4 bytes:
///   [0] version (1)  [1] 0x81  [2..3] alert_id (non-zero)
public enum ReachGATT {
    public static let deviceName = "WEA-Nano33"
    public static let service = "8f1d0001-6c2a-4b7e-9e3d-5a4c3b2a1f00"
    public static let alert = "8f1d0002-6c2a-4b7e-9e3d-5a4c3b2a1f00"
    public static let ack = "8f1d0003-6c2a-4b7e-9e3d-5a4c3b2a1f00"
    public static let status = "8f1d0004-6c2a-4b7e-9e3d-5a4c3b2a1f00"
}

public enum AlertKind: UInt8, Codable, Sendable {
    case emergency = 1  // D2
    case medical = 2    // D3
    case family = 3     // D4

    public var label: String {
        switch self {
        case .emergency: return "Emergency (D2)"
        case .medical: return "Medical (D3)"
        case .family: return "Family (D4)"
        }
    }
}

public enum DeviceMessage: Equatable, Sendable {
    case alert(alertID: UInt16, kind: AlertKind, attempt: UInt8)
    case cancel(alertID: UInt16, kind: AlertKind)
}

/// Firmware State enum order (lib/app/state_machine.h).
public enum DeviceState: UInt8, Sendable {
    case idle, pending, confirmed, alertSent, acknowledged, cancelled, retry, error

    public var label: String {
        switch self {
        case .idle: return "IDLE"
        case .pending: return "PENDING"
        case .confirmed: return "CONFIRMED"
        case .alertSent: return "ALERT_SENT"
        case .acknowledged: return "ACKNOWLEDGED"
        case .cancelled: return "CANCELLED"
        case .retry: return "RETRY"
        case .error: return "ERROR"
        }
    }
}

public struct DeviceStatus: Equatable, Sendable {
    public let state: DeviceState
    public let alertID: UInt16
    public let kindRaw: UInt8
    public let attempts: UInt8
}

public enum ProtocolError: Error, Equatable {
    case badLength(Int)
    case badVersion(UInt8)
    case badType(UInt8)
    case badAlertID
    case badAlertKind(UInt8)
    case badAttempt(UInt8)
    case badState(UInt8)
}

public enum AlertProtocol {
    public static let version: UInt8 = 1
    static let msgAlert: UInt8 = 0x01
    static let msgCancel: UInt8 = 0x02
    static let msgAck: UInt8 = 0x81

    public static func decodeAlertCharacteristic(_ data: Data) throws -> DeviceMessage {
        let b = [UInt8](data)
        guard b.count == 6 else { throw ProtocolError.badLength(b.count) }
        guard b[0] == version else { throw ProtocolError.badVersion(b[0]) }
        let id = UInt16(b[2]) | (UInt16(b[3]) << 8)
        guard id != 0 else { throw ProtocolError.badAlertID }
        guard let kind = AlertKind(rawValue: b[4]) else { throw ProtocolError.badAlertKind(b[4]) }
        switch b[1] {
        case msgAlert:
            guard b[5] >= 1 else { throw ProtocolError.badAttempt(b[5]) }
            return .alert(alertID: id, kind: kind, attempt: b[5])
        case msgCancel:
            return .cancel(alertID: id, kind: kind)
        default:
            throw ProtocolError.badType(b[1])
        }
    }

    public static func decodeStatus(_ data: Data) throws -> DeviceStatus {
        let b = [UInt8](data)
        guard b.count == 6 else { throw ProtocolError.badLength(b.count) }
        guard b[0] == version else { throw ProtocolError.badVersion(b[0]) }
        guard let state = DeviceState(rawValue: b[1]) else { throw ProtocolError.badState(b[1]) }
        return DeviceStatus(state: state, alertID: UInt16(b[2]) | (UInt16(b[3]) << 8),
                            kindRaw: b[4], attempts: b[5])
    }

    public static func encodeAck(alertID: UInt16) -> Data {
        precondition(alertID != 0, "alert_id 0 means no alert and can never be acknowledged")
        return Data([version, msgAck, UInt8(alertID & 0xFF), UInt8(alertID >> 8)])
    }
}
