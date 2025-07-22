//
//  ChatLive.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/19/25.
//

import SwiftUI
import AVFoundation
// LiveKit imports
import LiveKit
import LiveKitComponents

struct HashtagScreen: View {
    let matchData: LiveMatchData
    @Environment(\.dismiss) private var dismiss
    
    @StateObject private var liveKitService = LiveKitCallService()
    @State private var showHangUpConfirmation = false
    @State private var isIntentionallyLeaving = false
    @State private var participantLeftMessage: String? = nil
    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            Image("sidebar")
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: 50, height: 204)
                .shadow(color: .white, radius: 12)
                .padding(.top, -120)
                .padding(.leading, 4)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)

            Image("orb")
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: 170, height: 170)
                .overlay(
                    LinearGradient(
                        gradient: Gradient(stops: [
                            .init(color: .clear,                   location: 0.0),
                            .init(color: Color.black.opacity(0.4), location: 0.3),
                            .init(color: Color.black.opacity(0.7), location: 1.0)
                        ]),
                        startPoint: .top, endPoint: .bottom
                    )
                )
                .overlay(
                    RadialGradient(
                        gradient: Gradient(colors: [.clear, Color.black.opacity(0.5)]),
                        center: .center, startRadius: 0, endRadius: 85
                    )
                )
                .padding(.top, 8)
                .padding(.trailing, 8)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topTrailing)

            
                .font(.custom("Rajdhani", size: 40))
                .foregroundColor(.white)
                .padding(.bottom, 150)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom)

            // Dynamic participant display
            ZStack {
                ForEach(Array(liveKitService.participants.enumerated()), id: \.offset) { index, participant in
                    let offsets = getParticipantOffset(for: index, total: liveKitService.participants.count)
                    
                    ParticipantView(participant: participant, isConnected: liveKitService.isConnected)
                        .offset(x: offsets.x, y: offsets.y)
                        .shadow(color: participant.isCurrentUser ? .blue.opacity(0.5) : .white.opacity(0.3), 
                               radius: 15, x: 0, y: 0)
                        .animation(.easeInOut(duration: 0.3), value: liveKitService.participants.count) // Smooth animation when participants change
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
            .padding(.bottom, 140)

            Image("pullhandle")
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: 120, height: 50)
                .shadow(color: Color.white.opacity(0.25), radius: 2)
                .offset(y: 38)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom)

            // Hang up button with proper cleanup
            VStack {
                HStack {
                    Spacer()
                    Button(action: {
                        print("📞 [CHAT] User tapped hang up button - showing confirmation")
                        showHangUpConfirmation = true
                    }) {
                        Image("X circle")
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                            .frame(width: 60, height: 60)
                            .foregroundColor(.red)
                            .shadow(color: .red.opacity(0.6), radius: 15)
                            .scaleEffect(showHangUpConfirmation ? 1.1 : 1.0)
                            .animation(.easeInOut(duration: 0.2), value: showHangUpConfirmation)
                    }
                }
                .padding()
                Spacer()
            }
            
            // Mute/Unmute button
            VStack {
                Spacer()
                
                Button(action: {
                    liveKitService.toggleMute()
                }) {
                    Image(systemName: liveKitService.isMuted ? "mic.slash.fill" : "mic.fill")
                        .font(.system(size: 30))
                        .foregroundColor(liveKitService.isMuted ? .red : .white)
                        .padding(15)
                        .background(Circle().fill(Color.white.opacity(0.2)))
                }
                .padding(.bottom, 80)
            }
            
            // Connection status indicator
            VStack {
                HStack {
                    Spacer()
                    HStack {
                        Circle()
                            .fill(liveKitService.isConnected ? .green : .red)
                            .frame(width: 8, height: 8)
                        Text(liveKitService.isConnected ? "Connected" : "Connecting...")
                            .font(.caption)
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Capsule().fill(Color.black.opacity(0.6)))
                }
                .padding()
                Spacer()
            }
            
            // Participant left notification
            if let message = participantLeftMessage {
                VStack {
                    HStack {
                        Spacer()
                        Text(message)
                            .font(.caption)
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(Capsule().fill(Color.red.opacity(0.8)))
                            .transition(.opacity)
                    }
                    .padding(.top, 60)
                    Spacer()
                }
            }
        }
        .onAppear {
            print("📱 [CHAT] View appeared - connecting to LiveKit")
            
            // Set up participant left callback
            liveKitService.onParticipantLeft = { displayName in
                withAnimation(.easeIn(duration: 0.3)) {
                    participantLeftMessage = "\(displayName) left the call"
                }
                
                // Hide the message after 3 seconds
                DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
                    withAnimation(.easeOut(duration: 0.5)) {
                        participantLeftMessage = nil
                    }
                }
            }
            
            // Connect to LiveKit when view appears
            Task {
                await liveKitService.connect(
                    roomId: matchData.roomId,
                    token: matchData.livekitToken,
                    participants: matchData.participants
                )
            }
        }
        .onDisappear {
            print("📱 [CHAT] View disappeared - isIntentionallyLeaving: \(isIntentionallyLeaving)")
            
            // Only cleanup if the user intentionally left (hang up button) or after a delay for other cases
            if isIntentionallyLeaving {
                print("📱 [CHAT] User intentionally left - immediate cleanup")
                if liveKitService.hasConnected {
                    liveKitService.disconnect()
                }
            } else {
                // Add a longer delay to prevent premature cleanup during navigation transitions
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                    // Only disconnect if we're still not connected to prevent cleanup during normal operation
                    if liveKitService.hasConnected && !liveKitService.isDisconnecting && !liveKitService.isConnected {
                        print("📱 [CHAT] Cleaning up LiveKit connection after delay (connection lost)")
                        liveKitService.disconnect()
                    } else {
                        print("⚠️ [CHAT] Skipping cleanup - connection still active or already disconnecting")
                    }
                }
            }
        }
        .navigationBarHidden(true)
        .alert("End Call", isPresented: $showHangUpConfirmation) {
            Button("Cancel", role: .cancel) {
                showHangUpConfirmation = false
            }
                            Button("End Call", role: .destructive) {
                    print("📞 [CHAT] User confirmed hang up - ending call")
                    isIntentionallyLeaving = true
                    liveKitService.disconnect()
                    
                    // CRITICAL: Clear match data from AI service to prevent auto-navigation to old matches
                    print("🧹 [CHAT] Clearing AI service match data to prevent auto-navigation")
                    AIVoiceService.shared.clearMatchData()
                    
                    // Cleanup AI service when user intentionally leaves
                    print("🧹 [CHAT] Cleaning up AI service on intentional exit")
                    NotificationCenter.default.post(name: NSNotification.Name("CleanupAIServices"), object: nil)
                    
                    // Reset navigation state to return to home
                    print("🔄 [CHAT] Resetting navigation state to return home")
                    VoiceMatchingService.shared.resetNavigation()
                    
                    // Navigate back to home screen
                    dismiss()
                }
        } message: {
            Text("Are you sure you want to end this call? You'll be returned to the home screen.")
        }
    }
}

    // Helper function to position participants in a circle
    private func getParticipantOffset(for index: Int, total: Int) -> (x: CGFloat, y: CGFloat) {
        switch total {
        case 1:
            return (0, 0)
        case 2:
            return index == 0 ? (-80, 0) : (80, 0)
        case 3:
            let positions = [(-100, -100), (100, 0), (-100, 70)]
            return (CGFloat(positions[index].0), CGFloat(positions[index].1))
        default:
            // For more participants, arrange in a circle
            let angle = (2 * Double.pi / Double(total)) * Double(index)
            let radius: CGFloat = 100
            let x = radius * cos(angle)
            let y = radius * sin(angle)
            return (x, y)
        }
    }


