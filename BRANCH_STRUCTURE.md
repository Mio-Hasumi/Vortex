# 🌳 VoiceApp 仓库分支结构

## 📂 **分支说明**

### 🐍 **`python-backend`** (当前分支)
- **内容**: 完整的Python FastAPI后端
- **状态**: ✅ **生产就绪**
- **用途**: 后端API服务
- **技术栈**: Python 3.12 + FastAPI + Firebase + Redis + LiveKit

### 📱 **`main`** (主分支)
- **内容**: 历史遗留的React Native代码
- **状态**: ⚠️ **已废弃**
- **计划**: 将被清理或保留作为历史记录

---

## 🚀 **推荐的部署流程**

### **对于后端部署**:
```bash
# 使用python-backend分支
git checkout python-backend
git pull origin python-backend

# Railway部署
# 连接GitHub仓库时选择python-backend分支
```

### **对于iOS开发**:
```bash
# 创建新的iOS分支
git checkout python-backend
git checkout -b ios-client
# 开始iOS开发
```

---

## 📋 **分支管理建议**

### **清理main分支**:
```bash
# 1. 备份main分支（如果需要）
git checkout main
git checkout -b main-backup

# 2. 重置main分支到python-backend
git checkout main
git reset --hard python-backend
git push origin main --force

# 3. 删除备份分支（如果不需要）
git branch -D main-backup
```

### **设置python-backend为默认分支**:
1. 在GitHub仓库设置中
2. 选择 "Default branch"
3. 改为 `python-backend`

---

## 🎯 **当前状态**

### ✅ **已完成**
- 后端代码推送到 `python-backend` 分支
- 完整的生产就绪后端
- 所有部署配置文件

### 📋 **下一步**
- 清理main分支（可选）
- 设置python-backend为默认分支
- 开始Railway部署
- 开始iOS开发

---

## 🔗 **相关链接**

- **GitHub仓库**: https://github.com/Mio-Hasumi/VoiceApp
- **后端分支**: https://github.com/Mio-Hasumi/VoiceApp/tree/python-backend
- **Railway部署**: 连接到python-backend分支

---

**🎉 恭喜！您的后端代码已经成功推送到GitHub！** 