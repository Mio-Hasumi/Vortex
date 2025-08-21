import SwiftUI

struct FriendsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var selectedTab = 0
    
    var body: some View {
        NavigationView {
            VStack {
                // Tab Selector
                Picker("", selection: $selectedTab) {
                    Text("Friends").tag(0)
                    Text("Requests").tag(1)
                    Text("Find People").tag(2)
                }
                .pickerStyle(SegmentedPickerStyle())
                .padding(.horizontal, 20)
                .padding(.top, 10)
                
                // Content
                TabView(selection: $selectedTab) {
                    FriendsListView()
                        .tag(0)
                    
                    FriendRequestsView()
                        .tag(1)
                    
                    FindPeopleView()
                        .tag(2)
                }
                .tabViewStyle(PageTabViewStyle(indexDisplayMode: .never))
            }
            .background(Color.black)
            .navigationTitle("Friends")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(.blue)
                }
            }
        }
    }
}

struct FriendsListView: View {
    let friends = [
        Friend(name: "Alice Johnson", status: "Online", lastSeen: "Active now"),
        Friend(name: "Bob Smith", status: "Away", lastSeen: "2 hours ago"),
        Friend(name: "Carol Williams", status: "Offline", lastSeen: "Yesterday")
    ]
    
    var body: some View {
        List(friends) { friend in
            FriendRow(friend: friend)
        }
        .listStyle(PlainListStyle())
        .background(Color.black)
    }
}

struct FriendRequestsView: View {
    @StateObject private var friendService = FriendRequestService.shared
    
    var body: some View {
        VStack {
            if friendService.isLoading {
                ProgressView("Loading requests...")
                    .foregroundColor(.white)
                    .padding()
            } else if friendService.incomingRequests.isEmpty {
                VStack(spacing: 20) {
                    Image(systemName: "person.badge.plus")
                        .font(.system(size: 60))
                        .foregroundColor(.gray)
                    
                    Text("No Friend Requests")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                    
                    Text("When someone sends you a friend request, it will appear here.")
                        .font(.body)
                        .foregroundColor(.gray)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 40)
                }
                .padding(.top, 60)
            } else {
                List(friendService.incomingRequests) { request in
                    FriendRequestRow(request: request)
                }
                .listStyle(PlainListStyle())
                .background(Color.black)
            }
        }
        .background(Color.black)
        .onAppear {
            Task {
                await friendService.fetchFriendRequests()
            }
        }
    }
}

struct FindPeopleView: View {
    @State private var searchText = ""
    @State private var searchResults: [UserProfile] = []
    @State private var topicRecommendations: [UserProfile] = []
    @State private var isSearching = false
    @State private var showTopicRecommendations = false
    @StateObject private var friendService = FriendRequestService.shared
    
    var body: some View {
        VStack(spacing: 20) {
            // Search Bar
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.gray)
                
                TextField("Search by display name...", text: $searchText)
                    .textFieldStyle(PlainTextFieldStyle())
                    .foregroundColor(.white)
                    .onChange(of: searchText) { newValue in
                        if !newValue.isEmpty {
                            searchUsers(query: newValue)
                        } else {
                            searchResults = []
                        }
                    }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.gray.opacity(0.2))
            .cornerRadius(10)
            .padding(.horizontal, 20)
            
