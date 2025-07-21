//
//  UV-TM.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/18/25.
//
import SwiftUI
import Combine
import AVFoundation

// 简化后的视图，只保留核心功能
struct UserVoiceTopicMatchingView: View {
    let matchResult: MatchResult
    @Environment(\.dismiss) private var dismiss
    
    // AI服务，处理所有WebSocket和音频逻辑
    @StateObject private var aiVoiceService = AIVoiceService()

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
                        aiVoiceService.stopAudioEngine(stopPlayback: true)
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
    }
}

// MARK: - AI 语音服务 - GPT-4o Realtime WebSocket
class AIVoiceService: NSObject, ObservableObject, WebSocketDelegate {
    @Published var isConnected = false
    @Published var isMuted = false
    @Published var currentResponse = ""
    @Published var isAISpeaking = false
    
    private var matchContext: MatchResult?
    private var conversationContext: String = ""
    private var webSocketService: WebSocketService?
    private var authToken: String?
    private var isAuthenticated = false
    private var sessionStarted = false
    
    // 音频录制引擎
    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private var isRecording = false
    
    // 音频播放引擎，用于无缝流式播放
    private let playbackAudioEngine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    private var playerFormat: AVAudioFormat!
    
    private var audioStartTime: Date?
    private var audioChunkIndex: Int = 0  // 追踪发送的音频块序号
    
    override init() {
        authToken = AuthService.shared.firebaseToken
        super.init()
        setupAudioSession()
        setupAudioEngine()
        setupPlaybackEngine()
    }
    
    private func setupPlaybackEngine() {
        // AI返回的音频格式：24kHz PCM Int16 单声道
        playerFormat = AVAudioFormat(commonFormat: .pcmFormatInt16,
                                     sampleRate: 24000,
                                     channels: 1,
                                     interleaved: false)!
                                     
        playbackAudioEngine.attach(playerNode)
        playbackAudioEngine.connect(playerNode, to: playbackAudioEngine.mainMixerNode, format: playerFormat)
        
        do {
            try playbackAudioEngine.start()
            playerNode.play()
            print("✅ [AIVoice] Playback engine started for seamless streaming.")
        } catch {
            print("❌ [AIVoice] Failed to start playback engine: \(error)")
        }
    }

    private func setupAudioSession() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
            try audioSession.setPreferredSampleRate(16000)
            try audioSession.setActive(true)
            print("✅ [AIVoice] Audio session configured for 16kHz voice chat")
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
        
        let inputFormat = inputNode.inputFormat(forBus: 0)
        print("🎙️ [AIVoice] Hardware input format: \(inputFormat)")
        
