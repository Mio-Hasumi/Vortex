//
//  SignIn.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/18/25.
//
import SwiftUI

// MARK: - Auth Method Enum
enum AuthMethod: String, CaseIterable {
    case email = "Email"
    case phone = "Phone"
}

struct SignIn: View {
    @ObservedObject private var authService = AuthService.shared
    @State private var isShowingSignInForm = false
    @State private var isShowingRegisterForm = false
    
    var body: some View {
        ZStack {
            // — Orb —
            Image("orb")
                .resizable()
                .aspectRatio(contentMode: .fill)
                .frame(width: 288, height: 289)
                .clipped()
                .shadow(radius: 4.7)

            Text("VORTEX")
                .font(.rajdhaniTitle)
                .foregroundColor(.white)
                .shadow(radius: 4)

            VStack {
                Spacer()                // fills all space above
                HeaderAuth(
                    onSignInTapped: { isShowingSignInForm = true },
                    onRegisterTapped: { isShowingRegisterForm = true }
                )
                    .padding(.bottom, 100)  // can move lower/higher
            }
        }
        .frame(width: 450, height: 930)
        .background(Color.black)
        .cornerRadius(39)
        .sheet(isPresented: $isShowingSignInForm) {
            SignInFormView()
        }
        .sheet(isPresented: $isShowingRegisterForm) {
            RegisterFormView()
        }
        .onAppear {
            print("👀 SignIn view onAppear, isAuthenticated = \(authService.isAuthenticated)")
        }
    }
}

struct HeaderAuth: View {
    let onSignInTapped: () -> Void
    let onRegisterTapped: () -> Void
    
    private let buttonWidth: CGFloat = (324 - 12) / 2

    var body: some View {
        HStack(spacing: 12) {
            // Sign‑In button
            Button(action: onSignInTapped) {
            Text("Sign in")
                .font(.rajdhaniBody)
                .foregroundColor(Color(red: 0.12, green: 0.12, blue: 0.12))
                .frame(width: buttonWidth, height: 42)
                .background(Color(red: 0.89, green: 0.89, blue: 0.89))
                .cornerRadius(8)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color(red: 0.46, green: 0.46, blue: 0.46), lineWidth: 0.5)
                )
            }

            // Register button
            Button(action: onRegisterTapped) {
            Text("Register")
                .font(.rajdhaniBody)
                .foregroundColor(Color(red: 0.96, green: 0.96, blue: 0.96))
                .frame(width: buttonWidth, height: 42)
                .background(Color(red: 0.17, green: 0.17, blue: 0.17))
                .cornerRadius(8)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color(red: 0.17, green: 0.17, blue: 0.17), lineWidth: 0.5)
                )
            }
        }
        .frame(width: 324, height: 125)
    }
}

// MARK: - Sign In Form
struct SignInFormView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    
    @State private var selectedOption: SignInOption = .email
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var showSignInForm = false
    
    enum SignInOption: String, CaseIterable {
        case email = "Email"
        case phone = "Phone Number"
    }
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Sign In")
                    .font(.rajdhaniTitle)
                    .foregroundColor(.white)
                    .padding(.top, 40)
                
                Text("Choose how you'd like to sign in:")
                    .font(.rajdhaniBody)
                    .foregroundColor(.gray)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
                
                // Sign In Options
                VStack(spacing: 16) {
                    ForEach(SignInOption.allCases, id: \.self) { option in
                        Button(action: {
                            selectedOption = option
                        }) {
                            HStack {
                                Text(option.rawValue)
                                    .font(.rajdhaniBody)
                                    .foregroundColor(.white)
                                Spacer()
                                if selectedOption == option {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(.blue)
                                }
                            }
                            .padding()
                            .background(selectedOption == option ? Color.blue.opacity(0.3) : Color(red: 0.1, green: 0.1, blue: 0.1))
                            .cornerRadius(8)
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(selectedOption == option ? Color.blue : Color(red: 0.3, green: 0.3, blue: 0.3), lineWidth: 1)
                            )
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
                .padding(.horizontal, 40)
                
                if showError {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .font(.caption)
                        .padding(.horizontal, 40)
                }
                
                // Continue Button
                Button(action: continueWithSelectedOption) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(0.8)
                        }
                        Text(isLoading ? "Processing..." : "Continue")
                            .font(.rajdhaniBody)
                            .foregroundColor(.white)
                    }
                    .frame(width: 280, height: 44)
                    .background(Color.blue)
                    .cornerRadius(8)
                }
                .disabled(isLoading)
                .padding(.top, 20)
                
                Spacer()
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                }
            }
            .sheet(isPresented: $showSignInForm) {
                switch selectedOption {
                case .email:
                    EmailSignInView()
                case .phone:
                    PhoneSignInView()
                }
            }
        }
    }
    
    private func continueWithSelectedOption() {
        showSignInForm = true
    }
}

