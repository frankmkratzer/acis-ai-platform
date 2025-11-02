"""
Clients Router - Manage client accounts
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..models import schemas

router = APIRouter(prefix="/api/clients", tags=["Clients"])


@router.get("/", response_model=List[schemas.Client])
async def get_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all clients

    Returns list of clients with pagination
    """
    # Validate pagination parameters
    if skip < 0:
        raise HTTPException(status_code=422, detail="skip must be non-negative")
    if limit < 0:
        raise HTTPException(status_code=422, detail="limit must be non-negative")

    query = text(
        """
        SELECT
            client_id,
            client_name,
            email,
            phone,
            client_type,
            status,
            first_name,
            last_name,
            date_of_birth,
            is_active,
            auto_trading_enabled,
            trading_mode,
            risk_tolerance,
            created_at,
            updated_at
        FROM clients
        WHERE is_active = TRUE
        ORDER BY client_name
        LIMIT :limit OFFSET :skip
    """
    )

    result = db.execute(query, {"limit": limit, "skip": skip})
    clients = []

    for row in result:
        clients.append(
            schemas.Client(
                client_id=row.client_id,
                client_name=row.client_name,
                email=row.email,
                phone=row.phone,
                client_type=row.client_type,
                status=row.status,
                first_name=row.first_name,
                last_name=row.last_name,
                date_of_birth=str(row.date_of_birth) if row.date_of_birth else None,
                is_active=row.is_active,
                auto_trading_enabled=row.auto_trading_enabled,
                trading_mode=row.trading_mode,
                risk_tolerance=row.risk_tolerance,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )

    return clients


@router.get("/{client_id}", response_model=schemas.Client)
async def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get a specific client by ID"""
    query = text(
        """
        SELECT
            client_id,
            client_name,
            email,
            phone,
            client_type,
            status,
            first_name,
            last_name,
            date_of_birth,
            is_active,
            auto_trading_enabled,
            trading_mode,
            risk_tolerance,
            created_at,
            updated_at
        FROM clients
        WHERE client_id = :client_id
    """
    )

    result = db.execute(query, {"client_id": client_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Client not found")

    return schemas.Client(
        client_id=result.client_id,
        client_name=result.client_name,
        email=result.email,
        phone=result.phone,
        client_type=result.client_type,
        status=result.status,
        first_name=result.first_name,
        last_name=result.last_name,
        date_of_birth=str(result.date_of_birth) if result.date_of_birth else None,
        is_active=result.is_active,
        auto_trading_enabled=result.auto_trading_enabled,
        trading_mode=result.trading_mode,
        risk_tolerance=result.risk_tolerance,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post("/", response_model=schemas.Client)
async def create_client(client: schemas.ClientCreate, db: Session = Depends(get_db)):
    """Create a new client"""
    query = text(
        """
        INSERT INTO clients (
            client_name, email, phone, client_type, status,
            first_name, last_name, date_of_birth, is_active, created_at, updated_at
        )
        VALUES (
            :client_name, :email, :phone, :client_type, :status,
            :first_name, :last_name, :date_of_birth, TRUE, NOW(), NOW()
        )
        RETURNING client_id, client_name, email, phone, client_type,
                  status, first_name, last_name, date_of_birth, is_active,
                  auto_trading_enabled, trading_mode, risk_tolerance,
                  created_at, updated_at
    """
    )

    result = db.execute(
        query,
        {
            "client_name": client.client_name,
            "email": client.email,
            "phone": client.phone,
            "client_type": client.client_type or "individual",
            "status": client.status or "active",
            "first_name": client.first_name,
            "last_name": client.last_name,
            "date_of_birth": client.date_of_birth,
        },
    ).fetchone()

    db.commit()

    return schemas.Client(
        client_id=result.client_id,
        client_name=result.client_name,
        email=result.email,
        phone=result.phone,
        client_type=result.client_type,
        status=result.status,
        first_name=result.first_name,
        last_name=result.last_name,
        date_of_birth=str(result.date_of_birth) if result.date_of_birth else None,
        is_active=result.is_active,
        auto_trading_enabled=result.auto_trading_enabled,
        trading_mode=result.trading_mode,
        risk_tolerance=result.risk_tolerance,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.put("/{client_id}", response_model=schemas.Client)
async def update_client(
    client_id: int, client: schemas.ClientUpdate, db: Session = Depends(get_db)
):
    """Update an existing client"""
    # Build update query dynamically based on provided fields
    update_fields = []
    params = {"client_id": client_id}

    if client.client_name is not None:
        update_fields.append("client_name = :client_name")
        params["client_name"] = client.client_name

    if client.email is not None:
        update_fields.append("email = :email")
        params["email"] = client.email

    if client.phone is not None:
        update_fields.append("phone = :phone")
        params["phone"] = client.phone

    if client.client_type is not None:
        update_fields.append("client_type = :client_type")
        params["client_type"] = client.client_type

    if client.status is not None:
        update_fields.append("status = :status")
        params["status"] = client.status

    if client.first_name is not None:
        update_fields.append("first_name = :first_name")
        params["first_name"] = client.first_name

    if client.last_name is not None:
        update_fields.append("last_name = :last_name")
        params["last_name"] = client.last_name

    if client.date_of_birth is not None:
        update_fields.append("date_of_birth = :date_of_birth")
        params["date_of_birth"] = client.date_of_birth

    if client.auto_trading_enabled is not None:
        update_fields.append("auto_trading_enabled = :auto_trading_enabled")
        params["auto_trading_enabled"] = client.auto_trading_enabled

    if client.trading_mode is not None:
        update_fields.append("trading_mode = :trading_mode")
        params["trading_mode"] = client.trading_mode

    if client.risk_tolerance is not None:
        update_fields.append("risk_tolerance = :risk_tolerance")
        params["risk_tolerance"] = client.risk_tolerance

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_fields.append("updated_at = NOW()")

    query = text(
        f"""
        UPDATE clients
        SET {", ".join(update_fields)}
        WHERE client_id = :client_id
        RETURNING client_id, client_name, email, phone, client_type,
                  status, first_name, last_name, date_of_birth, is_active, auto_trading_enabled,
                  trading_mode, risk_tolerance, created_at, updated_at
    """
    )

    result = db.execute(query, params).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Client not found")

    db.commit()

    return schemas.Client(
        client_id=result.client_id,
        client_name=result.client_name,
        email=result.email,
        phone=result.phone,
        client_type=result.client_type,
        status=result.status,
        first_name=result.first_name,
        last_name=result.last_name,
        date_of_birth=str(result.date_of_birth) if result.date_of_birth else None,
        is_active=result.is_active,
        auto_trading_enabled=result.auto_trading_enabled,
        trading_mode=result.trading_mode,
        risk_tolerance=result.risk_tolerance,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.delete("/{client_id}")
async def delete_client(client_id: int, db: Session = Depends(get_db)):
    """Soft delete a client (set is_active = FALSE)"""
    query = text(
        """
        UPDATE clients
        SET is_active = FALSE, updated_at = NOW()
        WHERE client_id = :client_id
        RETURNING client_id
    """
    )

    result = db.execute(query, {"client_id": client_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Client not found")

    db.commit()

    return {"message": "Client deleted successfully", "client_id": client_id}


@router.get("/{client_id}/accounts", response_model=List[schemas.ClientBrokerageAccount])
async def get_client_accounts(client_id: int, db: Session = Depends(get_db)):
    """Get all brokerage accounts for a client"""
    query = text(
        """
        SELECT
            id,
            client_id,
            brokerage_id,
            account_number,
            account_type,
            is_active,
            notes,
            created_at,
            updated_at
        FROM client_brokerage_accounts
        WHERE client_id = :client_id AND is_active = TRUE
        ORDER BY created_at DESC
    """
    )

    result = db.execute(query, {"client_id": client_id})
    accounts = []

    for row in result:
        accounts.append(
            schemas.ClientBrokerageAccount(
                id=row.id,
                client_id=row.client_id,
                brokerage_id=row.brokerage_id,
                account_number=row.account_number,
                account_type=row.account_type,
                is_active=row.is_active,
                notes=row.notes,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )

    return accounts


# ============================================
# Autonomous Trading Settings Endpoints
# ============================================


@router.get("/{client_id}/autonomous-settings")
async def get_client_autonomous_settings(client_id: int, db: Session = Depends(get_db)):
    """
    Get autonomous trading settings for a client

    Returns all autonomous trading configuration including:
    - Opt-in status
    - Risk tolerance
    - Rebalancing preferences
    - Position limits
    - Strategy preferences
    """
    try:
        query = text(
            """
            SELECT
                auto_trading_enabled,
                trading_mode,
                risk_tolerance,
                rebalance_frequency,
                drift_threshold,
                max_position_size,
                allowed_strategies,
                min_cash_balance,
                tax_optimization_enabled,
                esg_preferences,
                sector_limits
            FROM clients
            WHERE client_id = :client_id
        """
        )

        result = db.execute(query, {"client_id": client_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Client not found")

        return {
            "client_id": client_id,
            "auto_trading_enabled": row.auto_trading_enabled,
            "trading_mode": row.trading_mode or "paper",
            "risk_tolerance": row.risk_tolerance,
            "rebalance_frequency": row.rebalance_frequency,
            "drift_threshold": float(row.drift_threshold) if row.drift_threshold else 0.05,
            "max_position_size": float(row.max_position_size) if row.max_position_size else 0.10,
            "allowed_strategies": row.allowed_strategies or [],
            "min_cash_balance": float(row.min_cash_balance) if row.min_cash_balance else 1000.0,
            "tax_optimization_enabled": row.tax_optimization_enabled,
            "esg_preferences": row.esg_preferences or {},
            "sector_limits": row.sector_limits or {},
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching autonomous settings: {str(e)}")


@router.put("/{client_id}/autonomous-settings")
async def update_client_autonomous_settings(
    client_id: int, settings: dict, db: Session = Depends(get_db)
):
    """
    Update autonomous trading settings for a client

    Allows updating any of:
    - auto_trading_enabled
    - risk_tolerance
    - rebalance_frequency
    - drift_threshold
    - max_position_size
    - allowed_strategies
    - min_cash_balance
    - tax_optimization_enabled
    - esg_preferences
    - sector_limits
    """
    try:
        # Verify client exists
        check_query = text("SELECT client_id FROM clients WHERE client_id = :client_id")
        result = db.execute(check_query, {"client_id": client_id})
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Client not found")

        # Build dynamic update query
        update_parts = []
        params = {"client_id": client_id}

        if "auto_trading_enabled" in settings:
            update_parts.append("auto_trading_enabled = :auto_trading_enabled")
            params["auto_trading_enabled"] = settings["auto_trading_enabled"]

        if "trading_mode" in settings:
            if settings["trading_mode"] not in ["paper", "live"]:
                raise HTTPException(
                    status_code=400, detail="Invalid trading_mode. Must be: paper or live"
                )
            update_parts.append("trading_mode = :trading_mode")
            params["trading_mode"] = settings["trading_mode"]

        if "risk_tolerance" in settings:
            if settings["risk_tolerance"] not in ["conservative", "moderate", "aggressive"]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid risk_tolerance. Must be: conservative, moderate, or aggressive",
                )
            update_parts.append("risk_tolerance = :risk_tolerance")
            params["risk_tolerance"] = settings["risk_tolerance"]

        if "rebalance_frequency" in settings:
            if settings["rebalance_frequency"] not in [
                "daily",
                "weekly",
                "monthly",
                "quarterly",
                "threshold",
            ]:
                raise HTTPException(status_code=400, detail="Invalid rebalance_frequency")
            update_parts.append("rebalance_frequency = :rebalance_frequency")
            params["rebalance_frequency"] = settings["rebalance_frequency"]

        if "drift_threshold" in settings:
            if not (0.01 <= settings["drift_threshold"] <= 1.0):
                raise HTTPException(
                    status_code=400, detail="drift_threshold must be between 0.01 and 1.0"
                )
            update_parts.append("drift_threshold = :drift_threshold")
            params["drift_threshold"] = settings["drift_threshold"]

        if "max_position_size" in settings:
            if not (0.01 <= settings["max_position_size"] <= 1.0):
                raise HTTPException(
                    status_code=400, detail="max_position_size must be between 0.01 and 1.0"
                )
            update_parts.append("max_position_size = :max_position_size")
            params["max_position_size"] = settings["max_position_size"]

        if "allowed_strategies" in settings:
            update_parts.append("allowed_strategies = :allowed_strategies")
            params["allowed_strategies"] = settings["allowed_strategies"]

        if "min_cash_balance" in settings:
            update_parts.append("min_cash_balance = :min_cash_balance")
            params["min_cash_balance"] = settings["min_cash_balance"]

        if "tax_optimization_enabled" in settings:
            update_parts.append("tax_optimization_enabled = :tax_optimization_enabled")
            params["tax_optimization_enabled"] = settings["tax_optimization_enabled"]

        if "esg_preferences" in settings:
            import json

            update_parts.append("esg_preferences = CAST(:esg_preferences AS jsonb)")
            params["esg_preferences"] = json.dumps(settings["esg_preferences"])

        if "sector_limits" in settings:
            import json

            update_parts.append("sector_limits = CAST(:sector_limits AS jsonb)")
            params["sector_limits"] = json.dumps(settings["sector_limits"])

        if not update_parts:
            raise HTTPException(status_code=400, detail="No valid settings provided")

        # Add updated_at
        update_parts.append("updated_at = CURRENT_TIMESTAMP")

        update_query = text(
            f"""
            UPDATE clients
            SET {', '.join(update_parts)}
            WHERE client_id = :client_id
        """
        )

        db.execute(update_query, params)
        db.commit()

        # Fetch and return updated settings
        return await get_client_autonomous_settings(client_id, db)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating autonomous settings: {str(e)}")


@router.get("/aggregate/portfolio-stats")
async def get_aggregate_portfolio_stats(db: Session = Depends(get_db)):
    """
    Get aggregate portfolio statistics across all active clients

    Returns:
    - Total portfolio value across all client accounts
    - Total number of active client accounts
    - Total number of positions across all accounts
    - Breakdown by client
    """
    try:
        # Aggregate query to sum portfolio values from paper_positions + cash from paper_accounts
        # Use subqueries to avoid double-counting cash when joining with positions
        query = text(
            """
            SELECT
                COUNT(DISTINCT cba.client_id) as total_clients,
                COUNT(DISTINCT cba.account_hash) as total_accounts,
                COALESCE(
                    (SELECT SUM(market_value) FROM paper_positions WHERE account_id IN
                        (SELECT account_hash FROM client_brokerage_accounts WHERE is_active = true)
                    ), 0
                ) as total_positions_value,
                COALESCE(
                    (SELECT SUM(cash_balance) FROM paper_accounts WHERE account_id IN
                        (SELECT account_hash FROM client_brokerage_accounts WHERE is_active = true)
                    ), 0
                ) as total_cash,
                COALESCE(
                    (SELECT SUM(market_value) FROM paper_positions WHERE account_id IN
                        (SELECT account_hash FROM client_brokerage_accounts WHERE is_active = true)
                    ), 0
                ) + COALESCE(
                    (SELECT SUM(cash_balance) FROM paper_accounts WHERE account_id IN
                        (SELECT account_hash FROM client_brokerage_accounts WHERE is_active = true)
                    ), 0
                ) as total_portfolio_value,
                (SELECT COUNT(*) FROM paper_positions WHERE account_id IN
                    (SELECT account_hash FROM client_brokerage_accounts WHERE is_active = true)
                ) as total_positions
            FROM client_brokerage_accounts cba
            WHERE cba.is_active = true
        """
        )

        result = db.execute(query).fetchone()

        # Get per-client breakdown (positions + cash)
        # Use subqueries to avoid double-counting
        breakdown_query = text(
            """
            SELECT
                c.client_id,
                c.first_name,
                c.last_name,
                c.email,
                cba.account_hash,
                COALESCE(
                    (SELECT SUM(market_value) FROM paper_positions
                     WHERE account_id = cba.account_hash), 0
                ) + COALESCE(
                    (SELECT cash_balance FROM paper_accounts
                     WHERE account_id = cba.account_hash), 0
                ) as portfolio_value,
                COALESCE(
                    (SELECT COUNT(*) FROM paper_positions
                     WHERE account_id = cba.account_hash), 0
                ) as num_positions
            FROM clients c
            JOIN client_brokerage_accounts cba ON cba.client_id = c.client_id
            WHERE c.is_active = true AND cba.is_active = true
            ORDER BY portfolio_value DESC
        """
        )

        breakdown_result = db.execute(breakdown_query)
        breakdown = []

        for row in breakdown_result:
            breakdown.append(
                {
                    "client_id": row.client_id,
                    "client_name": f"{row.first_name} {row.last_name}",
                    "email": row.email,
                    "account_hash": row.account_hash,
                    "portfolio_value": float(row.portfolio_value),
                    "num_positions": row.num_positions,
                }
            )

        return {
            "total_portfolio_value": float(result.total_portfolio_value),
            "total_positions_value": float(result.total_positions_value),
            "total_cash": float(result.total_cash),
            "total_clients": result.total_clients,
            "total_accounts": result.total_accounts,
            "total_positions": result.total_positions,
            "breakdown": breakdown,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching aggregate portfolio stats: {str(e)}"
        )


@router.post("/{client_id}/sync-balance-from-schwab")
async def sync_balance_from_schwab(client_id: int, db: Session = Depends(get_db)):
    """
    Fetch current Schwab account balance and update paper_accounts

    This allows paper trading and backtesting to start with accurate real account balances.
    """
    try:
        # Get client's brokerage account info
        account_query = text(
            """
            SELECT cba.account_hash, cba.brokerage_id
            FROM client_brokerage_accounts cba
            WHERE cba.client_id = :client_id
              AND cba.is_active = true
            LIMIT 1
        """
        )
        account_result = db.execute(account_query, {"client_id": client_id}).fetchone()

        if not account_result:
            raise HTTPException(
                status_code=404, detail="No active brokerage account found for this client"
            )

        account_hash = account_result.account_hash
        brokerage_id = account_result.brokerage_id

        # Get OAuth token for this client
        token_query = text(
            """
            SELECT access_token, expires_at
            FROM brokerage_oauth_tokens
            WHERE client_id = :client_id AND brokerage_id = :brokerage_id
            ORDER BY created_at DESC
            LIMIT 1
        """
        )
        token_result = db.execute(
            token_query, {"client_id": client_id, "brokerage_id": brokerage_id}
        ).fetchone()

        if not token_result or not token_result.access_token:
            raise HTTPException(
                status_code=404, detail="No valid Schwab OAuth token found for this client"
            )

        access_token = token_result.access_token

        # Import here to avoid circular dependencies
        from ..services.schwab_api import SchwabAPIClient

        # Initialize Schwab API client
        schwab = SchwabAPIClient(access_token=access_token)

        # Fetch account details from Schwab
        account_data = await schwab.get_account(account_hash, fields="positions")

        # Extract balance information
        balances = account_data.get("securitiesAccount", {})
        initial_balances = balances.get("initialBalances", {})
        current_balances = balances.get("currentBalances", {})

        # Get cash balance and account value
        cash_balance = current_balances.get("cashBalance", 0) or 0
        buying_power = current_balances.get("buyingPower", 0) or 0
        account_value = current_balances.get("liquidationValue", 0) or 0

        # Update paper_accounts table directly
        update_query = text(
            """
            INSERT INTO paper_accounts (account_id, cash_balance, buying_power, total_value, updated_at)
            VALUES (:account_id, :cash_balance, :buying_power, :total_value, NOW())
            ON CONFLICT (account_id)
            DO UPDATE SET
                cash_balance = EXCLUDED.cash_balance,
                buying_power = EXCLUDED.buying_power,
                total_value = EXCLUDED.total_value,
                updated_at = NOW()
        """
        )

        db.execute(
            update_query,
            {
                "account_id": account_hash,
                "cash_balance": float(cash_balance),
                "buying_power": float(buying_power),
                "total_value": float(account_value),
            },
        )
        db.commit()

        return {
            "success": True,
            "account_hash": account_hash,
            "synced_balance": {
                "cash_balance": float(cash_balance),
                "buying_power": float(buying_power),
                "account_value": float(account_value),
            },
            "message": "Balance synced successfully from Schwab",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing balance from Schwab: {str(e)}")
