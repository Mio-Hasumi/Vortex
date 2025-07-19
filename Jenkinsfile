pipeline {
    agent any
    
    environment {
        PYTHON_VERSION = '3.9'
        REDIS_URL = 'redis://localhost:6379'
        API_BASE_URL = 'http://localhost:8000'
    }
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        retry(2)
    }
    
    triggers {
        // Run daily at 2 AM
        cron('0 2 * * *')
        // Poll SCM every 5 minutes for changes
        pollSCM('H/5 * * * *')
    }
    
    stages {
        stage('🔍 Checkout & Setup') {
            steps {
                echo '📥 Checking out code...'
                checkout scm
                
                echo '🐍 Setting up Python environment...'
                sh '''
                    python3 --version
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install aiohttp websockets firebase-admin requests
                '''
            }
        }
        
        stage('🔍 Health Check') {
            steps {
                echo '🔍 Starting basic health checks...'
                sh '''
                    . venv/bin/activate
                    python3 -c "import sys; print(f'Python: {sys.version}')"
                    pip list | grep -E "(fastapi|redis|firebase)"
                '''
            }
        }
        
        stage('🚀 Start Services') {
            parallel {
                stage('Redis') {
                    steps {
                        echo '🔥 Starting Redis...'
                        sh '''
                            # Start Redis in background
                            redis-server --daemonize yes --port 6379
                            sleep 2
                            redis-cli ping
                        '''
                    }
                }
                
                stage('API Server') {
                    steps {
                        echo '🚀 Starting VoiceApp API...'
                        sh '''
                            . venv/bin/activate
                            export REDIS_URL=redis://localhost:6379
                            export DEBUG=true
                            export PORT=8000
                            
                            # Start server in background
                            python3 main.py &
                            export SERVER_PID=$!
                            echo $SERVER_PID > server.pid
                            
                            # Wait for server to be ready
                            echo "⏳ Waiting for API server to start..."
                            for i in {1..30}; do
                                if curl -f http://localhost:8000/ >/dev/null 2>&1; then
                                    echo "✅ API server is ready"
                                    break
                                fi
                                echo "Attempt $i/30 - waiting..."
                                sleep 2
                            done
                            
                            # Verify server is responding
                            curl -f http://localhost:8000/ || exit 1
                        '''
                    }
                }
            }
        }
        
        stage('🔥 Smoke Tests') {
            steps {
                echo '🧪 Running comprehensive smoke tests...'
                script {
                    try {
                        sh '''
                            . venv/bin/activate
                            python3 scripts/smoke_test.py --base-url http://localhost:8000 --verbose
                        '''
                        currentBuild.result = 'SUCCESS'
                    } catch (Exception e) {
                        currentBuild.result = 'UNSTABLE'
                        echo "❌ Smoke tests failed: ${e.getMessage()}"
                    }
                }
            }
            post {
                always {
                    // Archive test results
                    archiveArtifacts artifacts: 'test-results/**/*', allowEmptyArchive: true
                    
                    // Publish test results if available
                    publishTestResults testResultsPattern: 'test-results.xml'
                }
            }
        }
        
        stage('📚 Generate Documentation') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                echo '📚 Generating API documentation...'
                sh '''
                    . venv/bin/activate
                    python3 scripts/generate_docs.py --base-url http://localhost:8000 --output-dir docs
                '''
            }
            post {
                success {
                    // Archive documentation
                    archiveArtifacts artifacts: 'docs/**/*', allowEmptyArchive: false
                    
                    // Publish HTML reports
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'docs',
                        reportFiles: 'api_docs.html',
                        reportName: 'API Documentation',
                        reportTitles: 'VoiceApp API Documentation'
                    ])
                }
            }
        }
        
        stage('🐳 Docker Tests') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                echo '🐳 Running Docker-based tests...'
                script {
                    try {
                        sh '''
                            # Stop local services first
                            if [ -f server.pid ]; then
                                kill $(cat server.pid) || true
                                rm server.pid
                            fi
                            redis-cli shutdown || true
                            
                            # Run Docker tests
                            chmod +x scripts/docker_test.sh
                            ./scripts/docker_test.sh
                        '''
                    } catch (Exception e) {
                        echo "⚠️ Docker tests failed: ${e.getMessage()}"
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
        }
        
        stage('⚡ Performance Tests') {
            when {
                anyOf {
                    branch 'main'
                    triggeredBy 'TimerTrigger'
                }
            }
            steps {
                echo '⚡ Running performance tests...'
                sh '''
                    # Install Apache Bench if not available
                    which ab || (apt-get update && apt-get install -y apache2-utils)
                    
                    # Start fresh server instance
                    . venv/bin/activate
                    redis-server --daemonize yes --port 6379
                    python3 main.py &
                    export SERVER_PID=$!
                    sleep 10
                    
                    # Run performance tests
                    echo "🎯 Testing root endpoint..."
                    ab -n 100 -c 10 -T application/json http://localhost:8000/ > performance-results.txt
                    
                    echo "🎯 Testing health endpoint..."
                    ab -n 50 -c 5 http://localhost:8000/api/ai-host/health >> performance-results.txt
                    
                    # Cleanup
                    kill $SERVER_PID
                    redis-cli shutdown
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'performance-results.txt', allowEmptyArchive: true
                }
            }
        }
        
        stage('🔒 Security Scan') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                echo '🔒 Running security scans...'
                sh '''
                    . venv/bin/activate
                    pip install bandit safety
                    
                    # Run Bandit security linter
                    bandit -r . -f json -o bandit-report.json || true
                    
                    # Check for known security vulnerabilities
                    safety check --json --output safety-report.json || true
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: '*-report.json', allowEmptyArchive: true
                }
            }
        }
    }
    
    post {
        always {
            echo '🧹 Cleaning up...'
            sh '''
                # Stop any running services
                if [ -f server.pid ]; then
                    kill $(cat server.pid) || true
                    rm server.pid
                fi
                redis-cli shutdown || true
                
                # Cleanup Docker containers
                docker-compose -f docker-compose.test.yml down -v --remove-orphans || true
            '''
        }
        
        success {
            echo '🎉 Pipeline completed successfully!'
            
            // Send success notification
            script {
                if (env.BRANCH_NAME == 'main') {
                    // Send Slack notification for main branch
                    slackSend(
                        channel: '#voiceapp-ci',
                        color: 'good',
                        message: "✅ VoiceApp CI/CD Pipeline SUCCESS on ${env.BRANCH_NAME}\nBuild: ${env.BUILD_URL}"
                    )
                }
            }
        }
        
        failure {
            echo '❌ Pipeline failed!'
            
            // Send failure notification
            slackSend(
                channel: '#voiceapp-ci',
                color: 'danger',
                message: "❌ VoiceApp CI/CD Pipeline FAILED on ${env.BRANCH_NAME}\nBuild: ${env.BUILD_URL}\nPlease check the logs."
            )
        }
        
        unstable {
            echo '⚠️ Pipeline completed with warnings!'
            
            // Send warning notification
            slackSend(
                channel: '#voiceapp-ci',
                color: 'warning',
                message: "⚠️ VoiceApp CI/CD Pipeline UNSTABLE on ${env.BRANCH_NAME}\nSome tests failed but build continued.\nBuild: ${env.BUILD_URL}"
            )
        }
        
        cleanup {
            // Clean workspace on success
            cleanWs()
        }
    }
} 