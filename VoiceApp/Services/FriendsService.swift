import Foundation

class FriendsService: ObservableObject {
    static let shared = FriendsService()
    private init() {}
    
    @Published var friends: [FriendData] = []
    @Published var isLoading = false
    @Published var error: String?
    
    var sortedFriends: [FriendData] {
        return friends.sorted { first, second in
            // First sort by online status
            let firstOnline = first.status.lowercased() == "online"
            let secondOnline = second.status.lowercased() == "online"
            
            if firstOnline != secondOnline {
                return firstOnline
            }
            
            // Then sort by last activity (most recent first)
            let formatter = ISO8601DateFormatter()
            let firstDate = formatter.date(from: first.last_seen) ?? Date.distantPast
            let secondDate = formatter.date(from: second.last_seen) ?? Date.distantPast
            
            return firstDate > secondDate
        }
    }
    
    func fetchFriends() async {
        await MainActor.run {
            isLoading = true
            error = nil
        }
        
        print("🔍 [FriendsService] Starting to fetch friends...")
        
        // Check if user is authenticated
        let authService = AuthService.shared
        guard authService.firebaseToken != nil else {
            print("❌ [FriendsService] User not authenticated")
            await MainActor.run {
                self.error = "Please sign in to view friends"
                self.isLoading = false
            }
            return
        }
        
        // Ensure we have a valid auth token
        await ensureValidAuthToken()
        
        do {
            let response: FriendsListResponse = try await APIService.shared.request(
                endpoint: APIConfig.Endpoints.friends
            )
            
            print("✅ [FriendsService] Successfully fetched \(response.friends.count) friends")
            
            await MainActor.run {
                self.friends = response.friends
                self.isLoading = false
            }
        } catch {
            print("❌ [FriendsService] Failed to fetch friends: \(error)")
            
            await MainActor.run {
                self.error = error.localizedDescription
                self.isLoading = false
            }
        }
    }
    
    func refreshFriends() async {
        print("🔄 [FriendsService] Manually refreshing friends...")
        await fetchFriends()
    }
    
    func clearFriends() {
        print("🧹 [FriendsService] Clearing friends list")
        friends = []
        error = nil
        isLoading = false
    }
    
    func blockUser(_ userId: String) async -> Bool {
        print("🚫 [FriendsService] Blocking user: \(userId)")
        
        do {
            let endpoint = APIConfig.Endpoints.blockUser.replacingOccurrences(of: "{user_id}", with: userId)
            let response: BlockResponse = try await APIService.shared.request(
                endpoint: endpoint,
                method: "POST"
            )
            
            print("✅ [FriendsService] User blocked successfully: \(response.message)")
            
            // Refresh friends list to reflect changes
            await fetchFriends()
            
            return true
        } catch {
            print("❌ [FriendsService] Failed to block user: \(error)")
            return false
        }
    }
    
    func unfriendUser(_ userId: String) async -> Bool {
        print("👋 [FriendsService] Unfriending user: \(userId)")
        
        do {
            let endpoint = APIConfig.Endpoints.unfriendUser.replacingOccurrences(of: "{user_id}", with: userId)
            let response: UnfriendResponse = try await APIService.shared.request(
                endpoint: endpoint,
                method: "DELETE"
            )
            
            print("✅ [FriendsService] User unfriended successfully: \(response.message)")
            
            // Refresh friends list to reflect changes
            await fetchFriends()
            
            return true
        } catch {
            print("❌ [FriendsService] Failed to unfriend user: \(error)")
            return false
        }
    }
    
    func unblockUser(_ userId: String) async -> Bool {
        print("🔓 [FriendsService] Unblocking user: \(userId)")
        
        do {
            let endpoint = APIConfig.Endpoints.unblockUser.replacingOccurrences(of: "{user_id}", with: userId)
            let response: UnblockResponse = try await APIService.shared.request(
                endpoint: endpoint,
                method: "DELETE"
            )
            
            print("✅ [FriendsService] User unblocked successfully: \(response.message)")
            
            // Refresh friends list to reflect changes
            await fetchFriends()
            
            return true
        } catch {
            print("❌ [FriendsService] Failed to unblock user: \(error)")
            return false
        }
    }
    
    private func ensureValidAuthToken() async {
        let authService = AuthService.shared
        
        // First, try to use the current token if available
        if let currentToken = authService.firebaseToken {
            print("🔑 [FriendsService] Using existing auth token: \(String(currentToken.prefix(20)))...")
            APIService.shared.setAuthToken(currentToken)
        } else {
            print("⚠️ [FriendsService] No current auth token available")
        }
        
        do {
            print("🔄 [FriendsService] Refreshing auth token...")
            try await authService.refreshToken()
            print("✅ [FriendsService] Auth token refreshed successfully")
        } catch {
            print("⚠️ [FriendsService] Failed to refresh token: \(error)")
            // If token refresh fails, we might need to re-authenticate
            await MainActor.run {
                self.error = "Authentication failed. Please sign in again."
            }
        }
    }
}

// MARK: - API Response Models
struct FriendsListResponse: Codable {
    let friends: [FriendData]
    let total: Int
}

struct BlockResponse: Codable {
    let message: String
}

struct UnfriendResponse: Codable {
    let message: String
}

struct UnblockResponse: Codable {
    let message: String
}

struct FriendData: Codable, Identifiable {
    let user_id: String
    let display_name: String
    let profile_image_url: String?
    let status: String
    let last_seen: String
    let friendship_status: String
    
    var id: String { user_id }
    
    var statusColor: String {
        switch status.lowercased() {
        case "online": return "green"
        case "away": return "yellow"
        default: return "gray"
        }
    }
    
    var lastSeenText: String {
        // Convert ISO date to readable format
        let formatter = ISO8601DateFormatter()
        if let date = formatter.date(from: last_seen) {
            let now = Date()
            let timeInterval = now.timeIntervalSince(date)
            
            if timeInterval < 60 {
                return "Just now"
            } else if timeInterval < 3600 {
                let minutes = Int(timeInterval / 60)
                return "\(minutes) min ago"
            } else if timeInterval < 86400 {
                let hours = Int(timeInterval / 3600)
                return "\(hours) hour\(hours == 1 ? "" : "s") ago"
            } else if timeInterval < 604800 {
                let days = Int(timeInterval / 86400)
                return "\(days) day\(days == 1 ? "" : "s") ago"
            } else {
                let weeks = Int(timeInterval / 604800)
                return "\(weeks) week\(weeks == 1 ? "" : "s") ago"
            }
        }
        return "Unknown"
    }
    
    var isRecentlyActive: Bool {
        let formatter = ISO8601DateFormatter()
        if let date = formatter.date(from: last_seen) {
            let now = Date()
            let timeInterval = now.timeIntervalSince(date)
            return timeInterval < 300 // 5 minutes
        }
        return false
    }
}
