import SwiftUI

struct ProfileView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    @ObservedObject private var userStatsService = UserStatsService.shared
    @State private var showEditProfile = false
    @State private var showImagePicker = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                // Profile Header
                VStack(spacing: 16) {
                    // Profile Image with Change Button
                    ZStack(alignment: .bottomTrailing) {
                        Circle()
                            .fill(
                                LinearGradient(
                                    colors: [.blue.opacity(0.8), .purple.opacity(0.8)],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .frame(width: 120, height: 120)
                            .overlay(
                                Image(systemName: "person.fill")
                                    .font(.system(size: 50))
                                    .foregroundColor(.white)
                            )
                        
                        // Profile Picture Change Button
                        Button(action: {
                            showImagePicker = true
                        }) {
                            Image(systemName: "plus.circle.fill")
                                .font(.system(size: 30))
                                .foregroundColor(.blue)
                                .background(Color.white, in: Circle())
                        }
                        .offset(x: 5, y: 5)
                    }
                    
                    VStack(spacing: 8) {
                        Text(authService.uiDisplayName)
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                        
                        // Friends and Uploads Count
                        HStack(spacing: 20) {
                            VStack(spacing: 4) {
                                Text("Friends")
                                    .font(.caption)
                                    .foregroundColor(.gray)
                                Text("\(userStatsService.friendsCount)")
                                    .font(.subheadline)
                                    .fontWeight(.semibold)
                                    .foregroundColor(.white)
                            }
                            
                            VStack(spacing: 4) {
                                Text("Uploads")
                                    .font(.caption)
                                    .foregroundColor(.gray)
                                Text("\(userStatsService.uploadsCount)")
                                    .font(.subheadline)
                                    .fontWeight(.semibold)
                                    .foregroundColor(.white)
                            }
                        }
                    }
                    
                    Button("Edit Profile") {
                        showEditProfile = true
                    }
                    .foregroundColor(.blue)
                    .padding(.top, 8)
                }
                .padding(.top, 20)
                
                // Profile Info
                VStack(spacing: 16) {
                    ProfileInfoRow(title: "Display Name", value: authService.displayName ?? "N/A")
                    ProfileInfoRow(title: "Email", value: authService.realEmail ?? authService.email ?? "N/A")
                    ProfileInfoRow(title: "Phone Number", value: userStatsService.phoneNumber ?? "Not added")
                    ProfileInfoRow(title: "Status", value: "Active")
                }
                .padding(.horizontal, 20)
                
                // Authentication Methods Section
                VStack(spacing: 16) {
                    Text("Authentication Methods")
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    
                    VStack(spacing: 12) {
                        // Email Method
                        HStack {
                            Image(systemName: "envelope.fill")
                                .foregroundColor(.blue)
                            Text("Email")
                                .foregroundColor(.gray)
                            Spacer()
                            Text(authService.realEmail ?? authService.email ?? "Not set")
                                .foregroundColor(.white)
                                .font(.caption)
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(Color.gray.opacity(0.2))
                        .cornerRadius(8)
                        
                        // Phone Method
                        HStack {
                            Image(systemName: "phone.fill")
                                .foregroundColor(.green)
                            Text("Phone")
                                .foregroundColor(.gray)
                            Spacer()
                            Text(userStatsService.phoneNumber ?? "Not set")
                                .foregroundColor(.white)
                                .font(.caption)
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(Color.gray.opacity(0.2))
                        .cornerRadius(8)
                        
                        // Gmail Method (if available)
                        if let realEmail = authService.realEmail, realEmail.contains("@gmail.com") {
                            HStack {
                                Image(systemName: "person.circle.fill")
                                    .foregroundColor(.red)
                                Text("Google Account")
                                    .foregroundColor(.gray)
                                Spacer()
                                Text("Connected")
                                    .foregroundColor(.green)
                                    .font(.caption)
                            }
                            .padding(.horizontal, 16)
                            .padding(.vertical, 8)
                            .background(Color.gray.opacity(0.2))
                            .cornerRadius(8)
                        }
                    }
                }
                .padding(.horizontal, 20)
                
                Spacer()
            }
            .background(Color.black)
            .navigationTitle("Profile")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(.blue)
                }
            }
        }
        .sheet(isPresented: $showEditProfile) {
            EditProfileView()
        }
        .sheet(isPresented: $showImagePicker) {
            ImagePickerView()
        }
        .onAppear {
            Task {
                await userStatsService.refreshStats()
            }
        }
    }
}

struct ProfileInfoRow: View {
    let title: String
    let value: String
    
    var body: some View {
        HStack {
            Text(title)
                .font(.subheadline)
                .foregroundColor(.gray)
                .frame(width: 100, alignment: .leading)
            
            Spacer()
            
            Text(value)
                .font(.subheadline)
                .foregroundColor(.white)
        }
        .padding(.vertical, 8)
    }
}

