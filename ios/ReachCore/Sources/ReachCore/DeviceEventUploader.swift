import Foundation

/// Runtime backend settings. Never compiled in; supplied by the operator.
public struct BackendConfig: Equatable, Sendable {
    public var baseURL: URL
    public var deviceID: String
    public var token: String

    public init(baseURL: URL, deviceID: String, token: String) {
        self.baseURL = baseURL
        self.deviceID = deviceID
        self.token = token
    }

    /// Accepts https, or http only to an IP literal / `.local` / localhost for
    /// LAN testing. Returns nil for anything else.
    public static func parseBaseURL(_ text: String) -> URL? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard var comps = URLComponents(string: trimmed), let host = comps.host, !host.isEmpty,
              comps.query == nil, comps.fragment == nil, comps.user == nil else { return nil }
        switch comps.scheme?.lowercased() {
        case "https": break
        case "http":
            let local = host == "localhost" || host.hasSuffix(".local")
                || host.allSatisfy { $0.isNumber || $0 == "." } || host.contains(":")
            guard local else { return nil }
        default: return nil
        }
        while comps.path.hasSuffix("/") { comps.path.removeLast() }
        return comps.url
    }

    /// Same rule as the backend's DeviceEvent model.
    public static func isValidIdentifier(_ s: String, maxLength: Int) -> Bool {
        !s.isEmpty && s.count <= maxLength && s.unicodeScalars.allSatisfy {
            CharacterSet.alphanumerics.contains($0) && $0.isASCII || "_.:-".unicodeScalars.contains($0)
        }
    }
}

public enum UploadResult: Equatable, Sendable {
    case recorded(httpStatus: Int, duplicate: Bool, receivedAt: String)
    /// Do not retry automatically (401/403/409/413/422, or a response that
    /// does not match the request).
    case rejected(httpStatus: Int?, reason: String)
    /// Network error, timeout or 5xx: retry with the same event_id.
    case retryable(httpStatus: Int?, reason: String)
}

/// POST /api/device-events per docs/REACH_INTEGRATION_HANDOFF.md.
public struct DeviceEventUploader: Sendable {
    public static let eventType = "help_request"
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func upload(eventID: String, config: BackendConfig) async -> UploadResult {
        var request = URLRequest(url: config.baseURL.appendingPathComponent("api/device-events"),
                                 timeoutInterval: 15)
        request.httpMethod = "POST"
        request.setValue("Bearer \(config.token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ["event_id": eventID, "device_id": config.deviceID, "event_type": Self.eventType]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body, options: [.sortedKeys])

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            // URLError descriptions can include the URL; report only the code.
            let code = (error as? URLError)?.code.rawValue ?? -1
            return .retryable(httpStatus: nil, reason: "network_error(\(code))")
        }
        guard let http = response as? HTTPURLResponse else {
            return .retryable(httpStatus: nil, reason: "no_http_response")
        }
        return Self.classify(status: http.statusCode, body: data, eventID: eventID, config: config)
    }

    static func classify(status: Int, body: Data, eventID: String, config: BackendConfig) -> UploadResult {
        switch status {
        case 200, 201:
            guard let json = try? JSONSerialization.jsonObject(with: body) as? [String: Any],
                  let event = json["event"] as? [String: Any],
                  event["event_id"] as? String == eventID,
                  event["device_id"] as? String == config.deviceID,
                  event["event_type"] as? String == eventType,
                  let receivedAt = event["received_at"] as? String,
                  json["status"] as? String == (status == 201 ? "received" : "duplicate") else {
                return .rejected(httpStatus: status, reason: "unexpected_success_body")
            }
            return .recorded(httpStatus: status, duplicate: status == 200, receivedAt: receivedAt)
        case 401: return .rejected(httpStatus: status, reason: "credential_invalid")
        case 403: return .rejected(httpStatus: status, reason: "credential_device_mismatch")
        case 409: return .rejected(httpStatus: status, reason: "event_id_conflict")
        case 413: return .rejected(httpStatus: status, reason: "body_too_large")
        case 422: return .rejected(httpStatus: status, reason: "invalid_schema")
        case 408, 429, 500...599: return .retryable(httpStatus: status, reason: "server_unavailable")
        default: return .rejected(httpStatus: status, reason: "unexpected_status")
        }
    }

    /// 2, 4, 8, 16, 30, 30... seconds.
    public static func backoff(afterAttempt attempt: Int) -> TimeInterval {
        min(30, pow(2, Double(max(1, attempt))))
    }

    public static let maxAutomaticAttempts = 8
}
