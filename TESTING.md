# VoiceApp Testing Guide

This document describes the comprehensive testing strategy for VoiceApp, including unit tests, integration tests, and contract tests.

## 🧪 Testing Architecture

Our testing strategy follows a three-tier approach:

### 1. Unit Tests (`tests/unit/`)
**Goal:** Test individual modules and functions in isolation

**Coverage:**
- Queue operations and timeout matching algorithms
- UUID validation and parameter validation  
- Error handling and fallback behavior when services are offline
- Business logic without external dependencies

**Tools:** `pytest` + `pytest-asyncio` + `pytest-mock`

**Example:**
```bash
# Run unit tests only
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=. --cov-report=html
```

### 2. Integration Tests (`tests/integration/`)
**Goal:** Test complete workflows and service interactions

**Coverage:**
- Firebase Emulator + Auth Emulator: Register → Login → CRUD rooms
- AI services: TTS + topic extraction with real OpenAI calls
- WebSocket room connections + real-time messaging
- End-to-end user flows

**Tools:** Firebase Emulator Suite + Redis + running VoiceApp server

**Example:**
```bash
# Start emulators and server, then run integration tests
./run_tests.sh --integration
```

### 3. Contract Tests (`tests/contract/`)
**Goal:** Ensure API endpoints match OpenAPI documentation

**Coverage:**
- OpenAPI schema validation for all endpoints
- Response format consistency
- Error response contracts
- WebSocket message contracts

**Tools:** `schemathesis` + custom contract validators

**Example:**
```bash
# Run contract tests
./run_tests.sh --contract

# Run schemathesis automated testing
schemathesis run http://localhost:8000/openapi.json
```

## 🚀 Quick Start

### Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Run All Tests
```bash
# Run everything
./run_tests.sh --all

# Run specific test suite
./run_tests.sh --unit
./run_tests.sh --integration  
./run_tests.sh --contract
```

### Run Tests with Verbose Output
```bash
./run_tests.sh --all --verbose
```

## 📋 Test Categories

### Unit Test Examples

#### Queue Operations (`tests/unit/test_matching_queue.py`)
```python
def test_queue_enqueue_success(self, matching_repo, sample_user):
    """Test successful queue enqueue operation"""
    request_id = matching_repo.add_to_queue(sample_user.id, ["technology", "ai"])
    assert request_id is not None
```

#### Validation Logic (`tests/unit/test_validation.py`)
```python
def test_invalid_uuid_string(self):
    """Test validation of invalid UUID strings"""
    invalid_uuids = ["not-a-uuid", "12345", "", None]
    for invalid_uuid in invalid_uuids:
        with pytest.raises((ValueError, TypeError)):
            UUID(invalid_uuid)
```

#### Fallback Behavior (`tests/unit/test_fallback_behavior.py`)
```python
@pytest.mark.asyncio
async def test_tts_service_offline(self, openai_service):
    """Test TTS service fallback when OpenAI is offline"""
    openai_service.client.audio.speech.create = AsyncMock(
        side_effect=ConnectionError("OpenAI service unavailable")
    )
    with pytest.raises(ConnectionError):
        await openai_service.generate_tts("Hello world")
```

### Integration Test Structure

Integration tests require:
1. **Firebase Emulators** running on localhost:8080 (Firestore) and localhost:9099 (Auth)
2. **Redis** running on localhost:6379
3. **VoiceApp server** running on localhost:8000

Example test flow:
```python
async def test_complete_user_flow(self):
    """Test complete user registration and room creation flow"""
    # 1. Register user via Firebase Auth Emulator
    # 2. Login and get ID token
    # 3. Create room via API
    # 4. Connect to WebSocket
    # 5. Send/receive messages
    # 6. Cleanup
```

### Contract Test Examples

#### OpenAPI Schema Validation
```python
async def test_rooms_list_schema(self, base_url, openapi_schema):
    """Test rooms list endpoint matches OpenAPI schema"""
    response = await client.get(f"{base_url}/api/rooms/")
    assert response.status_code == 200
    
    # Validate against OpenAPI schema
    response_data = response.json()
    assert "rooms" in response_data
    assert isinstance(response_data["rooms"], list)
```

#### Automated API Testing with Schemathesis
```python
@schema.parametrize()
def test_api_endpoints_automatically(self, case):
    """Automatically test all endpoints based on OpenAPI schema"""
    response = case.call()
    case.validate_response(response)  # Automatic schema validation
```

## 🔧 Configuration

### Test Environment Variables
```bash
# Firebase Emulators
export FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
export FIRESTORE_EMULATOR_HOST=localhost:8080

# Test Services
export REDIS_URL=redis://localhost:6379
export OPENAI_API_KEY=test_key_for_testing
export LIVEKIT_API_KEY=test_livekit_key
export LIVEKIT_API_SECRET=test_livekit_secret
```

