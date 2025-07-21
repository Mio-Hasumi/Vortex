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
                ForEach(Array(matchData.participants.enumerated()), id: \.offset) { index, participant in
                    let offsets = getParticipantOffset(for: index, total: matchData.participants.count)
                    
                    ParticipantView(participant: participant, isConnected: liveKitService.isConnected)
                        .offset(x: offsets.x, y: offsets.y)
                        .shadow(color: participant.isCurrentUser ? .blue.opacity(0.5) : .white.opacity(0.3), 
                               radius: 15, x: 0, y: 0)
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

            // Back button with proper cleanup
            VStack {
                HStack {
                    Button(action: {
                        liveKitService.disconnect()
                        dismiss()
                    }) {
                        Image(systemName: "arrow.left")
                            .font(.title2)
                            .foregroundColor(.white)
                    }
                    Spacer()
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
        }
        .onAppear {
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
            // Clean up when leaving
            liveKitService.disconnect()
        }
        .navigationBarHidden(true)
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
    
    init() {
        setupAudioSession()
    }
    
    private func setupAudioSession() {
        do {
            audioSession = AVAudioSession.sharedInstance()
            // Configure for voice chat with speaker output
            try audioSession?.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
            try audioSession?.setActive(true)
            print("✅ [LiveKit] Audio session configured for voice chat")
        } catch {
            print("❌ [LiveKit] Audio session setup failed: \(error)")
        }
    }
    

    
    func connect(roomId: String, token: String, participants: [MatchParticipant]) async {
        print("🔗 [LiveKit] Connecting to room: \(roomId)")
        
        await MainActor.run {
            self.participants = participants
            self.connectionState = "Connecting..."
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
            
            self.isConnected = true
            self.connectionState = "Connected"
            self.localParticipant = self.room?.localParticipant
            
            print("✅ [LiveKit] Successfully connected to room!")
            
        } catch {
            print("❌ [LiveKit] Failed to connect: \(error)")
            self.connectionState = "Connection failed"
            self.isConnected = false
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
    
    // Handle new participants joining
    nonisolated func room(_ room: Room, participantDidConnect participant: RemoteParticipant) {
        print("🎉 [LiveKit] Participant joined: \(participant.identity)")
        // LiveKit will automatically handle audio track subscriptions
    }
    
    // Handle participants leaving
    nonisolated func room(_ room: Room, participantDidDisconnect participant: RemoteParticipant) {
        print("👋 [LiveKit] Participant left: \(participant.identity)")
    }
    
    func disconnect() {
        print("🔌 [LiveKit] Disconnecting from live call")
        
        // REAL LIVEKIT DISCONNECT:
        Task { @MainActor in
            await room?.disconnect()
            self.room = nil
            self.localParticipant = nil
            self.isConnected = false
            self.connectionState = "Disconnected"
            self.isMuted = false
            self.participants = []
            self.isSimulatingConnection = false
        }
        
        print("✅ [LiveKit] Disconnected successfully")
    }
    
    func toggleMute() {
        isMuted.toggle()
        print("🔇 [LiveKit] Audio \(isMuted ? "muted" : "unmuted")")
        
        // REAL LIVEKIT MUTE:
        Task { @MainActor in
            try? await localParticipant?.setMicrophone(enabled: !isMuted)
        }
    }
    

}

// MARK: - LiveKit Room Delegate
extension LiveKitCallService: RoomDelegate {
    // Implement required delegate methods for handling room events
    nonisolated func room(_ room: Room, didUpdateConnectionState connectionState: ConnectionState, from oldValue: ConnectionState) {
        Task { @MainActor in
            switch connectionState {
            case .connected:
                self.connectionState = "Connected"
                self.isConnected = true
            case .connecting:
                self.connectionState = "Connecting..."
                self.isConnected = false
            case .disconnected:
                self.connectionState = "Disconnected"
                self.isConnected = false
            case .reconnecting:
                self.connectionState = "Reconnecting..."
                self.isConnected = false
            default:
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
