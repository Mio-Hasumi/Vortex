import Foundation
import Firebase
import FirebaseAuth
import GoogleSignIn

class AuthService: ObservableObject {
    static let shared = AuthService()
    
    // Directly publish login status - top-level @Published property
    @Published var isAuthenticated = false
    @Published var userId: String?
    @Published var displayName: String?
    @Published var email: String?
    @Published var firebaseToken: String?
    
    // Store the real Gmail address from Google Sign-In
    @Published var realEmail: String?
    
    // Computed property to always show first name from real Gmail address in UI
    var uiDisplayName: String {
        print("🔍 [AuthService] uiDisplayName called - realEmail: \(realEmail ?? "nil"), email: \(email ?? "nil"), displayName: \(displayName ?? "nil")")
        if let realEmail = realEmail, !realEmail.isEmpty {
            let firstName = extractFirstNameFromEmail(realEmail)
            print("🔍 [AuthService] Extracted firstName: \(firstName) from realEmail: \(realEmail)")
            return firstName
        }
        print("🔍 [AuthService] Using fallback displayName: \(displayName ?? "User")")
        return displayName ?? "User"
    }
    
    private init() {
        // Configure Firebase if not already configured
        if FirebaseApp.app() == nil {
            FirebaseApp.configure()
        }
        
        // Listen for auth state changes
        Auth.auth().addStateDidChangeListener { [weak self] _, firebaseUser in
            DispatchQueue.main.async {
                if let firebaseUser = firebaseUser {
                    print("🔐 Firebase user detected: \(firebaseUser.uid)")
                    // User is signed in with Firebase
                    Task {
                        await self?.handleFirebaseSignIn(firebaseUser)
                    }
                } else {
                    print("🔐 No Firebase user, logging out")
                    // User is signed out
                    self?.logout()
                }
            }
        }
    }
    
    private func updateAuthState(userResponse: AuthResponse, token: String, realEmail: String? = nil) {
        DispatchQueue.main.async {
            self.userId = userResponse.user_id
            self.displayName = userResponse.display_name
            self.email = userResponse.email
            self.firebaseToken = token
            self.isAuthenticated = true
            
            // Store the real Gmail address if provided
            if let realEmail = realEmail {
                self.realEmail = realEmail
                print("🔐 Auth state updated - realEmail: \(realEmail)")
            }
            
            print("🔐 Auth state updated - isAuthenticated: \(self.isAuthenticated)")
            print("🔐 Auth state updated - email: \(userResponse.email ?? "nil")")
            print("🔐 Auth state updated - displayName: \(userResponse.display_name ?? "nil")")
        }
    }
    
    // Helper function to extract first name from email
    private func extractFirstNameFromEmail(_ email: String) -> String {
        print("🔍 [AuthService] extractFirstNameFromEmail called with: \(email)")
        
        // Extract the part before @ symbol
        let emailPrefix = email.components(separatedBy: "@").first ?? ""
        print("🔍 [AuthService] emailPrefix: \(emailPrefix)")
        
        // Split by common separators and take the first part
        let separators = [".", "_", "-"]
        var firstName = emailPrefix
        
        for separator in separators {
            if emailPrefix.contains(separator) {
                firstName = emailPrefix.components(separatedBy: separator).first ?? emailPrefix
                print("🔍 [AuthService] Found separator '\(separator)', firstName: \(firstName)")
                break
            }
        }
        
        // Capitalize the first letter
        let result = firstName.prefix(1).uppercased() + firstName.dropFirst().lowercased()
        print("🔍 [AuthService] Final result: \(result)")
        return result
    }
    
    private func logout() {
        DispatchQueue.main.async {
            self.userId = nil
            self.displayName = nil
            self.email = nil
            self.realEmail = nil
            self.firebaseToken = nil
            self.isAuthenticated = false
            print("🔐 Logged out - isAuthenticated: \(self.isAuthenticated)")
        }
    }
    
    // MARK: - Google Sign In
    
