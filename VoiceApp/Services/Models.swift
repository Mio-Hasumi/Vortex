import Foundation

// MARK: - Authentication Models
struct SignUpRequest: Codable {
    let firebase_uid: String
    let display_name: String
    let email: String?
    let phone_number: String?
    
    init(firebase_uid: String, display_name: String, email: String? = nil, phone_number: String? = nil) {
        self.firebase_uid = firebase_uid
        self.display_name = display_name
        self.email = email
        self.phone_number = phone_number
    }
}

struct SignInRequest: Codable {
    let firebase_uid: String
    let email: String?
    let phone_number: String?
    
    init(firebase_uid: String, email: String? = nil, phone_number: String? = nil) {
        self.firebase_uid = firebase_uid
        self.email = email
        self.phone_number = phone_number
    }
}

struct AuthResponse: Codable {
    let user_id: String
    let display_name: String
    let email: String
    let message: String
}

struct UserResponse: Codable {
    let id: String
    let display_name: String
    let email: String
    let phone_number: String?
    let profile_image_url: String?
}

struct UpdateProfileResponse: Codable {
    let message: String
    let user: UserResponse
}

struct ProfilePictureResponse: Codable {
    let message: String
    let profile_image_url: String
    let user: UserResponse
}

// MARK: - Matching Models
struct AIMatchRequest: Codable {
    let user_voice_input: String
    let audio_file_url: String?
    let max_participants: Int
    let language_preference: String?
}

struct AIMatchResponse: Codable {
    let match_id: String
    let session_id: String
    let extracted_topics: [String]
    let generated_hashtags: [String]
    let match_confidence: Double
    let estimated_wait_time: Int
    let ai_greeting: String
    let status: String
}

// Use AnyCodable to handle dynamic JSON data
struct MatchConfirmationResponse: Codable {
    let match_id: String
    let status: String
    let is_ready: Bool
    let room_id: String?
    let room_name: String?
    let livekit_room_name: String?
    let livekit_token: String?
    let topic: String?
    let participants: [AnyCodable]?
    let match_confidence: Double?
    let created_at: String?
    let matched_at: String?
    let message: String?
    let estimated_wait_time: Int?
}

// MARK: - Room Models
struct CreateRoomRequest: Codable {
    let name: String
    let topic: String
    let max_participants: Int
    let is_private: Bool
}

struct JoinRoomRequest: Codable {
    let room_id: String
}

struct RoomResponse: Codable {
    let id: String
    let name: String
    let topic: String
    let participants: [String]
    let max_participants: Int
    let status: String
    let created_at: String
    let livekit_room_name: String
    let livekit_token: String
    let ai_host_enabled: Bool?  // NEW: Indicates if VortexAgent is enabled
}

// MARK: - Topic Models
struct TopicResponse: Codable {
    let id: String
    let name: String
    let description: String
    let category: String
    let difficulty_level: Int
    let is_active: Bool
}

struct TopicExtractionRequest: Codable {
    let text: String
    let user_context: AnyCodable?
}

struct TopicExtractionResponse: Codable {
    let main_topics: [String]
    let hashtags: [String]
    let category: String
    let sentiment: String
    let conversation_style: String
    let confidence: Double
}

// MARK: - AI Host Models
struct StartSessionRequest: Codable {
    let user_preferences: AnyCodable?
    let language: String?
    let voice: String?
}

struct StartSessionResponse: Codable {
    let session_id: String
    let ai_greeting: String
    let audio_url: String?
    let session_state: String
}

struct TTSRequest: Codable {
    let text: String
    let voice: String?
    let speed: Double?
}

// MARK: - Helper type for Any values in JSON
struct AnyCodable: Codable {
    let value: Any
    
    init<T>(_ value: T?) {
        self.value = value ?? ()
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        
        if container.decodeNil() {
            self.value = ()
        } else if let bool = try? container.decode(Bool.self) {
            self.value = bool
        } else if let int = try? container.decode(Int.self) {
            self.value = int
        } else if let double = try? container.decode(Double.self) {
            self.value = double
        } else if let string = try? container.decode(String.self) {
            self.value = string
        } else if let array = try? container.decode([AnyCodable].self) {
            self.value = array.map { $0.value }
        } else if let dictionary = try? container.decode([String: AnyCodable].self) {
            self.value = dictionary.mapValues { $0.value }
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "AnyCodable value cannot be decoded")
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        
        switch value {
        case is Void:
            try container.encodeNil()
        case let bool as Bool:
            try container.encode(bool)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let string as String:
            try container.encode(string)
        case let array as [Any]:
            let codableArray = array.map { AnyCodable($0) }
            try container.encode(codableArray)
        case let dictionary as [String: Any]:
            let codableDictionary = dictionary.mapValues { AnyCodable($0) }
            try container.encode(codableDictionary)
        default:
            let context = EncodingError.Context(codingPath: container.codingPath, debugDescription: "AnyCodable value cannot be encoded")
            throw EncodingError.invalidValue(value, context)
        }
    }
}

// MARK: - VortexAgent Management Models (NEW - Optional advanced features)
struct AgentStatusResponse: Codable {
    let room_id: String
    let room_name: String
    let agent_identity: String
    let is_active: Bool
    let deployment_time: String
    let participants_count: Int
    let ai_features: [String]
}

struct AgentSettingsRequest: Codable {
    let personality: String?         // "friendly", "professional", "casual"
    let engagement_level: Int?       // 1-10 scale
    let greeting_enabled: Bool?
    let fact_checking_enabled: Bool?
    let topic_suggestions_enabled: Bool?
}

struct AgentSettingsResponse: Codable {
    let success: Bool
    let message: String
    let updated_settings: [String: AnyCodable]
}

struct AgentStatsResponse: Codable {
    let total_agents: Int
    let active_agents: Int
    let rooms_with_agents: [String]
    let timestamp: String
} 