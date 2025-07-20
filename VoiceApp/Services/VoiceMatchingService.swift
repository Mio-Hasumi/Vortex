import Foundation
import AVFoundation

// 匹配结果数据结构
struct MatchResult {
    let transcription: String
    let topics: [String]
    let hashtags: [String]
    let matchId: String
    let sessionId: String
    let confidence: Double
    let waitTime: Int
}

class VoiceMatchingService: ObservableObject {
    static let shared = VoiceMatchingService()
    
    @Published var isRecording = false
    @Published var isMatching = false
    @Published var matchStatus: String?
    @Published var matchedTopics: [String] = []
    @Published var estimatedWaitTime: Int = 0
    @Published var shouldNavigateToWaitingRoom = false  // 新增：控制导航
    @Published var lastMatchResult: MatchResult?        // 新增：存储匹配结果
    
    private var audioRecorder: AVAudioRecorder?
    private var recordingURL: URL?
    
    private init() {}
    
    func startRecording() async throws {
        print("🎙️ [VoiceService] Starting recording request...")
        
        // 请求麦克风权限
        let audioSession = AVAudioSession.sharedInstance()
        
        // requestRecordPermission 不是 async，需要手动桥接
        let granted = await withCheckedContinuation { continuation in
            audioSession.requestRecordPermission { allowed in
                continuation.resume(returning: allowed)
            }
        }
        guard granted else {
            print("❌ [VoiceService] Microphone permission denied")
            throw VoiceMatchingError.permissionDenied
        }
        
        print("✅ [VoiceService] Microphone permission granted")
        
        // 配置录音会话
        try audioSession.setCategory(.playAndRecord, mode: .default)
        try audioSession.setActive(true)
        
        // 创建临时文件URL
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        recordingURL = documentsPath.appendingPathComponent("voice_input.wav")
        
        print("📁 [VoiceService] Recording file path: \(recordingURL?.absoluteString ?? "nil")")
        
        // 录音设置
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 44100.0,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        // 创建录音器
        audioRecorder = try AVAudioRecorder(url: recordingURL!, settings: settings)
        let success = audioRecorder?.record() ?? false
        
        print("🎤 [VoiceService] Audio recorder started: \(success)")
        
        await MainActor.run {
            isRecording = true
            print("🔴 [VoiceService] UI state updated - isRecording: true")
        }
    }
    
    func stopRecording() async throws {
        print("⏹️ [VoiceService] Stopping recording...")
        
        audioRecorder?.stop()
        await MainActor.run {
            isRecording = false
            print("⚫ [VoiceService] UI state updated - isRecording: false")
        }
        
        guard let recordingURL = recordingURL else {
            print("❌ [VoiceService] No recording URL found")
            throw VoiceMatchingError.noRecording
        }
        
        // 检查文件是否存在
        let fileExists = FileManager.default.fileExists(atPath: recordingURL.path)
        print("📄 [VoiceService] Recording file exists: \(fileExists)")
        
        if fileExists {
            // 获取文件大小
            do {
                let attributes = try FileManager.default.attributesOfItem(atPath: recordingURL.path)
                let fileSize = attributes[.size] as? Int64 ?? 0
                print("📊 [VoiceService] Recording file size: \(fileSize) bytes")
            } catch {
                print("⚠️ [VoiceService] Could not get file attributes: \(error)")
            }
        }
        
        // 获取录音数据
        let audioData = try Data(contentsOf: recordingURL)
        print("🔊 [VoiceService] Audio data loaded: \(audioData.count) bytes")
        
        // 开始匹配过程
        print("🔍 [VoiceService] Starting matching process...")
        await startMatching(audioData: audioData)
    }
    
