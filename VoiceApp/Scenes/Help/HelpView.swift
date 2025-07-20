import SwiftUI

struct HelpView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var selectedTab = 0
    
    var body: some View {
        NavigationView {
            VStack {
                // Tab Selector
                Picker("", selection: $selectedTab) {
                    Text("FAQ").tag(0)
                    Text("Guide").tag(1)
                    Text("Contact").tag(2)
                }
                .pickerStyle(SegmentedPickerStyle())
                .padding(.horizontal, 20)
                .padding(.top, 10)
                
                // Content
                TabView(selection: $selectedTab) {
                    FAQView()
                        .tag(0)
                    
                    GuideView()
                        .tag(1)
                    
                    ContactView()
                        .tag(2)
                }
                .tabViewStyle(PageTabViewStyle(indexDisplayMode: .never))
            }
            .background(Color.black)
            .navigationTitle("Help & Support")
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

struct FAQView: View {
    let faqs = [
        FAQ(question: "How does voice matching work?", answer: "Our AI analyzes your voice input to understand your interests and conversation style, then matches you with compatible people."),
        FAQ(question: "Is my voice data secure?", answer: "Yes, we use end-to-end encryption and delete voice recordings after processing. Your privacy is our priority."),
        FAQ(question: "Can I block someone?", answer: "Yes, you can block users from your profile or during conversations. Blocked users cannot contact you."),
        FAQ(question: "How do I improve match quality?", answer: "Speak clearly about your interests and be specific about topics you'd like to discuss."),
        FAQ(question: "What languages are supported?", answer: "Currently we support English, Chinese, Spanish, French, and German with more languages coming soon.")
    ]
    
    var body: some View {
        List(faqs) { faq in
            FAQRow(faq: faq)
        }
        .listStyle(PlainListStyle())
        .background(Color.black)
    }
}

struct GuideView: View {
    let guides = [
        GuideItem(icon: "mic.fill", title: "Getting Started", description: "Learn how to use voice matching and find interesting conversations"),
        GuideItem(icon: "waveform", title: "Voice Tips", description: "Best practices for clear voice recording and better matches"),
        GuideItem(icon: "person.2.fill", title: "Making Friends", description: "How to connect with people and build lasting friendships"),
        GuideItem(icon: "gear", title: "Privacy Settings", description: "Manage your privacy and security preferences"),
        GuideItem(icon: "bell", title: "Notifications", description: "Customize your notification preferences")
    ]
    
    var body: some View {
        List(guides) { guide in
            GuideRow(guide: guide)
        }
        .listStyle(PlainListStyle())
        .background(Color.black)
    }
}

struct ContactView: View {
    var body: some View {
        VStack(spacing: 30) {
            VStack(spacing: 16) {
                Image(systemName: "envelope.fill")
                    .font(.system(size: 50))
                    .foregroundColor(.blue)
                
                Text("Get in Touch")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                
                Text("We're here to help! Reach out to us through any of the following channels.")
                    .font(.body)
                    .foregroundColor(.gray)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 20)
            }
            
            VStack(spacing: 16) {
                ContactButton(
                    icon: "envelope",
                    title: "Email Support",
                    subtitle: "support@voiceapp.com",
                    action: {
                        // TODO: 打开邮件应用
                    }
                )
                
                ContactButton(
                    icon: "message",
                    title: "Live Chat",
                    subtitle: "Available 24/7",
                    action: {
                        // TODO: 打开聊天支持
                    }
                )
                
                ContactButton(
                    icon: "questionmark.circle",
                    title: "Help Center",
                    subtitle: "Browse our knowledge base",
                    action: {
                        // TODO: 打开帮助中心
                    }
                )
            }
            .padding(.horizontal, 20)
            
            Spacer()
        }
        .padding(.top, 40)
        .background(Color.black)
    }
}

struct FAQRow: View {
    let faq: FAQ
    @State private var isExpanded = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Button(action: {
                withAnimation(.easeInOut(duration: 0.3)) {
                    isExpanded.toggle()
                }
            }) {
                HStack {
                    Text(faq.question)
                        .font(.body)
                        .fontWeight(.medium)
                        .foregroundColor(.white)
                        .multilineTextAlignment(.leading)
                    
                    Spacer()
                    
                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .font(.system(size: 14))
                        .foregroundColor(.gray)
                }
            }
            .buttonStyle(PlainButtonStyle())
            
            if isExpanded {
                Text(faq.answer)
                    .font(.subheadline)
                    .foregroundColor(.gray)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .padding(.vertical, 8)
        .background(Color.black)
    }
}

struct GuideRow: View {
    let guide: GuideItem
    
    var body: some View {
        HStack(spacing: 16) {
            Circle()
                .fill(Color.blue.opacity(0.2))
                .frame(width: 50, height: 50)
                .overlay(
                    Image(systemName: guide.icon)
                        .font(.system(size: 20))
                        .foregroundColor(.blue)
                )
            
            VStack(alignment: .leading, spacing: 4) {
                Text(guide.title)
                    .font(.body)
                    .fontWeight(.medium)
                    .foregroundColor(.white)
                
                Text(guide.description)
                    .font(.caption)
                    .foregroundColor(.gray)
            }
            
            Spacer()
            
            Image(systemName: "chevron.right")
                .font(.system(size: 14))
                .foregroundColor(.gray)
        }
        .padding(.vertical, 8)
        .background(Color.black)
    }
}

struct ContactButton: View {
    let icon: String
    let title: String
    let subtitle: String
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 16) {
                Image(systemName: icon)
                    .font(.system(size: 24))
                    .foregroundColor(.blue)
                    .frame(width: 40, height: 40)
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.body)
                        .fontWeight(.medium)
                        .foregroundColor(.white)
                    
                    Text(subtitle)
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                
                Spacer()
                
                Image(systemName: "arrow.up.right")
                    .font(.system(size: 16))
                    .foregroundColor(.blue)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 16)
            .background(Color.gray.opacity(0.1))
            .cornerRadius(12)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

// MARK: - Models
struct FAQ: Identifiable {
    let id = UUID()
    let question: String
    let answer: String
}

struct GuideItem: Identifiable {
    let id = UUID()
    let icon: String
    let title: String
    let description: String
}

#Preview {
    HelpView()
} 