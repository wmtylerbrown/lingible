import Foundation
import Security

// MARK: - Keychain Storage Protocol
protocol KeychainStorageProtocol {
    func save(_ data: Data, for key: String) throws
    func load(for key: String) throws -> Data?
    func delete(for key: String) throws
    func clearAll()
}

// MARK: - Keychain Storage Implementation
final class KeychainStorage: KeychainStorageProtocol {

    // MARK: - Private Properties
    private let service: String

    // MARK: - Initialization
    init(service: String = Bundle.main.bundleIdentifier ?? "com.lingible.lingible") {
        self.service = service
    }

    // MARK: - Public Methods
    func save(_ data: Data, for key: String) throws {
        // Delete existing item first
        try? delete(for: key)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlocked
        ]

        let status = SecItemAdd(query as CFDictionary, nil)

        guard status == errSecSuccess else {
            throw KeychainError.saveFailed(status)
        }
    }

    func load(for key: String) throws -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        switch status {
        case errSecSuccess:
            return result as? Data
        case errSecItemNotFound:
            return nil
        default:
            throw KeychainError.loadFailed(status)
        }
    }

    func delete(for key: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key
        ]

        let status = SecItemDelete(query as CFDictionary)

        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.deleteFailed(status)
        }
    }

    func clearAll() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service
        ]

        SecItemDelete(query as CFDictionary)
    }
}

// MARK: - Keychain Errors
enum KeychainError: LocalizedError {
    case saveFailed(OSStatus)
    case loadFailed(OSStatus)
    case deleteFailed(OSStatus)

    var errorDescription: String? {
        switch self {
        case .saveFailed(let status):
            return "Failed to save to keychain. Status: \(status)"
        case .loadFailed(let status):
            return "Failed to load from keychain. Status: \(status)"
        case .deleteFailed(let status):
            return "Failed to delete from keychain. Status: \(status)"
        }
    }
}

// MARK: - Convenience Extensions
extension KeychainStorage {

    func saveString(_ string: String, for key: String) throws {
        guard let data = string.data(using: .utf8) else {
            throw KeychainError.saveFailed(errSecParam)
        }
        try save(data, for: key)
    }

    func loadString(for key: String) throws -> String? {
        guard let data = try load(for: key) else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }

    func saveCodable<T: Codable>(_ object: T, for key: String) throws {
        let data = try JSONEncoder().encode(object)
        try save(data, for: key)
    }

    func loadCodable<T: Codable>(_ type: T.Type, for key: String) throws -> T? {
        guard let data = try load(for: key) else {
            return nil
        }
        return try JSONDecoder().decode(type, from: data)
    }
}