            if isSearching {
                ProgressView("Searching...")
                    .foregroundColor(.white)
                    .padding()
            } else if !searchText.isEmpty && !searchResults.isEmpty {
                // Search Results
                VStack(alignment: .leading, spacing: 12) {
                    Text("Search Results")
                        .font(.headline)
                        .foregroundColor(.white)
                        .padding(.horizontal, 20)
                    
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(searchResults, id: \.id) { user in
                                UserSearchRow(user: user) { userId in
                                    Task {
                                        await sendFriendRequest(to: userId)
                                    }
                                }
                            }
                        }
                        .padding(.horizontal, 20)
                    }
                }
            } else if !searchText.isEmpty && searchResults.isEmpty && !isSearching {
                // No search results
                VStack(spacing: 20) {
                    Image(systemName: "person.slash")
                        .font(.system(size: 60))
                        .foregroundColor(.gray)
                    
                    Text("No users found")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                    
                    Text("Try searching with a different name")
                        .font(.body)
                        .foregroundColor(.gray)
                        .multilineTextAlignment(.center)
                }
                .padding()
            } else {
                // Default view with topic recommendations
                VStack(spacing: 20) {
                    Image(systemName: "person.2.badge.plus")
                        .font(.system(size: 60))
                        .foregroundColor(.gray)
                    
                    Text("Find People")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                    
                    Text("Discover new friends based on your interests and voice matching preferences.")
                        .font(.body)
                        .foregroundColor(.gray)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 40)
                    
                    Button("Start Finding People") {
                        showTopicRecommendations = true
                        loadTopicRecommendations()
                    }
                    .padding(.horizontal, 30)
                    .padding(.vertical, 12)
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                }
                .padding(.top, 20)
            }
            
            if showTopicRecommendations && !topicRecommendations.isEmpty {
                // Topic-based recommendations
                VStack(alignment: .leading, spacing: 12) {
                    Text("People with Similar Interests")
                        .font(.headline)
                        .foregroundColor(.white)
                        .padding(.horizontal, 20)
                    
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(topicRecommendations, id: \.id) { user in
                                UserSearchRow(user: user) { userId in
                                    Task {
                                        await sendFriendRequest(to: userId)
                                    }
                                }
                            }
                        }
                        .padding(.horizontal, 20)
                    }
                }
            }
            
            Spacer()
        }
        .background(Color.black)
    }
    
    private func searchUsers(query: String) {
        isSearching = true
        
        Task {
            do {
                let response: UserSearchResponse = try await APIService.shared.request(
                    endpoint: APIConfig.Endpoints.searchUsers + "?q=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query)&limit=20"
                )
                
                await MainActor.run {
                    self.searchResults = response.users.map { user in
                        UserProfile(
                            id: user.user_id,
                            displayName: user.display_name,
                            profilePicture: user.profile_image_url,
                            topics: user.topic_preferences
                        )
                    }
                    self.isSearching = false
                }
            } catch {
                print("❌ Failed to search users: \(error)")
                await MainActor.run {
                    // Fallback to mock data if API fails
                    self.searchResults = [
                        UserProfile(id: "1", displayName: "Alex Johnson", profilePicture: nil, topics: ["AI", "Technology"]),
                        UserProfile(id: "2", displayName: "Sarah Chen", profilePicture: nil, topics: ["Science", "Innovation"]),
                        UserProfile(id: "3", displayName: "Mike Davis", profilePicture: nil, topics: ["Technology", "Business"])
                    ].filter { $0.displayName.lowercased().contains(query.lowercased()) }
                    self.isSearching = false
                }
            }
        }
    }
    
    private func loadTopicRecommendations() {
        Task {
            do {
                let response: UserRecommendationsResponse = try await APIService.shared.request(
                    endpoint: APIConfig.Endpoints.userRecommendations + "?limit=20&min_common_interests=1"
                )
                
                await MainActor.run {
                    self.topicRecommendations = response.users.map { user in
                        UserProfile(
                            id: user.user_id,
                            displayName: user.display_name,
                            profilePicture: user.profile_image_url,
                            topics: user.topic_preferences
                        )
                    }
                }
            } catch {
                print("❌ Failed to load topic recommendations: \(error)")
                await MainActor.run {
                    // Fallback to mock data if API fails
                    self.topicRecommendations = [
                        UserProfile(id: "4", displayName: "Emma Wilson", profilePicture: nil, topics: ["AI", "Machine Learning"]),
                        UserProfile(id: "5", displayName: "David Brown", profilePicture: nil, topics: ["Technology", "Innovation"]),
                        UserProfile(id: "6", displayName: "Lisa Garcia", profilePicture: nil, topics: ["Science", "Research"]),
                        UserProfile(id: "7", displayName: "Tom Anderson", profilePicture: nil, topics: ["AI", "Technology"])
                    ]
                }
            }
        }
    }
    
    private func sendFriendRequest(to userId: String) async {
        do {
            let result = try await friendService.sendFriendRequest(to: userId)
            await MainActor.run {
                // Show success message or update UI
                print("Friend request sent successfully: \(result.message)")
            }
        } catch {
            await MainActor.run {
                print("Failed to send friend request: \(error.localizedDescription)")
            }
            }
        }
    }

// MARK: - User Profile Model
struct UserProfile: Identifiable {
    let id: String
    let displayName: String
    let profilePicture: String?
    let topics: [String]
}

// MARK: - API Response Models
struct UserSearchResponse: Codable {
    let users: [SearchUserData]
    let query: String
    let total: Int
    let message: String?
}

struct UserRecommendationsResponse: Codable {
    let users: [RecommendationUserData]
    let total: Int
    let user_interests: [String]
    let min_common_interests: Int
    let message: String?
}

