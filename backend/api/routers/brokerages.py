"""
Brokerages Router - Manage brokerage connections
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..models import schemas

router = APIRouter(prefix="/api/brokerages", tags=["Brokerages"])


@router.get("/", response_model=List[schemas.Brokerage])
async def get_brokerages(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all brokerages"""
    # Validate pagination parameters
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be non-negative")
    if limit < 0:
        raise HTTPException(status_code=400, detail="limit must be non-negative")

    query = text(
        """
        SELECT
            brokerage_id,
            name,
            display_name,
            supports_live_trading,
            supports_paper_trading,
            api_type,
            status,
            created_at,
            updated_at
        FROM brokerages
        WHERE status = 'active'
        ORDER BY name
        LIMIT :limit OFFSET :skip
    """
    )

    result = db.execute(query, {"limit": limit, "skip": skip})
    brokerages = []

    for row in result:
        brokerages.append(
            schemas.Brokerage(
                brokerage_id=row.brokerage_id,
                name=row.name,
                display_name=row.display_name,
                supports_live_trading=row.supports_live_trading,
                supports_paper_trading=row.supports_paper_trading,
                api_type=row.api_type,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )

    return brokerages


@router.get("/{brokerage_id}", response_model=schemas.Brokerage)
async def get_brokerage(brokerage_id: int, db: Session = Depends(get_db)):
    """Get a specific brokerage by ID"""
    query = text(
        """
        SELECT
            brokerage_id,
            name,
            display_name,
            supports_live_trading,
            supports_paper_trading,
            api_type,
            status,
            created_at,
            updated_at
        FROM brokerages
        WHERE brokerage_id = :brokerage_id
    """
    )

    result = db.execute(query, {"brokerage_id": brokerage_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Brokerage not found")

    return schemas.Brokerage(
        brokerage_id=result.brokerage_id,
        name=result.name,
        display_name=result.display_name,
        supports_live_trading=result.supports_live_trading,
        supports_paper_trading=result.supports_paper_trading,
        api_type=result.api_type,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post("/", response_model=schemas.Brokerage)
async def create_brokerage(brokerage: schemas.BrokerageCreate, db: Session = Depends(get_db)):
    """Create a new brokerage"""
    query = text(
        """
        INSERT INTO brokerages (
            name, display_name, supports_live_trading, supports_paper_trading,
            api_type, status, created_at, updated_at
        )
        VALUES (
            :name, :display_name, :supports_live_trading, :supports_paper_trading,
            :api_type, :status, NOW(), NOW()
        )
        RETURNING
            brokerage_id, name, display_name, supports_live_trading,
            supports_paper_trading, api_type, status, created_at, updated_at
    """
    )

    result = db.execute(
        query,
        {
            "name": brokerage.name,
            "display_name": brokerage.display_name,
            "supports_live_trading": brokerage.supports_live_trading,
            "supports_paper_trading": brokerage.supports_paper_trading,
            "api_type": brokerage.api_type or "rest",
            "status": brokerage.status or "active",
        },
    ).fetchone()

    db.commit()

    return schemas.Brokerage(
        brokerage_id=result.brokerage_id,
        name=result.name,
        display_name=result.display_name,
        supports_live_trading=result.supports_live_trading,
        supports_paper_trading=result.supports_paper_trading,
        api_type=result.api_type,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.put("/{brokerage_id}", response_model=schemas.Brokerage)
async def update_brokerage(
    brokerage_id: int, brokerage: schemas.BrokerageUpdate, db: Session = Depends(get_db)
):
    """Update an existing brokerage"""
    # Build dynamic update query
    update_fields = []
    params = {"brokerage_id": brokerage_id}

    if brokerage.name is not None:
        update_fields.append("name = :name")
        params["name"] = brokerage.name

    if brokerage.display_name is not None:
        update_fields.append("display_name = :display_name")
        params["display_name"] = brokerage.display_name

    if brokerage.supports_live_trading is not None:
        update_fields.append("supports_live_trading = :supports_live_trading")
        params["supports_live_trading"] = brokerage.supports_live_trading

    if brokerage.supports_paper_trading is not None:
        update_fields.append("supports_paper_trading = :supports_paper_trading")
        params["supports_paper_trading"] = brokerage.supports_paper_trading

    if brokerage.api_type is not None:
        update_fields.append("api_type = :api_type")
        params["api_type"] = brokerage.api_type

    if brokerage.status is not None:
        update_fields.append("status = :status")
        params["status"] = brokerage.status

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_fields.append("updated_at = NOW()")

    query = text(
        f"""
        UPDATE brokerages
        SET {", ".join(update_fields)}
        WHERE brokerage_id = :brokerage_id
        RETURNING
            brokerage_id, name, display_name, supports_live_trading,
            supports_paper_trading, api_type, status, created_at, updated_at
    """
    )

    result = db.execute(query, params).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Brokerage not found")

    db.commit()

    return schemas.Brokerage(
        brokerage_id=result.brokerage_id,
        name=result.name,
        display_name=result.display_name,
        supports_live_trading=result.supports_live_trading,
        supports_paper_trading=result.supports_paper_trading,
        api_type=result.api_type,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.delete("/{brokerage_id}")
async def delete_brokerage(brokerage_id: int, db: Session = Depends(get_db)):
    """Delete a brokerage"""
    # Check if brokerage has associated accounts
    check_query = text(
        """
        SELECT COUNT(*) as count
        FROM client_brokerage_accounts
        WHERE brokerage_id = :brokerage_id
    """
    )

    count_result = db.execute(check_query, {"brokerage_id": brokerage_id}).fetchone()

    if count_result.count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete brokerage with {count_result.count} associated accounts",
        )

    delete_query = text(
        """
        DELETE FROM brokerages
        WHERE brokerage_id = :brokerage_id
    """
    )

    result = db.execute(delete_query, {"brokerage_id": brokerage_id})
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Brokerage not found")

    return {"success": True, "message": "Brokerage deleted successfully"}


# ============================================
# Brokerage Account CRUD Endpoints
# ============================================


@router.get("/client/{client_id}/accounts", response_model=List[schemas.ClientBrokerageAccount])
async def get_client_accounts(client_id: int, db: Session = Depends(get_db)):
    """Get all brokerage accounts for a client"""
    query = text(
        """
        SELECT
            id,
            client_id,
            brokerage_id,
            account_number,
            account_hash,
            account_type,
            is_active,
            notes,
            created_at,
            updated_at
        FROM client_brokerage_accounts
        WHERE client_id = :client_id
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
                account_hash=row.account_hash,
                account_type=row.account_type,
                is_active=row.is_active,
                notes=row.notes,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )

    return accounts


@router.get("/accounts/{account_id}", response_model=schemas.ClientBrokerageAccount)
async def get_account(account_id: int, db: Session = Depends(get_db)):
    """Get a specific brokerage account by ID"""
    query = text(
        """
        SELECT
            id,
            client_id,
            brokerage_id,
            account_number,
            account_hash,
            account_type,
            is_active,
            notes,
            created_at,
            updated_at
        FROM client_brokerage_accounts
        WHERE id = :account_id
    """
    )

    result = db.execute(query, {"account_id": account_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Account not found")

    return schemas.ClientBrokerageAccount(
        id=result.id,
        client_id=result.client_id,
        brokerage_id=result.brokerage_id,
        account_number=result.account_number,
        account_hash=result.account_hash,
        account_type=result.account_type,
        is_active=result.is_active,
        notes=result.notes,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post("/accounts", response_model=schemas.ClientBrokerageAccount)
async def create_account(
    account: schemas.ClientBrokerageAccountCreate, db: Session = Depends(get_db)
):
    """Create a new brokerage account for a client"""
    # Verify client exists
    client_check = db.execute(
        text("SELECT client_id FROM clients WHERE client_id = :client_id"),
        {"client_id": account.client_id},
    ).fetchone()

    if not client_check:
        raise HTTPException(status_code=404, detail="Client not found")

    # Verify brokerage exists
    brokerage_check = db.execute(
        text("SELECT brokerage_id FROM brokerages WHERE brokerage_id = :brokerage_id"),
        {"brokerage_id": account.brokerage_id},
    ).fetchone()

    if not brokerage_check:
        raise HTTPException(status_code=404, detail="Brokerage not found")

    # Insert account
    query = text(
        """
        INSERT INTO client_brokerage_accounts
        (client_id, brokerage_id, account_number, account_hash, account_type, is_active, notes)
        VALUES (:client_id, :brokerage_id, :account_number, :account_hash, :account_type, :is_active, :notes)
        RETURNING id, client_id, brokerage_id, account_number, account_hash, account_type, is_active, notes, created_at, updated_at
    """
    )

    result = db.execute(
        query,
        {
            "client_id": account.client_id,
            "brokerage_id": account.brokerage_id,
            "account_number": account.account_number,
            "account_hash": account.account_hash or "",
            "account_type": account.account_type,
            "is_active": account.is_active if account.is_active is not None else True,
            "notes": account.notes,
        },
    ).fetchone()

    db.commit()

    return schemas.ClientBrokerageAccount(
        id=result.id,
        client_id=result.client_id,
        brokerage_id=result.brokerage_id,
        account_number=result.account_number,
        account_hash=result.account_hash,
        account_type=result.account_type,
        is_active=result.is_active,
        notes=result.notes,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.put("/accounts/{account_id}", response_model=schemas.ClientBrokerageAccount)
async def update_account(
    account_id: int, account: schemas.ClientBrokerageAccountUpdate, db: Session = Depends(get_db)
):
    """Update a brokerage account"""
    # Check if account exists
    existing = db.execute(
        text("SELECT id FROM client_brokerage_accounts WHERE id = :account_id"),
        {"account_id": account_id},
    ).fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")

    # Build update query dynamically based on provided fields
    updates = []
    params = {"account_id": account_id}

    if account.account_number is not None:
        updates.append("account_number = :account_number")
        params["account_number"] = account.account_number

    if account.account_hash is not None:
        updates.append("account_hash = :account_hash")
        params["account_hash"] = account.account_hash

    if account.account_type is not None:
        updates.append("account_type = :account_type")
        params["account_type"] = account.account_type

    if account.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = account.is_active

    if account.notes is not None:
        updates.append("notes = :notes")
        params["notes"] = account.notes

    updates.append("updated_at = CURRENT_TIMESTAMP")

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    query = text(
        f"""
        UPDATE client_brokerage_accounts
        SET {", ".join(updates)}
        WHERE id = :account_id
        RETURNING id, client_id, brokerage_id, account_number, account_hash, account_type, is_active, notes, created_at, updated_at
    """
    )

    result = db.execute(query, params).fetchone()
    db.commit()

    return schemas.ClientBrokerageAccount(
        id=result.id,
        client_id=result.client_id,
        brokerage_id=result.brokerage_id,
        account_number=result.account_number,
        account_hash=result.account_hash,
        account_type=result.account_type,
        is_active=result.is_active,
        notes=result.notes,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    """Delete a brokerage account"""
    # Check if account exists
    existing = db.execute(
        text("SELECT id, client_id FROM client_brokerage_accounts WHERE id = :account_id"),
        {"account_id": account_id},
    ).fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")

    # Delete the account
    db.execute(
        text("DELETE FROM client_brokerage_accounts WHERE id = :account_id"),
        {"account_id": account_id},
    )
    db.commit()

    return {
        "success": True,
        "message": f"Account {account_id} deleted successfully",
        "account_id": account_id,
        "client_id": existing.client_id,
    }
