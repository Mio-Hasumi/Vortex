import Foundation

class FriendRequestService: ObservableObject {
    static let shared = FriendRequestService()
    init() {}
    
    @Published var incomingRequests: [FriendRequestData] = []
    @Published var outgoingRequests: [FriendRequestData] = []
    @Published var isLoading = false
    
    func sendFriendRequest(to userId: String) async throws -> FriendRequestResponse {
        let requestBody = SendFriendRequestRequest(user_id: userId)
        
        let jsonData = try JSONEncoder().encode(requestBody)
        
        return try await APIService.shared.request(
            endpoint: APIConfig.Endpoints.friendRequest,
            method: "POST",
            body: jsonData
        )
    }
    
    func fetchFriendRequests() async {
        await MainActor.run {
            isLoading = true
        }
        
        do {
            let response: FriendRequestListResponse = try await APIService.shared.request(
                endpoint: APIConfig.Endpoints.friendRequests + "?type=received"
            )
            
            await MainActor.run {
                self.incomingRequests = response.requests
                self.isLoading = false
            }
        } catch {
            print("❌ Failed to fetch friend requests: \(error)")
            await MainActor.run {
                self.isLoading = false
            }
        }
    }
    
    func acceptFriendRequest(requestId: String) async throws -> AcceptFriendRequestResponse {
        return try await APIService.shared.request(
            endpoint: APIConfig.Endpoints.friendRequests + "/\(requestId)/accept",
            method: "POST"
        )
    }
    
    func rejectFriendRequest(requestId: String) async throws -> RejectFriendRequestResponse {
        return try await APIService.shared.request(
            endpoint: APIConfig.Endpoints.friendRequests + "/\(requestId)/reject",
            method: "POST"
        )
    }
    
    func getFriendshipRequestId(for userId: String) async throws -> GetFriendshipRequestIdResponse {
        return try await APIService.shared.request(
            endpoint: APIConfig.Endpoints.getFriendshipRequestId + "/\(userId)"
        )
    }
    
    // Get friendship status for a specific user using search API
    func getFriendshipStatus(for userId: String) async throws -> String {
        do {
            let response: UserSearchResponse = try await APIService.shared.request(
                endpoint: APIConfig.Endpoints.searchUsers + "?q=\(userId)&limit=1"
            )
            
            if let user = response.users.first {
                return user.friendship_status
            } else {
                return "none"
            }
        } catch {
            print("❌ Failed to get friendship status for user \(userId): \(error)")
            return "none"
        }
    }
}

// MARK: - Request/Response Models
struct SendFriendRequestRequest: Codable {
    let user_id: String
}

struct FriendRequestResponse: Codable {
    let message: String
    let request_id: String
}

struct FriendRequestListResponse: Codable {
    let requests: [FriendRequestData]
    let total: Int
}

struct FriendRequestData: Codable, Identifiable {
    let id: String
    let from_user_id: String
    let from_display_name: String
    let from_profile_image_url: String?
    let to_user_id: String
    let to_display_name: String
    let to_profile_image_url: String?
    let status: String
    let created_at: String
    let message: String?
}

struct AcceptFriendRequestResponse: Codable {
    let message: String
}

struct RejectFriendRequestResponse: Codable {
    let message: String
}

struct GetFriendshipRequestIdResponse: Codable {
    let friendship_id: String?
    let status: String
    let message: String
}