// Participant view component
private struct ParticipantView: View {
    let participant: MatchParticipant
    let isConnected: Bool
    
    var body: some View {
        VStack {
            // Use default profile image for now, could be enhanced with actual user avatars
            let profileImage = participant.isCurrentUser ? "profile1" : "profile\(min(Int.random(in: 1...3), 3))"
            
            CirclePic(asset: profileImage)
                .overlay(
                    // Audio indicator
                    Circle()
                        .stroke(isConnected ? .green : .gray, lineWidth: 3)
                        .scaleEffect(isConnected ? 1.1 : 1.0)
                        .animation(.easeInOut(duration: 0.5).repeatForever(autoreverses: true), value: isConnected)
                )
            
            Text(participant.displayName)
                .font(.custom("Rajdhani", size: 14))
                .foregroundColor(.white)
                .padding(.top, 5)
        }
    }
}

private struct CirclePic: View {
    let asset: String
    var body: some View {
        Image(asset)
            .resizable()
            .aspectRatio(contentMode: .fill)
            .frame(width: 120, height: 120)
            .clipShape(Circle())
            .shadow(radius: 3)
    }
}

// Real LiveKit service implementation
@MainActor
class LiveKitCallService: ObservableObject, @unchecked Sendable {
    @Published var isConnected = false
    @Published var isMuted = false
    @Published var participants: [MatchParticipant] = []
    @Published var connectionState: String = "Disconnected"
    