    @MainActor
    func signInWithGoogle() async throws -> AuthResponse {
        guard let clientID = FirebaseApp.app()?.options.clientID else {
            throw AuthError.configError
        }
        
        // Configure Google Sign In
        let config = GIDConfiguration(clientID: clientID)
        GIDSignIn.sharedInstance.configuration = config
        
        // Get the root view controller
        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let rootViewController = windowScene.windows.first?.rootViewController else {
            throw AuthError.presentationError
        }
        
        // Start Google Sign In flow
        let result = try await GIDSignIn.sharedInstance.signIn(withPresenting: rootViewController)
        
        guard let idToken = result.user.idToken?.tokenString else {
            throw AuthError.invalidCredentials
        }
        
        // Create Firebase credential
        let credential = GoogleAuthProvider.credential(
            withIDToken: idToken,
            accessToken: result.user.accessToken.tokenString
        )
        
        // Sign in with Firebase
        let authResult = try await Auth.auth().signIn(with: credential)
        
        // Get Firebase ID token
        let token = try await authResult.user.getIDToken()
        APIService.shared.setAuthToken(token)
        
        // Store the real Gmail address from Google Sign-In
        let realGmailAddress = result.user.profile?.email ?? authResult.user.email ?? ""
        print("🔍 [AuthService] Real Gmail address from Google Sign-In: \(realGmailAddress)")
        
        // Try to login first
        let signInRequest = SignInRequest(
            firebase_uid: authResult.user.uid,
            email: authResult.user.email ?? ""
        )
        
        do {
            let requestData = try JSONEncoder().encode(signInRequest)
            let authResponse: AuthResponse = try await APIService.shared.request(
                endpoint: APIConfig.Endpoints.login,
                method: "POST",
                body: requestData
            )
            
            // Login successful
            updateAuthState(userResponse: authResponse, token: token, realEmail: realGmailAddress)
            return authResponse
            
        } catch let error as APIError {
            // If login fails with notFound, try to register
            if case .notFound = error {
                // Extract first name from email for display name
                let userEmail = authResult.user.email ?? ""
                let displayName = extractFirstNameFromEmail(userEmail)
                
                // Register the user
                let signUpRequest = SignUpRequest(
                    firebase_uid: authResult.user.uid,
                    display_name: displayName,
                    email: userEmail
                )
                
                let registerData = try JSONEncoder().encode(signUpRequest)
                let authResponse: AuthResponse = try await APIService.shared.request(
                    endpoint: APIConfig.Endpoints.register,
                    method: "POST",
                    body: registerData
                )
                
                // Registration successful
                updateAuthState(userResponse: authResponse, token: token, realEmail: realGmailAddress)
                return authResponse
            }
            
            // If error is not notFound, rethrow it
            throw error
        }
    }
    
    // MARK: - Email Password Authentication
    
    @MainActor
    func signUpWithEmail(email: String, password: String, displayName: String) async throws -> AuthResponse {
        // 1. Create Firebase user
        let authResult = try await Auth.auth().createUser(withEmail: email, password: password)
        
        // 2. Update Firebase profile
        let changeRequest = authResult.user.createProfileChangeRequest()
        changeRequest.displayName = displayName
        try await changeRequest.commitChanges()
        
        // 3. Get Firebase ID token
        let token = try await authResult.user.getIDToken()
        
        // 4. Register with backend
        let signUpRequest = SignUpRequest(
            firebase_uid: authResult.user.uid,
            display_name: displayName,
            email: email
        )
        
        APIService.shared.setAuthToken(token)
        
        let requestData = try JSONEncoder().encode(signUpRequest)
        let authResponse: AuthResponse = try await APIService.shared.request(
            endpoint: APIConfig.Endpoints.register,
            method: "POST",
            body: requestData
        )
        
        // 5. Update local user state
        updateAuthState(userResponse: authResponse, token: token)
        
        return authResponse
    }
    
