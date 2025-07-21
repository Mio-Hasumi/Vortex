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
                        aiVoiceService.stopAudioEngine()
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
class AIVoiceService: NSObject, ObservableObject, WebSocketDelegate, AVAudioPlayerDelegate {
    @Published var isConnected = false
    @Published var isListening = false
    @Published var isMuted = false
    @Published var currentResponse = ""
    @Published var isAISpeaking = false
    
    private var matchContext: MatchResult?
    private var conversationContext: String = ""
    private var webSocketService: WebSocketService?
    private var authToken: String?
    private var isAuthenticated = false
    private var sessionStarted = false
    
    // 音频相关
    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private var audioPlayer: AVAudioPlayer?
    private var isRecording = false
    private var silenceTimer: Timer?
    private var lastAudioTime: Date = Date()
    private var hasDetectedSpeech = false
    private var speechStartTime: Date?
    private var maxUtteranceDuration: TimeInterval = 8.0  // 最大8秒utterance
    private var maxUtteranceTimer: Timer?
    private var forceUtteranceTimer: Timer?  // 强制超时，防止永远不发utterance_end
    private var audioStartTime: Date?
    private var audioChunkIndex: Int = 0  // 追踪发送的音频块序号
    private var consecutiveSpeechFrames: Int = 0  // 连续检测到语音的帧数
    
    // AI音频播放缓冲区
    private var audioBuffer = Data()  // 累积AI音频块
    private var aiAudioPlayer: AVAudioPlayer?  // 专门播放AI音频
    private var consecutiveSilenceFrames: Int = 0  // 连续检测到静音的帧数
    private let minSpeechFrames: Int = 3  // 至少3帧连续检测到语音才算说话
    private let minSilenceFrames: Int = 5  // 至少5帧连续静音才算停止说话
    
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
            
            // 设置首选采样率为16kHz
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
        
        // 使用硬件的实际输入格式，避免格式不匹配
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
        
        // 设置对话上下文 - AI应该是聊天伙伴，不是匹配算法
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
        
        print("🧠 [AIVoice] AI conversation context set:")
        print("   📝 Transcription: \(matchResult.transcription)")
        print("   🏷️ Topics: \(matchResult.topics)")
        print("   #️⃣ Hashtags: \(matchResult.hashtags)")
        
        // 连接到 WebSocket
        print("🔌 [AIVoice] Connecting to GPT-4o Realtime API...")
        print("🎯 [AIVoice] Will send conversation context about: \(matchResult.topics)")
        
        await connectToRealtimeAPI()
        
