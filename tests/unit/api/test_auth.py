"""
Authentication API Tests

Tests for /api/auth endpoints including login, token generation,
and password verification.

Coverage Target: 95% (authentication is security-critical)
"""

import os

import bcrypt
import pytest
from fastapi.testclient import TestClient
from jose import jwt


class TestAuthLogin:
    """Tests for POST /api/auth/login endpoint"""

    def test_login_success(self, test_client: TestClient, admin_credentials):
        """Test successful login with correct credentials"""
        email, password = admin_credentials

        response = test_client.post("/api/auth/login", auth=(email, password))

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "access_token" in data, "access_token missing from response"
        assert "token_type" in data, "token_type missing from response"
        assert data["token_type"] == "bearer"
        assert data["email"] == email
        assert data["role"] == "admin"

        # Verify token is valid JWT
        token = data["access_token"]
        secret_key = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert "sub" in decoded
        assert "exp" in decoded

    def test_login_invalid_password(self, test_client: TestClient):
        """Test login fails with incorrect password"""
        response = test_client.post("/api/auth/login", auth=("admin@acis-ai.com", "wrongpassword"))

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Incorrect email or password" in data["detail"]

    def test_login_invalid_email(self, test_client: TestClient):
        """Test login fails with incorrect email"""
        response = test_client.post("/api/auth/login", auth=("wrong@email.com", "admin123"))

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_missing_credentials(self, test_client: TestClient):
        """Test login fails when credentials are missing"""
        response = test_client.post("/api/auth/login")

        # Should return 401 (Unauthorized) when credentials are missing
        assert response.status_code == 401

    def test_login_empty_password(self, test_client: TestClient):
        """Test login fails with empty password"""
        response = test_client.post("/api/auth/login", auth=("admin@acis-ai.com", ""))

        assert response.status_code == 401

    def test_login_case_sensitive_email(self, test_client: TestClient):
        """Test that email is case-sensitive"""
        response = test_client.post(
            "/api/auth/login", auth=("ADMIN@ACIS-AI.COM", "admin123")  # Uppercase
        )

        # Should fail - email is case-sensitive
        assert response.status_code == 401

    def test_login_returns_correct_token_expiry(self, test_client: TestClient, admin_credentials):
        """Test that token has correct expiration time"""
        email, password = admin_credentials

        response = test_client.post("/api/auth/login", auth=(email, password))

        assert response.status_code == 200
        token = response.json()["access_token"]

        # Decode token and check expiration
        secret_key = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])

        import time

        current_time = time.time()
        exp_time = decoded["exp"]

        # Token should expire in approximately 30 minutes (1800 seconds)
        time_until_expiry = exp_time - current_time
        assert (
            1700 < time_until_expiry < 1900
        ), f"Token expiry is {time_until_expiry}s, expected ~1800s"


class TestAuthGetMe:
    """Tests for GET /api/auth/me endpoint"""

    def test_get_me_success(self, test_client: TestClient, admin_credentials):
        """Test getting current user info with valid credentials"""
        email, password = admin_credentials

        response = test_client.get("/api/auth/me", auth=(email, password))

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert data["role"] == "admin"
        assert data["is_active"] is True

    def test_get_me_invalid_credentials(self, test_client: TestClient):
        """Test /me endpoint fails with invalid credentials"""
        response = test_client.get("/api/auth/me", auth=("admin@acis-ai.com", "wrongpassword"))

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_get_me_no_auth(self, test_client: TestClient):
        """Test /me endpoint fails without authentication"""
        response = test_client.get("/api/auth/me")

        assert response.status_code == 401


class TestAuthHealthCheck:
    """Tests for GET /api/auth/health endpoint"""

    def test_health_check(self, test_client: TestClient):
        """Test health check endpoint (no auth required)"""
        response = test_client.get("/api/auth/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "auth"

    def test_health_check_no_auth_required(self, test_client: TestClient):
        """Verify health check works without authentication"""
        # Make request without auth headers
        response = test_client.get("/api/auth/health")

        assert response.status_code == 200, "Health check should not require authentication"


class TestPasswordVerification:
    """Tests for password verification logic"""

    def test_password_hashing_bcrypt(self):
        """Test that password verification uses bcrypt correctly"""
        from backend.api.routers.auth import verify_password

        # Create a test password hash
        password = "testpassword123"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Verify correct password
        assert verify_password(password, hashed) is True

        # Verify incorrect password
        assert verify_password("wrongpassword", hashed) is False

    def test_password_verification_empty_hash(self):
        """Test password verification with empty hash"""
        from backend.api.routers.auth import verify_password

        # Should return False, not raise exception
        result = verify_password("anypassword", "")
        assert result is False

    def test_password_verification_invalid_hash(self):
        """Test password verification with invalid hash format"""
        from backend.api.routers.auth import verify_password

        # Should return False, not raise exception
        result = verify_password("anypassword", "not-a-valid-hash")
        assert result is False


class TestJWTTokenGeneration:
    """Tests for JWT token creation"""

    def test_create_access_token(self):
        """Test JWT token is created correctly"""
        from datetime import timedelta

        from backend.api.routers.auth import create_access_token

        data = {"sub": "test@example.com"}
        token = create_access_token(data, expires_delta=timedelta(minutes=30))

        assert token is not None
        assert isinstance(token, str)

        # Decode and verify
        secret_key = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert decoded["sub"] == "test@example.com"
        assert "exp" in decoded

    def test_token_without_expiry_has_default(self):
        """Test that token without explicit expiry gets default expiration"""
        import time

        from backend.api.routers.auth import create_access_token

        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        secret_key = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])

        # Default should be 15 minutes
        current_time = time.time()
        exp_time = decoded["exp"]
        time_until_expiry = exp_time - current_time

        assert (
            800 < time_until_expiry < 1000
        ), f"Default expiry should be ~15min (900s), got {time_until_expiry}s"


