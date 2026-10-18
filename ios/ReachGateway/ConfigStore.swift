import Foundation
import Security

/// Runtime backend configuration. The base URL and device ID live in
/// UserDefaults; the device credential lives only in the Keychain
/// (this device only, never synced or backed up in clear). Nothing here is
/// ever logged.
enum ConfigStore {
    static let defaultDeviceID = "nano-01"
    private static let urlKey = "backendBaseURL"
    private static let deviceKey = "deviceID"
    private static let keychainService = "ReachGateway.backend"
    private static let keychainAccount = "device-credential"

    static var baseURLText: String { UserDefaults.standard.string(forKey: urlKey) ?? "" }
    static var deviceID: String { UserDefaults.standard.string(forKey: deviceKey) ?? defaultDeviceID }
    static var hasToken: Bool { readToken() != nil }

    static func load() -> BackendConfig? {
        guard let url = BackendConfig.parseBaseURL(baseURLText), let token = readToken() else { return nil }
        return BackendConfig(baseURL: url, deviceID: deviceID, token: token)
    }

    enum SaveError: Error {
        case invalidURL, invalidDeviceID, keychain(OSStatus)
    }

    /// An empty `token` keeps the stored credential.
    static func save(baseURLText: String, deviceID: String, token: String) throws {
        guard let url = BackendConfig.parseBaseURL(baseURLText) else { throw SaveError.invalidURL }
        guard BackendConfig.isValidIdentifier(deviceID, maxLength: 64) else { throw SaveError.invalidDeviceID }
        let trimmed = token.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty {
            try writeToken(trimmed)
        }
        UserDefaults.standard.set(url.absoluteString, forKey: urlKey)
        UserDefaults.standard.set(deviceID, forKey: deviceKey)
    }

    static func clear() {
        UserDefaults.standard.removeObject(forKey: urlKey)
        UserDefaults.standard.removeObject(forKey: deviceKey)
        SecItemDelete(baseQuery() as CFDictionary)
    }

    private static func baseQuery() -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: keychainService,
         kSecAttrAccount as String: keychainAccount]
    }

    private static func readToken() -> String? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    private static func writeToken(_ token: String) throws {
        SecItemDelete(baseQuery() as CFDictionary)
        var attrs = baseQuery()
        attrs[kSecValueData as String] = Data(token.utf8)
        attrs[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        let status = SecItemAdd(attrs as CFDictionary, nil)
        guard status == errSecSuccess else { throw SaveError.keychain(status) }
    }
}
