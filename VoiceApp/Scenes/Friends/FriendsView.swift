import SwiftUI
import UIKit

struct FriendsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var selectedTab = 0
    
    init() {
        // Customize segmented control appearance for dark background
        let appearance = UISegmentedControl.appearance()
        appearance.selectedSegmentTintColor = UIColor.systemBlue
        appearance.backgroundColor = UIColor(white: 1.0, alpha: 0.12)
        appearance.setTitleTextAttributes([.foregroundColor: UIColor.lightGray], for: .normal)
        appearance.setTitleTextAttributes([.foregroundColor: UIColor.white], for: .selected)
    }
    
    var body: some View {
        NavigationView {
            VStack {
                // Tab Selector
                Picker("", selection: $selectedTab) {
                    Text("Friends (\(FriendsService.shared.sortedFriends.count))").tag(0)
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
                ToolbarItem(placement: .navigationBarLeading) {
                    if selectedTab == 0 { // Only show refresh button on Friends tab
                        Button(action: {
                            Task {
                                await FriendsService.shared.fetchFriends()
                            }
                        }) {
                            Image(systemName: "arrow.clockwise")
                        }
                        .foregroundColor(.blue)
                    }
                }
                
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
    @StateObject private var friendsService = FriendsService.shared
    
    var body: some View {
        VStack {
            if friendsService.isLoading {
                ProgressView("Loading friends...")
                    .foregroundColor(.white)
                    .padding()
            } else if friendsService.friends.isEmpty {
                VStack(spacing: 20) {
                    Image(systemName: "person.2")
                        .font(.system(size: 60))
                        .foregroundColor(.gray)
                    
                    Text("No Friends Yet")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                    
                    Text("Start adding friends to see them here!")
                        .font(.body)
                        .foregroundColor(.gray)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 40)
                }
                .padding(.top, 60)
            } else {
                List(friendsService.sortedFriends) { friend in
                    FriendRow(friend: friend)
                }
                .listStyle(PlainListStyle())
                .background(Color.black)
                .refreshable {
                    await friendsService.fetchFriends()
                }
            }
        }
        .background(Color.black)
        .onAppear {
            Task {
                await friendsService.fetchFriends()
            }
        }
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
    @State private var isLoadingRecommendations = false
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
                EmptyView()
            }
            
            if showTopicRecommendations {
                // Topic-based recommendations
                VStack(alignment: .leading, spacing: 12) {
                    Text("People with Similar Interests")
                        .font(.headline)
                        .foregroundColor(.white)
                        .padding(.horizontal, 20)
                    
                    if isLoadingRecommendations {
                        ProgressView("Loading recommendations...")
                            .foregroundColor(.white)
                            .padding(.horizontal, 20)
                    } else if topicRecommendations.isEmpty {
                        Text("No recommendations yet. Try updating your interests in Profile.")
                            .font(.caption)
                            .foregroundColor(.gray)
                            .padding(.horizontal, 20)
                    } else {
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
            }
            
            Spacer()
        }
        .background(Color.black)
        .onAppear {
            // Auto-load recommendations on first appear
            if !showTopicRecommendations {
                showTopicRecommendations = true
                if topicRecommendations.isEmpty {
                    loadTopicRecommendations()
                }
            }
        }
    }
    
    private func searchUsers(query: String) {
        isSearching = true
        print("🔍 iOS: Starting search for query: '\(query)'")
        
        Task {
            do {
                print("🔍 iOS: Making API request to search endpoint...")
                let response: UserSearchResponse = try await APIService.shared.request(
                    endpoint: APIConfig.Endpoints.searchUsers + "?q=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query)&limit=20"
                )
                
                print("🔍 iOS: Search successful! Found \(response.users.count) users")
                
                await MainActor.run {
                    self.searchResults = response.users.map { user in
                        UserProfile(
                            id: user.user_id,
                            displayName: user.display_name,
                            profilePicture: user.profile_image_url,
                            topics: user.topic_preferences,
                            friendshipStatus: user.friendship_status
                        )
                    }
                    self.isSearching = false
                }
            } catch {
                print("❌ iOS: Failed to search users: \(error)")
                print("❌ iOS: Error details: \(error.localizedDescription)")
                
                await MainActor.run {
                    self.searchResults = []
                    self.isSearching = false
                }
            }
        }
    }
    
    private func loadTopicRecommendations() {
        Task {
            await MainActor.run { isLoadingRecommendations = true }
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
                            topics: user.topic_preferences,
                            friendshipStatus: user.friendship_status
                        )
                    }
                    self.isLoadingRecommendations = false
                }
            } catch {
                print("❌ Failed to load topic recommendations: \(error)")
                await MainActor.run {
                    self.topicRecommendations = []
                    self.isLoadingRecommendations = false
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
    let friendshipStatus: String

    init(id: String, displayName: String, profilePicture: String?, topics: [String], friendshipStatus: String = "none") {
        self.id = id
        self.displayName = displayName
        self.profilePicture = profilePicture
        self.topics = topics
        self.friendshipStatus = friendshipStatus
    }
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
            
            // Action Button based on friendship status
            actionButton
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color.gray.opacity(0.1))
        .cornerRadius(12)
    }
    
    @ViewBuilder
    private var actionButton: some View {
        switch user.friendshipStatus {
        case "friends":
            // Already friends - show friends indicator
            HStack(spacing: 4) {
                Image(systemName: "person.2.fill")
                    .font(.caption)
                Text("Friends")
                    .font(.caption)
                    .fontWeight(.medium)
            }
            .foregroundColor(.green)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.green.opacity(0.2))
            .cornerRadius(8)
            
        case "pending_sent":
            // Friend request sent - show pending indicator
            HStack(spacing: 4) {
                Image(systemName: "clock.fill")
                    .font(.caption)
                Text("Pending")
                    .font(.caption)
                    .fontWeight(.medium)
            }
            .foregroundColor(.orange)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.orange.opacity(0.2))
            .cornerRadius(8)
            
        case "pending_received":
            // Received friend request - show accept/decline
            HStack(spacing: 8) {
                Button("Accept") {
                    // Handle accept - could navigate to friend requests
                }
                .font(.caption)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(6)
                
                Button("Decline") {
                    // Handle decline
                }
                .font(.caption)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.gray.opacity(0.3))
                .foregroundColor(.white)
                .cornerRadius(6)
            }
            
        case "blocked":
            // User is blocked
            Text("Blocked")
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(.red)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Color.red.opacity(0.2))
                .cornerRadius(8)
            
        default:
            // No relationship - show add friend button
            Button(action: {
                onSendRequest(user.id)
                isRequestSent = true
            }) {
                Image(systemName: isRequestSent ? "checkmark.circle.fill" : "plus.circle.fill")
                    .font(.title2)
                    .foregroundColor(isRequestSent ? .green : .blue)
            }
        }
    }
}

