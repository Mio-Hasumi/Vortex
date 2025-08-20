import Foundation
import UIKit
import SwiftUI
import CoreHaptics

class ImageCacheService: ObservableObject {
    static let shared = ImageCacheService()
    
    private let cache = NSCache<NSString, UIImage>()
    private let imageLoader = ImageLoader()
    
    private init() {
        // Set cache limits
        cache.countLimit = 100 // Max 100 images
        cache.totalCostLimit = 50 * 1024 * 1024 // 50MB limit
    }
    
    func getImage(from urlString: String) -> UIImage? {
        return cache.object(forKey: urlString as NSString)
    }
    
    func loadImage(from urlString: String) async -> UIImage? {
        // Check cache first
        if let cachedImage = getImage(from: urlString) {
            return cachedImage
        }
        
        // Load from network
        guard let image = await imageLoader.loadImage(from: urlString) else {
            return nil
        }
        
        // Cache the image
        cache.setObject(image, forKey: urlString as NSString)
        return image
    }
    
    func preloadImage(from urlString: String) {
        Task {
            _ = await loadImage(from: urlString)
        }
    }
    
    func clearCache() {
        cache.removeAllObjects()
    }
}

class ImageLoader {
    func loadImage(from urlString: String) async -> UIImage? {
        guard let url = URL(string: urlString) else { return nil }
        
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return UIImage(data: data)
        } catch {
            print("Failed to load image from \(urlString): \(error)")
            return nil
        }
    }
}

// Optimized AsyncImage with caching and smooth transitions
struct CachedAsyncImage<Content: View, Placeholder: View>: View {
    let url: String?
    let content: (Image) -> Content
    let placeholder: () -> Placeholder
    
    @StateObject private var imageCache = ImageCacheService.shared
    @State private var image: UIImage?
    @State private var isLoading = false
    
    init(
        url: String?,
        @ViewBuilder content: @escaping (Image) -> Content,
        @ViewBuilder placeholder: @escaping () -> Placeholder
    ) {
        self.url = url
        self.content = content
        self.placeholder = placeholder
    }
    
    var body: some View {
        Group {
            if let image = image {
                content(Image(uiImage: image))
                    // No transitions or animations to prevent any layout movement
            } else {
                placeholder()
                    .onAppear {
                        loadImage()
                    }
                    .overlay(
                        // Add a subtle loading indicator
                        Group {
                            if isLoading {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                    .scaleEffect(0.8)
                            }
                        }
                    )
            }
        }
    }
    
    private func loadImage() {
        guard let url = url, !url.isEmpty, !isLoading else { return }
        
        isLoading = true
        
        Task {
            if let loadedImage = await imageCache.loadImage(from: url) {
                await MainActor.run {
                    // Add subtle haptic feedback for better UX
                    let impactFeedback = UIImpactFeedbackGenerator(style: .light)
                    impactFeedback.impactOccurred()
                    
                    // No animation to prevent layout movement
                    self.image = loadedImage
                }
            }
            isLoading = false
        }
    }
}
