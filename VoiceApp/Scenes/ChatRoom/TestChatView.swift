import SwiftUI
import LiveKit
import LiveKitComponents
import FirebaseAuth

struct TestChatView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var liveKitService = LiveKitCallService()
    @State private var showHangUpConfirmation = false
    @State private var isConnecting = false
    @State private var errorMessage: String?
    
    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            
            VStack(spacing: 20) {
                // Header
                HStack {
                    Button("Back") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                    .padding()
                    
                    Spacer()
                    
                    Text("Test Chat Room")
                        .font(.title2)
                        .foregroundColor(.white)
                    
                    Spacer()
                    
                    Button("Leave") {
                        showHangUpConfirmation = true
                    }
                    .foregroundColor(.red)
                    .padding()
                }
                
                // Room Info
                VStack(spacing: 12) {
                    Text("Test Room")
                        .font(.title)
                        .foregroundColor(.white)
                    
                    Text("Topic: Testing Live Chat Functionality")
                        .font(.subheadline)
                        .foregroundColor(.gray)
                    
                    Text("This is a test room for testing live chat features")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                .padding()
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.white.opacity(0.1))
                )
                
                // Connection Status
                HStack {
                    Circle()
                        .fill(liveKitService.isConnected ? .green : .red)
                        .frame(width: 12, height: 12)
                    
                    Text(liveKitService.isConnected ? "Connected" : "Disconnected")
                        .foregroundColor(.white)
                    
                    Spacer()
                }
                .padding(.horizontal)
                
                // LiveKit Controls
                VStack(spacing: 16) {
                    // Connect Button
                    Button(action: {
                        Task {
                            await connectToTestRoom()
                        }
                    }) {
                        HStack {
                            if isConnecting {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                    .scaleEffect(0.8)
                            } else {
                                Image(systemName: "phone.fill")
                            }
                            Text(isConnecting ? "Connecting..." : "Connect to Test Room")
                        }
                        .foregroundColor(.white)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(liveKitService.isConnected ? .gray : .blue)
                        )
                    }
                    .disabled(liveKitService.isConnected || isConnecting)
                    
                    // Mute Button
                    Button(action: {
                        liveKitService.toggleMute()
                    }) {
                        HStack {
                            Image(systemName: liveKitService.isMuted ? "mic.slash.fill" : "mic.fill")
                            Text(liveKitService.isMuted ? "Unmute" : "Mute")
                        }
                        .foregroundColor(.white)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(liveKitService.isMuted ? .red : .green)
                        )
                    }
                    .disabled(!liveKitService.isConnected)
                    
                    // AI Host Toggle
                    Button(action: {
                        liveKitService.isAIListening.toggle()
                    }) {
                        HStack {
                            Image(systemName: liveKitService.isAIListening ? "brain.head.profile.fill" : "brain.head.profile")
                            Text(liveKitService.isAIListening ? "AI Listening" : "AI Host Off")
                        }
                        .foregroundColor(.white)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(liveKitService.isAIListening ? .purple : .gray)
                        )
                    }
                    .disabled(!liveKitService.isConnected)
                }
                .padding(.horizontal)
                
                // Error Message
                if let errorMessage = errorMessage {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .font(.caption)
                        .padding()
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.red.opacity(0.1))
                        )
                        .padding(.horizontal)
                }
                
                // Participants
                VStack(alignment: .leading, spacing: 8) {
                    Text("Participants (\(liveKitService.participants.count))")
                        .font(.headline)
                        .foregroundColor(.white)
                    
                    ForEach(liveKitService.participants, id: \.userId) { participant in
                        HStack {
                            Circle()
                                .fill(participant.isCurrentUser ? .blue : .green)
                                .frame(width: 8, height: 8)
                            
                            Text(participant.displayName)
                                .foregroundColor(.white)
                            
                            if participant.isCurrentUser {
                                Text("(You)")
                                    .foregroundColor(.blue)
                                    .font(.caption)
                            }
                            
                            Spacer()
                        }
                        .padding(.horizontal)
                    }
                }
                .padding()
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.white.opacity(0.1))
                )
                
                Spacer()
            }
        }
        .navigationBarHidden(true)
        .onAppear {
            print("🧪 [TestChatView] View appeared")
        }
        .onDisappear {
            print("🧪 [TestChatView] View disappeared, cleaning up")
            if liveKitService.isConnected {
                liveKitService.disconnect()
            }
        }
        .alert("Leave Room", isPresented: $showHangUpConfirmation) {
            Button("Cancel", role: .cancel) { }
            Button("Leave", role: .destructive) {
                leaveRoom()
            }
        } message: {
            Text("Are you sure you want to leave this test room?")
        }
    }
    
    private func connectToTestRoom() async {
        print("🧪 [TestChatView] Creating and connecting to test room")
        
        await MainActor.run {
            isConnecting = true
            errorMessage = nil
        }
        
        // Check if user is authenticated
        guard let currentUser = Auth.auth().currentUser else {
            await MainActor.run {
                errorMessage = "You must be signed in to create a test room"
                isConnecting = false
            }
            return
        }
        
        do {
            // Get fresh Firebase ID token
            let token = try await currentUser.getIDToken(forcingRefresh: true)
            print("🧪 [TestChatView] Got Firebase token: \(String(token.prefix(20)))...")
            
            // Set the token in APIService
            APIService.shared.setAuthToken(token)
            
            // Step 1: Create a test room
            let createRequest = CreateRoomRequest(
                name: "Test Room \(Int.random(in: 1000...9999))",
                topic: "Testing Live Chat Functionality",
                max_participants: 4,
                is_private: false
            )
            
            let jsonData = try JSONEncoder().encode(createRequest)
            print("🧪 [TestChatView] Creating room with request: \(String(data: jsonData, encoding: .utf8) ?? "nil")")
            
            let room: RoomResponse = try await APIService.shared.request(
                endpoint: APIConfig.Endpoints.rooms,
                method: "POST",
                body: jsonData
            )
            
            print("✅ [TestChatView] Created room: \(room.name) with ID: \(room.id)")
            
            // Step 2: Join the room
            let joinRequest = JoinRoomRequest(room_id: room.id)
            let joinJsonData = try JSONEncoder().encode(joinRequest)
            
            let updatedRoom: RoomResponse = try await APIService.shared.request(
                endpoint: APIConfig.Endpoints.joinRoom,
                method: "POST",
                body: joinJsonData
            )
            
            print("✅ [TestChatView] Joined room: \(updatedRoom.name)")
            
            // Step 3: Create participant and connect to LiveKit
            let testParticipant = MatchParticipant(
                userId: UUID().uuidString,
                displayName: "Test User",
                isCurrentUser: true,
                isAIHost: false
            )
            
            // Connect using the real room ID and LiveKit token
            await liveKitService.connect(
                roomId: updatedRoom.id,
                token: updatedRoom.livekit_token,
                participants: [testParticipant],
                livekitName: updatedRoom.livekit_room_name ?? updatedRoom.id,
                userId: testParticipant.userId
            )
            
            print("✅ [TestChatView] Connected to LiveKit room: \(updatedRoom.id)")
            
        } catch {
            print("❌ [TestChatView] Failed to create/join test room: \(error)")
            
            // Show error to user
            await MainActor.run {
                let errorMessage: String
                if let apiError = error as? APIError {
                    errorMessage = "Failed to create test room: \(apiError.message)"
                } else {
                    errorMessage = "Failed to create test room: \(error.localizedDescription)"
                }
                self.errorMessage = errorMessage
            }
        }
        
        await MainActor.run {
            isConnecting = false
        }
    }
    
    private func leaveRoom() {
        print("🧪 [TestChatView] Leaving test room")
        if liveKitService.isConnected {
            liveKitService.disconnect()
        }
        dismiss()
    }
}

#Preview {
    TestChatView()
        .preferredColorScheme(.dark)
}
