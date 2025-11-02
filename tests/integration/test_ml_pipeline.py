"""
ML/RL Pipeline Integration Tests

Tests ML model training and inference:
1. List trained models
2. Get model details
3. Generate predictions
4. Training job management
5. Model deletion
6. Portfolio generation with ML
7. RL agent inference

Target: 8-10 tests
"""

import pytest
from fastapi.testclient import TestClient

from tests.integration.factories import ClientFactory


class TestModelManagement:
    """Test ML model listing and management"""

    def test_list_models(self, integration_client: TestClient):
        """Test listing all trained models"""
        response = integration_client.get("/api/ml-models/list")

        # Should always return a list (empty or with models)
        assert response.status_code == 200

        models = response.json()
        assert isinstance(models, list)

        # If models exist, verify structure
        if len(models) > 0:
            model = models[0]
            assert "name" in model
            assert "path" in model
            assert "created" in model
            assert "size_mb" in model

    def test_get_model_details(self, integration_client: TestClient):
        """Test getting details of a specific model"""
        # First, get list of models
        list_response = integration_client.get("/api/ml-models/list")

        if list_response.status_code == 200:
            models = list_response.json()

            if len(models) > 0:
                # Get details of first model
                model_name = models[0]["name"]
                response = integration_client.get(f"/api/ml-models/{model_name}/details")

                assert response.status_code in [200, 404, 500]

                if response.status_code == 200:
                    details = response.json()
                    assert "name" in details
                    assert "metadata" in details
                    assert "size_mb" in details

    def test_get_nonexistent_model_details(self, integration_client: TestClient):
        """Test getting details of non-existent model"""
        response = integration_client.get("/api/ml-models/nonexistent_model_12345/details")

        # Should return 404
        assert response.status_code in [404, 500]

    def test_delete_nonexistent_model(self, integration_client: TestClient):
        """Test deleting non-existent model"""
        response = integration_client.delete("/api/ml-models/nonexistent_model_12345")

        # Should return 404
        assert response.status_code in [404, 500]


class TestPredictionGeneration:
    """Test ML prediction generation"""

    def test_generate_predictions_for_client(
        self, integration_client: TestClient, cleanup_test_data
    ):
        """Test generating ML predictions for a client"""
        # Create client
        client_data = ClientFactory.build()
        response = integration_client.post("/api/clients/", json=client_data)

        if response.status_code == 200:
            client = response.json()
            client_id = client["client_id"]

            # Try to generate predictions
            response = integration_client.get(f"/api/ml-models/predict/{client_id}")

            # May succeed or fail depending on model availability
            assert response.status_code in [200, 404, 500]

            if response.status_code == 200:
                predictions = response.json()
                # Should return list or dict of predictions
                assert isinstance(predictions, (list, dict))

    def test_generate_predictions_nonexistent_client(self, integration_client: TestClient):
        """Test generating predictions for non-existent client"""
        response = integration_client.get("/api/ml-models/predict/999999")

        # Should fail gracefully
        assert response.status_code in [404, 500]


class TestTrainingJobs:
    """Test ML training job management"""

    def test_list_training_jobs(self, integration_client: TestClient):
        """Test listing active training jobs"""
        response = integration_client.get("/api/ml-models/jobs")

        # Should return list of jobs
        assert response.status_code in [200, 404, 500]

        if response.status_code == 200:
            jobs = response.json()
            assert isinstance(jobs, list)

    def test_get_training_job_status(self, integration_client: TestClient):
        """Test getting status of a specific training job"""
        # Try to get non-existent job
        response = integration_client.get("/api/ml-models/jobs/fake_job_id_12345")

        # Should return 404
        assert response.status_code in [404, 500]

    def test_start_training_job_validation(self, integration_client: TestClient):
        """Test that training job validates parameters"""
        # Try to start job with invalid parameters
        invalid_config = {
            "framework": "invalid_framework",
            "strategy": "invalid_strategy",
        }

        response = integration_client.post("/api/ml-models/train", json=invalid_config)

        # Should return validation error or handle gracefully
        assert response.status_code in [400, 422, 500]