// MARK: - Register Form
struct RegisterFormView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    
    @State private var selectedOption: RegistrationOption = .email
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var showRegistrationForm = false
    
    enum RegistrationOption: String, CaseIterable {
        case email = "Email"
        case phone = "Phone Number"
    }
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Create Account")
                    .font(.rajdhaniTitle)
                    .foregroundColor(.white)
                    .padding(.top, 40)
                
                Text("Choose how you'd like to register:")
                    .font(.rajdhaniBody)
                    .foregroundColor(.gray)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
                
                // Registration Options
                VStack(spacing: 16) {
                    ForEach(RegistrationOption.allCases, id: \.self) { option in
                        Button(action: {
                            selectedOption = option
                        }) {
                            HStack {
                                Text(option.rawValue)
                                    .font(.rajdhaniBody)
                                    .foregroundColor(.white)
                                Spacer()
                                if selectedOption == option {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(.blue)
                                }
                            }
                            .padding()
                            .background(selectedOption == option ? Color.blue.opacity(0.3) : Color(red: 0.1, green: 0.1, blue: 0.1))
                            .cornerRadius(8)
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(selectedOption == option ? Color.blue : Color(red: 0.3, green: 0.3, blue: 0.3), lineWidth: 1)
                            )
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
                .padding(.horizontal, 40)
                
                if showError {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .font(.caption)
                        .padding(.horizontal, 40)
                }
                
                // Continue Button
                Button(action: continueWithSelectedOption) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(0.8)
                        }
                        Text(isLoading ? "Processing..." : "Continue")
                            .font(.rajdhaniBody)
                            .foregroundColor(.white)
                    }
                    .frame(width: 280, height: 44)
                    .background(Color.blue)
                    .cornerRadius(8)
                }
                .disabled(isLoading)
                .padding(.top, 20)
                
                Spacer()
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                }
            }
            .sheet(isPresented: $showRegistrationForm) {
                switch selectedOption {
                case .email:
                    EmailRegistrationView()
                case .phone:
                    PhoneRegistrationView()
                }
            }
        }
    }
    
    private func continueWithSelectedOption() {
        showRegistrationForm = true
    }
}

// MARK: - Email Registration View
struct EmailRegistrationView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    
    @State private var email = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var displayName = ""
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Register with Email")
                    .font(.rajdhaniTitle)
                    .foregroundColor(.white)
                    .padding(.top, 40)
                
                VStack(spacing: 16) {
                    TextField("Display Name", text: $displayName)
                        .textFieldStyle(CustomTextFieldStyle())
                    
                    TextField("Email", text: $email)
                        .textFieldStyle(CustomTextFieldStyle())
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                    
                    SecureField("Password", text: $password)
                        .textFieldStyle(CustomTextFieldStyle())
                    
                    SecureField("Confirm Password", text: $confirmPassword)
                        .textFieldStyle(CustomTextFieldStyle())
                }
                .padding(.horizontal, 40)
                
                if showError {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .font(.caption)
                        .padding(.horizontal, 40)
                }
                
                Button(action: register) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(0.8)
                        }
                        Text(isLoading ? "Creating Account..." : "Register")
                            .font(.rajdhaniBody)
                            .foregroundColor(.white)
                    }
                    .frame(width: 280, height: 44)
                    .background(Color.blue)
                    .cornerRadius(8)
                }
                .disabled(isLoading || !isFormValid)
                .padding(.top, 20)
                
                // Add separator line
                HStack {
                    Rectangle()
                        .frame(height: 1)
                        .foregroundColor(.gray.opacity(0.3))
                    Text("OR")
                        .foregroundColor(.gray)
                        .font(.caption)
                    Rectangle()
                        .frame(height: 1)
                        .foregroundColor(.gray.opacity(0.3))
                }
                .padding(.horizontal, 40)
                .padding(.vertical, 20)
                
                // Add Google sign up button
                Button(action: signUpWithGoogle) {
                    HStack(spacing: 12) {
                        Image("google_logo")
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                            .frame(width: 18, height: 18)
                        
                        Text("Sign up with Google")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(Color(red: 60/255, green: 64/255, blue: 67/255))
                    }
                    .frame(width: 280, height: 44)
                    .background(Color.white)
                    .cornerRadius(4)
                    .overlay(
                        RoundedRectangle(cornerRadius: 4)
                            .stroke(Color(red: 218/255, green: 220/255, blue: 224/255), lineWidth: 1)
                    )
                }
                .disabled(isLoading)
                
                Spacer()
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Back") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                }
            }
        }
    }
    
    private var isFormValid: Bool {
        return !email.isEmpty && 
        !password.isEmpty && 
        !displayName.isEmpty && 
        password == confirmPassword &&
        password.count >= 6
    }
    
    private func register() {
        guard password == confirmPassword else {
            errorMessage = "Passwords don't match"
            showError = true
            return
        }
        
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                _ = try await authService.signUpWithEmail(
                    email: email,
                    password: password,
                    displayName: displayName
                )
                
                await MainActor.run {
                    isLoading = false
                    if authService.isAuthenticated {
                        dismiss()
                    }
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showError = true
                    isLoading = false
                }
            }
        }
    }
    
    private func signUpWithGoogle() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                _ = try await authService.signInWithGoogle()
                await MainActor.run {
                    isLoading = false
                    if authService.isAuthenticated {
                        dismiss()
                    }
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showError = true
                    isLoading = false
                }
            }
        }
    }
}

