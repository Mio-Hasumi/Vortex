//
//  UV-TM.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/18/25.
//
import SwiftUI
import Combine
import AVFoundation
import FirebaseAuth

// Data model for live match information
struct LiveMatchData {
    let matchId: String
    let sessionId: String
    let roomId: String
    let livekitToken: String
    let participants: [MatchParticipant]
    let topics: [String]
    let hashtags: [String]
}

struct MatchParticipant {
    let userId: String
    let displayName: String
    let isCurrentUser: Bool
    let isAIHost: Bool
    
    // Convenience initializer for backward compatibility
    init(userId: String, displayName: String, isCurrentUser: Bool, isAIHost: Bool = false) {
        self.userId = userId
        self.displayName = displayName
        self.isCurrentUser = isCurrentUser
        self.isAIHost = isAIHost
    }
}

// Simplified view, keeping only core functionality
struct UserVoiceTopicMatchingView: View {
    let matchResult: MatchResult
    @Environment(\.dismiss) private var dismiss
    
    // AI service, handles all WebSocket and audio logic
    @StateObject private var aiVoiceService = AIVoiceService.shared
    
    // Topic facts service for displaying interesting facts while waiting
    @StateObject private var topicFactsService = TopicFactsService.shared
    
    // Navigation state for when match is found
    @State private var navigateToLiveChat = false
    @State private var matchData: LiveMatchData?
    @State private var showPreparingRoom = false
    @State private var preparingMessage = "Preparing room..."

