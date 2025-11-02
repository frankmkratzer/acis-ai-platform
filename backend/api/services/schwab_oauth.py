"""
Schwab OAuth Service

Handles OAuth2 flow for Schwab API:
1. Generate authorization URL
2. Handle OAuth callback
3. Store tokens in database
4. Refresh tokens when expired

Schwab API Documentation:
https://developer.schwab.com/
"""

import base64
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import text

# Schwab OAuth Configuration
SCHWAB_AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
SCHWAB_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
SCHWAB_CLIENT_ID = os.getenv("SCHWAB_CLIENT_ID", "")
SCHWAB_CLIENT_SECRET = os.getenv("SCHWAB_CLIENT_SECRET", "")
SCHWAB_REDIRECT_URI = os.getenv("SCHWAB_REDIRECT_URI", "http://localhost:8000/api/schwab/callback")


class SchwabOAuthService:
    """
    Schwab OAuth2 service for managing API authentication.
    """

    def __init__(self, db_session):
        self.db = db_session
        self.client_id = SCHWAB_CLIENT_ID
        self.client_secret = SCHWAB_CLIENT_SECRET
        self.redirect_uri = SCHWAB_REDIRECT_URI

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Schwab API credentials not configured. "
                "Set SCHWAB_CLIENT_ID and SCHWAB_CLIENT_SECRET environment variables."
            )

    def generate_authorization_url(
        self, client_id: int, state: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate Schwab OAuth authorization URL.

        Args:
            client_id: Internal client ID (not Schwab client ID)
            state: Optional state parameter for CSRF protection

        Returns:
            Dict with authorization_url and state
        """
        # Generate random state for CSRF protection if not provided
        if not state:
            state = secrets.token_urlsafe(32)

        # Store state in session or database for validation later
        # For now, we'll include client_id in state
        state_with_client = f"{client_id}:{state}"

        # Schwab OAuth scopes
        scopes = [
            "AccountsAndTrading",  # Read account data and place trades
            "MarketData",  # Read market data
        ]

        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": state_with_client,
        }

        # Construct URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        authorization_url = f"{SCHWAB_AUTH_URL}?{query_string}"

        return {
            "authorization_url": authorization_url,
            "state": state_with_client,
            "client_id": client_id,
            "redirect_uri": self.redirect_uri,
        }

    async def handle_callback(
        self, code: str, state: str, brokerage_id: int = 1  # Schwab brokerage ID
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback from Schwab.

        Args:
            code: Authorization code from Schwab
            state: State parameter (contains client_id)
            brokerage_id: Brokerage ID (default: 1 for Schwab)

        Returns:
            Dict with token info and client_id
        """
        # Extract client_id from state
        try:
            client_id, _ = state.split(":", 1)
            client_id = int(client_id)
        except (ValueError, AttributeError):
            raise ValueError("Invalid state parameter")

        # Exchange authorization code for access token
        token_data = await self._exchange_code_for_token(code)

        # Store tokens in database
        await self._store_tokens(
            client_id=client_id,
            brokerage_id=brokerage_id,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data["expires_in"],
            token_type=token_data.get("token_type", "Bearer"),
            scope=token_data.get("scope", ""),
        )

        return {
            "client_id": client_id,
            "brokerage_id": brokerage_id,
            "token_type": token_data["token_type"],
            "expires_in": token_data["expires_in"],
            "scope": token_data.get("scope", ""),
            "success": True,
        }

    async def _exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token response from Schwab
        """
        # Prepare Basic Auth header
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode("ascii")
        auth_base64 = base64.b64encode(auth_bytes).decode("ascii")

        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri}

        async with httpx.AsyncClient() as client:
            response = await client.post(SCHWAB_TOKEN_URL, headers=headers, data=data, timeout=30.0)

            if response.status_code != 200:
                raise Exception(
                    f"Failed to exchange code for token: {response.status_code} - {response.text}"
                )

            return response.json()

    async def _store_tokens(
        self,
        client_id: int,
        brokerage_id: int,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        token_type: str,
        scope: str,
    ):
        """
        Store OAuth tokens in database.

        Args:
            client_id: Internal client ID
            brokerage_id: Brokerage ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_in: Token expiration time in seconds
            token_type: Token type (usually "Bearer")
            scope: OAuth scopes granted
        """
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Upsert token (insert or update if exists)
        query = text(
            """
            INSERT INTO brokerage_oauth_tokens (
                client_id, brokerage_id, access_token, refresh_token,
                token_type, scope, expires_at, created_at, updated_at
            )
            VALUES (
                :client_id, :brokerage_id, :access_token, :refresh_token,
                :token_type, :scope, :expires_at, NOW(), NOW()
            )
            ON CONFLICT (client_id, brokerage_id)
            DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                token_type = EXCLUDED.token_type,
                scope = EXCLUDED.scope,
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
        """
        )

        self.db.execute(
            query,
            {
                "client_id": client_id,
                "brokerage_id": brokerage_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": token_type,
                "scope": scope,
                "expires_at": expires_at,
            },
        )

        self.db.commit()

    async def get_valid_token(self, client_id: int, brokerage_id: int = 1) -> Optional[str]:
        """
        Get a valid access token for client.
        Refreshes token if expired.

        Args:
            client_id: Internal client ID
            brokerage_id: Brokerage ID

        Returns:
            Valid access token or None if not found
        """
        # Get token from database
        query = text(
            """
            SELECT access_token, refresh_token, expires_at
            FROM brokerage_oauth_tokens
            WHERE client_id = :client_id
              AND brokerage_id = :brokerage_id
        """
        )

        result = self.db.execute(
            query, {"client_id": client_id, "brokerage_id": brokerage_id}
        ).fetchone()

        if not result:
            return None

        access_token, refresh_token, expires_at = result

        # Check if token is expired (with 5-minute buffer)
        if expires_at <= datetime.utcnow() + timedelta(minutes=5):
            # Token expired or expiring soon, refresh it
            new_token_data = await self._refresh_token(refresh_token)

            # Store new tokens
            await self._store_tokens(
                client_id=client_id,
                brokerage_id=brokerage_id,
                access_token=new_token_data["access_token"],
                refresh_token=new_token_data.get("refresh_token", refresh_token),
                expires_in=new_token_data["expires_in"],
                token_type=new_token_data.get("token_type", "Bearer"),
                scope=new_token_data.get("scope", ""),
            )

            return new_token_data["access_token"]

        return access_token

    async def _refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            New token data from Schwab
        """
        # Prepare Basic Auth header
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode("ascii")
        auth_base64 = base64.b64encode(auth_bytes).decode("ascii")

        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}

        async with httpx.AsyncClient() as client:
            response = await client.post(SCHWAB_TOKEN_URL, headers=headers, data=data, timeout=30.0)

            if response.status_code != 200:
                raise Exception(
                    f"Failed to refresh token: {response.status_code} - {response.text}"
                )

            return response.json()

    def revoke_token(self, client_id: int, brokerage_id: int = 1):
        """
        Revoke (delete) stored tokens for a client.

        Args:
            client_id: Internal client ID
            brokerage_id: Brokerage ID
        """
        query = text(
            """
            DELETE FROM brokerage_oauth_tokens
            WHERE client_id = :client_id
              AND brokerage_id = :brokerage_id
        """
        )

        self.db.execute(query, {"client_id": client_id, "brokerage_id": brokerage_id})

        self.db.commit()