// MARK: - Phone Registration View
struct PhoneRegistrationView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    
    @State private var phoneNumber = ""
    @State private var verificationCode = ""
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var currentStep: PhoneRegistrationStep = .phoneInput
    
    enum PhoneRegistrationStep {
        case phoneInput
        case codeVerification
    }
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Register with Phone")
                    .font(.rajdhaniTitle)
                    .foregroundColor(.white)
                    .padding(.top, 40)
                
                switch currentStep {
                case .phoneInput:
                    phoneInputView
                case .codeVerification:
                    codeVerificationView
                }
                
                Spacer()
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Back") {
                        if currentStep == .phoneInput {
                            dismiss()
                        } else {
                            currentStep = .phoneInput
                        }
                    }
                    .foregroundColor(.white)
                }
            }
        }
    }
    
    private var phoneInputView: some View {
        VStack(spacing: 20) {
            Text("Enter your phone number")
                .font(.rajdhaniBody)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            TextField("Phone Number", text: $phoneNumber)
                .textFieldStyle(CustomTextFieldStyle())
                .keyboardType(.phonePad)
                .onChange(of: phoneNumber) { newValue in
                    if isPhoneNumber(newValue) {
                        phoneNumber = formatPhoneNumber(newValue)
                    }
                }
                .padding(.horizontal, 40)
            
            Text("Enter your phone number (e.g., 555-123-4567)")
                .font(.caption)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            Text("Make sure notifications are enabled to receive SMS verification codes")
                .font(.caption)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            if showError {
                Text(errorMessage)
                    .foregroundColor(.red)
                    .font(.caption)
                    .padding(.horizontal, 40)
            }
            
            Button(action: sendVerificationCode) {
                HStack {
                    if isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            .scaleEffect(0.8)
                    }
                    Text(isLoading ? "Sending..." : "Send Verification Code")
                        .font(.rajdhaniBody)
                        .foregroundColor(.white)
                }
                .frame(width: 280, height: 44)
                .background(Color.blue)
                .cornerRadius(8)
            }
            .disabled(isLoading || !isValidPhoneNumber)
            .padding(.top, 20)
        }
    }
    
    private var codeVerificationView: some View {
        VStack(spacing: 20) {
            Text("Enter the 6-digit code sent to \(phoneNumber)")
                .font(.rajdhaniBody)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            TextField("Verification Code", text: $verificationCode)
                .textFieldStyle(CustomTextFieldStyle())
                .keyboardType(.numberPad)
                .padding(.horizontal, 40)
            
            if showError {
                Text(errorMessage)
                    .foregroundColor(.red)
                    .font(.caption)
                    .padding(.horizontal, 40)
            }
            
            Button(action: verifyCode) {
                HStack {
                    if isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            .scaleEffect(0.8)
                    }
                    Text(isLoading ? "Verifying..." : "Verify Code")
                        .font(.rajdhaniBody)
                        .foregroundColor(.white)
                }
                .frame(width: 280, height: 44)
                .background(Color.blue)
                .cornerRadius(8)
            }
            .disabled(isLoading || verificationCode.count != 6)
            .padding(.top, 20)
            
            Button("Resend Code") {
                sendVerificationCode()
            }
            .foregroundColor(.blue)
            .disabled(isLoading)
        }
    }
    
    private var isValidPhoneNumber: Bool {
        let cleaned = phoneNumber.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
        // Allow 10-15 digits (US numbers and international numbers)
        return cleaned.count >= 10 && cleaned.count <= 15
    }
    
    private func isPhoneNumber(_ input: String) -> Bool {
        let cleaned = input.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
        return cleaned.count >= 10 && cleaned.count <= 15
    }
    
    private func formatPhoneNumber(_ phone: String) -> String {
        let cleaned = phone.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
        let mask = "(XXX) XXX-XXXX"
        var result = ""
        var index = cleaned.startIndex
        for ch in mask where index < cleaned.endIndex {
            if ch == "X" {
                result.append(cleaned[index])
                index = cleaned.index(after: index)
            } else {
                result.append(ch)
            }
        }
        return result
    }
    
    // Convert phone number to E.164 format for Firebase
    private func formatPhoneNumberForFirebase(_ phone: String) -> String {
        // If it already has a + prefix, return as is
        if phone.hasPrefix("+") {
            return phone
        }
        
        let cleaned = phone.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
        
        // If it's a US number (10 digits), add +1
        if cleaned.count == 10 {
            return "+1\(cleaned)"
        }
        // If it already has country code (11+ digits starting with 1), add +
        else if cleaned.count >= 11 && cleaned.hasPrefix("1") {
            return "+\(cleaned)"
        }
        // If it has other country code, add +
        else if cleaned.count >= 10 {
            return "+\(cleaned)"
        }
        
        // Fallback - return as is with +
        return "+\(cleaned)"
    }
    
    private func sendVerificationCode() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                // Convert to E.164 format for Firebase
                let firebasePhoneNumber = formatPhoneNumberForFirebase(phoneNumber)
                print("📱 Sending verification to Firebase format: \(firebasePhoneNumber)")
                
                try await authService.sendPhoneVerificationCode(phoneNumber: firebasePhoneNumber)
                await MainActor.run {
                    isLoading = false
                    currentStep = .codeVerification
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    
                    // Provide user-friendly error messages
                    if let authError = error as? AuthError {
                        switch authError {
                        case .phoneVerificationFailed:
                            errorMessage = "Phone verification failed. Please check your phone number and try again."
                        case .unknown(let message):
                            if message.contains("notification") || message.contains("NOTIFICATION_NOT_FORWARDED") {
                                errorMessage = "Please enable notifications in Settings to receive SMS verification codes."
                            } else if message.contains("Invalid format") || message.contains("ERROR_INVALID_PHONE_NUMBER") {
                                errorMessage = "Please enter a valid phone number with country code (e.g., +1 for US)."
                            } else {
                                errorMessage = message
                            }
                        default:
                            errorMessage = error.localizedDescription
                        }
                    } else {
                        errorMessage = error.localizedDescription
                    }
                    
                    showError = true
                }
            }
        }
    }
    
    private func verifyCode() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                // Convert to E.164 format for Firebase
                let firebasePhoneNumber = formatPhoneNumberForFirebase(phoneNumber)
                print("📱 Completing registration with Firebase format: \(firebasePhoneNumber)")
                
                // Generate display name from phone number (like Gmail registration does)
                let displayName = generateDisplayNameFromPhone(phoneNumber)
                
                _ = try await authService.verifyPhoneCodeAndSignUp(
                    phoneNumber: firebasePhoneNumber,
                    verificationCode: verificationCode,
                    displayName: displayName
                )
                
                await MainActor.run {
                    isLoading = false
                    if authService.isAuthenticated {
                        dismiss()
                    }
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showError = true
                    isLoading = false
                }
            }
        }
    }
    
    // Generate a display name from phone number (similar to Gmail registration)
    private func generateDisplayNameFromPhone(_ phone: String) -> String {
        let cleaned = phone.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
        
        // Use last 4 digits as display name
        if cleaned.count >= 4 {
            let lastFour = String(cleaned.suffix(4))
            return "User\(lastFour)"
        }
        
        // Fallback
        return "User"
    }
}

