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
    let requests = [
        FriendRequest(name: "David Brown", mutualFriends: 3),
        FriendRequest(name: "Emma Davis", mutualFriends: 1)
    ]
    
    var body: some View {
        List(requests) { request in
            FriendRequestRow(request: request)
        }
        .listStyle(PlainListStyle())
        .background(Color.black)
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
    let request: FriendRequest
    
    var body: some View {
        VStack(spacing: 12) {
            HStack(spacing: 12) {
                Circle()
                    .fill(Color.purple.opacity(0.8))
                    .frame(width: 50, height: 50)
                    .overlay(
                        Text(String(request.name.prefix(1)))
                            .font(.title3)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                    )
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(request.name)
                        .font(.body)
                        .fontWeight(.medium)
                        .foregroundColor(.white)
                    
                    Text("\(request.mutualFriends) mutual friends")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                
                Spacer()
            }
            
            HStack(spacing: 12) {
                Button("Accept") {
                    // TODO: Accept friend request
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 8)
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(8)
                
                Button("Decline") {
                    // TODO: Reject friend request
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 8)
                .background(Color.gray.opacity(0.3))
                .foregroundColor(.white)
                .cornerRadius(8)
                
                Spacer()
            }
        }
        .padding(.vertical, 8)
        .background(Color.black)
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

struct FriendRequest: Identifiable {
    let id = UUID()
    let name: String
    let mutualFriends: Int
}

#Preview {
    FriendsView()
} 