        guard let targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, 
                                             sampleRate: 24000,
                                             channels: 1, 
                                             interleaved: false) else {
            print("❌ [AIVoice] Failed to create target audio format")
            return
        }
        
        print("🎵 [AIVoice] Target format for OpenAI: 24kHz, PCM16, mono")
        
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, time in
            self?.processAudioBuffer(buffer, originalFormat: inputFormat, targetFormat: targetFormat)
        }
        
        print("✅ [AIVoice] Audio engine configured for streaming")
    }
    
    func initializeAIConversation(with matchResult: MatchResult) async {
        print("🤖 [AIVoice] Initializing AI conversation for session: \(generateSessionId())")
        
        self.matchContext = matchResult
        
        conversationContext = """
        You are a friendly AI conversation partner in a voice chat app. The user wants to discuss these topics: \(matchResult.topics.joined(separator: ", ")).
        
        Their original message was: "\(matchResult.transcription)"
        
        Key guidelines:
        - You are NOT a matching algorithm or service
        - You are a conversation partner who enjoys discussing these topics
        - Keep responses conversational and engaging
        - Ask follow-up questions to keep the conversation flowing
        - Use natural, spoken language (this is voice chat)
        - Don't mention "finding matches" or "waiting for others"
        - Focus on having an interesting discussion about the topics
        
        Hashtags for context: \(matchResult.hashtags.joined(separator: ", "))
        """
        
        await connectToRealtimeAPI()
    }
    
    private func connectToRealtimeAPI() async {
        guard let token = authToken else {
            print("❌ [AIVoice] No auth token available")
            return
        }
        
        await MainActor.run {
            webSocketService = WebSocketService()
            webSocketService?.delegate = self
            webSocketService?.connect(to: APIConfig.WebSocket.aiAudioStream, with: token)
        }
    }
    
    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer, originalFormat: AVAudioFormat, targetFormat: AVAudioFormat) {
        guard sessionStarted && !isMuted && isRecording else { return }
        
        let audioLevel = calculateAudioLevel(buffer)
        
        guard let converter = AVAudioConverter(from: originalFormat, to: targetFormat) else { return }
        
        let outputFrameCapacity = AVAudioFrameCount(Double(buffer.frameLength) * targetFormat.sampleRate / originalFormat.sampleRate)
        guard let outputBuffer = AVAudioPCMBuffer(pcmFormat: targetFormat, frameCapacity: outputFrameCapacity) else { return }
        
        var error: NSError?
        _ = converter.convert(to: outputBuffer, error: &error) { _, outStatus in
            outStatus.pointee = .haveData
            return buffer
        }
        
        if error != nil { return }
        
        guard let audioData = outputBuffer.toData() else { return }
        
        let base64Audio = audioData.base64EncodedString()
        
        let audioMessage: [String: Any] = [
            "type": "input_audio_buffer.append",
            "audio": base64Audio,
            "timestamp": Date().timeIntervalSince1970
        ]
        
        audioChunkIndex += 1
        webSocketService?.send(audioMessage)
    }
    
    private func calculateAudioLevel(_ buffer: AVAudioPCMBuffer) -> Float {
        guard let channelData = buffer.floatChannelData?[0] else { return 0.0 }
        var maxLevel: Float = 0.0
        let frameCount = Int(buffer.frameLength)
        for i in 0..<frameCount {
            let sample = abs(channelData[i])
            maxLevel = max(maxLevel, sample)
        }
        return maxLevel
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
        guard sessionStarted && !isMuted else { return }
        await MainActor.run { isListening = true }
        startAudioEngine()
    }
    
    func toggleMute() {
        isMuted.toggle()
        print("🔇 [AIVoice] Audio input \(isMuted ? "muted" : "unmuted")")
        if isMuted {
            stopAudioEngine(stopPlayback: false)
        } else if sessionStarted {
            startAudioEngine()
        }
    }
    
    private func startAudioEngine() {
        guard !isMuted, let audioEngine = audioEngine else { return }
        do {
            if !audioEngine.isRunning {
                audioEngine.prepare()
                try audioEngine.start()
                isRecording = true
                print("🎙️ [AIVoice] ✅ Recording engine started.")
            }
        } catch {
            print("❌ [AIVoice] Failed to start recording engine: \(error)")
        }
    }
    
    func stopAudioEngine(stopPlayback: Bool = true) {
        if let audioEngine = audioEngine, audioEngine.isRunning {
            audioEngine.stop()
            isRecording = false
            print("⏹️ [AIVoice] Recording engine stopped.")
        }
        if stopPlayback && playbackAudioEngine.isRunning {
             playbackAudioEngine.stop()
             playerNode.stop()
             print("⏹️ [AIVoice] Playback engine stopped.")
        }
    }
    
    deinit {
        stopAudioEngine()
        inputNode?.removeTap(onBus: 0)
        print("🧹 [AIVoice] Audio service cleaned up")
    }
    
    private func generateSessionId() -> String {
        return "ai_waiting_\(UUID().uuidString)_\(Date().timeIntervalSince1970)"
    }
    
    // MARK: - WebSocketDelegate
    
    func webSocketDidConnect(_ service: WebSocketService) {
        print("✅ [AIVoice] WebSocket connected")
        DispatchQueue.main.async { self.isConnected = true }
        let authMessage: [String: Any] = ["type": "auth", "token": authToken ?? ""]
        service.send(authMessage)
    }
    
    func webSocketDidDisconnect(_ service: WebSocketService) {
        print("❌ [AIVoice] WebSocket disconnected")
        DispatchQueue.main.async {
            self.isConnected = false
            self.isListening = false
        }
    }
    
    func webSocket(_ service: WebSocketService, didReceiveMessage message: [String: Any]) {
        guard let type = message["type"] as? String else { return }
        
        switch type {
        case "authenticated":
            if !isAuthenticated {
                sendStartSession()
                isAuthenticated = true
            }
            
        case "session_started":
            sessionStarted = true
            Task { await startListening() }
            
        case "stt_done":
            if let text = message["text"] as? String {
                print("📝✅ [AIVoice] You said: '\(text)'")
                DispatchQueue.main.async { self.currentResponse = "" }
            }
            
        case "ai_response_started":
            print("🤖 [AIVoice] AI response started")
            DispatchQueue.main.async { self.isAISpeaking = true }

        case "response.text.delta":
            if let textDelta = message["delta"] as? String {
                DispatchQueue.main.async { self.currentResponse += textDelta }
            }
            
        case "audio_chunk", "response.audio.delta":
            let audioKey = (type == "audio_chunk") ? "audio" : "delta"
            if let base64String = message[audioKey] as? String, let audioData = Data(base64Encoded: base64String) {
                self.scheduleBuffer(audioData)
            }

        case "response.done":
            print("✅ [AIVoice] GPT-4o response completed.")
            DispatchQueue.main.async { self.isAISpeaking = false }
            
        case "error":
            print("❌ [AIVoice] WebSocket error: \(message["message"] as? String ?? "unknown")")
            
        default:
            // Handles speech_started, speech_stopped, audio_received, etc.
            print("ℹ️ [AIVoice] Received info message: \(type)")
        }
    }

    func webSocket(_ service: WebSocketService, didEncounterError error: Error) {
        print("❌ [AIVoice] WebSocket error: \(error)")
        DispatchQueue.main.async {
            self.isConnected = false
            self.isListening = false
        }
    }
    
    // MARK: - Streaming Audio Playback
    
    private func scheduleBuffer(_ pcmData: Data) {
        let bytesPerFrame = Int(playerFormat.streamDescription.pointee.mBytesPerFrame)
        let frameCount = UInt32(pcmData.count) / UInt32(bytesPerFrame)
        
        guard frameCount > 0, let buffer = AVAudioPCMBuffer(pcmFormat: playerFormat, frameCapacity: frameCount) else {
            print("⚠️ [AIVoice] Failed to create or schedule empty audio buffer.")
            return
        }
        
        buffer.frameLength = frameCount
        pcmData.withUnsafeBytes { ptr in
            if let dest = buffer.int16ChannelData?[0] {
                ptr.copyBytes(to: dest, count: pcmData.count)
            }
        }
        
        playerNode.scheduleBuffer(buffer, at: nil, options: [], completionHandler: nil)
        
        if !playerNode.isPlaying {
            playerNode.play()
        }
    }
}

// 保持向后兼容的预览
struct UserVoiceInput: View {
    var body: some View {
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