    private func startMatching(audioData: Data) async {
        print("🔍 [VoiceService] Entering startMatching with \(audioData.count) bytes")
        
        await MainActor.run {
            isMatching = true
            matchStatus = "Analyzing your voice..."
            print("🔵 [VoiceService] UI state updated - isMatching: true")
        }
        
        do {
            print("📤 [VoiceService] Uploading audio to backend...")
            
            // 上传音频文件并获取语音识别结果
            let uploadedData = try await APIService.shared.upload(
                endpoint: APIConfig.Endpoints.aiUploadAudio,
                audioData: audioData
            )
            
            print("✅ [VoiceService] Audio upload successful, response size: \(uploadedData.count) bytes")
            
            // 解析上传响应，获取主题和标签
            struct UploadResponse: Codable {
                let transcription: String
                let language: String
                let duration: Double
                let confidence: Double
                let words: [WordInfo]?
                let extracted_topics: [String]?
                let generated_hashtags: [String]?
            }
            
            struct WordInfo: Codable {
                let word: String
                let start: Double
                let end: Double
            }
            
            let uploadResponse = try JSONDecoder().decode(UploadResponse.self, from: uploadedData)
            
            print("🎯 [VoiceService] Voice processing results:")
            print("   📝 Transcription: \(uploadResponse.transcription)")
            print("   🏷️ Topics: \(uploadResponse.extracted_topics ?? [])")
            print("   #️⃣ Hashtags: \(uploadResponse.generated_hashtags ?? [])")
            
            // 使用从语音识别获得的主题和标签进行匹配
            let extractedTopics = uploadResponse.extracted_topics ?? ["General topic"]
            let generatedHashtags = uploadResponse.generated_hashtags ?? ["#general", "#chat"]
            
            // 创建匹配请求，将语音处理结果作为字符串传递
            let voiceResult = [
                "transcription": uploadResponse.transcription,
                "extracted_topics": extractedTopics,
                "generated_hashtags": generatedHashtags
            ] as [String : Any]
            
            let voiceResultJSON = try JSONSerialization.data(withJSONObject: voiceResult)
            let voiceResultString = String(data: voiceResultJSON, encoding: .utf8) ?? ""
            
            let matchRequest = AIMatchRequest(
                user_voice_input: voiceResultString,  // 传递完整的语音处理结果
                audio_file_url: nil,   // 已经上传了文件
                max_participants: 2,    // 默认1对1匹配
                language_preference: "en-US"
            )
            
            print("🤖 [VoiceService] Sending AI match request with extracted topics...")
            
            let requestData = try JSONEncoder().encode(matchRequest)
            let matchResponse: AIMatchResponse = try await APIService.shared.request(
                endpoint: APIConfig.Endpoints.aiMatch,
                method: "POST",
                body: requestData
            )
            
            print("🎯 [VoiceService] Match response received:")
            print("   - Topics: \(matchResponse.extracted_topics)")
            print("   - Hashtags: \(matchResponse.generated_hashtags)")
            print("   - Confidence: \(matchResponse.match_confidence)")
            print("   - Wait time: \(matchResponse.estimated_wait_time)")
            
            await MainActor.run {
                // 使用从语音识别获得的主题，而不是匹配响应中的主题
                matchedTopics = extractedTopics
                estimatedWaitTime = matchResponse.estimated_wait_time
                matchStatus = "Found the following topics:\n" + extractedTopics.joined(separator: "\n")
                isMatching = false
                print("✅ [VoiceService] Match completed - isMatching: false")
                print("🏷️ [VoiceService] Topics found: \(matchedTopics)")
                
                // 创建匹配结果
                lastMatchResult = MatchResult(
                    transcription: uploadResponse.transcription,
                    topics: extractedTopics,
                    hashtags: generatedHashtags,
                    matchId: matchResponse.match_id,
                    sessionId: matchResponse.session_id,
                    confidence: matchResponse.match_confidence,
                    waitTime: matchResponse.estimated_wait_time
                )
                
                // 触发导航到等待房间
                shouldNavigateToWaitingRoom = true
                print("🚪 [VoiceService] Navigating to waiting room.")
            }
            
        } catch {
            print("❌ [VoiceService] Matching failed with error: \(error)")
            print("   Error type: \(type(of: error))")
            print("   Error description: \(error.localizedDescription)")
            
            await MainActor.run {
                matchStatus = "Matching failed: \(error.localizedDescription)"
                isMatching = false
                print("🔴 [VoiceService] UI state updated after error - isMatching: false")
            }
        }
    }
    
    func cancelMatching() {
        Task {
            do {
                let _: EmptyResponse = try await APIService.shared.request(
                    endpoint: APIConfig.Endpoints.cancelMatch,
                    method: "POST"
                )
                
                await MainActor.run {
                    isMatching = false
                    matchStatus = nil
                }
            } catch {
                print("Cancel matching failed: \(error)")
            }
        }
    }
    
    // 重置导航状态（从等候室返回时调用）
    func resetNavigation() {
        shouldNavigateToWaitingRoom = false
        lastMatchResult = nil
        matchStatus = nil
        matchedTopics = []
        estimatedWaitTime = 0
        print("🔄 [VoiceService] Navigation state reset")
    }
}

enum VoiceMatchingError: Error, LocalizedError {
    case noRecording
    case uploadFailed
    case matchingFailed
    case permissionDenied
    
    var errorDescription: String? {
        switch self {
        case .noRecording:
            return "No recording found"
        case .uploadFailed:
            return "Failed to upload audio"
        case .matchingFailed:
            return "Failed to find matches"
        case .permissionDenied:
            return "Microphone permission denied"
        }
    }
}

struct EmptyResponse: Codable {} 
 