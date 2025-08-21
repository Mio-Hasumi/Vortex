import SwiftUI

struct FriendsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var searchText = ""
    @State private var selectedTab = 0
    
    var body: some View {
        NavigationView {
            VStack {
                // Search Bar
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.gray)
                    
                    TextField("Search friends...", text: $searchText)
                        .textFieldStyle(PlainTextFieldStyle())
                        .foregroundColor(.white)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color.gray.opacity(0.2))
                .cornerRadius(10)
                .padding(.horizontal, 20)
                
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
    var body: some View {
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
            
            Button("Start Finding Friends") {
                // TODO: Implement find friends functionality
            }
            .padding(.horizontal, 30)
            .padding(.vertical, 12)
            .background(Color.blue)
            .foregroundColor(.white)
            .cornerRadius(10)
            
            Spacer()
        }
        .padding(.top, 60)
        .background(Color.black)
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