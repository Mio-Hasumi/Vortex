import SwiftUI

struct HistoryView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var selectedFilter = "All"
    
    let filters = ["All", "Voice Matches", "Chat Rooms", "Recordings"]
    
    let historyItems = [
        HistoryItem(
            type: .voiceMatch,
            title: "Voice Match with Sarah",
            subtitle: "Technology discussion",
            timestamp: "2 hours ago",
            duration: "15 min"
        ),
        HistoryItem(
            type: .chatRoom,
            title: "Tech Talk Room",
            subtitle: "AI and Machine Learning",
            timestamp: "Yesterday",
            duration: "45 min"
        ),
        HistoryItem(
            type: .recording,
            title: "Voice Note #42",
            subtitle: "Travel plans discussion",
            timestamp: "2 days ago",
            duration: "3 min"
        ),
        HistoryItem(
            type: .voiceMatch,
            title: "Voice Match with Alex",
            subtitle: "Sports conversation",
            timestamp: "3 days ago",
            duration: "22 min"
        )
    ]
    
    var filteredItems: [HistoryItem] {
        if selectedFilter == "All" {
            return historyItems
        } else {
            return historyItems.filter { item in
                switch selectedFilter {
                case "Voice Matches":
                    return item.type == .voiceMatch
                case "Chat Rooms":
                    return item.type == .chatRoom
                case "Recordings":
                    return item.type == .recording
                default:
                    return true
                }
            }
        }
    }
    
    var body: some View {
        NavigationView {
            VStack {
                // Filter Picker
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(filters, id: \.self) { filter in
                            Button(filter) {
                                selectedFilter = filter
                            }
                            .padding(.horizontal, 16)
                            .padding(.vertical, 8)
                            .background(
                                selectedFilter == filter ?
                                Color.blue : Color.gray.opacity(0.3)
                            )
                            .foregroundColor(.white)
                            .cornerRadius(20)
                        }
                    }
                    .padding(.horizontal, 20)
                }
                .padding(.vertical, 10)
                
                // History List
                List(filteredItems) { item in
                    HistoryItemRow(item: item)
                }
                .listStyle(PlainListStyle())
                .background(Color.black)
            }
            .background(Color.black)
            .navigationTitle("History")
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

struct HistoryItemRow: View {
    let item: HistoryItem
    
    var body: some View {
        HStack(spacing: 12) {
            // Icon
            Circle()
                .fill(item.iconColor)
                .frame(width: 50, height: 50)
                .overlay(
                    Image(systemName: item.iconName)
                        .font(.system(size: 20))
                        .foregroundColor(.white)
                )
            
            // Content
            VStack(alignment: .leading, spacing: 4) {
                Text(item.title)
                    .font(.body)
                    .fontWeight(.medium)
                    .foregroundColor(.white)
                
                Text(item.subtitle)
                    .font(.caption)
                    .foregroundColor(.gray)
                
                HStack {
                    Text(item.timestamp)
                        .font(.caption2)
                        .foregroundColor(.gray)
                    
                    Text("•")
                        .font(.caption2)
                        .foregroundColor(.gray)
                    
                    Text(item.duration)
                        .font(.caption2)
                        .foregroundColor(.gray)
                }
            }
            
            Spacer()
            
            // Action Button
            Button(action: {
                // TODO: 处理历史项目的操作
            }) {
                Image(systemName: "ellipsis")
                    .font(.system(size: 16))
                    .foregroundColor(.gray)
            }
        }
        .padding(.vertical, 8)
        .background(Color.black)
    }
}

// MARK: - Models
struct HistoryItem: Identifiable {
    let id = UUID()
    let type: HistoryType
    let title: String
    let subtitle: String
    let timestamp: String
    let duration: String
    
    var iconName: String {
        switch type {
        case .voiceMatch:
            return "waveform"
        case .chatRoom:
            return "person.2.fill"
        case .recording:
            return "mic.fill"
        }
    }
    
    var iconColor: Color {
        switch type {
        case .voiceMatch:
            return .blue
        case .chatRoom:
            return .green
        case .recording:
            return .purple
        }
    }
}

enum HistoryType {
    case voiceMatch
    case chatRoom
    case recording
}

#Preview {
    HistoryView()
} 