struct EditProfileView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    @State private var displayName = ""
    @State private var newEmail = ""
    @State private var newPhoneNumber = ""
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var showSuccess = false
    @State private var successMessage = ""
    @State private var showAddAuthMethod = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                ScrollView {
                    VStack(spacing: 20) {
                        // Display Name Section
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Display Name")
                                .font(.headline)
                                .foregroundColor(.white)
                            
                            TextField("Display Name", text: $displayName)
                                .textFieldStyle(CustomTextFieldStyle())
                        }
                        .padding(.horizontal, 20)
                        
                        // Add Authentication Method Section
                        VStack(alignment: .leading, spacing: 16) {
                            Text("Add Authentication Method")
                                .font(.headline)
                                .foregroundColor(.white)
                            
                            VStack(spacing: 12) {
                                TextField("Email (optional)", text: $newEmail)
                                    .textFieldStyle(CustomTextFieldStyle())
                                    .keyboardType(.emailAddress)
                                    .autocapitalization(.none)
                                
                                TextField("Phone Number (optional)", text: $newPhoneNumber)
                                    .textFieldStyle(CustomTextFieldStyle())
                                    .keyboardType(.phonePad)
                            }
                            
                            Button(action: addAuthMethod) {
                                HStack {
                                    if isLoading {
                                        ProgressView()
                                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                            .scaleEffect(0.8)
                                    }
                                    Text("Add Authentication Method")
                                        .font(.subheadline)
                                        .foregroundColor(.white)
                                }
                                .frame(maxWidth: .infinity)
                                .frame(height: 44)
                                .background(Color.blue)
                                .cornerRadius(8)
                            }
                            .disabled(isLoading || (newEmail.isEmpty && newPhoneNumber.isEmpty))
                        }
                        .padding(.horizontal, 20)
                        
                        if showError {
                            Text(errorMessage)
                                .foregroundColor(.red)
                                .font(.caption)
                                .padding(.horizontal, 20)
                        }
                        
                        if showSuccess {
                            Text(successMessage)
                                .foregroundColor(.green)
                                .font(.caption)
                                .padding(.horizontal, 20)
                        }
                    }
                }
                
                Spacer()
            }
            .background(Color.black)
            .navigationTitle("Edit Profile")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(.red)
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Save") {
                        saveChanges()
                    }
                    .foregroundColor(.blue)
                    .disabled(isLoading)
                }
            }
        }
        .onAppear {
            displayName = authService.displayName ?? ""
        }
    }
    
    private func saveChanges() {
        guard !displayName.isEmpty else {
            errorMessage = "Display name cannot be empty"
            showError = true
            return
        }
        
        isLoading = true
        showError = false
        showSuccess = false
        
        Task {
            do {
                _ = try await authService.updateDisplayName(displayName)
                
                await MainActor.run {
                    successMessage = "Display name updated successfully!"
                    showSuccess = true
                    isLoading = false
                    
                    // Dismiss after a short delay
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
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
    
    private func addAuthMethod() {
        guard !newEmail.isEmpty || !newPhoneNumber.isEmpty else {
            errorMessage = "Please provide either an email or phone number"
            showError = true
            return
        }
        
        isLoading = true
        showError = false
        showSuccess = false
        
        Task {
            do {
                _ = try await authService.addAuthMethod(
                    email: newEmail.isEmpty ? nil : newEmail,
                    phoneNumber: newPhoneNumber.isEmpty ? nil : newPhoneNumber
                )
                
                await MainActor.run {
                    successMessage = "Authentication method added successfully!"
                    showSuccess = true
                    isLoading = false
                    
                    // Clear the fields
                    newEmail = ""
                    newPhoneNumber = ""
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

#Preview {
    ProfileView()
}

// MARK: - Image Picker View
struct ImagePickerView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var selectedImage: UIImage?
    @State private var showImagePicker = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                if let selectedImage = selectedImage {
                    Image(uiImage: selectedImage)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 200, height: 200)
                        .clipShape(Circle())
                } else {
                    Image(systemName: "photo")
                        .font(.system(size: 100))
                        .foregroundColor(.gray)
                        .frame(width: 200, height: 200)
                }
                
                Text("Select Profile Picture")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                
                Text("Choose a photo from your library or take a new one")
                    .font(.body)
                    .foregroundColor(.gray)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
                
                HStack(spacing: 20) {
                    Button("Choose Photo") {
                        showImagePicker = true
                    }
                    .padding(.horizontal, 30)
                    .padding(.vertical, 12)
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                    
                    Button("Remove") {
                        selectedImage = nil
                    }
                    .padding(.horizontal, 30)
                    .padding(.vertical, 12)
                    .background(Color.red)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                    .disabled(selectedImage == nil)
                }
                
                Spacer()
            }
            .padding(.top, 40)
            .background(Color.black)
            .navigationTitle("Profile Picture")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(.red)
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Save") {
                        // TODO: Implement save profile picture logic
                        dismiss()
                    }
                    .foregroundColor(.blue)
                    .disabled(selectedImage == nil)
                }
            }
        }
        .sheet(isPresented: $showImagePicker) {
            ImagePicker(selectedImage: $selectedImage)
        }
    }
}

// MARK: - UIKit Image Picker
struct ImagePicker: UIViewControllerRepresentable {
    @Binding var selectedImage: UIImage?
    @Environment(\.dismiss) private var dismiss
    
    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.delegate = context.coordinator
        picker.sourceType = .photoLibrary
        picker.allowsEditing = true
        return picker
    }
    
    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: ImagePicker
        
        init(_ parent: ImagePicker) {
            self.parent = parent
        }
        
        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            if let editedImage = info[.editedImage] as? UIImage {
                parent.selectedImage = editedImage
            } else if let originalImage = info[.originalImage] as? UIImage {
                parent.selectedImage = originalImage
            }
            parent.dismiss()
        }
        
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.dismiss()
        }
    }
} 