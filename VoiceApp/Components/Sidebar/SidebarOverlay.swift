//
//  SidebarOverlay.swift
//  VoiceApp
//
//  Created by Yuxiang Cheng on 7/18/25.
//

import SwiftUI

// ─────────────────────────────────────────────────────────────
// SIDEBAR OVERLAY - Reusable sidebar component
// ─────────────────────────────────────────────────────────────

struct SidebarOverlay: View {
    @Binding var isPresented: Bool
    let configuration: SidebarConfiguration
    
    @State private var dragOffset: CGFloat = 0
    @State private var isDragging: Bool = false
    
    // Configuration structure
    struct SidebarConfiguration {
        let widthRatio: CGFloat
        let showCloseButton: Bool
        let cornerRadius: CGFloat
        
        static let `default` = SidebarConfiguration(
            widthRatio: 0.6,
            showCloseButton: true,
            cornerRadius: 20
        )
    }
    
    var body: some View {
        GeometryReader { geometry in
            let screenWidth = geometry.size.width
            let sidebarWidth = screenWidth * configuration.widthRatio
            
            let currentOffset = isDragging ? 
                max(-sidebarWidth, min(0, dragOffset)) :
                (isPresented ? 0 : -sidebarWidth)
            
            if isPresented || isDragging {
                ZStack(alignment: .leading) {
                    // Background overlay (tap to close)
                    Color.black.opacity(0.3)
                        .ignoresSafeArea()
                        .onTapGesture {
                            withAnimation(.easeOut(duration: 0.3)) {
                                isPresented = false
                            }
                        }
                    
                    // Sidebar content
                    SidebarContent(configuration: configuration)
                        .frame(width: sidebarWidth)
                        .background(
                            // Glass background effect
                            Color.clear
                                .background(.thickMaterial, in: UnevenRoundedRectangle(bottomTrailingRadius: configuration.cornerRadius, topTrailingRadius: configuration.cornerRadius))
                                .background(
                                    UnevenRoundedRectangle(bottomTrailingRadius: configuration.cornerRadius, topTrailingRadius: configuration.cornerRadius)
                                        .fill(.regularMaterial)
                                        .opacity(0.3)
                                )
                                .background(
                                    UnevenRoundedRectangle(bottomTrailingRadius: configuration.cornerRadius, topTrailingRadius: configuration.cornerRadius)
                                        .fill(.bar)
                                        .opacity(0.2)
                                )
                                .compositingGroup()
                                .opacity(0.85)
                        )
                        .clipShape(UnevenRoundedRectangle(bottomTrailingRadius: configuration.cornerRadius, topTrailingRadius: configuration.cornerRadius))
                        .offset(x: currentOffset)
                        .animation(.easeInOut(duration: isDragging ? 0 : 0.3), value: currentOffset)
                        .gesture(
                            DragGesture()
                                .onChanged { value in
                                    if !isDragging {
                                        isDragging = true
                                    }
                                    dragOffset = value.translation.width
                                }
                                .onEnded { value in
                                    isDragging = false
                                    let translation = value.translation.width
                                    let velocity = value.velocity.width
                                    
                                    withAnimation(.easeOut(duration: 0.3)) {
                                        if translation < -100 || velocity < -500 {
                                            // Swipe left enough, close sidebar
                                            isPresented = false
                                        } else {
                                            // Return to open state
                                            dragOffset = 0
                                        }
                                    }
                                }
                        )
                }
                .transition(.move(edge: .leading).combined(with: .opacity))
            }
        }
        .ignoresSafeArea()
    }
}

// ─────────────────────────────────────────────────────────────
// SIDEBAR CONTENT - Main sidebar content view
// ─────────────────────────────────────────────────────────────

struct SidebarContent: View {
    let configuration: SidebarOverlay.SidebarConfiguration
    @ObservedObject private var authService = AuthService.shared
    @State private var showSettings = false
    @State private var showProfile = false
    @State private var showFriends = false
    @State private var showHistory = false
    @State private var showHelp = false
    
