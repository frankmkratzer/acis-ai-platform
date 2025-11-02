"""
Portfolio Analyzer

Analyzes client portfolios and generates intelligent rebalancing recommendations.
Identifies:
- Position drift from target allocation
- Underperforming positions
- Swap candidates with better risk/reward
- Tax-loss harvesting opportunities
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor


@dataclass
class Position:
    """Represents a portfolio position"""

    ticker: str
    quantity: float
    current_price: float
    market_value: float
    current_weight: float
    target_weight: float
    cost_basis: float
    unrealized_gain_loss: float
    days_held: int
    ml_score: Optional[float] = None
    sector: Optional[str] = None


@dataclass
class SwapRecommendation:
    """Recommendation to swap one position for another"""

    sell_ticker: str
    buy_ticker: str
    reason: str
    expected_improvement: float
    sell_ml_score: float
    buy_ml_score: float
    tax_impact: float
    transaction_cost: float
    net_benefit: float
    priority: str  # 'high', 'medium', 'low'


class PortfolioAnalyzer:
    """
    Analyzes portfolios and generates rebalancing recommendations
    """

    def __init__(self, db_conn_string: str):
        self.db_conn_string = db_conn_string

    def analyze_portfolio(
        self, client_id: int, account_id: str, target_strategy: str = "growth_largecap"
    ) -> Dict:
        """
        Comprehensive portfolio analysis

        Returns:
            - Current positions with drift analysis
            - Underperforming positions
            - Swap recommendations
            - Tax-loss harvest opportunities
            - Overall health score
        """
        conn = psycopg2.connect(self.db_conn_string)

        try:
            # Get current positions
            positions = self._get_current_positions(conn, account_id)

            # Get client settings
            settings = self._get_client_settings(conn, client_id)

            # Get target portfolio weights
            target_weights = self._get_target_weights(conn, target_strategy)

            # Calculate drift
            drift_analysis = self._analyze_drift(
                positions, target_weights, settings["drift_threshold"]
            )

            # Identify underperformers
            underperformers = self._identify_underperformers(conn, positions)

            # Generate swap recommendations
            swap_recommendations = self._generate_swap_recommendations(
                conn, underperformers, target_strategy, settings
            )

            # Find tax-loss harvest opportunities
            tax_harvest_opps = self._find_tax_harvest_opportunities(positions, settings)

            # Calculate portfolio health score
            health_score = self._calculate_health_score(positions, drift_analysis, underperformers)

            return {
                "client_id": client_id,
                "account_id": account_id,
                "analysis_date": datetime.now().isoformat(),
                "positions": [self._position_to_dict(p) for p in positions],
                "drift_analysis": drift_analysis,
                "underperformers": underperformers,
                "swap_recommendations": [self._swap_to_dict(s) for s in swap_recommendations],
                "tax_harvest_opportunities": tax_harvest_opps,
                "health_score": health_score,
                "needs_rebalance": drift_analysis["max_drift"] > settings["drift_threshold"],
                "total_portfolio_value": sum(p.market_value for p in positions),
            }

        finally:
            conn.close()

    def _get_current_positions(self, conn, account_id: str) -> List[Position]:
        """Fetch current portfolio positions"""
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                p.ticker,
                p.quantity,
                p.avg_price as cost_basis,
                p.market_value,
                p.unrealized_pnl,
                p.updated_at,
                q.close as current_price,
                t.sic_description as sector,
                t.market_cap
            FROM paper_positions p
            LEFT JOIN ticker_overview t ON p.ticker = t.ticker
            LEFT JOIN daily_bars q ON p.ticker = q.ticker
                AND q.date = (SELECT MAX(date) FROM daily_bars WHERE ticker = p.ticker)
            WHERE p.account_id = %s AND p.quantity > 0
        """

        cursor.execute(query, (account_id,))
        rows = cursor.fetchall()

        total_value = sum(r["market_value"] for r in rows)

        positions = []
        for row in rows:
            days_held = (datetime.now() - row["updated_at"]).days if row["updated_at"] else 0

            # Convert all numeric fields to float to avoid Decimal type issues
            quantity = float(row["quantity"]) if row["quantity"] is not None else 0
            current_price = float(row["current_price"]) if row["current_price"] else 0
            market_value = float(row["market_value"]) if row["market_value"] is not None else 0
            cost_basis = float(row["cost_basis"]) if row["cost_basis"] is not None else 0
            unrealized_pnl = (
                float(row["unrealized_pnl"]) if row["unrealized_pnl"] is not None else 0
            )

            pos = Position(
                ticker=row["ticker"],
                quantity=quantity,
                current_price=current_price,
                market_value=market_value,
                current_weight=market_value / float(total_value) if total_value > 0 else 0,
                target_weight=0.0,  # Will be filled in later
                cost_basis=cost_basis,
                unrealized_gain_loss=unrealized_pnl,
                days_held=days_held,
                sector=row["sector"],
            )
            positions.append(pos)

        return positions

    def _get_client_settings(self, conn, client_id: int) -> Dict:
        """Get client autonomous trading settings"""
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                drift_threshold,
                max_position_size,
                min_cash_balance,
                tax_optimization_enabled,
                risk_tolerance
            FROM clients
            WHERE client_id = %s
        """

        cursor.execute(query, (client_id,))
        row = cursor.fetchone()

        return {
            "drift_threshold": float(row["drift_threshold"]) if row else 0.05,
            "max_position_size": float(row["max_position_size"]) if row else 0.10,
            "min_cash_balance": float(row["min_cash_balance"]) if row else 1000.0,
            "tax_optimization_enabled": row["tax_optimization_enabled"] if row else True,
            "risk_tolerance": row["risk_tolerance"] if row else "moderate",
        }

    def _get_target_weights(self, conn, strategy: str) -> Dict[str, float]:
        """
        Get target portfolio weights for strategy

        Attempts to fetch target weights from multiple sources in order of priority:
        1. Active RL portfolio allocation (if available)
        2. ML model predictions (if available)
        3. Equal weight distribution as fallback
        """
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Try to get target weights from active RL portfolio
        rl_weights = self._get_rl_target_weights(cursor, strategy)
        if rl_weights:
            return rl_weights

        # Try to get target weights from ML predictions
        ml_weights = self._get_ml_target_weights(cursor, strategy)
        if ml_weights:
            return ml_weights

        # Fallback: equal weight distribution
        return self._get_equal_weight_targets(cursor)

    def _get_rl_target_weights(self, cursor, strategy: str) -> Dict[str, float]:
        """Get target weights from RL portfolio allocation"""
        # Query latest RL portfolio weights
        query = """
            SELECT
                ticker,
                target_weight
            FROM rl_portfolio_weights rw
            JOIN rl_portfolios rp ON rw.portfolio_id = rp.id
            WHERE rp.strategy_type = %s
                AND rp.is_active = TRUE
                AND rw.updated_at = (
                    SELECT MAX(updated_at)
                    FROM rl_portfolio_weights
                    WHERE portfolio_id = rw.portfolio_id
                )
        """

        try:
            cursor.execute(query, (strategy,))
            rows = cursor.fetchall()

            if rows:
                return {row["ticker"]: float(row["target_weight"]) for row in rows}
        except Exception as e:
            # Table might not exist yet
            pass

        return {}

    def _get_ml_target_weights(self, cursor, strategy: str) -> Dict[str, float]:
        """Generate target weights from ML predictions"""
        # Get latest ML predictions for top-scoring tickers
        query = """
            SELECT
                ticker,
                prediction_score
            FROM ml_predictions
            WHERE prediction_date = (SELECT MAX(prediction_date) FROM ml_predictions)
                AND prediction_score > 0.6
            ORDER BY prediction_score DESC
            LIMIT 30
        """

        try:
            cursor.execute(query)
            rows = cursor.fetchall()

            if rows:
                # Convert prediction scores to weights
                total_score = sum(float(row["prediction_score"]) for row in rows)
                if total_score > 0:
                    weights = {
                        row["ticker"]: float(row["prediction_score"]) / total_score for row in rows
                    }

                    # Apply position size limits (max 10% per position)
                    max_weight = 0.10
                    capped_weights = {}
                    excess = 0

                    for ticker, weight in weights.items():
                        if weight > max_weight:
                            capped_weights[ticker] = max_weight
                            excess += weight - max_weight
                        else:
                            capped_weights[ticker] = weight

                    # Redistribute excess proportionally
                    if excess > 0:
                        eligible_tickers = [t for t, w in capped_weights.items() if w < max_weight]
                        if eligible_tickers:
                            eligible_total = sum(capped_weights[t] for t in eligible_tickers)
                            if eligible_total > 0:
                                for ticker in eligible_tickers:
                                    proportion = capped_weights[ticker] / eligible_total
                                    addition = min(
                                        excess * proportion, max_weight - capped_weights[ticker]
                                    )
                                    capped_weights[ticker] += addition

                    return capped_weights
        except Exception as e:
            # Table might not exist yet
            pass

        return {}

    def _get_equal_weight_targets(self, cursor) -> Dict[str, float]:
        """
        Fallback: equal weight distribution across universe

        Gets the top 20-30 liquid stocks and assigns equal weights
        """
        query = """
            SELECT ticker, AVG(volume) as avg_volume
            FROM daily_bars
            WHERE date >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY ticker
            HAVING AVG(volume) > 1000000
            ORDER BY avg_volume DESC
            LIMIT 25
        """

        try:
            cursor.execute(query)
            rows = cursor.fetchall()

            if rows:
                n = len(rows)
                equal_weight = 1.0 / n
                return {row["ticker"]: equal_weight for row in rows}
        except Exception as e:
            pass

        return {}

    def _analyze_drift(
        self, positions: List[Position], target_weights: Dict, threshold: float
    ) -> Dict:
        """
        Analyze position drift from targets

        For positions not in target weights, target weight is 0 (should be reduced/sold)
        """
        drifts = []

        for pos in positions:
            # If ticker not in target weights, target is 0 (position should be exited)
            target = target_weights.get(pos.ticker, 0.0)
            drift = abs(pos.current_weight - target)

            drifts.append(
                {
                    "ticker": pos.ticker,
                    "current_weight": pos.current_weight,
                    "target_weight": target,
                    "drift": drift,
                    "exceeds_threshold": drift > threshold,
                    "action": self._determine_action(pos.current_weight, target, threshold),
                }
            )

        return {
            "positions": drifts,
            "max_drift": max([d["drift"] for d in drifts]) if drifts else 0,
            "avg_drift": np.mean([d["drift"] for d in drifts]) if drifts else 0,
            "positions_exceeding_threshold": sum(1 for d in drifts if d["exceeds_threshold"]),
        }

    def _determine_action(self, current: float, target: float, threshold: float) -> str:
        """Determine recommended action based on drift"""
        drift = abs(current - target)

        if drift <= threshold:
            return "HOLD"
        elif current > target:
            return "REDUCE"
        else:
            return "INCREASE"

    def _identify_underperformers(self, conn, positions: List[Position]) -> List[Dict]:
        """Identify underperforming positions based on unrealized losses"""
        underperformers = []

        for pos in positions:
            # Identify underperformers based on unrealized losses only (ML scores not available)
            if pos.market_value > 0 and pos.unrealized_gain_loss / pos.market_value < -0.10:
                underperformers.append(
                    {
                        "ticker": pos.ticker,
                        "unrealized_pnl_pct": pos.unrealized_gain_loss / pos.market_value,
                        "current_weight": pos.current_weight,
                        "market_value": pos.market_value,
                        "unrealized_loss": pos.unrealized_gain_loss,
                        "reason": f"Loss of {(pos.unrealized_gain_loss / pos.market_value * 100):.1f}%",
                    }
                )

        return sorted(underperformers, key=lambda x: x["unrealized_pnl_pct"])

    def _generate_swap_recommendations(
        self, conn, underperformers: List[Dict], strategy: str, settings: Dict
    ) -> List[SwapRecommendation]:
        """Generate swap recommendations for underperformers (ML scoring disabled)"""
        # ML-based recommendations disabled until ml_score column is available
        # Returning empty list for now
        return []

    def _find_tax_harvest_opportunities(
        self, positions: List[Position], settings: Dict
    ) -> List[Dict]:
        """Find tax-loss harvesting opportunities"""
        if not settings["tax_optimization_enabled"]:
            return []

        opportunities = []

        for pos in positions:
            # Tax-loss harvest if:
            # 1. Position has unrealized loss > $1000
            # 2. Held long enough to avoid wash sale (simplified)
            if pos.unrealized_gain_loss < -1000 and pos.days_held > 30:
                opportunities.append(
                    {
                        "ticker": pos.ticker,
                        "unrealized_loss": pos.unrealized_gain_loss,
                        "tax_benefit": abs(pos.unrealized_gain_loss)
                        * 0.25,  # Assuming 25% tax rate
                        "market_value": pos.market_value,
                        "recommendation": f"Harvest ${abs(pos.unrealized_gain_loss):.0f} loss",
                    }
                )

        return sorted(opportunities, key=lambda x: x["tax_benefit"], reverse=True)

    def _calculate_health_score(
        self, positions: List[Position], drift_analysis: Dict, underperformers: List
    ) -> float:
        """Calculate overall portfolio health score (0-100)"""
        score = 100.0

        # Penalize for drift
        score -= drift_analysis["max_drift"] * 100

        # Penalize for underperformers
        score -= len(underperformers) * 5

        # Penalize for concentration
        max_weight = max([p.current_weight for p in positions]) if positions else 0
        if max_weight > 0.15:
            score -= (max_weight - 0.15) * 100

        return max(0, min(100, score))

    def _position_to_dict(self, pos: Position) -> Dict:
        """Convert Position to dictionary"""
        return {
            "ticker": pos.ticker,
            "quantity": pos.quantity,
            "current_price": pos.current_price,
            "market_value": pos.market_value,
            "current_weight": pos.current_weight,
            "target_weight": pos.target_weight,
            "cost_basis": pos.cost_basis,
            "unrealized_gain_loss": pos.unrealized_gain_loss,
            "days_held": pos.days_held,
            "sector": pos.sector,
        }

    def _swap_to_dict(self, swap: SwapRecommendation) -> Dict:
        """Convert SwapRecommendation to dictionary"""
        return {
            "sell_ticker": swap.sell_ticker,
            "buy_ticker": swap.buy_ticker,
            "reason": swap.reason,
            "expected_improvement": swap.expected_improvement,
            "sell_ml_score": swap.sell_ml_score,
            "buy_ml_score": swap.buy_ml_score,
            "tax_impact": swap.tax_impact,
            "transaction_cost": swap.transaction_cost,
            "net_benefit": swap.net_benefit,
            "priority": swap.priority,
        }