class TestAuthSecurity:
    """Security-focused tests"""

    def test_password_not_returned_in_response(self, test_client: TestClient, admin_credentials):
        """Ensure password is never returned in any response"""
        email, password = admin_credentials

        # Login
        response = test_client.post("/api/auth/login", auth=(email, password))
        # Check the literal password isn't in response (ignore error messages that contain word "password")
        assert password not in response.text, "Actual password should not be in response"

        # Get me
        response = test_client.get("/api/auth/me", auth=(email, password))
        assert password not in response.text, "Actual password should not be in response"

    def test_sql_injection_attempt(self, test_client: TestClient):
        """Test that SQL injection attempts are handled safely"""
        malicious_inputs = [
            "admin@acis-ai.com'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin' --",
            "1' UNION SELECT * FROM users--",
        ]

        for malicious_input in malicious_inputs:
            response = test_client.post("/api/auth/login", auth=(malicious_input, "anypassword"))

            # Should return 401, not 500 (server error)
            assert (
                response.status_code == 401
            ), f"SQL injection attempt should be rejected: {malicious_input}"

    def test_timing_attack_resistance(self, test_client: TestClient):
        """Test that response times don't leak information about valid emails"""
        import time

        # Time for invalid email
        start = time.time()
        test_client.post("/api/auth/login", auth=("invalid@example.com", "password"))
        invalid_email_time = time.time() - start

        # Time for valid email with invalid password
        start = time.time()
        test_client.post("/api/auth/login", auth=("admin@acis-ai.com", "wrongpassword"))
        valid_email_time = time.time() - start

        # Times should be similar (within 100ms)
        # This prevents attackers from enumerating valid emails
        time_diff = abs(valid_email_time - invalid_email_time)
        assert (
            time_diff < 0.1
        ), f"Timing difference {time_diff}s is too large (potential timing attack)"

    @pytest.mark.parametrize(
        "special_char_password",
        [
            "pass@word!",
            "p@ssw0rd#123",
            "test$pass%word",
            "abc&def*ghi",
        ],
    )
    def test_special_characters_in_password(self, test_client: TestClient, special_char_password):
        """Test that special characters in passwords are handled correctly"""
        # This test verifies bcrypt handles special characters
        # We expect it to fail with 401 (these aren't the real password)
        response = test_client.post(
            "/api/auth/login", auth=("admin@acis-ai.com", special_char_password)
        )

        # Should return 401, not crash with 500
        assert response.status_code == 401


class TestAuthRateLimiting:
    """Tests for rate limiting (future implementation)"""

    @pytest.mark.skip(reason="Rate limiting not yet implemented")
    def test_rate_limiting_on_login(self, test_client: TestClient):
        """Test that excessive login attempts are rate limited"""
        # TODO: Implement rate limiting
        # Make 10 rapid login attempts
        for _ in range(10):
            test_client.post("/api/auth/login", auth=("admin@acis-ai.com", "wrongpassword"))

        # 11th attempt should be rate limited
        response = test_client.post("/api/auth/login", auth=("admin@acis-ai.com", "wrongpassword"))

        assert response.status_code == 429  # Too Many Requests


# ============================================================================
# Test Coverage Summary
# ============================================================================
"""
Coverage for backend/api/routers/auth.py:

✅ POST /api/auth/login
  - Success case
  - Invalid password
  - Invalid email
  - Missing credentials
  - Empty password
  - Case sensitivity
  - Token expiration

✅ GET /api/auth/me
  - Success case
  - Invalid credentials
  - No authentication

✅ GET /api/auth/health
  - Health check works
  - No auth required

✅ Password verification
  - Bcrypt verification
  - Empty hash
  - Invalid hash

✅ JWT token generation
  - Token creation
  - Default expiry
  - Custom expiry

✅ Security
  - Password not in responses
  - SQL injection attempts
  - Timing attack resistance
  - Special characters
  - Rate limiting (TODO)

Expected Coverage: 95%+ of auth.py
"""
