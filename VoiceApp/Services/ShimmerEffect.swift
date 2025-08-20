import SwiftUI

struct ShimmerEffect: View {
    @State private var isAnimating = false
    
    var body: some View {
        LinearGradient(
            gradient: Gradient(colors: [
                Color.white.opacity(0.05), // Reduced opacity for subtler effect
                Color.white.opacity(0.2),  // Reduced opacity for subtler effect
                Color.white.opacity(0.05)  // Reduced opacity for subtler effect
            ]),
            startPoint: .leading,
            endPoint: .trailing
        )
        .mask(
            Rectangle()
                .fill(
                    LinearGradient(
                        gradient: Gradient(colors: [
                            Color.clear,
                            Color.white,
                            Color.clear
                        ]),
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .rotationEffect(.degrees(30))
                .offset(x: isAnimating ? 400 : -400)
        )
        .onAppear {
            // Disable shimmer animation to prevent any layout movement
            // withAnimation(
            //     .linear(duration: 2.0) // Slower animation for less distraction
            //     .repeatForever(autoreverses: false)
            // ) {
            //     isAnimating = true
            // }
        }
    }
}

// Enhanced placeholder with shimmer effect
struct ShimmerPlaceholder: View {
    let size: CGSize
    let cornerRadius: CGFloat
    
    var body: some View {
        RoundedRectangle(cornerRadius: cornerRadius)
            .fill(
                LinearGradient(
                    colors: [.blue.opacity(0.8), .purple.opacity(0.8)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .frame(width: size.width, height: size.height)
            .overlay(
                ShimmerEffect()
                    .opacity(0.3)
            )
    }
}
