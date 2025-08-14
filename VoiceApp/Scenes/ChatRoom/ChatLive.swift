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
// WebSocket for AI control
import Foundation

struct HashtagScreen: View {
    let matchData: LiveMatchData
    @Environment(\.dismiss) private var dismiss
    
    @StateObject private var liveKitService = LiveKitCallService()
    @State private var showHangUpConfirmation = false
    @State private var isIntentionallyLeaving = false
    @State private var participantLeftMessage: String? = nil
    @State private var aiHostWelcomeMessage: String? = nil
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
                
                HStack(spacing: 20) {
                    // AI Control Button - Now functional with backend communication
                    Button(action: {
                        liveKitService.toggleAI()
                    }) {
                        Image(systemName: liveKitService.isAIListening ? "brain.head.profile.fill" : "brain.head.profile")
                            .font(.system(size: 30))
                            .foregroundColor(liveKitService.isAIListening ? .purple : .white)
                            .padding(15)
                            .background(Circle().fill(Color.white.opacity(0.2)))
                    }
                    
                    // Mute/Unmute button
                    Button(action: {
                        liveKitService.toggleMute()
                    }) {
                        Image(systemName: liveKitService.isMuted ? "mic.slash.fill" : "mic.fill")
                            .font(.system(size: 30))
                            .foregroundColor(liveKitService.isMuted ? .red : .white)
                            .padding(15)
                            .background(Circle().fill(Color.white.opacity(0.2)))
                    }
                }
                .padding(.bottom, 80)
            }
            
            // Connection status and AI host indicator
            VStack {
                HStack {
                    Spacer()
                    
                    // AI Listening indicator
                    if liveKitService.isAIListening {
                        HStack(spacing: 6) {
                            Image(systemName: "brain.head.profile.fill")
                                .font(.caption)
                                .foregroundColor(.purple)
                            Text("AI Listening...")
                                .font(.caption2)
                                .foregroundColor(.purple)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(Color.purple.opacity(0.2)))
                    }
                    
                    // AI Host indicator
                    if liveKitService.participants.contains(where: { $0.isAIHost }) {
                        HStack(spacing: 6) {
                            Image(systemName: "brain.head.profile")
                                .font(.caption)
                                .foregroundColor(.purple)
                            Text("AI Host Active")
                                .font(.caption2)
                                .foregroundColor(.purple)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(Color.purple.opacity(0.2)))
                    }
                    
                    // Connection status
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
            
            // AI Host welcome notification
            if let message = aiHostWelcomeMessage {
                VStack {
                    HStack {
                        Spacer()
                        HStack(spacing: 8) {
                            Image(systemName: "brain.head.profile")
                                .font(.caption)
                                .foregroundColor(.purple)
                            Text(message)
                                .font(.caption)
                                .foregroundColor(.white)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(Capsule().fill(LinearGradient(
                            gradient: Gradient(colors: [.purple, .blue]),
                            startPoint: .leading,
                            endPoint: .trailing
                        )))
                        .transition(.opacity)
                    }
                    .padding(.top, 100) // Offset below participant left message
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
            
            // Set up AI host welcome callback
            liveKitService.onAIHostWelcome = { welcomeMessage in
                withAnimation(.easeIn(duration: 0.3)) {
                    aiHostWelcomeMessage = welcomeMessage
                }
                
                // Hide the welcome message after 5 seconds
                DispatchQueue.main.asyncAfter(deadline: .now() + 5.0) {
                    withAnimation(.easeOut(duration: 0.5)) {
                        aiHostWelcomeMessage = nil
                    }
                }
            }
            
            // Connect to LiveKit when view appears
            Task {
                await liveKitService.connect(
                    roomId: matchData.roomId,
                    token: matchData.livekitToken,
                    participants: matchData.participants,
                    livekitName: matchData.livekitName,
                    userId: matchData.userId
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
    
    // Computed property for profile image
    private var profileImage: String {
        if participant.isAIHost {
            return "orb"
        } else if participant.isCurrentUser {
            return "profile1"
        } else {
            return "profile\(min(Int.random(in: 1...3), 3))"
        }
    }
    
    var body: some View {
        VStack {
            // AI Host gets special treatment with orb image
            if participant.isAIHost {
                Image("orb")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 120, height: 120)
                    .clipShape(Circle())
                    .shadow(radius: 3)
                    .overlay(
                        // Special AI indicator - pulsing purple ring
                        Circle()
                            .stroke(
                                LinearGradient(
                                    gradient: Gradient(colors: [.purple, .blue]),
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                ),
                                lineWidth: 4
                            )
                            .scaleEffect(isConnected ? 1.2 : 1.0)
                            .animation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true), value: isConnected)
                    )
                    .overlay(
                        // AI badge
                        VStack {
                            Spacer()
                            HStack {
                                Spacer()
                                Text("AI")
                                    .font(.caption2)
                                    .fontWeight(.bold)
                                    .foregroundColor(.white)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(
                                        Capsule()
                                            .fill(LinearGradient(
                                                gradient: Gradient(colors: [.purple, .blue]),
                                                startPoint: .leading,
                                                endPoint: .trailing
                                            ))
                                    )
                                    .offset(x: -10, y: -10)
                            }
                        }
                    )
            } else {
                // Regular participant view
                CirclePic(asset: profileImage)
                    .overlay(
                        // Audio indicator
                        Circle()
                            .stroke(isConnected ? .green : .gray, lineWidth: 3)
                            .scaleEffect(isConnected ? 1.1 : 1.0)
                            .animation(.easeInOut(duration: 0.5).repeatForever(autoreverses: true), value: isConnected)
                    )
            }
            
            Text(participant.displayName)
                .font(.custom("Rajdhani", size: 14))
                .foregroundColor(participant.isAIHost ? .purple : .white)
                .fontWeight(participant.isAIHost ? .bold : .regular)
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
class LiveKitCallService: ObservableObject, @unchecked Sendable, WebSocketDelegate {
    @Published var isConnected = false
    @Published var isMuted = false
    @Published var isAIListening = false  // AI starts disabled by default
    @Published var participants: [MatchParticipant] = []
    @Published var connectionState: String = "Disconnected"
    
    // MARK: - LiveKit Integration
    private var room: Room?
    private var localParticipant: LocalParticipant?
    
    // MARK: - WebSocket Integration for AI Control
    private var webSocketService: WebSocketService?
    private var roomId: String?
    private var livekitName: String?
    private var userId: String?
    
    // Audio session for LiveKit
    private var audioSession: AVAudioSession?
    private var isSimulatingConnection = false
    private(set) var hasConnected = false  // Track if we've successfully connected
    private(set) var isDisconnecting = false  // Prevent multiple disconnects
    
    init() {
        setupAudioSession()
        initializeAIState()  // Ensure AI starts disabled
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
    
    // MARK: - AI Toggle Functionality
    func toggleAI() {
        guard let webSocketService = webSocketService else {
            print("⚠️ [AI] WebSocket service not initialized")
            return
        }
        
        guard webSocketService.isConnected else {
            print("⚠️ [AI] WebSocket not connected, attempting to reconnect...")
            // Try to reconnect if not connected
            if let roomId = roomId, let livekitName = livekitName, let userId = userId {
                // Use Task to handle async call
                Task {
                    await connectToRoomWebSocket(token: AuthService.shared.firebaseToken ?? "")
                }
            }
            return
        }
        
        // Toggle the local state first for immediate UI feedback
        isAIListening.toggle()
        
        // Send toggle message to backend
        let toggleMessage: [String: Any] = [
            "type": "toggle_ai",
            "ai_enabled": isAIListening,
            "user_id": userId ?? "",
            "timestamp": Date().timeIntervalSince1970
        ]
        
        webSocketService.send(toggleMessage)
        print("🎛️ [AI] Sent AI toggle message: \(isAIListening ? "enabled" : "disabled")")
        
        // Show user feedback
        print("🎛️ [AI] AI is now \(isAIListening ? "enabled" : "disabled") - waiting for backend confirmation")
    }
    
    // MARK: - AI Initialization
    func initializeAIState() {
        // Ensure AI starts in disabled state
        isAIListening = false
        print("🎛️ [AI] AI initialized in disabled state")
    }
    
    // MARK: - AI Status Methods
    func getAIStatus() -> Bool {
        return isAIListening
    }
    
    func isWebSocketConnected() -> Bool {
        return webSocketService?.isConnected ?? false
    }
    
    // MARK: - WebSocket Delegate Methods
    func webSocket(_ service: WebSocketService, didReceiveMessage message: [String: Any]) {
        guard let messageType = message["type"] as? String else { return }
        
        switch messageType {
        case "ai_toggle_response":
            if let aiEnabled = message["ai_enabled"] as? Bool {
                Task { @MainActor in
                    self.isAIListening = aiEnabled
                }
                print("✅ [AI] Backend confirmed AI toggle: \(aiEnabled ? "enabled" : "disabled")")
            }
        case "ai_room_state":
            if let aiEnabled = message["ai_enabled"] as? Bool {
                Task { @MainActor in
                    self.isAIListening = aiEnabled
                }
                print("🔄 [AI] Room-wide AI state updated: \(aiEnabled ? "enabled" : "disabled")")
            }
        
        case "room_joined":
            print("✅ [WebSocket] Successfully joined room WebSocket")
            
            // Update AI status based on backend response
            if let aiEnabled = message["ai_enabled"] as? Bool {
                Task { @MainActor in
                    self.isAIListening = aiEnabled
                }
                print("🎛️ [AI] Backend confirmed initial AI state: \(aiEnabled ? "enabled" : "disabled")")
            }
            
        case "error":
            if let errorMessage = message["message"] as? String {
                print("❌ [WebSocket] Error: \(errorMessage)")
            }
            
        default:
            print("📨 [WebSocket] Received message: \(messageType)")
        }
    }
    
    func webSocket(_ service: WebSocketService, didEncounterError error: Error) {
        print("❌ [WebSocket] Error: \(error)")
    }
    
    func webSocketDidConnect(_ service: WebSocketService) {
        print("✅ [WebSocket] Connected to room WebSocket")
    }
    
    nonisolated func webSocketDidDisconnect(_ service: WebSocketService) {
        print("📡 [WebSocket] Disconnected from room WebSocket")
    }
    
    func connect(roomId: String, token: String, participants: [MatchParticipant], livekitName: String, userId: String) async {
        print("🔗 [LiveKit] Connecting to room: \(roomId)")
        
        // Store room information for WebSocket
        self.roomId = roomId
        self.livekitName = livekitName
        self.userId = userId
        
        await MainActor.run {
            // Initialize with the provided participants from match data
            self.participants = participants
            self.connectionState = "Connecting..."
            self.hasConnected = false
            self.isDisconnecting = false
            print("👥 [LiveKit] Initialized with \(participants.count) participants from match data")
        }
        
        // Connect to room WebSocket for AI control
        await connectToRoomWebSocket(token: token)
        
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
    
    private func connectToRoomWebSocket(token: String) async {
        guard let roomId = roomId, let livekitName = livekitName, let userId = userId else {
            print("❌ [WebSocket] Missing room information for WebSocket connection")
            return
        }
        
        // Create WebSocket endpoint with query parameters
        let endpoint = "/api/rooms/ws/\(roomId)?livekit_name=\(livekitName)&user_id=\(userId)"
        
        // Create and configure WebSocket service
        webSocketService = WebSocketService()
        webSocketService?.delegate = self
        
        // Connect to the room WebSocket
        webSocketService?.connect(to: endpoint, with: token)
        
        print("🔌 [WebSocket] Connecting to room WebSocket: \(endpoint)")
        
        // Wait a moment for connection to establish
        try? await Task.sleep(nanoseconds: 1_000_000_000) // 1 second
        
        if let webSocketService = webSocketService, webSocketService.isConnected {
            print("✅ [WebSocket] Successfully connected to room WebSocket")
        } else {
            print("⚠️ [WebSocket] WebSocket connection may not be ready yet")
        }
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
        
        // Disconnect WebSocket for AI control
        webSocketService?.disconnect()
        webSocketService = nil
        
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
    
    // Callback for AI host welcome
    var onAIHostWelcome: ((String) -> Void)?
    
    private func showParticipantLeftNotification(_ displayName: String) {
        onParticipantLeft?(displayName)
    }
    
    private func showAIHostWelcome() {
        onAIHostWelcome?("Vortex has joined as your conversation host!")
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
                // Check if this is an AI host participant
                let isAIHost = participantId.hasPrefix("host_") || cleanParticipantId.hasPrefix("host_")
                
                print("🔍 [PARTICIPANT DEBUG] Processing participant: \(participantId)")
                print("🔍 [PARTICIPANT DEBUG] Clean ID: \(cleanParticipantId)")
                print("🔍 [PARTICIPANT DEBUG] Is AI Host: \(isAIHost)")
                print("🔍 [PARTICIPANT DEBUG] Checking prefixes: host_ -> \(participantId.hasPrefix("host_")), clean host_ -> \(cleanParticipantId.hasPrefix("host_"))")
                
                // Use the clean ID (without "user_" prefix) for consistency with match data
                let displayName: String
                if isAIHost {
                    displayName = "Vortex" // AI host name
                    print("✅ [PARTICIPANT DEBUG] AI HOST DETECTED! Setting displayName to: \(displayName)")
                } else {
                    displayName = "User \(String(cleanParticipantId.prefix(8)))" // Use first 8 chars of clean ID
                    print("👤 [PARTICIPANT DEBUG] Regular user detected: \(displayName)")
                }
                
                let newParticipant = MatchParticipant(
                    userId: cleanParticipantId,
                    displayName: displayName,
                    isCurrentUser: false,
                    isAIHost: isAIHost
                )
                
                print("🎭 [PARTICIPANT DEBUG] Created participant: \(newParticipant)")
                print("🎭 [PARTICIPANT DEBUG] Participant isAIHost flag: \(newParticipant.isAIHost)")
                
                self.participants.append(newParticipant)
                print("➕ [LiveKit] Added new participant to UI: \(newParticipant.displayName) (clean ID: '\(cleanParticipantId)')")
                
                // Show welcome message for AI host
                if newParticipant.isAIHost {
                    self.showAIHostWelcome()
                }
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
                    print("🎭 [DISCONNECT DEBUG] Was AI host: \(removedParticipant!.isAIHost)")
                    break
                }
            }
            
            if let participant = removedParticipant {
                // Show notification that participant left
                self.showParticipantLeftNotification(participant.displayName)
                print("🎭 [DISCONNECT DEBUG] Total participants after removal: \(self.participants.count)")
                print("🎭 [DISCONNECT DEBUG] AI hosts remaining: \(self.participants.filter { $0.isAIHost }.count)")
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
        livekitName: "preview_room",  // Add missing parameter
        userId: "user1",              // Add missing parameter
        participants: [
            MatchParticipant(userId: "user1", displayName: "You", isCurrentUser: true),
            MatchParticipant(userId: "user2", displayName: "Alex", isCurrentUser: false),
            MatchParticipant(userId: "host_vortex", displayName: "Vortex", isCurrentUser: false, isAIHost: true)
        ],
        topics: ["Artificial Intelligence", "Technology"],
        hashtags: ["#AI", "#Tech"]
    )
    HashtagScreen(matchData: mockMatchData)
}
