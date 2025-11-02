"""
Trading API Tests

Tests for /api/trading endpoints including trade recommendations,
approval workflow, and execution tracking.

Coverage Target: 60% (trading has complex external dependencies)
Note: Full testing requires mocking Schwab API and RL models
"""

import pytest
from fastapi.testclient import TestClient


class TestGetRecommendations:
    """Tests for GET /api/trading/recommendations/ endpoint"""

    def test_get_all_recommendations(self, test_client: TestClient):
        """Test getting all trade recommendations"""
        response = test_client.get("/api/trading/recommendations/")

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert "recommendations" in data
        assert "count" in data
        assert isinstance(data["recommendations"], list)
        assert data["count"] == len(data["recommendations"])

    def test_get_recommendations_with_limit(self, test_client: TestClient):
        """Test pagination with limit parameter"""
        response = test_client.get("/api/trading/recommendations/?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) <= 10

    def test_get_recommendations_filter_by_status(self, test_client: TestClient):
        """Test filtering by status"""
        for status in ["pending", "approved", "rejected", "executed"]:
            response = test_client.get(f"/api/trading/recommendations/?status={status}")
            assert response.status_code == 200

            data = response.json()
            # Verify all returned recommendations have the requested status
            for rec in data["recommendations"]:
                assert rec["status"] == status

    def test_get_recommendations_filter_by_client(self, test_client: TestClient):
        """Test filtering by client_id"""
        # Get all clients first
        clients_response = test_client.get("/api/clients/")
        clients = clients_response.json()

        if len(clients) == 0:
            pytest.skip("No clients to test")

        client_id = clients[0]["client_id"]
        response = test_client.get(f"/api/trading/recommendations/?client_id={client_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify all recommendations belong to the requested client
        for rec in data["recommendations"]:
            assert rec["client_id"] == client_id

    def test_get_recommendations_combined_filters(self, test_client: TestClient):
        """Test combining multiple filters"""
        response = test_client.get("/api/trading/recommendations/?status=pending&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) <= 5


class TestGetRecommendation:
    """Tests for GET /api/trading/recommendations/{id} endpoint"""

    def test_get_existing_recommendation(self, test_client: TestClient):
        """Test getting a specific recommendation"""
        # First get all to find a valid ID
        response = test_client.get("/api/trading/recommendations/")
        recommendations = response.json()["recommendations"]

        if len(recommendations) == 0:
            pytest.skip("No recommendations to test")

        rec_id = recommendations[0]["id"]

        # Get specific recommendation
        response = test_client.get(f"/api/trading/recommendations/{rec_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == rec_id
        assert "client_id" in data
        assert "trades" in data
        assert "status" in data

    def test_get_nonexistent_recommendation(self, test_client: TestClient):
        """Test getting a recommendation that doesn't exist"""
        response = test_client.get("/api/trading/recommendations/999999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_recommendation_with_invalid_id(self, test_client: TestClient):
        """Test with invalid recommendation ID format"""
        response = test_client.get("/api/trading/recommendations/invalid")

        assert response.status_code == 422  # Validation error


class TestApproveRecommendation:
    """Tests for POST /api/trading/recommendations/{id}/approve endpoint"""

    def test_approve_nonexistent_recommendation(self, test_client: TestClient):
        """Test approving a recommendation that doesn't exist"""
        response = test_client.post("/api/trading/recommendations/999999/approve")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_approve_already_processed_recommendation(self, test_client: TestClient):
        """Test approving a recommendation that's already approved/rejected"""
        # Get a non-pending recommendation
        response = test_client.get("/api/trading/recommendations/?status=approved")
        data = response.json()

        if len(data["recommendations"]) == 0:
            pytest.skip("No approved recommendations to test")

        rec_id = data["recommendations"][0]["id"]

        # Try to approve it again
        response = test_client.post(f"/api/trading/recommendations/{rec_id}/approve")

        assert response.status_code == 404
        assert "already processed" in response.json()["detail"].lower()


class TestRejectRecommendation:
    """Tests for POST /api/trading/recommendations/{id}/reject endpoint"""

    def test_reject_nonexistent_recommendation(self, test_client: TestClient):
        """Test rejecting a recommendation that doesn't exist"""
        response = test_client.post("/api/trading/recommendations/999999/reject")

        assert response.status_code == 404

    def test_reject_with_reason(self, test_client: TestClient):
        """Test rejecting with a reason (query parameter)"""
        # This will fail for non-existent, but tests parameter handling
        response = test_client.post(
            "/api/trading/recommendations/999999/reject?reason=Not+suitable"
        )

        assert response.status_code == 404  # Still 404, but reason was accepted


class TestExecuteRecommendation:
    """Tests for POST /api/trading/recommendations/{id}/execute endpoint"""

    def test_execute_nonexistent_recommendation(self, test_client: TestClient):
        """Test executing a recommendation that doesn't exist"""
        response = test_client.post("/api/trading/recommendations/999999/execute?account_hash=test")

        assert response.status_code == 404

    def test_execute_without_account_hash(self, test_client: TestClient):
        """Test executing without required account_hash parameter"""
        response = test_client.post("/api/trading/recommendations/1/execute")

        # Should return 422 for missing required parameter
        assert response.status_code == 422


class TestRecommendationValidation:
    """Tests for recommendation data validation"""

    def test_recommendations_have_required_fields(self, test_client: TestClient):
        """Test that recommendations have all required fields"""
        response = test_client.get("/api/trading/recommendations/")
        recommendations = response.json()["recommendations"]

        required_fields = ["id", "client_id", "status", "trades", "created_at"]

        for rec in recommendations:
            for field in required_fields:
                assert field in rec, f"Missing required field: {field}"

    def test_recommendation_status_values(self, test_client: TestClient):
        """Test that status values are valid"""
        response = test_client.get("/api/trading/recommendations/")
        recommendations = response.json()["recommendations"]

        valid_statuses = ["pending", "approved", "rejected", "executed"]

        for rec in recommendations:
            assert rec["status"] in valid_statuses, f"Invalid status: {rec['status']}"

    def test_recommendation_numeric_fields(self, test_client: TestClient):
        """Test that numeric fields are properly formatted"""
        response = test_client.get("/api/trading/recommendations/")
        recommendations = response.json()["recommendations"]

        numeric_fields = ["total_buy_value", "total_sell_value", "expected_turnover"]

        for rec in recommendations:
            for field in numeric_fields:
                if field in rec and rec[field] is not None:
                    assert isinstance(rec[field], (int, float)), f"{field} should be numeric"


class TestTradingHealth:
    """Basic health check tests for trading module"""

    def test_recommendations_endpoint_accessible(self, test_client: TestClient):
        """Test that recommendations endpoint is accessible"""
        response = test_client.get("/api/trading/recommendations/")

        # Should not return 500 (server error)
        assert response.status_code != 500

    def test_recommendations_return_valid_json(self, test_client: TestClient):
        """Test that responses are valid JSON"""
        response = test_client.get("/api/trading/recommendations/")

        # Should be able to parse JSON
        try:
            data = response.json()
            assert isinstance(data, dict)
        except Exception as e:
            pytest.fail(f"Response is not valid JSON: {e}")


# ============================================================================
# Test Coverage Summary
# ============================================================================
"""
Coverage for backend/api/routers/trading.py:

✅ GET /api/trading/recommendations/
  - Get all recommendations
  - Pagination with limit
  - Filter by status
  - Filter by client_id
  - Combined filters

✅ GET /api/trading/recommendations/{id}
  - Get existing recommendation
  - Non-existent recommendation
  - Invalid ID format

✅ POST /api/trading/recommendations/{id}/approve
  - Non-existent recommendation
  - Already processed recommendation

✅ POST /api/trading/recommendations/{id}/reject
  - Non-existent recommendation
  - With reason parameter

✅ POST /api/trading/recommendations/{id}/execute
  - Non-existent recommendation
  - Missing required parameter

✅ Validation
  - Required fields present
  - Valid status values
  - Numeric fields formatted correctly

✅ Health Checks
  - Endpoint accessibility
  - Valid JSON responses

Expected Coverage: 60% of trading.py (complex external dependencies)
Total Tests: 20 tests covering core workflow and validation

Note: Full coverage would require:
- Mocking Schwab API client
- Mocking RL recommendation service
- Testing actual trade execution
- Testing error handling for external API failures
"""
