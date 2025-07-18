# VoiceApp - AI驱动的智能语音通话应用

## 🎯 项目概述

**VoiceApp Backend**: 为iOS语音社交应用提供后端服务的Python API服务器。支持话题匹配、AI主持聊天、多人语音房间、好友系统和录音管理等功能。

**注意**: 此项目为后端服务，配合iOS客户端使用 (详见 `iOS_WORKFLOW.md`)。

## 🏗️ 核心功能

### 1. 用户管理与社交
- 用户注册/登录/登出
- 用户身份验证和授权
- 用户资料和兴趣管理
- 好友系统（聊天后可加好友）
- 用户聊天历史和录音回放

### 2. 话题匹配系统
- 用户选择或输入感兴趣的话题
- AI智能匹配相同话题兴趣的用户
- 等待队列机制（无匹配时与AI聊天）
- 话题分类和管理系统

### 3. AI主持人功能
- AI使用GPT-4进行智能对话和主持
- 支持语音识别(STT)和文本转语音(TTS)
- 基于LiveKit的高质量实时音频通信
- AI作为聊天助理帮助梳理和引导对话
- 智能话题转换和气氛调节

### 4. 多人语音聊天
- 支持2+人 + AI的多人聊天室
- 动态参与者管理（用户可中途加入/退出）
- 会话状态管理（WAITING → MATCHING → ACTIVE → ENDED）
- 实时语音通信和音频处理

### 5. 录音和回放系统
- 自动录制聊天内容
- 聊天结束后提供录音回放
- 录音存储和管理
- 转录文本查看和搜索

## 🔧 技术架构

### 架构模式
- **Clean Architecture** (清洁架构)
- **Domain-Driven Design** (领域驱动设计)
- **Dependency Inversion** (依赖倒置)

### 后端技术栈
- **后端语言**: Python 3.12
- **Web框架**: FastAPI (高性能异步API)
- **AI服务**: OpenAI GPT-4 (对话) + GPT-4o (语音识别/合成)
- **实时通信**: LiveKit Server (WebRTC音视频)
- **数据库**: Firebase Firestore (NoSQL文档数据库)
- **认证**: Firebase Auth + JWT Token
- **推送通知**: Firebase Cloud Messaging (FCM)
- **文件存储**: Firebase Storage (录音文件存储)
- **匹配算法**: 基于向量相似度的话题匹配
- **队列系统**: Redis (匹配队列和实时状态管理)
- **部署**: Docker + 云服务 (AWS/GCP/Azure)

### 客户端技术栈 [RESERVED FOR LATER]
- **iOS应用**: Swift + SwiftUI + LiveKit iOS SDK
- **详细信息**: 参见 `iOS_WORKFLOW.md`
- **状态**: 暂时保留，专注后端开发

### 后端服务架构
```
┌─────────────────────────────────────────────────────────────┐
│                [RESERVED FOR LATER]                         │
│                   iOS Client                                │
│         SwiftUI Views │ ViewModels │ Services               │
├─────────────────────────────────────────────────────────────┤
│                FastAPI Web Server                           │
│   REST API │ WebSocket │ Middleware │ Authentication        │
├─────────────────────────────────────────────────────────────┤
│                API Controllers                               │
│      Auth │ Topics │ Matching │ Rooms │ Friends │ Media     │
├─────────────────────────────────────────────────────────────┤
│                   Use Cases                                  │
│  Match │ StartRoom │ JoinRoom │ EndRoom │ AddFriend │ Record │
│  GetHistory │ GetRecording │ SignUp │ SignIn │ SignOut      │
├─────────────────────────────────────────────────────────────┤
│                 Domain Layer                                 │
│   User │ Topic │ Room │ Match │ Friend │ Recording │ Message │
│          Policies │ Business Rules │ Entities                │
├─────────────────────────────────────────────────────────────┤
│               Infrastructure Layer                           │
│ Firebase │ LiveKit │ Redis │ Storage │ OpenAI │ FCM │ JWT    │
└─────────────────────────────────────────────────────────────┘
```

### 系统交互图
```
[RESERVED FOR LATER] ──HTTP/WebSocket──> FastAPI Server ──> Firebase
   iOS App                                      │                  │
   │                                            ├──> Redis         │
   │                                            ├──> OpenAI        │
   │                                            └──> LiveKit       │
   │                                                               │
   └──LiveKit SDK──> LiveKit Server ──> AI Agent ──[RESERVED]────┘
```