// MARK: - Email Sign In View
struct EmailSignInView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    
    @State private var email = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var showForgotPassword = false
    @State private var showCreateAccount = false
    @State private var displayName = ""
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Sign In with Email")
                    .font(.rajdhaniTitle)
                    .foregroundColor(.white)
                    .padding(.top, 40)
                
                VStack(spacing: 16) {
                    TextField("Email", text: $email)
                        .textFieldStyle(CustomTextFieldStyle())
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                    
                    SecureField("Password", text: $password)
                        .textFieldStyle(CustomTextFieldStyle())
                }
                .padding(.horizontal, 40)
                
                if showError {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .font(.caption)
                        .padding(.horizontal, 40)
                    
                    // Show create account option when sign-in fails
                    if !isLoading {
                        VStack(spacing: 12) {
                            Text("Don't have an account?")
                                .font(.caption)
                                .foregroundColor(.gray)
                            
                            Button("Create Account with these credentials") {
                                showCreateAccount = true
                            }
                            .foregroundColor(.blue)
                            .font(.caption)
                        }
                        .padding(.top, 8)
                    }
                }
                
                Button(action: signIn) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(0.8)
                        }
                        Text(isLoading ? "Signing In..." : "Sign In")
                            .font(.rajdhaniBody)
                            .foregroundColor(.white)
                    }
                    .frame(width: 280, height: 44)
                    .background(Color.blue)
                    .cornerRadius(8)
                }
                .disabled(isLoading || !isFormValid)
                .padding(.top, 20)
                
                // Forgot password button
                Button("Forgot Password?") {
                    showForgotPassword = true
                }
                .foregroundColor(.blue)
                .padding(.top, 8)
                
                // Add separator line
                HStack {
                    Rectangle()
                        .frame(height: 1)
                        .foregroundColor(.gray.opacity(0.3))
                    Text("OR")
                        .foregroundColor(.gray)
                        .font(.caption)
                    Rectangle()
                        .frame(height: 1)
                        .foregroundColor(.gray.opacity(0.3))
                }
                .padding(.horizontal, 40)
                .padding(.vertical, 20)
                
                // Add Google sign in button
                Button(action: signInWithGoogle) {
                    HStack(spacing: 12) {
                        Image("google_logo")
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                            .frame(width: 18, height: 18)
                        
                        Text("Sign in with Google")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(Color(red: 60/255, green: 64/255, blue: 67/255))
                    }
                    .frame(width: 280, height: 44)
                    .background(Color.white)
                    .cornerRadius(4)
                    .overlay(
                        RoundedRectangle(cornerRadius: 4)
                            .stroke(Color(red: 218/255, green: 220/255, blue: 224/255), lineWidth: 1)
                    )
                }
                .disabled(isLoading)
                
                Spacer()
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Back") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                }
            }
            .sheet(isPresented: $showForgotPassword) {
                ForgotPasswordView()
            }
            .sheet(isPresented: $showCreateAccount) {
                CreateAccountFromSignInView(
                    email: email,
                    password: password,
                    onAccountCreated: {
                        showCreateAccount = false
                        dismiss()
                    }
                )
            }
        }
    }
    
    private var isFormValid: Bool {
        return !email.isEmpty && !password.isEmpty
    }
    
    private func signIn() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                _ = try await authService.signInWithEmail(email: email, password: password)
                
                await MainActor.run {
                    isLoading = false
                    if authService.isAuthenticated {
                        dismiss()
                    }
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    errorMessage = error.localizedDescription
                    showError = true
                }
            }
        }
    }
    
    private func signInWithGoogle() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                _ = try await authService.signInWithGoogle()
                await MainActor.run {
                    isLoading = false
                    if authService.isAuthenticated {
                        dismiss()
                    }
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showError = true
                    isLoading = false
                }
            }
        }
    }
}

