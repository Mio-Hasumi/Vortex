import Foundation

enum APIError: Error {
    case invalidURL
    case networkError(Error)
    case invalidResponse
    case decodingError(Error)
    case serverError(String)
    case unauthorized
    case notFound
    
    var message: String {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .invalidResponse:
            return "Invalid server response"
        case .decodingError(let error):
            return "Data decoding error: \(error.localizedDescription)"
        case .serverError(let message):
            return "Server error: \(message)"
        case .unauthorized:
            return "Unauthorized access"
        case .notFound:
            return "Resource not found"
        }
    }
}

class APIService {
    static let shared = APIService()
    private init() {}
    
    private var authToken: String?
    
    func setAuthToken(_ token: String) {
        self.authToken = token
    }
    
    func clearAuthToken() {
        self.authToken = nil
    }
    
    func request<T: Codable>(
        endpoint: String,
        method: String = "GET",
        body: Data? = nil,
        headers: [String: String]? = nil
    ) async throws -> T {
        guard let url = URL(string: APIConfig.baseURL + endpoint) else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body
        
        // Add default headers
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = authToken {
            request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        // Add custom headers
        headers?.forEach { key, value in
            request.addValue(value, forHTTPHeaderField: key)
        }
        
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.invalidResponse
            }
            
            switch httpResponse.statusCode {
            case 200...299:
                do {
                    return try JSONDecoder().decode(T.self, from: data)
                } catch {
                    throw APIError.decodingError(error)
                }
            case 401:
                throw APIError.unauthorized
            case 404:
                throw APIError.notFound
            default:
                if let errorMessage = String(data: data, encoding: .utf8) {
                    throw APIError.serverError(errorMessage)
                } else {
                    throw APIError.serverError("Unknown server error")
                }
            }
        } catch {
            throw APIError.networkError(error)
        }
    }
    
    func upload(
        endpoint: String,
        audioData: Data,
        mimeType: String = "audio/wav"
    ) async throws -> Data {
        print("📤 [APIService] Starting upload to endpoint: \(endpoint)")
        print("📤 [APIService] Audio data size: \(audioData.count) bytes")
        print("📤 [APIService] MIME type: \(mimeType)")
        
        guard let url = URL(string: APIConfig.baseURL + endpoint) else {
            print("❌ [APIService] Invalid URL: \(APIConfig.baseURL + endpoint)")
            throw APIError.invalidURL
        }
        
        print("📤 [APIService] Full URL: \(url.absoluteString)")
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            print("📤 [APIService] Authorization header added")
        } else {
            print("⚠️ [APIService] No auth token available")
        }
        
        var body = Data()
        
        // Add audio file
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"audio_file\"; filename=\"recording.wav\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(audioData)
        body.append("\r\n".data(using: .utf8)!)
        
        // End boundary
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        
        print("📤 [APIService] Form data size: \(body.count) bytes")
        
        request.httpBody = body
        
        do {
            print("📤 [APIService] Sending request...")
            let (data, response) = try await URLSession.shared.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse else {
                print("❌ [APIService] Invalid HTTP response")
                throw APIError.invalidResponse
            }
            
            print("📤 [APIService] Response status code: \(httpResponse.statusCode)")
            print("📤 [APIService] Response data size: \(data.count) bytes")
            
            if data.count < 1000 {
                // Only print response if it's small (likely error message)
                if let responseString = String(data: data, encoding: .utf8) {
                    print("📤 [APIService] Response body: \(responseString)")
                }
            }
            
            switch httpResponse.statusCode {
            case 200...299:
                print("✅ [APIService] Upload successful")
                return data
            case 401:
                print("❌ [APIService] Unauthorized (401)")
                throw APIError.unauthorized
            case 404:
                print("❌ [APIService] Not found (404)")
                throw APIError.notFound
            default:
                if let errorMessage = String(data: data, encoding: .utf8) {
                    print("❌ [APIService] Server error (\(httpResponse.statusCode)): \(errorMessage)")
                    throw APIError.serverError(errorMessage)
                } else {
                    print("❌ [APIService] Unknown server error (\(httpResponse.statusCode))")
                    throw APIError.serverError("Unknown server error")
                }
            }
        } catch {
            print("❌ [APIService] Network error: \(error)")
            throw APIError.networkError(error)
        }
    }
} 