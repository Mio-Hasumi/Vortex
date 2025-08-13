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
import UserNotifications

// Firebase initialization delegate
class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    func application(_ application: UIApplication,
                    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
        FirebaseApp.configure()
        
        // Configure Firestore settings
        let db = Firestore.firestore()
        let settings = FirestoreSettings()
        settings.isPersistenceEnabled = true  // Enable offline support
        db.settings = settings
        
        // Request notification permissions for Firebase phone auth
        UNUserNotificationCenter.current().delegate = self
        requestNotificationPermissions()
        
        print("🔥 Firebase configured with Auth, Firestore, and Storage")
        return true
    }
    
    // MARK: - Notification Permissions
    
    private func requestNotificationPermissions() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, error in
            DispatchQueue.main.async {
                if granted {
                    print("✅ Notification permissions granted")
                    // Register for remote notifications
                    UIApplication.shared.registerForRemoteNotifications()
                } else {
                    print("❌ Notification permissions denied: \(error?.localizedDescription ?? "Unknown error")")
                }
            }
        }
    }
    
    // MARK: - Remote Notification Handling for Firebase Phone Auth
    
    func application(_ application: UIApplication,
                    didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        // Forward device token to Firebase for phone authentication
        Auth.auth().setAPNSToken(deviceToken, type: .prod)
        print("📱 Device token registered for Firebase phone auth")
    }
    
    func application(_ application: UIApplication,
                    didFailToRegisterForRemoteNotificationsWithError error: Error) {
        print("❌ Failed to register for remote notifications: \(error)")
    }
    
    func application(_ application: UIApplication,
                    didReceiveRemoteNotification userInfo: [AnyHashable: Any],
                    fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void) {
        
        // Check if this notification is for Firebase phone authentication
        if Auth.auth().canHandleNotification(userInfo) {
            print("📱 Firebase phone auth notification received")
            completionHandler(.noData)
            return
        }
        
        // Handle other remote notifications if needed
        completionHandler(.noData)
    }
    
    // MARK: - User Notification Center Delegate
    
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                              willPresent notification: UNNotification,
                              withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        // Show notification even when app is in foreground
        completionHandler([.alert, .badge, .sound])
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

