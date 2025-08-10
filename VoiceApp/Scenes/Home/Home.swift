//
//  Home.swift
//  VoiceApp
//
//  Created by Yuxiang Cheng on 7/18/25.
//

import SwiftUI

// ─────────────────────────────────────────────────────────────
// HOME VIEW - Home page view
// ─────────────────────────────────────────────────────────────

struct HomeView: View {
    @StateObject private var voiceService = VoiceMatchingService.shared
    @State private var showFeed = false
    @State private var showSidebar = false
    @State private var searchQuery = ""
    @State private var textSegments: [String] = [] // Array of completed text segments
    @State private var currentTypingText = "" // Currently typing text
    @State private var fullText = "Tap to start recording, let me help you find interesting conversations..." // Full text to type
    @State private var typingTimer: Timer?
    @State private var currentCharIndex = 0
    @State private var isTyping = false
    @State private var showCursor = true // For blinking cursor effect
    @State private var cursorTimer: Timer?
    @State private var showTestChat = false
    
    // Voice matching related text
    private let matchingTexts = [
        "Tap to start recording, let me help you find interesting conversations...",
        "Share your interests, and I'll match you with like-minded people",
        "What would you like to talk about? Tech, sports, culture, or life? Let me hear your thoughts",
        "Use your voice to start a new conversation, I'm here waiting for you",
        "What kind of people do you want to chat with today? Share your thoughts"
    ]
    
    private func startVoiceMatching() {
        print("🏠 [HomeView] User tapped to start voice matching")
        
        Task {
            do {
                try await voiceService.startRecording()
                await MainActor.run {
                    print("🏠 [HomeView] Recording started, updating UI")
                    // Stop current typing animation
                    stopTyping()
                    // Clear text segments to hide scrolling text
                    textSegments.removeAll()
                    currentTypingText = ""
                    // Start recording state pulse animation
                    startCursorBlinking()
                }
            } catch {
                await MainActor.run {
                    print("🏠 [HomeView] Recording failed: \(error)")
                    // Show error message
                    fullText = "Recording failed. Please try again."
                    currentTypingText = ""
                    currentCharIndex = 0
                    startTyping()
                }
            }
        }
    }
    
    private func stopVoiceMatching() {
        print("🏠 [HomeView] User tapped to stop voice matching")
        
        Task {
            do {
                try await voiceService.stopRecording()
                await MainActor.run {
                    print("🏠 [HomeView] Recording stopped, updating UI")
                    // Stop recording animation
                    stopCursorBlinking()
                }
            } catch {
                await MainActor.run {
                    print("🏠 [HomeView] Stop recording failed: \(error)")
                    // Show error message
                    fullText = "Failed to process recording. Please try again."
                    currentTypingText = ""
                    currentCharIndex = 0
                    startTyping()
                }
            }
        }
    }
    
    private func navigateToTestChat() {
        print("🧪 [HomeView] Navigating to test chat")
        showTestChat = true
    }
    
    // Simulate API text updates with typing effect
    private func startTypingNewText() {
        let newText = matchingTexts.randomElement() ?? matchingTexts[0]
        
        // Move current typing text to completed segments if it exists
        if !currentTypingText.isEmpty {
            textSegments.append(currentTypingText)
            // Keep only last 5 segments to prevent memory growth
            if textSegments.count > 5 {
                textSegments.removeFirst()
            }
        }
        
        // Start typing the new text
        fullText = newText
        currentTypingText = ""
        currentCharIndex = 0
        startTyping()
    }
    
