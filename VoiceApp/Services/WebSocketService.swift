import Foundation

enum WebSocketError: Error {
    case connectionFailed
    case authenticationFailed
    case invalidMessage
    case disconnected
    
    var message: String {
        switch self {
        case .connectionFailed:
            return "Failed to connect to server"
        case .authenticationFailed:
            return "WebSocket authentication failed"
        case .invalidMessage:
            return "Invalid message format"
        case .disconnected:
            return "WebSocket disconnected"
        }
    }
}

protocol WebSocketDelegate: AnyObject {
    func webSocket(_ service: WebSocketService, didReceiveMessage message: [String: Any])
    func webSocket(_ service: WebSocketService, didEncounterError error: Error)
    func webSocketDidConnect(_ service: WebSocketService)
    func webSocketDidDisconnect(_ service: WebSocketService)
}

class WebSocketService: NSObject, URLSessionWebSocketDelegate {
    private var webSocket: URLSessionWebSocketTask?
    private var session: URLSession!
    private(set) var isConnected = false
    private var authToken: String?
    private var reconnectAttempts = 0
    private let maxReconnectAttempts = 3
    
    weak var delegate: WebSocketDelegate?
    
    override init() {
        super.init()
        session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
    }
    
    func connect(to endpoint: String, with token: String) {
        guard let url = URL(string: APIConfig.wsBaseURL + endpoint) else { return }
        
        authToken = token
        webSocket = session.webSocketTask(with: url)
        webSocket?.resume()
        
        // Set connected state when WebSocket is created
        isConnected = true
        
        // Notify delegate of connection
        DispatchQueue.main.async {
            self.delegate?.webSocketDidConnect(self)
        }
        
        receiveMessage()
    }
    
    func disconnect() {
        webSocket?.cancel(with: .goingAway, reason: nil)
        webSocket = nil
        isConnected = false
        reconnectAttempts = 0
    }
    
    func send(_ message: [String: Any]) {
        guard let jsonData = try? JSONSerialization.data(withJSONObject: message),
              let jsonString = String(data: jsonData, encoding: .utf8) else {
            delegate?.webSocket(self, didEncounterError: WebSocketError.invalidMessage)
            return
        }
        
        let message = URLSessionWebSocketTask.Message.string(jsonString)
        webSocket?.send(message) { [weak self] error in
            if let error = error {
                self?.delegate?.webSocket(self!, didEncounterError: error)
            }
        }
    }
    
    private func authenticate() {
        guard let token = authToken else { return }
        
        let authMessage: [String: Any] = [
            "type": "auth",
            "token": token
        ]
        
        send(authMessage)
    }
    
    private func receiveMessage() {
        webSocket?.receive { [weak self] result in
            guard let self = self else { return }
            
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    if let data = text.data(using: .utf8),
                       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                        
                        DispatchQueue.main.async {
                            self.delegate?.webSocket(self, didReceiveMessage: json)
                        }
                    }
                case .data(let data):
                    if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                        DispatchQueue.main.async {
                            self.delegate?.webSocket(self, didReceiveMessage: json)
                        }
                    }
                @unknown default:
                    break
                }
                
                // Continue receiving messages
                self.receiveMessage()
                
            case .failure(let error):
                DispatchQueue.main.async {
                    self.delegate?.webSocket(self, didEncounterError: error)
                }
                
                // Try to reconnect
                self.handleDisconnection()
            }
        }
    }
    
    private func handleDisconnection() {
        isConnected = false
        
        guard reconnectAttempts < maxReconnectAttempts else {
            delegate?.webSocket(self, didEncounterError: WebSocketError.connectionFailed)
            return
        }
        
        reconnectAttempts += 1
        let delay = Double(pow(2, Double(reconnectAttempts - 1)))
        
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self = self,
                  let token = self.authToken else { return }
            
            // Reconnect with the same endpoint
            if let url = self.webSocket?.originalRequest?.url,
               let endpoint = url.path.components(separatedBy: APIConfig.wsBaseURL).last {
                self.connect(to: endpoint, with: token)
            }
        }
    }
    
    // MARK: - URLSessionWebSocketDelegate
    
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        isConnected = true
        reconnectAttempts = 0
        
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.delegate?.webSocketDidConnect(self)
            self.authenticate()
        }
    }
    
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        isConnected = false
        
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.delegate?.webSocketDidDisconnect(self)
        }
        
        // Handle reconnection if needed
        if closeCode != .goingAway {
            handleDisconnection()
        }
    }
} 