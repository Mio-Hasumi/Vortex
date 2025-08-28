//
//  FeedTabOverlay.swift
//  VoiceApp
//
//  Created by Yuxiang Cheng on 7/18/25.
//

import SwiftUI

// ─────────────────────────────────────────────────────────────
// FEED TAB OVERLAY - Reusable feed page component
// ─────────────────────────────────────────────────────────────

struct FeedTabOverlay: View {
    @Binding var isPresented: Bool
    @Binding var searchQuery: String
    let configuration: FeedConfiguration
    
    @State private var dragOffset: CGFloat = 0
    @State private var isExpanded: Bool = false
    @State private var isDragging: Bool = false
    @State private var showProfile = false
    
    // Configuration structure
    struct FeedConfiguration {
        let placeholder: String
        let showProfile: Bool
        let maxHeightRatio: CGFloat
        let topMarginRatio: CGFloat
        
        static let `default` = FeedConfiguration(
            placeholder: "Latest popular chat on #Sports_",
            showProfile: true,
            maxHeightRatio: 0.8,
            topMarginRatio: 0.2
        )
    }
    
    var body: some View {
        GeometryReader { geometry in
            let screenHeight = geometry.size.height
            let topMargin = screenHeight * configuration.topMarginRatio
            // Note: bumpHeight no longer used - handle is now inside tab
            let bottomBarHeight: CGFloat = 120
            let idleHeight: CGFloat = 90 // Small height for idle state
            let minTotalHeight = screenHeight * 0.55 + bottomBarHeight // Bump extends upward, no need to add its height
            let maxTotalHeight = screenHeight * configuration.maxHeightRatio + bottomBarHeight
            
            let currentTotalHeight = isDragging ? 
                max(minTotalHeight * 0.4, min(maxTotalHeight, isExpanded ? maxTotalHeight : minTotalHeight + dragOffset)) :
                (isExpanded ? maxTotalHeight : minTotalHeight)
            
            let feedContentHeight = currentTotalHeight - bottomBarHeight // Only subtract bottom bar height
            
            // Unified animated tab (always present)
            VStack {
                // Top tap-to-close area (only when expanded)
                if isPresented {
                    Color.clear
                        .frame(height: topMargin)
                        .contentShape(Rectangle())
                        .onTapGesture {
                            withAnimation(.easeOut(duration: 0.3)) {
                                isPresented = false
                            }
                        }
                }
                
                Spacer()
                
                // Unified tab container
                ZStack(alignment: .top) {
                    // Main tab content
                    VStack(spacing: 0) {
                        // Top spacing (varies by state)
                        if !isPresented {
                            Spacer()
                                .frame(height: 25)
                        }
                        
                        // Search bar and avatar area
                        VStack(spacing: isPresented ? 16 : 0) {
                                // Search bar and avatar
                                HStack(spacing: 12) {
                                    HStack {
                                        TextField(configuration.placeholder, text: $searchQuery)
                                            .textFieldStyle(.plain)
                                            .foregroundColor(.white)
                                            .font(.system(size: 14))
                                            .padding(.leading, 12)
                                        
                                        Spacer()
                                    }
                                    .frame(height: 44)
                                    .background(Color.white.opacity(0.15))
                                    .clipShape(RoundedRectangle(cornerRadius: 12))
                                    
                                    // Avatar button (optional)
                                    if configuration.showProfile {
                                        Button(action: {
                                            showProfile = true
                                        }) {
                                            Circle()
                                                .fill(Color.white.opacity(0.25))
                                                .frame(width: 44, height: 44)
                                                .overlay(
                                                    Image(systemName: "person.fill")
                                                        .font(.system(size: 20))
                                                        .foregroundColor(.white.opacity(0.9))
                                                )
                                        }
                                    }
                                }
                                .padding(.horizontal, 24)
                                .padding(.top, isPresented ? 20 : 0)
                                .padding(.bottom, isPresented ? 20 : 0)
                            }
                            
                            // Feed content (only when expanded)
                            if isPresented {
                                FeedView()
                                    .frame(height: feedContentHeight)
                                    .clipped()
                            }
                    }
                    .clipShape(
                        isPresented ? 
                        UnevenRoundedRectangle(topLeadingRadius: 35, bottomLeadingRadius: 0, bottomTrailingRadius: 0, topTrailingRadius: 35) :
                        UnevenRoundedRectangle(topLeadingRadius: 35, topTrailingRadius: 35)
                    )
                    
                    // Drag handle (two lines)
                    VStack(spacing: 4) {
                        Capsule()
                            .frame(width: 44, height: 3)
                            .foregroundColor(.white.opacity(0.7))
                        Capsule()
                            .frame(width: 44, height: 3)
                            .foregroundColor(.white.opacity(0.7))
                    }
                }
                .frame(height: isPresented ? currentTotalHeight : idleHeight)
                .padding(.bottom, isPresented ? 0 : 10)
                .background(
                    // Animated glass background
                    Color.clear
                        .background(
                            .thickMaterial, 
                            in: isPresented ? 
                                UnevenRoundedRectangle(topLeadingRadius: 35, bottomLeadingRadius: 0, bottomTrailingRadius: 0, topTrailingRadius: 35) :
                                UnevenRoundedRectangle(topLeadingRadius: 35, topTrailingRadius: 35)
                        )
                        .background(
                            (isPresented ? 
                                UnevenRoundedRectangle(topLeadingRadius: 35, bottomLeadingRadius: 0, bottomTrailingRadius: 0, topTrailingRadius: 35) :
                                UnevenRoundedRectangle(topLeadingRadius: 35, topTrailingRadius: 35)
                            ).fill(.regularMaterial).opacity(0.3)
                        )
                        .background(
                            (isPresented ? 
                                UnevenRoundedRectangle(topLeadingRadius: 35, bottomLeadingRadius: 0, bottomTrailingRadius: 0, topTrailingRadius: 35) :
                                UnevenRoundedRectangle(topLeadingRadius: 35, topTrailingRadius: 35)
                            ).fill(.bar).opacity(0.2)
                        )
                        .compositingGroup()
                        .opacity(0.85)
                        .ignoresSafeArea(edges: .bottom)
                )
                .ignoresSafeArea(edges: .bottom)
                .animation(.easeInOut(duration: 0.3), value: isPresented)
                .animation(.easeInOut(duration: isDragging ? 0 : 0.3), value: currentTotalHeight)
                .gesture(
                    DragGesture()
                        .onChanged { value in
                            if !isDragging {
                                isDragging = true
                            }
                            dragOffset = -value.translation.height
                        }
                        .onEnded { value in
                            isDragging = false
                            let translation = value.translation.height
                            let velocity = value.velocity.height
                            
                            withAnimation(.easeOut(duration: 0.3)) {
                                if translation > 150 || velocity > 800 {
                                    // Drag down far enough, close
                                    isPresented = false
                                } else if translation < -100 || velocity < -800 {
                                    // Drag up, expand
                                    isPresented = true
                                    isExpanded = true
                                } else if !isPresented {
                                    // Tap to expand when closed
                                    isPresented = true
                                } else if currentTotalHeight > maxTotalHeight * 0.7 {
                                    // Over 70% height, auto expand
                                    isExpanded = true
                                } else {
                                    // Return to initial state
                                    isExpanded = false
                                }
                                dragOffset = 0
                            }
                        }
                )
                .onTapGesture {
                    if !isPresented {
                        withAnimation(.easeOut(duration: 0.3)) {
                            isPresented = true
                        }
                    }
                }
            }
        }
        .ignoresSafeArea()
        .sheet(isPresented: $showProfile) {
            ProfileView()
        }
    }
}

