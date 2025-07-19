# VoiceApp iOS - 开发指南

> **状态**: 📱 **后端API就绪，可开始iOS开发**
>
> **后端支持**: 28个API端点完全可用，生产环境部署完成

## 📱 项目概述

**VoiceApp iOS**: 基于后端API的语音社交iOS应用，支持智能话题匹配、实时语音聊天、AI主持（计划中）、好友系统和录音回放。

## 🎯 核心功能

### ✅ 后端API就绪功能
- **用户认证** - Firebase Auth集成
- **话题管理** - 8个预设话题 + 用户偏好  
- **智能匹配** - Redis队列匹配算法
- **语音房间** - LiveKit多人实时通话
- **好友系统** - 完整社交功能
- **录音系统** - 录音存储和回放

### ⚠️ 计划中功能  
- **AI主持人** - OpenAI GPT-4 + STT + TTS
- **推送通知** - 匹配和好友通知
- **实时聊天** - WebSocket文字消息

## 🛠️ 技术栈

### iOS开发技术
- **语言**: Swift 5.9+
- **UI框架**: SwiftUI (主要) + UIKit (复杂组件)
- **架构**: MVVM + Clean Architecture  
- **网络**: URLSession + Combine
- **实时音频**: LiveKit iOS SDK
- **音频处理**: AVFoundation
- **数据存储**: Core Data + UserDefaults

### 主要依赖库
```swift
// Firebase
.package(url: "https://github.com/firebase/firebase-ios-sdk", from: "10.0.0")

// LiveKit
.package(url: "https://github.com/livekit/client-sdk-swift", from: "1.0.0")

// 网络增强
.package(url: "https://github.com/Alamofire/Alamofire", from: "5.0.0")
```

## 🚀 快速开始

### 1. 项目设置
```bash
# 创建iOS项目
# 在Xcode中创建新的iOS App项目
# - Product Name: VoiceApp
# - Language: Swift
# - Interface: SwiftUI
# - Use Core Data: Yes
```

### 2. 依赖配置
```swift
// Package.swift 或 Xcode > File > Add Package Dependencies
dependencies: [
    .package(url: "https://github.com/firebase/firebase-ios-sdk"),
    .package(url: "https://github.com/livekit/client-sdk-swift"),
    .package(url: "https://github.com/Alamofire/Alamofire")
]
```

### 3. Firebase配置
```swift
// 1. 下载 GoogleService-Info.plist 添加到项目
// 2. AppDelegate中初始化Firebase
import FirebaseCore
import FirebaseAuth

@main
struct VoiceAppApp: App {
    init() {
        FirebaseApp.configure()
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
```

### 4. 权限配置
在 `Info.plist` 中添加：
```xml
<key>NSMicrophoneUsageDescription</key>
<string>需要麦克风权限进行语音聊天</string>

<key>NSNetworkVolumesUsageDescription</key>
<string>需要网络权限连接语音服务</string>
```

## 📋 开发路线图

### Phase 1: 项目基础 (1天)
- [x] 后端API文档了解 (28个端点)
- [ ] iOS项目创建和依赖配置
- [ ] Firebase和LiveKit SDK集成
- [ ] 基础架构搭建 (MVVM + Repository)

### Phase 2: 认证系统 (2天)
- [ ] AuthService - Firebase Auth集成
- [ ] 登录/注册界面 - SwiftUI
- [ ] 用户状态管理 - Combine
- [ ] 自动登录和Token管理

### Phase 3: 核心功能 (5天)
- [ ] **话题选择** - API: `/api/topics/`
- [ ] **智能匹配** - API: `/api/matching/` + WebSocket
- [ ] **语音聊天** - LiveKit Room + API: `/api/rooms/`
- [ ] **用户资料** - API: `/api/auth/profile`

### Phase 4: 社交功能 (3天)
- [ ] **好友系统** - API: `/api/friends/`
- [ ] **录音回放** - API: `/api/recordings/`
- [ ] **聊天历史** - 本地Core Data存储

### Phase 5: 增强功能 (按需)
- [ ] **推送通知** - Firebase Cloud Messaging
- [ ] **AI功能集成** - 等待后端OpenAI集成
- [ ] **UI/UX优化** - 动画和用户体验改进

## 🔗 API集成参考

### 主要端点
```swift
// 后端API Base URL
let baseURL = "https://your-railway-app.railway.app"

// 核心API端点
enum APIEndpoint {
    // 认证
    case register, login, profile
    
    // 话题
    case topics, updatePreferences  
    
    // 匹配
    case findMatch, cancelMatch, matchStatus
    
    // 房间
    case createRoom, joinRoom, leaveRoom, roomToken
    
    // 好友
    case sendFriendRequest, acceptRequest, friendsList
    
    // 录音
    case uploadRecording, downloadRecording, recordingsList
}
```

### Firebase Auth集成
```swift
// 用户注册后获取ID Token
user.getIDToken { idToken, error in
    // 使用idToken调用后端API
    // 后端会验证Firebase ID Token
}
```

### LiveKit集成示例
```swift
import LiveKit

class RoomManager: ObservableObject {
    private var room: Room?
    
    func joinRoom(token: String) async throws {
        room = Room()
        
        try await room?.connect(
            url: "wss://voodooo-5oh49lvx.livekit.cloud",
            token: token
        )
    }
}
```

## 📱 UI架构建议

### SwiftUI视图结构
```
ContentView
├── AuthenticationView (未登录状态)
├── MainTabView (已登录状态)
│   ├── TopicsView (话题选择)
│   ├── MatchingView (匹配界面)  
│   ├── RoomView (语音聊天室)
│   ├── FriendsView (好友列表)
│   └── ProfileView (个人资料)
```

### MVVM架构
```swift
// ViewModel示例
class AuthViewModel: ObservableObject {
    @Published var isLoggedIn = false
    @Published var currentUser: User?
    
    private let authService: AuthService
    private let apiService: APIService
    
    func login(email: String, password: String) async {
        // Firebase Auth登录
        // 获取ID Token
        // 调用后端验证API
    }
}
```

## 🎯 当前优势

### ✅ 后端完全就绪
- **28个API端点**全部实现并测试
- **生产环境部署**Railway + Redis + Firebase
- **实时语音**LiveKit服务配置完成
- **安全认证**Firebase Auth集成

### 📱 iOS开发可立即开始
- API文档完整 (`/docs`)
- 所有核心功能后端支持
- LiveKit iOS SDK兼容
- Firebase iOS SDK集成

## 📚 参考资源

- **后端API文档**: `https://your-app.railway.app/docs`
- **LiveKit iOS文档**: https://docs.livekit.io/client-sdk-swift/
- **Firebase iOS文档**: https://firebase.google.com/docs/ios
- **SwiftUI官方文档**: https://developer.apple.com/swiftui/

---

## 🎉 项目状态

**🟢 后端**: 生产就绪，28个API端点完全可用  
**🔄 iOS**: 可立即开始开发，后端API完全支持  
**⏳ AI功能**: 后端框架就绪，OpenAI集成进行中

**开始iOS开发的最佳时机已到！** 🚀 