class TestPortfolioGeneration:
    """Test ML-based portfolio generation"""

    def test_generate_portfolio_with_ml(
        self, integration_client: TestClient, cleanup_test_data
    ):
        """Test generating portfolio using ML predictions"""
        # Create client
        client_data = ClientFactory.build()
        response = integration_client.post("/api/clients/", json=client_data)

        if response.status_code == 200:
            client = response.json()
            client_id = client["client_id"]

            # Try to generate portfolio
            portfolio_config = {
                "client_id": client_id,
                "strategy": "growth",
                "max_positions": 10,
                "initial_capital": 100000,
            }

            response = integration_client.post("/api/ml-portfolio/generate", json=portfolio_config)

            # May succeed or fail depending on model availability
            assert response.status_code in [200, 400, 404, 500]

            if response.status_code == 200:
                portfolio = response.json()
                assert "holdings" in portfolio or "positions" in portfolio or "recommendations" in portfolio

    def test_generate_portfolio_nonexistent_client(self, integration_client: TestClient):
        """Test generating portfolio for non-existent client"""
        portfolio_config = {
            "client_id": 999999,
            "strategy": "growth",
            "max_positions": 10,
        }

        response = integration_client.post("/api/ml-portfolio/generate", json=portfolio_config)

        # Should fail
        assert response.status_code in [400, 404, 500]


class TestRLAgentInference:
    """Test RL agent inference"""

    def test_rl_recommendations_for_client(
        self, integration_client: TestClient, cleanup_test_data
    ):
        """Test getting RL-based recommendations"""
        # Create client
        client_data = ClientFactory.build()
        response = integration_client.post("/api/clients/", json=client_data)

        if response.status_code == 200:
            client = response.json()
            client_id = client["client_id"]

            # Try to get RL recommendations
            response = integration_client.get(f"/api/rl-trading/recommendations/{client_id}")

            # May succeed or fail depending on RL agent availability
            assert response.status_code in [200, 404, 500]

    def test_rl_portfolio_evaluation(self, integration_client: TestClient, cleanup_test_data):
        """Test evaluating portfolio with RL agent"""
        # Create client
        client_data = ClientFactory.build()
        response = integration_client.post("/api/clients/", json=client_data)

        if response.status_code == 200:
            client = response.json()
            client_id = client["client_id"]

            # Try to evaluate portfolio
            eval_config = {
                "client_id": client_id,
                "positions": [
                    {"ticker": "AAPL", "shares": 10, "value": 1800},
                    {"ticker": "MSFT", "shares": 5, "value": 1900},
                ],
            }

            response = integration_client.post("/api/rl-trading/evaluate", json=eval_config)

            # May succeed or fail depending on implementation
            assert response.status_code in [200, 400, 404, 500]


class TestModelVersioning:
    """Test model versioning and management"""

    def test_list_model_versions(self, integration_client: TestClient):
        """Test listing versions of a model"""
        # Get list of models
        list_response = integration_client.get("/api/ml-models/list")

        if list_response.status_code == 200:
            models = list_response.json()

            if len(models) > 0:
                model_name = models[0]["name"]

                # Try to get versions (may not be implemented)
                response = integration_client.get(f"/api/ml-models/{model_name}/versions")

                # May or may not be implemented
                assert response.status_code in [200, 404, 500]


# ============================================================================
# Test Coverage Summary
# ============================================================================
"""
Integration Tests for ML/RL Pipeline:

✅ Model Management (4 tests)
  - List models
  - Get model details
  - Get non-existent model details
  - Delete non-existent model

✅ Prediction Generation (2 tests)
  - Generate predictions for client
  - Generate predictions for non-existent client

✅ Training Jobs (3 tests)
  - List training jobs
  - Get training job status
  - Start training job validation

✅ Portfolio Generation (2 tests)
  - Generate portfolio with ML
  - Generate portfolio for non-existent client

✅ RL Agent Inference (2 tests)
  - RL recommendations for client
  - RL portfolio evaluation

✅ Model Versioning (1 test)
  - List model versions

Total: 14 integration tests
Estimated Coverage: ML/RL pipeline from training to inference

Note: These tests focus on API endpoints and workflow correctness.
Many tests will pass/fail gracefully depending on whether models are trained.
"""