    @MainActor
    func signInWithEmail(email: String, password: String) async throws -> AuthResponse {
        // 1. Sign in with Firebase
        let authResult = try await Auth.auth().signIn(withEmail: email, password: password)
        
        // 2. Get Firebase ID token
        let token = try await authResult.user.getIDToken()
        
        // 3. Sign in with backend
        let signInRequest = SignInRequest(
            firebase_uid: authResult.user.uid,
            email: email
        )
        
        APIService.shared.setAuthToken(token)
        
        let requestData = try JSONEncoder().encode(signInRequest)
        let authResponse: AuthResponse = try await APIService.shared.request(
            endpoint: APIConfig.Endpoints.login,
            method: "POST",
            body: requestData
        )
        
        // 4. Update local user state
        updateAuthState(userResponse: authResponse, token: token)
        
        return authResponse
    }
    
    @MainActor
    func signOut() async throws {
        // 1. Sign out from Firebase
        try Auth.auth().signOut()
        
        // 2. Sign out from Google
        GIDSignIn.sharedInstance.signOut()
        
        // 3. Call backend signout
        if isAuthenticated {
            do {
                struct EmptyResponse: Codable {}
                let _: EmptyResponse = try await APIService.shared.request(
                    endpoint: APIConfig.Endpoints.signout,
                    method: "POST"
                )
            } catch {
                print("Backend signout error: \(error)")
                // Continue with local signout even if backend fails
            }
        }
        
        // 4. Clear local state
        APIService.shared.clearAuthToken()
        logout()
    }
    
    @MainActor
    private func handleFirebaseSignIn(_ firebaseUser: FirebaseAuth.User) async {
        do {
            // Get fresh token
            let token = try await firebaseUser.getIDToken(forcingRefresh: true)
            
            // Try to get user profile from backend
            APIService.shared.setAuthToken(token)
            
            let userResponse: UserResponse = try await APIService.shared.request(
                endpoint: APIConfig.Endpoints.profile,
                method: "GET"
            )
            
            // Convert UserResponse to AuthResponse for consistency
            let authResponse = AuthResponse(
                user_id: userResponse.id,
                display_name: userResponse.display_name,
                email: userResponse.email,
                message: "Authenticated successfully"
            )
            
            // Use Firebase user's email as realEmail to preserve Gmail username
            let realEmail = firebaseUser.email ?? userResponse.email
            updateAuthState(userResponse: authResponse, token: token, realEmail: realEmail)
            
        } catch {
            print("Failed to authenticate with backend: \(error)")
            // Sign out from Firebase if backend auth fails
            try? await signOut()
        }
    }
    
    // MARK: - Password Reset
    
    @MainActor
    func sendPasswordResetEmail(email: String) async throws {
        try await Auth.auth().sendPasswordReset(withEmail: email)
    }
    
    // MARK: - User Profile
    
    func getCurrentUser() async throws -> UserResponse {
        let userResponse: UserResponse = try await APIService.shared.request(
            endpoint: APIConfig.Endpoints.profile,
            method: "GET"
        )
        return userResponse
    }
    
    func refreshToken() async throws {
        guard let currentUser = Auth.auth().currentUser else {
            throw AuthError.notAuthenticated
        }
        
        let token = try await currentUser.getIDToken(forcingRefresh: true)
        APIService.shared.setAuthToken(token)
        firebaseToken = token
    }
}

// MARK: - Auth Errors

enum AuthError: Error, LocalizedError {
    case notAuthenticated
    case invalidCredentials
    case userNotFound
    case emailAlreadyInUse
    case weakPassword
    case networkError
    case configError
    case presentationError
    case unknown(String)
    
    var errorDescription: String? {
        switch self {
        case .notAuthenticated:
            return "User is not authenticated"
        case .invalidCredentials:
            return "Invalid email or password"
        case .userNotFound:
            return "User account not found"
        case .emailAlreadyInUse:
            return "An account with this email already exists"
        case .weakPassword:
            return "Password is too weak"
        case .networkError:
            return "Network connection error"
        case .configError:
            return "Firebase configuration error"
        case .presentationError:
            return "Could not present sign in screen"
        case .unknown(let message):
            return message
        }
    }
} 