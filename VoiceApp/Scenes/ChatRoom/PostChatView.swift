import SwiftUI
import FirebaseAuth

struct PostChatView: View {
    let participants: [ChatParticipant]
    @Environment(\.dismiss) private var dismiss
    @StateObject private var friendService = FriendRequestService.shared
    @State private var showSuccessMessage = false
    @State private var successMessage = ""
    @State private var participantsWithStatus: [ChatParticipantWithStatus] = []
    
    var body: some View {
        NavigationView {
            ZStack {
                Color.black.ignoresSafeArea()
                
                VStack(spacing: 20) {
                    // Title
                    VStack(spacing: 8) {
                        Text("Chat Participants")
                            .font(.title)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                        
                        Text("Add people you'd like to stay connected with")
                            .font(.subheadline)
                            .foregroundColor(.gray)
                            .multilineTextAlignment(.center)
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 20)
                    
                    // Participants List
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(participantsWithStatus.filter { !$0.participant.isCurrentUser && !$0.participant.isAIHost }, id: \.participant.userId) { participantWithStatus in
                                ParticipantRowView(
                                    participantWithStatus: participantWithStatus,
                                    onSendRequest: { userId in
                                        Task {
                                            await sendFriendRequest(to: userId)
                                        }
                                    }
                                )
                            }
                        }
                        .padding(.horizontal, 20)
                    }
                    
                    Spacer()
                    
                    // Continue to Home button
                    Button("Continue to Home") {
                        // Reset navigation state before dismissing
                        VoiceMatchingService.shared.resetNavigation()
                        dismiss()
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 40)
                    .padding(.vertical, 15)
                    .background(Color.blue)
                    .cornerRadius(25)
                    .padding(.bottom, 30)
                }
            }
            .navigationTitle("Chat Participants")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarBackButtonHidden(true)
        }
        .onAppear {
            // Add a small delay to ensure the view is fully presented before loading data
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                Task {
                    await loadParticipantsWithStatus()
                }
            }
        }
        .alert("Friend Request", isPresented: $showSuccessMessage) {
            Button("OK") { }
        } message: {
            Text(successMessage)
        }
    }
    
    private func loadParticipantsWithStatus() async {
        var participantsWithStatusList: [ChatParticipantWithStatus] = []
        
        for participant in participants.filter({ !$0.isCurrentUser && !$0.isAIHost }) {
            do {
                let status = try await friendService.getFriendshipStatus(for: participant.userId)
                
                let participantWithStatus = ChatParticipantWithStatus(
                    participant: participant,
                    friendshipStatus: status
                )
                participantsWithStatusList.append(participantWithStatus)
            } catch {
                print("❌ Failed to get friendship status for \(participant.displayName): \(error)")
                let participantWithStatus = ChatParticipantWithStatus(
                    participant: participant,
                    friendshipStatus: "none"
                )
                participantsWithStatusList.append(participantWithStatus)
            }
        }
        
        await MainActor.run {
            self.participantsWithStatus = participantsWithStatusList
        }
    }
    
    private func sendFriendRequest(to userId: String) async {
        do {
            let result = try await friendService.sendFriendRequest(to: userId)
            await MainActor.run {
                successMessage = "Friend request sent to \(participants.first { $0.userId == userId }?.displayName ?? "user")!"
                showSuccessMessage = true
            }
            
            // Refresh participants status
            await loadParticipantsWithStatus()
        } catch {
            await MainActor.run {
                successMessage = "Failed to send friend request: \(error.localizedDescription)"
                showSuccessMessage = true
            }
        }
    }
}

// MARK: - Chat Participant with Friendship Status
struct ChatParticipantWithStatus {
    let participant: ChatParticipant
    let friendshipStatus: String
}

struct ParticipantRowView: View {
    let participantWithStatus: ChatParticipantWithStatus
    let onSendRequest: (String) -> Void
    
    var body: some View {
        HStack(spacing: 16) {
            // Profile Picture
            Circle()
                .fill(Color.purple.opacity(0.8))
                .frame(width: 50, height: 50)
                .overlay(
                    Text(String(participantWithStatus.participant.displayName.prefix(1)))
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                )
            
            // User Info
            VStack(alignment: .leading, spacing: 4) {
                Text(participantWithStatus.participant.displayName)
                    .font(.body)
                    .fontWeight(.medium)
                    .foregroundColor(.white)
                
                // Status text based on friendship status
                Text(statusText)
                    .font(.caption)
                    .foregroundColor(.gray)
            }
            
            Spacer()
            
            // Action Button based on friendship status
            actionButton
        }
        .padding(.vertical, 12)
        .padding(.horizontal, 16)
        .background(Color.white.opacity(0.05))
        .cornerRadius(12)
    }
    
    private var statusText: String {
        switch participantWithStatus.friendshipStatus {
        case "friends":
            return "Already friends"
        case "pending_sent":
            return "Friend request sent"
        case "pending_received":
            return "Sent you a friend request"
        case "blocked":
            return "User blocked"
        default:
            return "Tap + to send friend request"
        }
    }
    
    @ViewBuilder
    private var actionButton: some View {
        switch participantWithStatus.friendshipStatus {
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
                    // Show message to go to friend requests
                    print("ℹ️ Please go to Friends > Requests to accept this friend request")
                }
                .font(.caption)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(6)
                
                Button("Decline") {
                    // Show message to go to friend requests
                    print("ℹ️ Please go to Friends > Requests to reject this friend request")
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
                onSendRequest(participantWithStatus.participant.userId)
            }) {
                Image(systemName: "plus.circle.fill")
                    .font(.title2)
                    .foregroundColor(.blue)
            }
        }
    }
}

#Preview {
    PostChatView(participants: [])
}