// MARK: - Phone Sign In View
struct PhoneSignInView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    
    @State private var phoneNumber = ""
    @State private var verificationCode = ""
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var currentStep: PhoneSignInStep = .phoneInput
    @State private var showCreateAccount = false
    
    enum PhoneSignInStep {
        case phoneInput
        case codeVerification
    }
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Sign In with Phone")
                    .font(.rajdhaniTitle)
                    .foregroundColor(.white)
                    .padding(.top, 40)
                
                switch currentStep {
                case .phoneInput:
                    phoneInputView
                case .codeVerification:
                    codeVerificationView
                }
                
                Spacer()
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Back") {
                        if currentStep == .phoneInput {
                            dismiss()
                        } else {
                            currentStep = .phoneInput
                        }
                    }
                    .foregroundColor(.white)
                }
            }
            .sheet(isPresented: $showCreateAccount) {
                CreateAccountFromPhoneSignInView(
                    phoneNumber: phoneNumber,
                    onAccountCreated: {
                        showCreateAccount = false
                        dismiss()
                    }
                )
            }
        }
    }
    
    private var phoneInputView: some View {
        VStack(spacing: 20) {
            Text("Enter your phone number")
                .font(.rajdhaniBody)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            TextField("Phone Number", text: $phoneNumber)
                .textFieldStyle(CustomTextFieldStyle())
                .keyboardType(.phonePad)
                .onChange(of: phoneNumber) { newValue in
                    if isPhoneNumber(newValue) {
                        phoneNumber = formatPhoneNumber(newValue)
                    }
                }
                .padding(.horizontal, 40)
            
            Text("Enter your phone number (e.g., 555-123-4567)")
                .font(.caption)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            Text("Make sure notifications are enabled to receive SMS verification codes")
                .font(.caption)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            if showError {
                Text(errorMessage)
                    .foregroundColor(.red)
                    .font(.caption)
                    .padding(.horizontal, 40)
            }
            
            Button(action: sendVerificationCode) {
                HStack {
                    if isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            .scaleEffect(0.8)
                    }
                    Text(isLoading ? "Sending..." : "Send Verification Code")
                        .font(.rajdhaniBody)
                        .foregroundColor(.white)
                }
                .frame(width: 280, height: 44)
                .background(Color.blue)
                .cornerRadius(8)
            }
            .disabled(isLoading || !isValidPhoneNumber)
            .padding(.top, 20)
        }
    }
    
    private var codeVerificationView: some View {
        VStack(spacing: 20) {
            Text("Enter the 6-digit code sent to \(phoneNumber)")
                .font(.rajdhaniBody)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            TextField("Verification Code", text: $verificationCode)
                .textFieldStyle(CustomTextFieldStyle())
                .keyboardType(.numberPad)
                .padding(.horizontal, 40)
            
            if showError {
                Text(errorMessage)
                    .foregroundColor(.red)
                    .font(.caption)
                    .padding(.horizontal, 40)
                
                // Show create account option when verification fails
                if !isLoading {
                    VStack(spacing: 12) {
                        Text("Don't have an account?")
                            .font(.caption)
                            .foregroundColor(.gray)
                        
                        Button("Create Account with this phone number") {
                            showCreateAccount = true
                        }
                        .foregroundColor(.blue)
                        .font(.caption)
                    }
                    .padding(.top, 8)
                }
            }
            
            Button(action: verifyCode) {
                HStack {
                    if isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            .scaleEffect(0.8)
                    }
                    Text(isLoading ? "Verifying..." : "Verify Code")
                        .font(.rajdhaniBody)
                        .foregroundColor(.white)
                }
                .frame(width: 280, height: 44)
                .background(Color.blue)
                .cornerRadius(8)
            }
            .disabled(isLoading || verificationCode.count != 6)
            .padding(.top, 20)
            
            Button("Resend Code") {
                sendVerificationCode()
            }
            .foregroundColor(.blue)
            .disabled(isLoading)
        }
    }
    
    private var isValidPhoneNumber: Bool {
        let cleaned = phoneNumber.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
        return cleaned.count >= 10 && cleaned.count <= 15
    }
    
    private func sendVerificationCode() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                let firebasePhoneNumber = formatPhoneNumberForFirebase(phoneNumber)
                print("📱 Sending verification to Firebase format: \(firebasePhoneNumber)")
                
                try await authService.sendPhoneVerificationCode(phoneNumber: firebasePhoneNumber)
                await MainActor.run {
                    isLoading = false
                    currentStep = .codeVerification
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    
                    if let authError = error as? AuthError {
                        switch authError {
                        case .phoneVerificationFailed:
                            errorMessage = "Phone verification failed. Please check your phone number and try again."
                        case .unknown(let message):
                            if message.contains("notification") || message.contains("NOTIFICATION_NOT_FORWARDED") {
                                errorMessage = "Please enable notifications in Settings to receive SMS verification codes."
                            } else if message.contains("Invalid format") || message.contains("ERROR_INVALID_PHONE_NUMBER") {
                                errorMessage = "Please enter a valid phone number with country code (e.g., +1 for US)."
                            } else {
                                errorMessage = message
                            }
                        default:
                            errorMessage = error.localizedDescription
                        }
                    } else {
                        errorMessage = error.localizedDescription
                    }
                    
                    showError = true
                }
            }
        }
    }
    
    private func verifyCode() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                let firebasePhoneNumber = formatPhoneNumberForFirebase(phoneNumber)
                print("📱 Verifying code with Firebase format: \(firebasePhoneNumber)")
                
                _ = try await authService.verifyPhoneCodeAndSignIn(
                    phoneNumber: firebasePhoneNumber,
                    verificationCode: verificationCode
                )
                
                await MainActor.run {
                    isLoading = false
                    if authService.isAuthenticated {
                        dismiss()
                    }
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showError = true
                    isLoading = false
                }
            }
        }
    }
}

