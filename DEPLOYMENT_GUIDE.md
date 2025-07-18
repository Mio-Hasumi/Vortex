# 🚀 VoiceApp 后端部署指南

## 📊 **当前状态**: 本地开发 → 生产环境

### 🚨 **部署需求**
- **Redis**: 当前使用 localhost，需要真实的Redis服务器
- **应用服务器**: 需要云服务器运行FastAPI应用
- **域名**: 需要SSL证书和域名配置

---

## 💡 **推荐部署方案**

### **🥇 Option 1: DigitalOcean Droplet (推荐)**

**成本**: ~$12-24/月
**优势**: 完全控制、性能稳定、成本合理

#### 1. **Droplet 配置**
```bash
# 推荐配置
CPU: 2 vCPUs
RAM: 4GB
Storage: 80GB SSD
OS: Ubuntu 22.04
估计成本: $24/月
```

#### 2. **服务架构**
```
┌─────────────────────────────────────────┐
│            DigitalOcean Droplet         │
├─────────────────────────────────────────┤
│  🐳 Docker Compose Stack:              │
│  ├── FastAPI App (Port 8000)           │
│  ├── Redis Server (Port 6379)          │
│  ├── Nginx Reverse Proxy (Port 80/443) │
│  └── SSL Certificate (Let's Encrypt)   │
├─────────────────────────────────────────┤
│  🔥 External Services:                  │
│  ├── Firebase (Already configured)     │
│  ├── LiveKit (Already configured)      │
│  └── Domain + DNS                      │
└─────────────────────────────────────────┘
```

#### 3. **部署步骤**

##### Step 1: 创建Droplet
```bash
# 1. 在DigitalOcean创建Droplet
# 2. 选择Ubuntu 22.04 LTS
# 3. 添加SSH密钥
# 4. 配置防火墙规则
```

##### Step 2: 服务器初始化
```bash
# 连接到服务器
ssh root@your-droplet-ip

# 更新系统
apt update && apt upgrade -y

# 安装Docker和Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 安装Docker Compose
apt install docker-compose -y

# 创建应用目录
mkdir -p /app/voiceapp
cd /app/voiceapp
```

##### Step 3: 配置Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_HOST=redis
    volumes:
      - ./voiceapp-8f09a-firebase-adminsdk-fbsvc-4f84f483d1.json:/app/firebase-key.json
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - app
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    restart: unless-stopped

volumes:
  redis_data:
```

##### Step 4: 配置生产环境变量
```bash
# .env.production
APP_NAME=VoiceApp Backend
DEBUG=false

# Redis (内部Docker网络)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_URL=redis://redis:6379/0

# Firebase (保持不变)
FIREBASE_PROJECT_ID=voiceapp-8f09a
FIREBASE_CREDENTIALS_PATH=/app/firebase-key.json

# LiveKit (保持不变)
LIVEKIT_API_KEY=APIQgCgiwHnYkue
LIVEKIT_API_SECRET=Reqvp9rjEeLAe9XZOsdjGwPFs4qJcp5VEKTVIUpn40hA
LIVEKIT_SERVER_URL=wss://voodooo-5oh49lvx.livekit.cloud

# 域名配置
ALLOWED_ORIGINS=["https://yourapp.com", "https://www.yourapp.com"]
```

##### Step 5: 创建Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

##### Step 6: 部署命令
```bash
# 上传代码到服务器
scp -r . root@your-droplet-ip:/app/voiceapp/

# 在服务器上启动服务
cd /app/voiceapp
docker-compose up -d

# 查看状态
docker-compose logs -f
```

---

### **🥈 Option 2: 云Redis服务**

**成本**: ~$15-30/月
**优势**: 托管服务、自动备份、高可用

#### 2.1 **Redis Cloud (推荐)**
```bash
# Redis Labs提供的托管Redis
# 免费层: 30MB
# 付费层: $15/月起 (250MB)
# URL示例: redis://username:password@host:port/db
```

#### 2.2 **DigitalOcean Managed Redis**
```bash
# DigitalOcean提供的托管Redis
# 成本: $15/月起
# 自动备份、监控、高可用
```

#### 配置示例:
```bash
# 使用云Redis服务
REDIS_HOST=your-redis-cloud-host.com
REDIS_PORT=12345
REDIS_PASSWORD=your-secure-password
REDIS_URL=redis://:your-secure-password@your-redis-cloud-host.com:12345/0
```

---

### **🥉 Option 3: 完全云服务**

**成本**: ~$50-100/月
**优势**: 完全托管、自动扩展、高可用

#### 3.1 **使用 Railway/Render/Heroku**
```bash
# 应用托管: Railway/Render ($7-20/月)
# Redis: Redis Cloud ($15/月)
# 文件存储: Firebase (已配置)
# 语音服务: LiveKit (已配置)
```

---

## 🎯 **立即行动计划**

### **推荐方案: DigitalOcean Droplet**

**为什么选择这个方案?**
- ✅ 成本合理 ($24/月)
- ✅ 完全控制服务器
- ✅ 可以运行完整的Docker栈
- ✅ 良好的性能和稳定性
- ✅ 容易扩展和维护

### **immediate Steps:**

1. **🚀 立即可做**:
   ```bash
   # 创建Docker配置文件
   # 准备生产环境配置
   # 测试本地Docker部署
   ```

2. **💰 需要付费**:
   ```bash
   # 购买DigitalOcean Droplet ($24/月)
   # 可选: 购买域名 ($10-15/年)
   # 可选: 配置SSL证书 (免费 Let's Encrypt)
   ```

3. **⏱️ 部署时间**: 2-4小时

---

## 📊 **成本对比**

| 方案 | 月成本 | 年成本 | 优势 | 劣势 |
|------|--------|--------|------|------|
| **DigitalOcean Droplet** | $24 | $288 | 完全控制、性能好 | 需要维护 |
| **云Redis + 应用托管** | $30-50 | $360-600 | 托管服务、省心 | 成本较高 |
| **完全云服务** | $50-100 | $600-1200 | 完全托管、自动扩展 | 成本最高 |

---

## 🛠️ **下一步操作**

### **Option A: 快速测试部署**
1. 创建最小的DigitalOcean Droplet ($6/月)
2. 部署应用进行测试
3. 验证所有功能正常
4. 升级到生产配置

### **Option B: 直接生产部署**
1. 创建推荐配置的Droplet ($24/月)
2. 配置完整的生产环境
3. 设置监控和备份
4. 配置域名和SSL

---

## 🔧 **需要您的决定**

**我们需要您确认:**
1. **预算**: 您愿意每月投入多少? ($24推荐)
2. **复杂度**: 您更喜欢自己管理还是托管服务?
3. **时间**: 您希望多快部署? (2-4小时可完成)

**准备好开始部署了吗?** 🚀 