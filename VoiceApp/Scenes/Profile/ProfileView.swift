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
                    ProfileInfoRow(title: "Display Name", value: authService.uiDisplayName)
                    ProfileInfoRow(title: "Email", value: authService.realEmail ?? authService.email ?? "N/A")
                    ProfileInfoRow(title: "Phone Number", value: userStatsService.phoneNumber)
                    ProfileInfoRow(title: "Status", value: "Active")
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
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                TextField("Display Name", text: $displayName)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .padding(.horizontal, 20)
                
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
                        // TODO: Implement save logic
                        dismiss()
                    }
                    .foregroundColor(.blue)
                }
            }
        }
        .onAppear {
            displayName = authService.displayName ?? ""
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