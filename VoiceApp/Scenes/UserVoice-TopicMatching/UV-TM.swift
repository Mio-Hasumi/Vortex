//
//  UV-TM.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/18/25.
//
import SwiftUI
import Combine
import AVFoundation

private enum CaptureState { case idle, listening, result }

// 等候室视图 - 与 AI 进行语音对话，同时在后台匹配用户
struct UserVoiceTopicMatchingView: View {
    let matchResult: MatchResult
    @Environment(\.dismiss) private var dismiss
    
    @State private var captureState: CaptureState = .idle
    @State private var levels: [CGFloat] = Array(repeating: 0.1, count: 3)
    @State private var currentText: String = ""
    @State private var isConnectedToAI = false
    @StateObject private var aiVoiceService = AIVoiceService()

    // demo timer – swap with AVAudioEngine later
    private let timer = Timer.publish(every: 0.12, on: .main, in: .common).autoconnect()

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            sidebar
            topRightCluster
            bubblesIfListening
            pullHandle
            micIdleButton
            bottomResultButtons
        }
        .onReceive(timer) { _ in
            if captureState == .listening {
                levels = levels.map { _ in .random(in: 0.05...1) }
            }
        }
        .onAppear {
            setupWaitingRoom()
        }
        .onReceive(aiVoiceService.$currentResponse) { response in
            if !response.isEmpty {
                print("🎨 [WaitingRoom] Received AI response, updating UI: \(String(response.prefix(50)))...")
                captureState = .result
                currentText = response
                
                // 较长时间显示响应后回到 idle 状态
                DispatchQueue.main.asyncAfter(deadline: .now() + 8) {
                    captureState = .idle
                    currentText = "What else would you like to discuss about \(matchResult.topics.first ?? "this topic")? Keep talking while I find others to join!"
                }
            }
        }
        .onReceive(aiVoiceService.$isListening) { isListening in
            if isListening && captureState == .idle {
                captureState = .listening
                currentText = "🎤 Now listening continuously..."
            }
        }
        .onReceive(aiVoiceService.$isAISpeaking) { isSpeaking in
            if isSpeaking {
                captureState = .result
                currentText = "🔊 AI is speaking..."
            }
        }
        .onReceive(aiVoiceService.$isMuted) { isMuted in
            if captureState == .listening {
                currentText = isMuted ? "🔇 Muted - Tap mic to unmute" : "🎤 Listening continuously..."
            }
        }
        .onReceive(aiVoiceService.$isConnected) { connected in
            if connected {
                print("🔗 [WaitingRoom] Connected to AI service")
            }
        }
        .navigationBarHidden(true)
    }

    
    private var sidebar: some View {
        VStack {
            // 返回按钮
            Button(action: {
                print("🔙 [WaitingRoom] User tapped back button")
                VoiceMatchingService.shared.resetNavigation()
                dismiss()
            }) {
                Image(systemName: "arrow.left")
                    .font(.title2)
                    .foregroundColor(.white)
                    .frame(width: 40, height: 40)
                    .background(Color.black.opacity(0.3))
                    .clipShape(Circle())
            }
            .padding(.bottom, 20)
            
            // 原来的 sidebar 图标
        Image("sidebar")
            .resizable()
            .aspectRatio(contentMode: .fit)
            .frame(width: 50, height: 204)
            .shadow(color: .white, radius: 12)
        }
            .padding(.top, -120)
            .padding(.leading, 4)
            .frame(maxWidth: .infinity,
                   maxHeight: .infinity,
                   alignment: .topLeading)
    }

    
    private var topRightCluster: some View {
        VStack(alignment: .trailing, spacing: 24) {
            Image("orb")
                .resizable().aspectRatio(contentMode: .fit)
                .frame(width: 170, height: 170)
                .overlay(
                    LinearGradient(
                        gradient: Gradient(stops: [
                            .init(color: .clear,                   location: 0),
                            .init(color: Color.black.opacity(0.4), location: 0.3),
                            .init(color: Color.black.opacity(0.7), location: 1)
                        ]),
                        startPoint: .top, endPoint: .bottom)
                )
                .overlay(
                    RadialGradient(
                        gradient: Gradient(colors: [.clear, Color.black.opacity(0.5)]),
                        center: .center, startRadius: 0, endRadius: 85)
                )

            if captureState == .idle {
                Text(currentText)
                    .font(.custom("Rajdhani", size: 28))  // 稍微减小字体
                    .foregroundColor(.white)
                    .multilineTextAlignment(.leading)
                    .lineLimit(nil)  // 允许无限行
                    .frame(maxWidth: 320, alignment: .leading)  // 增加最大宽度
                    .padding(.horizontal, 20)  // 添加水平边距
                    .offset(x: -40)
            } else if captureState == .listening {
                Text(aiVoiceService.isMuted ? "🔇 Muted - Tap mic to unmute" : "🎤 Listening continuously...")
                    .font(.custom("Rajdhani", size: 32))
                    .foregroundColor(aiVoiceService.isMuted ? .red : .green)
                    .multilineTextAlignment(.leading)
                    .frame(maxWidth: 300, alignment: .leading)
                    .offset(x: -40)
            } else if captureState == .result {
                if aiVoiceService.isAISpeaking {
                    Text("🔊 AI is speaking...")
                        .font(.custom("Rajdhani", size: 32))
                        .foregroundColor(.blue)
                        .multilineTextAlignment(.leading)
                        .frame(maxWidth: 300, alignment: .leading)
                        .offset(x: -40)
                } else {
                    ScrollView {
                        Text(currentText)
                            .font(.custom("Rajdhani", size: 26))  // 稍微减小字体以适应更多内容
                .foregroundColor(.white)
                .multilineTextAlignment(.leading)
                            .lineLimit(nil)
                .frame(maxWidth: 320, alignment: .leading)
                            .padding(.horizontal, 20)
                    }
                    .frame(maxHeight: 200)  // 限制滚动区域高度
                .offset(x: -40)
                }
            }
        }
        .padding(.top, 8)
        .padding(.trailing, 8)
        .frame(maxWidth: .infinity,
               maxHeight: .infinity,
               alignment: .topTrailing)
    }

    
    private var bubblesIfListening: some View {
        VStack {
            Spacer()
            if captureState == .listening {
                HStack(spacing: 24) {
                    ForEach(levels.indices, id: \.self) { idx in
                        VoicePinchedCircle(level: levels[idx])
                            .animation(.easeInOut(duration: 0.1), value: levels[idx])
                    }
                }
                .frame(height: 100)
                .padding(.bottom, 135)
            }
        }
    }

    
    private var pullHandle: some View {
        Image("pullhandle")
            .resizable()
            .aspectRatio(contentMode: .fit)
            .frame(width: 120, height: 50)
            .shadow(color: Color.white.opacity(0.25), radius: 2)
            .offset(y: 38)
            .frame(maxWidth: .infinity,
                   maxHeight: .infinity,
                   alignment: .bottom)
    }

   
    private var micIdleButton: some View {
        Group {
            if captureState == .idle || captureState == .listening {
                Button(action: {
                    if aiVoiceService.isConnected {
                        aiVoiceService.toggleMute()
                    }
                }) {
                    Image(systemName: aiVoiceService.isMuted ? "mic.slash" : "mic")
                    .resizable()
                    .frame(width: 64, height: 64)
                        .foregroundColor(aiVoiceService.isMuted ? .red : .white)
                    .shadow(radius: 4)
                }
                    .frame(maxWidth: .infinity,
                           maxHeight: .infinity,
                           alignment: .bottom)
                    .padding(.bottom, 120)
            }
        }
    }

    
    private var bottomResultButtons: some View {
        Group {
            if captureState == .result && !aiVoiceService.isAISpeaking {
                HStack(spacing: 24) {
                    Button(action: {
                        aiVoiceService.toggleMute()
                    }) {
                        Image(systemName: aiVoiceService.isMuted ? "mic.slash" : "mic")
                        .resizable()
                        .frame(width: 36, height: 36)
                            .foregroundColor(aiVoiceService.isMuted ? .red : .white)
                        .shadow(radius: 2)
                    }
                       
                    Button("Back to Chat") {
                        captureState = .listening
                        currentText = aiVoiceService.isMuted ? "🔇 Muted - Tap mic to unmute" : "🎤 Listening continuously..."
                    }
                    .font(.headline)
                    .foregroundColor(.white)
                    .padding(.vertical, 14)
                    .padding(.horizontal, 28)
                    .background(.ultraThinMaterial)
                    .clipShape(Capsule())
                    .shadow(radius: 4)
                }
                .padding(.bottom, 85)
                .frame(maxWidth: .infinity,
                       maxHeight: .infinity,
                       alignment: .bottom)
            }
        }
    }

    // MARK: - AI 语音对话逻辑
    
    private func setupWaitingRoom() {
        print("🏠 [WaitingRoom] Setting up waiting room for topics: \(matchResult.topics)")
        
        // 初始化 AI 对话
        Task {
            await aiVoiceService.initializeAIConversation(with: matchResult)
        }
        
        // 设置初始文本
        let topicList = matchResult.topics.joined(separator: "\n• ")
        currentText = "🎯 Great! I found these topics:\n\n• \(topicList)\n\n🤖 I'm your AI conversation partner!\n\n🎙️ I'm listening - just start talking!"
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
        
        // 创建目标格式 (16kHz, Int16, mono)
        guard let targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, 
                                             sampleRate: 16000, 
                                             channels: 1, 
                                             interleaved: false) else {
            print("❌ [AIVoice] Failed to create target audio format")
            return
        }
        
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
        
        // 检测音频活动 (简单的能量检测)
        let audioLevel = calculateAudioLevel(buffer)
        let speechThreshold: Float = 0.01  // 可调整的阈值
        let isSpeechDetected = audioLevel > speechThreshold
        
        if isSpeechDetected {
            hasDetectedSpeech = true
            lastAudioTime = Date()
            // 取消静音计时器
            silenceTimer?.invalidate()
            silenceTimer = nil
        } else if hasDetectedSpeech {
            // 如果之前检测到语音，现在是静音，开始计时
            if silenceTimer == nil {
                print("🔇 [AIVoice] Silence detected, starting timer...")
                silenceTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: false) { _ in
                    self.triggerUtteranceEnd()
                }
            }
        }
        
        print("🎤 [AIVoice] Processing audio buffer - frames: \(buffer.frameLength), level: \(audioLevel), speech: \(isSpeechDetected)")
        
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
        
        let audioMessage: [String: Any] = [
            "type": "audio_chunk",
            "audio_data": base64Audio,
            "language": "en-US",
            "timestamp": Date().timeIntervalSince1970
        ]
        
        webSocketService?.send(audioMessage)
        print("📤 [AIVoice] Sent audio chunk: \(audioData.count) bytes (\(base64Audio.count) base64 chars)")
    }
    
    private func calculateAudioLevel(_ buffer: AVAudioPCMBuffer) -> Float {
        guard let channelData = buffer.floatChannelData?[0] else { return 0.0 }
        
        var sum: Float = 0.0
        let frameCount = Int(buffer.frameLength)
        
        for i in 0..<frameCount {
            sum += abs(channelData[i])
        }
        
        return frameCount > 0 ? sum / Float(frameCount) : 0.0
    }
    
    private func triggerUtteranceEnd() {
        guard hasDetectedSpeech else { return }
        
        print("🔚 [AIVoice] Triggering utterance end...")
        
        let utteranceEndMessage: [String: Any] = [
            "type": "utterance_end",
            "timestamp": Date().timeIntervalSince1970
        ]
        
        webSocketService?.send(utteranceEndMessage)
        
        // 重置状态
        hasDetectedSpeech = false
        silenceTimer?.invalidate()
        silenceTimer = nil
        
        print("🔚 [AIVoice] Utterance end sent, state reset")
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
            silenceTimer?.invalidate()
            silenceTimer = nil
            hasDetectedSpeech = false
            
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
            
            // 会话开始后自动开始监听
            print("🚀 [AIVoice] About to start listening...")
            Task {
                await startListening()
            }
            
        case "stt_chunk":
            print("📝 [AIVoice] Received STT chunk")
            if let text = message["text"] as? String {
                print("🎤📝 [AIVoice] Partial transcription: '\(text)'")
                print("🎤📝 [AIVoice] Confidence: \(message["confidence"] ?? "unknown")")
                // Could update UI with partial transcription
                DispatchQueue.main.async {
                    self.currentResponse = "🎤 Hearing: \(text)"
                }
            }
            
        case "stt_done":
            print("✅ [AIVoice] Complete transcription received")
            if let text = message["text"] as? String {
                print("📝✅ [AIVoice] COMPLETE UTTERANCE: '\(text)'")
                print("📝✅ [AIVoice] Full message data: \(message)")
                // UI could show the complete transcription
                DispatchQueue.main.async {
                    self.currentResponse = "✅ You said: \(text)"
                }
            }
            
        case "ai_response":
            print("🤖 [AIVoice] Received AI response")
            if let responseText = message["text"] as? String {
                print("💬🤖 [AIVoice] AI FULL RESPONSE: '\(responseText)'")
                print("💬🤖 [AIVoice] Response length: \(responseText.count) characters")
                print("💬🤖 [AIVoice] Full AI message data: \(message)")
                
                DispatchQueue.main.async {
                    self.currentResponse = responseText
                    self.isListening = false
                }
            }
            
        case "audio_response":
            print("🔊 [AIVoice] Received AI audio response")
            if let audioData = message["audio"] as? String {
                print("🔊🎵 [AIVoice] Audio data length: \(audioData.count) base64 chars")
                print("🔊🎵 [AIVoice] Audio format: \(message["format"] ?? "unknown")")
                playAudioResponse(audioData)
            }
            
        case "audio_chunk":
            print("🎵 [AIVoice] Received real-time audio chunk")
            if let audioDelta = message["audio_delta"] as? String {
                print("🔊🎵 [AIVoice] Audio chunk length: \(audioDelta.count) base64 chars")
                print("🔊🎵 [AIVoice] Audio format: \(message["format"] ?? "pcm16")")
                // For now, we'll accumulate chunks and play the complete response
                // Real-time streaming would require more complex audio handling
            }
            
        case "utterance_end":
            print("✅ [AIVoice] Utterance ended")
            // 当语音活动结束时，重置语音检测状态
            hasDetectedSpeech = false
            lastAudioTime = Date()
            print("🔊 [AIVoice] New state - hasDetectedSpeech: \(hasDetectedSpeech), lastAudioTime: \(lastAudioTime)")
            
        case "error":
            print("❌ [AIVoice] WebSocket error: \(message["message"] as? String ?? "unknown")")
            print("❌ [AIVoice] Full error message: \(message)")
            
        default:
            print("❓ [AIVoice] Unknown message type: \(type)")
            print("❓ [AIVoice] Full unknown message: \(message)")
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
