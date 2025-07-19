# VoiceApp - AI驱动的语音社交平台

> 🎯 **愿景**: 构建一个AI驱动的智能语音社交平台，通过话题匹配连接用户，AI主持引导对话，创造有意义的语音社交体验。

## 📱 项目概述

**VoiceApp** 是一个完整的语音社交平台，包含：

### 🖥️ 后端API服务 ✅ **生产就绪**
- **语言**: Python 3.12 + FastAPI
- **架构**: Clean Architecture + 依赖注入
- **认证**: Firebase Auth 集成
- **实时通信**: LiveKit Server（完全配置）
- **数据存储**: Firebase Firestore + Redis
- **状态**: 🟢 **核心功能完成，生产就绪！**

### 📱 iOS客户端应用 📋 **可开始开发**
- **语言**: Swift 5.9+ + SwiftUI
- **架构**: MVVM + Clean Architecture
- **音频**: LiveKit iOS SDK + AVFoundation
- **功能**: 完整的语音社交用户体验
- **状态**: 🔄 **后端就绪，可开始iOS开发**

## 🎯 核心功能

### 1. 智能话题匹配 ✅ **完成**
- 8个预设话题分类系统
- Redis驱动的实时匹配队列
- 智能用户匹配算法
- 用户话题偏好管理

### 2. 多人语音房间 ✅ **完成**
- LiveKit驱动的高质量实时音频
- 支持多人语音聊天
- 动态参与者管理
- 房间状态实时同步

### 3. 社交功能 ✅ **完成**
- 完整的好友系统（申请/接受/拒绝）
- 用户资料管理
- 好友列表和状态管理
- 用户封禁/解封功能

### 4. 录音系统 ✅ **完成**
- 自动录制聊天内容
- Firebase存储录音文件
- 录音元数据管理
- 录音下载和回放

### 5. AI功能 ⚠️ **框架就绪，待实现**
- ✅ AI实体模型设计完成
- ✅ LiveKit AI Agent集成框架
- 🔄 OpenAI GPT-4集成 (待实现)
- 🔄 语音识别(STT) (待实现)  
- 🔄 语音合成(TTS) (待实现)

## 🏗️ 技术架构

### 架构模式
- **Clean Architecture** (清洁架构)
- **Domain-Driven Design** (领域驱动设计)  
- **Dependency Injection** (依赖注入容器)

### 技术栈
```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Router                         │
│  Auth │ Topics │ Matching │ Rooms │ Friends │ Recordings   │
├─────────────────────────────────────────────────────────────┤
│                     Business Logic                         │
│    6 Use Cases │ Firebase Auth Middleware                  │
├─────────────────────────────────────────────────────────────┤
│                     Domain Layer                           │
│  User │ Topic │ Room │ Match │ Friend │ Recording entities │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure                           │
│ Firebase │ LiveKit │ Redis │ ~~OpenAI (待集成)~~          │
└─────────────────────────────────────────────────────────────┘
```

### 核心服务
- 🔥 **Firebase**: 认证 + Firestore数据库 + 文件存储
- 🎬 **LiveKit**: 实时语音通信服务
- 📦 **Redis**: 匹配队列 + 缓存服务
- ~~🧠 **OpenAI**: GPT-4 + STT + TTS (计划集成)~~

## 🚀 快速开始

### 环境配置
```bash
# 克隆项目
git clone [repository-url]
cd VoiceApp-martin

# 安装依赖
pip install -r requirements.txt

# 环境变量配置
cp .env.example .env
# 编辑 .env 配置以下变量:
# FIREBASE_CREDENTIALS_BASE64=your_firebase_credentials
# LIVEKIT_API_KEY=your_livekit_key  
# LIVEKIT_API_SECRET=your_livekit_secret
# REDIS_URL=redis://localhost:6379 (或 Railway Redis)
```

### 本地运行
```bash
# 启动开发服务器
python main.py

# 或使用uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API文档
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📊 功能完成度

### ✅ 核心语音社交功能 (100% 完成)
| 模块 | API端点 | 状态 |
|------|---------|------|
| **认证系统** | 4个 | ✅ Firebase集成完成 |
| **用户管理** | 3个 | ✅ 完整CRUD |
| **话题系统** | 2个 | ✅ 8个预设话题 |
| **匹配系统** | 4个 | ✅ Redis队列 |
| **语音房间** | 5个 | ✅ LiveKit集成 |
| **好友系统** | 6个 | ✅ 完整社交功能 |
| **录音系统** | 4个 | ✅ Firebase存储 |

**总计**: **28个API端点** 全部实现并测试通过

### ⚠️ AI功能 (框架就绪，待实现)
- ✅ 实体设计: `AIHostSession`模型完成
- ✅ LiveKit集成: AI Agent框架就绪
- 🔄 **需要实现**: OpenAI GPT-4 + STT + TTS集成

## 🌐 生产部署

### Railway部署 (推荐)
```bash
# 连接Railway
railway login
railway init
railway up

# 环境变量配置
railway variables:set FIREBASE_CREDENTIALS_BASE64=your_base64_creds
```
详见: `RAILWAY_GUIDE.md`

### 系统状态
- ✅ **核心功能**: 生产就绪
- ✅ **数据库**: Firebase + Redis集群
- ✅ **认证**: Firebase Auth安全认证
- ✅ **实时通信**: LiveKit高可用
- ⚠️ **AI功能**: 框架完成，OpenAI待集成

## 📱 iOS客户端开发

**当前状态**: 后端API完全就绪，可立即开始iOS开发

### 可用功能
1. **用户注册/登录** → Firebase Auth SDK
2. **话题选择** → `/api/topics/*` 端点  
3. **智能匹配** → `/api/matching/*` 端点
4. **语音聊天** → LiveKit iOS SDK
5. **好友系统** → `/api/friends/*` 端点
6. **录音回放** → `/api/recordings/*` 端点

## 📈 开发路线图

### Phase 1: 核心功能 ✅ **已完成**
- [x] 后端API服务 (28个端点)
- [x] Firebase认证集成
- [x] LiveKit语音通信
- [x] Redis匹配队列
- [x] 完整社交功能
- [x] 生产部署配置

### Phase 2: AI功能集成 ⚠️ **进行中**
- [ ] OpenAI GPT-4集成 (对话引擎)
- [ ] 语音识别STT (语音转文字)  
- [ ] 语音合成TTS (AI语音输出)
- [ ] AI主持人逻辑实现

### Phase 3: iOS客户端 📋 **可开始**
- [ ] iOS项目架构
- [ ] LiveKit iOS SDK集成
- [ ] SwiftUI用户界面
- [ ] Firebase iOS SDK集成

## 🎉 项目状态

**🟢 核心语音社交平台**: 生产就绪！  
**🟡 AI增强功能**: 框架完成，OpenAI集成待实现  
**🔄 iOS客户端**: 后端就绪，可开始开发

**下一步**: AI功能集成 或 iOS客户端开发并行进行 