    var body: some View {
        VStack(spacing: 0) {
            // Header area
            VStack(spacing: 20) {
                // Top spacing
                Spacer()
                    .frame(height: 60)
                
                // Profile section
                VStack(spacing: 16) {
                    // Profile image
                    Button(action: { showProfile = true }) {
                        CachedAsyncImage(url: authService.profileImageUrl) { image in
                            image
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                                .frame(width: 80, height: 80)
                                .clipShape(Circle())
                        } placeholder: {
                            ShimmerPlaceholder(
                                size: CGSize(width: 80, height: 80),
                                cornerRadius: 40
                            )
                            .overlay(
                                Image(systemName: "person.fill")
                                    .font(.system(size: 35))
                                    .foregroundColor(.white)
                            )
                        }
                    }
                    .onAppear {
                        // Preload profile image for smoother experience
                        if let profileImageUrl = authService.profileImageUrl, !profileImageUrl.isEmpty {
                            ImageCacheService.shared.preloadImage(from: profileImageUrl)
                        }
                    }
                    
                    // User name - display first name from email
                    Text(authService.uiDisplayName)
                        .font(.system(size: 24, weight: .semibold, design: .rounded))
                        .foregroundColor(.white)
                    
                    // User status
                    Text("Ready to explore")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.white.opacity(0.7))
                }
                .padding(.horizontal, 24)
            }
            
            Spacer()
                .frame(height: 40)
            
            // Menu items
            VStack(spacing: 8) {
                SidebarMenuItem(
                    icon: "house.fill",
                    title: "Home",
                    isSelected: true,
                    action: {
                        // Already on Home page, no additional action needed
                        print("Home selected")
                    }
                )
                
                SidebarMenuItem(
                    icon: "person.2.fill",
                    title: "Friends",
                    action: {
                        showFriends = true
                    }
                )
                
                SidebarMenuItem(
                    icon: "heart.fill",
                    title: "Favorites",
                    action: {
                        print("Favorites selected")
                    }
                )
                
                SidebarMenuItem(
                    icon: "clock.fill",
                    title: "History",
                    action: {
                        showHistory = true
                    }
                )
                
                Divider()
                    .background(Color.white.opacity(0.2))
                    .padding(.horizontal, 24)
                    .padding(.vertical, 16)
                
                SidebarMenuItem(
                    icon: "gear",
                    title: "Settings",
                    action: {
                        showSettings = true
                    }
                )
                
                SidebarMenuItem(
                    icon: "questionmark.circle",
                    title: "Help",
                    action: {
                        showHelp = true
                    }
                )
                
                SidebarMenuItem(
                    icon: "rectangle.portrait.and.arrow.right",
                    title: "Sign Out",
                    action: {
                        Task {
                            try await authService.signOut()
                        }
                    }
                )
            }
            .padding(.horizontal, 16)
            
            Spacer()
            
            // Bottom info
            VStack(spacing: 8) {
                Text("VoiceApp")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
                
                Text("Version 1.0.0")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(.white.opacity(0.5))
            }
            .padding(.bottom, 40)
        }
        .sheet(isPresented: $showSettings) {
            SettingsView()
        }
        .sheet(isPresented: $showProfile) {
            ProfileView()
        }
        .sheet(isPresented: $showFriends) {
            FriendsView()
        }
        .sheet(isPresented: $showHistory) {
            HistoryView()
        }
        .sheet(isPresented: $showHelp) {
            HelpView()
        }
    }
}

// ─────────────────────────────────────────────────────────────
// SIDEBAR MENU ITEM - Individual menu item component
// ─────────────────────────────────────────────────────────────

struct SidebarMenuItem: View {
    let icon: String
    let title: String
    var isSelected: Bool = false
    var action: (() -> Void)? = nil
    
    var body: some View {
        Button(action: { action?() }) {
            HStack(spacing: 16) {
                Image(systemName: icon)
                    .font(.system(size: 18, weight: .medium))
                    .foregroundColor(isSelected ? .white : .white.opacity(0.8))
                    .frame(width: 24, height: 24)
                
                Text(title)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(isSelected ? .white : .white.opacity(0.8))
                
                Spacer()
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 16)
            .background(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(isSelected ? Color.white.opacity(0.15) : Color.clear)
            )
        }
        .buttonStyle(PlainButtonStyle())
    }
}

// ─────────────────────────────────────────────────────────────
// PREVIEW
// ─────────────────────────────────────────────────────────────

#Preview("Sidebar - Closed State") {
    @State var isPresented = false
    
    return ZStack {
        Color.black.ignoresSafeArea()
        
        // Simulate home page background
        VStack {
            Text("Home Page Content")
                .font(.largeTitle)
                .foregroundColor(.white)
            Spacer()
        }
        .padding(.top, 100)
        
        SidebarOverlay(
            isPresented: $isPresented,
            configuration: .default
        )
    }
    .preferredColorScheme(.dark)
}

#Preview("Sidebar - Open State") {
    @State var isPresented = true
    
    return ZStack {
        Color.black.ignoresSafeArea()
        
        // Simulate home page background
        VStack {
            Text("Home Page Content")
                .font(.largeTitle)
                .foregroundColor(.white)
            Spacer()
        }
        .padding(.top, 100)
        
        SidebarOverlay(
            isPresented: $isPresented,
            configuration: .default
        )
    }
    .preferredColorScheme(.dark)
} 