    private func typeNextCharacter() {
        guard currentCharIndex < fullText.count else {
            // Typing completed
            isTyping = false
            
            // Keep cursor blinking for a moment after typing completes
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                stopCursorBlinking()
            }
            
            // Start typing next text after a delay
            DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
                startTypingNewText()
            }
            return
        }
        
        let index = fullText.index(fullText.startIndex, offsetBy: currentCharIndex)
        currentTypingText = String(fullText[...index])
        currentCharIndex += 1
        
        // Variable typing speed for more natural effect
        let baseInterval: Double = 0.05
        let currentChar = fullText[index]
        var interval = baseInterval
        
        // Slower for punctuation
        if currentChar.isPunctuation {
            interval = baseInterval * 3
        }
        // Pause at spaces
        else if currentChar.isWhitespace {
            interval = baseInterval * 2
        }
        // Add some randomness
        else {
            interval = baseInterval * Double.random(in: 0.8...1.5)
        }
        
        typingTimer = Timer.scheduledTimer(withTimeInterval: interval, repeats: false) { _ in
            typeNextCharacter()
        }
    }
    
    private func startTyping() {
        guard !isTyping else { return }
        
        isTyping = true
        typingTimer?.invalidate()
        startCursorBlinking()
        
        typeNextCharacter()
    }
    
    private func startCursorBlinking() {
        cursorTimer?.invalidate()
        showCursor = true
        
        cursorTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { _ in
            showCursor.toggle()
        }
    }
    
    private func stopCursorBlinking() {
        cursorTimer?.invalidate()
        cursorTimer = nil
        showCursor = false
    }
    
    private func stopTyping() {
        typingTimer?.invalidate()
        typingTimer = nil
        stopCursorBlinking()
        isTyping = false
          }
      
      var body: some View {
        ZStack {
            // Background
            Color.black.ignoresSafeArea()
            
            // Starfield background decoration
            StarfieldView()
            
            VStack(spacing: 0) {
                // Top area - Hamburger menu and avatar
                VStack(spacing: 0) {
                    // Hamburger menu
                    HStack {
                        Button(action: {
                            showSidebar = true
                        }) {
                            VStack(spacing: 4) {
                                Rectangle()
                                    .frame(width: 20, height: 2)
                                Rectangle()
                                    .frame(width: 20, height: 2)
                                Rectangle()
                                    .frame(width: 20, height: 2)
                            }
                            .foregroundColor(.white)
                        }
                        
                        Spacer()
                        
                        // Test Chat Button
                        Button(action: {
                            navigateToTestChat()
                        }) {
                            HStack(spacing: 8) {
                                Image(systemName: "message.circle.fill")
                                    .font(.system(size: 16))
                                
                                Text("Test Chat")
                                    .font(.system(size: 14, weight: .medium))
                            }
                            .foregroundColor(.white)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 8)
                            .background(
                                RoundedRectangle(cornerRadius: 20)
                                    .fill(Color.blue.opacity(0.3))
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 20)
                                            .stroke(Color.blue.opacity(0.6), lineWidth: 1)
                                    )
                            )
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 20)
                    
                    Spacer()
                }
                .frame(maxHeight: .infinity)
                
                // Bottom area - Dynamic API text with scrolling
                VStack {
                    Spacer() // Push content to bottom
                    
                                        // Scrollable dynamic text with fade effect
                    ZStack {
                        ScrollViewReader { proxy in
                            ScrollView(.vertical, showsIndicators: false) {
                                LazyVStack(alignment: .leading, spacing: 16) {
                                    // Add blank space when no text segments to push current text below fade zone
                                    if textSegments.isEmpty {
                                        Text(" ")
                                            .font(.system(size: 48, weight: .light))
                                            .foregroundColor(.clear)
                                            .frame(height: 80) // Spacer to push content below fade area
                                            .id("blank-spacer")
                                    }
                                    
                                    // Show completed text segments only when not recording or matching
                                    if !voiceService.isRecording && !voiceService.isMatching {
                                        ForEach(Array(textSegments.enumerated()), id: \.offset) { index, segment in
                                            Text(segment)
                                                .font(.system(size: 48, weight: .light))
                                                .foregroundColor(.white)
                                                .frame(maxWidth: .infinity, alignment: .leading)
                                                .lineLimit(nil)
                                                .multilineTextAlignment(.leading)
                                                .id("segment-\(index)")
                                        }
                                    }
                                    
                                    // Show currently typing text with voice matching status
                                    Group {
                                        if voiceService.isRecording {
                                            // Recording state with animation
                                            Text("Recording... Tap to stop")
                                                .font(.system(size: 48, weight: .light))
                                                .foregroundColor(showCursor ? .white : .white.opacity(0.8))
                                                .animation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true), value: showCursor)
                                                .padding(.leading, 20) // Move text to the right
                                        } else if voiceService.isMatching {
                                            // Matching state with loading animation
                                            HStack(spacing: 16) {
                                                // Loading spinner
                                                ProgressView()
                                                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                                    .scaleEffect(1.5)
                                                
                                                Text("Analyzing voice...")
                                                    .font(.system(size: 48, weight: .light))
                                                    .foregroundColor(showCursor ? .white : .white.opacity(0.8))
                                                    .animation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true), value: showCursor)
                                            }
                                            .padding(.leading, 20) // Move both spinner and text to the right
                                        } else {
                                            // Normal typing text - use same layout structure for consistency
                                            HStack(spacing: 16) {
                                                // Invisible spacer to maintain layout consistency
                                                Rectangle()
                                                    .fill(Color.clear)
                                                    .frame(width: 20, height: 20)
                                                
                                                Text(currentTypingText + (showCursor ? "|" : ""))
                                                    .font(.system(size: 48, weight: .light))
                                                    .foregroundColor(.white)
                                            }
                                            .padding(.leading, 20) // Same padding as other states
                                        }
                                    }
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .lineLimit(nil)
                                        .multilineTextAlignment(.leading)
                                        .id("current-typing")
                                    .onTapGesture {
                                        if voiceService.isRecording {
                                            stopVoiceMatching()
                                        } else if !voiceService.isMatching {
                                            startVoiceMatching()
                                        }
                                    }
                                }
                                .padding(.vertical, 8)
                            }
                            .onChange(of: currentTypingText) { _ in
                                // Auto scroll to bottom when typing progresses
                                withAnimation(.easeOut(duration: 0.3)) {
                                    proxy.scrollTo("current-typing", anchor: .bottom)
                                }
                            }
                            .onChange(of: textSegments.count) { _ in
                                // Auto scroll to bottom when new segment is added
                                withAnimation(.easeOut(duration: 0.5)) {
                                    proxy.scrollTo("current-typing", anchor: .bottom)
                                }
                            }
                        }
                        
                        // Top fade overlay
                        VStack {
                            LinearGradient(
                                colors: [
                                    Color.black,
                                    Color.black.opacity(0.8),
                                    Color.black.opacity(0.4),
                                    Color.clear
                                ],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                            .frame(height: 50)
                            .allowsHitTesting(false)
                            
                            Spacer()
                        }
                    }
                    .frame(maxHeight: 48 * 4 + 32)
                    .clipped()
                    .padding(.leading, 20)
                    .padding(.trailing, 50)
                    .padding(.bottom, 110)
                }
            }
        }
        .navigationBarHidden(true)
        .navigationDestination(isPresented: $showTestChat) {
            TestChatView()
        }
        .onAppear {
            print("🏠 [HomeView] View appeared")
            startTypingNewText()
        }
        .onChange(of: voiceService.shouldNavigateToWaitingRoom) { shouldNavigate in
            if shouldNavigate {
                print("🚪 [HomeView] About to navigate to waiting room")
            }
                    }
        .onChange(of: voiceService.isMatching) { isMatching in
            print("🏠 [HomeView] Matching state changed: \(isMatching)")
            if !isMatching && !voiceService.isRecording {
                print("🏠 [HomeView] Both recording and matching finished, scheduling text reset")
                // Only restart typing if not navigating to waiting room
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                    if !voiceService.shouldNavigateToWaitingRoom {
                        print("🏠 [HomeView] Resetting to normal text after showing results")
                        startTypingNewText()
                    }
                }
            } else if isMatching {
                // Stop typing when matching starts
                print("🏠 [HomeView] Matching started, stopping typing animation")
                stopTyping()
                textSegments.removeAll()
                currentTypingText = ""
            }
        }
        .onChange(of: voiceService.isRecording) { isRecording in
            print("🏠 [HomeView] Recording state changed: \(isRecording)")
            if isRecording {
                print("🏠 [HomeView] Recording started, updating UI")
            } else {
                print("🏠 [HomeView] Recording stopped, updating UI")
            }
        }
        .onChange(of: voiceService.matchStatus) { status in
            print("🏠 [HomeView] Match status changed: \(status ?? "nil")")
            if let status = status, status.contains("Found the following topics") {
                print("🎉 [HomeView] Match found with topics!")
            }
        }
        .onDisappear {
            stopTyping()
        }
        // Avatar positioned as overlay to not affect layout
        .overlay(
            ZStack {
                // Main glowing sphere
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [.white, .white.opacity(0.8), .white.opacity(0.4), .clear],
                            center: .center,
                            startRadius: 0,
                            endRadius: 220
                        )
                    )
                    .frame(width: 420, height: 420)
                    .blur(radius: 2)
                
                // Internal texture
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [.white.opacity(0.9), .white.opacity(0.6), .white.opacity(0.3)],
                            center: .center,
                            startRadius: 0,
                            endRadius: 180
                        )
                    )
                    .frame(width: 360, height: 360)
                    .overlay(
                        // Add some texture points
                        ForEach(0..<80, id: \.self) { _ in
                            Circle()
                                .fill(Color.white.opacity(0.3))
                                .frame(width: CGFloat.random(in: 1...3), height: CGFloat.random(in: 1...3))
                                .position(
                                    x: CGFloat.random(in: 0...360),
                                    y: CGFloat.random(in: 0...360)
                                )
                        }
                    )
            }
            .offset(x: -60, y: -180) // Position independently without affecting layout
        )
        // Use new FeedTab component
        .overlay(
            FeedTabOverlay(
                isPresented: $showFeed,
                searchQuery: $searchQuery,
                configuration: .default
            )
        )
        // Add sidebar component
        .overlay(
            SidebarOverlay(
                isPresented: $showSidebar,
                configuration: .default
            )
        )
    }
}

// ─────────────────────────────────────────────────────────────
// STARFIELD BACKGROUND
// ─────────────────────────────────────────────────────────────

struct StarfieldView: View {
    var body: some View {
        ZStack {
            ForEach(0..<100, id: \.self) { _ in
                Circle()
                    .fill(Color.white.opacity(Double.random(in: 0.1...0.8)))
                    .frame(width: CGFloat.random(in: 0.5...2), height: CGFloat.random(in: 0.5...2))
                    .position(
                        x: CGFloat.random(in: 0...400),
                        y: CGFloat.random(in: 0...800)
                    )
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────
// PREVIEW
// ─────────────────────────────────────────────────────────────

#Preview {
    HomeView()
        .preferredColorScheme(.dark)
} 