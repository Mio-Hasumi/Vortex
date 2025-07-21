//
//  ChatLive.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/19/25.
//

import SwiftUI
import AVFoundation

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

            Text("Let's talk about \(matchData.hashtags.first ?? "#general")")
                .font(.custom("Rajdhani", size: 40))
                .foregroundColor(.white)
                .padding(.bottom, 150)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom)

            // Dynamic participant display
            ZStack {
                ForEach(Array(matchData.participants.enumerated()), id: \.offset) { index, participant in
                    let offsets = getParticipantOffset(for: index, total: matchData.participants.count)
                    
                    ParticipantView(participant: participant)
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
    
    var body: some View {
        VStack {
            // Use default profile image for now, could be enhanced with actual user avatars
            let profileImage = participant.isCurrentUser ? "profile1" : "profile\(min(Int.random(in: 1...3), 3))"
            
            CirclePic(asset: profileImage)
            
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

// LiveKit service for managing the audio call
class LiveKitCallService: ObservableObject {
    @Published var isConnected = false
    @Published var isMuted = false
    @Published var participants: [MatchParticipant] = []
    
    private var audioSession: AVAudioSession?
    
    init() {
        setupAudioSession()
    }
    
    private func setupAudioSession() {
        do {
            audioSession = AVAudioSession.sharedInstance()
            try audioSession?.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker])
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
            self.isConnected = true
        }
        
        // TODO: Implement actual LiveKit connection
        // This would integrate with the LiveKit iOS SDK
        // For now, we simulate a successful connection
        
        print("✅ [LiveKit] Connected to live audio call")
        print("   🏷️ Room: \(roomId)")
        print("   👥 Participants: \(participants.count)")
    }
    
    func disconnect() {
        print("🔌 [LiveKit] Disconnecting from live call")
        
        isConnected = false
        isMuted = false
        participants = []
        
        // TODO: Implement actual LiveKit disconnection
        print("✅ [LiveKit] Disconnected successfully")
    }
    
    func toggleMute() {
        isMuted.toggle()
        print("🔇 [LiveKit] Audio \(isMuted ? "muted" : "unmuted")")
        
        // TODO: Implement actual mute/unmute with LiveKit SDK
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
