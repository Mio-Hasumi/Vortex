import SwiftUI

struct ProfileView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    @ObservedObject private var userStatsService = UserStatsService.shared
    @State private var showEditProfile = false
    @State private var showImagePicker = false
    @State private var showSourceTypeSelector = false
    @State private var imagePickerSourceType: UIImagePickerController.SourceType = .photoLibrary
    @State private var currentProfileImage: UIImage?
    @State private var selectedImage: UIImage?
    @State private var isLoading = false
    @State private var showError = false
    @State private var showSuccess = false
    @State private var errorMessage = ""
    @State private var successMessage = ""
    
    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                // Profile Header
                VStack(spacing: 16) {
                    // Profile Image with Change Button
                    ZStack(alignment: .bottomTrailing) {
                        if let profileImage = currentProfileImage {
                            Image(uiImage: profileImage)
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                                .frame(width: 120, height: 120)
                                .clipShape(Circle())
                        } else if let profileImageUrl = authService.profileImageUrl, !profileImageUrl.isEmpty {
                            AsyncImage(url: URL(string: profileImageUrl)) { image in
                                image
                                    .resizable()
                                    .aspectRatio(contentMode: .fill)
                                    .frame(width: 120, height: 120)
                                    .clipShape(Circle())
                            } placeholder: {
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
                            }
                        } else {
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
                        }
                        
                        // Profile Picture Change Button
                        Button(action: {
                            showSourceTypeSelector = true
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
                    ProfileInfoRow(title: "Email", value: authService.phoneAuthNumber != nil ? "N/A" : (authService.realEmail ?? authService.email ?? "N/A"))
                    ProfileInfoRow(title: "Phone Number", value: authService.phoneAuthNumber ?? userStatsService.phoneNumber ?? "Not added")
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
                            Text(authService.phoneAuthNumber != nil ? "N/A" : (authService.realEmail ?? authService.email ?? "Not set"))
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
                            Text(authService.phoneAuthNumber ?? userStatsService.phoneNumber ?? "Not set")
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
            ImagePicker(selectedImage: $selectedImage, sourceType: imagePickerSourceType)
        }
        .actionSheet(isPresented: $showSourceTypeSelector) {
            ActionSheet(
                title: Text("Select Photo Source"),
                buttons: [
                    .default(Text("Photo Library")) {
                        imagePickerSourceType = .photoLibrary
                        showImagePicker = true
                    },
                    .default(Text("Camera")) {
                        imagePickerSourceType = .camera
                        showImagePicker = true
                    },
                    .cancel()
                ]
            )
        }
        .onChange(of: selectedImage) { newImage in
            if let image = newImage {
                currentProfileImage = image
                uploadProfilePicture(image)
            }
        }
        .alert("Success", isPresented: $showSuccess) {
            Button("OK") { }
        } message: {
            Text(successMessage)
        }
        .alert("Error", isPresented: $showError) {
            Button("OK") { }
        } message: {
            Text(errorMessage)
        }
        .onAppear {
            Task {
                await userStatsService.refreshStats()
                refreshProfileImage()
            }
        }
    }
    
    private func refreshProfileImage() {
        // If we have a profile image URL, try to load it
        if let profileImageUrl = authService.profileImageUrl, !profileImageUrl.isEmpty {
            // The AsyncImage will handle loading the image
            // We just need to ensure the URL is set
        }
    }
    
    private func uploadProfilePicture(_ image: UIImage) {
        isLoading = true
        showError = false
        showSuccess = false
        
        Task {
            do {
                let response = try await authService.uploadProfilePicture(image)
                
                await MainActor.run {
                    // Update the profile image URL in AuthService
                    authService.profileImageUrl = response.profile_image_url
                    
                    isLoading = false
                    showSuccess = true
                    successMessage = "Profile picture updated successfully!"
                    
                    // Clear the selected image after successful upload
                    selectedImage = nil
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
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var showSuccess = false
    @State private var successMessage = ""
    
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
    

}

#Preview {
    ProfileView()
}

// MARK: - Image Picker View
struct ImagePickerView: View {
    @Environment(\.dismiss) private var dismiss
    @Binding var selectedImage: UIImage?
    @State private var showImagePicker = false
    @State private var showSourceTypeSelector = false
    @State private var imagePickerSourceType: UIImagePickerController.SourceType = .photoLibrary
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var showSuccess = false
    @ObservedObject private var authService = AuthService.shared
    
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
                        showSourceTypeSelector = true
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
                
                if showError {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .font(.caption)
                        .padding(.horizontal, 20)
                }
                
                if showSuccess {
                    Text("Profile picture updated successfully!")
                        .foregroundColor(.green)
                        .font(.caption)
                        .padding(.horizontal, 20)
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
                        saveProfilePicture()
                    }
                    .foregroundColor(.blue)
                    .disabled(selectedImage == nil || isLoading)
                }
            }
        }
        .sheet(isPresented: $showImagePicker) {
            ImagePicker(selectedImage: $selectedImage, sourceType: imagePickerSourceType)
        }
        .actionSheet(isPresented: $showSourceTypeSelector) {
            ActionSheet(
                title: Text("Select Photo Source"),
                buttons: [
                    .default(Text("Photo Library")) {
                        imagePickerSourceType = .photoLibrary
                        showImagePicker = true
                    },
                    .default(Text("Camera")) {
                        imagePickerSourceType = .camera
                        showImagePicker = true
                    },
                    .cancel()
                ]
            )
        }
    }
    
    private func saveProfilePicture() {
        guard let image = selectedImage else { return }
        
        isLoading = true
        showError = false
        showSuccess = false
        
        Task {
            do {
                let response = try await authService.uploadProfilePicture(image)
                
                await MainActor.run {
                    // Update the profile image URL in AuthService
                    authService.profileImageUrl = response.profile_image_url
                    
                    isLoading = false
                    showSuccess = true
                    
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
}

// MARK: - UIKit Image Picker
struct ImagePicker: UIViewControllerRepresentable {
    @Binding var selectedImage: UIImage?
    @Environment(\.dismiss) private var dismiss
    let sourceType: UIImagePickerController.SourceType
    
    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.delegate = context.coordinator
        picker.sourceType = sourceType
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

// MARK: - Display Name Setup View for New Users
struct DisplayNameSetupView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    @State private var displayName = ""
    @State private var isLoading = false
    @State private var errorMessage = ""
    @State private var showError = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 30) {
                Spacer()
                
                // Welcome message
                VStack(spacing: 16) {
                    Image(systemName: "person.circle.fill")
                        .font(.system(size: 80))
                        .foregroundColor(.blue)
                    
                    Text("Welcome to Vortex!")
                        .font(.title)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                    
                    Text("Let's personalize your experience by setting a display name.")
                        .font(.body)
                        .foregroundColor(.gray)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 20)
                }
                
                // Display name input
                VStack(alignment: .leading, spacing: 8) {
                    Text("Display Name")
                        .font(.headline)
                        .foregroundColor(.white)
                    
                    TextField("Enter your display name", text: $displayName)
                        .textFieldStyle(CustomTextFieldStyle())
                        .autocapitalization(.words)
                }
                .padding(.horizontal, 20)
                
                // Current default name info
                VStack(spacing: 8) {
                    Text("Currently using: \(authService.uiDisplayName)")
                        .font(.caption)
                        .foregroundColor(.gray)
                    
                    Text("You can change this anytime in your profile settings.")
                        .font(.caption2)
                        .foregroundColor(.gray.opacity(0.7))
                }
                
                // Continue button
                Button(action: saveDisplayName) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(0.8)
                        }
                        Text("Continue")
                            .font(.headline)
                            .foregroundColor(.white)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 50)
                    .background(displayName.isEmpty ? Color.gray : Color.blue)
                    .cornerRadius(12)
                }
                .disabled(displayName.isEmpty || isLoading)
                .padding(.horizontal, 20)
                
                Spacer()
            }
            .background(Color.black)
            .navigationTitle("Set Display Name")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarBackButtonHidden(true)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Skip for now") {
                        // Mark as complete and dismiss
                        authService.markDisplayNameSetupCompleted()
                        dismiss()
                    }
                    .foregroundColor(.gray)
                }
            }
        }
        .onAppear {
            // Pre-fill with current uiDisplayName if it's not the default "User"
            if authService.uiDisplayName != "User" {
                displayName = authService.uiDisplayName
            }
        }
    }
    
    private func saveDisplayName() {
        guard !displayName.isEmpty else { return }
        
        isLoading = true
        showError = false
        
        Task {
            do {
                _ = try await authService.updateDisplayName(displayName)
                
                await MainActor.run {
                    isLoading = false
                    dismiss()
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