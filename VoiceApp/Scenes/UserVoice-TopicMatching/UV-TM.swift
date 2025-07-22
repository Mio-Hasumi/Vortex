//
//  UV-TM.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/18/25.
//
import SwiftUI
import Combine
import AVFoundation

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
    
    // Navigation state for when match is found
    @State private var navigateToLiveChat = false
    @State private var matchData: LiveMatchData?

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
                
                // AI text response display area
                ScrollView {
                    Text(aiVoiceService.currentResponse)
                        .font(.custom("Rajdhani", size: 28))
                        .foregroundColor(.white)
                        .multilineTextAlignment(.center)
                        .padding()
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
                    Image(systemName: aiVoiceService.isMuted ? "mic.slash.fill" : "mic.fill")
                        .font(.system(size: 40))
                        .foregroundColor(aiVoiceService.isMuted ? .red : .white)
                        .padding(20)
                        .background(Circle().fill(Color.white.opacity(0.2)))
                }
                
                Text(aiVoiceService.isMuted ? "Muted" : "Listening...")
                    .foregroundColor(.white)
                    .padding(.bottom, 30)
            }
        }
        .onAppear {
            // Initialize AI conversation when view appears
            Task {
                await aiVoiceService.initializeAIConversation(with: matchResult)
            }
        }
        .onDisappear {
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
                print("🚀 [NAVIGATION] Match found - immediately navigating to chat!")
                
                // Stop AI conversation and navigate immediately
                Task {
                    await aiVoiceService.stopAIConversation()
                    await MainActor.run {
                        self.matchData = matchData
                        // Add a small delay to ensure proper navigation
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                            self.navigateToLiveChat = true
                            print("✅ [NAVIGATION] Direct navigation to chat initiated")
                        }
                    }
                }
            }
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
    
    private func setupAudioSession() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
            
            // Set preferred sample rate to 24kHz to match GPT-4o
            try audioSession.setPreferredSampleRate(24000)
            try audioSession.setActive(true)
            
            print("✅ [AIVoice] Audio session configured for 24kHz voice chat (GPT-4o compatible)")
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
        
        // Create target format (24kHz, Int16, mono) - match OpenAI Realtime API requirements
        guard let targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, 
                                             sampleRate: 24000,  // OpenAI requires 24kHz
                                             channels: 1, 
                                             interleaved: false) else {
            print("❌ [AIVoice] Failed to create target audio format")
            return
        }
        
        print("🎵 [AIVoice] Target format for OpenAI: 24kHz, PCM16, mono")
        
        // Install tap using hardware's native format - use 0 for automatic buffer size
        inputNode.installTap(onBus: 0, bufferSize: 0, format: inputFormat) { [weak self] buffer, time in
            self?.processAudioBuffer(buffer, originalFormat: inputFormat, targetFormat: targetFormat)
        }
        
        print("✅ [AIVoice] Audio engine configured for streaming")
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
- Greet naturally with "Hi! I'm Vortex, nice to meet you!"
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
            if let userId = AuthService.shared.userId {
                let matchingEndpoint = "\(APIConfig.WebSocket.matching)?user_id=\(userId)"
                matchingWebSocketService?.connect(to: matchingEndpoint, with: token)
                print("🎯 [MATCHING] Connecting to matching WebSocket with user ID: \(userId)")
                print("🎯 [MATCHING] Full endpoint: \(matchingEndpoint)")
            } else {
                print("❌ [MATCHING] No user ID available for matching WebSocket - CRITICAL ERROR!")
            }
        }
    }
    
    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer, originalFormat: AVAudioFormat, targetFormat: AVAudioFormat) {
        guard sessionStarted && !isMuted && isRecording else { 
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
            "timestamp": Date().timeIntervalSince1970
        ]
        
        webSocketService?.send(startSessionMessage)
        print("📤 [AIVoice] Sent start session with topic context")
    }
    
    func startListening() async {
        guard sessionStarted && !isMuted else {
            print("⚠️ [AIVoice] Cannot start listening - session not started or muted")
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
        } else if sessionStarted {
            startAudioEngine()
        }
    }
    

    
    private func startAudioEngine() {
        guard !isMuted, let audioEngine = audioEngine else { 
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
        
        // Remove notification observer
        NotificationCenter.default.removeObserver(self)
        
        // Stop audio engine immediately
        if let audioEngine = audioEngine, audioEngine.isRunning {
            audioEngine.stop()
            inputNode?.removeTap(onBus: 0)
        }
        audioEngine = nil
        inputNode = nil
        isRecording = false
        
        // Stop audio playback immediately
        currentAudioPlayer?.stop()
        currentAudioPlayer = nil
        audioQueue.removeAll()
        audioAccumulator = Data()
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
    
    private func stopAllAudio() {
        audioPlaybackQueue.async {
            // Stop current playback
            self.currentAudioPlayer?.stop()
            self.currentAudioPlayer = nil
            
            // Clear queue
            self.audioQueue.removeAll()
            self.audioAccumulator = Data()
            
            DispatchQueue.main.async {
                self.isAISpeaking = false
            }
            
            self.isPlayingAudio = false
            print("🔇 [AIVoice] All audio playback stopped and cleared")
        }
    }
    
    private func addAudioChunk(_ base64AudioData: String) {
        guard let audioData = Data(base64Encoded: base64AudioData) else {
            print("❌ [AIVoice] Failed to decode audio chunk")
            return
        }
        
        audioPlaybackQueue.async {
            // Accumulate audio data (GPT-4o sends PCM16 fragments)
            let previousSize = self.audioAccumulator.count
            self.audioAccumulator.append(audioData)
            // print("🎵 [AIVoice] Audio chunk accumulated: +\(audioData.count) bytes, total: \(previousSize) → \(self.audioAccumulator.count) bytes")  // COMMENTED OUT - too verbose
        }
    }
    
    private func finalizeAndPlayAudio() {
        audioPlaybackQueue.async {
            guard !self.audioAccumulator.isEmpty else {
                print("🔇 [AIVoice] No accumulated audio to play")
                return
            }
            
            // print("🔊 [AIVoice] Finalizing and playing complete audio response: \(self.audioAccumulator.count) bytes")  // COMMENTED OUT - too verbose
            
            // Convert PCM16 data to WAV format for playback
            let wavData = self.convertPCM16ToWAV(self.audioAccumulator)
            
            // Add to playback queue
            self.audioQueue.append(wavData)
            
            // Start playback queue (if not currently playing)
            if !self.isPlayingAudio {
                self.playNextAudioInQueue()
            }
            
            // Clear accumulator, prepare for next response
            self.audioAccumulator = Data()
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
                // Stop previous player
                self.currentAudioPlayer?.stop()
                
                // Create new player
                self.currentAudioPlayer = try AVAudioPlayer(data: audioData)
                self.currentAudioPlayer?.delegate = self
                
                // Start playback
                let success = self.currentAudioPlayer?.play() ?? false
                print("🔊 [AIVoice] \(success ? "✅ Started" : "❌ Failed to start") playing audio: \(audioData.count) bytes")
                
                if !success {
                    self.audioPlaybackFinished()
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
                }
            }
            
            // Continue playing the next audio in the queue
            if !self.audioQueue.isEmpty {
                self.playNextAudioInQueue()
            }
            
            // print("🔊 [AIVoice] Audio playback finished, queue remaining: \(self.audioQueue.count)")  // COMMENTED OUT - too verbose
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
            
            // Set a simple static greeting and start listening
            DispatchQueue.main.async {
                self.currentResponse = "Hi! I'm Vortex. What would you like to talk about?"
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
                addAudioChunk(audioData)
            }
            
        case "response.done":
            print("✅ [AI_AUDIO] AI response completed")
            finalizeAndPlayAudio() // Finalize and play
            
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