## 📊 当前状态

### ✅ 后端已完成 (15-20%)
- **基础Domain实体**: User、CallSession基础结构
- **LiveKit集成**: 完整的AI代理和音频处理
- **基础Use Case**: 部分通话逻辑抽象
- **项目架构**: 清晰的依赖关系设计

### ⚠️ 后端部分完成
- **Firebase集成**: 只有接口框架，核心方法未实现
- **Domain层**: 需要新增Topic、Match、Friend、Recording等实体

### ❌ 后端缺失组件
- **FastAPI服务器**: 无Web框架和HTTP接口
- **话题匹配系统**: 无匹配算法和队列
- **好友系统**: 无好友管理功能
- **录音系统**: 无录音存储和回放
- **多人聊天**: 当前只支持固定3人
- **API控制器层**: 无RESTful API实现
- **WebSocket支持**: 无实时通信接口
- **依赖注入容器**: 无组件装配
- **认证服务**: 无JWT/密码处理
- **通知系统**: 无推送通知
- **配置管理**: 无环境变量管理

### 📱 iOS客户端状态 [RESERVED FOR LATER]
- **当前状态**: 未开始 (0%) - 暂时保留
- **详细计划**: 参见 `iOS_WORKFLOW.md`
- **预计时间**: 26-35天
- **依赖**: 需要后端API服务完成
- **优先级**: 后端API完成后再开始

## 🚀 实现计划

### Phase 1: 核心基础设施 (预计4-5天)
#### 1.1 扩展Domain层
- [ ] 新增Topic实体（话题管理）
- [ ] 新增Match实体（匹配记录）
- [ ] 新增Friend实体（好友关系）
- [ ] 新增Recording实体（录音记录）
- [ ] 更新Room实体（支持多人聊天）
- [ ] 新增匹配策略和业务规则

#### 1.2 Firebase适配器实现
- [ ] 完成`FirebaseAdminService`类
- [ ] 实现用户CRUD操作
- [ ] 实现话题和匹配数据存储
- [ ] 实现好友关系管理
- [ ] 实现录音元数据存储
- [ ] 实现身份验证方法

#### 1.3 认证服务实现
- [ ] 实现JWT token服务
- [ ] 实现密码哈希服务
- [ ] 集成Firebase Auth

#### 1.4 依赖注入容器
- [ ] 创建IoC容器
- [ ] 实现依赖装配
- [ ] 配置管理系统

### Phase 2: 话题匹配系统 (预计3-4天)
#### 2.1 话题管理
- [ ] 话题分类和标签系统
- [ ] 话题向量化和相似度计算
- [ ] 话题推荐算法

#### 2.2 匹配引擎
- [ ] 实现匹配算法（基于话题和用户偏好）
- [ ] Redis队列管理（等待匹配的用户）
- [ ] 实时匹配通知
- [ ] 匹配失败fallback（与AI聊天）

#### 2.3 Use Case层
- [ ] FindMatch用例（寻找匹配）
- [ ] JoinWaitingQueue用例（加入等待队列）
- [ ] StartAIChat用例（开始AI对话）

### Phase 3: 多人聊天室 (预计2-3天)
#### 3.1 聊天室管理
- [ ] 动态房间创建和管理
- [ ] 多人加入/退出机制
- [ ] 房间状态同步

#### 3.2 录音系统
- [ ] 实时录音功能
- [ ] 录音文件存储（Firebase Storage）
- [ ] 录音回放和下载
- [ ] 转录文本生成和存储

#### 3.3 Use Case层
- [ ] CreateRoom用例（创建聊天室）
- [ ] JoinRoom用例（加入聊天室）
- [ ] LeaveRoom用例（离开聊天室）
- [ ] StartRecording用例（开始录音）
- [ ] GetRecording用例（获取录音）

### Phase 4: 社交功能 (预计2-3天)
#### 4.1 好友系统
- [ ] 好友请求和确认
- [ ] 好友列表管理
- [ ] 好友状态同步

#### 4.2 历史记录
- [ ] 聊天历史查看
- [ ] 录音历史管理
- [ ] 数据统计和分析

#### 4.3 Use Case层
- [ ] SendFriendRequest用例（发送好友请求）
- [ ] AcceptFriendRequest用例（接受好友请求）
- [ ] GetChatHistory用例（获取聊天历史）
- [ ] GetRecordingHistory用例（获取录音历史）