### Pytest Configuration (`pytest.ini`)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
addopts = 
    -v
    --tb=short
    --asyncio-mode=auto
    --cov=.
    --cov-report=term-missing
markers =
    unit: Unit tests
    integration: Integration tests  
    contract: Contract tests
```

## 🤖 CI/CD Integration

### GitHub Actions (`.github/workflows/test.yml`)

The CI pipeline runs:

1. **Unit Tests** - Fast, no external dependencies
2. **Integration Tests** - Firebase Emulators + Redis + VoiceApp server
3. **Contract Tests** - API schema validation + schemathesis
4. **Code Quality** - Black, isort, flake8, mypy
5. **Security Scan** - Safety, bandit

### Local CI Simulation
```bash
# Simulate the CI pipeline locally
./run_tests.sh --all --verbose

# Check code quality
black --check .
isort --check-only .
flake8 .
mypy . --ignore-missing-imports
```

## 📊 Test Markers

Use pytest markers to run specific test categories:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests  
pytest -m integration

# Run only contract tests
pytest -m contract

# Run slow tests
pytest -m slow

# Exclude slow tests
pytest -m "not slow"
```

## 🐛 Debugging Tests

### Verbose Output
```bash
pytest -vv --tb=long tests/unit/test_matching_queue.py
```

### Run Single Test
```bash
pytest tests/unit/test_validation.py::TestUUIDValidation::test_valid_uuid_string -v
```

### Debug with Print Statements
```python
def test_debug_example():
    result = some_function()
    print(f"Debug: result = {result}")  # Will show in pytest output with -s
    assert result == expected
```

```bash
pytest tests/unit/test_example.py -s  # -s shows print statements
```

### Debug with PDB
```python
def test_debug_with_pdb():
    result = some_function()
    import pdb; pdb.set_trace()  # Debugger breakpoint
    assert result == expected
```

## 🎯 Test Coverage

### Generate Coverage Report
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
open htmlcov/index.html  # View detailed coverage report
```

### Coverage Goals
- **Unit Tests:** 90%+ coverage for core business logic
- **Integration Tests:** Cover all critical user flows
- **Contract Tests:** 100% API endpoint coverage

## 🔄 Continuous Testing

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

### Test-Driven Development (TDD)
1. Write failing test
2. Implement minimal code to pass test
3. Refactor while keeping tests green
4. Repeat

### Example TDD Cycle
```python
# 1. Write failing test
def test_new_feature():
    result = new_feature("input")
    assert result == "expected_output"

# 2. Implement feature
def new_feature(input):
    return "expected_output"  # Minimal implementation

# 3. Refactor
def new_feature(input):
    # Proper implementation
    return process_input(input)
```

## 🚨 Common Issues

### Firebase Emulator Not Starting
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Start emulators
firebase emulators:start --only firestore,auth --project demo-test
```

### Redis Connection Failed
```bash
# Start Redis locally
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### OpenAI API Rate Limits
```python
# Mock OpenAI in tests
@patch('infrastructure.ai.openai_service.OpenAI')
def test_with_mocked_openai(self, mock_openai):
    # Test without making real API calls
```

### WebSocket Connection Issues
```bash
# Check if server is running
curl http://localhost:8000/

# Check WebSocket endpoint
wscat -c ws://localhost:8000/api/ai-host/live-subtitle
```

## 📈 Performance Testing

### Load Testing with Locust
```python
from locust import HttpUser, task, between

class VoiceAppUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def health_check(self):
        self.client.get("/")
    
    @task
    def get_rooms(self):
        self.client.get("/api/rooms/", headers={"Authorization": "Bearer test_token"})
```

### Memory Usage Testing
```python
import tracemalloc

def test_memory_usage():
    tracemalloc.start()
    
    # Run memory-intensive operation
    result = heavy_operation()
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    assert peak < 100 * 1024 * 1024  # Less than 100MB
```

## 🎉 Best Practices

1. **Test Isolation:** Each test should be independent
2. **Descriptive Names:** Test names should describe what they test
3. **Arrange-Act-Assert:** Structure tests clearly
4. **Mock External Services:** Don't depend on external APIs in unit tests
5. **Use Fixtures:** Share common setup code
6. **Test Edge Cases:** Test boundary conditions and error cases
7. **Keep Tests Fast:** Unit tests should run in milliseconds
8. **Maintain Tests:** Update tests when code changes

---

## 📞 Support

For questions about testing:
1. Check this documentation first
2. Look at existing test examples
3. Ask the team for help
4. Update this documentation when you learn something new!

Happy testing! 🧪✨ 