// MARK: - Helper Functions

private func isPhoneNumber(_ input: String) -> Bool {
    let cleaned = input.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
    return cleaned.count >= 10 && cleaned.count <= 15
}

private func formatPhoneNumber(_ phone: String) -> String {
    let cleaned = phone.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
    let mask = "(XXX) XXX-XXXX"
    var result = ""
    var index = cleaned.startIndex
    for ch in mask where index < cleaned.endIndex {
        if ch == "X" {
            result.append(cleaned[index])
            index = cleaned.index(after: index)
        } else {
            result.append(ch)
        }
    }
    return result
}

// Convert phone number to E.164 format for Firebase
private func formatPhoneNumberForFirebase(_ phone: String) -> String {
    // If it already has a + prefix, return as is
    if phone.hasPrefix("+") {
        return phone
    }
    
    let cleaned = phone.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
    
    // If it's a US number (10 digits), add +1
    if cleaned.count == 10 {
        return "+1\(cleaned)"
    }
    // If it already has country code (11+ digits starting with 1), add +
    else if cleaned.count >= 11 && cleaned.hasPrefix("1") {
        return "+\(cleaned)"
    }
    // If it has other country code, add +
    else if cleaned.count >= 10 {
        return "+\(cleaned)"
    }
    
    // Fallback - return as is with +
    return "+\(cleaned)"
}