    // MARK: - LiveKit Integration
    private var room: Room?
    private var localParticipant: LocalParticipant?
    
    // Audio session for LiveKit
    private var audioSession: AVAudioSession?
    private var isSimulatingConnection = false
    private(set) var hasConnected = false  // Track if we've successfully connected
    private(set) var isDisconnecting = false  // Prevent multiple disconnects
    
    init() {
        setupAudioSession()
    }
    
    private func setupAudioSession() {
        do {
            audioSession = AVAudioSession.sharedInstance()
            // Configure for voice chat with echo cancellation (removed defaultToSpeaker to prevent feedback)
            try audioSession?.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth])
            try audioSession?.setActive(true)
            print("✅ [LiveKit] Audio session configured for voice chat with echo cancellation")
        } catch {
            print("❌ [LiveKit] Audio session setup failed: \(error)")
        }
    }
    

    
    func connect(roomId: String, token: String, participants: [MatchParticipant]) async {
        print("🔗 [LiveKit] Connecting to room: \(roomId)")
        
        await MainActor.run {
            // Initialize with the provided participants from match data
            self.participants = participants
            self.connectionState = "Connecting..."
            self.hasConnected = false
            self.isDisconnecting = false
            print("👥 [LiveKit] Initialized with \(participants.count) participants from match data")
        }
        
        // REAL LIVEKIT IMPLEMENTATION:
        do {
            room = Room()
            
            // Configure connect options for voice-only
            let connectOptions = ConnectOptions(
                autoSubscribe: true
            )
            
            try await room?.connect(
                url: "wss://voodooo-5oh49lvx.livekit.cloud", // Your LiveKit server URL
                token: token,
                connectOptions: connectOptions
            )
            
            // Enable microphone after connecting
            try await room?.localParticipant.setMicrophone(enabled: true)
            
            // Set up event handlers
            setupRoomEventHandlers()
            
            await MainActor.run {
                self.isConnected = true
                self.connectionState = "Connected"
                self.localParticipant = self.room?.localParticipant
                self.hasConnected = true  // Mark as successfully connected
            }
            
            print("✅ [LiveKit] Successfully connected to room!")
            
        } catch {
            print("❌ [LiveKit] Failed to connect: \(error)")
            await MainActor.run {
                self.connectionState = "Connection failed"
                self.isConnected = false
                self.hasConnected = false
            }
        }
        
        print("✅ [LiveKit] Connected to live audio call")
        print("   🏷️ Room: \(roomId)")
        print("   👥 Participants: \(participants.count)")
    }
    
    // REAL LIVEKIT EVENT HANDLERS:
    private func setupRoomEventHandlers() {
        guard let room = room else { return }
        
        // Handle participant connections
        room.add(delegate: self)
        
        print("✅ [LiveKit] Room event handlers configured")
    }
    
    func disconnect() {
        print("🔌 [LiveKit] Disconnect requested - hasConnected: \(hasConnected), isDisconnecting: \(isDisconnecting)")
        
        // Prevent multiple disconnects
        guard !isDisconnecting else {
            print("⚠️ [LiveKit] Already disconnecting, ignoring duplicate request")
            return
        }
        
        // Only disconnect if we actually have a connection
        guard hasConnected, room != nil else {
            print("⚠️ [LiveKit] No active connection to disconnect")
            return
        }
        
        isDisconnecting = true
        
        // REAL LIVEKIT DISCONNECT:
        Task { @MainActor in
            if let room = room {
                print("🔌 [LiveKit] Disconnecting from room...")
                await room.disconnect()
            } else {
                print("⚠️ [LiveKit] No room to disconnect from")
            }
            
            self.room = nil
            self.localParticipant = nil
            self.isConnected = false
            self.connectionState = "Disconnected"
            self.isMuted = false
            // Clear all participants when disconnecting
            self.participants = []
            self.isSimulatingConnection = false
            self.hasConnected = false
            self.isDisconnecting = false
            
            print("✅ [LiveKit] Disconnected successfully")
            print("👥 [LiveKit] Cleared all participants from UI")
        }
    }
    
    func toggleMute() {
        isMuted.toggle()
        print("🔇 [LiveKit] Audio \(isMuted ? "muted" : "unmuted")")
        
        // REAL LIVEKIT MUTE:
        Task { @MainActor in
            try? await localParticipant?.setMicrophone(enabled: !isMuted)
        }
    }
    
    // Callback for participant left notifications
    var onParticipantLeft: ((String) -> Void)?
    
    private func showParticipantLeftNotification(_ displayName: String) {
        onParticipantLeft?(displayName)
    }
}

