import Foundation
import AVFoundation

// Matching result data structure
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
    @Published var shouldNavigateToWaitingRoom = false  // Added: Control navigation
    @Published var lastMatchResult: MatchResult?        // Added: Store match result
    @Published var waitingRoomInfo: WaitingRoomResponse?
    
    private var audioRecorder: AVAudioRecorder?
    private var recordingURL: URL?
    
    private init() {}
    
    func startRecording() async throws {
        print("🎙️ [VoiceService] Starting recording request...")
        
        // Request microphone permission
        let audioSession = AVAudioSession.sharedInstance()
        
        // requestRecordPermission is not async, manual bridging is needed
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
        
        // Configure recording session
        try audioSession.setCategory(.playAndRecord, mode: .default)
        try audioSession.setActive(true)
        
        // Create temporary file URL
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        recordingURL = documentsPath.appendingPathComponent("voice_input.wav")
        
        print("📁 [VoiceService] Recording file path: \(recordingURL?.absoluteString ?? "nil")")
        
        // Recording settings
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 44100.0,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        // Create recorder
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
        
        // Check if file exists
        let fileExists = FileManager.default.fileExists(atPath: recordingURL.path)
        print("📄 [VoiceService] Recording file exists: \(fileExists)")
        
        if fileExists {
            // Get file size
            do {
                let attributes = try FileManager.default.attributesOfItem(atPath: recordingURL.path)
                let fileSize = attributes[.size] as? Int64 ?? 0
                print("📊 [VoiceService] Recording file size: \(fileSize) bytes")
            } catch {
                print("⚠️ [VoiceService] Could not get file attributes: \(error)")
            }
        }
        
        // Get audio data
        let audioData = try Data(contentsOf: recordingURL)
        print("🔊 [VoiceService] Audio data loaded: \(audioData.count) bytes")
        
        // Start matching process
        print("🔍 [VoiceService] Starting matching process...")
        await startMatching(audioData: audioData)
    }
    
    private func startMatching(audioData: Data) async {
        await MainActor.run {
            isMatching = true
            matchStatus = "Finding a conversation partner..."
        }

        do {
            let _: WaitingRoomResponse = try await APIService.shared.request(
                endpoint: APIConfig.Endpoints.startWaitingRoom,
                method: "POST",
                body: WaitingRoomRequest()
            )

            // For now, we just trigger navigation. The actual connection will be handled by the view.
            await MainActor.run {
                shouldNavigateToWaitingRoom = true
            }

        } catch {
            await MainActor.run {
                matchStatus = "Could not start the waiting room. Please try again."
                isMatching = false
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
    
    // Reset navigation state (called when returning from waiting room)
    func resetNavigation() {
        DispatchQueue.main.async {
            self.shouldNavigateToWaitingRoom = false
            self.lastMatchResult = nil
            self.waitingRoomInfo = nil
        }
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
 