struct FriendRow: View {
    let friend: FriendData
    
    var body: some View {
        HStack(spacing: 12) {
            if let url = friend.profile_image_url, !url.isEmpty {
                CachedAsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    Circle()
                        .fill(Color.blue.opacity(0.8))
                        .overlay(
                            Text(String(friend.display_name.prefix(1)))
                                .font(.title3)
                                .fontWeight(.bold)
                                .foregroundColor(.white)
                        )
                }
                .frame(width: 50, height: 50)
                .clipShape(Circle())
            } else {
                Circle()
                    .fill(Color.blue.opacity(0.8))
                    .frame(width: 50, height: 50)
                    .overlay(
                        Text(String(friend.display_name.prefix(1)))
                            .font(.title3)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                    )
            }
            
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 8) {
                    Text(friend.display_name)
                        .font(.body)
                        .fontWeight(.medium)
                        .foregroundColor(.white)
                    
                    if friend.isRecentlyActive {
                        Text("🟢")
                            .font(.caption)
                    }
                }
                
                HStack(spacing: 8) {
                    Text(friend.lastSeenText)
                        .font(.caption)
                        .foregroundColor(.gray)
                    
                    if friend.friendship_status == "accepted" {
                        Text("• Friend")
                            .font(.caption)
                            .foregroundColor(.green)
                    }
                }
            }
            
            Spacer()
            
            Circle()
                .fill(statusColor)
                .frame(width: 12, height: 12)
        }
        .padding(.vertical, 8)
        .background(Color.black)
    }
    
    private var statusColor: Color {
        switch friend.status.lowercased() {
        case "online": return .green
        case "away": return .yellow
        default: return .gray
        }
    }
}

struct FriendRequestRow: View {
    let request: FriendRequestData
    @StateObject private var friendService = FriendRequestService.shared
    @State private var isProcessing = false
    
    var body: some View {
        VStack(spacing: 12) {
            HStack(spacing: 12) {
                if let url = request.from_profile_image_url, !url.isEmpty {
                    CachedAsyncImage(url: url) { image in
                        image
                            .resizable()
                            .scaledToFill()
                    } placeholder: {
                        Circle()
                            .fill(Color.purple.opacity(0.8))
                            .overlay(
                                Text(String(request.from_display_name.prefix(1)))
                                    .font(.title3)
                                    .fontWeight(.bold)
                                    .foregroundColor(.white)
                            )
                    }
                    .frame(width: 50, height: 50)
                    .clipShape(Circle())
                } else {
                    Circle()
                        .fill(Color.purple.opacity(0.8))
                        .frame(width: 50, height: 50)
                        .overlay(
                            Text(String(request.from_display_name.prefix(1)))
                                .font(.title3)
                                .fontWeight(.bold)
                                .foregroundColor(.white)
                        )
                }
                
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
        await MainActor.run { isProcessing = true }
        do {
            _ = try await friendService.acceptFriendRequest(requestId: request.id)
            // Refresh friend requests and friends list
            await friendService.fetchFriendRequests()
            await FriendsService.shared.fetchFriends()
        } catch {
            print("❌ Failed to accept friend request: \(error)")
        }
        await MainActor.run { isProcessing = false }
    }

    private func rejectRequest() async {
        await MainActor.run { isProcessing = true }
        do {
            _ = try await friendService.rejectFriendRequest(requestId: request.id)
            // Refresh the list after rejecting
            await friendService.fetchFriendRequests()
        } catch {
            print("❌ Failed to reject friend request: \(error)")
        }
        await MainActor.run { isProcessing = false }
    }
}

// MARK: - Models
// Friend model moved to FriendsService.swift



#Preview {
    FriendsView()
} 