// MARK: - LiveKit Room Delegate
extension LiveKitCallService: RoomDelegate {
    // Handle new participants joining
    nonisolated func room(_ room: Room, participantDidConnect participant: RemoteParticipant) {
        print("🎉 [LiveKit] Participant joined: \(participant.identity)")
        // LiveKit will automatically handle audio track subscriptions
        
        Task { @MainActor in
            let participantId: String
            if let identity = participant.identity {
                participantId = String(describing: identity)
            } else {
                participantId = "unknown"
            }
            
            print("🔍 [LiveKit] Adding participant with ID: '\(participantId)'")
            
            // Check if participant is already in our list (avoid duplicates)
            // Try both with and without "user_" prefix to handle format differences
            let cleanParticipantId = participantId.replacingOccurrences(of: "user_", with: "")
            let possibleIds = [participantId, cleanParticipantId]
            
            let alreadyExists = possibleIds.contains { id in
                self.participants.contains(where: { $0.userId == id })
            }
            
            if !alreadyExists {
                // Use the clean ID (without "user_" prefix) for consistency with match data
                let newParticipant = MatchParticipant(
                    userId: cleanParticipantId,
                    displayName: "User \(String(cleanParticipantId.prefix(8)))", // Use first 8 chars of clean ID
                    isCurrentUser: false
                )
                
                self.participants.append(newParticipant)
                print("➕ [LiveKit] Added new participant to UI: \(newParticipant.displayName) (clean ID: '\(cleanParticipantId)')")
            } else {
                print("⚠️ [LiveKit] Participant already exists in UI, skipping duplicate")
            }
            
            print("📊 [LiveKit] Total participants now: \(room.remoteParticipants.count + 1)")
            print("👥 [LiveKit] Participants in UI: \(self.participants.count)")
        }
    }
    
