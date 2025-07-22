import Foundation

class TopicFactsService: ObservableObject {
    static let shared = TopicFactsService()
    
    @Published var currentFact = ""
    @Published var isGeneratingFact = false
    
    private var factTimer: Timer?
    private var currentTopic = ""
    private var factsQueue: [String] = []
    
    private init() {}
    
    func startFactsForTopic(_ topic: String) {
        print("📚 [TopicFacts] Starting facts for topic: \(topic)")
        currentTopic = topic
        stopFacts()
        
        // Generate initial fact
        generateNewFact()
        
        // Set up timer to show new facts every 12 seconds (10 seconds display + 2 seconds fade gap)
        factTimer = Timer.scheduledTimer(withTimeInterval: 12.0, repeats: true) { _ in
            self.generateNewFact()
        }
    }
    
    func stopFacts() {
        factTimer?.invalidate()
        factTimer = nil
        currentFact = ""
        factsQueue.removeAll()
    }
    
    private func generateNewFact() {
        guard !currentTopic.isEmpty else { return }
        
        // First, fade out the current fact
        DispatchQueue.main.async {
            self.currentFact = ""
        }
        
        // Wait 2 seconds for fade out, then generate new fact
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            self.isGeneratingFact = true
            
            // Generate a fact about the topic using AI
            Task {
                do {
                    let fact = try await self.generateFactAboutTopic(self.currentTopic)
                    await MainActor.run {
                        self.currentFact = fact
                        self.isGeneratingFact = false
                    }
                } catch {
                    await MainActor.run {
                        self.currentFact = "Did you know? \(self.currentTopic) is an interesting topic to explore!"
                        self.isGeneratingFact = false
                    }
                }
            }
        }
    }
    
    private func generateFactAboutTopic(_ topic: String) async throws -> String {
        // For now, we'll use a simple approach with predefined facts
        // In a real implementation, this would call an AI service
        
        let facts = getPredefinedFacts(for: topic)
        return facts.randomElement() ?? "\(topic) is a fascinating subject to discuss!"
    }
    
    private func getPredefinedFacts(for topic: String) -> [String] {
        let lowercasedTopic = topic.lowercased()
        
        // Technology facts
        if lowercasedTopic.contains("tech") || lowercasedTopic.contains("technology") || lowercasedTopic.contains("ai") || lowercasedTopic.contains("artificial intelligence") {
            return [
                "Did you know? The first computer programmer was Ada Lovelace in the 1840s!",
                "Fun fact: The first iPhone was released in 2007 and revolutionized mobile computing.",
                "Interesting: AI can now write code, create art, and even compose music!",
                "Did you know? The internet was originally created for military communication in the 1960s.",
                "Fun fact: There are more mobile phones on Earth than there are people!"
            ]
        }
        
        // Sports facts
        if lowercasedTopic.contains("sport") || lowercasedTopic.contains("football") || lowercasedTopic.contains("basketball") || lowercasedTopic.contains("soccer") {
            return [
                "Did you know? Basketball was invented by Dr. James Naismith in 1891!",
                "Fun fact: The fastest recorded serve in tennis was 163.7 mph by Sam Groth.",
                "Interesting: Soccer is played by over 4 billion people worldwide!",
                "Did you know? The Olympic Games originated in ancient Greece in 776 BC.",
                "Fun fact: The longest tennis match lasted 11 hours and 5 minutes!"
            ]
        }
        
        // Culture facts
        if lowercasedTopic.contains("culture") || lowercasedTopic.contains("art") || lowercasedTopic.contains("music") || lowercasedTopic.contains("film") {
            return [
                "Did you know? The Mona Lisa has no eyebrows - it was fashionable in Renaissance Florence!",
                "Fun fact: The shortest song ever recorded is 'You Suffer' by Napalm Death at 1.316 seconds.",
                "Interesting: The first movie ever made was 'Roundhay Garden Scene' in 1888.",
                "Did you know? Van Gogh only sold one painting during his lifetime!",
                "Fun fact: The longest movie ever made is 'Logistics' at 35 days long!"
            ]
        }
        
        // Life/General facts
        if lowercasedTopic.contains("life") || lowercasedTopic.contains("philosophy") || lowercasedTopic.contains("psychology") {
            return [
                "Did you know? The average person spends 6 months of their lifetime waiting for red lights!",
                "Fun fact: Your brain uses 20% of your body's total energy.",
                "Interesting: Humans are the only animals that blush!",
                "Did you know? The average person dreams 4-6 times per night.",
                "Fun fact: Your heart beats about 100,000 times every day!"
            ]
        }
        
        // Default facts for any topic
        return [
            "Did you know? \(topic) is a great conversation starter!",
            "Fun fact: People who discuss \(topic) often have deeper conversations.",
            "Interesting: \(topic) brings people together from different backgrounds.",
            "Did you know? Talking about \(topic) can improve your mood!",
            "Fun fact: \(topic) is a topic that never gets old!"
        ]
    }
} 