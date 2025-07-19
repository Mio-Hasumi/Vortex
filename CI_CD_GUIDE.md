# VoiceApp CI/CD Integration Guide

This guide provides complete instructions for integrating VoiceApp's automated testing and documentation pipeline with various CI/CD platforms.

## 🚀 Quick Start

### One-Command Testing
```bash
# Run complete pipeline locally
./scripts/run_complete_test.sh

# Docker-based testing
./scripts/docker_test.sh

# Simple smoke tests
./scripts/run_smoke_tests.sh
```

## 🔧 CI/CD Platform Configurations

### 🐙 GitHub Actions

**File:** `.github/workflows/api-testing.yml`

**Features:**
- ✅ Multi-environment support (staging/production)
- 🔥 Comprehensive smoke tests
- 📚 Automatic documentation generation
- ⚡ Performance testing
- 🔒 Security scanning
- 📢 PR comments with results
- 🌐 GitHub Pages deployment

**Setup:**
1. Add repository secrets:
   ```
   STAGING_API_URL: https://staging-api.voiceapp.com
   PRODUCTION_API_URL: https://api.voiceapp.com
   FIREBASE_CREDENTIALS: <base64-encoded-firebase-credentials.json>
   OPENAI_API_KEY: <your-openai-key>
   LIVEKIT_API_KEY: <your-livekit-key>
   LIVEKIT_API_SECRET: <your-livekit-secret>
   LIVEKIT_URL: <your-livekit-url>
   SLACK_WEBHOOK_URL: <optional-slack-webhook>
   ```

2. Enable GitHub Pages:
   - Go to repository Settings → Pages
   - Select "GitHub Actions" as source
   - Documentation will be available at: `https://your-org.github.io/your-repo/api-docs/`

**Triggering:**
```bash
# Manual trigger with environment selection
gh workflow run api-testing.yml -f environment=production -f run_docs=true

# View workflow status
gh run list
```

### 🦊 GitLab CI/CD

**File:** `.gitlab-ci.yml`

**Features:**
- 🐳 Docker-based testing
- 📚 GitLab Pages integration
- 🔒 Security scanning with reports
- ⚡ Performance testing
- 🔗 Integration testing

**Setup:**
1. Add CI/CD variables in GitLab:
   ```
   STAGING_API_URL: https://staging-api.voiceapp.com
   PRODUCTION_API_URL: https://api.voiceapp.com
   FIREBASE_CREDENTIALS: <base64-encoded-firebase-credentials.json>
   OPENAI_API_KEY: <your-openai-key>
   LIVEKIT_API_KEY: <your-livekit-key>
   LIVEKIT_API_SECRET: <your-livekit-secret>
   LIVEKIT_URL: <your-livekit-url>
   ```

2. Enable GitLab Pages:
   - Documentation automatically deployed to: `https://your-org.gitlab.io/your-repo/`

**Pipeline Stages:**
- `test` - Smoke tests, security scans
- `build` - Docker builds
- `docs` - Documentation generation
- `deploy` - Pages deployment

### 🏗️ Jenkins

**File:** `Jenkinsfile`

**Features:**
- 🔄 Parallel testing stages
- 📊 Test result publishing
- 📚 HTML report publishing
- 🔔 Slack notifications
- ⚡ Performance testing
- 🔒 Security scanning

**Setup:**
1. Install required Jenkins plugins:
   ```
   - Pipeline
   - Docker Pipeline
   - HTML Publisher
   - Test Results Analyzer
   - Slack Notification
   ```

2. Configure Jenkins credentials:
   ```
   STAGING_API_URL: https://staging-api.voiceapp.com
   PRODUCTION_API_URL: https://api.voiceapp.com
   FIREBASE_CREDENTIALS: <firebase-credentials.json>
   OPENAI_API_KEY: <your-openai-key>
   SLACK_WEBHOOK: <slack-webhook-url>
   ```

3. Create multibranch pipeline pointing to your repository

### 🐳 Docker-based Testing

**Files:** `docker-compose.test.yml`, `Dockerfile.test`, `scripts/docker_test.sh`

**Usage:**
```bash
# Full Docker testing pipeline
./scripts/docker_test.sh

# Run individual services
docker-compose -f docker-compose.test.yml up smoke-tests
docker-compose -f docker-compose.test.yml up docs-generator

# Background mode
./scripts/docker_test.sh --detach

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

**Benefits:**
- 🔒 Isolated testing environment
- 📦 Consistent across all platforms
- 🚀 Easy local reproduction
- ⚡ Parallel test execution

## 🎯 CI/CD Best Practices

### 1. Environment Strategy
```bash
# Development (feature branches)
- Smoke tests only
- Quick feedback
- Documentation preview

# Staging (develop branch)
- Full test suite
- Performance testing
- Security scanning
- Documentation deployment

# Production (main branch)
- All tests
- Performance benchmarks
- Security audits
- Final documentation
```

### 2. Test Execution Strategy

**Fast Feedback Loop:**
```bash
# On every commit
1. Health checks (30s)
2. Smoke tests (2-5 min)
3. Basic documentation (1 min)

# On PR/MR
1. Full smoke tests
2. Security scanning
3. Performance testing
4. Documentation generation

