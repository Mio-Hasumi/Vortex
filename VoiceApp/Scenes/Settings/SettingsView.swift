import SwiftUI

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var authService = AuthService.shared
    
    var body: some View {
        NavigationView {
            List {
                // Account Section
                Section("Account") {
                    SettingsRow(
                        icon: "person.circle",
                        title: "Profile",
                        subtitle: "Edit your profile information"
                    )
                    
                    SettingsRow(
                        icon: "key",
                        title: "Privacy",
                        subtitle: "Manage your privacy settings"
                    )
                    
                    SettingsRow(
                        icon: "bell",
                        title: "Notifications",
                        subtitle: "Manage notification preferences"
                    )
                }
                
                // Voice Section
                Section("Voice & Audio") {
                    SettingsRow(
                        icon: "mic",
                        title: "Microphone",
                        subtitle: "Audio input settings"
                    )
                    
                    SettingsRow(
                        icon: "speaker.wave.2",
                        title: "Audio Quality",
                        subtitle: "Adjust audio quality settings"
                    )
                    
                    SettingsRow(
                        icon: "waveform",
                        title: "Voice Recognition",
                        subtitle: "Improve voice matching accuracy"
                    )
                }
                
                // App Section
                Section("App Settings") {
                    SettingsRow(
                        icon: "moon",
                        title: "Dark Mode",
                        subtitle: "Always enabled"
                    )
                    
                    SettingsRow(
                        icon: "globe",
                        title: "Language",
                        subtitle: "English"
                    )
                    
                    SettingsRow(
                        icon: "arrow.clockwise",
                        title: "Auto-Update",
                        subtitle: "Keep app updated automatically"
                    )
                }
                
                // Support Section
                Section("Support") {
                    SettingsRow(
                        icon: "questionmark.circle",
                        title: "Help Center",
                        subtitle: "Get help and support"
                    )
                    
                    SettingsRow(
                        icon: "envelope",
                        title: "Contact Us",
                        subtitle: "Send feedback or report issues"
                    )
                    
                    SettingsRow(
                        icon: "doc.text",
                        title: "Terms & Privacy",
                        subtitle: "Legal information"
                    )
                }
                
                // Danger Zone
                Section("Account Actions") {
                    Button(action: {
                        Task {
                            try await authService.signOut()
                        }
                    }) {
                        HStack {
                            Image(systemName: "rectangle.portrait.and.arrow.right")
                                .foregroundColor(.red)
                            Text("Sign Out")
                                .foregroundColor(.red)
                        }
                    }
                }
            }
            .listStyle(InsetGroupedListStyle())
            .background(Color.black)
            .scrollContentBackground(.hidden)
            .navigationTitle("Settings")
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
    }
}

struct SettingsRow: View {
    let icon: String
    let title: String
    let subtitle: String
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(.blue)
                .frame(width: 32, height: 32)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.body)
                    .foregroundColor(.white)
                
                Text(subtitle)
                    .font(.caption)
                    .foregroundColor(.gray)
            }
            
            Spacer()
            
            Image(systemName: "chevron.right")
                .font(.system(size: 14))
                .foregroundColor(.gray)
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())
    }
}

#Preview {
    SettingsView()
} 