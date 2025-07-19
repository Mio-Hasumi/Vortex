# GitHub Actions Setup Guide 🚀

Due to token permissions, the GitHub Actions workflow files need to be added manually. Here's how to enable automated CI/CD for this repository:

## 📁 **Add Workflow Files**

### 1. Create Directory Structure
```bash
mkdir -p .github/workflows
```

### 2. Copy Workflow Files
Copy these files from your local repository to the GitHub repository via web interface:

**File: `.github/workflows/api-testing.yml`**
- Location: `.github/workflows/api-testing.yml` (in this repository)
- Purpose: Complete API testing and documentation pipeline

## ⚙️ **Configure Repository Secrets**

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

### Required Secrets:
```
STAGING_API_URL: https://staging-api.voiceapp.com
PRODUCTION_API_URL: https://api.voiceapp.com
FIREBASE_CREDENTIALS: <base64-encoded-firebase-credentials.json>
OPENAI_API_KEY: <your-openai-key>
LIVEKIT_API_KEY: <your-livekit-key>
LIVEKIT_API_SECRET: <your-livekit-secret>
LIVEKIT_URL: <your-livekit-url>
```

### Optional Secrets:
```
SLACK_WEBHOOK_URL: <slack-webhook-for-notifications>
```

## 🌐 **Enable GitHub Pages**

1. Go to repository Settings → Pages
2. Select "GitHub Actions" as source
3. Your API documentation will be available at:
   `https://your-org.github.io/your-repo/api-docs/`

## ✅ **Verify Setup**

After adding the workflow file and secrets:

1. Push a commit to trigger the workflow
2. Go to Actions tab to see the pipeline running
3. Check that documentation is generated and deployed
4. Verify PR comments are working (make a test PR)

## 🔧 **Manual Workflow Creation Steps**

### Option 1: GitHub Web Interface
1. Go to your repository on GitHub
2. Click "Actions" tab
3. Click "New workflow"
4. Click "set up a workflow yourself"
5. Copy the content from `.github/workflows/api-testing.yml`
6. Commit the file

### Option 2: Command Line (with workflow permissions)
```bash
# If you have a token with workflow permissions:
git add .github/
git commit -m "Add GitHub Actions workflow"
git push origin main
```

## 🎯 **What You Get**

Once set up, every push and PR will:
- ✅ Run comprehensive API tests
- ✅ Generate fresh documentation
- ✅ Run performance benchmarks
- ✅ Scan for security issues
- ✅ Comment on PRs with results
- ✅ Deploy docs to GitHub Pages

## 📊 **Workflow Features**

- **Multi-environment support** (staging/production)
- **Manual triggers** with environment selection
- **Parallel test execution** for speed
- **Artifact storage** (test results, docs)
- **Notification integration** (Slack)
- **Security scanning** (Bandit)
- **Performance testing** (Apache Bench)

---

**Need help?** Check the `CI_CD_GUIDE.md` for complete setup instructions across all platforms! 