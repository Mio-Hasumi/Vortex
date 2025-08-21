import Foundation

// MARK: - Shared Models for Voice Chat
struct ChatParticipant {
    let userId: String
    let displayName: String
    let isCurrentUser: Bool
    let isAIHost: Bool
    
    // Convenience initializer for backward compatibility
    init(userId: String, displayName: String, isCurrentUser: Bool, isAIHost: Bool = false) {
        self.userId = userId
        self.displayName = displayName
        self.isCurrentUser = isCurrentUser
        self.isAIHost = isAIHost
    }
}

struct LiveMatchData {
    let matchId: String
    let sessionId: String
    let roomId: String
    let livekitToken: String
    let livekitName: String  // LiveKit room name for WebSocket connection
    let userId: String       // Current user ID for WebSocket authentication
    let participants: [ChatParticipant]
    let topics: [String]
    let hashtags: [String]
}
