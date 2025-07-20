//
//  SignIn.swift
//  VoiceApp
//
//  Created by Amedeo Ercole on 7/18/25.
//
import SwiftUI

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
    
    @State private var email = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var showForgotPassword = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Sign In")
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
                .disabled(isLoading || email.isEmpty || password.isEmpty)
                .padding(.top, 20)
                
                // 修改忘记密码按钮
                Button("Forgot Password?") {
                    showForgotPassword = true
                }
                .foregroundColor(.blue)
                .padding(.top, 8)
                
                // 添加分隔线
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
                
                // 添加 Google 登录按钮
                Button(action: signInWithGoogle) {
                    HStack {
                        Image(systemName: "g.circle.fill")
                            .foregroundColor(.white)
                            .font(.title2)
                        Text("Sign in with Google")
                            .font(.rajdhaniBody)
                            .foregroundColor(.white)
                    }
                    .frame(width: 280, height: 44)
                    .background(Color.red)
                    .cornerRadius(8)
                }
                .disabled(isLoading)
                
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
        .sheet(isPresented: $showForgotPassword) {
            ForgotPasswordView()
        }
    }
    
    private func signIn() {
        isLoading = true
        showError = false
        errorMessage = ""
        
        Task {
            do {
                print("📧 Starting email sign in...")
                _ = try await authService.signInWithEmail(email: email, password: password)
                await MainActor.run {
                    print("📧 Email sign in completed. Auth status: \(authService.isAuthenticated)")
                    isLoading = false
                    // 检查认证状态并关闭表单
                    if authService.isAuthenticated {
                        print("📧 Dismissing sign in form...")
                        dismiss()
                    }
                }
            } catch {
                await MainActor.run {
                    print("📧 Email sign in failed: \(error)")
                    errorMessage = error.localizedDescription
                    showError = true
                    isLoading = false
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
                print("🔴 Starting Google sign in...")
                _ = try await authService.signInWithGoogle()
                await MainActor.run {
                    print("🔴 Google sign in completed. Auth status: \(authService.isAuthenticated)")
                    isLoading = false
                    // 检查认证状态并关闭表单
                    if authService.isAuthenticated {
                        print("🔴 Dismissing sign in form...")
                        dismiss()
                    }
                }
            } catch {
                await MainActor.run {
                    print("🔴 Google sign in failed: \(error)")
                    errorMessage = error.localizedDescription
                    showError = true
                    isLoading = false
                }
            }
        }
    }
}

// MARK: - Register Form
struct RegisterFormView: View {
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
                Text("Register")
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
        !email.isEmpty && 
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
                    // 检查认证状态并关闭表单
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

#Preview {
    SignIn()
}
