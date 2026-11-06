"""Shared-token authentication for the explicitly shared prototype workspace."""

import hmac

from fastmcp.server.auth import AccessToken, TokenVerifier
from pydantic import SecretStr


class SharedTokenVerifier(TokenVerifier):
    def __init__(self, token: SecretStr, base_url: str):
        super().__init__(base_url=base_url, required_scopes=["regulatory:access"])
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token.encode(), self._token.get_secret_value().encode()):
            return None
        return AccessToken(token=token, client_id="shared-prototype", scopes=["regulatory:access"])
