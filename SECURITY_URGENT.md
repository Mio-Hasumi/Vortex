# 🚨 URGENT: Firebase密钥泄漏处理

## 问题描述
Firebase服务账号密钥文件 `voiceapp-8f09a-firebase-adminsdk-fbsvc-4f84f483d1.json` 被意外推送到GitHub public repository，这是一个严重的安全漏洞。

## 立即采取的行动

### 1. 🔒 立即撤销当前Firebase密钥
```bash
# 登录Firebase Console
# 1. 进入 https://console.firebase.google.com/
# 2. 选择项目 "voiceapp-8f09a"
# 3. 进入 Project Settings > Service accounts
# 4. 删除当前的service account密钥
# 5. 生成新的密钥
```

### 2. 🔄 重新生成新的Firebase密钥
1. 在Firebase Console中生成新的服务账号密钥
2. 下载新的JSON文件
3. 重命名为 `firebase-credentials.json`
4. 放在项目根目录（已被.gitignore忽略）

### 3. 🔐 更新环境变量
```bash
# 对于Railway部署
railway variables set FIREBASE_CREDENTIALS="$(cat firebase-credentials.json)"

# 对于其他平台
export FIREBASE_CREDENTIALS="$(cat firebase-credentials.json)"
```

### 4. 🚫 已采取的预防措施
- ✅ 从git历史中移除了泄漏的密钥文件
- ✅ 更新了.gitignore防止未来泄漏
- ✅ 创建了新的安全分支 `backend-secure`

## 文件命名约定
- ❌ 旧文件: `voiceapp-8f09a-firebase-adminsdk-fbsvc-4f84f483d1.json`
- ✅ 新文件: `firebase-credentials.json` (已在.gitignore中)

## 更新代码配置
更新 `infrastructure/config.py` 中的文件路径：
```python
# 旧路径
FIREBASE_CREDENTIALS_PATH = "voiceapp-8f09a-firebase-adminsdk-fbsvc-4f84f483d1.json"

# 新路径
FIREBASE_CREDENTIALS_PATH = "firebase-credentials.json"
```

## 检查清单
- [ ] 撤销泄漏的Firebase密钥
- [ ] 生成新的Firebase密钥
- [ ] 更新本地文件
- [ ] 更新环境变量
- [ ] 测试新配置
- [ ] 删除此文档（完成后）

## 教训
永远不要将以下文件提交到git：
- `*.json` (Firebase密钥)
- `.env` (环境变量)
- `*.pem` (SSL证书)
- `*.key` (私钥)
- `config.ini` (配置文件) 