// MARK: - Custom Text Field Style
struct CustomTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding(12)
            .background(Color(red: 0.1, green: 0.1, blue: 0.1))
            .foregroundColor(.white)
            .cornerRadius(8)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color(red: 0.3, green: 0.3, blue: 0.3), lineWidth: 1)
            )
    }
}

// MARK: - Forgot Password Form
struct ForgotPasswordView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    
    @State private var email = ""
    @State private var isLoading = false
    @State private var message = ""
    @State private var showMessage = false
    @State private var isSuccess = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Reset Password")
                    .font(.rajdhaniTitle)
                    .foregroundColor(.white)
                    .padding(.top, 40)
                
                Text("Enter your email address and we'll send you a link to reset your password.")
                    .font(.rajdhaniBody)
                    .foregroundColor(.gray)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
                
                TextField("Email", text: $email)
                    .textFieldStyle(CustomTextFieldStyle())
                    .keyboardType(.emailAddress)
                    .autocapitalization(.none)
                    .padding(.horizontal, 40)
                
                if showMessage {
                    Text(message)
                        .foregroundColor(isSuccess ? .green : .red)
                        .font(.caption)
                        .padding(.horizontal, 40)
                        .multilineTextAlignment(.center)
                }
                
                Button(action: sendResetEmail) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(0.8)
                        }
                        Text(isLoading ? "Sending..." : "Send Reset Email")
                            .font(.rajdhaniBody)
                            .foregroundColor(.white)
                    }
                    .frame(width: 280, height: 44)
                    .background(email.isEmpty ? Color.gray : Color.blue)
                    .cornerRadius(8)
                }
                .disabled(isLoading || email.isEmpty)
                .padding(.top, 20)
                
                Spacer()
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                }
            }
        }
    }
    
    private func sendResetEmail() {
        isLoading = true
        showMessage = false
        
        Task {
            do {
                try await authService.sendPasswordResetEmail(email: email)
                await MainActor.run {
                    message = "✅ Password reset email sent! Please check your inbox and follow the instructions."
                    isSuccess = true
                    showMessage = true
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    message = "❌ Failed to send reset email: \(error.localizedDescription)"
                    isSuccess = false
                    showMessage = true
                    isLoading = false
                }
            }
        }
    }
}

// MARK: - Create Account From Sign In View
struct CreateAccountFromSignInView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    
    @State private var email: String
    @State private var password: String
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var displayName = ""
    
    let onAccountCreated: () -> Void
    
    init(email: String, password: String, onAccountCreated: @escaping () -> Void) {
        self._email = State(initialValue: email)
        self._password = State(initialValue: password)
        self.onAccountCreated = onAccountCreated
    }
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Create Account with Email")
                    .font(.rajdhaniTitle)
                    .foregroundColor(.white)
                    .padding(.top, 40)
                
                VStack(spacing: 16) {
                    TextField("Display Name", text: $displayName)
                        .textFieldStyle(CustomTextFieldStyle())
                    
                    TextField("Email", text: $email)
                        .textFieldStyle(CustomTextFieldStyle())
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                    
                    SecureField("Password", text: $password)
                        .textFieldStyle(CustomTextFieldStyle())
                }
                .padding(.horizontal, 40)
                
                if showError {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .font(.caption)
                        .padding(.horizontal, 40)
                }
                
                Button(action: createAccount) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(0.8)
                        }
                        Text(isLoading ? "Creating Account..." : "Create Account")
                            .font(.rajdhaniBody)
                            .foregroundColor(.white)
                    }
                    .frame(width: 280, height: 44)
                    .background(Color.blue)
                    .cornerRadius(8)
                }
                .disabled(isLoading || !isFormValid)
                .padding(.top, 20)
                
                Spacer()
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                }
            }
        }
    }
    
    private var isFormValid: Bool {
        return !displayName.isEmpty && 
        !email.isEmpty && 
        !password.isEmpty && 
        password.count >= 6
    }
    
    private func createAccount() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                _ = try await authService.signUpWithEmail(
                    email: email,
                    password: password,
                    displayName: displayName
                )
                
                await MainActor.run {
                    isLoading = false
                    if authService.isAuthenticated {
                        onAccountCreated()
                    }
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showError = true
                    isLoading = false
                }
            }
        }
    }
}

