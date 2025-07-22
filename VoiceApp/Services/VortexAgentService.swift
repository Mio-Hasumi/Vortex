import Foundation

/**
 * VortexAgentService
 * 
 * Optional service for managing VortexAgent features from the iOS app.
 * These are advanced features - basic AI functionality works automatically.
 */
class VortexAgentService: ObservableObject {
    static let shared = VortexAgentService()
    
    private let apiService = APIService.shared
    
    private init() {}
    
    // MARK: - Agent Status Management
    
    /**
     * Get the status of VortexAgent in a specific room
     * This tells you if the AI host is active and what features are available
     */
    func getAgentStatus(roomId: String) async throws -> AgentStatusResponse {
        let path = APIConfig.agentStatusPath(roomId)
        
        let request = APIRequest<EmptyRequest, AgentStatusResponse>(
            endpoint: path,
            method: .GET,
            body: EmptyRequest()
        )
        
        return try await apiService.performRequest(request)
    }
    
    /**
     * Update VortexAgent settings for a room
     * Allows customizing the AI's personality and behavior
     */
    func updateAgentSettings(
        roomId: String,
        personality: String? = nil,
        engagementLevel: Int? = nil,
        greetingEnabled: Bool? = nil,
        factCheckingEnabled: Bool? = nil,
        topicSuggestionsEnabled: Bool? = nil
    ) async throws -> AgentSettingsResponse {
        let path = APIConfig.agentSettingsPath(roomId)
        
        let settings = AgentSettingsRequest(
            personality: personality,
            engagement_level: engagementLevel,
            greeting_enabled: greetingEnabled,
            fact_checking_enabled: factCheckingEnabled,
            topic_suggestions_enabled: topicSuggestionsEnabled
        )
        
        let request = APIRequest<AgentSettingsRequest, AgentSettingsResponse>(
            endpoint: path,
            method: .PUT,
            body: settings
        )
        
        return try await apiService.performRequest(request)
    }
    
    /**
     * Remove VortexAgent from a room
     * This stops the AI host and returns to human-only conversation
     */
    func removeAgent(fromRoom roomId: String) async throws -> [String: Any] {
        let path = APIConfig.removeAgentPath(roomId)
        
        let request = APIRequest<EmptyRequest, [String: AnyCodable]>(
            endpoint: path,
            method: .DELETE,
            body: EmptyRequest()
        )
        
        let response = try await apiService.performRequest(request)
        return response.mapValues { $0.value }
    }
    
    /**
     * Get overall agent deployment statistics
     * Useful for debugging and monitoring
     */
    func getAgentStats() async throws -> AgentStatsResponse {
        let path = APIConfig.Endpoints.agentStats
        
        let request = APIRequest<EmptyRequest, AgentStatsResponse>(
            endpoint: path,
            method: .GET,
            body: EmptyRequest()
        )
        
        return try await apiService.performRequest(request)
    }
    
    // MARK: - Convenience Methods
    
    /**
     * Check if an AI host is active in a room
     * Simple boolean check for UI purposes
     */
    func isAgentActive(in roomId: String) async -> Bool {
        do {
            let status = try await getAgentStatus(roomId: roomId)
            return status.is_active
        } catch {
            print("⚠️ [VortexAgent] Error checking agent status: \(error)")
            return false
        }
    }
    
    /**
     * Set agent to friendly personality
     * Quick preset for casual conversations
     */
    func setFriendlyMode(roomId: String) async throws {
        _ = try await updateAgentSettings(
            roomId: roomId,
            personality: "friendly",
            engagementLevel: 8,
            greetingEnabled: true,
            factCheckingEnabled: true,
            topicSuggestionsEnabled: true
        )
    }
    
    /**
     * Set agent to professional personality
     * Quick preset for formal discussions
     */
    func setProfessionalMode(roomId: String) async throws {
        _ = try await updateAgentSettings(
            roomId: roomId,
            personality: "professional",
            engagementLevel: 6,
            greetingEnabled: true,
            factCheckingEnabled: true,
            topicSuggestionsEnabled: false
        )
    }
    
    /**
     * Enable minimal intervention mode
     * AI host will be less active, only helping when needed
     */
    func setMinimalMode(roomId: String) async throws {
        _ = try await updateAgentSettings(
            roomId: roomId,
            personality: "casual",
            engagementLevel: 3,
            greetingEnabled: false,
            factCheckingEnabled: false,
            topicSuggestionsEnabled: false
        )
    }
}

// MARK: - Supporting Types

private struct EmptyRequest: Codable {}

// MARK: - Usage Examples
/*
 
 // Example 1: Check if AI is active
 let isActive = await VortexAgentService.shared.isAgentActive(in: roomId)
 
 // Example 2: Get detailed status
 do {
     let status = try await VortexAgentService.shared.getAgentStatus(roomId: roomId)
     print("AI Features: \(status.ai_features)")
 } catch {
     print("Error: \(error)")
 }
 
 // Example 3: Customize AI personality
 do {
     try await VortexAgentService.shared.setFriendlyMode(roomId: roomId)
     print("✅ AI set to friendly mode")
 } catch {
     print("❌ Failed to update AI: \(error)")
 }
 
 // Example 4: Remove AI from room
 do {
     try await VortexAgentService.shared.removeAgent(fromRoom: roomId)
     print("✅ AI host removed")
 } catch {
     print("❌ Failed to remove AI: \(error)")
 }
 
 */ 