struct SearchUserData: Codable {
    let user_id: String
    let display_name: String
    let profile_image_url: String?
    let bio: String?
    let status: String
    let friendship_status: String
    let topic_preferences: [String]
}

struct RecommendationUserData: Codable {
    let user_id: String
    let display_name: String
    let profile_image_url: String?
    let bio: String?
    let status: String
    let friendship_status: String
    let topic_preferences: [String]
    let common_interests: [String]
    let similarity_score: Double
    let total_common_interests: Int
}

// MARK: - User Search Row Component
struct UserSearchRow: View {
    let user: UserProfile
    let onSendRequest: (String) -> Void
    @State private var isRequestSent = false
    
    var body: some View {
        HStack(spacing: 16) {
            // Profile Picture
            Circle()
                .fill(Color.purple.opacity(0.8))
                .frame(width: 50, height: 50)
                .overlay(
                    Text(String(user.displayName.prefix(1)))
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                )
            
            // User Info
            VStack(alignment: .leading, spacing: 4) {
                Text(user.displayName)
                    .font(.body)
                    .fontWeight(.medium)
                    .foregroundColor(.white)
                
                if !user.topics.isEmpty {
                    Text(user.topics.joined(separator: ", "))
                        .font(.caption)
                        .foregroundColor(.gray)
                }
            }
            
            Spacer()
            
            // Plus Icon Button
            Button(action: {
                onSendRequest(user.id)
                isRequestSent = true
            }) {
                Image(systemName: isRequestSent ? "checkmark.circle.fill" : "plus.circle.fill")
                    .font(.title2)
                    .foregroundColor(isRequestSent ? .green : .blue)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color.gray.opacity(0.1))
        .cornerRadius(12)
    }
}

struct FriendRow: View {
    let friend: Friend
    
    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(Color.blue.opacity(0.8))
                .frame(width: 50, height: 50)
                .overlay(
                    Text(String(friend.name.prefix(1)))
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                )
            
            VStack(alignment: .leading, spacing: 4) {
                Text(friend.name)
                    .font(.body)
                    .fontWeight(.medium)
                    .foregroundColor(.white)
                
                Text(friend.lastSeen)
                    .font(.caption)
                    .foregroundColor(.gray)
            }
            
            Spacer()
            
            Circle()
                .fill(friend.statusColor)
                .frame(width: 12, height: 12)
        }
        .padding(.vertical, 8)
        .background(Color.black)
    }
}

struct FriendRequestRow: View {
    let request: FriendRequestData
    @StateObject private var friendService = FriendRequestService.shared
    @State private var isProcessing = false
    
    var body: some View {
        VStack(spacing: 12) {
            HStack(spacing: 12) {
                Circle()
                    .fill(Color.purple.opacity(0.8))
                    .frame(width: 50, height: 50)
                    .overlay(
                        Text(String(request.from_display_name.prefix(1)))
                            .font(.title3)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                    )
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(request.from_display_name)
                        .font(.body)
                        .fontWeight(.medium)
                        .foregroundColor(.white)
                    
                    Text("Sent you a friend request")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                
                Spacer()
            }
            
            HStack(spacing: 12) {
                Button("Accept") {
                    Task {
                        await acceptRequest()
                    }
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 8)
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(8)
                .disabled(isProcessing)
                
                Button("Decline") {
                    Task {
                        await rejectRequest()
                    }
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 8)
                .background(Color.gray.opacity(0.3))
                .foregroundColor(.white)
                .cornerRadius(8)
                .disabled(isProcessing)
                
                Spacer()
            }
        }
        .padding(.vertical, 8)
        .background(Color.black)
    }
    
    private func acceptRequest() async {
        isProcessing = true
        do {
            _ = try await friendService.acceptFriendRequest(requestId: request.id)
            // Refresh the list after accepting
            await friendService.fetchFriendRequests()
        } catch {
            print("❌ Failed to accept friend request: \(error)")
        }
        isProcessing = false
    }
    
    private func rejectRequest() async {
        isProcessing = true
        do {
            _ = try await friendService.rejectFriendRequest(requestId: request.id)
            // Refresh the list after rejecting
            await friendService.fetchFriendRequests()
        } catch {
            print("❌ Failed to reject friend request: \(error)")
        }
        isProcessing = false
    }
}

// MARK: - Models
struct Friend: Identifiable {
    let id = UUID()
    let name: String
    let status: String
    let lastSeen: String
    
    var statusColor: Color {
        switch status {
        case "Online": return .green
        case "Away": return .yellow
        default: return .gray
        }
    }
}



#Preview {
    FriendsView()
} 