        print("✅ [AIVoice] AI conversation initialized with topic context")
    }
    
    private func connectToRealtimeAPI() async {
        guard let token = authToken else {
            print("❌ [AIVoice] No auth token available")
            return
        }
        
        print("🔌 [AIVoice] Connecting to GPT-4o Audio Stream API...")
        print("🎯 [AIVoice] Will send conversation context about: \(matchContext?.topics ?? [])")
        
        await MainActor.run {
            // 创建 WebSocket 服务
            webSocketService = WebSocketService()
            webSocketService?.delegate = self
            
            // 连接到新的音频流端点
            webSocketService?.connect(to: APIConfig.WebSocket.aiAudioStream, with: token)
        }
    }
    
    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer, originalFormat: AVAudioFormat, targetFormat: AVAudioFormat) {
        guard sessionStarted && !isMuted && isRecording else { 
            // print("🔇 [AIVoice] Skipping audio - sessionStarted: \(sessionStarted), muted: \(isMuted), recording: \(isRecording)")
            return 
        }
        
        // 🔑 SERVER-SIDE VAD: No client-side speech detection needed!
        // OpenAI's server will handle voice activity detection automatically
        let audioLevel = calculateAudioLevel(buffer)
        
        // 只记录音频电平用于调试，不做语音检测
        if audioLevel > 0.001 {
            print("🎤 [AIVoice] Audio level: \(audioLevel) - SERVER VAD ENABLED")
        }
        
        print("🎤 [AIVoice] Processing audio buffer - frames: \(buffer.frameLength), level: \(audioLevel) - using server-side VAD")
        
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
        
        print("🎵 [AIVoice] Audio converted successfully: \(audioData.count) bytes (from \(buffer.frameLength) frames)")
        
        // 编码为base64并发送
        let base64Audio = audioData.base64EncodedString()
        
        // 记录首次音频时间（仅用于调试）
        if audioStartTime == nil {
            audioStartTime = Date()
            print("⏱️ [AIVoice] First audio chunk - server VAD will handle turn detection")
        }
        
        let audioMessage: [String: Any] = [
            "type": "audio_chunk",
            "audio_data": base64Audio,
            "language": "en-US",
            "timestamp": Date().timeIntervalSince1970
        ]
        
        audioChunkIndex += 1
        webSocketService?.send(audioMessage)
        print("📤 [AIVoice] Sent audio chunk #\(audioChunkIndex): \(audioData.count) bytes (\(base64Audio.count) base64 chars)")
    }
    
    private func calculateAudioLevel(_ buffer: AVAudioPCMBuffer) -> Float {
        guard let channelData = buffer.floatChannelData?[0] else { return 0.0 }
        
        var maxLevel: Float = 0.0
        var rmsSum: Float = 0.0
        let frameCount = Int(buffer.frameLength)
        
        // 计算RMS（均方根）和峰值电平
        for i in 0..<frameCount {
            let sample = abs(channelData[i])
            maxLevel = max(maxLevel, sample)
            rmsSum += sample * sample
        }
        
        let rmsLevel = sqrt(rmsSum / Float(frameCount))
        
        // 结合RMS和峰值，给予RMS更大权重
        return (rmsLevel * 0.7 + maxLevel * 0.3)
    }
    
    private func triggerUtteranceEnd() {
        print("🔚 [AIVoice] triggerUtteranceEnd called - hasDetectedSpeech: \(hasDetectedSpeech)")
        guard hasDetectedSpeech else { 
            print("🔚 [AIVoice] No speech detected, skipping utterance end")
            return 
        }
        
        print("🔚 [AIVoice] ✅ Triggering utterance end...")
        
        let utteranceEndMessage: [String: Any] = [
            "type": "utterance_end",
            "timestamp": Date().timeIntervalSince1970
        ]
        
        if webSocketService != nil {
            webSocketService?.send(utteranceEndMessage)
            print("🔚 [AIVoice] ✅ Utterance end message sent to backend")
            print("🔚 [AIVoice] Utterance end sent:", utteranceEndMessage)
            print("🔚 [AIVoice] Current state - isRecording: \(isRecording), sessionStarted: \(sessionStarted)")
        } else {
            print("🔚 [AIVoice] ❌ WebSocket service is nil!")
        }
        
        // 重置状态和计时器
        resetAudioState()
    }
    
    private func forceUtteranceEnd() {
        print("🚨 [AIVoice] Force utterance end triggered - safety mechanism")
        
        let utteranceEndMessage: [String: Any] = [
            "type": "utterance_end",
            "timestamp": Date().timeIntervalSince1970,
            "reason": "force_timeout"
        ]
        
        if webSocketService != nil {
            webSocketService?.send(utteranceEndMessage)
            print("🚨 [AIVoice] ✅ Force utterance end message sent to backend")
            print("🚨 [AIVoice] Force utterance end sent:", utteranceEndMessage)
            print("🚨 [AIVoice] Current state - isRecording: \(isRecording), sessionStarted: \(sessionStarted)")
        }
        
        // 重置所有状态和计时器
        resetAudioState()
    }
    
    private func resetAudioState() {
        hasDetectedSpeech = false
        speechStartTime = nil
        audioStartTime = nil
        audioChunkIndex = 0
        consecutiveSpeechFrames = 0
        consecutiveSilenceFrames = 0
        
        // 清理所有计时器
        silenceTimer?.invalidate()
        silenceTimer = nil
        maxUtteranceTimer?.invalidate()
        maxUtteranceTimer = nil
        forceUtteranceTimer?.invalidate()
        forceUtteranceTimer = nil
        
        print("🔄 [AIVoice] All audio state and timers reset (chunk index reset to 0)")
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
            print("⚠️ [AIVoice] sessionStarted: \(sessionStarted), isMuted: \(isMuted)")
            return
        }
        
        print("🎤 [AIVoice] Starting continuous voice listening with audio engine")
        print("🎤 [AIVoice] Current state - sessionStarted: \(sessionStarted), isMuted: \(isMuted)")
        
        await MainActor.run {
            isListening = true
        }
        
        startAudioEngine()
    }
    
    func toggleMute() {
        isMuted.toggle()
        print("🔇 [AIVoice] Audio input \(isMuted ? "muted" : "unmuted")")
        print("🔇 [AIVoice] New state - isMuted: \(isMuted), isRecording: \(isRecording)")
        
        if isMuted {
            stopAudioEngine()
        } else if sessionStarted {
            startAudioEngine()
        }
    }
    
    private func startAudioEngine() {
        guard !isMuted, let audioEngine = audioEngine else { 
            print("⚠️ [AIVoice] Cannot start audio engine - muted: \(isMuted), engine exists: \(audioEngine != nil)")
            return 
        }
        
        do {
            // 确保引擎已准备好
            if !audioEngine.isRunning {
                print("🎵 [AIVoice] Preparing and starting audio engine...")
                audioEngine.prepare()
                try audioEngine.start()
                isRecording = true
                print("🎙️ [AIVoice] ✅ Audio engine started for streaming - isRecording: \(isRecording)")
            } else {
                print("🎙️ [AIVoice] Audio engine already running")
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
            
            // 清理语音检测状态
            resetAudioState()
            
            Task { @MainActor in
                isListening = false
            }
            
            print("⏹️ [AIVoice] Audio engine stopped, state cleared")
        }
    }
    
    deinit {
        // 清理音频引擎
        stopAudioEngine()
        inputNode?.removeTap(onBus: 0)
        silenceTimer?.invalidate()
        print("🧹 [AIVoice] Audio service cleaned up")
    }
    
    // 生成基于话题的 AI 响应（当前是模拟，真实实现会来自 GPT-4o）
    func generateTopicBasedResponse() -> String {
        guard let context = matchContext else {
            return "Let's continue our conversation!"
        }
        
        let topic = context.topics.first ?? "this topic"
        let responses = [
            "That's fascinating! What specifically interests you about \(topic)?",
            "I'd love to hear more about your experience with \(topic).",
            "What got you started with \(topic)? Any interesting stories?",
            "Have you seen any recent developments in \(topic) that caught your attention?",
            "What aspects of \(topic) do you think others should know about?"
        ]
        
        return responses.randomElement() ?? "Tell me more about \(topic)!"
    }
    
    // MARK: - Helper 方法
    
    private func generateSessionId() -> String {
        return "ai_waiting_\(UUID().uuidString)_\(Date().timeIntervalSince1970)"
    }
    
    // MARK: - WebSocketDelegate
    
    func webSocketDidConnect(_ service: WebSocketService) {
        print("✅ [AIVoice] WebSocket connected to GPT-4o Realtime")
        
        DispatchQueue.main.async {
            self.isConnected = true
        }
        
        // 发送认证消息
        let authMessage: [String: Any] = [
            "type": "auth",
            "token": authToken ?? ""
        ]
        
        service.send(authMessage)
        print("📤 [AIVoice] Sent authentication")
    }
    
    func webSocketDidDisconnect(_ service: WebSocketService) {
        print("❌ [AIVoice] WebSocket disconnected")
        
        DispatchQueue.main.async {
            self.isConnected = false
            self.isListening = false
        }
    }
    
    func webSocket(_ service: WebSocketService, didReceiveMessage message: [String: Any]) {
        print("📥 [AIVoice] Received message: \(message["type"] as? String ?? "unknown")")
        
        guard let type = message["type"] as? String else { return }
        
        switch type {
        case "authenticated":
            print("✅ [AIVoice] Authenticated with backend")
            // 只在第一次认证时开始会话
            if !isAuthenticated {
                sendStartSession()
                isAuthenticated = true
            }
            
        case "session_started":
            print("✅ [AIVoice] Session started")
            print("🎯 [AIVoice] Session message data: \(message)")
            sessionStarted = true
            print("✅ [AIVoice] sessionStarted flag set →", sessionStarted)
            
            // 会话开始后自动开始监听
            print("🚀 [AIVoice] About to start listening...")
            print("🚀 [AIVoice] Current state before startListening - sessionStarted: \(sessionStarted), isMuted: \(isMuted)")
            Task {
                await startListening()
            }
            
        case "stt_chunk":
            // 简化：不显示部分转写，避免UI闪烁
            if let text = message["text"] as? String {
                print("🎤📝 [AIVoice] Partial: '\(text)'")
            }
            
        case "stt_done":
            print("✅ [AIVoice] Complete transcription received")
            if let text = message["text"] as? String {
                print("📝✅ [AIVoice] You said: '\(text)'")
                // 清空显示，准备接收AI回复
                DispatchQueue.main.async {
                    self.currentResponse = ""
                }
            }
            
        case "speech_started":
            print("🎤 [AIVoice] User speech started")
            
        case "speech_stopped":
            print("🔇 [AIVoice] User speech stopped")
            
        case "ai_response_started":
            print("🤖 [AIVoice] AI response started")
            // 清空音频缓冲区，准备接收新的AI回复
            audioBuffer = Data()
            DispatchQueue.main.async {
                self.isAISpeaking = true
            }
            
        case "audio_chunk":
            print("🔊 [AIVoice] Received real-time audio chunk")
            if let audioData = message["audio"] as? String {
                print("🔊🎵 [AIVoice] Real-time audio chunk: \(audioData.count) base64 chars")
                // 累积音频块，避免播放被打断
                accumulateAudioChunk(audioData)
            }
            
        case "utterance_end":
            print("✅ [AIVoice] Utterance ended")
            // 当语音活动结束时，重置语音检测状态
            resetAudioState()
            lastAudioTime = Date()
            print("🔊 [AIVoice] Audio state reset, lastAudioTime updated")
            
        // GPT-4o Realtime API 标准事件
        case "response.audio.delta":
            print("🔊 [AIVoice] Received GPT-4o audio delta")
            if let audioData = message["delta"] as? String {
                print("🔊🎵 [AIVoice] GPT-4o audio delta: \(audioData.count) base64 chars")
                playAudioResponse(audioData)
            }
            
        case "response.text.delta":
            print("📝 [AIVoice] Received GPT-4o text delta")
            if let textDelta = message["delta"] as? String {
                print("📝🤖 [AIVoice] GPT-4o text: '\(textDelta)'")
                DispatchQueue.main.async {
                    self.currentResponse += textDelta  // 简单累加文字显示
                }
            }
            
        case "response.done":
            print("✅ [AIVoice] GPT-4o response completed")
            // AI回复完成，播放累积的音频
            playAccumulatedAudio()
            DispatchQueue.main.async {
                self.isAISpeaking = false
            }
            
        case "audio_received":
            print("📥 [AIVoice] Backend acknowledgment - audio received")
            if let chunksAccumulated = message["chunks_accumulated"] as? Int {
                print("🎵 [AIVoice] Audio chunks accumulated: \(chunksAccumulated)")
            }
            
        case "error":
            print("❌ [AIVoice] WebSocket error: \(message["message"] as? String ?? "unknown")")
            print("❌ [AIVoice] Full error message: \(message)")
            
        default:
            print("❓ [AIVoice] Unknown message type: \(type)")
            print("❓ [AIVoice] Full unknown message: \(message)")
        }
    }
    
    // MARK: - Audio Accumulation and Playback
    
    private func accumulateAudioChunk(_ audioData: String) {
        guard let audioBytes = Data(base64Encoded: audioData) else {
            print("❌ [AIVoice] Failed to decode audio chunk")
            return
        }
        
        audioBuffer.append(audioBytes)
        print("🎵 [AIVoice] Audio chunk accumulated: \(audioBytes.count) bytes, total: \(audioBuffer.count) bytes")
    }
    
    private func playAccumulatedAudio() {
        guard !audioBuffer.isEmpty else {
            print("🔇 [AIVoice] No audio to play")
            return
        }
        
        print("🔊 [AIVoice] Playing accumulated audio: \(audioBuffer.count) bytes")
        
        do {
            // 停止之前的AI音频播放
            aiAudioPlayer?.stop()
            
            // 播放累积的完整音频
            aiAudioPlayer = try AVAudioPlayer(data: audioBuffer)
            aiAudioPlayer?.delegate = self
            aiAudioPlayer?.play()
            
            print("✅ [AIVoice] Started playing complete AI response")
            
        } catch {
            print("❌ [AIVoice] Failed to play accumulated audio: \(error)")
        }
    }
    
    private func playAudioResponse(_ audioData: String) {
        // 解码并播放AI的音频回应
        guard let data = Data(base64Encoded: audioData) else {
            print("❌ [AIVoice] Failed to decode audio data")
            return
        }
        
        do {
            audioPlayer = try AVAudioPlayer(data: data)
            audioPlayer?.delegate = self
            audioPlayer?.play()
            
            DispatchQueue.main.async {
                self.isAISpeaking = true
            }
            
            print("🔊 [AIVoice] Playing AI audio response")
        } catch {
            print("❌ [AIVoice] Failed to play audio: \(error)")
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
        DispatchQueue.main.async {
            self.isAISpeaking = false
        }
        print("🔊 [AIVoice] AI finished speaking")
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
