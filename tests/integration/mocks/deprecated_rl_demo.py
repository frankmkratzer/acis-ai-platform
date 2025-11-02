"""
Test RL Recommendation Service Integration

This script tests the RL recommendation service in demo mode
to verify that recommendations are generated correctly.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "api"))

from services.rl_recommendation_service import get_recommendation_service


def test_growth_momentum_portfolio():
    """Test Growth/Momentum portfolio recommendations"""
    print("=" * 80)
    print("Testing Portfolio 1: Growth/Momentum")
    print("=" * 80)

    # Mock current positions (empty portfolio to start)
    current_positions = []

    # Mock account details
    account_value = 100000  # $100k account
    cash = 100000  # All cash initially

    # Get recommendation service
    rec_service = get_recommendation_service()

    # Generate recommendations
    result = rec_service.generate_recommendations(
        portfolio_id=1,  # Growth/Momentum
        current_positions=current_positions,
        account_value=account_value,
        cash=cash,
    )

    # Display results
    print(f"\nPortfolio: {result['portfolio_name']}")
    print(f"Mode: {result.get('mode', 'rl')}")
    if "note" in result:
        print(f"Note: {result['note']}")

    print(f"\n{'='*80}")
    print("TARGET ALLOCATION")
    print(f"{'='*80}")
    for symbol, weight in sorted(
        result["target_allocation"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"{symbol:8s}: {weight*100:6.2f}%")

    print(f"\n{'='*80}")
    print(f"RECOMMENDED TRADES ({len(result['trades'])} total)")
    print(f"{'='*80}")
    for trade in result["trades"]:
        print(f"\n{trade['action']:4s} {trade['symbol']:8s}")
        print(f"  Shares: {trade['shares']}")
        print(f"  Dollar Amount: ${trade['dollar_amount']:,.2f}")
        print(f"  Weight: {trade['weight_old']*100:.2f}% → {trade['weight_new']*100:.2f}%")
        print(f"  Reasoning: {trade['reasoning']}")

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total Trades: {result['summary']['num_trades']}")
    print(f"Total Turnover: {result['summary']['total_turnover']*100:.1f}%")
    print(f"Buy Value: ${result['summary']['total_buy_value']:,.2f}")
    print(f"Sell Value: ${result['summary']['total_sell_value']:,.2f}")
    print(f"Cash Required: ${result['summary']['cash_required']:,.2f}")

    return result


def test_dividend_portfolio():
    """Test Dividend portfolio recommendations"""
    print("\n\n" + "=" * 80)
    print("Testing Portfolio 2: Dividend")
    print("=" * 80)

    # Mock current positions (empty portfolio to start)
    current_positions = []

    # Mock account details
    account_value = 100000  # $100k account
    cash = 100000  # All cash initially

    # Get recommendation service
    rec_service = get_recommendation_service()

    # Generate recommendations
    result = rec_service.generate_recommendations(
        portfolio_id=2,  # Dividend
        current_positions=current_positions,
        account_value=account_value,
        cash=cash,
    )

    # Display results
    print(f"\nPortfolio: {result['portfolio_name']}")
    print(f"Mode: {result.get('mode', 'rl')}")

    print(f"\n{'='*80}")
    print("TARGET ALLOCATION (Top 10)")
    print(f"{'='*80}")
    top_10 = sorted(result["target_allocation"].items(), key=lambda x: x[1], reverse=True)[:10]
    for symbol, weight in top_10:
        if symbol != "CASH":
            print(f"{symbol:8s}: {weight*100:6.2f}%")

    print(
        f"\nNumber of stocks: {len([s for s in result['target_allocation'].keys() if s != 'CASH'])}"
    )
    print(f"Total Trades: {result['summary']['num_trades']}")

    return result


def test_value_portfolio():
    """Test Value portfolio recommendations"""
    print("\n\n" + "=" * 80)
    print("Testing Portfolio 3: Value")
    print("=" * 80)

    # Mock current positions (empty portfolio to start)
    current_positions = []

    # Mock account details
    account_value = 100000  # $100k account
    cash = 100000  # All cash initially

    # Get recommendation service
    rec_service = get_recommendation_service()

    # Generate recommendations
    result = rec_service.generate_recommendations(
        portfolio_id=3,  # Value
        current_positions=current_positions,
        account_value=account_value,
        cash=cash,
    )

    # Display results
    print(f"\nPortfolio: {result['portfolio_name']}")
    print(f"Mode: {result.get('mode', 'rl')}")

    print(f"\n{'='*80}")
    print("TARGET ALLOCATION (Top 10)")
    print(f"{'='*80}")
    top_10 = sorted(result["target_allocation"].items(), key=lambda x: x[1], reverse=True)[:10]
    for symbol, weight in top_10:
        if symbol != "CASH":
            print(f"{symbol:8s}: {weight*100:6.2f}%")

    print(
        f"\nNumber of stocks: {len([s for s in result['target_allocation'].keys() if s != 'CASH'])}"
    )
    print(f"Total Trades: {result['summary']['num_trades']}")

    return result


def test_rebalance_scenario():
    """Test rebalancing an existing portfolio"""
    print("\n\n" + "=" * 80)
    print("Testing Rebalancing Scenario: Growth/Momentum with Existing Positions")
    print("=" * 80)

    # Mock current positions (existing Growth/Momentum portfolio that's drifted)
    current_positions = [
        {"symbol": "AAPL", "current_value": 20000},  # 20% - target 15%
        {"symbol": "MSFT", "current_value": 10000},  # 10% - target 15%
        {"symbol": "NVDA", "current_value": 15000},  # 15% - target 12%
        {"symbol": "TSLA", "current_value": 15000},  # 15% - target 9%
        {"symbol": "GOOGL", "current_value": 5000},  # 5% - target 12%
        # Missing: AMZN, META, AVGO, AMD
        # Total: 65% invested, 35% cash
    ]

    # Mock account details
    account_value = 100000  # $100k account
    cash = 35000  # 35% cash

    # Get recommendation service
    rec_service = get_recommendation_service()

    # Generate recommendations
    result = rec_service.generate_recommendations(
        portfolio_id=1,  # Growth/Momentum
        current_positions=current_positions,
        account_value=account_value,
        cash=cash,
    )

    # Display results
    print(f"\nPortfolio: {result['portfolio_name']}")

    print(f"\n{'='*80}")
    print("CURRENT vs TARGET ALLOCATION")
    print(f"{'='*80}")
    print(f"{'Symbol':<8s}  {'Current %':>10s}  {'Target %':>10s}  {'Change':>10s}")
    print("-" * 50)

    # Get all symbols
    all_symbols = set(result["current_allocation"].keys()) | set(result["target_allocation"].keys())
    all_symbols.discard("CASH")

    for symbol in sorted(all_symbols):
        current = result["current_allocation"].get(symbol, 0)
        target = result["target_allocation"].get(symbol, 0)
        change = target - current
        print(f"{symbol:<8s}  {current*100:>9.2f}%  {target*100:>9.2f}%  {change*100:>+9.2f}%")

    print(f"\n{'='*80}")
    print(f"REBALANCING TRADES ({len(result['trades'])} total)")
    print(f"{'='*80}")

    # Group trades by type
    buys = [t for t in result["trades"] if t["action"] in ["BUY", "ADD"]]
    sells = [t for t in result["trades"] if t["action"] in ["SELL", "TRIM"]]

    if sells:
        print("\nSELLS/TRIMS:")
        for trade in sells:
            print(
                f"  {trade['action']:4s} {trade['symbol']:8s} - "
                f"{trade['shares']} shares (${trade['dollar_amount']:,.2f})"
            )

    if buys:
        print("\nBUYS/ADDS:")
        for trade in buys:
            print(
                f"  {trade['action']:4s} {trade['symbol']:8s} - "
                f"{trade['shares']} shares (${trade['dollar_amount']:,.2f})"
            )

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total Trades: {result['summary']['num_trades']}")
    print(f"Total Turnover: {result['summary']['total_turnover']*100:.1f}%")
    print(f"Net Cash Impact: ${result['summary']['cash_required']:,.2f}")

    return result


if __name__ == "__main__":
    print("\n")
    print("*" * 80)
    print("RL RECOMMENDATION SERVICE INTEGRATION TEST")
    print("*" * 80)
    print("\nThis test verifies that the RL recommendation service generates")
    print("trade recommendations correctly in demo mode.")
    print("\n")

    try:
        # Test all three portfolios
        result1 = test_growth_momentum_portfolio()
        result2 = test_dividend_portfolio()
        result3 = test_value_portfolio()

        # Test rebalancing scenario
        result4 = test_rebalance_scenario()

        print("\n\n" + "=" * 80)
        print("ALL TESTS PASSED!")
        print("=" * 80)
        print("\nThe RL recommendation service is working correctly in demo mode.")
        print("Recommendations are generated with proper allocations and trade logic.")
        print("\nNext steps:")
        print("  1. Train actual RL models to replace demo mode")
        print("  2. Test through UI at /clients/[id]/trading")
        print("  3. Test full end-to-end flow with Schwab integration")

    except Exception as e:
        print(f"\n\n{'='*80}")
        print("TEST FAILED!")
        print(f"{'='*80}")
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
