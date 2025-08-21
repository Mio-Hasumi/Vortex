import SwiftUI
import FirebaseAuth

struct PostChatView: View {
    let participants: [ChatParticipant]
    @Environment(\.dismiss) private var dismiss
    @StateObject private var friendService = FriendRequestService.shared
    @State private var showSuccessMessage = false
    @State private var successMessage = ""
    
    var body: some View {
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
                        ForEach(participants.filter { !$0.isCurrentUser && !$0.isAIHost }, id: \.userId) { participant in
                            ParticipantRowView(
                                participant: participant,
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
        .alert("Friend Request", isPresented: $showSuccessMessage) {
            Button("OK") { }
        } message: {
            Text(successMessage)
        }
    }
    
    private func sendFriendRequest(to userId: String) async {
        do {
            let result = try await friendService.sendFriendRequest(to: userId)
            await MainActor.run {
                successMessage = "Friend request sent to \(participants.first { $0.userId == userId }?.displayName ?? "user")!"
                showSuccessMessage = true
            }
        } catch {
            await MainActor.run {
                successMessage = "Failed to send friend request: \(error.localizedDescription)"
                showSuccessMessage = true
            }
        }
    }
}

struct ParticipantRowView: View {
    let participant: ChatParticipant
    let onSendRequest: (String) -> Void
    @State private var isRequestSent = false
    
    var body: some View {
        HStack(spacing: 16) {
            // Profile Picture
            Circle()
                .fill(Color.purple.opacity(0.8))
                .frame(width: 50, height: 50)
                .overlay(
                    Text(String(participant.displayName.prefix(1)))
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                )
            
            // User Info
            VStack(alignment: .leading, spacing: 4) {
                Text(participant.displayName)
                    .font(.body)
                    .fontWeight(.medium)
                    .foregroundColor(.white)
                
                Text("Tap + to send friend request")
                    .font(.caption)
                    .foregroundColor(.gray)
            }
            
            Spacer()
            
            // Plus Icon Button
            Button(action: {
                onSendRequest(participant.userId)
                isRequestSent = true
            }) {
                Image(systemName: isRequestSent ? "checkmark.circle.fill" : "plus.circle.fill")
                    .font(.title2)
                    .foregroundColor(isRequestSent ? .green : .blue)
            }
        }
        .padding(.vertical, 12)
        .padding(.horizontal, 16)
        .background(Color.white.opacity(0.05))
        .cornerRadius(12)
    }
}

#Preview {
    let sampleParticipants = [
        ChatParticipant(userId: "1", displayName: "John Doe", isCurrentUser: false, isAIHost: false),
        ChatParticipant(userId: "2", displayName: "Jane Smith", isCurrentUser: false, isAIHost: false),
        ChatParticipant(userId: "3", displayName: "Current User", isCurrentUser: true, isAIHost: false),
        ChatParticipant(userId: "4", displayName: "Vortex", isCurrentUser: false, isAIHost: true)
    ]
    
    PostChatView(participants: sampleParticipants)
}
