# Tests Directory

This directory contains all tests for the Wallet Service application.

## Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `test_auth_google.py` - Tests for `/auth/google` endpoint

## Running Tests

### Run all tests:
```bash
uv run pytest tests/ -v
```

### Run specific test file:
```bash
uv run pytest tests/test_auth_google.py -v
```

### Run with coverage:
```bash
uv run pytest tests/ -v --cov=app.api.auth --cov-report=term-missing
```

### Run specific test:
```bash
uv run pytest tests/test_auth_google.py::TestGoogleLoginEndpoint::test_google_login_redirects_to_google -v
```

## Test Coverage

The test suite covers:
- ✅ Happy path scenarios (successful OAuth redirect)
- ✅ Error handling (missing credentials, OAuth failures)
- ✅ Configuration validation (redirect URI, scopes)
- ✅ HTTP method validation
- ✅ Response header validation