    var body: some View {
        ZStack {
            // Background
            Color.black.ignoresSafeArea()

            // Top UI elements
            VStack {
                // Back button
                HStack {
                    Button(action: {
                        print("🚪 [EXIT] User tapped exit button - returning to home")
                        // Clean up AI voice service before dismissing
                        aiVoiceService.cleanup()
                        // CRITICAL FIX: Reset navigation state to prevent self-matching
                        VoiceMatchingService.shared.resetNavigation()
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
                
                // AI text response display area OR preparing room message
                ScrollView {
                    if showPreparingRoom {
                        VStack(spacing: 16) {
                            // Preparing room UI
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(1.5)
                            
                            Text(preparingMessage)
                                .font(.custom("Rajdhani", size: 28))
                                .foregroundColor(.white)
                                .multilineTextAlignment(.center)
                            
                            Text("Setting up AI host...")
                                .font(.custom("Rajdhani", size: 18))
                                .foregroundColor(.white.opacity(0.7))
                                .multilineTextAlignment(.center)
                        }
                        .padding()
                    } else {
                        VStack(spacing: 20) {
                            // AI response
                            Text(aiVoiceService.currentResponse)
                                .font(.custom("Rajdhani", size: 28))
                                .foregroundColor(.white)
                                .multilineTextAlignment(.center)
                            
                            // Topic facts display
                            if !topicFactsService.currentFact.isEmpty {
                                VStack(spacing: 8) {
                                    if topicFactsService.isGeneratingFact {
                                        ProgressView()
                                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                            .scaleEffect(0.8)
                                    }
                                    
                                    Text(topicFactsService.currentFact)
                                        .font(.custom("Rajdhani", size: 18))
                                        .foregroundColor(.white.opacity(0.8))
                                        .multilineTextAlignment(.center)
                                        .transition(.opacity.combined(with: .scale))
                                        .animation(.easeInOut(duration: 0.5), value: topicFactsService.currentFact)
                                }
                                .padding(.horizontal, 20)
                            }
                        }
                        .padding()
                    }
                }
                
                Spacer()
            }
            
            // Bottom microphone button
            VStack {
                Spacer()
                // Add subtle searching indicator if still waiting for match
                if !navigateToLiveChat, let firstTopic = matchResult.topics.first {
                    HStack(spacing: 8) {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            .scaleEffect(0.8)
                        
                        Text("Searching for someone to talk about #\(firstTopic) with you...")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundColor(Color.white.opacity(0.7))
                    }
                    .padding(.bottom, 8)
                    .transition(.opacity)
                }
                Button(action: {
                    // Toggle mute state
                    aiVoiceService.toggleMute()
                }) {
                    Image(systemName: aiVoiceService.isMuted ? "mic.slash.fill" : (aiVoiceService.isAISpeaking ? "speaker.wave.2.fill" : "mic.fill"))
                        .font(.system(size: 40))
                        .foregroundColor(aiVoiceService.isMuted ? .red : (aiVoiceService.isAISpeaking ? .blue : .white))
                        .padding(20)
                        .background(Circle().fill(Color.white.opacity(0.2)))
                }
                
                Text(aiVoiceService.isMuted ? "Muted" : (aiVoiceService.isAISpeaking ? "Vortex Speaking..." : "Listening..."))
                    .foregroundColor(.white)
                    .padding(.bottom, 30)
            }
        }
        .onAppear {
            // Initialize AI conversation when view appears
            Task {
                await aiVoiceService.initializeAIConversation(with: matchResult)
            }
            
            // Start topic facts service with the first topic
            if let firstTopic = matchResult.topics.first {
                topicFactsService.startFactsForTopic(firstTopic)
            }
        }
        .onDisappear {
            // Stop topic facts service
            topicFactsService.stopFacts()
            
            // Only cleanup if we're not navigating to a successful match
            print("🚪 [EXIT] View disappearing - checking if we should cleanup")
            
            if navigateToLiveChat && matchData != nil {
                print("✅ [EXIT] Navigating to live chat - preserving AI service indefinitely")
                // Don't cleanup the AI service when navigating to a successful match
                // Let the chat room handle cleanup when the user actually leaves the chat
                print("🔒 [EXIT] AI service will persist until chat room is manually exited")
            } else {
                print("🧹 [EXIT] No active navigation - cleaning up AI voice service")
                aiVoiceService.cleanup()
            }
            
            // CRITICAL FIX: Only reset navigation state if we're not navigating to a successful match
            if !navigateToLiveChat || matchData == nil {
                print("🔄 [EXIT] Resetting navigation state")
                VoiceMatchingService.shared.resetNavigation()
            } else {
                print("🔒 [EXIT] Preserving navigation state during successful match navigation")
            }
        }
        .navigationBarHidden(true)
        // Navigation to live chat when match is found
        .background(
            NavigationLink(
                destination: Group {
                    if let data = matchData {
                        HashtagScreen(matchData: data)
                            .onAppear {
                                print("🚀 [NAVIGATION] HashtagScreen appeared")
                                print("   🆔 Match ID: \(data.matchId)")
                                print("   🏠 Room ID: \(data.roomId)")
                                print("   👥 Participants: \(data.participants.count)")
                            }
                    } else {
                        EmptyView()
                    }
                },
                isActive: $navigateToLiveChat
            ) {
                EmptyView()
            }
            .hidden()
        )
        // Listen for match found events
        .onReceive(aiVoiceService.$matchFound) { matchData in
            if let matchData = matchData {
                print("🎯 [NAVIGATION] Match found - entering room preparation phase!")
                
                // Stop AI conversation and show preparing state
                Task {
                    await aiVoiceService.stopAIConversation()
                    await MainActor.run {
                        self.matchData = matchData
                        self.showPreparingRoom = true
                        self.preparingMessage = "Match found! Preparing your room..."
                        print("🏗️ [NAVIGATION] Showing room preparation UI")
                    }
                    
                    // Wait for agent to be ready before navigation
                    await waitForAgentReadyAndNavigate(matchData: matchData)
                }
            }
        }
    }
    
    // MARK: - Agent Readiness Check
    
    private func waitForAgentReadyAndNavigate(matchData: LiveMatchData) async {
        print("🤖 [AGENT_CHECK] Starting agent readiness check for room: \(matchData.roomId)")
        
        // Update UI to show agent setup status
        await MainActor.run {
            preparingMessage = "Setting up AI host..."
        }
        
        // Check agent readiness with timeout
        let maxAttempts = 15  // 15 seconds timeout
        var agentReady = false
        
        for attempt in 1...maxAttempts {
            print("🔍 [AGENT_CHECK] Attempt \(attempt)/\(maxAttempts): Checking if agent is ready...")
            
            // Update UI with progress
            await MainActor.run {
                preparingMessage = "Setting up AI host... (\(attempt)/\(maxAttempts))"
            }
            
            // Check if agent is ready via API
            agentReady = await checkAgentStatus(roomId: matchData.roomId)
            
            if agentReady {
                print("✅ [AGENT_CHECK] Agent confirmed ready! Proceeding to navigation...")
                break
            }
            
            // Wait 1 second before next check
            try? await Task.sleep(nanoseconds: 1_000_000_000)
        }
        
        // Navigate to chat regardless of agent status (with timeout fallback)
        await MainActor.run {
            if agentReady {
                preparingMessage = "AI host ready! Joining room..."
                print("🎉 [AGENT_CHECK] Agent ready - navigating to chat!")
            } else {
                preparingMessage = "Joining room... (AI host may join shortly)"
                print("⚠️ [AGENT_CHECK] Agent readiness timeout - proceeding anyway")
            }
            
            // Short delay for UI feedback, then navigate
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                self.showPreparingRoom = false
                self.navigateToLiveChat = true
                print("🚀 [NAVIGATION] Navigating to chat room!")
            }
        }
    }
    
    private func checkAgentStatus(roomId: String) async -> Bool {
        do {
            // Call backend API to check if agent is ready using the proper path format
            let endpoint = "/api/agents/status/\(roomId)"
            let response: AgentStatusResponse = try await APIService.shared.request(
                endpoint: endpoint,
                method: "GET"
            )
            
            // Backend returns is_active (bool), need to check that field instead
            let isReady = response.is_active
            print("🔍 [AGENT_CHECK] Agent active: \(response.is_active), ready: \(isReady)")
            
            return isReady
        } catch {
            print("❌ [AGENT_CHECK] Error checking agent status: \(error)")
            return false  // Assume not ready on error
        }
    }
}

// MARK: - AI Voice Service - GPT-4o Realtime WebSocket
class AIVoiceService: NSObject, ObservableObject, WebSocketDelegate, AVAudioPlayerDelegate {
    static let shared = AIVoiceService()
    @Published var isConnected = false
    @Published var isListening = false
    @Published var isMuted = false
    @Published var currentResponse = ""
    @Published var isAISpeaking = false
    @Published var matchFound: LiveMatchData? {
        didSet {
            if let matchData = matchFound {
                print("🎯 [AIVoice] matchFound SET with Match ID: \(matchData.matchId)")
                // Store a backup copy to prevent accidental resets
                lastMatchData = matchData
                hasActiveMatch = true
            } else {
                print("⚠️ [AIVoice] matchFound set to NIL")
                // REMOVED RESTORE LOGIC - this was causing infinite recursion issues
                // if hasActiveMatch && lastMatchData != nil {
                //     print("🔄 [AIVoice] Restoring matchFound from backup...")
                //     matchFound = lastMatchData
                // }
            }
        }
    }
    
    // Backup storage for match data
    var lastMatchData: LiveMatchData?  // Made public for debugging
    var hasActiveMatch: Bool = false   // Made public for debugging
    
    // Audio crossfading to prevent clicking between PCM chunks
    private var lastTail: [Int16] = []
    
    private var matchContext: MatchResult?
    private var conversationContext: String = ""
    private var webSocketService: WebSocketService?
    private var matchingWebSocketService: WebSocketService?  // NEW: Separate WebSocket for matching notifications
    private var authToken: String?
    private var isAuthenticated = false
    private var sessionStarted = false
    private var greetingSent = false  // NEW: Track if greeting has been sent
    private var isInitializing = false  // NEW: Prevent multiple simultaneous initializations
    private var conversationActive = false  // NEW: Track if conversation is currently active
    private var lastSessionId: String?  // NEW: Track session continuity
    
    // Audio related
    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private var isRecording = false
    private var audioStartTime: Date?
    private var audioChunkIndex: Int = 0
    
    // 🔧 Fixed unified audio playback system
    private var audioPlaybackQueue = DispatchQueue(label: "audio.playback", qos: .userInitiated)
    private var currentAudioPlayer: AVAudioPlayer?
    private var audioQueue: [Data] = [] // Audio data waiting to be played
    private var audioAccumulator = Data() // Accumulate all audio chunks for a single complete response
    private var isPlayingAudio = false
    
    private override init() {
        // Get authentication token
        authToken = AuthService.shared.firebaseToken
        super.init()
        setupAudioSession()
        setupAudioEngine()
        
        // Listen for cleanup notifications from chat room
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleDelayedCleanup),
            name: NSNotification.Name("CleanupAIServices"),
            object: nil
        )
        
        // Listen for audio session interruptions
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleAudioSessionInterruption),
            name: AVAudioSession.interruptionNotification,
            object: nil
        )
        
        // Listen for audio session route changes
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleAudioSessionRouteChange),
            name: AVAudioSession.routeChangeNotification,
            object: nil
        )
    }
    
    @objc private func handleDelayedCleanup() {
        print("🧹 [AIVoice] Received delayed cleanup notification from chat room")
        // Only cleanup if we're not currently in an active match
        if matchFound == nil && !hasActiveMatch {
            print("🧹 [AIVoice] No active match - proceeding with cleanup")
            cleanup()
        } else {
            print("⚠️ [AIVoice] Active match detected - skipping cleanup")
        }
    }
    
    @objc private func handleAudioSessionInterruption(_ notification: Notification) {
        guard let userInfo = notification.userInfo,
              let typeValue = userInfo[AVAudioSessionInterruptionTypeKey] as? UInt,
              let type = AVAudioSession.InterruptionType(rawValue: typeValue) else {
            return
        }
        
        print("🔄 [AIVoice] Audio session interruption: \(type)")
        
        switch type {
        case .began:
            // Interruption began - stop audio
            stopAudioEngine()
        case .ended:
            // Interruption ended - restart audio if needed
            if sessionStarted && !isMuted && !isAISpeaking {
                handleAudioSessionChange()
            }
        @unknown default:
            break
        }
    }
    
    @objc private func handleAudioSessionRouteChange(_ notification: Notification) {
        guard let userInfo = notification.userInfo,
              let reasonValue = userInfo[AVAudioSessionRouteChangeReasonKey] as? UInt,
              let reason = AVAudioSession.RouteChangeReason(rawValue: reasonValue) else {
            return
        }
        
        print("🔄 [AIVoice] Audio route change: \(reason)")
        
        // Handle route changes that might affect our audio setup
        switch reason {
        case .newDeviceAvailable, .oldDeviceUnavailable, .categoryChange:
            if sessionStarted {
                handleAudioSessionChange()
            }
        default:
            break
        }
    }
    
    private func setupAudioSession() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            
            // Check if audio session is already active and configured for calls
            if audioSession.category == .playAndRecord && audioSession.mode == .voiceChat {
                print("✅ [AIVoice] Audio session already configured for voice chat")
                return
            }
            
            // Configure for voice chat with more flexible options
            try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
            
            // Try to set 24kHz, but fall back to system default if it fails
            do {
                try audioSession.setPreferredSampleRate(24000)
                print("✅ [AIVoice] Set preferred sample rate to 24kHz")
            } catch {
                print("⚠️ [AIVoice] Could not set 24kHz sample rate, using system default")
            }
            
            // Set buffer duration with fallback
            do {
                try audioSession.setPreferredIOBufferDuration(512.0 / 24000.0)
                print("✅ [AIVoice] Set preferred IO buffer duration")
            } catch {
                print("⚠️ [AIVoice] Could not set preferred buffer duration, using system default")
            }
            
            try audioSession.setActive(true)
            
            let frames = Int(audioSession.ioBufferDuration * audioSession.sampleRate)
            print("🔥 [AIVoice] IO block = \(frames) frames @ \(audioSession.sampleRate) Hz")
            print("✅ [AIVoice] Audio session configured successfully")
        } catch {
            print("❌ [AIVoice] Audio session setup failed: \(error)")
        }
    }
    
    private func setupAudioEngine() {
        audioEngine = AVAudioEngine()
        inputNode = audioEngine?.inputNode
        
        guard let audioEngine = audioEngine,
              let inputNode = inputNode else {
            print("❌ [AIVoice] Failed to setup audio engine")
            return
        }
        
        // Use hardware's actual input format
        let inputFormat = inputNode.inputFormat(forBus: 0)
        print("🎙️ [AIVoice] Hardware input format: \(inputFormat)")
        
        // Check if input format has valid properties
        guard inputFormat.sampleRate > 0 && inputFormat.channelCount > 0 else {
            print("❌ [AIVoice] Invalid input format properties: sampleRate=\(inputFormat.sampleRate), channels=\(inputFormat.channelCount)")
            return
        }
        
        // Create target format with fallback options
        var targetFormat: AVAudioFormat?
        
        // Try 24kHz first (OpenAI preferred)
        targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, 
                                   sampleRate: 24000, 
                                   channels: 1, 
                                   interleaved: false)
        
        // If 24kHz fails, try 16kHz (common fallback)
        if targetFormat == nil {
            print("⚠️ [AIVoice] 24kHz format failed, trying 16kHz")
            targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, 
                                       sampleRate: 16000, 
                                       channels: 1, 
                                       interleaved: false)
        }
        
        // If that fails, try 44.1kHz (system default)
        if targetFormat == nil {
            print("⚠️ [AIVoice] 16kHz format failed, trying 44.1kHz")
            targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, 
                                       sampleRate: 44100, 
                                       channels: 1, 
                                       interleaved: false)
        }
        
        // If all fail, use input format as-is
        if targetFormat == nil {
            print("⚠️ [AIVoice] All target formats failed, using input format as-is")
            targetFormat = inputFormat
        }
        
        guard let finalTargetFormat = targetFormat else {
            print("❌ [AIVoice] Failed to create any valid target audio format")
            return
        }
        
        print("🎵 [AIVoice] Using target format: \(finalTargetFormat)")
        
        // Install tap using hardware's native format with validation
        do {
            inputNode.installTap(onBus: 0, bufferSize: 0, format: inputFormat) { [weak self] buffer, time in
                self?.processAudioBuffer(buffer, originalFormat: inputFormat, targetFormat: finalTargetFormat)
            }
            print("✅ [AIVoice] Audio engine configured for streaming")
        } catch {
            print("❌ [AIVoice] Failed to install audio tap: \(error)")
        }
    }
    
    func initializeAIConversation(with matchResult: MatchResult) async {
        // Prevent multiple simultaneous initializations
        guard !isInitializing && !sessionStarted else {
            print("⚠️ [AIVoice] Initialization already in progress or session active, skipping...")
            return
        }
        
        isInitializing = true
        print("🤖 [AIVoice] Initializing AI conversation for session: \(generateSessionId())")
        
        self.matchContext = matchResult
        
        conversationContext = """
You are Vortex, a friendly AI conversation companion in a voice chat app. The user is interested in discussing: \(matchResult.topics.joined(separator: ", "))

Their original message was: "\(matchResult.transcription)"

Guidelines:
- Greet naturally with "Hi! I'm Vortex, nice to meet you! Tell me more about \(matchResult.topics.first ?? "your interests")"
- You're a conversation partner who enjoys these topics
- Keep responses brief and engaging (1-2 sentences max)
- Ask thoughtful follow-up questions
- Use natural spoken language (this is voice chat)
- Focus on the topics, avoid meta-discussion about matching
- Be genuine and curious about their interests

Start the conversation now with your greeting and a question about their interests.
"""
        
        print("🧠 [AIVoice] AI conversation context set for topics: \(matchResult.topics)")
        
        do {
            // Connect to WebSocket
            await connectToRealtimeAPI()
            
            print("✅ [AIVoice] AI conversation initialized")
        } catch {
            print("❌ [AIVoice] Failed to initialize AI conversation: \(error)")
        }
        
        isInitializing = false
    }
    
    private func connectToRealtimeAPI() async {
        guard let token = authToken else {
            print("❌ [AIVoice] No auth token available")
            return
        }
        
        print("🔌 [AIVoice] Connecting to both AI Audio Stream and Matching WebSockets...")
        print("🔍 [MATCHING] Starting WebSocket connection setup for matching notifications")
        
        await MainActor.run {
            // Create AI audio stream WebSocket service
            webSocketService = WebSocketService()
            webSocketService?.delegate = self
            
            // Create matching notification WebSocket service
            matchingWebSocketService = MatchingWebSocketService()
            matchingWebSocketService?.delegate = self
            
            // Connect to audio stream endpoint
            webSocketService?.connect(to: APIConfig.WebSocket.aiAudioStream, with: token)
            print("🎵 [AI_AUDIO] Connecting to AI audio stream WebSocket")
            
            // Connect to matching notification endpoint (requires user ID)
            // DEBUG: Check all possible sources for user ID
            let authServiceUserId = AuthService.shared.userId
            let firebaseUserId = Auth.auth().currentUser?.uid
            
            print("🔍 [MATCHING DEBUG] AuthService.shared.userId: \(authServiceUserId ?? "nil")")
            print("🔍 [MATCHING DEBUG] Auth.auth().currentUser?.uid: \(firebaseUserId ?? "nil")")
            print("🔍 [MATCHING DEBUG] AuthService.shared.isAuthenticated: \(AuthService.shared.isAuthenticated)")
            
            // Try to get user ID from multiple sources
            let userId = authServiceUserId ?? firebaseUserId
            
            if let userId = userId {
                let matchingEndpoint = "\(APIConfig.WebSocket.matching)?user_id=\(userId)"
                matchingWebSocketService?.connect(to: matchingEndpoint, with: token)
                print("🎯 [MATCHING] ✅ Connecting to matching WebSocket with user ID: \(userId)")
                print("🎯 [MATCHING] ✅ Full endpoint: \(matchingEndpoint)")
            } else {
                print("❌ [MATCHING] CRITICAL ERROR: No user ID available from any source!")
                print("❌ [MATCHING] AuthService userId: \(authServiceUserId ?? "nil")")
                print("❌ [MATCHING] Firebase userId: \(firebaseUserId ?? "nil")")
                print("❌ [MATCHING] Cannot connect to matching WebSocket without user_id!")
            }
        }
    }
    
    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer, originalFormat: AVAudioFormat, targetFormat: AVAudioFormat) {
        // Don't process audio if:
        // 1. Session not started
        // 2. User manually muted
        // 3. Not recording
        // 4. AI is currently speaking (auto-mute during AI speech)
        guard sessionStarted && !isMuted && isRecording && !isAISpeaking else { 
            return 
        }
        
        // Use actual frame count from buffer, not hardcoded values
        let actualFrameCount = buffer.frameLength
        guard actualFrameCount > 0 else {
            return // Skip empty buffers
        }
        
        // Create audio converter
        guard let converter = AVAudioConverter(from: originalFormat, to: targetFormat) else {
            print("❌ [AIVoice] Failed to create audio converter")
            return
        }
        
        // Create output buffer with proper capacity calculation
        let outputFrameCapacity = AVAudioFrameCount(Double(actualFrameCount) * targetFormat.sampleRate / originalFormat.sampleRate)
        guard let outputBuffer = AVAudioPCMBuffer(pcmFormat: targetFormat, frameCapacity: outputFrameCapacity) else {
            print("❌ [AIVoice] Failed to create output buffer")
            return
        }
        
        // Perform format conversion
        var error: NSError?
        _ = converter.convert(to: outputBuffer, error: &error) { _, outStatus in
            outStatus.pointee = .haveData
            return buffer
        }
        
        if let error = error {
            print("❌ [AIVoice] Audio conversion failed: \(error)")
            return
        }
        
        // Convert to Data
        guard let audioData = outputBuffer.toData() else {
            print("❌ [AIVoice] Failed to convert converted buffer to data")
            return
        }
        
        // Encode to base64 and send
        let base64Audio = audioData.base64EncodedString()
        
        let audioMessage: [String: Any] = [
            "type": "audio_chunk",
            "audio_data": base64Audio,
            "language": "en-US",
            "timestamp": Date().timeIntervalSince1970
        ]
        
        audioChunkIndex += 1
        webSocketService?.send(audioMessage)
        // print("📤 [AIVoice] Sent audio chunk #\(audioChunkIndex): \(audioData.count) bytes") // COMMENTED OUT - too verbose
    }
    
    private func sendStartSession() {
        let startSessionMessage: [String: Any] = [
            "type": "start_session",
            "user_context": [
                "topics": matchContext?.topics ?? [],
                "hashtags": matchContext?.hashtags ?? [],
                "transcription": matchContext?.transcription ?? "",
                "conversation_context": conversationContext
            ],
            "output_audio_format": [
                "type": "pcm16"
            ],
            "timestamp": Date().timeIntervalSince1970
        ]
        
        webSocketService?.send(startSessionMessage)
        print("📤 [AIVoice] Sent start session with topic context and PCM16 audio format")
    }
    
    func startListening() async {
        guard sessionStarted && !isMuted && !isAISpeaking else {
            print("⚠️ [AIVoice] Cannot start listening - session not started, muted, or AI is speaking")
            return
        }
        
        print("🎤 [AIVoice] Starting voice listening")
        
        await MainActor.run {
            isListening = true
        }
        
        startAudioEngine()
    }
    
    func toggleMute() {
        isMuted.toggle()
        print("🔇 [AIVoice] Audio input \(isMuted ? "muted" : "unmuted")")
        
        if isMuted {
            stopAudioEngine()
        } else if sessionStarted && !isAISpeaking {
            // Only restart audio if AI is not currently speaking
            startAudioEngine()
        }
    }
    

    
    private func startAudioEngine() {
        guard !isMuted && !isAISpeaking, let audioEngine = audioEngine else { 
            return 
        }
        
        do {
            if !audioEngine.isRunning {
                print("🎵 [AIVoice] Starting audio engine...")
                audioEngine.prepare()
                try audioEngine.start()
                isRecording = true
                print("🎙️ [AIVoice] ✅ Audio engine started - isRecording: \(isRecording)")
            }
        } catch {
            print("❌ [AIVoice] Failed to start audio engine: \(error)")
        }
    }
    
    private func stopAudioEngine() {
        guard let audioEngine = audioEngine else { return }
        
        if audioEngine.isRunning {
            audioEngine.stop()
            isRecording = false
            audioChunkIndex = 0
            
            Task { @MainActor in
                isListening = false
            }
            
            print("⏹️ [AIVoice] Audio engine stopped")
        }
    }
    
    // 🛑 Stop AI conversation method
    func stopAIConversation() async {
        print("🛑 [AIVoice] Stopping AI conversation...")
        
        await MainActor.run {
            // Stop all audio activities
            isListening = false
            isAISpeaking = false
            currentResponse = ""
        }
        
        // Stop audio engine
        stopAudioEngine()
        
        // Stop all audio playback
        stopAllAudio()
        
        // Disconnect AI Audio WebSocket (keep Matching WebSocket connection)
        webSocketService?.disconnect()
        webSocketService = nil
        
        // Reset authentication state
        isAuthenticated = false
        sessionStarted = false
        greetingSent = false
        isInitializing = false
        
        print("✅ [AIVoice] AI conversation stopped and cleaned up")
    }
    
    // Method to clear match data
    func clearMatchData() {
        print("🧹 [AIVoice] Clearing match data...")
        hasActiveMatch = false
        lastMatchData = nil
        matchFound = nil
        print("✅ [AIVoice] Match data cleared")
    }
    
    deinit {
        print("🧹 [AIVoice] AIVoiceService deallocating - cleaning up resources")
        
        // Synchronous cleanup to prevent crashes - NO ASYNC CALLS in deinit
        cleanupSynchronously()
    }
    
    // Synchronous cleanup method for deinit
    private func cleanupSynchronously() {
        print("🧹 [AIVoice] Starting synchronous cleanup")
        
        // Remove all notification observers
        NotificationCenter.default.removeObserver(self, name: NSNotification.Name("CleanupAIServices"), object: nil)
        NotificationCenter.default.removeObserver(self, name: AVAudioSession.interruptionNotification, object: nil)
        NotificationCenter.default.removeObserver(self, name: AVAudioSession.routeChangeNotification, object: nil)
        
        // Stop audio engine immediately
        if let audioEngine = audioEngine, audioEngine.isRunning {
            audioEngine.stop()
            inputNode?.removeTap(onBus: 0)
        }
        audioEngine = nil
        inputNode = nil
        isRecording = false
        
        // Stop audio playback immediately (final cleanup - use stop, not pause)
        currentAudioPlayer?.stop()
        currentAudioPlayer = nil
        audioQueue.removeAll()
        audioAccumulator = Data()
        lastTail.removeAll()
        isPlayingAudio = false
        
        // Disconnect AI Audio WebSocket but preserve Matching WebSocket if we have an active match
        webSocketService?.disconnect()
        webSocketService = nil
        
        // Only disconnect matching WebSocket if we don't have an active match
        if !hasActiveMatch && matchFound == nil {
            print("🔌 [AIVoice] No active match - disconnecting matching WebSocket")
            matchingWebSocketService?.disconnect()
            matchingWebSocketService = nil
        } else {
            print("🔒 [AIVoice] Active match detected - preserving matching WebSocket connection")
        }
        
        // Reset all state (don't use @Published properties in deinit)
        isConnected = false
        isListening = false
        isMuted = false
        isAISpeaking = false
        currentResponse = ""
        isAuthenticated = false
        sessionStarted = false
        greetingSent = false
        isInitializing = false
        conversationActive = false
        
        // Clear match data
        hasActiveMatch = false
        lastMatchData = nil
        matchFound = nil
        
        print("✅ [AIVoice] Synchronous cleanup completed")
    }
    
    // Public cleanup method for view dismissal
    func cleanup() {
        cleanupSynchronously()
    }
    
    // Method to handle audio session changes (e.g., when entering a call)
    func handleAudioSessionChange() {
        print("🔄 [AIVoice] Handling audio session change")
        
        // Stop current audio engine
        stopAudioEngine()
        
        // Re-setup audio session and engine
        setupAudioSession()
        setupAudioEngine()
        
        print("✅ [AIVoice] Audio session change handled")
    }
    
    // Reset method for singleton - reinitialize state
    func reset() {
        print("🔄 [AIVoice] Resetting shared AI service instance")
        cleanup()
        
        // Reinitialize key components
        setupAudioSession()
        setupAudioEngine()
        
        // Reset all published properties
        DispatchQueue.main.async {
            self.isConnected = false
            self.isListening = false
            self.isMuted = false
            self.currentResponse = ""
            self.isAISpeaking = false
            self.matchFound = nil
        }
    }
    
    // MARK: - 🔧 Fixed unified audio playback system
    
    private func fadeAndStop(_ player: AVAudioPlayer?, duration: TimeInterval = 0.05) {
        guard let player = player else { return }
        player.setVolume(0, fadeDuration: duration)
        DispatchQueue.main.asyncAfter(deadline: .now() + duration) {
            player.pause()  // Use pause instead of stop to keep audio pipeline alive
        }
    }
    
    private func stopAllAudio() {
        audioPlaybackQueue.async {
            // Stop current playback with fade out (using pause to keep pipeline alive)
            self.fadeAndStop(self.currentAudioPlayer)
            // Don't set currentAudioPlayer = nil to keep reference alive
            
            // Clear queue
            self.audioQueue.removeAll()
            self.audioAccumulator = Data()
            
            DispatchQueue.main.async {
                self.isAISpeaking = false
            }
            
            self.isPlayingAudio = false
            print("🔇 [AIVoice] All audio playback stopped and cleared (pipeline kept alive)")
        }
    }
    
    private func addPCMChunk(_ base64AudioData: String) {
        guard var chunk = Data(base64Encoded: base64AudioData) else {
            print("❌ [AIVoice] Failed to decode PCM chunk")
            return
        }
        
        // Safety: trim to even number of bytes (Int16 requires pairs)
        if chunk.count & 1 == 1 { 
            chunk.removeLast() 
        }
        
        audioPlaybackQueue.async {
            // Decode to Int16 for crossfading
            chunk.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
                let ptr = raw.bindMemory(to: Int16.self)
                var samples = Array(ptr)
                
                // CROSSFADE with adaptive length and Hann window to prevent clicking
                let maxFade = 180  // 7.5ms @ 24kHz   
                let fade = min(maxFade, min(self.lastTail.count, samples.count / 2))
                if fade > 0 {
                    for i in 0..<fade {
                        // Hann window for smoother crossfade
                        let progress = Double(i) / Double(fade)
                        let hannWeight = 0.5 - 0.5 * cos(progress * Double.pi)
                        
                        let tailSample = Float(self.lastTail[self.lastTail.count - fade + i])
                        let currentSample = Float(samples[i])
                        
                        let crossfaded = (1.0 - Float(hannWeight)) * tailSample + Float(hannWeight) * currentSample
                        samples[i] = Int16(crossfaded)
                    }
                }
                
                // Store new tail for next crossfade (adaptive size)
                self.lastTail = Array(samples.suffix(min(maxFade, samples.count)))
                
                // Convert back to bytes and append
                samples.withUnsafeBytes { buf in
                    self.audioAccumulator.append(buf.bindMemory(to: UInt8.self))
                }
            }
            // print("🎵 [AIVoice] PCM chunk crossfaded: +\(chunk.count) bytes, total: \(self.audioAccumulator.count) bytes")  // COMMENTED OUT - too verbose
        }
    }
    
    private func finalizeAndPlayAudio() {
        audioPlaybackQueue.async {
            self.finalizeAndPlayAudioOnQueue()
        }
    }
    
    private func finalizeAndPlayAudioOnQueue() {
        guard !self.audioAccumulator.isEmpty else {
            print("🔇 [AIVoice] No accumulated PCM data to play")
            return
        }
        
        // print("🔊 [AIVoice] Finalizing and playing complete audio response: \(self.audioAccumulator.count) bytes PCM16")  // COMMENTED OUT - too verbose
        
        // Apply attack ramp to first ~10ms to prevent sentence-start clicking
        var pcmDataWithRamp = self.audioAccumulator
        self.applyAttackRamp(to: &pcmDataWithRamp)
        
        // Convert accumulated PCM16 data to WAV format for playback
        let wavData = self.convertPCM16ToWAV(pcmDataWithRamp)
        
        // Add to playback queue
        self.audioQueue.append(wavData)
        
        // Clear accumulator and crossfade tail for next response
        self.audioAccumulator.removeAll(keepingCapacity: true)
        self.lastTail.removeAll(keepingCapacity: true)
        
        // Start playback queue (if not currently playing)
        if !self.isPlayingAudio {
            self.playNextAudioInQueue()
        }
    }
    
    private func playNextAudioInQueue() {
        audioPlaybackQueue.async {
            guard !self.isPlayingAudio, !self.audioQueue.isEmpty else {
                return
            }
            
            let audioData = self.audioQueue.removeFirst()
            self.isPlayingAudio = true
            
            DispatchQueue.main.async {
                self.isAISpeaking = true
            }
            
            do {
                // Stop previous player with fade out
                self.fadeAndStop(self.currentAudioPlayer)
                
                // Wait for fade out to complete before starting new audio
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.06) { // Wait 60ms (fade duration + buffer)
                    do {
                        // Create new player
                        self.currentAudioPlayer = try AVAudioPlayer(data: audioData)
                        self.currentAudioPlayer?.delegate = self
                        self.currentAudioPlayer?.prepareToPlay()
                        
                        // Start with very small volume to keep pipeline alive, then fade in
                        self.currentAudioPlayer?.volume = 0.0001  // Keep pipeline alive
                        let success = self.currentAudioPlayer?.play() ?? false
                        self.currentAudioPlayer?.setVolume(1.0, fadeDuration: 0.05)  // ~50ms fade in
                        
                        print("🔊 [AIVoice] \(success ? "✅ Started" : "❌ Failed to start") playing audio: \(audioData.count) bytes")
                        
                        if !success {
                            self.audioPlaybackFinished()
                        }
                    } catch {
                        print("❌ [AIVoice] Failed to create delayed audio player: \(error)")
                        self.audioPlaybackFinished()
                    }
                }
                
            } catch {
                print("❌ [AIVoice] Failed to create audio player: \(error)")
                self.audioPlaybackFinished()
            }
        }
    }
    
    private func audioPlaybackFinished() {
        audioPlaybackQueue.async {
            self.isPlayingAudio = false
            
            DispatchQueue.main.async {
                if self.audioQueue.isEmpty {
                    self.isAISpeaking = false
                    // Restart audio recording when AI finishes speaking
                    if self.sessionStarted && !self.isMuted {
                        self.startAudioEngine()
                    }
                }
            }
            
            // Continue playing the next audio in the queue
            if !self.audioQueue.isEmpty {
                self.playNextAudioInQueue()
            }
            
            // print("🔊 [AIVoice] Audio playback finished, queue remaining: \(self.audioQueue.count)")  // COMMENTED OUT - too verbose
        }
    }
    
    private func applyAttackRamp(to data: inout Data, samples: Int = 180 /* 7.5ms @24kHz */) {
        data.withUnsafeMutableBytes { (raw: UnsafeMutableRawBufferPointer) in
            let ptr = raw.bindMemory(to: Int16.self)
            let count = min(samples, ptr.count)
            for i in 0..<count {
                let progress = Float(i) / Float(count)
                // Hann window for smooth attack ramp
                let hannWeight = 0.5 - 0.5 * cosf(Float.pi * progress)
                ptr[i] = Int16(Float(ptr[i]) * hannWeight)
            }
        }
    }
    
    private func convertPCM16ToWAV(_ pcmData: Data) -> Data {
        // WAV file header information (24kHz, 16-bit, mono)
        let sampleRate: UInt32 = 24000
        let channels: UInt16 = 1
        let bitsPerSample: UInt16 = 16
        let byteRate = sampleRate * UInt32(channels) * UInt32(bitsPerSample) / 8
        let blockAlign = channels * bitsPerSample / 8
        let dataSize = UInt32(pcmData.count)
        let fileSize = 36 + dataSize
        
        var wavData = Data()
        
        // RIFF header
        wavData.append("RIFF".data(using: .ascii)!)
        wavData.append(withUnsafeBytes(of: fileSize.littleEndian) { Data($0) })
        wavData.append("WAVE".data(using: .ascii)!)
        
        // fmt block
        wavData.append("fmt ".data(using: .ascii)!)
        wavData.append(withUnsafeBytes(of: UInt32(16).littleEndian) { Data($0) }) // fmt block size
        wavData.append(withUnsafeBytes(of: UInt16(1).littleEndian) { Data($0) })  // PCM format
        wavData.append(withUnsafeBytes(of: channels.littleEndian) { Data($0) })
        wavData.append(withUnsafeBytes(of: sampleRate.littleEndian) { Data($0) })
        wavData.append(withUnsafeBytes(of: byteRate.littleEndian) { Data($0) })
        wavData.append(withUnsafeBytes(of: blockAlign.littleEndian) { Data($0) })
        wavData.append(withUnsafeBytes(of: bitsPerSample.littleEndian) { Data($0) })
        
        // data block
        wavData.append("data".data(using: .ascii)!)
        wavData.append(withUnsafeBytes(of: dataSize.littleEndian) { Data($0) })
        wavData.append(pcmData)
        
        return wavData
    }

    
    // MARK: - Helper methods
    
    private func generateSessionId() -> String {
        return "ai_waiting_\(UUID().uuidString)_\(Date().timeIntervalSince1970)"
    }
    
    private func handleMatchFound(_ message: [String: Any]) {
        print("🚀 [MATCHING] Match found - processing for immediate navigation")
        
        guard let matchId = message["match_id"] as? String,
              let sessionId = message["session_id"] as? String,
              let roomId = message["room_id"] as? String,
              let livekitToken = message["livekit_token"] as? String else {
            print("❌ [MATCHING] Invalid match data - missing required fields")
            return
        }
        
        // Parse participants
        let participantsData = message["participants"] as? [[String: Any]] ?? []
        let participants = participantsData.compactMap { data -> MatchParticipant? in
            guard let userId = data["user_id"] as? String,
                  let displayName = data["display_name"] as? String,
                  let isCurrentUser = data["is_current_user"] as? Bool else {
                return nil
            }
            return MatchParticipant(userId: userId, displayName: displayName, isCurrentUser: isCurrentUser)
        }
        
        let topics = message["topics"] as? [String] ?? []
        let hashtags = message["hashtags"] as? [String] ?? []
        
        let liveMatchData = LiveMatchData(
            matchId: matchId,
            sessionId: sessionId,
            roomId: roomId,
            livekitToken: livekitToken,
            participants: participants,
            topics: topics,
            hashtags: hashtags
        )
        
        // Immediately update match found to trigger navigation
        DispatchQueue.main.async {
            print("✅ [MATCHING] Setting matchFound to trigger immediate navigation")
                self.matchFound = liveMatchData
        }
    }
    
    // MARK: - WebSocketDelegate
    
    func webSocketDidConnect(_ service: WebSocketService) {
        let isMatchingWebSocket = service is MatchingWebSocketService
        
        if isMatchingWebSocket {
            print("✅✅✅ [MATCHING] ===== MATCHING WEBSOCKET CONNECTED =====")
            print("🎯 [MATCHING] Ready to receive match notifications")
            print("🔍 [MATCHING] Current user ID: \(AuthService.shared.userId ?? "unknown")")
            print("🔍 [MATCHING] Current timestamp: \(Date().timeIntervalSince1970)")
            print("🔍 [MATCHING] Connection established successfully!")
        } else {
            print("✅ [AI_AUDIO] AI Audio WebSocket connected to GPT-4o Realtime")
            
            DispatchQueue.main.async {
                self.isConnected = true
            }
            
            // Send authentication message
            let authMessage: [String: Any] = [
                "type": "auth",
                "token": authToken ?? ""
            ]
            
            service.send(authMessage)
            print("📤 [AI_AUDIO] Sent authentication to AI audio stream")
        }
    }
    
    func webSocketDidDisconnect(_ service: WebSocketService) {
        let isMatchingWebSocket = service is MatchingWebSocketService
        
        if isMatchingWebSocket {
            print("❌❌❌ [MATCHING] ===== MATCHING WEBSOCKET DISCONNECTED =====")
            print("❌ [MATCHING] NO MORE MATCH NOTIFICATIONS WILL BE RECEIVED!")
            print("🔍 [MATCHING] Disconnect timestamp: \(Date().timeIntervalSince1970)")
            print("🔍 [MATCHING] Current user ID: \(AuthService.shared.userId ?? "unknown")")
            print("🔍 [MATCHING] Current matchFound state: \(String(describing: matchFound))")
            print("⚠️ [MATCHING] This could be why matches are being missed!")
        } else {
            print("❌ [AI_AUDIO] AI Audio WebSocket disconnected")
            
            DispatchQueue.main.async {
                self.isConnected = false
                self.isListening = false
            }
            
            stopAllAudio()
        }
    }
    
    func webSocket(_ service: WebSocketService, didReceiveMessage message: [String: Any]) {
        let messageType = message["type"] as? String ?? "unknown"
        let isMatchingWebSocket = service is MatchingWebSocketService
        
        // Only log important messages, not frequent audio messages
        if !["response.audio.delta", "audio_received", "stt_chunk", "audio_chunk"].contains(messageType) {
            print("📥 [AIVoice] Received message: \(messageType) from \(isMatchingWebSocket ? "MATCHING" : "AI_AUDIO") WebSocket")
        }
        
        guard let type = message["type"] as? String else { return }
        
        // Handle messages from Matching WebSocket
        if isMatchingWebSocket {
            print("🎯🎯🎯 [MATCHING] ===== PROCESSING MATCHING WEBSOCKET MESSAGE =====")
            print("🔍 [MATCHING] Message type: \(type)")
            print("🔍 [MATCHING] Full message: \(message)")
            print("🔍 [MATCHING] Current thread: \(Thread.current)")
            print("🔍 [MATCHING] Is main thread: \(Thread.isMainThread)")
            
            switch type {
            case "welcome":
                print("✅ [MATCHING] Connected to matching WebSocket successfully!")
                print("🎯 [MATCHING] Connection ID: \(message["connection_id"] as? String ?? "unknown")")
                print("🎯 [MATCHING] User ID: \(message["user_id"] as? String ?? "unknown")")
                
            case "match_found":
                print("🎉🎉🎉 [MATCHING] MATCH FOUND NOTIFICATION RECEIVED!")
                print("🎯 [MATCHING] Match ID: \(message["match_id"] as? String ?? "unknown")")
                print("🎯 [MATCHING] Room ID: \(message["room_id"] as? String ?? "unknown")")
                print("🎯 [MATCHING] Session ID: \(message["session_id"] as? String ?? "unknown")")
                print("🎯 [MATCHING] Processing match data...")
                handleMatchFound(message)
                
            case "queue_update", "queue_position_update":
                let position = message["position"] as? Int ?? 0
                let waitTime = message["estimated_wait_time"] as? Int ?? 0
                print("📊 [MATCHING] Queue update - Position: \(position), Wait time: \(waitTime)s")
                
            case "ai_match_found":
                print("🤖🎉🎉🎉 [MATCHING] AI MATCH FOUND NOTIFICATION!")
                print("🤖 [MATCHING] AI Match ID: \(message["match_id"] as? String ?? "unknown")")
                print("🤖 [MATCHING] AI Room ID: \(message["room_id"] as? String ?? "unknown")")
                print("🤖 [MATCHING] Processing AI match data...")
                handleMatchFound(message)
                
            case "timeout_match_found":
                print("⏰🎉🎉🎉 [MATCHING] TIMEOUT MATCH FOUND!")
                print("⏰ [MATCHING] Timeout Match ID: \(message["match_id"] as? String ?? "unknown")")
                print("⏰ [MATCHING] Timeout Room ID: \(message["room_id"] as? String ?? "unknown")")
                print("⏰ [MATCHING] Processing timeout match data...")
                handleMatchFound(message)
                
            case "ping":
                // Heartbeat message - just acknowledge
                print("💓 [MATCHING] Heartbeat received")
                
            case "queue_stats":
                let totalUsers = message["total_users_in_queue"] as? Int ?? 0
                let avgWaitTime = message["average_wait_time"] as? Int ?? 0
                print("📊 [MATCHING] Queue stats - Total users: \(totalUsers), Avg wait: \(avgWaitTime)s")
                
            case "error":
                let errorMsg = message["message"] as? String ?? "unknown"
                print("❌❌❌ [MATCHING] WebSocket Error: \(errorMsg)")
                print("❌ [MATCHING] Full error message: \(message)")
                
            default:
                print("❓❓❓ [MATCHING] Unknown matching message type: \(type)")
                print("🔍 [MATCHING] Full unknown message: \(message)")
            }
            
            print("🎯🎯🎯 [MATCHING] ===== MATCHING WEBSOCKET MESSAGE PROCESSED =====")
            return
        }
        
        // Handle messages from AI Audio WebSocket (existing logic with less verbose logging)
        switch type {
        case "authenticated":
            print("✅ [AI_AUDIO] Authenticated with backend")
            if !isAuthenticated {
                sendStartSession()
                isAuthenticated = true
            }
            
        case "session_started":
            print("✅ [AI_AUDIO] Session started")
            sessionStarted = true
            
            // Set a simple static greeting with topic and start listening
            DispatchQueue.main.async {
                if let firstTopic = self.matchContext?.topics.first {
                    self.currentResponse = "Hi! I'm Vortex, nice to meet you! Tell me more about \(firstTopic)."
                } else {
                    self.currentResponse = "Hi! I'm Vortex, nice to meet you! What would you like to talk about?"
                }
            }
            
            Task {
                await startListening()
            }
            
        case "stt_chunk":
            // Do not display partial transcription to avoid UI flicker - COMMENTED OUT
            break
        
        case "stt_done":
            print("✅ [AI_AUDIO] Complete transcription received")
            if let text = message["text"] as? String {
                print("📝✅ [AI_AUDIO] You said: '\(text)'")
                DispatchQueue.main.async {
                    self.currentResponse = "" // Clear to prepare for AI response
                }
            }
            
        case "speech_started":
            print("🎤 [AI_AUDIO] User speech started")
            
        case "speech_stopped":
            print("🔇 [AI_AUDIO] User speech stopped")
            
        case "ai_response_started":
            print("🤖 [AI_AUDIO] AI response started")
            stopAllAudio() // Stop previous audio, start new response
            audioPlaybackQueue.async {
                self.audioAccumulator.removeAll(keepingCapacity: true)
                self.lastTail.removeAll(keepingCapacity: true)
            }
            
            // Auto-mute user input during AI speech
            DispatchQueue.main.async {
                self.isAISpeaking = true
            }
            stopAudioEngine() // Stop recording user input
            
        case "response.text.delta":
            // print("📝 [AI_AUDIO] Text delta received") // COMMENTED OUT - too verbose
            if let textDelta = message["delta"] as? String {
                DispatchQueue.main.async {
                    self.currentResponse += textDelta
                }
            }
            
        case "response.audio.delta":
            // print("🔊 [AI_AUDIO] Audio delta received") // COMMENTED OUT - too verbose
            if let audioData = message["delta"] as? String {
                addPCMChunk(audioData)
            }
            
        case "response.done":
            print("✅ [AI_AUDIO] AI response completed")
            audioPlaybackQueue.async {
                self.finalizeAndPlayAudioOnQueue()
            }
            
        case "audio_received":
            // COMMENTED OUT - too verbose: print("📥 [AI_AUDIO] Audio received confirmation")
            break
            

            
        case "error":
            print("❌ [AI_AUDIO] WebSocket error: \(message["message"] as? String ?? "unknown")")
            
        default:
            // Only log unknown types that aren't common verbose messages
            if !["response.audio.delta", "audio_chunk", "stt_chunk"].contains(type) {
                print("❓ [AI_AUDIO] Unknown AI audio message type: \(type)")
            }
        }
    }
    
    func webSocket(_ service: WebSocketService, didEncounterError error: Error) {
        print("❌ [AIVoice] WebSocket error: \(error)")
        
        DispatchQueue.main.async {
            self.isConnected = false
            self.isListening = false
        }
    }
}

