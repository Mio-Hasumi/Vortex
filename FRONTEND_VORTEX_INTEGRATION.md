# VortexAgent 前端集成指南

## 🎯 集成状态

### ✅ 已完成 - 自动工作
你的iOS前端现在**完全支持VortexAgent**，无需额外配置！

#### 核心功能（自动运行）:
- **自动识别AI主持人** - 检测以"host_"开头的参与者
- **特殊UI显示** - AI用紫色orb头像和"Vortex"标识
- **语音通信** - 通过现有LiveKit SDK处理AI语音
- **实时状态** - 显示"AI Host Active"指示器
- **欢迎通知** - AI加入时显示友好消息

### 🔧 可选功能 - 高级管理
如果你想要更多控制，可以使用新的API：

#### 新增的可选API:
- `VortexAgentService.swift` - Swift服务类
- `/api/agents/*` - 后端管理endpoints
- 新的Models - `AgentStatusResponse`, `AgentSettingsRequest`等

## 📱 前端使用方式

### 基础使用（推荐）
**什么都不需要做！** VortexAgent会自动：
1. 在房间创建时部署
2. 作为参与者出现在LiveKit
3. 用特殊UI显示
4. 进行语音对话

### 高级使用（可选）
如果想要控制AI行为：

```swift
// 检查AI是否活跃
let isActive = await VortexAgentService.shared.isAgentActive(in: roomId)

// 自定义AI性格
try await VortexAgentService.shared.setFriendlyMode(roomId: roomId)

// 获取AI状态
let status = try await VortexAgentService.shared.getAgentStatus(roomId: roomId)
print("AI功能: \(status.ai_features)")

// 移除AI（如果需要纯人类对话）
try await VortexAgentService.shared.removeAgent(fromRoom: roomId)
```

## 🎨 UI增强

### 自动视觉区分
- **AI头像**: 使用现有的"orb"图像
- **特殊边框**: 紫色到蓝色渐变脉冲效果
- **AI徽章**: 显示"AI"标识
- **紫色文字**: AI名称用紫色显示
- **状态指示**: 顶部显示"AI Host Active"

### 通知系统
- **加入通知**: "Vortex has joined as your conversation host!"
- **离开通知**: 如果AI离开房间
- **平滑动画**: 所有UI变化都有过渡效果

## 🔄 向后兼容

### ✅ 完全兼容
- 所有现有功能正常工作
- 没有AI时界面完全正常
- 新功能是渐进增强的

### 更新的文件
1. **UI增强**:
   - `ChatLive.swift` - AI参与者特殊显示
   - `UV-TM.swift` - MatchParticipant模型更新

2. **API支持**:
   - `Models.swift` - 新增Agent管理模型
   - `APIConfig.swift` - 新增Agent endpoints
   - `VortexAgentService.swift` - 可选管理服务

3. **数据模型**:
   - `MatchParticipant` - 增加`isAIHost`字段
   - `RoomResponse` - 增加`ai_host_enabled`字段

## 🚀 快速开始

### 1. 基础使用（推荐新手）
```swift
// 什么都不需要做！
// 创建房间 -> AI自动加入 -> 开始对话
```

### 2. 检查AI状态（可选）
```swift
@State private var aiActive = false

// 在房间视图中
Task {
    aiActive = await VortexAgentService.shared.isAgentActive(in: roomId)
}
```

### 3. 自定义AI行为（高级）
```swift
// 设置为专业模式
try await VortexAgentService.shared.setProfessionalMode(roomId: roomId)

// 或友好模式
try await VortexAgentService.shared.setFriendlyMode(roomId: roomId)

// 或最小干预模式
try await VortexAgentService.shared.setMinimalMode(roomId: roomId)
```

## 📋 API Endpoints

### 新增的可选endpoints:
- `GET /api/agents/status/{room_id}` - 获取AI状态
- `PUT /api/agents/settings/{room_id}` - 更新AI设置  
- `DELETE /api/agents/{room_id}` - 移除AI
- `GET /api/agents/stats` - 获取统计信息

### Helper方法:
- `APIConfig.agentStatusPath(roomId)`
- `APIConfig.agentSettingsPath(roomId)` 
- `APIConfig.removeAgentPath(roomId)`

## ⚡ 性能说明

### 自动功能（零成本）:
- AI识别和显示 - 本地处理
- LiveKit通信 - 使用现有连接
- UI更新 - SwiftUI原生动画

### 可选功能（按需使用）:
- API调用 - 仅在需要控制时
- 状态检查 - 可以缓存结果
- 设置更新 - 一次性操作

## 🎉 总结

**你的前端已经准备好了！** 

VortexAgent会：
- ✅ 自动部署到新房间
- ✅ 在LiveKit中正常工作
- ✅ 用特殊UI显示  
- ✅ 进行语音对话
- ✅ 提供可选的高级控制

**下一步**: 启动后端，创建房间，享受AI主持的对话体验！ 