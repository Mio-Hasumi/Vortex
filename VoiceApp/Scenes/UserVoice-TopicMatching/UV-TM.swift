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
}

// 简化后的视图，只保留核心功能
struct UserVoiceTopicMatchingView: View {
    let matchResult: MatchResult
    @Environment(\.dismiss) private var dismiss
    
    // AI服务，处理所有WebSocket和音频逻辑
    @StateObject private var aiVoiceService = AIVoiceService()
    
    // Navigation state for when match is found
    @State private var navigateToLiveChat = false
    @State private var matchData: LiveMatchData?

    var body: some View {
        ZStack {
            // 背景
            Color.black.ignoresSafeArea()

            // 顶部UI元素
            VStack {
                // 返回按钮
                HStack {
                    Button(action: {
                        // 停止AI服务并返回
                        aiVoiceService.cleanup()
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
                
                // AI回复的文字显示区域
                ScrollView {
                    Text(aiVoiceService.currentResponse)
                        .font(.custom("Rajdhani", size: 28))
                        .foregroundColor(.white)
                        .multilineTextAlignment(.center)
                        .padding()
                }
                
                Spacer()
            }
            
            // 底部麦克风按钮
            VStack {
                Spacer()
                
                Button(action: {
                    // 切换静音状态
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
            // 视图出现时初始化AI对话
            Task {
                await aiVoiceService.initializeAIConversation(with: matchResult)
            }
        }
        .navigationBarHidden(true)
        // Navigation to live chat when match is found
        .background(
            NavigationLink(
                destination: matchData.map { data in
                    HashtagScreen(matchData: data)
                },
                isActive: $navigateToLiveChat
            ) {
                EmptyView()
            }
            .hidden()
        )
        // Listen for match found events
        .onReceive(aiVoiceService.$matchFound) { matchData in
            print("🔔 [NAVIGATION] onReceive triggered - matchData received!")
            
            if let matchData = matchData {
                print("✅ [NAVIGATION] Match data is valid:")
                print("   🆔 Match ID: \(matchData.matchId)")
                print("   🏠 Room ID: \(matchData.roomId)")
                print("   👥 Participants: \(matchData.participants.count)")
                print("🚀 [NAVIGATION] Setting navigation state...")
                
                self.matchData = matchData
                self.navigateToLiveChat = true
                
                print("✅ [NAVIGATION] Navigation state set - should navigate now!")
            } else {
                print("❌ [NAVIGATION] Match data is nil - no navigation will occur")
            }
        }
    }
}

// MARK: - AI 语音服务 - GPT-4o Realtime WebSocket
class AIVoiceService: NSObject, ObservableObject, WebSocketDelegate, AVAudioPlayerDelegate {
    @Published var isConnected = false
    @Published var isListening = false
    @Published var isMuted = false
    @Published var currentResponse = ""
    @Published var isAISpeaking = false
    @Published var matchFound: LiveMatchData?
    
    private var matchContext: MatchResult?
    private var conversationContext: String = ""
    private var webSocketService: WebSocketService?
    private var matchingWebSocketService: WebSocketService?  // NEW: Separate WebSocket for matching notifications
    private var authToken: String?
    private var isAuthenticated = false
    private var sessionStarted = false
    
    // 音频相关
    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private var isRecording = false
    private var audioStartTime: Date?
    private var audioChunkIndex: Int = 0
    
    // 🔧 修复后的统一音频播放系统
    private var audioPlaybackQueue = DispatchQueue(label: "audio.playback", qos: .userInitiated)
    private var currentAudioPlayer: AVAudioPlayer?
    private var audioQueue: [Data] = [] // 排队等待播放的音频数据
    private var isPlayingAudio = false
    private var audioAccumulator = Data() // 累积单个完整响应的所有音频块
    
    override init() {
        // 获取认证令牌
        authToken = AuthService.shared.firebaseToken
        super.init()
        setupAudioSession()
        setupAudioEngine()
    }
    
    private func setupAudioSession() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
            
            // 设置首选采样率为24kHz匹配GPT-4o
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
        
        // 使用硬件的实际输入格式
        let inputFormat = inputNode.inputFormat(forBus: 0)
        print("🎙️ [AIVoice] Hardware input format: \(inputFormat)")
        
        // 创建目标格式 (24kHz, Int16, mono) - 匹配OpenAI Realtime API要求
        guard let targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, 
                                             sampleRate: 24000,  // OpenAI要求24kHz
                                             channels: 1, 
                                             interleaved: false) else {
            print("❌ [AIVoice] Failed to create target audio format")
            return
        }
        
        print("🎵 [AIVoice] Target format for OpenAI: 24kHz, PCM16, mono")
        
        // 安装tap使用硬件的原生格式
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, time in
            self?.processAudioBuffer(buffer, originalFormat: inputFormat, targetFormat: targetFormat)
        }
        
        print("✅ [AIVoice] Audio engine configured for streaming")
    }
    
    func initializeAIConversation(with matchResult: MatchResult) async {
        print("🤖 [AIVoice] Initializing AI conversation for session: \(generateSessionId())")
        
        self.matchContext = matchResult
        
        // 设置对话上下文
        let systemPrompt = """
You are Vortex, a friendly AI conversation partner in a voice chat app called Vortex. The user wants to discuss these topics: \(matchResult.topics.joined(separator: ", ")).

Please start by saying "Hi, I'm Vortex! Nice to meet you!" and then engage in a natural conversation about these topics, asking thoughtful questions and sharing relevant insights. Keep your responses concise and engaging.
"""
        
                  conversationContext = """
          You are Vortex, a friendly AI conversation partner in a voice chat app. The user wants to discuss these topics: \(matchResult.topics.joined(separator: ", "))
        
        Their original message was: "\(matchResult.transcription)"
        
        Key guidelines:
        - Start with a warm greeting: "Hi, I'm Vortex! Nice to meet you!"
        - You are NOT a matching algorithm or service
        - You are a conversation partner who enjoys discussing these topics
        - Keep responses conversational and engaging (1-3 sentences)
        - Ask follow-up questions to keep the conversation flowing
        - Use natural, spoken language (this is voice chat)
        - Don't mention "finding matches" or "waiting for others"
        - Focus on having an interesting discussion about the topics
        
        Hashtags for context: \(matchResult.hashtags.joined(separator: ", "))
        """
        
        print("🧠 [AIVoice] AI conversation context set for topics: \(matchResult.topics)")
        
        // 连接到 WebSocket
        await connectToRealtimeAPI()
        
        print("✅ [AIVoice] AI conversation initialized")
    }
    
    private func connectToRealtimeAPI() async {
        guard let token = authToken else {
            print("❌ [AIVoice] No auth token available")
            return
        }
        
        print("🔌 [AIVoice] Connecting to both AI Audio Stream and Matching WebSockets...")
        print("🔍 [MATCHING] Starting WebSocket connection setup for matching notifications")
        
        await MainActor.run {
            // 创建 AI 音频流 WebSocket 服务
            webSocketService = WebSocketService()
            webSocketService?.delegate = self
            
            // 创建匹配通知 WebSocket 服务
            matchingWebSocketService = MatchingWebSocketService()
            matchingWebSocketService?.delegate = self
            
            // 连接到音频流端点
            webSocketService?.connect(to: APIConfig.WebSocket.aiAudioStream, with: token)
            print("🎵 [AI_AUDIO] Connecting to AI audio stream WebSocket")
            
            // 连接到匹配通知端点 (需要用户ID)
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
        
        // 创建音频转换器
        guard let converter = AVAudioConverter(from: originalFormat, to: targetFormat) else {
            print("❌ [AIVoice] Failed to create audio converter")
            return
        }
        
        // 创建输出缓冲区
        let outputFrameCapacity = AVAudioFrameCount(Double(buffer.frameLength) * targetFormat.sampleRate / originalFormat.sampleRate)
        guard let outputBuffer = AVAudioPCMBuffer(pcmFormat: targetFormat, frameCapacity: outputFrameCapacity) else {
            print("❌ [AIVoice] Failed to create output buffer")
            return
        }
        
        // 执行格式转换
        var error: NSError?
        _ = converter.convert(to: outputBuffer, error: &error) { _, outStatus in
            outStatus.pointee = .haveData
            return buffer
        }
        
        if let error = error {
            print("❌ [AIVoice] Audio conversion failed: \(error)")
            return
        }
        
        // 转换为Data
        guard let audioData = outputBuffer.toData() else {
            print("❌ [AIVoice] Failed to convert converted buffer to data")
            return
        }
        
        // 编码为base64并发送
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
    
    func cleanup() {
        print("🧹 [AIVoice] Starting cleanup process")
        
        // Stop audio engine
        stopAudioEngine()
        
        // Stop any playing audio
        stopAllAudio()
        
        // Disconnect both WebSocket connections
        webSocketService?.disconnect()
        webSocketService = nil
        
        matchingWebSocketService?.disconnect()
        matchingWebSocketService = nil
        
        // Reset all state
        isConnected = false
        isListening = false
        sessionStarted = false
        isAuthenticated = false
        
        // Clear audio data
        audioQueue.removeAll()
        audioAccumulator = Data()
        
        print("✅ [AIVoice] Cleanup completed")
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
    
    deinit {
        cleanup()
        inputNode?.removeTap(onBus: 0)
        print("🧹 [AIVoice] Audio service deallocated")
    }
    
    // MARK: - 🔧 修复后的统一音频播放系统
    
    private func stopAllAudio() {
        audioPlaybackQueue.async {
            // 停止当前播放
            self.currentAudioPlayer?.stop()
            self.currentAudioPlayer = nil
            
            // 清空队列
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
            // 累积音频数据（GPT-4o发送的是PCM16片段）
            let previousSize = self.audioAccumulator.count
            self.audioAccumulator.append(audioData)
            print("🎵 [AIVoice] Audio chunk accumulated: +\(audioData.count) bytes, total: \(previousSize) → \(self.audioAccumulator.count) bytes")
        }
    }
    
    private func finalizeAndPlayAudio() {
        audioPlaybackQueue.async {
            guard !self.audioAccumulator.isEmpty else {
                print("🔇 [AIVoice] No accumulated audio to play")
                return
            }
            
            print("🔊 [AIVoice] Finalizing and playing complete audio response: \(self.audioAccumulator.count) bytes")
            
            // 转换PCM16数据为WAV格式用于播放
            let wavData = self.convertPCM16ToWAV(self.audioAccumulator)
            
            // 添加到播放队列
            self.audioQueue.append(wavData)
            
            // 开始播放队列（如果当前没有在播放）
            if !self.isPlayingAudio {
                self.playNextAudioInQueue()
            }
            
            // 清空累积器，准备下一个响应
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
                // 停止之前的播放器
                self.currentAudioPlayer?.stop()
                
                // 创建新的播放器
                self.currentAudioPlayer = try AVAudioPlayer(data: audioData)
                self.currentAudioPlayer?.delegate = self
                
                // 开始播放
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
            
            // 继续播放队列中的下一个音频
            if !self.audioQueue.isEmpty {
                self.playNextAudioInQueue()
            }
            
            print("🔊 [AIVoice] Audio playback finished, queue remaining: \(self.audioQueue.count)")
        }
    }
    
    private func convertPCM16ToWAV(_ pcmData: Data) -> Data {
        // WAV文件头信息 (24kHz, 16-bit, mono)
        let sampleRate: UInt32 = 24000
        let channels: UInt16 = 1
        let bitsPerSample: UInt16 = 16
        let byteRate = sampleRate * UInt32(channels) * UInt32(bitsPerSample) / 8
        let blockAlign = channels * bitsPerSample / 8
        let dataSize = UInt32(pcmData.count)
        let fileSize = 36 + dataSize
        
        var wavData = Data()
        
        // RIFF头
        wavData.append("RIFF".data(using: .ascii)!)
        wavData.append(withUnsafeBytes(of: fileSize.littleEndian) { Data($0) })
        wavData.append("WAVE".data(using: .ascii)!)
        
        // fmt块
        wavData.append("fmt ".data(using: .ascii)!)
        wavData.append(withUnsafeBytes(of: UInt32(16).littleEndian) { Data($0) }) // fmt块大小
        wavData.append(withUnsafeBytes(of: UInt16(1).littleEndian) { Data($0) })  // PCM格式
        wavData.append(withUnsafeBytes(of: channels.littleEndian) { Data($0) })
        wavData.append(withUnsafeBytes(of: sampleRate.littleEndian) { Data($0) })
        wavData.append(withUnsafeBytes(of: byteRate.littleEndian) { Data($0) })
        wavData.append(withUnsafeBytes(of: blockAlign.littleEndian) { Data($0) })
        wavData.append(withUnsafeBytes(of: bitsPerSample.littleEndian) { Data($0) })
        
        // data块
        wavData.append("data".data(using: .ascii)!)
        wavData.append(withUnsafeBytes(of: dataSize.littleEndian) { Data($0) })
        wavData.append(pcmData)
        
        return wavData
    }
    
    // MARK: - Helper 方法
    
    private func generateSessionId() -> String {
        return "ai_waiting_\(UUID().uuidString)_\(Date().timeIntervalSince1970)"
    }
    
    private func handleMatchFound(_ message: [String: Any]) {
        print("🎯🎯🎯 [MATCHING] ===== PROCESSING MATCH FOUND MESSAGE =====")
        print("🔍 [MATCHING] Full message received: \(message)")
        
        guard let matchId = message["match_id"] as? String,
              let sessionId = message["session_id"] as? String,
              let roomId = message["room_id"] as? String,
              let livekitToken = message["livekit_token"] as? String else {
            print("❌ [MATCHING] Invalid match data received - missing required fields!")
            print("❌ [MATCHING] match_id: \(message["match_id"] as? String ?? "MISSING")")
            print("❌ [MATCHING] session_id: \(message["session_id"] as? String ?? "MISSING")")
            print("❌ [MATCHING] room_id: \(message["room_id"] as? String ?? "MISSING")")
            print("❌ [MATCHING] livekit_token: \(message["livekit_token"] as? String ?? "MISSING")")
            return
        }
        
        print("✅ [MATCHING] All required fields present:")
        print("   🆔 Match ID: \(matchId)")
        print("   📱 Session ID: \(sessionId)")
        print("   🏠 Room ID: \(roomId)")
        print("   🎫 LiveKit Token: \(livekitToken.prefix(20))...")
        
        // Parse participants
        let participantsData = message["participants"] as? [[String: Any]] ?? []
        print("👥 [MATCHING] Parsing \(participantsData.count) participants...")
        
        let participants = participantsData.compactMap { data -> MatchParticipant? in
            guard let userId = data["user_id"] as? String,
                  let displayName = data["display_name"] as? String,
                  let isCurrentUser = data["is_current_user"] as? Bool else {
                print("❌ [MATCHING] Invalid participant data: \(data)")
                return nil
            }
            print("👤 [MATCHING] Participant: \(displayName) (\(userId)) - Current user: \(isCurrentUser)")
            return MatchParticipant(userId: userId, displayName: displayName, isCurrentUser: isCurrentUser)
        }
        
        let topics = message["topics"] as? [String] ?? []
        let hashtags = message["hashtags"] as? [String] ?? []
        
        print("🏷️ [MATCHING] Topics: \(topics)")
        print("#️⃣ [MATCHING] Hashtags: \(hashtags)")
        
        let liveMatchData = LiveMatchData(
            matchId: matchId,
            sessionId: sessionId,
            roomId: roomId,
            livekitToken: livekitToken,
            participants: participants,
            topics: topics,
            hashtags: hashtags
        )
        
        print("✅ [MATCHING] Match data processed successfully!")
        print("   👥 Participants count: \(participants.count)")
        print("   🏷️ Topics count: \(topics.count)")
        print("   #️⃣ Hashtags count: \(hashtags.count)")
        
        print("🚀 [MATCHING] Setting matchFound to trigger navigation...")
        
        // Update on main thread
        DispatchQueue.main.async {
            self.matchFound = liveMatchData
            print("✅ [MATCHING] matchFound set on main thread - should trigger navigation now!")
        }
        
        print("🎯🎯🎯 [MATCHING] ===== MATCH PROCESSING COMPLETED =====")
    }
    
    // MARK: - WebSocketDelegate
    
    func webSocketDidConnect(_ service: WebSocketService) {
        let isMatchingWebSocket = service is MatchingWebSocketService
        
        if isMatchingWebSocket {
            print("✅ [MATCHING] Matching WebSocket connected successfully!")
            print("🎯 [MATCHING] Ready to receive match notifications")
        } else {
            print("✅ [AI_AUDIO] AI Audio WebSocket connected to GPT-4o Realtime")
            
            DispatchQueue.main.async {
                self.isConnected = true
            }
            
            // 发送认证消息
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
            print("❌ [MATCHING] Matching WebSocket disconnected - NO MORE MATCH NOTIFICATIONS!")
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
        if !["response.audio.delta", "audio_received", "stt_chunk"].contains(messageType) {
            print("📥 [AIVoice] Received message: \(messageType) from \(isMatchingWebSocket ? "MATCHING" : "AI_AUDIO") WebSocket")
        }
        
        guard let type = message["type"] as? String else { return }
        
        // Handle messages from Matching WebSocket
        if isMatchingWebSocket {
            print("🎯 [MATCHING] Processing matching WebSocket message: \(type)")
            
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
                print("🤖🎉 [MATCHING] AI MATCH FOUND NOTIFICATION!")
                handleMatchFound(message)
                
            case "timeout_match_found":
                print("⏰🎉 [MATCHING] TIMEOUT MATCH FOUND!")
                handleMatchFound(message)
                
            case "ping":
                // Heartbeat message - just acknowledge
                print("💓 [MATCHING] Heartbeat received")
                
            case "error":
                let errorMsg = message["message"] as? String ?? "unknown"
                print("❌ [MATCHING] WebSocket Error: \(errorMsg)")
                
            default:
                print("❓ [MATCHING] Unknown matching message type: \(type)")
                print("🔍 [MATCHING] Full message: \(message)")
            }
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
            
            // Send initial greeting
            let greetingMessage: [String: Any] = [
                "type": "user_message",
                "message": "start_conversation",
                "timestamp": Date().timeIntervalSince1970
            ]
            service.send(greetingMessage)
            print("👋 [AI_AUDIO] Sent initial greeting request")
            
            Task {
                await startListening()
            }
            
        case "stt_chunk":
            // 不显示部分转写，避免UI闪烁 - COMMENTED OUT
            break
            
        case "stt_done":
            print("✅ [AI_AUDIO] Complete transcription received")
            if let text = message["text"] as? String {
                print("📝✅ [AI_AUDIO] You said: '\(text)'")
                DispatchQueue.main.async {
                    self.currentResponse = "" // 清空，准备接收AI回复
                }
            }
            
        case "speech_started":
            print("🎤 [AI_AUDIO] User speech started")
            
        case "speech_stopped":
            print("🔇 [AI_AUDIO] User speech stopped")
            
        case "ai_response_started":
            print("🤖 [AI_AUDIO] AI response started")
            stopAllAudio() // 停止之前的音频，开始新响应
            
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
            finalizeAndPlayAudio() // 完成累积并播放
            
        case "audio_received":
            // COMMENTED OUT - too verbose: print("📥 [AI_AUDIO] Audio received confirmation")
            break
            
        case "error":
            print("❌ [AI_AUDIO] WebSocket error: \(message["message"] as? String ?? "unknown")")
            
        default:
            print("❓ [AI_AUDIO] Unknown AI audio message type: \(type)")
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

// 保持向后兼容的预览
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
