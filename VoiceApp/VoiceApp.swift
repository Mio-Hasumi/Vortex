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

// Firebase initialization delegate
class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
        FirebaseApp.configure()
        
        // Configure Firestore settings
        let db = Firestore.firestore()
        let settings = FirestoreSettings()
        settings.isPersistenceEnabled = true  // Enable offline support
        db.settings = settings
        
        print("🔥 Firebase configured with Auth, Firestore, and Storage")
        return true
    }
}

@main
struct VoiceAppApp: App {
    // Register AppDelegate to set up Firebase
    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate
    
    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}

// Root view - manage authentication state
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