// MARK: - AVAudioPlayerDelegate
extension AIVoiceService {
    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        print("🔊 [AIVoice] Audio finished playing successfully: \(flag)")
        audioPlaybackFinished()
    }
    
    func audioPlayerDecodeErrorDidOccur(_ player: AVAudioPlayer, error: Error?) {
        print("❌ [AIVoice] Audio decode error: \(error?.localizedDescription ?? "unknown")")
        audioPlaybackFinished()
    }
}

struct VoicePinchedCircle: View {
    var level: CGFloat
    private let baseDiameter: CGFloat = 34
    private let growth: CGFloat = 38

    var body: some View {
        Capsule()
            .fill(Color(white: 0.93))
            .frame(width: baseDiameter,
                   height: baseDiameter + level * growth)
            .shadow(radius: 2)
    }
}

// Keep backward compatibility for preview
struct UserVoiceInput: View {
    var body: some View {
        NavigationView {
            UserVoiceTopicMatchingView(matchResult: MatchResult(
                transcription: "I want to talk about AI",
                topics: ["Artificial Intelligence", "Technology"],
                hashtags: ["#AI", "#Tech"],
                matchId: "preview_match",
                sessionId: "preview_session",
                confidence: 0.8,
                waitTime: 30
            ))
        }
    }
}

#Preview {
    UserVoiceInput()
}

// MARK: - Extensions
extension AVAudioPCMBuffer {
    func toData() -> Data? {
        let audioBuffer = audioBufferList.pointee.mBuffers
        let data = Data(bytes: audioBuffer.mData!, count: Int(audioBuffer.mDataByteSize))
        return data
    }
}

// MARK: - Matching WebSocket Service
class MatchingWebSocketService: WebSocketService {
    override func connect(to endpoint: String, with token: String) {
        print("🎯 [MatchingWS] Connecting to matching WebSocket: \(endpoint)")
        print("🎯 [MatchingWS] Full URL will be: \(APIConfig.wsBaseURL)\(endpoint)")
        print("🎯 [MatchingWS] Token prefix: \(token.prefix(20))...")
        super.connect(to: endpoint, with: token)
    }
    
    override func send(_ message: [String : Any]) {
        print("📤 [MatchingWS] Sending message: \(message["type"] as? String ?? "unknown")")
        super.send(message)
    }
}
