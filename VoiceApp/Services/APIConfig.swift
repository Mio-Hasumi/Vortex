import Foundation

enum APIConfig {
    static let baseURL = "https://vortex-production-71fe.up.railway.app"
    static let wsBaseURL = "wss://vortex-production-71fe.up.railway.app"
    
    enum Endpoints {
        // Auth
        static let register = "/api/auth/register"
        static let login = "/api/auth/login"
        static let signout = "/api/auth/signout"
        static let profile = "/api/auth/profile"
        static let updateDisplayName = "/api/auth/profile/display-name"
        static let addAuthMethod = "/api/auth/profile/auth-methods"
        static let uploadProfilePicture = "/api/auth/profile/picture"
        
        // Topics
        static let topics = "/api/topics"
        static let popularTopics = "/api/topics/popular"
        static let searchTopics = "/api/topics/search"
        static let topicPreferences = "/api/topics/preferences"
        
        // Matching
        static let match = "/api/matching/match"
        static let aiMatch = "/api/matching/ai-match"
        static let confirmMatch = "/api/matching/confirm"
        static let cancelMatch = "/api/matching/cancel"
        static let matchStatus = "/api/matching/status"
        static let matchHistory = "/api/matching/history"
        
        // Rooms
        static let rooms = "/api/rooms"
        static let joinRoom = "/api/rooms/join"
        static let leaveRoom = "/api/rooms/{room_id}/leave"
        static let roomParticipants = "/api/rooms/{room_id}/participants"
        
        // Friends
        static let friends = "/api/friends"
        static let friendRequest = "/api/friends/request"
        static let friendRequests = "/api/friends/requests"
        static let searchUsers = "/api/friends/search"
        static let userRecommendations = "/api/friends/recommendations"
        static let findPeopleByTopics = "/api/friends/find-people-by-topics"
        
        // Recordings
        static let recordings = "/api/recordings"
        static let recordingMetadata = "/api/recordings/{recording_id}/metadata"
        static let recordingTranscript = "/api/recordings/{recording_id}/transcript"
        static let recordingSummary = "/api/recordings/{recording_id}/summary"
        
        // AI Host
        static let aiStartSession = "/api/ai-host/start-session"
        static let aiProcessInput = "/api/ai-host/process-input"
        static let aiTTS = "/api/ai-host/tts"
        static let aiExtractTopics = "/api/ai-host/extract-topics"
        static let aiExtractTopicsFromVoice = "/api/ai-host/extract-topics-from-voice"
        static let aiUploadAudio = "/api/ai-host/upload-audio"
        
        // VortexAgent Management (NEW - Optional advanced features)
        static let agentStatus = "/api/agents/status"
        static let agentSettings = "/api/agents/settings"
        static let agentStats = "/api/agents/stats"
        static let removeAgent = "/api/agents"
    }
    
    enum WebSocket {
        static let aiVoiceChat = "/api/ai-host/voice-chat"
        static let aiAudioStream = "/api/ai-host/audio-stream"  // NEW - for real-time audio streaming
        static let liveSubtitle = "/api/ai-host/live-subtitle"
        static let roomChat = "/api/rooms/ws"
        static let matching = "/api/matching/ws"
    }
    
    // MARK: - Environment Info
    static let environment = "production"
    static let apiDocsURL = "https://vortex-production-71fe.up.railway.app/docs"
    
    // MARK: - YouTube Ad Configuration
    static let youtubeAdVideoId = "Ydp7cNF5p74" // YouTube video ID for waiting room ad
    static let youtubeAdTimeoutSeconds = 30 // Auto-hide timeout if video doesn't end properly
    
    // MARK: - Helper Methods
    static func roomPath(_ roomId: String) -> String {
        return "/api/rooms/\(roomId)"
    }
    
    static func leaveRoomPath(_ roomId: String) -> String {
        return "/api/rooms/\(roomId)/leave"
    }
    
    static func roomParticipantsPath(_ roomId: String) -> String {
        return "/api/rooms/\(roomId)/participants"
    }
    
    static func roomWebSocketPath(_ roomId: String) -> String {
        return "/api/rooms/ws/\(roomId)"
    }
    
    static func recordingPath(_ recordingId: String) -> String {
        return "/api/recordings/\(recordingId)"
    }
    
    static func recordingMetadataPath(_ recordingId: String) -> String {
        return "/api/recordings/\(recordingId)/metadata"
    }
    
    static func recordingTranscriptPath(_ recordingId: String) -> String {
        return "/api/recordings/\(recordingId)/transcript"
    }
    
    static func recordingSummaryPath(_ recordingId: String) -> String {
        return "/api/recordings/\(recordingId)/summary"
    }
    
    // MARK: - VortexAgent Helper Methods (NEW)
    static func agentStatusPath(_ roomId: String) -> String {
        return "/api/agents/status/\(roomId)"
    }
    
    static func agentSettingsPath(_ roomId: String) -> String {
        return "/api/agents/settings/\(roomId)"
    }
    
    static func removeAgentPath(_ roomId: String) -> String {
        return "/api/agents/\(roomId)"
    }
    
    static func confirmMatchPath(_ matchId: String) -> String {
        return "/api/matching/confirm/\(matchId)"
    }
} 