import SwiftUI
import Combine

struct WaitingRoomView: View {
    @StateObject private var waitingRoomService = WaitingRoomService()
    @Environment(\.dismiss) private var dismiss

    let waitingRoomInfo: WaitingRoomResponse
    
    @State private var navigateToLiveChat = false
    @State private var matchData: LiveMatchData?

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            // NavigationLink to the actual chat room
            if let matchData = matchData {
                NavigationLink(
                    destination: HashtagScreen(matchData: matchData, isWaitingRoom: false),
                    isActive: $navigateToLiveChat
                ) {
                    EmptyView()
                }
            }

            VStack {
                HStack {
                    Button(action: {
                        waitingRoomService.disconnect()
                        dismiss()
                    }) {
                        Image(systemName: "xmark")
                            .font(.title2)
                            .foregroundColor(.white)
                    }
                    Spacer()
                }
                .padding()

                Spacer()

                VStack(spacing: 20) {
                    Text("Chatting with Vortex")
                        .font(.custom("Rajdhani", size: 32))
                        .foregroundColor(.white)
                    
                    Text("Tell our AI what you'd like to talk about to find the best match.")
                        .font(.custom("Rajdhani", size: 18))
                        .foregroundColor(.white.opacity(0.7))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)

                    // You could add a participant view here to show the user and the agent
                    // For now, a simple progress view indicates activity.
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(1.5)
                }

                Spacer()
            }
            
            VStack {
                 Spacer()
                 Button(action: {
                     waitingRoomService.toggleMute()
                 }) {
                     Image(systemName: waitingRoomService.isMuted ? "mic.slash.fill" : "mic.fill")
                         .font(.system(size: 40))
                         .foregroundColor(waitingRoomService.isMuted ? .red : .white)
                         .padding(20)
                         .background(Circle().fill(Color.white.opacity(0.2)))
                 }
                 
                 Text(waitingRoomService.isMuted ? "Muted" : "Listening...")
                     .foregroundColor(.white)
                     .padding(.bottom, 30)
             }
        }
        .navigationBarHidden(true)
        .onAppear {
            waitingRoomService.connect(waitingRoomInfo: waitingRoomInfo)
        }
        .onDisappear {
            waitingRoomService.disconnect()
        }
        .onReceive(waitingRoomService.$matchFound) { matchData in
            if let data = matchData {
                self.matchData = data
                self.navigateToLiveChat = true
            }
        }
    }
}