### Phase 5: API接口层 (预计3-4天)
#### 5.1 FastAPI控制器
- [ ] 用户认证接口 (`/api/auth/*`)
- [ ] 话题管理接口 (`/api/topics/*`)
- [ ] 匹配系统接口 (`/api/matching/*`)
- [ ] 聊天室接口 (`/api/rooms/*`)
- [ ] 好友系统接口 (`/api/friends/*`)
- [ ] 录音管理接口 (`/api/recordings/*`)
- [ ] 健康检查接口 (`/api/health`)

#### 5.2 中间件
- [ ] 认证中间件
- [ ] 错误处理中间件
- [ ] 日志中间件
- [ ] 限流中间件

#### 5.3 WebSocket支持
- [ ] 实时匹配通知
- [ ] 房间状态同步
- [ ] 好友状态更新

### Phase 6: 通知与部署 (预计2-3天)
#### 6.1 推送通知
- [ ] FCM通知实现
- [ ] 匹配成功通知
- [ ] 好友请求通知
- [ ] 聊天室邀请通知

#### 6.2 部署配置
- [ ] Docker容器化
- [ ] 环境变量配置
- [ ] Redis集群配置
- [ ] 部署脚本

#### 6.3 测试
- [ ] 单元测试
- [ ] 集成测试
- [ ] API测试
- [ ] 性能测试

## 🎯 API接口设计

### 认证接口
```
POST /api/auth/signup     # 用户注册
POST /api/auth/signin     # 用户登录
POST /api/auth/signout    # 用户登出
GET  /api/auth/profile    # 获取用户信息
PUT  /api/auth/profile    # 更新用户信息
```

### 话题管理接口
```
GET  /api/topics          # 获取话题列表
POST /api/topics          # 创建新话题
GET  /api/topics/popular  # 获取热门话题
GET  /api/topics/search   # 搜索话题
```

### 匹配系统接口
```
POST /api/matching/find   # 寻找匹配（指定话题）
POST /api/matching/queue  # 加入等待队列
DELETE /api/matching/queue # 退出等待队列
GET  /api/matching/status # 获取匹配状态
```

### 聊天室接口
```
POST /api/rooms/create    # 创建聊天室
POST /api/rooms/{id}/join # 加入聊天室
POST /api/rooms/{id}/leave # 离开聊天室
GET  /api/rooms/{id}      # 获取聊天室信息
POST /api/rooms/{id}/end  # 结束聊天室
GET  /api/rooms/history   # 获取聊天历史
```

### 好友系统接口
```
POST /api/friends/request # 发送好友请求
POST /api/friends/accept  # 接受好友请求
POST /api/friends/reject  # 拒绝好友请求
GET  /api/friends         # 获取好友列表
DELETE /api/friends/{id}  # 删除好友
GET  /api/friends/requests # 获取好友请求列表
```

### 录音管理接口
```
GET  /api/recordings      # 获取录音列表
GET  /api/recordings/{id} # 获取录音详情
GET  /api/recordings/{id}/download # 下载录音文件
GET  /api/recordings/{id}/transcript # 获取转录文本
DELETE /api/recordings/{id} # 删除录音
```

### 系统接口
```
GET  /api/health          # 健康检查
GET  /api/docs           # API文档
```

### WebSocket接口
```
WS   /ws/matching         # 匹配状态实时更新
WS   /ws/rooms/{id}       # 聊天室状态同步
WS   /ws/friends          # 好友状态更新
```

## 📱 客户端集成

### LiveKit客户端
```javascript
// 前端客户端连接LiveKit
const token = await fetch('/api/calls/start', {
  method: 'POST',
  body: JSON.stringify({ user_a_id: userId })
});

const room = new Room();
await room.connect(LIVEKIT_URL, token);
```

### AI代理集成
```python
# AI代理监听 http://localhost:8000/invite
# 当满足邀请条件时，AI会调用此接口
await context.session.http.post(
    f"{ORCHESTRATOR_URL}/invite",
    json={
        "room": room_name,
        "identity": user_b_id,
        "reason": "Ready for 3-way call"
    }
)
```

## 🔐 安全考虑

### 认证和授权
- JWT token验证
- Firebase Auth集成
- API rate limiting
- 输入验证和清理

### 数据保护
- 通话记录加密存储
- 个人信息保护
- GDPR合规性考虑