# Nightly/Scheduled
1. Integration tests
2. Load testing
3. Security audits
4. Dependency updates
```

### 3. Secrets Management

**Required Secrets:**
```bash
# Firebase Authentication
FIREBASE_CREDENTIALS=<base64-encoded-json>

# API Keys
OPENAI_API_KEY=sk-...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

# Environment URLs
STAGING_API_URL=https://staging-api.voiceapp.com
PRODUCTION_API_URL=https://api.voiceapp.com

# Notifications (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

**Security Best Practices:**
- ✅ Use platform-provided secret management
- ✅ Rotate secrets regularly
- ✅ Scope secrets to minimum required access
- ✅ Never commit secrets to code
- ✅ Use separate credentials for testing

### 4. Artifact Management

**Test Results:**
```bash
# Artifacts to preserve
- test-results/           # Test output and logs
- docs/                   # Generated documentation
- performance-results.txt # Performance metrics
- *-report.json          # Security scan reports
```

**Retention Policies:**
- Test results: 30 days
- Documentation: 90 days
- Security reports: 30 days
- Performance data: 60 days

### 5. Notification Strategy

**Success Notifications:**
- 📧 Main branch deployments
- 📱 Performance degradations
- 🔒 Security issues found

**Failure Notifications:**
- 🚨 All test failures
- 💥 Build failures
- ⚠️ Security vulnerabilities

## 🔍 Monitoring & Alerting

### 1. Test Health Monitoring
```bash
# Monitor test success rates
- Smoke test pass rate > 95%
- Performance test variance < 20%
- Documentation generation success > 99%

# Alert on trends
- Increasing test failures
- Performance degradation
- Documentation build failures
```

### 2. API Health Monitoring
```bash
# Endpoint monitoring
GET /              # Basic health
GET /api/ai-host/health  # AI services
GET /openapi.json  # Documentation endpoint

# Performance thresholds
- Response time < 200ms (health endpoints)
- Response time < 2s (AI endpoints)
- Uptime > 99.9%
```

### 3. Infrastructure Monitoring
```bash
# CI/CD pipeline health
- Build time trends
- Test execution time
- Resource usage
- Queue wait times

# Dependencies
- Redis connectivity
- Firebase auth status
- External API availability
```

## 🚀 Deployment Integration

### 1. Staging Deployment
```bash
# Automatic deployment on develop branch
1. Run full test suite
2. Deploy to staging
3. Run integration tests
4. Generate staging documentation
5. Notify team of deployment
```

### 2. Production Deployment
```bash
# Manual/approved deployment on main branch
1. Run production test suite
2. Performance validation
3. Security scan approval
4. Deploy to production
5. Post-deployment verification
6. Update production documentation
```

### 3. Rollback Strategy
```bash
# Automated rollback triggers
- Health check failures
- Error rate > 5%
- Performance degradation > 50%

# Rollback process
1. Revert to previous version
2. Run smoke tests
3. Notify team
4. Generate incident report
```

## 📊 Metrics & Reporting

### 1. Test Metrics
```bash
# Track over time
- Test execution time
- Test pass/fail rates
- Coverage metrics
- Performance benchmarks

# Weekly reports
- Test reliability trends
- Performance regression alerts
- Security issue summaries
```

### 2. Documentation Metrics
```bash
# Documentation health
- Build success rate
- Update frequency
- API coverage
- Link validation

# Usage metrics
- Documentation page views
- Postman collection downloads
- API endpoint usage
```

### 3. CI/CD Pipeline Metrics
```bash
# Pipeline performance
- Build duration trends
- Queue wait times
- Resource utilization
- Cost optimization

# Success metrics
- Deployment frequency
- Lead time for changes
- Mean time to recovery
- Change failure rate
```

## 🎯 Getting Started Checklist

### For GitHub Actions:
- [ ] Copy `.github/workflows/api-testing.yml`
- [ ] Add required repository secrets
- [ ] Enable GitHub Pages
- [ ] Configure branch protection rules
- [ ] Set up Slack notifications (optional)

### For GitLab CI/CD:
- [ ] Copy `.gitlab-ci.yml`
- [ ] Add CI/CD variables
- [ ] Enable GitLab Pages
- [ ] Configure merge request pipelines
- [ ] Set up security scanning

### For Jenkins:
- [ ] Copy `Jenkinsfile`
- [ ] Install required plugins
- [ ] Configure credentials
- [ ] Create multibranch pipeline
- [ ] Set up build triggers

### For Docker Testing:
- [ ] Copy Docker files
- [ ] Make scripts executable
- [ ] Test locally first
- [ ] Configure CI platform

### For All Platforms:
- [ ] Test with sample data
- [ ] Verify documentation generation
- [ ] Check notification settings
- [ ] Monitor first few runs
- [ ] Train team on new workflow

---

## 🎉 Success!

Your VoiceApp API now has comprehensive CI/CD integration with:

✅ **Automated Testing** - Smoke tests, performance tests, security scans  
✅ **Documentation Generation** - OpenAPI specs, Postman collections, HTML docs  
✅ **Multi-Platform Support** - GitHub, GitLab, Jenkins, Docker  
✅ **Monitoring & Alerting** - Real-time notifications and health checks  
✅ **Best Practices** - Security, scalability, maintainability  

**Next Steps:**
1. Choose your CI/CD platform
2. Follow the setup checklist
3. Run your first pipeline
4. Monitor and iterate
5. Share documentation with your team

Happy automating! 🚀 