import Foundation
import Combine
import LiveKit
import AVFoundation
import SwiftUI
import FirebaseAuth

class WaitingRoomService: NSObject, ObservableObject, WebSocketDelegate {
    @Published var isConnectedToLiveKit = false
    @Published var isMuted = false
    @Published var matchFound: LiveMatchData?

    private var room: Room?
    private var matchingWebSocket: WebSocketService?
    
    override init() {
        super.init()
        setupAudioSession()
    }
    
    private func setupAudioSession() {
        do {
            try AVAudioSession.sharedInstance().setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth])
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            print("Failed to setup audio session for waiting room: \(error)")
        }
    }

    func connect(waitingRoomInfo: WaitingRoomResponse) {
        // 1. Connect to LiveKit to talk to the agent
        Task {
            do {
                let room = Room()
                self.room = room
                try await room.connect(
                    url: "wss://voodooo-5oh49lvx.livekit.cloud",
                    token: waitingRoomInfo.user_token
                )
                try await room.localParticipant.setMicrophone(enabled: true)
                await MainActor.run {
                    self.isConnectedToLiveKit = true
                }
            } catch {
                print("Failed to connect to waiting room LiveKit: \(error)")
            }
        }
        
        // 2. Connect to the matching WebSocket to listen for a match
        guard let userId = Auth.auth().currentUser?.uid, let token = AuthService.shared.firebaseToken else {
             print("User not authenticated, cannot connect to matching service.")
             return
         }
        
        self.matchingWebSocket = WebSocketService()
        self.matchingWebSocket?.delegate = self
        let matchingEndpoint = "\(APIConfig.WebSocket.matching)?user_id=\(userId)"
        self.matchingWebSocket?.connect(to: matchingEndpoint, with: token)
    }

    func disconnect() {
        Task {
            await room?.disconnect()
        }
        matchingWebSocket?.disconnect()
        self.room = nil
        self.matchingWebSocket = nil
        DispatchQueue.main.async {
            self.isConnectedToLiveKit = false
        }
    }

    func toggleMute() {
        guard let localParticipant = room?.localParticipant else { return }
        isMuted.toggle()
        Task {
            try? await localParticipant.setMicrophone(enabled: !isMuted)
        }
    }
    
    // MARK: - WebSocketDelegate
    
    func webSocketDidConnect(_ webSocket: WebSocketService) {
        print("✅ Matching WebSocket connected for waiting room.")
    }
    
    func webSocketDidDisconnect(_ webSocket: WebSocketService) {
        print("🔌 Matching WebSocket disconnected for waiting room.")
    }
    
    func webSocket(_ webSocket: WebSocketService, didReceiveMessage message: [String : Any]) {
        if let type = message["type"] as? String, type == "match_found" {
            print("🎉 Match found via WebSocket!")
            
            guard let matchId = message["match_id"] as? String,
                  let sessionId = message["session_id"] as? String,
                  let roomId = message["room_id"] as? String,
                  let livekitToken = message["livekit_token"] as? String else {
                print("❌ Invalid match data received")
                return
            }

            let participantsData = message["participants"] as? [[String: Any]] ?? []
            let participants = participantsData.compactMap { data -> MatchParticipant? in
                guard let userId = data["user_id"] as? String,
                      let displayName = data["display_name"] as? String,
                      let isCurrentUser = data["is_current_user"] as? Bool else {
                    return nil
                }
                let isAIHost = data["is_ai_host"] as? Bool ?? false
                return MatchParticipant(userId: userId, displayName: displayName, isCurrentUser: isCurrentUser, isAIHost: isAIHost)
            }
            
            let topics = message["topics"] as? [String] ?? []
            let hashtags = message["hashtags"] as? [String] ?? []
            
            let liveMatchData = LiveMatchData(matchId: matchId, sessionId: sessionId, roomId: roomId, livekitToken: livekitToken, participants: participants, topics: topics, hashtags: hashtags)
            
            DispatchQueue.main.async {
                self.matchFound = liveMatchData
            }
        }
    }
    
    func webSocket(_ webSocket: WebSocketService, didEncounterError error: Error) {
        print("❌ Matching WebSocket error in waiting room: \(error)")
    }
} 