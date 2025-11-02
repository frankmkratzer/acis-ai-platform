"""
Performance testing with Locust for ACIS AI Platform
Run with: locust -f tests/performance/locustfile.py --host=http://localhost:8000
"""

import json
import random
from datetime import datetime, timedelta

from locust import HttpUser, between, events, task


class ACISAPIUser(HttpUser):
    """Simulates a user interacting with the ACIS AI Platform API"""

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    def on_start(self):
        """Called when a simulated user starts"""
        # Login or get auth token if needed
        self.client.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    @task(5)
    def get_clients(self):
        """Get list of clients (most common operation)"""
        self.client.get("/api/clients")

    @task(3)
    def get_specific_client(self):
        """Get specific client details"""
        client_id = random.randint(1, 10)
        self.client.get(f"/api/clients/{client_id}")

    @task(2)
    def get_portfolio(self):
        """Get portfolio for a client"""
        client_id = random.randint(1, 10)
        self.client.get(f"/api/clients/{client_id}/portfolio")

    @task(4)
    def get_ml_predictions(self):
        """Get ML model predictions"""
        tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
        ticker = random.choice(tickers)
        self.client.get(f"/api/ml/predict?ticker={ticker}")

    @task(2)
    def get_portfolio_optimization(self):
        """Get portfolio optimization"""
        client_id = random.randint(1, 10)
        self.client.get(f"/api/portfolio/optimize/{client_id}")

    @task(1)
    def create_trade(self):
        """Execute a trade"""
        trade_data = {
            "client_id": random.randint(1, 10),
            "ticker": random.choice(["AAPL", "GOOGL", "MSFT"]),
            "quantity": random.randint(1, 100),
            "side": random.choice(["buy", "sell"]),
            "order_type": "market",
        }
        self.client.post("/api/trading/execute", json=trade_data)

    @task(3)
    def get_trading_history(self):
        """Get trading history"""
        client_id = random.randint(1, 10)
        self.client.get(f"/api/trading/history/{client_id}")

    @task(2)
    def get_model_performance(self):
        """Get ML model performance metrics"""
        self.client.get("/api/ml/performance")

    @task(1)
    def health_check(self):
        """Health check endpoint"""
        self.client.get("/health")


class ACISStressTestUser(HttpUser):
    """Stress test scenario with heavy operations"""

    wait_time = between(0.5, 2)  # Faster requests for stress testing

    @task(10)
    def rapid_ml_predictions(self):
        """Rapid ML predictions to stress the model"""
        tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
        ticker = random.choice(tickers)
        self.client.get(f"/api/ml/predict?ticker={ticker}")

    @task(5)
    def concurrent_optimizations(self):
        """Multiple portfolio optimizations"""
        client_id = random.randint(1, 10)
        self.client.get(f"/api/portfolio/optimize/{client_id}")

    @task(3)
    def bulk_trades(self):
        """Simulate bulk trading"""
        for _ in range(5):
            trade_data = {
                "client_id": random.randint(1, 10),
                "ticker": random.choice(["AAPL", "GOOGL", "MSFT", "AMZN"]),
                "quantity": random.randint(10, 500),
                "side": random.choice(["buy", "sell"]),
                "order_type": "market",
            }
            self.client.post("/api/trading/execute", json=trade_data)


class ACISBackgroundJobUser(HttpUser):
    """Simulates background jobs and long-running operations"""

    wait_time = between(5, 15)  # Longer wait between operations

    @task(1)
    def trigger_model_training(self):
        """Trigger ML model training"""
        training_config = {
            "model_type": random.choice(["growth", "value", "dividend", "momentum"]),
            "lookback_days": random.choice([30, 60, 90, 180]),
        }
        self.client.post("/api/ml/train", json=training_config)

    @task(2)
    def bulk_data_fetch(self):
        """Fetch large amounts of historical data"""
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        ticker = random.choice(["AAPL", "GOOGL", "MSFT"])
        self.client.get(f"/api/data/historical?ticker={ticker}&start={start_date}&end={end_date}")

    @task(1)
    def portfolio_rebalance(self):
        """Trigger portfolio rebalancing"""
        client_id = random.randint(1, 10)
        self.client.post(f"/api/portfolio/rebalance/{client_id}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    print("🚀 Performance test starting...")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
    print("\n✅ Performance test completed")
    stats = environment.stats

    print("\n📊 Summary Statistics:")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Failed requests: {stats.total.num_failures}")
    print(f"Failure rate: {stats.total.fail_ratio * 100:.2f}%")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Requests per second: {stats.total.total_rps:.2f}")


# Custom failure criteria
@events.quitting.add_listener
def check_failure_criteria(environment, **kwargs):
    """Check if test should fail based on performance criteria"""
    stats = environment.stats.total

    # Failure criteria
    max_failure_rate = 0.05  # 5%
    max_avg_response_time = 2000  # 2 seconds
    max_p95_response_time = 5000  # 5 seconds

    failures = []

    if stats.fail_ratio > max_failure_rate:
        failures.append(
            f"Failure rate {stats.fail_ratio * 100:.2f}% exceeds {max_failure_rate * 100}%"
        )

    if stats.avg_response_time > max_avg_response_time:
        failures.append(
            f"Average response time {stats.avg_response_time:.2f}ms exceeds {max_avg_response_time}ms"
        )

    p95 = stats.get_response_time_percentile(0.95)
    if p95 > max_p95_response_time:
        failures.append(f"95th percentile {p95:.2f}ms exceeds {max_p95_response_time}ms")

    if failures:
        print("\n❌ Performance test FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        environment.process_exit_code = 1
    else:
        print("\n✅ Performance test PASSED - All criteria met!")