// MARK: - Create Account From Phone Sign In View
struct CreateAccountFromPhoneSignInView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    
    @State private var phoneNumber: String
    @State private var verificationCode = ""
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var currentStep: PhoneCreateAccountStep = .codeVerification
    
    enum PhoneCreateAccountStep {
        case codeVerification
    }
    
    let onAccountCreated: () -> Void
    
    init(phoneNumber: String, onAccountCreated: @escaping () -> Void) {
        self._phoneNumber = State(initialValue: phoneNumber)
        self.onAccountCreated = onAccountCreated
    }
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Create Account with Phone")
                    .font(.rajdhaniTitle)
                    .foregroundColor(.white)
                    .padding(.top, 40)
                
                switch currentStep {
                case .codeVerification:
                    codeVerificationView
                }
                
                Spacer()
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                }
            }
        }
        .onAppear {
            // Automatically send verification code when view appears
            sendVerificationCode()
        }
    }
    
    private var codeVerificationView: some View {
        VStack(spacing: 20) {
            Text("Enter the 6-digit code sent to \(phoneNumber)")
                .font(.rajdhaniBody)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            TextField("Verification Code", text: $verificationCode)
                .textFieldStyle(CustomTextFieldStyle())
                .keyboardType(.numberPad)
                .padding(.horizontal, 40)
            
            if showError {
                Text(errorMessage)
                    .foregroundColor(.red)
                    .font(.caption)
                    .padding(.horizontal, 40)
            }
            
            Button(action: createAccount) {
                HStack {
                    if isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            .scaleEffect(0.8)
                    }
                    Text(isLoading ? "Creating Account..." : "Create Account")
                        .font(.rajdhaniBody)
                        .foregroundColor(.white)
                }
                .frame(width: 280, height: 44)
                .background(Color.blue)
                .cornerRadius(8)
            }
            .disabled(isLoading || verificationCode.count != 6)
            .padding(.top, 20)
            
            Button("Resend Code") {
                sendVerificationCode()
            }
            .foregroundColor(.blue)
            .disabled(isLoading)
        }
    }
    
    private func sendVerificationCode() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                let firebasePhoneNumber = formatPhoneNumberForFirebase(phoneNumber)
                print("📱 Sending verification to Firebase format: \(firebasePhoneNumber)")
                
                try await authService.sendPhoneVerificationCode(phoneNumber: firebasePhoneNumber)
                await MainActor.run {
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    errorMessage = error.localizedDescription
                    showError = true
                }
            }
        }
    }
    
    private func createAccount() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                let firebasePhoneNumber = formatPhoneNumberForFirebase(phoneNumber)
                print("📱 Creating account with Firebase format: \(firebasePhoneNumber)")
                
                // Generate display name from phone number (like Gmail registration does)
                let displayName = generateDisplayNameFromPhone(phoneNumber)
                
                _ = try await authService.verifyPhoneCodeAndSignUp(
                    phoneNumber: firebasePhoneNumber,
                    verificationCode: verificationCode,
                    displayName: displayName
                )
                
                await MainActor.run {
                    isLoading = false
                    if authService.isAuthenticated {
                        onAccountCreated()
                    }
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showError = true
                    isLoading = false
                }
            }
        }
    }
    
    // Generate a display name from phone number (similar to Gmail registration)
    private func generateDisplayNameFromPhone(_ phone: String) -> String {
        let cleaned = phone.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
        
        // Use last 4 digits as display name
        if cleaned.count >= 4 {
            let lastFour = String(cleaned.suffix(4))
            return "User\(lastFour)"
        }
        
        // Fallback
        return "User"
    }
    
    // Convert phone number to E.164 format for Firebase
    private func formatPhoneNumberForFirebase(_ phone: String) -> String {
        // If it already has a + prefix, return as is
        if phone.hasPrefix("+") {
            return phone
        }
        
        let cleaned = phone.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
        
        // If it's a US number (10 digits), add +1
        if cleaned.count == 10 {
            return "+1\(cleaned)"
        }
        // If it already has country code (11+ digits starting with 1), add +
        else if cleaned.count >= 11 && cleaned.hasPrefix("1") {
            return "+\(cleaned)"
        }
        // If it has other country code, add +
        else if cleaned.count >= 10 {
            return "+\(cleaned)"
        }
        
        // Fallback - return as is with +
        return "+\(cleaned)"
    }
}

#Preview {
    SignIn()
}