## 🚦 成功指标

### 功能指标
- [ ] 用户可以注册和登录
- [ ] 用户可以选择话题并寻找匹配
- [ ] 匹配算法能有效匹配相同兴趣用户
- [ ] 无匹配时可以与AI聊天
- [ ] 支持多人语音聊天室
- [ ] AI能够有效主持和引导对话
- [ ] 聊天结束后可以加好友
- [ ] 录音功能正常工作
- [ ] 用户可以回放和下载录音
- [ ] 转录文本准确生成

### 性能指标
- [ ] API响应时间 < 200ms
- [ ] 语音延迟 < 100ms
- [ ] 匹配算法响应时间 < 3秒
- [ ] 并发支持 > 100用户
- [ ] 系统可用性 > 99%
- [ ] 录音文件上传/下载速度 < 5秒

### 用户体验指标
- [ ] 匹配成功率 > 80%
- [ ] 用户留存率 > 60%
- [ ] 好友添加率 > 40%
- [ ] 录音回放使用率 > 30%

## 🎁 下一步行动

### 🏃 立即开始 (专注后端)
**策略**: 完成后端API服务，前端开发暂时保留

#### 后端 Phase 1.1 (1-2天) - 立即开始
1. **创建FastAPI项目**: 设置基础Web服务器
2. **扩展Domain层**: 新增Topic、Match、Friend、Recording实体
3. **重构现有实体**: 更新Room实体以支持多人聊天
4. **添加匹配策略**: 实现话题匹配的业务规则

#### 后端 Phase 1.2-1.4 (3-4天) - 接下来
1. **完成Firebase适配器**: 实现所有数据存储功能
2. **实现认证服务**: JWT和密码处理
3. **构建依赖注入**: 组件装配和配置管理
4. **创建基础API控制器**: 实现核心RESTful接口

### 🚀 后端开发继续 (Phase 2-3)
**专注后端API开发**

#### Phase 2: 话题匹配系统 (预计3-4天)
1. **构建匹配系统**: 话题匹配算法和队列管理
2. **集成Redis**: 实现等待队列和缓存
3. **完善API接口**: 实现所有业务功能接口
4. **添加WebSocket**: 实现实时通信

#### Phase 3: 多人聊天室 (预计2-3天)
1. **聊天室管理**: 动态房间创建和管理
2. **录音系统**: 实时录音功能和存储
3. **LiveKit集成**: 完善音频流管理

#### iOS客户端开发 [RESERVED FOR LATER]
- **状态**: 暂时保留，等待后端API完成
- **详细计划**: 参见 `iOS_WORKFLOW.md`
- **开始条件**: 后端API基本功能完成且稳定

### 🎯 当前阶段目标
构建**完整的后端API服务**，包含：
- 🖥️ **FastAPI Web服务**: 高性能RESTful API
- 🔥 **Firebase集成**: 完整的数据存储和认证
- 🎯 **智能话题匹配**: 基于AI的用户匹配算法
- 🤖 **AI主持和引导**: GPT-4驱动的聊天助手
- 👥 **多人语音聊天**: LiveKit音频流管理
- 👫 **社交好友系统**: 完整的社交功能API
- 🎵 **录音管理功能**: 录音存储和回放API
- 🔌 **WebSocket支持**: 实时通信接口

**当前开发时间**: 
- 后端API: 16-22天 (当前专注)
- iOS客户端: [RESERVED FOR LATER] 26-35天

### 🎯 最终目标 [RESERVED FOR LATER]
- 📱 **iOS客户端**: SwiftUI + LiveKit iOS SDK
- 🔗 **端到端集成**: 完整的语音社交平台
- 🚀 **产品发布**: App Store上线

---

**让我们开始构建这个令人兴奋的AI语音社交应用！** 🚀

## 💡 数据库设计预览

### 核心实体关系
```
User (用户) ─────┐
├─ Friends (好友关系)
├─ MatchRequests (匹配请求)
├─ RoomParticipants (房间参与者)
└─ Recordings (录音记录)

Topic (话题) ─────┐
├─ UserTopics (用户话题偏好)
├─ MatchRequests (匹配请求)
└─ Rooms (聊天室)

Room (聊天室) ─────┐
├─ RoomParticipants (参与者)
├─ Messages (消息记录)
└─ Recordings (录音记录)
```

这个设计为我们的AI语音社交平台提供了强大的数据基础！ 