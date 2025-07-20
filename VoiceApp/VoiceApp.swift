//
//  VoiceApp.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/18/25.
//

import SwiftUI
import FirebaseCore
import FirebaseAuth
import FirebaseFirestore
import FirebaseStorage

// Firebase 初始化代理
class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
        FirebaseApp.configure()
        
        // 配置 Firestore 设置
        let db = Firestore.firestore()
        let settings = FirestoreSettings()
        settings.isPersistenceEnabled = true  // 启用离线支持
        db.settings = settings
        
        print("🔥 Firebase configured with Auth, Firestore, and Storage")
        return true
    }
}

@main
struct VoiceAppApp: App {
    // 注册 AppDelegate 以设置 Firebase
    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate
    
    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}

// 根视图 - 管理认证状态
struct RootView: View {
    @StateObject private var authService = AuthService.shared
    @StateObject private var voiceService = VoiceMatchingService.shared
    
    var body: some View {
        NavigationStack {
            Group {
                if authService.isAuthenticated {
                    HomeView()
                } else {
            SignIn()
        }
    }
            .navigationDestination(isPresented: $voiceService.shouldNavigateToWaitingRoom) {
                if let matchResult = voiceService.lastMatchResult {
                    UserVoiceTopicMatchingView(matchResult: matchResult)
                }
            }
        }
        .onAppear {
            print("👀 RootView onAppear, isAuthenticated = \(authService.isAuthenticated)")
        }
    }
}

#Preview {
    RootView()
}