    // Handle participants leaving
    nonisolated func room(_ room: Room, participantDidDisconnect participant: RemoteParticipant) {
        print("👋 [LiveKit] Participant left: \(participant.identity)")
        
        Task { @MainActor in
            // Remove the participant from our local participant list
            let participantId: String
            if let identity = participant.identity {
                participantId = String(describing: identity)
            } else {
                participantId = "unknown"
            }
            
            print("🔍 [LiveKit] Looking for participant to remove with ID: '\(participantId)'")
            print("📋 [LiveKit] Current participants in UI:")
            for (index, p) in self.participants.enumerated() {
                print("   [\(index)] userId: '\(p.userId)', displayName: '\(p.displayName)', isCurrentUser: \(p.isCurrentUser)")
            }
            
            // Find and remove the participant from our list
            // Try both with and without "user_" prefix to handle LiveKit format differences
            let possibleIds = [participantId, participantId.replacingOccurrences(of: "user_", with: "")]
            var removedParticipant: MatchParticipant?
            
            for possibleId in possibleIds {
                if let index = self.participants.firstIndex(where: { $0.userId == possibleId }) {
                    removedParticipant = self.participants.remove(at: index)
                    print("🗑️ [LiveKit] Removed participant from UI: \(removedParticipant!.displayName) (matched with ID: '\(possibleId)')")
                    break
                }
            }
            
            if let participant = removedParticipant {
                // Show notification that participant left
                self.showParticipantLeftNotification(participant.displayName)
            } else {
                print("❌ [LiveKit] Could not find participant with ID '\(participantId)' to remove from UI")
                print("❌ [LiveKit] Tried IDs: \(possibleIds)")
                print("❌ [LiveKit] Available participant IDs: \(self.participants.map { $0.userId })")
            }
            
            print("📊 [LiveKit] Remaining participants in room: \(room.remoteParticipants.count)")
            print("👥 [LiveKit] Participants in UI: \(self.participants.count)")
            
            // Show notification when you're alone
            if room.remoteParticipants.isEmpty {
                print("ℹ️ [LiveKit] You are now alone in the call")
                // Could show a UI notification here if desired
            }
        }
    }
    
    // Implement required delegate methods for handling room events
    nonisolated func room(_ room: Room, didUpdateConnectionState connectionState: ConnectionState, from oldValue: ConnectionState) {
        print("🔄 [LiveKit] Connection state changed: \(oldValue) -> \(connectionState)")
        
        Task { @MainActor in
            switch connectionState {
            case .connected:
                print("✅ [LiveKit] Room delegate: Connected")
                self.connectionState = "Connected"
                self.isConnected = true
                self.hasConnected = true
            case .connecting:
                print("🔄 [LiveKit] Room delegate: Connecting...")
                self.connectionState = "Connecting..."
                self.isConnected = false
            case .disconnected:
                print("❌ [LiveKit] Room delegate: Disconnected")
                self.connectionState = "Disconnected"
                self.isConnected = false
                // Don't reset hasConnected here as it might be a temporary disconnection
            case .reconnecting:
                print("🔄 [LiveKit] Room delegate: Reconnecting...")
                self.connectionState = "Reconnecting..."
                self.isConnected = false
            default:
                print("❓ [LiveKit] Room delegate: Unknown state")
                self.connectionState = "Unknown"
            }
        }
    }
}

#Preview {
    // Preview with mock data
    let mockMatchData = LiveMatchData(
        matchId: "preview_match",
        sessionId: "preview_session",
        roomId: "preview_room",
        livekitToken: "mock_token",
        participants: [
            MatchParticipant(userId: "user1", displayName: "You", isCurrentUser: true),
            MatchParticipant(userId: "user2", displayName: "Alex", isCurrentUser: false)
        ],
        topics: ["Artificial Intelligence", "Technology"],
        hashtags: ["#AI", "#Tech"]
    )
    HashtagScreen(matchData: mockMatchData)
}