// ─────────────────────────────────────────────────────────────
// FEED VIEW - Feed content view
// ─────────────────────────────────────────────────────────────

struct FeedView: View {
    @State private var query = ""
    
    var body: some View {
        VStack(spacing: 20) {
            // Title
            HStack {
                Text("Trending")
                    .font(.system(size: 32, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
                Spacer()
            }
            .padding(.horizontal, 24)
            .padding(.top, 20)
            
            // Feed card list (infinite loop)
            ScrollView(showsIndicators: false) {
                LazyVStack(spacing: 18) {
                    // Repeat the same cards to achieve infinite loop effect
                    ForEach(0..<50) { index in
                        let item = sampleFeed[index % sampleFeed.count]
                        TrendingCard(item: item)
                            .id("\(index)-\(item.id)")
                    }
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 40)
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MODELS & DATA
// ─────────────────────────────────────────────────────────────

struct FeedItem: Identifiable {
    let id = UUID()
    let title: String
    let tags: String
    let gradient: [Color]
}

// Sample data
let sampleFeed = [
    FeedItem(title: "The Algorithm That Knows Why You're Single",
             tags: "#dating #relationships #tinder #bumble",
             gradient: [.red.opacity(0.9), .pink.opacity(0.9)]),
    FeedItem(title: "Chatbot Has Better Life Advice Than My Mom",
             tags: "#lifeadvice #family #millennialproblems",
             gradient: [.blue.opacity(0.85), .teal.opacity(0.9)]),
    FeedItem(title: "This Couple Asked AI About Their Relationship and Almost Broke Up On Air",
             tags: "#breakup #couplesgoals #relationshipdrama",
             gradient: [.purple.opacity(0.9), .pink.opacity(0.8)]),
    FeedItem(title: "Two Random Strangers Asked AI About Their Biggest Secrets and One Started Crying",
             tags: "#secret #awkward #vulnerability #mentalhealth",
             gradient: [.olive, .olive.opacity(0.8)]),
    FeedItem(title: "Two Random Strangers Asked AI About Their Biggest Secrets",
             tags: "#secret #awkward #vulnerability #mentalhealth",
             gradient: [.gray.opacity(0.4), .gray.opacity(0.6)])
]

// ─────────────────────────────────────────────────────────────
// UI COMPONENTS
// ─────────────────────────────────────────────────────────────

// Trending card
struct TrendingCard: View {
    let item: FeedItem
    
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("\"\(item.title)\"")
                .font(.headline.weight(.semibold))
                .foregroundColor(.white)
                .fixedSize(horizontal: false, vertical: true)
            
            Text(item.tags)
                .font(.footnote)
                .foregroundColor(.white.opacity(0.8))
            
            WaveformView()
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            ZStack {
                // Glass background
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(.ultraThinMaterial)
                    .opacity(0.3)
                
                // Light color gradient overlay
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: item.gradient.map { $0.opacity(0.15) },
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            }
        )
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(Color.white.opacity(0.1), lineWidth: 0.5)
        )
    }
}

// Audio waveform view
struct WaveformView: View {
    private let bars = (1...60).map { _ in CGFloat.random(in: 5...22) }
    
    var body: some View {
        HStack(alignment: .bottom, spacing: 2) {
            ForEach(bars.indices, id: \.self) { index in
                Capsule()
                    .frame(width: 2, height: bars[index])
            }
        }
        .foregroundColor(.white.opacity(0.9))
        .frame(height: 30)
        .padding(.top, 12)
    }
}

// Color extensions
extension Color {
    static let olive = Color(#colorLiteral(red: 0.4, green: 0.5, blue: 0.22, alpha: 1))
}

// ─────────────────────────────────────────────────────────────
// CUSTOM SHAPES
// ─────────────────────────────────────────────────────────────

// Custom shape for tab with protruding bump
struct TabWithBumpShape: Shape {
    let bumpWidth: CGFloat
    let bumpHeight: CGFloat
    let cornerRadius: CGFloat
    
    func path(in rect: CGRect) -> Path {
        var path = Path()
        
        let bumpCenterX = rect.midX
        let bumpStartX = bumpCenterX - bumpWidth / 2
        let bumpEndX = bumpCenterX + bumpWidth / 2
        let adjustedTop = rect.minY + bumpHeight // Main container starts below the bump
        
        // Start from top-left corner (below bump area)
        path.move(to: CGPoint(x: rect.minX + cornerRadius, y: adjustedTop))
        
        // Top edge until bump starts
        path.addLine(to: CGPoint(x: bumpStartX, y: adjustedTop))
        
        // Bump curve - create a smooth semicircular protrusion upward
        path.addQuadCurve(
            to: CGPoint(x: bumpEndX, y: adjustedTop),
            control: CGPoint(x: bumpCenterX, y: rect.minY) // Control point above creates upward bump
        )
        
        // Continue top edge after bump
        path.addLine(to: CGPoint(x: rect.maxX - cornerRadius, y: adjustedTop))
        
        // Top-right corner
        path.addQuadCurve(
            to: CGPoint(x: rect.maxX, y: adjustedTop + cornerRadius),
            control: CGPoint(x: rect.maxX, y: adjustedTop)
        )
        
        // Right edge
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY - cornerRadius))
        
        // Bottom-right corner
        path.addQuadCurve(
            to: CGPoint(x: rect.maxX - cornerRadius, y: rect.maxY),
            control: CGPoint(x: rect.maxX, y: rect.maxY)
        )
        
        // Bottom edge
        path.addLine(to: CGPoint(x: rect.minX + cornerRadius, y: rect.maxY))
        
        // Bottom-left corner
        path.addQuadCurve(
            to: CGPoint(x: rect.minX, y: rect.maxY - cornerRadius),
            control: CGPoint(x: rect.minX, y: rect.maxY)
        )
        
        // Left edge
        path.addLine(to: CGPoint(x: rect.minX, y: adjustedTop + cornerRadius))
        
        // Top-left corner
        path.addQuadCurve(
            to: CGPoint(x: rect.minX + cornerRadius, y: adjustedTop),
            control: CGPoint(x: rect.minX, y: adjustedTop)
        )
        
        return path
    }
}

// ─────────────────────────────────────────────────────────────
// PREVIEW
// ─────────────────────────────────────────────────────────────
#Preview("Feed Tab - Idle State") {
    @Previewable @State var isPresented = false
    @State var searchQuery = ""
    
    return ZStack {
        Color.black.ignoresSafeArea()
        
        // Simulated home page background
        VStack {
            Text("Home Page Content")
                .font(.largeTitle)
                .foregroundColor(.white)
            Spacer()
        }
        .padding(.top, 100)
        
        FeedTabOverlay(
            isPresented: $isPresented,
            searchQuery: $searchQuery,
            configuration: .default
        )
    }
    .preferredColorScheme(.dark)
}

#Preview("Feed Tab - Expanded State") {
    @State var isPresented = true
    @State var searchQuery = ""
    
    return ZStack {
        Color.black.ignoresSafeArea()
        
        VStack {
            Text("Home Page Content")
                .font(.largeTitle)
                .foregroundColor(.white)
            Spacer()
        }
        .padding(.top, 100)
        
        FeedTabOverlay(
            isPresented: $isPresented,
            searchQuery: $searchQuery,
            configuration: .default
        )
    }
    .preferredColorScheme(.dark)
} 
